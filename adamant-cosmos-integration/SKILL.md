---
name: adamant-cosmos-integration
description: COSMOS (OpenC3) ground system integration for Adamant assemblies -- CCSDS pipeline, plugin generation, and ground operations
---

# Adamant COSMOS (OpenC3) Integration

Connects an Adamant assembly to the COSMOS ground system via CCSDS TCP socket.

## Architecture

```
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

**Secondary Header (64 bits) — Telemetry only:**

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
| Ccsds_Packetizer | passive | Adamant packets → CCSDS (NO Sys_Time_T_Get — reads from headers) |
| Event_Packetizer | passive | Batch events into packets |
| Product_Packetizer | passive* | Fetch DPs, packetize for downlink |

*Product_Packetizer has async command connector — needs `init_base` with `Queue_Size`.

## Key Wiring Rules

- Depacketizer `Command_T_Send` → Router's `Command_T_To_Route_Recv_Async` (NOT indexed array)
- ALL `Packet_T_Send` sources must wire to `Ccsds_Packetizer`
- `Ccsds_Packetizer` has NO `Sys_Time_T_Get` — it reads timestamps from packet headers
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
    - "Addr => \"127.0.0.1\""          # "host.docker.internal" inside Docker
    - "Port => 2003"
  subtasks:
    - name: Listener
      priority: 0
      stack_size: 20000
      secondary_stack_size: 5000
```

**Port must match** `plugin.txt` `port_w`/`port_r` variables. Default: 2003.

**Socket is a TCP CLIENT** — COSMOS runs the server via `tcpip_server_interface.rb`.

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
```

Add `Assembly_Product_Packets` to assembly `with:`.

## COSMOS Plugin Generation

### Build Pipeline

```bash
# From assembly/main/ directory:
redo cosmos_config
```

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
```

## Plugin Installation

### Install Script

```bash
# From assembly/main/ directory:
./install_cosmos_plugin.sh /path/to/cosmos-project/plugins/openc3-cosmos-assembly/
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
Variable station_assembly_target_name Station_Assembly
Variable crc_parameter_name CRC
Variable checksum_parameter_name Checksum
Variable port_w 2003
Variable port_r 2003

Target Station_Assembly <%= station_assembly_target_name %>
# TCP server interface — COSMOS listens, Adamant connects as client
Interface <%= station_assembly_target_name %>_INT tcpip_server_interface.rb <%= port_w %> <%= port_r %> 10.0 nil Length 32 16 7
  Map_Target <%= station_assembly_target_name %>
  # TCP: crc_protocol.rb (no sync word). Serial: crc_sync_protocol.rb (strips sync word)
  Protocol Read crc_protocol.rb <%= crc_parameter_name %> false "ERROR" -16 16
  Protocol Write cmd_checksum.rb <%= checksum_parameter_name %>

# Optional router for forwarding to external tools
Router <%= station_assembly_target_name %>_Router tcpip_server_interface.rb 7779 7779 10.0 nil Length 32 16 7
  Map_Target <%= station_assembly_target_name %>
```

**Interface parameters:** `tcpip_server_interface.rb <write_port> <read_port> <timeout> <protocol> Length <bit_offset> <bit_size> <length_value_offset>`
- `Length 32 16 7`: Length field at bit 32, 16 bits wide, add 7 to get total packet size (6-byte header + 1)

### Protocol Files

**crc_sync_protocol.rb:** On read, strips 4-byte sync word (`FED4AFEE`), validates CRC-16 on remaining data. On write, appends CRC-16. Used for both serial and TCP (sync word only present in serial).

**cmd_checksum.rb:** On write, XOR all packet bytes with seed 0xFF, write result to Checksum field. TCP only.

**cmd_sync_checksum.rb:** Same as cmd_checksum but prepends sync word `FED4AFEE`. Serial only.

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
```

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

## Key Gotchas

1. Socket is a TCP CLIENT — COSMOS server must be running first
2. Socket address: `"127.0.0.1"` same host, `"host.docker.internal"` in Docker
3. Product_Packetizer needs `init_base` with `Queue_Size` (has async command connector)
4. Event_Packetizer `Packet_Id_Base` must avoid collision with auto-assigned product packet IDs
5. Protocol files from `adamant/gnd/cosmos/` → plugin `lib/` directory
6. Update `Command_T_Send_Count`, `Tick_T_Send_Count`, `T_Send_Count` when adding CCSDS components
7. For dev without COSMOS: use Event_Text_Logger stderr output as primary monitor
8. The Ccsds_Packetizer does NOT have a `Sys_Time_T_Get` connector — it reads time from packet headers
9. Command names in COSMOS are `Component_Instance-Command_Name` (hyphen separated)
10. Telemetry packets are identified by APID; commands are identified by `Adamant_Command_Id`

Details & full wiring examples: [references/plugin-setup-and-wiring.md](references/plugin-setup-and-wiring.md)

## Related Skills

- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
- **Framework components**: [adamant-framework-components](../adamant-framework-components/SKILL.md)
- **Style**: [adamant-style](../adamant-style/SKILL.md) -- run `redo style` on assembly dirs after adding CCSDS components
