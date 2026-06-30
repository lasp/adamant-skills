---
name: adamant-cosmos-suite-results
description: Run a COSMOS test suite headless from automation/CI and gate on pass/fail. Use when launching a suite via openc3cli script run (or the Script Runner REST API), streaming and parsing its results, and gating a pipeline on the outcome. Covers the version-stable stream method and the COSMOS 6.x (MinIO) vs 7.x (versitygw) object-store rename.
---

# COSMOS Suite Execution + Result Verification

Run a COSMOS test suite without the GUI and gate a pipeline on its result. The
version-stable path runs the suite via `openc3cli script run` inside the
cmd-tlm-api container and reads the result from the **streamed output plus the
process exit code** -- no object-store retrieval. (Earlier setups pulled the suite
log from the MinIO bucket; COSMOS 7.x replaced MinIO with versitygw, so the stream
method is both simpler and store-independent.)

## Architecture

```
Driver (bash/python)
  |
  |--> openc3cli script run (inside openc3-cosmos-cmd-tlm-api, $stdout.sync=true)
  |        |  suite emits result/report/summary lines on stdout
  |        v
  |--> stream parser (tee + classify) --> filtered log + live progress
  |        |
  |        v
  +--> exit code: 0 = all pass, non-zero = a failure   <-- the authoritative gate
       (on failure: docker compose logs <service> for debugging)
```

## Method A -- `openc3cli script run` + stream (preferred, version-stable)

Run the suite via the CLI inside `openc3-cosmos-cmd-tlm-api`, unbuffered, and pipe
stdout to a parser. The pipeline's exit status is the authoritative gate.

```bash
docker compose -f <compose> exec -T openc3-cosmos-cmd-tlm-api \
  ruby -e '$stdout.sync=true; load "/openc3/bin/openc3cli"' \
  -- script run "<SCRIPT_PATH>" \
       --suite "<SuiteClass>" \
       --method start \
       --options "continueAfterError" \
       --scope DEFAULT \
  2>&1 | tee suite_results.log
STATUS=${PIPESTATUS[0]}   # 0 = all tests passed; non-zero = a failure occurred
```

- `$stdout.sync=true` makes the suite output unbuffered, so a parser sees results live.
- `--method start` runs the suite's start entrypoint; `--options` passes suite-runner flags
  (`continueAfterError` runs every test even after a failure; `manual` skips interactive prompts).
- The suite emits structured lines on stdout (per-test results, report lines, a final summary).
  **Gate on the exit code**, not on grep counts -- the run exits non-zero iff any test failed.
- A richer parser can classify the stream into started / result / summary events for live
  progress and a filtered log; the exit code stays the gate. Keep the parser project-specific.

### Stop a running suite
```bash
docker compose -f <compose> exec -T openc3-cosmos-cmd-tlm-api \
  ruby /openc3/bin/openc3cli script running --scope DEFAULT      # list running ids (col 1)
docker compose -f <compose> exec -T openc3-cosmos-cmd-tlm-api \
  ruby /openc3/bin/openc3cli script stop <id> --scope DEFAULT
```

### Debugging: per-service container logs (store-independent)
```bash
for s in $(docker compose -f <compose> config --services); do
  docker compose -f <compose> logs "$s" > "${s}_$(date +%Y%m%d-%H%M%S).log" 2>/dev/null || true
done
```
This enumerates services dynamically, so it adapts to renamed/added 7.x services
(`openc3-buckets`, `openc3-tsdb`) automatically.

## Method B -- Script Runner REST API (run + poll)

An alternative HTTP trigger (base `http://localhost:2900`, header
`Authorization: openc3service`). The endpoint surface is COSMOS-version-dependent --
verify against your deployment before relying on it.

```bash
BASE=http://localhost:2900 ; AUTH="Authorization: openc3service" ; SCOPE=DEFAULT
# load (expect 200) -> lock -> run
curl -s -w '%{http_code}' -H "$AUTH" "$BASE/script-api/scripts/$SCRIPT/?scope=$SCOPE" -o /dev/null
curl -s -X POST -H "$AUTH" "$BASE/script-api/scripts/$SCRIPT/lock?scope=$SCOPE" -o /dev/null
curl -s -X POST -H 'Content-Type: application/json' -H "$AUTH" \
  "$BASE/script-api/scripts/$SCRIPT/run?scope=$SCOPE" \
  --data-raw '{"environment":[],"suiteRunner":{"method":"start","suite":"TestSuite","options":["continueAfterError"]}}'
# poll until empty, then read completion info (incl. log file names)
curl -s -H "$AUTH" "$BASE/script-api/running-script?scope=$SCOPE"     # [] == finished
curl -s -H "$AUTH" "$BASE/script-api/completed-scripts?scope=$SCOPE"
```

Prefer Method A's exit-code gate over retrieving and parsing an object-store log.

## Object store: COSMOS 6.x MinIO vs 7.x versitygw

COSMOS keeps tool logs in the `openc3-logs` bucket; the backing service changed at 7.0:

| | 6.x | 7.x |
|---|---|---|
| Service | `openc3-minio` (MinIO) | `openc3-buckets` (versitygw, S3-compatible) |
| Volume | `openc3-bucket-v` | `openc3-object-v` |
| Credentials | `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `ROOT_ACCESS_KEY` / `ROOT_SECRET_KEY` |
| Bucket URL host | `openc3-minio:9000` | `openc3-buckets:9000` |
| In-container client | `mc` with a preconfigured `local` alias | none -- use an S3 client (e.g. aws-cli) |

A bare image-tag bump to 7.x fails (`openc3-minio` publishes no 7.x tag). Because
versitygw ships no `mc`/`local`, any 6.x retrieval that did
`docker exec <minio> mc cp local/openc3-logs/...` must move to an S3 client -- or, better,
gate on Method A's stream + exit code so result verification does not depend on the store.

Suite-log path (both versions): `DEFAULT/tool_logs/sr/YYYY_MM_DD/` (underscored dates). The
Script Runner log lines are timestamped:
```
YYYY/MM/DD HH:MM:SS.SSS | SCRIPTRUNNER | <test_name> | PASS
YYYY/MM/DD HH:MM:SS.SSS | SCRIPTRUNNER | <test_name> | FAIL | <error message>
```

## COSMOS container names (compose stack)
```
openc3-cosmos-cmd-tlm-api   -- API server + the openc3cli entrypoint (run scripts here)
openc3-operator             -- manages microservices
openc3-traefik              -- reverse proxy (port 2900)
openc3-buckets              -- object store (versitygw; 6.x: openc3-minio)
openc3-tsdb                 -- time-series telemetry store (7.x; mandatory)
```
Resolve names dynamically: `docker compose -f <compose> config --services`.

## Guidelines
1. Gate CI on the run's **exit code** (Method A), not on grep counts or bucket availability.
2. `continueAfterError` -> partial results beat an early abort.
3. Run inside `openc3-cosmos-cmd-tlm-api`; stop a run via `openc3cli script stop <id>`.
4. `docker compose logs <service>` is the version-independent debug source; only collect on failure.
5. On 7.x, MinIO is gone (versitygw / `openc3-buckets`) -- do not rely on `mc`/`local`.
6. Give the suite a generous timeout for large assemblies; poll/stream rather than block blindly.
