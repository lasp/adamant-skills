---
name: adamant-cosmos-integration
description: COSMOS (OpenC3) ground system integration for Adamant assemblies -- CCSDS pipeline, plugin generation, and ground operations
---

# Adamant COSMOS (OpenC3) Integration

Complete guide to connecting an Adamant assembly to the COSMOS ground system via CCSDS.

## Architecture Overview

### Command Flow (Uplink)
```
COSMOS Ground System -> TCP Socket -> Ccsds_Socket_Interface -> Ccsds_Command_Depacketizer -> Command_Router -> Components
```

### Telemetry Flow (Downlink)
```
Components -> Events -> Event_Packetizer -> Ccsds_Packetizer -> Ccsds_Socket_Interface -> COSMOS
Components -> DPs -> Product_Database -> Product_Packetizer -> Ccsds_Packetizer -> Socket -> COSMOS
```

## Required Framework Components

### 1. Ccsds_Socket_Interface (active)
TCP socket for bidirectional COSMOS communication.
```yaml
- type: Ccsds_Socket_Interface
  name: Ccsds_Socket_Interface_Instance
  priority: 6
  stack_size: 50000
  secondary_stack_size: 10000
  init_base:
    - "Queue_Size => 8192"
  init:
    - "Addr => \"127.0.0.1\""          # Use "host.docker.internal" inside Docker
    - "Port => 2003"
  subtasks:
    - name: Listener
      priority: 0
      stack_size: 20000
      secondary_stack_size: 5000
      disabled: False
```
**Connectors:** `Ccsds_Space_Packet_T_Recv_Async` (downlink in), `Ccsds_Space_Packet_T_Send` (uplink out), `Event_T_Send`, `Sys_Time_T_Get`

### 2. Ccsds_Command_Depacketizer (passive)
Converts CCSDS packets to Adamant commands.
```yaml
- type: Ccsds_Command_Depacketizer
  name: Ccsds_Command_Depacketizer_Instance
```
**Connectors:** `Ccsds_Space_Packet_T_Recv_Sync` (from socket), `Command_T_Send` (to router), `Data_Product_T_Send`, `Event_T_Send`, `Packet_T_Send` (error packets), `Sys_Time_T_Get`, `Command_Response_T_Send`

### 3. Ccsds_Packetizer (passive)
Converts Adamant Packet.T to CCSDS with CRC and secondary header.
```yaml
- type: Ccsds_Packetizer
  name: Ccsds_Packetizer_Instance
```
**Connectors:** `Packet_T_Recv_Sync` (all packet sources feed here), `Ccsds_Space_Packet_T_Send` (to socket)

### 4. Event_Packetizer (passive)
Batches events into packets for downlink.
```yaml
- type: Event_Packetizer
  name: Event_Packetizer_Instance
  init:
    - "Num_Internal_Packets => 5"
    - "Partial_Packet_Timeout => 1"    # Ticks before partial packet flush
  set_id_bases:
    - "Packet_Id_Base => 98"
```
**Connectors:** `Tick_T_Recv_Sync`, `Event_T_Recv_Sync`, `Command_T_Recv_Sync`, `Packet_T_Send`, `Command_Response_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`

### 5. Product_Packetizer (passive, has async command)
Periodically fetches DPs from Product_Database and packetizes them.
```yaml
- type: Product_Packetizer
  name: Product_Packetizer_Instance
  init_base:
    - "Queue_Size => 3 * Product_Packetizer_Instance.Get_Max_Queue_Element_Size"
  discriminant:
    - "Packet_List => {Assembly_Name}_Product_Packets.Packet_List'Access"
  init:
```
**Connectors:** `Tick_T_Recv_Sync`, `Data_Product_Fetch_T_Request` (to Product_Database), `Packet_T_Send`, `Command_T_Recv_Async`, `Command_Response_T_Send`, `Event_T_Send`, `Data_Product_T_Send`, `Sys_Time_T_Get`

## Connection Wiring

### Uplink (Commands In)
```yaml
# Socket -> Depacketizer (CCSDS to Adamant command)
- from_component: Ccsds_Socket_Interface_Instance
  from_connector: Ccsds_Space_Packet_T_Send
  to_component: Ccsds_Command_Depacketizer_Instance
  to_connector: Ccsds_Space_Packet_T_Recv_Sync

# Depacketizer -> Command Router
- from_component: Ccsds_Command_Depacketizer_Instance
  from_connector: Command_T_Send
  to_component: Command_Router_Instance
  to_connector: Command_T_Recv_Async
```
**NOTE:** Depacketizer sends to `Command_T_Recv_Async` (NOT the indexed `Command_T_Send` array). This is the router's external command input.

### Downlink (Telemetry Out)
```yaml
# Event packets -> CCSDS packetizer
- from_component: Event_Packetizer_Instance
  from_connector: Packet_T_Send
  to_component: Ccsds_Packetizer_Instance
  to_connector: Packet_T_Recv_Sync

# Product packets -> CCSDS packetizer
- from_component: Product_Packetizer_Instance
  from_connector: Packet_T_Send
  to_component: Ccsds_Packetizer_Instance
  to_connector: Packet_T_Recv_Sync

# Error/dump packets -> CCSDS packetizer
- from_component: Ccsds_Command_Depacketizer_Instance
  from_connector: Packet_T_Send
  to_component: Ccsds_Packetizer_Instance
  to_connector: Packet_T_Recv_Sync

# Product Database dump packets -> CCSDS packetizer
- from_component: Product_Database_Instance
  from_connector: Packet_T_Send
  to_component: Ccsds_Packetizer_Instance
  to_connector: Packet_T_Recv_Sync

# CCSDS -> Socket -> COSMOS
- from_component: Ccsds_Packetizer_Instance
  from_connector: Ccsds_Space_Packet_T_Send
  to_component: Ccsds_Socket_Interface_Instance
  to_connector: Ccsds_Space_Packet_T_Recv_Async
```

### Data Product Fetch (Product_Packetizer -> Product_Database)
```yaml
- from_component: Product_Packetizer_Instance
  from_connector: Data_Product_Fetch_T_Request
  to_component: Product_Database_Instance
  to_connector: Data_Product_Fetch_T_Service
```

### Event Pipeline Integration
Route filtered/limited events to Event_Packetizer via the existing Event_Splitter:
```yaml
# Increase Event_Splitter T_Send_Count to include Event_Packetizer
# Event_Splitter T_Send index N -> Event_Packetizer
- from_component: Event_Splitter_Instance
  from_connector: T_Send
  from_index: 2                       # Index 1 = Event_Text_Logger, 2 = Event_Packetizer
  to_component: Event_Packetizer_Instance
  to_connector: Event_T_Recv_Sync
```

### New Components' Events -> Splitter
```yaml
- from_component: Ccsds_Socket_Interface_Instance
  from_connector: Event_T_Send
  to_component: Event_Splitter_Instance
  to_connector: T_Recv_Sync
- from_component: Ccsds_Command_Depacketizer_Instance
  from_connector: Event_T_Send
  to_component: Event_Splitter_Instance
  to_connector: T_Recv_Sync
- from_component: Product_Packetizer_Instance
  from_connector: Event_T_Send
  to_component: Event_Splitter_Instance
  to_connector: T_Recv_Sync
- from_component: Event_Packetizer_Instance
  from_connector: Event_T_Send
  to_component: Event_Splitter_Instance
  to_connector: T_Recv_Sync
```

### Command Routing for New Components
Add to Command_Router indexed sends (update `Command_T_Send_Count`):
```yaml
- from_component: Command_Router_Instance
  from_connector: Command_T_Send
  from_index: N
  to_component: Product_Packetizer_Instance
  to_connector: Command_T_Recv_Async              # NOTE: async for Product_Packetizer
- from_component: Command_Router_Instance
  from_connector: Command_T_Send
  from_index: N+1
  to_component: Event_Packetizer_Instance
  to_connector: Command_T_Recv_Sync
- from_component: Command_Router_Instance
  from_connector: Command_T_Send
  from_index: N+2
  to_component: Product_Database_Instance
  to_connector: Command_T_Recv_Sync
- from_component: Command_Router_Instance
  from_connector: Command_T_Send
  from_index: N+3
  to_component: Ccsds_Command_Depacketizer_Instance
  to_connector: Command_T_Recv_Sync
```

### Tick Connections
Event_Packetizer and Product_Packetizer both need ticks (update `Tick_T_Send_Count`).

### Sys_Time for All New Components
Wire `Sys_Time_T_Get -> System_Time_Instance.Sys_Time_T_Return` for:
- Ccsds_Socket_Interface_Instance
- Ccsds_Command_Depacketizer_Instance
- Event_Packetizer_Instance
- Product_Packetizer_Instance

**Ccsds_Packetizer does NOT have Sys_Time_T_Get** (it gets time from the packet secondary header).

## Product Packets Model

Create `assembly_name.product_packets.yaml` in the assembly directory:
```yaml
---
description: Data product packets for downlink
packets:
  - name: Housekeeping_Packet
    description: Core housekeeping telemetry
    id: 1
    data_products:
      - name: Sensor_Instance.Reading_Value
        use_timestamp: True              # Include DP timestamp (optional)
      - name: Controller_Instance.Status
    period: "1"                          # Create every N ticks

  - name: Status_Packet
    description: System status
    id: 2
    data_products:
      - name: Command_Router_Instance.Command_Receive_Count
      - name: Command_Router_Instance.Command_Success_Count
    period: "5"                          # Every 5 ticks
```

**Field reference:**
- `name`: `Component_Instance_Name.Data_Product_Name` (from data_products.yaml)
- `id`: Unique packet identifier (integer)
- `period`: Tick count between packet creation (string)
- `use_timestamp`: Include the DP's timestamp in the packet (boolean, optional)

Add `{Assembly_Name}_Product_Packets` to the assembly `with:` list. The package name follows the assembly name exactly (e.g., `Station_Assembly_Product_Packets` for assembly named `Station_Assembly`).

## COSMOS Plugin Structure

### Plugin Directory
```
openc3-cosmos-assembly-name/
├── plugin.txt                     # Interface/protocol config
└── targets/
    └── ASSEMBLY_NAME/             # Uppercase assembly name
        ├── cmd_tlm/
        │   ├── cmd.txt            # Generated command definitions
        │   └── tlm.txt            # Generated telemetry definitions
        ├── lib/
        │   ├── crc_protocol.rb    # From adamant/gnd/cosmos/
        │   └── cmd_checksum.rb    # From adamant/gnd/cosmos/
        └── target.txt             # Target config (optional)
```

### plugin.txt Template
```ruby
Variable assembly_target_name Assembly_Name
Variable crc_parameter_name CRC
Variable checksum_parameter_name Checksum
Variable port_w 2003
Variable port_r 2003

Target Assembly_Name <%= assembly_target_name %>

Interface <%= assembly_target_name %>_INT tcpip_server_interface.rb <%= port_w %> <%= port_r %> 10.0 nil Length 32 16 7
  Map_Target <%= assembly_target_name %>
  Protocol Read crc_protocol.rb <%= crc_parameter_name %> false "ERROR" -16 16
  Protocol Write cmd_checksum.rb <%= checksum_parameter_name %>
```

## Build & Install Workflow

### 1. Generate COSMOS Config
```bash
# From assembly/main/ directory
redo cosmos_config
```
This produces:
- `build/cosmos/plugin/{assembly}_ccsds_cosmos_commands.txt`
- `build/cosmos/plugin/{assembly}_ccsds_cosmos_telemetry.txt`

### 2. Install Plugin Files
```bash
./install_cosmos_plugin.sh /path/to/cosmos-project/openc3-cosmos-assembly-name/
```
Copies generated cmd/tlm files + protocol .rb files + plugin.txt to the COSMOS plugin directory.

### 3. Load Plugin into COSMOS
```bash
cd /path/to/cosmos-project
./openc3.sh cli load /path/to/plugin.gem
```

## COSMOS CLI Operations

```bash
# Start COSMOS
./openc3.sh start

# Load/validate plugins
./openc3.sh cli load plugin.gem SCOPE
./openc3.sh cli validate plugin.gem

# List installed plugins
./openc3.sh cli list

# Run scripts
./openc3.sh cli script run script.py
./openc3.sh cli script spawn script.py    # Background

# Script API (Python)
cmd("TARGET CMD with PARAM1 val1, PARAM2 val2")
value = tlm("TARGET PKT ITEM")
```

## Assembly `with:` Packages

When adding CCSDS pipeline, add to assembly YAML `with:`:
```yaml
with:
  - Assembly_Product_Packets          # For Product_Packetizer discriminant
  - Assembly_Event_To_Text            # For Event_Text_Logger (if present)
  - Assembly_Commands                 # Already present (for Command_Router)
  - Assembly_Data_Products            # Already present (for Product_Database)
```

## Key Gotchas

1. **Socket address in Docker**: Use `"host.docker.internal"` when assembly runs in Docker and COSMOS runs on host. Use `"127.0.0.1"` when both run on same host.
2. **Depacketizer command output**: Goes to `Command_T_Recv_Async` on router (external input), NOT the indexed `Command_T_Send` array.
3. **Ccsds_Packetizer has NO Sys_Time_T_Get**: It reads time from packet headers. Do not wire.
4. **Product_Packetizer has async command connector**: `Command_T_Recv_Async` -- needs `init_base` with `Queue_Size` even though it's passive execution. Has tick, command, event, DP, packet, and fetch connectors.
5. **Event_Packetizer Packet_Id_Base**: Set to avoid collision with auto-assigned IDs. Linux example uses 98.
6. **All Packet_T_Send sources must wire to Ccsds_Packetizer**: Including Depacketizer error packets and Product_Database dump packets.
7. **Generated COSMOS files are assembly-specific**: Target name = assembly name (uppercase in COSMOS).
8. **Protocol files come from adamant/gnd/cosmos/**: Copy `crc_protocol.rb`, `cmd_checksum.rb`, etc. to plugin lib/ directory.
9. **Product_Packetizer needs empty `init:` in assembly YAML**: Even though all init params are optional, the assembly generator requires the `init:` key to exist (can be empty).
10. **COSMOS config generation**: Run `redo cosmos_config` from `assembly/main/` directory. Produces `build/cosmos/plugin/` with command and telemetry txt files.
