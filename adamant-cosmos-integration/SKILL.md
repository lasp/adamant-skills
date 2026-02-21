---
name: adamant-cosmos-integration
description: COSMOS (OpenC3) ground system integration for Adamant assemblies -- CCSDS pipeline, plugin generation, and ground operations. Use when setting up telemetry/command ground systems, generating COSMOS plugins, or configuring TCP/serial interfaces.
---

# Adamant COSMOS (OpenC3) Integration

Connects an Adamant assembly to the COSMOS ground system via CCSDS TCP socket.

## Architecture

```yaml
Uplink:  COSMOS -> TCP -> Ccsds_Socket_Interface -> Ccsds_Command_Depacketizer -> Command_Router -> Components
Downlink: Components -> Event/Product_Packetizer -> Ccsds_Packetizer -> Socket -> COSMOS
```

## CCSDS Packet Structure (Detailed)

### Telemetry (Downlink) Packet Layout

```
| Primary Header (6B) | Secondary Header (8B) | Data (variable) | CRC-16 (2B) |
```

**Primary Header (48 bits, Big Endian):**

| Field             | Bits  | Offset | Description                           |
|-------------------|-------|--------|---------------------------------------|
| Version           | 3     | 0      | Always 0 (CCSDS version 1)           |
| Packet_Type       | 1     | 3      | 0=Telemetry, 1=Telecommand           |
| Secondary_Header  | 1     | 4      | 1=Present (always for Adamant)        |
| APID              | 11    | 5      | Application Process ID (packet ID)    |
| Sequence_Flag     | 2     | 16     | 3=Unsegmented (typical)               |
| Sequence_Count    | 14    | 18     | Incrementing counter                  |
| Packet_Length      | 16    | 32     | (data bytes + secondary header) - 1  |

**Secondary Header (64 bits) -- Telemetry only:**

| Field       | Bits | Description                       |
|-------------|------|-----------------------------------|
| Seconds     | 32   | Seconds since epoch (Sys_Time.T)  |
| Subseconds  | 32   | 1/(2^32) fractional seconds       |

**CRC-16:** CCITT polynomial, appended after data payload.

### Command (Uplink) Packet Layout

```
| Primary Header (6B) | Command Secondary Header (2B) | Adamant_Command_Id (2B) | Args (var) |
```

**Command Secondary Header (16 bits):**

| Field          | Bits | Description                      |
|----------------|------|----------------------------------|
| Reserved       | 1    | Always 0                         |
| Function_Code  | 7    | Command function code            |
| Checksum       | 8    | XOR of all packet bytes, seed 0xFF |

**Adamant_Command_Id (16 bits):** Maps to the registered command ID in the assembly's command routing table. This is used by COSMOS as the `ID_Parameter` to identify which command definition to use.

### APID and Packet ID Mapping

- **Telemetry APID** = Product packet `id` from `product_packets.yaml` (e.g., id: 1 → APID 1)
- **Command APID** = Fixed value 8 for all commands (commands are identified by `Adamant_Command_Id`, not APID)
- **Event Packetizer** uses `Packet_Id_Base` to avoid collisions with product packet IDs (e.g., `Packet_Id_Base => 98` reserves APID 98+ for event packets)
- Event packets use subpacket format: variable-length `Subpacket.Data` block instead of named fields

## Required Components

| Component | Execution | Purpose |
|-----------|-----------|---------|
| Ccsds_Socket_Interface | active | TCP client to COSMOS (NOT server) |
| Ccsds_Command_Depacketizer | passive | CCSDS → Adamant commands (validates size, XOR-8 checksum) |
| Ccsds_Packetizer | passive | Adamant packets → CCSDS (NO Sys_Time_T_Get -- reads from headers) |
| Event_Packetizer | passive | Batch events into packets |
| Product_Packetizer | passive* | Fetch DPs, packetize for downlink |

*Product_Packetizer has async command connector -- needs `init_base` with `Queue_Size`.

## Key Wiring Rules

- Depacketizer `Command_T_Send` → Router's `Command_T_To_Route_Recv_Async` (NOT indexed array)
- ALL `Packet_T_Send` sources must wire to `Ccsds_Packetizer`
- `Ccsds_Packetizer` has NO `Sys_Time_T_Get` -- it reads timestamps from packet headers
- Wire `Sys_Time_T_Get` for Socket, Depacketizer, Event_Packetizer, Product_Packetizer
- Product_Packetizer `Data_Product_Fetch_T_Request` → `Product_Database.Data_Product_Fetch_T_Service`
- Depacketizer `Command_Response_T_Send` → Router `Command_Response_T_Recv_Async`
- Depacketizer `Packet_T_Send` → `Ccsds_Packetizer` (for error/status packets)

## Complete Wiring (Uplink + Downlink)

See [references/plugin-setup-and-wiring.md](references/plugin-setup-and-wiring.md) for full YAML. Key connections:

**Uplink:** `Socket.Ccsds_Space_Packet_T_Send` → `Depacketizer.Ccsds_Space_Packet_T_Recv_Sync` → `Depacketizer.Command_T_Send` → `Router.Command_T_To_Route_Recv_Async`

**Downlink:** All `Packet_T_Send` (Event_Packetizer, Product_Packetizer, Depacketizer, Product_Database) → `Ccsds_Packetizer.Packet_T_Recv_Sync` → `Ccsds_Packetizer.Ccsds_Space_Packet_T_Send` → `Socket.Ccsds_Space_Packet_T_Recv_Async`

**Also wire:** Depacketizer `Command_Response_T_Send` → Router, Product_Packetizer `Data_Product_Fetch_T_Request` → Product_Database

## Socket Interface Config

```yaml
- type: Ccsds_Socket_Interface
  name: Ccsds_Socket_Interface_Instance
  priority: 6
  stack_size: 50000
  secondary_stack_size: 10000
  init_base:
    - "Queue_Size => 8192"
  init:
    - "Addr => \"host.docker.internal\""  # Use "127.0.0.1" if NOT in Docker
    - "Port => 2003"
  subtasks:
    - name: Listener
      priority: 0
      stack_size: 20000
      secondary_stack_size: 5000
```

**Port must match** `plugin.txt` `port_w`/`port_r` variables. Default: 2003.

**Socket is a TCP CLIENT** -- COSMOS runs the server via `tcpip_server_interface.rb`.

## Product Packets Model

`<assembly_name>.product_packets.yaml` in assembly directory:
```yaml
packets:
  - name: Housekeeping_Packet
    id: 1                              # Becomes CCSDS APID
    data_products:
      - name: Instance_Name.DP_Name
        use_timestamp: True
    period: "1"                        # Every N ticks
  - name: System_Status_Packet
    id: 2
    data_products:
      - name: Command_Router_Instance.Command_Receive_Count
    period: "5"
```ada

Add `Assembly_Product_Packets` to assembly `with:`.

## COSMOS Plugin Generation

### Build Pipeline

```bash
# From assembly/main/ directory:
redo cosmos_config
```ada

This invokes `build_cosmos_plugin.sh` which runs `redo-ifchange` on the assembly's COSMOS generators. The generators use Jinja2 templates to produce:

- `build/cosmos/plugin/<assembly>_ccsds_cosmos_commands.txt` → installed as `cmd.txt`
- `build/cosmos/plugin/<assembly>_ccsds_cosmos_telemetry.txt` → installed as `tlm.txt`

### What the Generators Do

**Telemetry generator** (`ccsds_packetizer/gen/generators/ccsds_xml.py`):
- Loads the assembly model and all packet definitions
- Iterates packets: renders CCSDS primary header fields, secondary header (Seconds/Subseconds), data product items, and CRC
- Uses `Id_Item Apid` with the packet's ID as the COSMOS packet identifier

**Command generator** (`ccsds_command_depacketizer/gen/generators/ccsds_commands.py`):
- Loads the assembly model and all command definitions
- Renders CCSDS primary header, command secondary header (Reserved, Function_Code, Checksum)
- Uses `ID_Parameter Adamant_Command_Id` as the unique command identifier
- Sets Packet_Type=1 (Telecommand), Secondary_Header=1, APID=8

### Generated Output Format

**Telemetry (tlm.txt):**
```
Telemetry Assembly_Name Packet_Name Big_Endian "description"
  Item Version 0 3 UINT "..."
  ...
  Id_Item Apid 5 11 UINT <packet_id> "..."
  ...
  Item Seconds 48 32 UINT "..."
  Item Subseconds 80 32 UINT "..."
  Append_Item Component.Field 32 UINT "..."
  Append_Item CRC 16 UINT "Packet CRC value"

# Event packets use negative offset for CRC:
  Item CRC -16 16 UINT "Packet CRC value"
```

**Commands (cmd.txt):**
```
Command Assembly_Name Component-Command_Name Big_Endian "description"
  Parameter Version 0 3 UINT 0 7 0 "..."
  ...
  Parameter Apid 5 11 UINT 0 2047 8 "..."
  ...
  Parameter Checksum 56 8 UINT 0 255 0 "..."
  ID_Parameter Adamant_Command_Id 64 16 UINT MIN MAX <cmd_id> "..."
  Append_Parameter Arg_Name 32 UINT MIN MAX 0 "..."
  # For buffer/array arguments:
  Append_Array_Parameter Buffer 8 UINT 256 "Buffer data"   # 256 bytes
```

## Plugin Installation

### Install Script

```bash
# From assembly/main/ directory:
./install_cosmos_plugin.sh /path/to/assembly.assembly.yaml /path/to/cosmos-project/plugins/openc3-cosmos-assembly/
```

This copies:
1. `build/cosmos/plugin/*_commands.txt` → `targets/ASSEMBLY_NAME/cmd_tlm/cmd.txt`
2. `build/cosmos/plugin/*_telemetry.txt` → `targets/ASSEMBLY_NAME/cmd_tlm/tlm.txt`
3. `adamant/gnd/cosmos/*.rb` → `targets/ASSEMBLY_NAME/lib/` (protocol files)
4. `main/cosmos/plugin/plugin.txt` → `plugin.txt`

### COSMOS Plugin Directory Structure

```
openc3-cosmos-assembly-name/
├── plugin.txt                         # Interface + protocol config
├── openc3-cosmos-assembly-name.gemspec
└── targets/ASSEMBLY_NAME_UPPER/
    ├── cmd_tlm/
    │   ├── cmd.txt                    # Generated by redo cosmos_config
    │   └── tlm.txt                    # Generated by redo cosmos_config
    └── lib/
        ├── crc_sync_protocol.rb       # CRC-16 validation on read, sync word strip
        ├── cmd_checksum.rb            # XOR checksum on write (TCP)
        └── cmd_sync_checksum.rb       # XOR checksum + sync word (serial)
```

### plugin.txt Configuration

```ruby
Variable assembly_target_name My_Assembly
Variable crc_parameter_name CRC
Variable checksum_parameter_name Checksum
Variable port_w 2003
Variable port_r 2003

Target My_Assembly <%= assembly_target_name %>
# TCP server interface -- COSMOS listens, Adamant connects as client
Interface <%= assembly_target_name %>_INT tcpip_server_interface.rb <%= port_w %> <%= port_r %> 10.0 nil Length 32 16 7
  Map_Target <%= assembly_target_name %>
  # TCP: crc_protocol.rb (no sync word). Serial: crc_sync_protocol.rb (strips sync word)
  Protocol Read crc_protocol.rb <%= crc_parameter_name %> false "ERROR" -16 16
  Protocol Write cmd_checksum.rb <%= checksum_parameter_name %>

# Optional router for forwarding to external tools
Router <%= assembly_target_name %>_Router tcpip_server_interface.rb 7779 7779 10.0 nil Length 32 16 7
  Map_Target <%= assembly_target_name %>
```ada

**Interface parameters:** `tcpip_server_interface.rb <write_port> <read_port> <timeout> <protocol> Length <bit_offset> <bit_size> <length_value_offset>`
- `Length 32 16 7`: Length field at bit 32 (CCSDS Packet_Length), 16 bits wide, add 7 to get total packet size
  - The `7` comes from CCSDS convention: `Packet_Length = (data_bytes + secondary_header) - 1`, so total = Packet_Length + 7 (6-byte primary header + 1 for the minus-one encoding)

### Protocol Files

**crc_protocol.rb:** COSMOS built-in protocol (NOT copied to plugin `lib/`). On read, validates CRC-16 on packet data. On write, computes and appends CRC-16. Used for TCP connections. Parameters: `crc_parameter_name false "ERROR" -16 16` (CRC at last 16 bits).

**crc_sync_protocol.rb:** Adamant-provided (copied to plugin `lib/`). On read, strips 4-byte sync word (`FED4AFEE`), then validates CRC-16. Used for serial connections where sync words frame packets.

**cmd_checksum.rb:** Adamant-provided (copied to plugin `lib/`). On write, XOR all packet bytes with seed 0xFF, write result to Checksum field. TCP only.

**cmd_sync_checksum.rb:** Adamant-provided (copied to plugin `lib/`). Same as cmd_checksum but prepends sync word `FED4AFEE`. Serial only.

### Gemspec Template

```ruby
# openc3-cosmos-<assembly_name>.gemspec
Gem::Specification.new do |s|
  s.name = "openc3-cosmos-<assembly_name>"
  s.summary = "COSMOS plugin for <Assembly_Name>"
  s.version = "0.0.1"
  s.authors = ["Your Name"]
  s.files = Dir["{targets,lib,procedures,plugin.txt}/**/*"]
end
```

### Building and Loading the Plugin Gem

```bash
# From cosmos-project directory:
cd plugins/openc3-cosmos-assembly-name/

# Build gem (inside COSMOS Docker):
docker compose -f ../../compose.yaml run --rm \
  -v "$(pwd):/openc3/local:z" -w /openc3/local \
  --no-deps openc3-cosmos-cmd-tlm-api gem build *.gemspec

# Load into running COSMOS:
../../openc3.sh cli load openc3-cosmos-assembly-name-0.0.1.gem
```ada

Or use the project's helper scripts:
```bash
# From project gnd/cosmos/ directory:
./build_cosmos_plugin.sh    # Builds the gem
./install_cosmos_plugin.sh  # Loads into COSMOS
```

## COSMOS Scripting API

```ruby
cmd("TARGET CMD with PARAM1 val1, PARAM2 val2")
value = tlm("TARGET PKT ITEM")              # Converted value
raw   = tlm_raw("TARGET PKT ITEM")          # Raw binary
```

## openc3.sh CLI Reference

### System Management
```bash
openc3.sh start                          # Start COSMOS (all containers)
openc3.sh stop                           # Stop COSMOS
openc3.sh cleanup                        # Stop + remove volumes
openc3.sh run                            # Start in foreground (Ctrl+C to stop)
```

### Plugin Management
```bash
openc3.sh cli load <gem_file>            # Install/update plugin (auto-detects upgrade)
openc3.sh cli load <gem> --variables v.json  # Install with variables file
openc3.sh cli list [SCOPE]               # List installed plugins (default scope: DEFAULT)
openc3.sh cli unload <plugin_name> [SCOPE]   # Remove a plugin by name
openc3.sh cli validate <gem_file>        # Validate plugin before loading
openc3.sh cli generate plugin <name>     # Generate new empty plugin skeleton
openc3.sh cli pkginstall <gem_file>      # Install Ruby/Python package dependency
openc3.sh cli pkguninstall <pkg_name>    # Remove package
```

`cli load` auto-detects existing plugins: same version = skip, different version = upgrade. Pass `force` as last arg to force reinstall. `cli unload` takes the plugin name from `cli list` output.

### Scripting and Testing
```bash
openc3.sh cli script list                # List available scripts
openc3.sh cli script run <script>        # Execute a script (blocking, prints output)
openc3.sh cli script spawn <script>      # Execute a script (background, returns ID)
openc3.sh cli script running [LIMIT]     # Show currently running scripts
openc3.sh cli script status <id>         # Check script execution status
openc3.sh cli script stop <id>           # Stop a running script
```

Scripts use the COSMOS Scripting API (`cmd()`, `tlm()`, etc.) and live in `procedures/` within a plugin target. `script run` supports `--disconnect` mode, `--wait N` timeout, and `ENV=VALUE` args.

**Using Adamant Python in COSMOS scripts:** Use `pydep` to build Adamant's generated Python dependencies (packed record types, CRC16, packing/unpacking utilities) into a version-controlled plugin configuration. Include the output in the plugin's `procedures/` path and copy built packages to the plugin `lib/` path. This lets test scripts use real Adamant records and tools instead of raw byte manipulation.

### Interactive and Debug
```bash
openc3.sh cli irb                        # Interactive Ruby console with COSMOS API
openc3.sh cli rake <task>                # Run Rake tasks (needs Rakefile in cwd)
openc3.sh cli bridge [config]            # Start protocol bridge (default: bridge.txt)
openc3.sh cli bridgesetup [filename]     # Generate default bridge config file
openc3.sh cli bridgegem <gem> [VAR=val]  # Run bridge from a gem's bridge.txt
openc3.sh cli xtce_converter             # Convert to/from XTCE format (--help for options)
openc3.sh cli cstol_converter            # Convert CSTOL to COSMOS scripts
openc3.sh cli redis keys                 # List all Redis keys (debug)
openc3.sh cli redis hget <hash> <key>    # Read Redis hash value (debug)
```

### Data Export
Telemetry data export is done through the COSMOS web UI (Data Extractor tool) or by writing scripts that use `tlm()` / `tlm_raw()` to query and log values programmatically.

## Assembly Organization

CCSDS components are typically placed in a **safe mode** or base assembly configuration (not nominal operations). This ensures ground communication is always available regardless of operational mode. Example from bot station: all CCSDS components live in `station_safe_mode.assembly.yaml`.

## Common Integration Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Socket connection refused | COSMOS not running or wrong port | Start COSMOS first; verify `port_w`/`port_r` match assembly `Port` init |
| CRC mismatch on telemetry | Wrong CRC protocol or bit offset | Ensure `Protocol Read crc_sync_protocol.rb ... -16 16` (CRC at end, 16-bit) |
| Commands not recognized | APID mismatch or wrong command ID | Commands use APID=8; identification is via `Adamant_Command_Id` field |
| No telemetry packets | Packets not wired to Ccsds_Packetizer | Every `Packet_T_Send` must connect to `Ccsds_Packetizer.Packet_T_Recv_Sync` |
| Event packet ID collision | `Packet_Id_Base` overlaps product IDs | Set `Packet_Id_Base` above max product packet ID (e.g., 98) |
| Docker connectivity | Adamant in Docker can't reach host COSMOS | Use `Addr => "host.docker.internal"` instead of `"127.0.0.1"` |
| Checksum validation fails | Checksum parameter name mismatch | `Variable checksum_parameter_name` must match the cmd.txt field name (`Checksum`) |
| Missing protocol files | `.rb` files not copied to plugin `lib/` | Run `install_cosmos_plugin.sh` which copies from `adamant/gnd/cosmos/` |
| Packet length wrong | `Length 32 16 7` offset incorrect | The `7` = 6-byte primary header + 1 (CCSDS length field semantics) |
| Product packets empty | Product_Packetizer not connected to DB | Wire `Data_Product_Fetch_T_Request` → `Product_Database.Data_Product_Fetch_T_Service` |

## Operational Behavior

### Socket Connection Lifecycle
- Socket **auto-reconnects**: On each send/receive attempt, if `not Is_Connected`, calls `Connect` again. No crash on disconnect.
- Events emitted: `Socket_Connected` on successful connect, `Socket_Not_Connected` on failure or disconnect.
- If COSMOS is not running at assembly startup, the socket logs `Socket_Not_Connected` and retries on next data send.
- **No data is lost silently** -- send failures when disconnected are visible through dropped packet events.

### Packet Size Limits
- CCSDS `Packet_Length` field is 16-bit (`Unsigned_16`), theoretical max ~65KB per packet.
- Practical limit set by `ccsds_packet_buffer_size` in project `configuration.yaml` (typically 512-1274 bytes).
- Socket `Queue_Size` (init_base) limits total buffered data, not individual packet size.

### Incremental Plugin Updates
- `redo cosmos_config` **regenerates everything** from assembly model. There is no incremental update.
- For quick prototyping, you CAN manually edit cmd.txt/tlm.txt, but changes will be overwritten on next `redo cosmos_config`.
- After manual edits, rebuild the gem and reload: `openc3.sh cli load <gem>`.

### Event Subpacket Format
- Event_Packetizer batches multiple events into a single CCSDS packet as variable-length subpackets.
- Each subpacket contains: event header (ID, timestamp) + serialized event data.
- COSMOS parses these using the generated tlm.txt `Subpacket.Data` block definition.
- `Num_Internal_Packets` init param controls max events per batch; `Partial_Packet_Timeout` forces send of partial batches.

## Rate Group Assignments

CCSDS components in rate groups:
- **Event_Packetizer**: Must be ticked -- sends batched events on tick. Place in a **slower rate group** (e.g., Slow_Rate_Group at 1 Hz or less) to batch events efficiently.
- **Product_Packetizer**: Must be ticked -- fetches data products and sends packets per `period` in product_packets.yaml. Place in a **slower rate group** for desired telemetry rates.
- **Auto-generated packet types**: The assembly generates `Error_Packet` and `Dump_Packet` telemetry types in addition to the packets defined in `product_packets.yaml`. These carry CCSDS error frames and database dump data respectively.
- **Ccsds_Socket_Interface**: Active component (has its own task + Listener subtask). Does NOT go in a rate group.
- **Ccsds_Command_Depacketizer**: Passive, driven by socket data arrival. Does NOT need ticking.
- **Ccsds_Packetizer**: Passive, driven by incoming Packet_T_Recv_Sync. Does NOT need ticking.

## Key Gotchas

1. Socket is a TCP CLIENT -- COSMOS server must be running first (but assembly won't crash if it's not -- it retries)
2. Socket address: `"127.0.0.1"` same host, `"host.docker.internal"` in Docker
3. Product_Packetizer needs `init_base` with `Queue_Size` (has async command connector)
4. Event_Packetizer `Packet_Id_Base` must avoid collision with auto-assigned product packet IDs
5. Protocol files from `adamant/gnd/cosmos/` → plugin `lib/` directory
6. Update `Command_T_Send_Count`, `Tick_T_Send_Count`, `T_Send_Count` when adding CCSDS components
7. For dev without COSMOS: use Event_Text_Logger stderr output as primary monitor
8. The Ccsds_Packetizer does NOT have a `Sys_Time_T_Get` connector -- it reads time from packet headers
9. Command names in COSMOS are `Component_Instance-Command_Name` (hyphen separated)
10. Telemetry packets are identified by APID; commands are identified by `Adamant_Command_Id`

Details & full wiring examples: [references/plugin-setup-and-wiring.md](references/plugin-setup-and-wiring.md)
Full scripting API, interface management, limits, bridge config, Docker architecture: [references/scripting-api-reference.md](references/scripting-api-reference.md)

## Related Skills

- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
- **Framework components**: [adamant-framework-components](../adamant-framework-components/SKILL.md)
- **Style**: [adamant-style](../adamant-style/SKILL.md) -- run `redo style` on assembly dirs after adding CCSDS components
