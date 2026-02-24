---
name: adamant-assembly-dev
description: Patterns and workflows for creating assemblies and system architectures in the Adamant framework. Use when defining assembly YAML, wiring components, configuring rate groups, command routing, event forwarding, or building multi-assembly projects.
---

# Adamant Assembly Development

An assembly instantiates components, defines connections, assigns task priorities/stack sizes, and maps IDs into an executable system.

## File Structure

```
assembly_name/
├── .all_path                              # Build path marker (REQUIRED)
├── assembly_name.assembly.yaml            # Assembly model (REQUIRED)
├── main/
│   ├── .all_path                          # Build path marker (REQUIRED here too)
│   └── main.adb                           # MUST be named main.adb
└── views/                                 # Focused diagrams (optional)
```

**CRITICAL**: Both `assembly_name/` AND `main/` need `.all_path` files. The main procedure file name must be unique across the entire build path. If the project shares build roots with another project that has `main.adb`, use a unique name like `project_main.adb` / `procedure Project_Main`. The build system discovers source files by filename -- collisions are fatal.

### Required Files for Specific Components

When using certain framework components, the assembly MUST include additional files:

- **Product_Packetizer** (or `Ccsds_Packetizer`): Assembly MUST have a corresponding `.product_packets.yaml` file in the assembly directory. This file defines the packet structure used by the packetizer discriminant.

## Assembly YAML Field-by-Field Reference

Every field from the schema (`gen/schemas/assembly.yaml`):

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | str | No | Human-readable description of the assembly |
| `with` | str[] | No | Additional Ada `with` packages (many are auto-deduced) |
| `with_adb` | str[] | No | Packages to `with` only in the `.adb` (not `.ads`) |
| `prepreamble` | str | No | Inline Ada inserted BEFORE the package spec definition |
| `preamble` | str | No | Inline Ada inserted AFTER the package spec definition |
| `subassemblies` | str[] | No | Names of sub-assembly files to include (e.g. `core`, `comm`) |
| `id_bases` | str[] | No | Assembly-wide ID base overrides (e.g. `"event_Id_Base => 1280"`) |
| `components` | map[] | **Yes** | List of component instances (min 1) |
| `connections` | map[] | No | List of connector wiring between components |

### Component Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | str | **Yes** | Component type name (must exist in build path) |
| `name` | str | No | Instance name (auto-generated from type if omitted) |
| `description` | str | No | Role of this instance in the assembly |
| `execution` | `active`\|`passive` | Only if component is `either` | Task mode |
| `priority` | int | **REQUIRED for active** | Task priority number |
| `stack_size` | int | **REQUIRED for active** | Primary stack size in bytes |
| `secondary_stack_size` | int | **REQUIRED for active** | Secondary stack for unconstrained return types |
| `generic_types` | str[] | No | Generic parameter resolution (e.g. `"T => Event.T"`) |
| `discriminant` | str[] | No | Record discriminant values (e.g. `"Period_Us => 200000"`) |
| `init_base` | str[] | No | Base init params: queue size, arrayed connector counts |
| `set_id_bases` | str[] | No | Component ID base overrides (auto-assigned if omitted) |
| `init` | str[] | No | Implementation-specific init params |
| `map_data_dependencies` | map[] | No | Map data dependencies to external data products |
| `subtasks` | map[] | No | Internal subtask definitions |

**CRITICAL -- Component Naming Rules**:

1. **Component `name` MUST differ from its `type`**. Standard convention: append `_Instance` suffix.

```yaml
# WRONG: Component name matches type name
components:
  - type: Event_Packetizer
    name: Event_Packetizer   # COMPILE ERROR: name = type

# CORRECT: Component name differs from type
  - type: Event_Packetizer
    name: Event_Packetizer_Instance
```ada

2. **Use instance NAMES (not type names) in `init_base` expressions**:

```yaml
# WRONG: Using type name in init_base expression
  - type: Rate_Group
    name: Rate_Group_Instance
    init_base:
      - "Queue_Size => 5 * Rate_Group.Get_Max_Queue_Element_Size"   # WRONG: Rate_Group

# CORRECT: Using instance name in init_base expression
      - "Queue_Size => 5 * Rate_Group_Instance.Get_Max_Queue_Element_Size"  # CORRECT: Rate_Group_Instance
```

⚠️ **CRITICAL - Active Components REQUIRE Priority/Stack**: Event_Text_Logger, Command_Router, and ANY active component MUST have `priority:`, `stack_size:`, and `secondary_stack_size:` in the assembly YAML. Missing these fields on active components causes build failures:

```yaml
# Event_Text_Logger is ACTIVE - requires all three fields
  - type: Event_Text_Logger
    name: Event_Text_Logger_Instance
    priority: 1                          # REQUIRED
    stack_size: 50000                    # REQUIRED  
    secondary_stack_size: 10000          # REQUIRED
    discriminant:
      - "Event_To_Text => Assembly_Name_Event_To_Text.Event_To_Text'Access"
    init_base:
      - "Queue_Size => 3 * Event_Text_Logger_Instance.Get_Max_Queue_Element_Size"
```ada

⚠️ **Event_Text_Logger build path caveat**: The `event_to_text` package is auto-generated in the assembly's `build/src/`. In some build configurations (especially with subassemblies), the ELF linker step may not find this package. If you hit `"Assembly_Name_Event_To_Text" is undefined` during linking, ensure the event_to_text `.adb` is generated first by running `redo build/src/assembly_name_event_to_text.adb` from the assembly directory before the ELF build. Alternatively, omit Event_Text_Logger for test assemblies.

⚠️ **CRITICAL - Component YAML vs Assembly YAML Fields**: `priority`, `stack_size`, `secondary_stack_size` are **assembly-level fields** and must NOT appear in the `.component.yaml` file. They go in the assembly YAML component entry only. Putting these in component YAML causes build errors.

### Subtask Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | str | **Yes** | Subtask name |
| `priority` | int | **Yes** | Subtask priority |
| `stack_size` | int | **Yes** | Subtask stack size in bytes |
| `secondary_stack_size` | int | **Yes** | Subtask secondary stack size |
| `disabled` | bool | No | Set `true` to skip starting this subtask (default: `false`) |

### Data Dependency Mapping Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `data_dependency` | str | **Yes** | Component's data dependency name (**must exactly match** a name from the component's `.data_dependencies.yaml`) |
| `data_product` | str | **Yes** | Target: `"Instance_Name.Data_Product_Name"` |
| `stale_limit_us` | int | **Yes** | Microseconds before stale (0 = never stale) |

### Connection Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | str | No | What this connection is for |
| `from_component` | str | **Yes** | Source component instance name |
| `from_connector` | str | **Yes** | Source connector name |
| `from_index` | int (1–65535) | No | Array index for arrayed send connectors |
| `to_component` | str | **Yes** | Destination component instance name |
| `to_connector` | str | **Yes** | Destination connector (or `ignore`) |
| `to_index` | int (1–65535) | No | Array index for arrayed receive connectors |

## Connection Wiring Rules

### Connector Count Parameters (init_base)

Arrayed connectors require a `_Count` in `init_base` matching the number of wired connections:

```yaml
init_base:
  - "Tick_T_Send_Count => 3"        # Must wire indices 1, 2, 3
  - "Command_T_Send_Count => 16"    # Must wire indices 1 through 16
  - "T_Send_Count => 4"             # Splitter: 4 output connections
  - "Command_Response_T_To_Forward_Send_Count => 1"  # Command router forwarding
  - "Pet_T_Recv_Sync_Count => 2"    # Task_Watchdog: 2 pet inputs (to_index)
```

**Rule**: The count MUST exactly match the number of connections using that connector. Mismatches cause compile errors or runtime crashes.

### Connector Kinds

- **Send → Recv_Sync**: Caller blocks until handler completes (same task context)
- **Send → Recv_Async**: Message enqueued to receiver's task queue (non-blocking)
- **Get → Return**: Synchronous request/response (e.g. `Sys_Time_T_Get` → `Sys_Time_T_Return`)
- **Request → Service**: Client/server fetch pattern (e.g. `Data_Product_Fetch_T_Request` → `Data_Product_Fetch_T_Service`)

### Connection Direction

**CRITICAL -- Get/Return Wiring Rule**: For Get/Return pairs, the `get` connector is the **INVOKER** (from), the `return` connector is the **INVOKEE** (to). Connection flows from the requesting component TO the provider:

```yaml
# CORRECT: Component requesting time -> Time_Source providing time
connections:
  - from_component: My_Component
    from_connector: Sys_Time_T_Get
    to_component: Gps_Time_Instance
    to_connector: Sys_Time_T_Return
```ada

The component with the `Get` connector is making a request; the component with the `Return` connector is providing the response. **Many sub-agents wire this backwards** -- double-check get/return directions.

### Non-Guarded (Sync) vs Guarded (Async)

| Pattern | When to use |
|---------|-------------|
| `Recv_Sync` | Passive components, time-critical paths, command handlers on passive components |
| `Recv_Async` | Active components receiving from different task contexts, rate group ticks |

**Key**: Active components typically receive ticks via `Recv_Async` (into their queue), but passive components ticked by a rate group use `Recv_Sync` (runs on rate group's task).

### Queue Type Selection

Active components use different queue types based on their `recv_async` connectors:

- **Standard queue**: When ALL `recv_async` connectors have the SAME priority (or no priority specified):
  ```yaml
  init_base:
    - "Queue_Size => 5 * My_Component_Instance.Get_Max_Queue_Element_Size"
  ```

- **Priority queue**: When `recv_async` connectors have DIFFERENT priorities:
  ```yaml
  init_base:
    - "Priority_Queue_Depth => 100"    # Integer count, NOT size expression
  ```

**CRITICAL**: If multiple async connectors have different priorities (e.g., one priority 1, another priority 10), the component automatically uses a priority queue. Use `Priority_Queue_Depth => N` (integer count) NOT `Queue_Size => N * Get_Max_Queue_Element_Size`.

### Ignoring Unconnected Connectors

To explicitly mark send connectors as intentionally unwired, use `to_component: ignore`. This suppresses warnings and generates `*_Send_Dropped` handlers (which you implement as `is null`). Alternatively, simply leave them unwired -- the framework generates the same dropped handlers either way.

**ONLY ignore connectors you can verify exist.** If you are unsure whether a connector exists on a component, **leave it unwired** -- the generator will warn about unattached connectors (warnings are non-fatal) rather than fail on a nonexistent connector name (which IS fatal). An unwired-connector warning is always better than a build-breaking invented name.

### Generic Component Connectors

Generic components (like `Splitter`) use generic parameter names for connectors, NOT instantiated type names:
```yaml
# Splitter with "T => Event.T" has connectors T_Recv_Sync and T_Send
# NOT Event_T_Recv_Sync
  - from_component: Some_Component
    from_connector: Event_T_Send
    to_component: Event_Splitter_Instance
    to_connector: T_Recv_Sync        # Generic name, not Event_T_Recv_Sync
```

## Rate Group Configuration Patterns

### Single Rate (Minimal)

```yaml
preamble: ""   # No dividers needed
components:
  - type: Ticker
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
connections:
  - from_component: Ticker_Instance
    from_connector: Tick_T_Send
    to_component: Rate_Group_Instance
    to_connector: Tick_T_Recv_Async
```ada

### Multi-Rate with Tick_Divider

```yaml
preamble: |
  Dividers : aliased Component.Tick_Divider.Divider_Array_Type := [1 => 1, 2 => 10, 3 => 5];
```

Divisor array: index 1 = first rate group, index 2 = second, etc. From a 5Hz base:
- `1` → 5Hz (every tick), `5` → 1Hz, `10` → 0.5Hz

Tick_Divider needs: `Tick_T_Send_Count` = number of rate groups, `init: "Dividers => Dividers'Access"`.

### Priority Strategy

```
Priority 11: Fault_Correction (immediate response)
Priority 10: Ticker, Watchdog_Rate_Group
Priority 9:  Application rate groups
Priority 8:  Command_Router
Priority 6:  Socket_Interface (I/O)
Priority 3:  Parameter system
Priority 1:  Event_Text_Logger, background
```

## Event/Command Routing Patterns

- **Events**: All `Event_T_Send` → Splitter `T_Recv_Sync` → indexed `T_Send` to logger, packetizer, etc.
- **Commands**: Router `Command_T_Send` (indexed) → each commandable component. Each component's `Command_Response_T_Send` → Router `Command_Response_T_Recv_Async`. Router self-loopback (`Command_Response_T_To_Forward_Send` → own `Command_Response_T_Recv_Async`) is REQUIRED.
- **Uplink**: Socket → `Ccsds_Command_Depacketizer` → Router `Command_T_To_Route_Recv_Async`

See `references/assembly-yaml-examples.md` for concrete connection YAML.

## View Filter Patterns

Views generate focused assembly diagrams. File naming: `views/<view_name>.<assembly_name>.view.yaml`

```yaml
description: Data processing subsystem
layout: left-to-right
show_component_type: true
rule: include_component_types & exclude_connector
filters:
  - name: include_component_types
    type: component_type
    include: [Sensor_Reader, Limit_Checker, Heater_Controller]
  - name: exclude_connector
    type: connector_name
    exclude: [Sys_Time_T_Get, Sys_Time_T_Return]
```yaml

Filter types: `component_name`, `component_type`, `component_execution`, `connector_name`, `connector_type`, `connector_kind`. Combine with `&` (AND) or `|` (OR) in `rule`.

Build: `redo build/svg/assembly.svg` (full) or `redo views/build/svg/<view_name>.svg`.

## Assembly-Level Configuration Files

Beyond the main `.assembly.yaml` and `.product_packets.yaml`, assemblies can use three additional YAML files for system-level configuration.

**⚠️ Config file naming:** All config files follow the `<name>.<assembly>.<config_type>.yaml` pattern. The `<name>` prefix MUST be distinct from the assembly name and any other generated package names. Files whose names match generated-file patterns (e.g., `<assembly>_<suffix>.ads`) may be deleted by `redo clean` -- if your config YAML disappears after a clean, rename it with a more distinct prefix.

### Fault Response Table (`<name>.<assembly>.fault_responses.yaml`)

Maps faults to corrective commands. Used by the `fault_correction` framework component.

```yaml
---
description: Fault response table for the assembly.
fault_responses:
  - fault: Task_Watchdog_Instance.Rate_Group_Fault     # Component_Instance.Fault_Name
    latching: True                                      # True = fire once until cleared; False = fire every occurrence
    startup_state: enabled                              # enabled | disabled
    command_response: Command_Router_Instance.Noop_Arg  # Component_Instance.Command_Name
    command_arg: "(Value => 1)"                         # Ada aggregate for command args (optional)
    description: Execute noop with value 1 on fault.
```

Fields: `fault` (required), `latching` (required, bool), `startup_state` (required, enabled/disabled), `command_response` (required), `command_arg` (optional, Ada aggregate string), `description` (optional).

### Parameter Table (`<name>.<assembly>.parameter_table.yaml`)

Defines the parameter table layout for the `parameters` framework component.

```yaml
---
description: Parameter table for the assembly.
parameters_instance_name: Parameters_Instance     # MUST match the Parameters component instance name in assembly
parameters:
  - Oscillator_A.Frequency                         # Component_Instance.Parameter_Name
  - Oscillator_A.Amplitude
  - Oscillator_B                                   # All parameters from this component
  - [Sensor_A.Gain, Sensor_B.Gain]                 # Grouped: share one table entry (must be same type)
```

Fields: `parameters_instance_name` (required), `parameters` (required, list of strings or lists for grouped params).

**WARNING:** The `<name>` portion becomes an Ada package name. It MUST NOT collide with existing package names -- especially the assembly package itself. For assembly `ceres_fsw`, do NOT name the file `ceres_fsw.ceres_fsw.parameter_table.yaml`. Use a distinct prefix like `ceres_fsw_params.ceres_fsw.parameter_table.yaml`.

### Task Watchdog List (`<name>.<assembly>.task_watchdog_list.yaml`)

Configures the `task_watchdog` framework component's pet monitoring.

```yaml
---
description: Task watchdog configuration.
petters:
  - name: Slow_Rate_Group                          # Optional, used for fault/DP naming
    connector_name: Slow_Rate_Group.Pet_T_Send      # Component_Instance.Connector_Name
    description: Monitor slow rate group.
    limit: 3                                        # Ticks without pet before action (1-65534)
    action: error_fault                             # disabled | warn | error_fault
    critical: False                                 # True = stop HW watchdog petting on failure
    fault_id: 1                                     # Required when action = error_fault
```

Fields: `connector_name` (required), `limit` (required, 1-65534), `critical` (required, bool), `name`/`description`/`action`/`fault_id` (optional).

## Multi-Assembly Projects

A project can have multiple independent assemblies sharing the same component library. Example: a project might have `primary_assembly` (full CCSDS ground system) and `mini_assembly` (minimal standalone).

### How They Coexist

- Each assembly has its own directory under `src/assembly/`
- Each generates its own packages: `Station_Assembly_Commands`, `Mini_Assembly_Commands`, etc.
- Each has its own `main/` with a separate main procedure
- They share the same component source via build path (`.all_path` markers)
- `with:` sections reference assembly-specific generated packages

### Main Procedure Naming

If both assemblies have `main/main.adb`, filename collision occurs. Solutions:
1. Use unique names: `project_main.adb` with `procedure Project_Main`
2. Keep only one `main.adb` and exclude the other from build path

### Subassemblies

For splitting a single large assembly into reusable pieces (NOT the same as separate assemblies):
```yaml
subassemblies:
  - core        # loads core.assembly.yaml
  - comm        # loads comm.assembly.yaml
```
Subassembly files must be in the build path. Components and connections merge into the parent.

**Cross-file references work**: After merging, all components are in a flat namespace. A subassembly connection can reference a component defined in the parent or another subassembly by name. Infrastructure components (ticker, rate groups, command router, event splitter, product database) typically live in the parent; application components live in subassemblies.

**Index coordination across files**: Arrayed connectors (`Tick_T_Send[N]`, `Command_T_Send[N]`, `T_Send[N]`) use indices that span all files after merge. Plan indices up front to avoid collisions:
- Assign index ranges per subassembly (e.g., ADCS=1-4, CDH=5-8, Power=9-12)
- The parent's `*_Count` fields must equal the total across ALL subassemblies
- Document the index map in a comment at the top of each subassembly file

**id_bases**: Declared in parent only, values >= 1. Each subassembly's components get unique IDs from the parent's `id_bases` section.

**Connection scoping**: ALL connections within a subassembly MUST be in that subassembly's file. A subassembly cannot wire to sibling/parent components that don't exist yet at parse time -- but after merge, cross-references resolve. Don't wire the same send connector in both a subassembly and the parent.

For detailed subassembly patterns (nesting, reuse, state-based decomposition): see [adamant-subassemblies](../adamant-subassemblies/SKILL.md).

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
```ada

**CRITICAL**: `Start_Components` BEFORE `Set_Up_Components`. Use `delay until` (Ravenscar -- no `delay 0.1`).

**CRITICAL**: The Ada procedure name MUST match the filename (without `.adb` extension). If the file is `my_main.adb`, the procedure must be `procedure My_Main`. Ada enforces this -- a mismatch is a compile error.

## Build Commands

```bash
redo build/svg/assembly.svg             # Diagram
redo all                                # Build
redo run                                # Build and run (from main/)
```ada

Assembly build cache: run `redo clean` in BOTH assembly dir AND main dir to regenerate. **NEVER use `rm -rf build`** -- always use `redo clean`.

### Phased Assembly Integration

Build assemblies incrementally. Start with the minimum viable assembly (time source, rate groups, mission components, event pipeline), verify it compiles, then add infrastructure one component at a time:

1. **Minimal:** Gps_Time + Ticker + Rate_Groups + mission components + Event_Splitter/Limiter/Packetizer/Text_Logger + Product_Database + Command_Router
2. **+Parameters:** Add Parameters component + parameter_table.yaml
3. **+CCSDS:** Add Ccsds_Packetizer + Ccsds_Command_Depacketizer + Ccsds_Socket_Interface + product_packets.yaml
4. **+Safety:** Add Fault_Correction + Task_Watchdog + supporting config YAMLs

Each addition requires correct wiring AND supporting YAML files. Verify `redo all` passes before adding the next layer.

**Build phases**: `redo all` runs multiple phases: YAML validation, Ada code generation, compilation, and documentation generation (LaTeX/SVG). Documentation failures (configuration.ads, .tex files) do NOT mean the core assembly failed -- the assembly Ada code may compile fine. Check whether the actual `.ads/.adb` files in `build/src/` were generated before concluding the build failed.

## Common Assembly Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Count mismatch | `Tick_T_Send_Count => 3` but 4 connections wired | Match count to actual connection count |
| Missing Sys_Time | Component has `Sys_Time_T_Get` but no connection | Wire EVERY `Sys_Time_T_Get` → time provider. Unwired = silent crash, zero ticks |
| Duplicate instance name | Two components with same `name` | Use unique names |
| Wrong connector name on generic | Using `Event_T_Recv_Sync` on Splitter | Use `T_Recv_Sync` (generic param name) |
| Fault_T to Event_T | Wiring `Fault_T_Send` to `Event_T_Recv` | These are different types -- leave unconnected or wire to `Fault_Correction` |
| No `with` for generated pkg | `Station_Assembly_Commands` not in `with:` | Add to `with:` list |
| `execution:` on non-either | Setting `execution: active` when component isn't `either` | Remove `execution:` field |
| `init_base` on simple passive | Adding `init_base` to a passive component without queues | Only use `init_base` for components with arrayed connectors or queues |
| Command_Response not wired | Component has `Command_Response_T_Send` but no connection | Wire to Command_Router or `ignore` |
| Missing router self-loop | `Command_Response_T_To_Forward_Send` not connected | Wire back to router's `Command_Response_T_Recv_Async` |
| Stack too small | Stack size < 2000 bytes | Minimum is 2000; use 50000 for typical components |
| Event_Splitter count mismatch | `T_Send_Count => 3` but only 2 connections wired | T_Send_Count MUST exactly match number of T_Send connections |
| Missing map_data_dependencies | Component has data_dependencies.yaml but no mapping | Every component with data_dependencies.yaml MUST have map_data_dependencies in assembly |

## Critical Assembly YAML Rules

### Component Field Restrictions

- **`execution:` is ONLY for `either`-execution components**: Components with `execution: either` in their component YAML require `execution: active` or `execution: passive` in the assembly YAML to resolve the ambiguity. Do NOT add it for components that are already `active` or `passive` in their component model.

- **Always check framework component YAML for init signatures**: Before using a framework component, read its `.component.yaml` to see exact init parameter names, types, and whether `not_null` is set. Do NOT guess init param types -- e.g., Stack_Monitor requires `Task_Types.Task_Info_List_Access` (not `Stack_Monitor.Task_List_Type`).
- **Do NOT specify `init:` when component has no init section**: If the component YAML has no `init:` block at all, the assembly MUST NOT include `init:` or `init: []`. Adding it causes `"init" does not exist` error.
- **`init: []` required when component defines init params**: If a component's YAML defines `init:` with parameters (even ones with defaults), the assembly instantiation MUST include the `init:` key. Use `init: []` to accept all defaults, or provide explicit values. Omitting `init:` entirely causes a code generation error. Furthermore, "default" values in component YAML are documentation only -- the generated Ada code has NO default parameter values. ALL init params must be explicitly provided in the assembly YAML.

- **Rate_Group and other framework components with optional init params**: Even when all init params are optional, the `init:` key must be present. Use `init: []` or provide values like `- "Ticks_Per_Timing_Report => 10"`.

### Connection Rules

- **`to_component: ignore` is valid**: Use it to explicitly mark send connectors as intentionally unwired. Generates dropped handlers. Equivalent to leaving the connector unwired but makes intent explicit in the YAML.

- **Don't wire same send connector in both subassembly and parent**: A send connector can only connect to one target. If a subassembly already wires a component's send connector internally, the parent cannot wire it again. Choose one location for the connection.

### Product Packets Configuration

- **Product_packets schema**: Each packet entry REQUIRES `name`, `id` (int), `period` (string, e.g., `"1"`), and `data_products` (list). Missing `period` causes schema validation failure. Each `data_products` entry is a dict with `name: Component_Instance.Data_Product_Name`. Optional packet fields: `enabled` (True/False/On_Change -- default True), `offset` (string, stagger ticks to distribute load), `use_tick_timestamp` (bool). Optional DP fields: `use_timestamp` (bool, use this DP's timestamp as packet timestamp), `include_timestamp` (bool, embed DP timestamp in packet), `event_on_missing` (bool), `pad_bytes` (int, insert spacing).

## Framework Component Init Requirements

Common framework components and their REQUIRED configuration in assembly YAML:

| Component | init | discriminant | init_base | Notes |
|-----------|------|--------------|-----------|-------|
| command_router | `Max_Number_Of_Commands => N` | -- | Queue_Size | Self-loopback required (from_index: 1) |
| event_packetizer | `Num_Internal_Packets => N`, `Partial_Packet_Timeout => T` | -- | -- | NO init_base |
| event_text_logger | -- | `Event_To_Text => Assembly_Name_Event_To_Text.Event_To_Text'Access` | Queue_Size, priority, stack_size, secondary_stack_size | ACTIVE component, requires discriminant |
| product_database | `Minimum_Data_Product_Id => M`, `Maximum_Data_Product_Id => N` | -- | -- | Use `init:` (NOT init_base) |
| product_packetizer | `init: []` (empty) | `Packet_List => My_Assembly_Product_Packets.Packet_List'Access` | Queue_Size | Has `Command_T_Recv_Async` -- needs Queue_Size even though passive |
| ticker | -- | -- | -- | Wire Sys_Time_T_Get (easy to forget) |
| rate_group | -- | -- | Queue_Size | Arrayed Tick_T_Send: count MUST match connections |
| tick_divider | `Dividers => Dividers'Access` | -- | -- | Preamble defines Divider_Array_Type |
| splitter (generic) | -- | -- | `T_Send_Count => N` | Component type is `Splitter`, requires `generic_types: ["T => Event.T"]` |

⚠️ **CRITICAL - Event_Text_Logger Discriminant**: Event_Text_Logger requires a discriminant that includes the assembly name:

```yaml
discriminant:
  - "Event_To_Text => Assembly_Name_Event_To_Text.Event_To_Text'Access"
```ada

⚠️ **CRITICAL - Splitter is Generic**: The component type is `Splitter` (not `Event_Splitter`). Must include `generic_types: ["T => Event.T"]` in the assembly YAML:

```yaml
components:
  - type: Splitter
    name: Event_Splitter_Instance
    generic_types: ["T => Event.T"]
    init_base:
      - "T_Send_Count => 3"
```

⚠️ **CRITICAL - Product_Database Uses init**: `Minimum_Data_Product_Id` and `Maximum_Data_Product_Id` go in `init:`, NOT `init_base:`

```yaml
# CORRECT
  - type: Product_Database  
    name: Product_Database_Instance
    init:
      - "Minimum_Data_Product_Id => My_Assembly_Data_Products.Minimum_Data_Product_Id"
      - "Maximum_Data_Product_Id => My_Assembly_Data_Products.Maximum_Data_Product_Id"
      # ^^^ Replace My_Assembly with YOUR assembly name (e.g., Enceladus_Assembly_Data_Products)

# WRONG
    init_base:
      - "Minimum_Data_Product_Id => ..."
```ada

## Assembly-Generated Packages

Auto-generated from the assembly model:
- `{Assembly}_Commands` -- `Number_Of_Commands`
- `{Assembly}_Events` -- `Minimum_Event_Id`, `Maximum_Event_Id`
- `{Assembly}_Data_Products` -- `Minimum_Data_Product_Id`, `Maximum_Data_Product_Id`
- `{Assembly}_Product_Packets` -- `Packet_List` (for Product_Packetizer discriminant)
- `{Assembly}_Event_To_Text` -- `Event_To_Text` function (for Event_Text_Logger)
- `{Assembly}_Components` -- component list for monitors

## Key Pitfalls

- **`set_id_bases` is optional** -- omit for auto-assignment. Don't use `"Auto"` as a value.
- **Only use `set_id_bases` on components that HAVE ID-bearing features** (commands, events, data products, faults, packets). Components like `Gps_Time` that only provide/return data have no IDs and will error if `set_id_bases` is specified.
- **`id_bases` values must be positive** (>= 1). Using 0 causes a code generation error.
- **Only include used `id_bases`**: Valid bases are `Data_Product_Id_Base`, `Event_Id_Base`, `Command_Id_Base`, `Packet_Id_Base`. Including unused bases (e.g., `Fault_Id_Base`) triggers a warning.
- **`Rate_Group` `Tick_T_Send_Count`** must EXACTLY match connected component count.
- **System time provider** is `Gps_Time` (NOT `System_Time`). Instance name is conventional.
- **`Product_Database`** uses `init:` (NOT `init_base:`) for Min/Max Data Product ID.
- **`Command_Router` needs** `Command_Response_T_To_Forward_Send_Count >= 1`.
- **`with:` packages** must exist in build path -- unknown packages silently fail.
- **`Ccsds_Socket_Interface`** is a TCP CLIENT -- connects TO a ground server.
- **ALL Event_T_Send** connectors must wire to Event_Splitter (or directly to Event_Packetizer). Missing = lost events.
- **ALL Data_Product_T_Send** connectors must wire to Product_Database. Missing = lost telemetry.
- **Arrayed connector indices** must be sequential starting from 1. `Tick_T_Send_Count => 3` needs exactly indices 1, 2, 3.
- **Every component with `commands.yaml`** MUST have its `Command_T_Recv_Sync` wired to the Command_Router. `Command_T_Send_Count` must include ALL commandable components. Missing wiring = commands never registered.
- **`map_data_dependencies.data_dependency`** must exactly match a name defined in the component's `.data_dependencies.yaml`. Do not rename or paraphrase -- copy it verbatim.
- **Data dependencies require matching sources**: Every `map_data_dependencies` entry maps to a `component_name.data_product_name` that MUST exist as a real data product produced by another component in the assembly. Plan the full telemetry data flow before designing data dependency interfaces -- if no component produces the needed DP, the assembly will fail to build.
- **Event_Text_Logger discriminant** must include assembly name: `Assembly_Name_Event_To_Text.Event_To_Text'Access`.
- **Splitter component type** is `Splitter` (not `Event_Splitter`) and requires `generic_types: ["T => Event.T"]`.
- **Active components** (Event_Text_Logger, Command_Router) MUST have priority, stack_size, secondary_stack_size.
- **Component YAML cannot contain** `priority`, `stack_size`, `secondary_stack_size` -- these are assembly-only fields.

## Assembly Wiring Checklist

Before building, verify every component has ALL required connections:

1. **Every component** → `Sys_Time_T_Get` wired to time provider (if component has that connector)
2. **Every `Event_T_Send`** → Event_Splitter `T_Recv_Sync` (index N)
3. **Every `Data_Product_T_Send`** → Product_Database `Data_Product_T_Recv_Sync`
4. **Every `Command_T_Recv_Sync`** → Command_Router `Command_T_Send` (index N)
5. **Every `Command_Response_T_Send`** → Command_Router `Command_Response_T_Recv_Async`
6. **Every `Fault_T_Send`** → Fault_Correction (or `to_component: ignore`)
7. **Arrayed send counts** (`Tick_T_Send_Count`, `T_Send_Count`, `Command_T_Send_Count`) match EXACTLY the number of wired connections
8. **Active components** have `priority`, `stack_size`, `secondary_stack_size`
9. **Passive components with `recv_async`** (Product_Packetizer, Limiter) have `init_base: Queue_Size`
10. **Command_Router self-loop**: `Command_Response_T_To_Forward_Send` → own `Command_Response_T_Recv_Async`

## Running an Assembly

```bash
# In Docker:
source /home/user/<project>/env/activate
cd src/assembly/<name>/main
redo build/bin/Linux/main.elf
./build/bin/Linux/main.elf 2>&1         # Events to stderr
```

## Style

Run `redo style` on the assembly directory and `main/` before finalizing. Assembly YAML `with:` sections ARE correct (unlike component YAML where it's preamble-only). See [adamant-style](../adamant-style/SKILL.md).

## References
- [references/assembly-yaml-examples.md](references/assembly-yaml-examples.md) -- Full YAML examples for assemblies
- [references/cosmos-integration.md](references/cosmos-integration.md) -- Assembly-level COSMOS wiring patterns
- [references/production-patterns.md](references/production-patterns.md) -- Production assembly patterns and best practices
- [references/runtime-monitoring.md](references/runtime-monitoring.md) -- Running, monitoring, and debugging assemblies

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md)
- **Style**: [adamant-style](../adamant-style/SKILL.md)
- **COSMOS integration**: [adamant-cosmos-integration](../adamant-cosmos-integration/SKILL.md)
