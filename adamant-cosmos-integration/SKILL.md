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

## CCSDS Packet Structure

```
| Primary Header (6B) | Secondary Header/Timestamp (8B) | Data (var) | CRC-16 (2B) |
```
- CRC-16: CCITT polynomial, seed 0xFFFF
- APID from original Adamant Packet ID

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

- Depacketizer `Command_T_Send` → Router's `Command_T_Recv_Async` (NOT indexed array)
- ALL `Packet_T_Send` sources must wire to `Ccsds_Packetizer`
- `Ccsds_Packetizer` has NO `Sys_Time_T_Get`
- Wire `Sys_Time_T_Get` for Socket, Depacketizer, Event_Packetizer, Product_Packetizer
- Product_Packetizer `Data_Product_Fetch_T_Request` → `Product_Database.Data_Product_Fetch_T_Service`

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

## Product Packets Model

`<assembly_name>.product_packets.yaml` in assembly directory:
```yaml
packets:
  - name: Housekeeping_Packet
    id: 1
    data_products:
      - name: Instance_Name.DP_Name
        use_timestamp: True
    period: "1"                        # Every N ticks
```

Add `Assembly_Product_Packets` to assembly `with:`.

## Build & Install

```bash
# Generate COSMOS config (from assembly/main/)
redo cosmos_config
# Produces build/cosmos/plugin/ with cmd.txt and tlm.txt

# Install to plugin directory
./install_cosmos_plugin.sh /path/to/openc3-cosmos-assembly/
```

## COSMOS Plugin Structure

```
openc3-cosmos-assembly-name/
├── plugin.txt
├── *.gemspec
└── targets/ASSEMBLY_NAME/
    ├── cmd_tlm/
    │   ├── cmd.txt            # Generated
    │   └── tlm.txt            # Generated
    ├── lib/
    │   ├── crc_protocol.rb    # From adamant/gnd/cosmos/
    │   └── cmd_checksum.rb
    └── target.txt
```

## COSMOS Scripting API

```ruby
cmd("TARGET CMD with PARAM1 val1, PARAM2 val2")
value = tlm("TARGET PKT ITEM")              # Converted value
raw   = tlm_raw("TARGET PKT ITEM")          # Raw binary
```

## Key Gotchas

1. Socket is a TCP CLIENT — COSMOS server must be running first
2. Socket address: `"127.0.0.1"` same host, `"host.docker.internal"` in Docker
3. Product_Packetizer needs empty `init:` even with no init params
4. Event_Packetizer `Packet_Id_Base` must avoid collision with auto-assigned IDs
5. Protocol files from `adamant/gnd/cosmos/` → plugin `lib/` directory
6. Update `Command_T_Send_Count`, `Tick_T_Send_Count`, `T_Send_Count` when adding CCSDS components
7. For dev without COSMOS: use Event_Text_Logger stderr output as primary monitor

Details & full wiring examples: [references/plugin-setup-and-wiring.md](references/plugin-setup-and-wiring.md)

## Related Skills

- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
- **Framework components**: [adamant-framework-components](../adamant-framework-components/SKILL.md)
- **Style**: [adamant-style](../adamant-style/SKILL.md) -- run `redo style` on assembly dirs after adding CCSDS components
