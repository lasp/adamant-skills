<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# COSMOS Plugin Setup & Assembly Wiring Details

## Component Configurations

### Ccsds_Socket_Interface (active)
TCP client for bidirectional COSMOS communication.
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
Connectors: `Ccsds_Space_Packet_T_Recv_Async` (downlink in), `Ccsds_Space_Packet_T_Send` (uplink out), `Event_T_Send`, `Sys_Time_T_Get`

### Ccsds_Command_Depacketizer (passive)
Connectors: `Ccsds_Space_Packet_T_Recv_Sync`, `Command_T_Send`, `Data_Product_T_Send`, `Event_T_Send`, `Packet_T_Send`, `Sys_Time_T_Get`, `Command_Response_T_Send`, `Command_T_Recv_Sync`

### Ccsds_Packetizer (passive)
Connectors: `Packet_T_Recv_Sync`, `Ccsds_Space_Packet_T_Send`. Has NO Sys_Time_T_Get.

### Event_Packetizer (passive)
```yaml
- type: Event_Packetizer
  name: Event_Packetizer_Instance
  init:
    - "Num_Internal_Packets => 5"
    - "Partial_Packet_Timeout => 1"
  set_id_bases:
    - "Packet_Id_Base => 98"
```

### Product_Packetizer (passive, has async command)
```yaml
- type: Product_Packetizer
  name: Product_Packetizer_Instance
  init_base:
    - "Queue_Size => 3 * Product_Packetizer_Instance.Get_Max_Queue_Element_Size"
  discriminant:
    - "packet_List => Assembly_Product_Packets.Packet_List'Access"
```

## Full Connection Wiring

### Uplink (Commands)
```yaml
# Socket -> Depacketizer
- from_component: Ccsds_Socket_Interface_Instance
  from_connector: Ccsds_Space_Packet_T_Send
  to_component: Ccsds_Command_Depacketizer_Instance
  to_connector: Ccsds_Space_Packet_T_Recv_Sync

# Depacketizer -> Router (async input, NOT indexed Command_T_Send)
- from_component: Ccsds_Command_Depacketizer_Instance
  from_connector: Command_T_Send
  to_component: Command_Router_Instance
  to_connector: Command_T_To_Route_Recv_Async

# Depacketizer command responses
- from_component: Ccsds_Command_Depacketizer_Instance
  from_connector: Command_Response_T_Send
  to_component: Command_Router_Instance
  to_connector: Command_Response_T_Recv_Async
```

### Downlink (Telemetry)
```yaml
# All Packet_T sources -> Ccsds_Packetizer
- from_component: Event_Packetizer_Instance
  from_connector: Packet_T_Send
  to_component: Ccsds_Packetizer_Instance
  to_connector: Packet_T_Recv_Sync

- from_component: Product_Packetizer_Instance
  from_connector: Packet_T_Send
  to_component: Ccsds_Packetizer_Instance
  to_connector: Packet_T_Recv_Sync

- from_component: Ccsds_Command_Depacketizer_Instance
  from_connector: Packet_T_Send
  to_component: Ccsds_Packetizer_Instance
  to_connector: Packet_T_Recv_Sync

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

### DP Fetch
```yaml
- from_component: Product_Packetizer_Instance
  from_connector: Data_Product_Fetch_T_Request
  to_component: Product_Database_Instance
  to_connector: Data_Product_Fetch_T_Service
```

### Events → Splitter
Wire `Event_T_Send` from Socket, Depacketizer, Product_Packetizer, Event_Packetizer → `Event_Splitter_Instance.T_Recv_Sync`.

### Command Routing
Add indexed `Command_T_Send` connections to Product_Packetizer (`Recv_Async`), Event_Packetizer (`Recv_Sync`), Product_Database (`Recv_Sync`), Depacketizer (`Recv_Sync`). Update `Command_T_Send_Count`.

### Sys_Time
Wire for: Socket, Depacketizer, Event_Packetizer, Product_Packetizer. NOT Ccsds_Packetizer.

## Product Packets Model

`<assembly_name>.product_packets.yaml`:
```yaml
packets:
  - name: Housekeeping_Packet
    id: 1
    data_products:
      - name: Temp_Sensor_Reader.Reading_Count
        use_timestamp: True
      - name: Temp_Sensor_Reader.Last_Reading
        use_timestamp: True
    period: "1"
  - name: System_Status_Packet
    id: 2
    data_products:
      - name: Command_Router_Instance.Command_Receive_Count
    period: "5"
```

## COSMOS Plugin Structure (Real Example)

```
openc3-cosmos-station-assembly/
├── plugin.txt
├── openc3-cosmos-station-assembly.gemspec
├── openc3-cosmos-station-assembly-0.0.1.gem   # Built artifact
└── targets/STATION_ASSEMBLY/
    ├── cmd_tlm/
    │   ├── cmd.txt
    │   └── tlm.txt
    └── lib/
        ├── crc_sync_protocol.rb
        ├── cmd_checksum.rb
        └── cmd_sync_checksum.rb
```

## Gem Build & Load

```bash
# Build gem inside COSMOS Docker:
cd cosmos-project/plugins/openc3-cosmos-station-assembly/
docker compose -f ../../compose.yaml run --rm \
  -v "$(pwd):/openc3/local:z" -w /openc3/local \
  --no-deps openc3-cosmos-cmd-tlm-api gem build *.gemspec

# Load into running COSMOS:
../../openc3.sh cli load openc3-cosmos-station-assembly-0.0.1.gem

# Or validate first:
../../openc3.sh cli validate openc3-cosmos-station-assembly-0.0.1.gem
```

## COSMOS CLI
```bash
./openc3.sh start                        # Start COSMOS
./openc3.sh cli load plugin.gem          # Load plugin
cmd("TARGET CMD with PARAM1 val1")       # Send command
value = tlm("TARGET PKT ITEM")          # Read telemetry
```
