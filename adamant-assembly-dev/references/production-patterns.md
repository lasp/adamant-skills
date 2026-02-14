# Assembly Production Patterns — Detailed Reference

## Multi-Rate Scheduling

Ticker -> Tick_Divider -> Rate_Groups at different rates:
```yaml
components:
  - type: Ticker
    priority: 10
    discriminant:
      - "Period_Us => 200000"              # 200ms base tick
  - type: Tick_Divider
    init_base:
      - "Tick_T_Send_Count => 3"
    init:
      - "Dividers => Dividers'Access"      # [1=>5, 2=>10, 3=>1] in preamble
  - type: Rate_Group
    name: Slow_Rate_Group                  # 0.5Hz = 200ms * 10
    priority: 9
    init_base:
      - "Queue_Size => 3 * Slow_Rate_Group.Get_Max_Queue_Element_Size"
      - "Tick_T_Send_Count => 8"
    init:
      - "Ticks_Per_Timing_Report => 10"
  - type: Rate_Group
    name: Fast_Rate_Group                  # 5Hz = 200ms * 1
    priority: 9
```

## Event Stream Bifurcation

Split events into filtered/limited downlink + unfiltered post-mortem:
```yaml
  - type: Splitter
    name: Event_Splitter_Instance
    generic_types:
      - "T => Event.T"
    init_base:
      - "T_Send_Count => 2"
  - type: Event_Filter
    init:
      - "Event_Id_Start_Range => My_Events.Minimum_Event_Id"
      - "Event_Id_End_Range => My_Events.Maximum_Event_Id"
  - type: Event_Limiter
  - type: Logger
    name: Event_Post_Mortem_Logger
    generic_types:
      - "T => Event.T"
      - "Serialized_Length => Event.Serialized_Length"
    init:
      - "Size => 1024 * 100"
      - "Initial_Mode => Logger_Enums.Logger_Mode.Enabled"
```

## Command Routing

```yaml
  - type: Command_Router
    priority: 8
    init_base:
      - "Queue_Size => 10 * Command_Router_Instance.Get_Max_Queue_Element_Size"
      - "Command_T_Send_Count => 22"
      - "Command_Response_T_To_Forward_Send_Count => 1"
    init:
      - "Max_Number_Of_Commands => My_Commands.Number_Of_Commands"
```

Route via indexed `Command_T_Send` connector. Components register commands during Set_Up via `Command_Response_T_Send`.

## Observation Infrastructure Pattern

```yaml
# Minimal event visibility: Splitter + Event_Text_Logger
  - type: Splitter
    name: Event_Splitter_Instance
    generic_types:
      - "T => Event.T"
    init_base:
      - "T_Send_Count => 1"
  - type: Event_Text_Logger
    name: Event_Text_Logger_Instance
    priority: 1
    stack_size: 50000
    secondary_stack_size: 10000
    init_base:
      - "Queue_Size => 3 * Event_Text_Logger_Instance.Get_Max_Queue_Element_Size"
    discriminant:
      - "Event_To_Text => Assembly_Event_To_Text.Event_To_Text'Access"
  - type: Product_Database
    name: Product_Database_Instance
    init:
      - "Minimum_Data_Product_Id => Assembly_Data_Products.Minimum_Data_Product_Id"
      - "Maximum_Data_Product_Id => Assembly_Data_Products.Maximum_Data_Product_Id"
      - "Send_Event_On_Missing => False"
```
Wire ALL `Event_T_Send` → `Event_Splitter_Instance.T_Recv_Sync`. Wire splitter `T_Send` index 1 → logger's `Event_T_Recv_Async`. Wire ALL `Data_Product_T_Send` → `Product_Database_Instance.Data_Product_T_Recv_Sync`.

## Parameter System Wiring

Three-component pattern: `Parameters` (active table) + `Parameter_Store` (default/NVM) + `Parameter_Manager` (copy commands):
```yaml
  - type: Parameters
    init_base:
      - "Queue_Size => 3 * Parameters_Instance.Get_Max_Queue_Element_Size"
      - "Parameter_Update_T_Provide_Count => 2"  # One per component with parameters
    init:
      - "Parameter_Table_Entries => Assembly_Parameter_Table.Parameter_Table_Entries'Access"
      - "Table_Id => Assembly_Parameter_Table.Parameter_Table_Id"
```
Connect `Parameter_Update_T_Provide` to each component's `Parameter_Update_T_Modify`.

## Event System Chain

`Event_Splitter` → `Event_Filter` → `Event_Limiter` → `Event_Packetizer`. Splitter fans out to filtered path + unfiltered post-mortem log.

## Fault System

`Fault_Correction` maps fault IDs to corrective commands via a response table. Connect all component `Fault_T_Send` to it.

**WARNING: Fault.T is NOT Event.T — never wire Fault_T_Send to Event_T_Recv.** If no Fault_Correction, leave fault sends unconnected.

## Assembly-Generated Constants

Assemblies auto-generate packages: `Assembly_Commands`, `Assembly_Events`, `Assembly_Data_Products` with `Number_Of_Commands`, `Minimum_Event_Id`, `Maximum_Event_Id`, etc.

## View Configuration

```yaml
# views/data_flow.assembly_name.view.yaml
description: Data processing subsystem
layout: left-to-right
show_component_type: true
rule: include_component_types & exclude_connector
filters:
  - name: include_component_types
    type: component_type
    include: [Example_Parameters]
  - name: exclude_connector
    type: connector_name
    exclude: [Science_Instance.Command_T_Recv_Async]
```

Filter types: `component_name`, `component_name_context`, `component_type`, `component_type_context`, `component_execution`, `connector_name`, `connector_type`, `connector_kind`, `data_dependency_name`, `data_dependency_type`.
