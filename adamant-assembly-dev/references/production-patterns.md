<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Assembly Production Patterns -- Detailed Reference

Core pitfalls and multi-rate scheduling are in SKILL.md. This file has subsystem wiring examples.

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

Route via indexed `Command_T_Send` connector. Components register commands during Set_Up.

## Observation Infrastructure Pattern

```yaml
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

## Parameter System Wiring

Three-component pattern: `Parameters` + `Parameter_Store` + `Parameter_Manager`:
```yaml
  - type: Parameters
    init_base:
      - "Queue_Size => 3 * Parameters_Instance.Get_Max_Queue_Element_Size"
      - "Parameter_Update_T_Provide_Count => 2"
    init:
      - "Parameter_Table_Entries => Assembly_Parameter_Table.Parameter_Table_Entries'Access"
      - "Table_Id => Assembly_Parameter_Table.Parameter_Table_Id"
```
