# COSMOS Plugin Setup & Assembly Wiring Details

## Required Framework Components (Detailed)

### Ccsds_Socket_Interface (active)
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
Connectors: `Ccsds_Space_Packet_T_Recv_Sync`, `Command_T_Send`, `Data_Product_T_Send`, `Event_T_Send`, `Packet_T_Send`, `Sys_Time_T_Get`, `Command_Response_T_Send`

### Ccsds_Packetizer (passive)
Connectors: `Packet_T_Recv_Sync`, `Ccsds_Space_Packet_T_Send`. Has NO Sys_Time_T_Get.

### Event_Packetizer (passive)
```yaml
- type: Event_Packetizer
  init:
    - "Num_Internal_Packets => 5"
    - "Partial_Packet_Timeout => 1"
  set_id_bases:
    - "Packet_Id_Base => 98"
```

### Product_Packetizer (passive, has async command)
```yaml
- type: Product_Packetizer
  init_base:
    - "Queue_Size => 3 * Product_Packetizer_Instance.Get_Max_Queue_Element_Size"
  discriminant:
    - "Packet_List => Assembly_Product_Packets.Packet_List'Access"
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
  to_connector: Command_T_Recv_Async
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

### Events → Splitter (all new components)
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
      - name: Instance_Name.DP_Name
        use_timestamp: True
    period: "1"
  - name: Status_Packet
    id: 2
    data_products:
      - name: Command_Router_Instance.Command_Receive_Count
    period: "5"
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

### plugin.txt
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

### Gem Build (Docker)
```bash
docker compose -f cosmos/compose.yaml run --rm \
  -v "$(pwd):/openc3/local:z" -w /openc3/local \
  --no-deps openc3-cosmos-cmd-tlm-api gem build *.gemspec

# Validate & Load similarly with ruby /openc3/bin/openc3cli validate/load
```

## COSMOS CLI
```bash
./openc3.sh start
./openc3.sh cli load plugin.gem
cmd("TARGET CMD with PARAM1 val1")
value = tlm("TARGET PKT ITEM")
```
