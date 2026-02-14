---
name: adamant-assembly-dev
description: Patterns and workflows for creating assemblies and system architectures in the Adamant framework
---

# Adamant Assembly Development

An assembly instantiates components, defines connections, assigns task priorities/stack sizes, and maps IDs into an executable system.

## File Structure

```
assembly_name/
├── .all_path                              # Build path marker
├── assembly_name.assembly.yaml            # Assembly model (REQUIRED)
├── main/main.adb                          # Handwritten main program
└── views/                                 # Focused diagrams (optional)
```

## Assembly Model

```yaml
description: What this assembly does
with:
  - Start_Up
  - My_Assembly_Commands
preamble: |
  Dividers : aliased Component.Tick_Divider.Divider_Array_Type := [1 => 5, 2 => 10];

components:
  - type: component_type_name
    name: instance_name
    description: What this instance does
    execution: active|passive             # Only if component is "either"
    priority: 10                          # Active only
    stack_size: 50000
    secondary_stack_size: 10000
    generic_types:
      - "T => Event.T"
    subtasks:
      - name: Listener
        priority: 0
        stack_size: 20000
    init_base:                            # Queue size, connector counts
      - "Queue_Size => 3 * Instance_Name.Get_Max_Queue_Element_Size"
      - "Tick_T_Send_Count => 3"
    init:                                 # Implementation params
      - "Dividers => Dividers'Access"
    discriminant:
      - "Period_Us => 200000"
    set_id_bases:                         # Optional (auto-assigned if omitted)
      - "Command_Id_Base => 100"
    map_data_dependencies:
      - data_dependency: Dep_Name
        data_product: "Instance.DP_Name"
        stale_limit_us: 1000000

connections:
  # Point-to-point
  - from_component: Source
    from_connector: Data_T_Send
    to_component: Sink
    to_connector: Data_T_Recv_Sync
  # Array (indexed)
  - from_component: Router
    from_connector: Command_T_Send
    from_index: 0
    to_component: Handler
    to_connector: Command_T_Recv_Async
  # Get/return
  - from_component: My_Component
    from_connector: Sys_Time_T_Get
    to_component: System_Time_Instance
    to_connector: Sys_Time_T_Return
```

Audit connections: `bash scripts/count_connections.sh <assembly.yaml>`

## Main Program Pattern

```ada
with Ada.Real_Time; use Ada.Real_Time;
with Assembly_Name;

procedure Main is
begin
   Assembly_Name.Init_Base;
   Assembly_Name.Set_Id_Bases;
   Assembly_Name.Connect_Components;
   Assembly_Name.Init_Components;
   delay until Clock + Milliseconds (1000);
   Assembly_Name.Start_Components;      -- Active tasks FIRST
   Assembly_Name.Set_Up_Components;     -- Then register commands
   loop
      delay until Clock + Milliseconds (1000);
   end loop;
end Main;
```

**CRITICAL**: `Start_Components` BEFORE `Set_Up_Components`. Use `delay until` (Ravenscar).

## Build Commands

```bash
redo build/svg/assembly.svg             # Diagram
redo all                                # Build
redo run                                # Build and run (from main/)
```

## Key Pitfalls (One-Liners)

Details: [references/production-patterns.md](references/production-patterns.md)

- Custom passive components: NO `init_base` (only framework components with arrayed connectors need it)
- Active components NEED `init_base` with `Queue_Size` and `priority`/`stack_size`
- `set_id_bases` is optional — omit for auto-assignment, don't use `"Auto"`
- Don't put `execution:` in assembly unless component is `either`
- `Rate_Group` `Tick_T_Send_Count` must EXACTLY match connected components
- `Sys_Time_T_Get` must be wired for EVERY component that has it (silent crash if not)
- Don't invent connectors on framework components — check the component YAML
- System time provider is `Gps_Time` (NOT `System_Time`)
- `Product_Database` (NOT `Data_Product_Database`) is the built-in DP store
- Assembly API is package-level procedures, NOT instance methods
- `Command_Router` needs `Command_Response_T_To_Forward_Send_Count >= 1`, MUST be connected
- Init params with defaults still need `init:` in assembly YAML
- Multiple assemblies: main procedure names must differ
- `with:` packages must exist in build path

## Assembly Validation (Auto)

Generator validates: connector type/kind matching, unique instance names, array index bounds, global ID uniqueness, stack minimums (2000), priority conflicts.

## Task Priority Guidelines

1-5 background, 6-10 normal, 11-15 high-priority RT, 16-20 critical, 21+ interrupt.

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md)
- **COSMOS integration**: [adamant-cosmos-integration](../adamant-cosmos-integration/SKILL.md)
