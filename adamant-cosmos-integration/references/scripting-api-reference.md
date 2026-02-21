# COSMOS Scripting API Reference for Adamant

<!-- source: openc3/cosmos (openc3/lib/openc3/api/) -->

## Command API

| Method | Description |
|--------|-------------|
| `cmd("TGT CMD with P1 v, P2 v")` | Send command with range + hazardous checks |
| `cmd_raw(...)` | Send command without parameter conversions |
| `cmd_no_range_check(...)` | Skip range validation |
| `cmd_no_hazardous_check(...)` | Skip hazardous confirmation |
| `cmd_no_checks(...)` | Skip all checks |
| `build_cmd(...)` | Build command binary without sending |
| `enable_cmd("TGT", "CMD")` | Re-enable a disabled command |
| `disable_cmd("TGT", "CMD")` | Disable a command (raises DisabledError if sent) |
| `send_raw("INTERFACE", data)` | Send raw binary to a named interface |
| `get_all_cmd_names("TGT")` | List all command names for target |
| `get_cmd("TGT", "CMD")` | Get command packet definition hash |
| `get_cmd_hazardous("TGT", "CMD", params)` | Check if command is hazardous with given params |
| `get_cmd_cnt("TGT", "CMD")` | Get transmit count |
| `get_cmd_time("TGT")` | Get timestamp of most recent command |

## Telemetry API

| Method | Description |
|--------|-------------|
| `tlm("TGT PKT ITEM")` | Get converted telemetry value |
| `tlm_raw("TGT PKT ITEM")` | Get raw (unconverted) value |
| `tlm_formatted("TGT PKT ITEM")` | Get formatted string value |
| `set_tlm("TGT PKT ITEM = val")` | Set CVT item (overwritten by next packet) |
| `override_tlm("TGT PKT ITEM = val")` | Override CVT item persistently (survives new packets) |
| `normalize_tlm("TGT PKT ITEM")` | Remove an override |
| `inject_tlm("TGT", "PKT", {items}, type:)` | Inject synthetic telemetry (useful for testing) |
| `get_tlm_packet("TGT", "PKT")` | Get all item values + limits states |
| `subscribe_packets([[TGT, PKT], ...])` | Subscribe to packet stream, returns subscription ID |
| `get_packets(id, count: 1000)` | Poll for new packets on subscription |
| `get_tlm_cnt("TGT", "PKT")` | Get receive count |
| `get_all_tlm_names("TGT")` | List all telemetry packet names |

**LATEST packet**: Use `"TGT LATEST ITEM"` to auto-resolve to the most recent packet containing the item.

## Interface Management API

| Method | Description |
|--------|-------------|
| `get_interface("INT_NAME")` | Get interface info hash (model + status) |
| `get_interface_names` | List all interface names |
| `connect_interface("INT_NAME")` | Connect/reconnect an interface |
| `disconnect_interface("INT_NAME")` | Disconnect an interface |
| `get_all_interface_info` | Returns [name, state, clients, txsize, rxsize, txbytes, rxbytes, txcnt, rxcnt] per interface |

Use `get_all_interface_info` to verify the Adamant TCP connection state programmatically.

## Limits API

| Method | Description |
|--------|-------------|
| `get_out_of_limits` | Returns [[target, packet, item, state], ...] for all violations |
| `get_overall_limits_state` | Returns 'GREEN', 'YELLOW', or 'RED' |
| `enable_limits("TGT", "PKT", "ITEM")` | Enable limits checking |
| `disable_limits("TGT", "PKT", "ITEM")` | Disable limits checking |
| `set_limits("TGT", "PKT", "ITEM", red_lo, yel_lo, yel_hi, red_hi)` | Set custom limits at runtime |
| `get_limits_groups` | List all limits groups |
| `enable_limits_group("GROUP")` | Enable all items in group |
| `disable_limits_group("GROUP")` | Disable all items in group |
| `set_limits_set("TVAC")` | Switch active limits set (DEFAULT, TVAC, CUSTOM) |

Limits groups allow batch operations by operational mode. Multiple limits sets let you switch thresholds by mission phase.

## Serial Bridge Configuration

For connecting COSMOS to Adamant hardware over serial, use the COSMOS bridge:

```
VARIABLE baud_rate 115200
VARIABLE parity NONE
VARIABLE stop_bits 1
VARIABLE data_bits 8
VARIABLE router_port 2950

INTERFACE SERIAL_INT serial_interface.rb COM1 COM1 <%= baud_rate %> <%= parity %> <%= stop_bits %> 10.0 nil
  OPTION FLOW_CONTROL NONE
  OPTION DATA_BITS <%= data_bits %>
  Protocol Read crc_sync_protocol.rb CRC false "ERROR" -16 16
  Protocol Write cmd_sync_checksum.rb Checksum

ROUTER SERIAL_ROUTER tcpip_server_interface.rb <%= router_port %> <%= router_port %> 10.0 nil BURST
  ROUTE SERIAL_INT
  OPTION LISTEN_ADDRESS 0.0.0.0
```

Serial uses `crc_sync_protocol.rb` (strips sync word `0xFED4AFEE`) and `cmd_sync_checksum.rb` (prepends sync word). TCP uses `crc_protocol.rb` (no sync word) and `cmd_checksum.rb`.

## Docker Architecture

COSMOS runs as 8 Docker containers behind Traefik reverse proxy:

| Service | Role | Port |
|---------|------|------|
| openc3-traefik | API gateway | **2900** (HTTP), **2943** (HTTPS) |
| openc3-operator | Runs interface microservices | Internal |
| openc3-cosmos-cmd-tlm-api | Command/telemetry Rails API | Internal |
| openc3-cosmos-script-runner-api | Script execution | Internal |
| openc3-redis | Persistent config store | Internal |
| openc3-redis-ephemeral | CVT + streaming telemetry | Internal |
| openc3-minio | Object storage (logs) | Internal |
| openc3-cosmos-init | One-shot plugin installer | None |

Access COSMOS web UI at `http://localhost:2900`. The operator container needs network access to Adamant -- if Adamant runs on the host, it connects via `host.docker.internal`.
