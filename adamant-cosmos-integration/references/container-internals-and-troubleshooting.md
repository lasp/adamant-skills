# COSMOS Container Internals and Troubleshooting

Operational reference for understanding the internal architecture of OpenC3 COSMOS
containers and diagnosing service-level failures. This covers the infrastructure
layer beneath the scripting API -- the processes, transports, and Docker services
that must be healthy for script execution to work.

## Container Architecture

### Services Overview

A COSMOS deployment runs 6+ Docker containers:

| Container | Role | Ports (internal) |
|-----------|------|-----------------|
| `openc3-cosmos-cmd-tlm-api` | Command/telemetry REST API, `openc3cli` host | 2901 (web), 3901 (ws) |
| `openc3-cosmos-script-runner-api` | Script execution engine | 2902 (web), 3902 (ws) |
| `openc3-operator` | Manages microservices (interfaces, routers, decom) | -- |
| `openc3-redis` | Persistent Redis -- configuration, script state | 6379 |
| `openc3-redis-ephemeral` | Ephemeral Redis -- transient telemetry, current values | 6380 |
| `openc3-minio` | Object storage (S3-compatible) -- logs, scripts, plugins | 9000 |
| `openc3-traefik` | Reverse proxy -- routes HTTP/WebSocket to correct API | 80 |

### Inside script-runner-api

The `openc3-cosmos-script-runner-api` container is not a single process. It uses
**shoreman** (a lightweight process manager) to run three processes from a Procfile:

| Process | Binary | Language | Role |
|---------|--------|----------|------|
| `web` | Puma (Rails) | Ruby | REST API for script CRUD, status queries (port 2902) |
| `ws` | **anycable-go** | **Go** | WebSocket server for real-time script output streaming (port 3902) |
| `rpc` | anycable | Ruby | gRPC RPC server bridging WebSocket events to Rails and the script runner |

The separation exists because Ruby's GIL makes native WebSocket handling inefficient
at scale. AnyCable replaces Rails' ActionCable with a Go binary for the WebSocket
layer, keeping application logic in Ruby. The Go and Ruby processes communicate
over **gRPC on localhost:50051** inside the container.

The `cmd-tlm-api` container has the same three-process architecture
(Puma + anycable-go + anycable Ruby RPC) on ports 2901/3901.

### Script Execution Flow

```
openc3cli script run (Ruby, inside cmd-tlm-api)
    │
    │  1. POST /script-api/scripts/.../run   (REST to script-runner-api Puma)
    │  2. WebSocket /script-api/cable         (to script-runner-api anycable-go via traefik)
    ▼
anycable-go (Go, inside script-runner-api)
    │
    │  gRPC (localhost:50051)
    ▼
anycable Ruby RPC (inside script-runner-api)
    │
    │  Redis Streams (pub/sub for script output)
    ▼
RunningScript (Ruby worker)
    │
    │  OpenC3 Python scripting API
    ▼
test_suite.py
```

**Critical detail:** `openc3cli script run` holds a **single long-lived WebSocket
connection** for the entire script/suite execution. There is no reconnection or
retry in `cli_script_monitor`. If the WebSocket drops at any point, the CLI
receives empty bytes, `JSON.parse("")` fails, and the run is lost.

### The `$stdout.sync` Pattern

When running `openc3cli` via `docker compose exec`, Ruby buffers stdout by default.
This means no output is streamed until the process exits -- breaking real-time
progress monitoring. The fix is to force line-buffered output:

```bash
# WRONG -- output buffered, nothing streams until completion:
docker compose exec -T openc3-cosmos-cmd-tlm-api \
  ruby /openc3/bin/openc3cli script run TARGET/procedures/test.py

# CORRECT -- stdout.sync forces line-buffered output:
docker compose exec -T openc3-cosmos-cmd-tlm-api \
  ruby -e '$stdout.sync=true; load "/openc3/bin/openc3cli"' \
  -- script run TARGET/procedures/test.py
```

This matters for any CI pipeline or wrapper script that parses openc3cli output
in real time (progress reporting, log capture, failure detection).

For the complete set of `docker compose exec` invocation patterns (single script,
full suite, group, running/stop), see the
[Test Script Execution section in SKILL.md](../SKILL.md#test-script-execution).

## Troubleshooting

### Diagnostic Commands

```bash
# Check container status (look for restarts, exit codes):
docker compose ps -a

# Check if a container restarted mid-run (uptime shorter than test duration):
docker inspect --format='{{.State.StartedAt}}' <container>

# Check for OOM kills:
docker inspect --format='{{.State.OOMKilled}}' <container>

# Service logs at failure time:
docker logs --since <timestamp> <container>

# Check for gRPC transport errors (GoAway, keepalive issues):
docker logs <script-runner-api-container> 2>&1 | grep -i "GoAway\|ENHANCE_YOUR_CALM\|too_many_pings"

# Check Redis connectivity:
docker logs <script-runner-api-container> 2>&1 | grep -i "Redis connection failed\|CannotConnectError"
```

### Common Service-Level Failures

| Symptom | Likely Cause | Diagnostic |
|---------|-------------|-----------|
| `unexpected end of input at line 1 column 1` / `Have you called 'script init'?` | WebSocket dropped between openc3cli and script-runner-api | Check script-runner-api logs for GoAway, Redis errors, or Ruby exceptions |
| `Unable to retrieve: TARGET/procedures/script.py in scope DEFAULT` | Script not in MinIO/plugin storage | Script must be uploaded via COSMOS Script Runner GUI or API, not just copied to container filesystem |
| `Redis connection failed ... no such host` | Redis container restarted or DNS not ready | Check redis container status; ensure services started in dependency order |
| Script hangs indefinitely | Script Runner API process died and restarted (shoreman respawns) | Check container restart count and uptime |
| `0 test results received` | openc3cli WebSocket died before any results were reported | Check script-runner-api logs; the test may have run but output was lost |
| Container in `Restarting` state | Configuration error or dependency not available | Check `docker logs` for the specific error; common: bad env var, missing volume |

### gRPC Keepalive / GoAway Issue

The anycable-go process (gRPC client) sends keepalive pings to the Ruby gRPC server
every 30 seconds by default. The Ruby gRPC server enforces a 300-second minimum
between pings (Go gRPC default `EnforcementPolicy.MinTime`). This mismatch causes
periodic `ENHANCE_YOUR_CALM` / `too_many_pings` GoAway frames that tear down the
gRPC connection.

Most GoAway events are survived (the gRPC client reconnects automatically), but
when a GoAway coincides with an active RPC, the in-flight operation fails, the
WebSocket drops, and the openc3cli monitoring session is lost.

**Fix:** Increase the `keepalive_ping_interval` in anycable-go to match the
server's 300-second enforcement minimum. This setting is only configurable via
a TOML config file (not environment variable or CLI flag in v1.6.1). The TOML
file is auto-discovered at `./anycable.toml` in anycable-go's working directory
(`/src/` in the container).

Docker Compose `configs:` can inject the file without bind mounts:

```yaml
services:
  openc3-cosmos-script-runner-api:
    configs:
      - source: anycable-go-config
        target: /src/anycable.toml

configs:
  anycable-go-config:
    content: |
      [rpc]
      keepalive_ping_interval = 300
```

Verify the fix is active by checking the container startup logs for:
```
INF Using configuration from file: ./anycable.toml
```

And confirming zero GoAway errors after a test run:
```bash
docker logs <script-runner-api-container> 2>&1 | grep -c "ENHANCE_YOUR_CALM"
```
