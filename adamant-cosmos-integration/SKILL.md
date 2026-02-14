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

## Required Components

| Component | Execution | Purpose |
|-----------|-----------|---------|
| Ccsds_Socket_Interface | active | TCP socket to COSMOS |
| Ccsds_Command_Depacketizer | passive | CCSDS → Adamant commands |
| Ccsds_Packetizer | passive | Adamant packets → CCSDS |
| Event_Packetizer | passive | Batch events into packets |
| Product_Packetizer | passive* | Fetch DPs, packetize for downlink |

*Product_Packetizer has async command connector — needs `init_base` with `Queue_Size`.

Details & full wiring: [references/plugin-setup-and-wiring.md](references/plugin-setup-and-wiring.md)

## Key Wiring Rules

- Depacketizer `Command_T_Send` → Router's `Command_T_Recv_Async` (NOT indexed array)
- ALL `Packet_T_Send` sources must wire to `Ccsds_Packetizer`
- `Ccsds_Packetizer` has NO `Sys_Time_T_Get` (reads time from headers)
- Wire `Sys_Time_T_Get` for Socket, Depacketizer, Event_Packetizer, Product_Packetizer
- Product_Packetizer `Data_Product_Fetch_T_Request` → `Product_Database.Data_Product_Fetch_T_Service`

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

## Key Gotchas

1. Socket address: `"127.0.0.1"` same host, `"host.docker.internal"` in Docker
2. Product_Packetizer needs empty `init:` even with no init params
3. Event_Packetizer `Packet_Id_Base` must avoid collision with auto-assigned IDs
4. Protocol files from `adamant/gnd/cosmos/` → plugin `lib/` directory
5. Update `Command_T_Send_Count`, `Tick_T_Send_Count`, `T_Send_Count` when adding CCSDS components

## Related Skills

- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
- **Framework components**: [adamant-framework-components](../adamant-framework-components/SKILL.md)
