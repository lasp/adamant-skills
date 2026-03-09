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
- Wire `Sys_Time_T_Get` for Socket, Depacketizer, Event_Packetizer, Product_Packetizer, Product_Database, **Command_Router** (crashes without it!)
- **Command_Router self-loops (REQUIRED):**
  - `Command_T_Send[N]` → `Command_T_Recv_Async` (self) — registers its own Noop commands
  - `Command_Response_T_Send` → `Command_Response_T_Recv_Async` (self) — handles own responses
  - `Command_T_Send_Count` must include self + Depacketizer (if it has commands)
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
  s.description = "OpenC3 COSMOS plugin for <Assembly_Name> Adamant assembly"  # REQUIRED -- missing description causes silent load failure
  s.version = "0.0.1"
  s.authors = ["Your Name"]
  s.license = "MIT"
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

### Gem Building
```bash
# Simplest method -- run rake inside COSMOS container via CLI:
cd /path/to/plugin/dir
openc3.sh cli rake build VERSION=1.0.0   # Builds gem in pkg/ subdir
# Then load:
openc3.sh cli load pkg/openc3-cosmos-assembly-1.0.0.gem
```

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

## End-to-End Workflow

### First-Time Setup (Bot Station Reference)

1. **Build COSMOS config from assembly:**
   ```bash
   # In Adamant container, from assembly/main/ dir:
   redo cosmos_config
   ```

2. **Install plugin files:**
   ```bash
   ./install_cosmos_plugin.sh /path/to/assembly.yaml /path/to/cosmos-project/plugins/openc3-cosmos-assembly/
   ```

3. **Collect Python dependencies (pydep):**
   Copy Adamant-generated Python packages (packed record types, CRC16, pack/unpack utilities) into the plugin's `targets/ASSEMBLY_NAME/lib/` directory. These are needed for any COSMOS test scripts that use Adamant records.

4. **Check .env / demo configuration:**
   - COSMOS ships with a demo plugin enabled by default
   - Check `cosmos-project/.env` for `OPENC3_DEMO` or similar flags
   - Disable demo targets if they conflict with your assembly's plugin
   - Verify `OPENC3_API_PASSWORD` is set (default: `openc3service`)

5. **Build and load plugin gem:**
   ```bash
   cd cosmos-project/plugins/openc3-cosmos-assembly/
   rake build          # or gem build *.gemspec inside COSMOS container
   ../../openc3.sh cli load openc3-cosmos-assembly-0.0.1.gem
   ```

6. **Start assembly (in container with exposed port):**
   ```bash
   # From project dir, expose TCP port for COSMOS:
   docker exec -it <container> bash -c "cd /path/to/assembly && ./build/bin/Linux/main.elf"
   ```
   Or configure Docker compose to expose port 2003 from the Adamant container.

7. **Start COSMOS:**
   ```bash
   cd cosmos-project && ./openc3.sh start
   ```
   COSMOS TCP server listens on the configured port. The assembly's socket interface connects as a client.

8. **Verify connectivity:**
   - COSMOS web UI: check for incoming telemetry packets
   - CLI: `./openc3.sh cli irb` then `tlm("Assembly Housekeeping_Packet")` to check live values
   - Send noop: `./openc3.sh cli cmd "Assembly Command_Router_Instance-Noop"`

### Iterating on Plugin Changes

After modifying assembly components (adding commands, events, data products):
1. `redo cosmos_config` (regenerates cmd.txt/tlm.txt)
2. Re-run install script to copy updated files
3. Rebuild gem: `rake build`
4. Reload: `openc3.sh cli load <gem>` (auto-upgrades if version matches)
5. No COSMOS restart needed -- plugin hot-reload works

### Docker Networking Notes

- **Assembly in Docker, COSMOS on host:** Assembly uses `Addr => "host.docker.internal"`, COSMOS listens on `127.0.0.1:2003`
- **Both in Docker:** Use Docker network or `host.docker.internal`. May need `--network host` or shared Docker network.
- **Assembly on host, COSMOS in Docker:** Assembly uses `Addr => "127.0.0.1"`, expose COSMOS port to host.
- **Recommended for development:** Assembly in Adamant container with port exposed, COSMOS in its own container stack. Both use host networking or a shared bridge network.

## Live Testing with COSMOS

### COSMOS Port Exposure

COSMOS runs in Docker. The `tcpip_server_interface` listens inside the operator container.
To reach it from the Adamant container (or host), expose the port in `compose.yaml`:

```yaml
openc3-operator:
  ports:
    - "127.0.0.1:2003:2003"  # Adamant CCSDS socket interface
```

Restart COSMOS after adding port mapping. Verify with `ss -tlnp | grep 2003` on host.

### Plugin Gem Build and Load (Non-Interactive)

```bash
# Build gem (from cosmos-project dir, mount plugin dir):
cd /path/to/cosmos-project
docker compose -f compose.yaml run -T --rm \
  -v "$(pwd):/openc3/local:z" \
  -v "/path/to/plugin:/plugin:z" \
  -w /plugin \
  -e OPENC3_API_PASSWORD=openc3service \
  --no-deps openc3-cosmos-cmd-tlm-api \
  gem build *.gemspec

# Load into COSMOS:
docker compose -f compose.yaml run -T --rm \
  -v "$(pwd):/openc3/local:z" \
  -v "/path/to/plugin:/plugin:z" \
  -w /plugin \
  -e OPENC3_API_PASSWORD=openc3service \
  --no-deps openc3-cosmos-cmd-tlm-api \
  ruby /openc3/bin/openc3cli load *.gem
```

If volume mount causes permissions issues with `/gems/cosmoscache/`, use `docker cp` instead:
```bash
# Copy gem into running API container, load from inside:
docker cp plugin.gem cosmos-project-openc3-cosmos-cmd-tlm-api-1:/tmp/
docker exec cosmos-project-openc3-cosmos-cmd-tlm-api-1 ruby /openc3/bin/openc3cli load /tmp/plugin.gem
```

### Plugin Management

```bash
# List installed plugins:
openc3cli list

# Unload a plugin (use exact name from list output):
openc3cli unload openc3-cosmos-station-assembly-0.0.1.gem__0

# Only one plugin can bind to a given port. Unload existing plugins before loading new ones on the same port.
```

### Assembly Launch for Live Testing

```bash
# Launch assembly ELF in background with timeout (capture BOTH stdout and stderr):
adamant_env.sh exec "cd /home/user/project && nohup timeout 300 path/to/main.elf > /tmp/assembly.log 2>&1 &"

# Wait for connection, then check log:
sleep 15
adamant_env.sh exec "cat /tmp/assembly.log"
# Look for Socket_Connected event (NOT Socket_Not_Connected)
# Look for "Init_Base...", "Running..." lines confirming startup sequence

# Kill when done:
adamant_env.sh exec "pkill -f main.elf || true"
```

**IMPORTANT:** Always do a clean rebuild before live testing to avoid stale .o file issues:
```bash
adamant_env.sh exec "cd /home/user/project/src/assembly/<name>/main && redo clean && redo build/bin/Linux/main.elf"
```

**Main procedure pattern** (reference: adamant_example linux assembly):
```ada
with Ada.Real_Time; use Ada.Real_Time;
with Ada.Text_IO; use Ada.Text_IO;
with Assembly_Name;
procedure Main is
begin
   Put_Line ("Init_Base...");
   Assembly_Name.Init_Base;
   Put_Line ("Set_Id_Bases...");
   Assembly_Name.Set_Id_Bases;
   Put_Line ("Connect_Components...");
   Assembly_Name.Connect_Components;
   Put_Line ("Init_Components...");
   Assembly_Name.Init_Components;
   delay until Clock + Milliseconds (1000);
   Put_Line ("Start_Components...");
   Assembly_Name.Start_Components;
   Put_Line ("Set_Up_Components...");
   Assembly_Name.Set_Up_Components;
   Put_Line ("Running...");
   loop
      delay until Clock + Milliseconds (1000);
   end loop;
end Main;
```

### Command Uplink Debugging

If commands are not reaching the assembly (COSMOS txcnt increments but assembly command counters stay at 0):

1. **Check assembly stderr** for `Invalid_Packet_Checksum` or `Packet_Recv_Failed` events from the depacketizer
2. **Verify the Listener subtask** is configured with `disabled: False` (or simply not set, which defaults to enabled)
3. **Check the cmd.txt** command definitions match the assembly's registered command IDs
4. **Verify APID=8** for all commands in cmd.txt (commands identified by `Adamant_Command_Id`, not APID)
5. **Check plugin.txt** has `Protocol Write cmd_checksum.rb` (XOR-8 checksum required by depacketizer)
6. **Ensure clean build** -- stale framework .o files can cause silent failures

### Test Script Execution

```bash
# Run a COSMOS test script via CLI:
cd /path/to/cosmos-project
docker compose -f compose.yaml run -T --rm \
  -v "$(pwd):/openc3/local:z" \
  -e OPENC3_API_PASSWORD=openc3service \
  --no-deps openc3-cosmos-cmd-tlm-api \
  ruby /openc3/bin/openc3cli script run TARGET/procedures/test_script.py
```

Scripts live in `targets/TARGET_NAME/procedures/` within the plugin.
Use `from openc3.script import *` for the scripting API.

### Test Script Format (Suite/Group pattern for Script Runner)

**Use the Suite/Group class pattern.** Script Runner executes suites via the
`suiteRunner` API field, which calls `SuiteRunner.start(Suite, Group)` internally.
Each `test_*` method in a Group runs independently with proper error isolation.

```python
from openc3.script import *
from openc3.script.suite import Suite, Group

TARGET = "ASSEMBLY_NAME"

class AssemblyTests(Group):
    def setup(self):
        """Runs before all tests in this group. Use for warmup."""
        print("Waiting 10s for telemetry warmup...")
        wait(10)

    def test_packets_flowing(self):
        """Verify telemetry packets are being received."""
        seq1 = tlm(f"{TARGET} Housekeeping_Packet Sequence_Count") or 0
        wait(3)
        seq2 = tlm(f"{TARGET} Housekeeping_Packet Sequence_Count") or 0
        if seq2 <= seq1:
            raise RuntimeError(f"Packet not flowing: {seq1} -> {seq2}")
        print(f"Packet flowing: {seq1} -> {seq2}")

    def test_noop_command(self):
        """Send Noop and verify it was accepted."""
        cmd(f"{TARGET} Command_Router_Instance-Noop")
        print("Noop sent successfully")

    def test_disable_enable_packet(self):
        """Disable a packet, verify it stops, re-enable, verify it resumes."""
        cmd(f"{TARGET} Product_Packetizer_Instance-Disable_Packet with ID 1")
        wait(3)
        seq1 = tlm(f"{TARGET} Housekeeping_Packet Sequence_Count") or 0
        wait(3)
        seq2 = tlm(f"{TARGET} Housekeeping_Packet Sequence_Count") or 0
        if seq2 != seq1:
            print(f"WARNING: packet still flowing while disabled: {seq1} -> {seq2}")
        cmd(f"{TARGET} Product_Packetizer_Instance-Enable_Packet with ID 1")
        wait(3)
        seq3 = tlm(f"{TARGET} Housekeeping_Packet Sequence_Count") or 0
        wait(3)
        seq4 = tlm(f"{TARGET} Housekeeping_Packet Sequence_Count") or 0
        if seq4 <= seq3:
            raise RuntimeError(f"Packet not flowing after re-enable: {seq3} -> {seq4}")
        print(f"Disable/enable OK")

class AssemblySuite(Suite):
    def __init__(self):
        super().__init__()
        self.add_group(AssemblyTests)
```

**Imports:** `from openc3.script.suite import Suite, Group` (NOT `from openc3.tools.test_runner.test`).

**Running via Script Runner API:**

```bash
# Upload the test script:
curl -s -X POST -H "Authorization: openc3service" -H "Content-Type: application/json" \
  "http://localhost:2900/script-api/scripts/TARGET/procedures/test_suite.py?scope=DEFAULT" \
  -d '{"text": "<escaped script content>"}'

# Run the suite (suiteRunner triggers Suite/Group execution):
RUN_ID=$(curl -s -X POST -H "Authorization: openc3service" \
  "http://localhost:2900/script-api/scripts/TARGET/procedures/test_suite.py/run?scope=DEFAULT" \
  -H "Content-Type: application/json" \
  -d '{"suiteRunner":{"method":"start","suite":"AssemblySuite","group":"AssemblyTests","options":[]}}')

# Poll for completion:
curl -s -H "Authorization: openc3service" \
  "http://localhost:2900/script-api/running-script/${RUN_ID}?scope=DEFAULT"
# state: "running" | "waiting" | "completed" | "error" | "completed_errors"
```

**The upload response confirms suite discovery:**
```json
{"suites": "{\"AssemblySuite\": {\"groups\": {\"AssemblyTests\": {\"scripts\": [\"test_disable_enable_packet\", \"test_noop_command\", \"test_packets_flowing\"]}}}}", "success": true}
```

**Key patterns:**
- `tlm()` returns `None` if the packet hasn't been received yet -- always default to 0 with `or 0`
- Add a warmup `wait(10)` in `Group.setup()` before tests run
- Test methods MUST start with `test_` (or `script_` or `op_`) to be discovered
- Each test method runs independently -- exceptions in one test don't skip others
- `raise RuntimeError(...)` to fail a test; returning normally = pass
- Suite class name and Group class name are passed in the `suiteRunner` API call
- The `suiteRunner.options` field accepts `["Loop"]`, `["Break Loop On Error"]`, `["Abort After Error"]`

### Script Runner REST API

**Authentication:** `Authorization: openc3service` header (NOT "password").
All endpoints require `?scope=DEFAULT` query parameter.

**Upload a test script to COSMOS (required before execution):**
```bash
# Scripts live in COSMOS's MinIO storage, NOT the local plugin directory.
# You MUST upload via API for Script Runner to see your script.
curl -s -X POST -H "Authorization: openc3service" -H "Content-Type: application/json" \
  "http://localhost:2900/script-api/scripts/TARGET/procedures/test_suite.py?scope=DEFAULT" \
  -d '{"text": "<escaped script content>"}'
```

**Run a script:**
```bash
RUN_ID=$(curl -s -X POST -H "Authorization: openc3service" \
  "http://localhost:2900/script-api/scripts/TARGET/procedures/test_suite.py/run?scope=DEFAULT" \
  -H "Content-Type: application/json" -d '{}')
```

**Poll for completion:**
```bash
curl -s -H "Authorization: openc3service" \
  "http://localhost:2900/script-api/running-script/${RUN_ID}?scope=DEFAULT"
# state: "running" | "waiting" | "completed" | "error" | "completed_errors"
```

**Retrieve logs from MinIO:**
```bash
docker exec <minio-container> find /data/logs -name "*test_suite*"
docker exec <minio-container> cat /data/logs/DEFAULT/tool_logs/sr/<date>/<timestamp>_sr_test_suite.txt
```

### Test Script Patterns (Reference)

```python
from openc3.script import *

# Send command (hyphen between instance name and command name):
cmd("Target Component_Instance-Command_Name")
cmd("Target Component_Instance-Command_Name with Param1 value1, Param2 value2")

# Check telemetry (use wait_check with generous timeouts for live systems):
wait_check("Target Packet_Name Item_Name.Value == expected", 30)
check("Target Packet_Name Item_Name.Value == expected")
value = tlm("Target Packet_Name Item_Name.Value")

# Get raw buffer for parameter table comparison:
buffer = get_tlm_buffer("Target Packet_Name")

# Wait between operations:
wait(seconds)
```

**IMPORTANT:** Read the generated cmd.txt and tlm.txt to get exact command names,
packet names, and item names. Names are derived from the assembly YAML component
instance names and their YAML model definitions. **NEVER guess or assume packet
names** -- product_packets.yaml `name:` field determines the COSMOS packet name
(converted to UPPER_SNAKE_CASE). If the YAML says `name: Safe_Mode_Thermal_Packet`,
COSMOS uses `SAFE_MODE_THERMAL_PACKET`. Test scripts MUST use the exact names
from the loaded plugin's tlm.txt, not shortened or assumed variants.

**This applies to telemetry ITEM names too** -- every `PACKET ITEM.NAME` referenced
in a test script must appear verbatim in tlm.txt. Do not infer item names from
component YAML, data_products.yaml, or implementation files. If an item is not
in tlm.txt, it does not exist in COSMOS and referencing it will cause a runtime error.

**COSMOS target name vs assembly name:**
- The COSMOS **target** is set by plugin.txt `Target` directive (e.g., `CERES_THERMAL`)
- The cmd.txt/tlm.txt use the **assembly name** (e.g., `Ceres_Thermal_Assembly`) after the target
- In COSMOS API calls, use the **target name** (the short one from plugin.txt), NOT the assembly name
- Example: `cmd("CERES_THERMAL Command_Router_Instance-Noop")` -- NOT `cmd("CERES_THERMAL_ASSEMBLY ...")`
- Example: `tlm("CERES_THERMAL Safe_Thermal_Housekeeping Sequence_Count")`
- The target name is what appears in `plugin.txt` after the `Target` keyword
- To find it: `grep "^Target" plugin.txt` or check the COSMOS web UI

**COSMOS naming rules:**
- Enum state names are normalized to UPPERCASE (e.g., `Safe` becomes `SAFE` in telemetry)
- Command arg parameter names include the type prefix (e.g., `T17_Instrument_Mode.Value` not just `Value`)
- Enum types used in commands/events/data products need a separate `.record.yaml` packed wrapper

**Test verification patterns:**
- Use POSITIVE verification (check expected telemetry effects) instead of checking Error_Packet.Sequence_Count
- Error_Packet may increment for reasons unrelated to command failures (assembly startup errors, timing)
- To verify commands work: send the command, then check that the expected telemetry value changed
- For NOOP: verify Events_Packet.Sequence_Count increments (NOOP always produces an event)
- For parameter updates: send Update_Parameter + Dump_Parameters, verify value in Active_Parameters packet
- For packetizer control: verify packet still flows (RECEIVED_COUNT increments over time)
- Do NOT rely on "no error occurred" assertions -- always verify the positive expected effect
- **NEVER use CCSDS Sequence_Count for liveness checks.** Multiple packet sources (Rate_Group timing + Product_Packetizer) can share the same APID with independent sequence counters. A `check(seq >= old)` between two API calls will race: a packet from the OTHER source can arrive between `tlm()` and `check()`, giving a lower counter. Use `RECEIVED_COUNT` (COSMOS-maintained, monotonically increasing) instead of `Sequence_Count` for all "packet still flowing" assertions.
- **Prefer `wait_check()` over bare `check()` for any telemetry assertion.** `check()` reads the COSMOS cache at one instant -- if a packet arrives between your `tlm()` baseline read and the `check()` call, you get stale or interleaved data. `wait_check("...", 5)` retries for up to N seconds, tolerating transient cache updates.

**Ground-testable component design:**
- For components that will be verified via COSMOS scripts, make state changes COMMAND-DRIVEN ONLY
- Do NOT auto-increment counters or auto-trigger faults on tick -- this creates race conditions with test scripts
- Tick handlers should only send data products / update telemetry, not change fault/mode/alarm state
- Use `wait_check()` (not raw `tlm()`) in test scripts -- it polls until condition met or timeout
- Keep test scripts simple: cmd() + wait_check() + print(). No complex logic.
- **Avoid long wait_check timeouts on on-demand packets** (like Active_Parameters).
  These only update when explicitly commanded (e.g., DUMP_PARAMETERS). Use a
  polling loop: send dump command, wait(3), read tlm(), check value, retry if stale.
- **Test script size**: aim for 50-200 lines. Larger scripts are fragile and hard
  to debug. Test one concern per function. Print PASS/FAIL per step.
- **No state machine logic in tests**: if a test requires complex setup sequences,
  break into smaller independent tests that each set up their own preconditions.
- **Do NOT restart the assembly ELF during test execution.** If Phase C launched
  the ELF and it is still running, use it as-is. Restarting can cause rate group
  queue overflow and partial telemetry loss (some subsystems stall). If the ELF
  died, re-launch from the CORRECT path: `src/assembly/<name>/main/build/bin/Linux/<name>_main.elf`
  (built by Phase B), NOT `main/build/bin/Linux/main.elf` or any other variant.

## COSMOS JSON-RPC API (Direct Telemetry Queries)

For verifying telemetry without writing a test script (e.g., Phase C plugin verification):

```bash
# Query a telemetry value:
curl -s -H "Authorization: openc3service" -H "Content-Type: application/json" \
  -X POST "http://localhost:2900/openc3-api/api" \
  -d '{"jsonrpc":"2.0","method":"tlm","params":["TARGET PACKET ITEM"],"id":1,"keyword_params":{"scope":"DEFAULT"}}'
# Returns: {"jsonrpc":"2.0","id":1,"result":12345}

# List all telemetry packets for a target:
curl -s -H "Authorization: openc3service" -H "Content-Type: application/json" \
  -X POST "http://localhost:2900/openc3-api/api" \
  -d '{"jsonrpc":"2.0","method":"get_all_telemetry","params":["TARGET"],"id":1,"keyword_params":{"scope":"DEFAULT"}}'

# Send a command:
curl -s -H "Authorization: openc3service" -H "Content-Type: application/json" \
  -X POST "http://localhost:2900/openc3-api/api" \
  -d '{"jsonrpc":"2.0","method":"cmd","params":["TARGET Component-Command"],"id":1,"keyword_params":{"scope":"DEFAULT"}}'

# List installed plugins:
curl -s -H "Authorization: openc3service" \
  "http://localhost:2900/openc3-api/plugins?scope=DEFAULT"

# List interfaces:
curl -s -H "Authorization: openc3service" \
  "http://localhost:2900/openc3-api/interfaces?scope=DEFAULT"
```

Use `RECEIVED_COUNT` (not `Sequence_Count`) to verify packets are flowing:
```bash
curl -s -H "Authorization: openc3service" -H "Content-Type: application/json" \
  -X POST "http://localhost:2900/openc3-api/api" \
  -d '{"jsonrpc":"2.0","method":"tlm","params":["TARGET PACKET RECEIVED_COUNT"],"id":1,"keyword_params":{"scope":"DEFAULT"}}'
```

## Known Limitations

1. **Subassembly incompatibility**: COSMOS generators (`redo build/cosmos/...`) expect flat assemblies with a top-level `components:` key. Assemblies using `subassemblies:` will fail with "Cannot find required key 'components'". Workaround: create a flattened assembly YAML for COSMOS generation, or generate per-subassembly.
2. **Cross-subassembly product_packets**: If `product_packets.yaml` references components from multiple subassemblies, generation fails when run against a single subassembly. Each subassembly needs its own product_packets referencing only its own components.
3. **No assembly flattening target**: There is no `redo flatten` or equivalent to merge subassemblies into a single flat file for generation purposes.

## Related Skills

- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
- **Framework components**: [adamant-framework-components](../adamant-framework-components/SKILL.md)
- **Style**: [adamant-style](../adamant-style/SKILL.md) -- run `redo style` on assembly dirs after adding CCSDS components
