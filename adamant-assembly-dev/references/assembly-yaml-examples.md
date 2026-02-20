<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Assembly YAML Examples

Concrete examples from real assemblies for quick reference.

## Minimal Assembly (No CCSDS, No Commands)

```yaml
description: Minimal assembly demonstrating basic component wiring
with:
  - Mini_Assembly_Event_To_Text
  - Mini_Assembly_Data_Products
  - Sensor_Id

components:
  - type: Gps_Time
    name: System_Time_Instance

  - type: Ticker
    name: Ticker_Instance
    priority: 10
    stack_size: 50000
    secondary_stack_size: 10000
    discriminant:
      - "Period_Us => 200000"

  - type: Rate_Group
    name: Rate_Group_Instance
    priority: 9
    stack_size: 50000
    secondary_stack_size: 10000
    init_base:
      - "Queue_Size => 3 * Rate_Group_Instance.Get_Max_Queue_Element_Size"
      - "Tick_T_Send_Count => 3"
    init:
      - "Ticks_Per_Timing_Report => 10"

  - type: Sensor_Reader
    name: Sensor_Reader_Instance
    init:
      - "Id => Sensor_Id.Sensor_Id_Type.Temperature_1"

  - type: Splitter
    name: Event_Splitter_Instance
    generic_types:
      - "T => Event.T"
    init_base:
      - "T_Send_Count => 2"

  - type: Event_Text_Logger
    name: Event_Text_Logger_Instance
    priority: 1
    stack_size: 50000
    secondary_stack_size: 10000
    init_base:
      - "Queue_Size => 3 * Event_Text_Logger_Instance.Get_Max_Queue_Element_Size"
    discriminant:
      - "Event_To_Text => Mini_Assembly_Event_To_Text.Event_To_Text'Access"

  - type: Product_Database
    name: Product_Database_Instance
    init:
      - "Minimum_Data_Product_Id => Mini_Assembly_Data_Products.Minimum_Data_Product_Id"
      - "Maximum_Data_Product_Id => Mini_Assembly_Data_Products.Maximum_Data_Product_Id"
      - "Send_Event_On_Missing => False"

connections:
  - from_component: Ticker_Instance
    from_connector: Tick_T_Send
    to_component: Rate_Group_Instance
    to_connector: Tick_T_Recv_Async
  - from_component: Rate_Group_Instance
    from_connector: Tick_T_Send
    from_index: 1
    to_component: Sensor_Reader_Instance
    to_connector: Tick_T_Recv_Sync
  - from_component: Rate_Group_Instance
    from_connector: Pet_T_Send
    to_component: ignore
    to_connector: ignore
  - from_component: Product_Database_Instance
    from_connector: Packet_T_Send
    to_component: ignore
    to_connector: ignore
```

## Multi-Rate with Tick_Divider

```yaml
preamble: |
  Dividers : aliased Component.Tick_Divider.Divider_Array_Type := [1 => 1, 2 => 10];

components:
  - type: Tick_Divider
    init_base:
      - "Tick_T_Send_Count => 2"
    init:
      - "Dividers => Dividers'Access"

  - type: Rate_Group
    name: Fast_Rate_Group             # 5Hz (divider=1)
    priority: 9
    stack_size: 50000
    secondary_stack_size: 10000
    init_base:
      - "Queue_Size => 3 * Fast_Rate_Group.Get_Max_Queue_Element_Size"
      - "Tick_T_Send_Count => 11"
    init:
      - "Ticks_Per_Timing_Report => 25"

  - type: Rate_Group
    name: Slow_Rate_Group             # 0.5Hz (divider=10)
    priority: 8
    stack_size: 50000
    secondary_stack_size: 10000
    init_base:
      - "Queue_Size => 3 * Slow_Rate_Group.Get_Max_Queue_Element_Size"
      - "Tick_T_Send_Count => 7"
    init:
      - "Ticks_Per_Timing_Report => 5"

connections:
  - from_component: Ticker_Instance
    from_connector: Tick_T_Send
    to_component: Tick_Divider_Instance
    to_connector: Tick_T_Recv_Sync
  - from_component: Tick_Divider_Instance
    from_connector: Tick_T_Send
    from_index: 1
    to_component: Fast_Rate_Group
    to_connector: Tick_T_Recv_Async
  - from_component: Tick_Divider_Instance
    from_connector: Tick_T_Send
    from_index: 2
    to_component: Slow_Rate_Group
    to_connector: Tick_T_Recv_Async
```

## Command Router with Self-Loopback

```yaml
  - type: Command_Router
    name: Command_Router_Instance
    priority: 8
    stack_size: 50000
    secondary_stack_size: 10000
    init_base:
      - "Queue_Size => 10 * Command_Router_Instance.Get_Max_Queue_Element_Size"
      - "Command_T_Send_Count => 16"
      - "Command_Response_T_To_Forward_Send_Count => 1"
    init:
      - "Max_Number_Of_Commands => Station_Assembly_Commands.Number_Of_Commands"

connections:
  # Self-loopback (REQUIRED)
  - from_component: Command_Router_Instance
    from_connector: Command_Response_T_To_Forward_Send
    to_component: Command_Router_Instance
    to_connector: Command_Response_T_Recv_Async
  # Router routes to itself (index 1, for noop test)
  - from_component: Command_Router_Instance
    from_connector: Command_T_Send
    from_index: 1
    to_component: Command_Router_Instance
    to_connector: Command_T_Recv_Async
```

## Task Watchdog with Pet Connections (to_index)

```yaml
  - type: Task_Watchdog
    init_base:
      - "Pet_T_Recv_Sync_Count => 2"
    init:
      - "Task_Watchdog_Entry_Init_List => Assembly_Task_Watchdog_List.Task_Watchdog_Entry_Init_List"

connections:
  - from_component: Slow_Rate_Group
    from_connector: Pet_T_Send
    to_component: Task_Watchdog_Instance
    to_connector: Pet_T_Recv_Sync
    to_index: 1
  - from_component: Fast_Rate_Group
    from_connector: Pet_T_Send
    to_component: Task_Watchdog_Instance
    to_connector: Pet_T_Recv_Sync
    to_index: 2
```

## Fault Protection Wiring

```yaml
  - type: Fault_Correction
    priority: 11
    stack_size: 40000
    secondary_stack_size: 5000
    init_base:
      - "Queue_Size => 5 * Fault_Correction_Instance.Get_Max_Queue_Element_Size"
    init:
      - "Fault_Response_Configurations => Assembly_Fault_Responses.Fault_Response_List"

connections:
  - from_component: Task_Watchdog_Instance
    from_connector: Fault_T_Send
    to_component: Fault_Correction_Instance
    to_connector: Fault_T_Recv_Async
  # Corrective commands bypass router queue (sync for fastest response)
  - from_component: Fault_Correction_Instance
    from_connector: Command_T_Send
    to_component: Command_Router_Instance
    to_connector: Command_T_To_Route_Recv_Sync
```

## Data Dependency Mapping

```yaml
  - type: My_Controller
    name: My_Controller_Instance
    map_data_dependencies:
      - data_dependency: Temperature
        data_product: "Temp_Sensor_Reader.Last_Reading"
        stale_limit_us: 1000000
      - data_dependency: Pressure
        data_product: "Pressure_Sensor_Reader.Last_Reading"
        stale_limit_us: 0
```

## Subtask Example (Socket Interface)

```yaml
  - type: Ccsds_Socket_Interface
    name: Ccsds_Socket_Interface_Instance
    priority: 6
    stack_size: 50000
    secondary_stack_size: 10000
    init_base:
      - "Queue_Size => 8192"
    init:
      - "Addr => \"127.0.0.1\""
      - "Port => 2003"
    subtasks:
      - name: Listener
        priority: 0
        stack_size: 20000
        secondary_stack_size: 5000
        disabled: False
```

## Prepreamble (Elaboration Control)

```yaml
prepreamble: |
  pragma Unreferenced (Start_Up);
  pragma Elaborate_All (Start_Up);
```
