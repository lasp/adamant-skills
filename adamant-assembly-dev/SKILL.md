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
with:                                 # Ada package imports for .ads
  - Start_Up
  - System
  - Ada.Interrupts.Names
  - My_Assembly_Commands
with_adb:                             # Ada package imports for .adb only
  - Implementation_Only_Package
prepreamble: |                        # Before package spec (pragma, elaborate)
  pragma Unreferenced (Start_Up);
  pragma Elaborate_All (Start_Up);
preamble: |                           # Inside package spec (types, variables)
  Dividers : aliased Component.Tick_Divider.Divider_Array_Type := [1 => 5, 2 => 10, 3 => 1];
subassemblies:                        # Include other assemblies
  - Sub_Assembly_Name
id_bases:                             # Assembly-level ID base offsets
  - "Event_Id_Base => 1280"
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
layout: left-to-right                 # or top-to-bottom, right-to-left, bottom-to-top
show_component_type: true             # Show/hide labels (all default true)
show_component_execution: true
show_component_priority: true
show_component_name: true
show_connector_type: true
show_data_dependencies: true
hide_group_outline: false
preamble: "rankdir=LR;"              # DOT snippet at digraph start
rule: include_component_types & exclude_connector
filters:
  - name: include_component_types
    type: component_type              # Filter types: component_name, component_name_context,
    include: [Example_Parameters]     #   component_type, component_type_context,
  - name: exclude_connector           #   component_execution, connector_name, connector_type,
    type: connector_name              #   connector_kind, data_dependency_name, data_dependency_type
    exclude: [Science_Instance.Command_T_Recv_Async]
```

## Main Program Pattern

```ada
with Ada.Real_Time; use Ada.Real_Time;
with Ada.Text_IO; use Ada.Text_IO;
with Ada.Exceptions; use Ada.Exceptions;
with Assembly_Name;

procedure Main is
   Wait_Time : constant Ada.Real_Time.Time_Span := Ada.Real_Time.Microseconds (1000000);
   Start_Time : constant Ada.Real_Time.Time := Ada.Real_Time.Clock + Wait_Time;
begin
   Assembly_Name.Init_Base;
   Assembly_Name.Set_Id_Bases;
   Assembly_Name.Connect_Components;
   Assembly_Name.Init_Components;

   Put_Line ("Starting assembly...");
   delay until Start_Time;
   Assembly_Name.Start_Components;    -- Start active tasks FIRST
   Assembly_Name.Set_Up_Components;   -- Then register commands (needs router running)

   loop
      delay until Clock + Milliseconds (1000);
   end loop;
exception
   when E : others =>
      Put_Line ("EXCEPTION: " & Exception_Information (E));
end Main;
```
**CRITICAL ordering**: `Start_Components` BEFORE `Set_Up_Components`. Set_Up registers commands with the Command_Router, which must already be running (active task). Add a 1-second delay before Start to let elaboration settle. The assembly API is package-level procedures (NOT instance methods). Use `delay until` (NOT `delay 1.0`) for Ravenscar compliance.

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

The generator validates:
- Connector type matching (kind compatibility + data type match)
- Component existence and unique instance names
- Array index bounds (1-65535)
- Global ID uniqueness across all components (commands, events, data products, packets, faults)
- All connectors connected or explicitly ignored
- Stack size minimums (2000 bytes)
- Priority conflicts (unique priorities or priority queue required)

### Automatic ID Assignment

If `set_id_bases` is omitted, the generator finds open ID ranges automatically. If specified, it validates no collisions with other components. Assembly-level `id_bases` set minimum starting IDs per entity type.

### Component Categorization (Computed)

The assembly model classifies each component instance as:
- `active`/`passive` -- execution model
- `queued`/`simple` -- has async connectors or not
- `init`/`commands`/`events`/`data_products`/`parameters`/`faults`/`packets` -- has that feature model

This drives which generated lifecycle methods exist.

## Common Assembly Pitfalls

- **Custom passive components: NO `init_base` unless active.** Only framework components with arrayed connectors (Rate_Group, Splitter, Command_Router) use `init_base` for connector counts. Custom components' connectors are fixed by their YAML model. Don't add `Event_T_Send_Count` or `Command_T_Send_Count` to custom component init_base.
- **`set_id_bases` is optional.** If omitted, the generator auto-assigns IDs. Don't use made-up values like `"Auto"` -- either specify numeric IDs or omit entirely.
- **Don't put `execution:` in assembly component definitions.** Execution model comes from the component's own YAML, not the assembly.
- **Active components need `init_base` in assembly YAML** with `Queue_Size`. Use `Instance_Name.Get_Max_Queue_Element_Size` multiplier.
- **Command_Router requires `Max_Number_Of_Commands` in `init`** -- total command count across all routed components.
- **Product_Database** (not `Data_Product_Database`) is the built-in DP store component name.
- **Data dependencies need `map_data_dependencies`** on the component instance:
```yaml
    map_data_dependencies:
      - data_dependency: Dep_Name           # From component's data_dependencies.yaml
        data_product: "Instance.DP_Name"    # "ComponentInstance.DataProductName"
        stale_limit_us: 1000000             # 0 = never stale
```
- **Assembly API is package-level, not instance**: Use `Assembly_Name.Init_Base`, `Assembly_Name.Set_Id_Bases`, etc. -- NOT instance methods.
- **Unique main procedure names**: Each assembly needs a unique `procedure Name` and filename. Multiple assemblies with `procedure Main` in `main.adb` cause build path conflicts.
- **Ravenscar: absolute delays only**: Use `delay until Clock + Milliseconds (N)`, NEVER `delay 1.0` (relative delays violate Ravenscar profile).
- **`with:` packages must exist in build path** -- don't include assembly-specific packages (like `Start_Up`) unless you've created them.
- **Unconnected `send` connectors are warnings, not errors** -- `_If_Connected` guards handle them at runtime. BUT some framework components (Command_Router, Tick_Divider) use non-guarded sends internally.
- **Command_Router's `Command_Response_T_To_Forward_Send_Count` minimum is 1** -- and `Set_Up` iterates ALL allocated forward connectors with non-guarded sends. MUST be connected (loopback to router's own `Command_Response_T_Recv_Async` if no external command source).
- **Rate_Group `Tick_T_Send_Count` must exactly match connected components** -- Rate_Group iterates ALL allocated tick send connectors with non-guarded sends.
- **Sys_Time_T_Get must be wired for EVERY component that has it** -- including Ticker! Unconnected `get` connectors cause silent task crashes at runtime (assertion failure in the task, no visible error). The assembly generator does NOT validate unconnected `get` connectors.
- **Do NOT invent connectors on framework components** -- check the component YAML. Event_Text_Logger has ONLY `Event_T_Recv_Async` (no Sys_Time_T_Get, no Tick). Product_Database has `Data_Product_T_Recv_Sync`, `Data_Product_Fetch_T_Service`, `Event_T_Send`, `Sys_Time_T_Get` (and commands if enabled).
- **Lifecycle order in main.adb**: `Start_Components` BEFORE `Set_Up_Components`. Set_Up registers commands with the router which must be running. Add a 1s delay before Start.

### Observation Infrastructure Pattern
```yaml
# Minimal event visibility: Splitter + Event_Text_Logger
  - type: Splitter
    name: Event_Splitter_Instance
    generic_types:
      - "T => Event.T"
    init_base:
      - "T_Send_Count => 1"                    # Match to downstream count
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
Wire ALL component `Event_T_Send` to `Event_Splitter_Instance.T_Recv_Sync`. Wire splitter `T_Send` index 1 to logger's `Event_T_Recv_Async`. Wire ALL `Data_Product_T_Send` to `Product_Database_Instance.Data_Product_T_Recv_Sync`. Add `Assembly_Event_To_Text` and `Assembly_Data_Products` to assembly `with:`.

## Real-World Subsystem Patterns (from linux_example)

### Parameter System Wiring
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

### Event System Chain
`Event_Splitter` -> `Event_Filter` -> `Event_Limiter` -> `Event_Packetizer`. Splitter fans out to filtered path + unfiltered post-mortem log.

### Fault System
`Fault_Correction` component maps fault IDs to corrective commands via a response table. Connect all component `Fault_T_Send` to it. **WARNING: Fault.T is NOT Event.T -- never wire Fault_T_Send to Event_T_Recv.** If no Fault_Correction is used, leave fault sends unconnected (use `_Send_If_Connected` in components).

### Assembly-Generated Constants
Assemblies auto-generate packages: `Assembly_Commands`, `Assembly_Events`, `Assembly_Data_Products` with `Number_Of_Commands`, `Minimum_Event_Id`, `Maximum_Event_Id`, etc. Use in init.

See [references/cosmos-integration.md](references/cosmos-integration.md) for COSMOS (OpenC3) ground system integration: generated config format, protocol files, plugin setup, scripting API, and Adamant-to-COSMOS type mapping.

See [references/runtime-monitoring.md](references/runtime-monitoring.md) for assembly runtime: lifecycle sequence, multi-rate scheduling, event flow architecture (dual-path), CCSDS pipeline, ground tools (Python event decoder), task watchdog, stack/queue monitoring, and practical run instructions.
