---
name: adamant-assembly-dev
description: Patterns and workflows for creating assemblies and system architectures in the Adamant framework
---

# Adamant Assembly Development

An assembly instantiates components, defines connections, assigns task priorities/stack sizes, and maps IDs into an executable system.

## File Structure

```
assembly_name/
├── .all_path                              # Build path inclusion
├── assembly_name.assembly.yaml            # Assembly model (REQUIRED)
├── main/main.adb                          # Handwritten main program
├── views/
│   └── view_name.assembly_name.view.yaml  # Focused diagrams
└── test/
```

## Assembly Model

### Top-Level Fields
```yaml
description: What this assembly does
with:                                 # Ada package imports
  - Start_Up
  - System
  - Ada.Interrupts.Names
  - My_Assembly_Commands
prepreamble: |                        # Before component declarations (pragma, elaborate)
  pragma Unreferenced (Start_Up);
  pragma Elaborate_All (Start_Up);
preamble: |                           # Inside package spec (types, variables)
  Dividers : aliased Component.Tick_Divider.Divider_Array_Type := [1 => 5, 2 => 10, 3 => 1];
```

### Component Instantiation
```yaml
components:
  - type: component_type_name        # From component.yaml filename
    name: instance_name               # Unique instance name
    description: What this instance does
    execution: active|passive         # Override if component is "either"
    priority: 10                      # Task priority (active only)
    stack_size: 50000                 # Primary stack bytes
    secondary_stack_size: 10000       # Secondary stack bytes

    # Generic type instantiation (for generic components like Splitter, Logger)
    generic_types:
      - "T => Event.T"
      - "Serialized_Length => Event.Serialized_Length"

    # Subtask overrides (for components with subtasks like Ccsds_Socket_Interface)
    subtasks:
      - name: Listener
        priority: 0
        stack_size: 20000
        secondary_stack_size: 5000
        disabled: False

    init_base:                        # Base class init (queue size, connector counts)
      - "Queue_Size => 3 * Instance_Name.Get_Max_Queue_Element_Size"
      - "Tick_T_Send_Count => 3"
    init:                             # Implementation init
      - "Dividers => Dividers'Access"
      - "Ticks_Per_Timing_Report => 10"
    discriminant:                     # Compile-time parameters
      - "Period_Us => 200000"
    set_id_bases:                     # ID assignment (auto-assigned if omitted)
      - "Command_Id_Base => 100"
      - "Event_Id_Base => 200"
      - "Data_Product_Id_Base => 300"
      - "Packet_Id_Base => 98"
```

### Connections
```yaml
connections:
  # Point-to-point
  - from_component: Source_Instance
    from_connector: Data_T_Send
    to_component: Sink_Instance
    to_connector: Data_T_Recv_Sync

  # Array connector (indexed)
  - from_component: Router_Instance
    from_connector: Command_T_Send
    from_index: 0
    to_component: Handler_Instance
    to_connector: Command_T_Recv_Async

  # Get/return (time service pattern -- every component needs this)
  - from_component: My_Component
    from_connector: Sys_Time_T_Get
    to_component: System_Time_Instance
    to_connector: Sys_Time_T_Return
```

### Views (Focused Diagrams)
```yaml
# views/data_flow.assembly_name.view.yaml -- simple component list
description: Data processing subsystem
components: [instance_1, instance_2]
connections:
  - from_component: instance_1
    from_connector: data_Send
    to_component: instance_2
    to_connector: data_Recv_Sync

# views/parameters.assembly_name.view.yaml -- filter rules
description: Parameter subsystem
rule: include_component_types & exclude_connector
filters:
  - name: include_component_types
    type: component_type
    include: [Example_Parameters, Example_Science]
  - name: exclude_connector
    type: connector_name
    exclude: [Science_Instance.Command_T_Recv_Async]
```

## Main Program Pattern

```ada
with Assembly_Package;
procedure Main is
   Assembly : Assembly_Package.Instance;
begin
   Assembly.Init (Assembly_Package.Init_Base_Args);
   Assembly.Connect_Components;
   Assembly.Start_Components;
   loop delay 1.0; end loop;
end Main;
```

## Build Commands

```bash
redo build/svg/assembly.svg                  # Assembly diagram
redo build/src/assembly.ads                  # Generated assembly package
redo build/html/assembly_commands.html       # Command documentation
redo build/html/assembly_connections.html    # Connection documentation
redo all                                     # Build everything
# From main/:
redo build/bin/Linux/main.elf               # Native build
redo build/bin/Pico/main.elf                # Cross-compile
redo run                                     # Build and run
```

## Task Priority Guidelines

1-5 background, 6-10 normal, 11-15 high-priority real-time, 16-20 critical, 21+ interrupt handlers.

## Production Patterns

### Multi-Rate Scheduling

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

### Event Stream Bifurcation

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

### Command Routing

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

Route via indexed `Command_T_Send` connector. Components register commands during init via `Command_Response_T_Send`.

## Assembly Validation

The generator validates: connector type matching, component existence, array index bounds, ID conflicts.
