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

**CRITICAL**: Both `assembly_name/` AND `main/` need `.all_path` files. Main procedure filename must be unique across the entire build path (collisions are fatal). If sharing build roots, use a unique name like `project_main.adb` / `procedure Project_Main`.

### Required Files for Specific Components

- **Product_Packetizer** (or `Ccsds_Packetizer`): Assembly MUST have a corresponding `.product_packets.yaml` file.

## Assembly YAML Field-by-Field Reference

Every field from the schema (`gen/schemas/assembly.yaml`):

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | str | No | Human-readable description |
| `with` | str[] | No | Additional Ada `with` packages (many auto-deduced) |
| `with_adb` | str[] | No | Packages to `with` only in the `.adb` |
| `prepreamble` | str | No | Inline Ada inserted BEFORE the package spec |
| `preamble` | str | No | Inline Ada inserted AFTER the package spec |
| `subassemblies` | str[] | No | Sub-assembly files to include (see [subassemblies](../adamant-subassemblies/SKILL.md)) |
| `id_bases` | str[] | No | Assembly-wide ID base overrides |
| `components` | map[] | **Yes** | Component instances (min 1) |
| `connections` | map[] | No | Connector wiring between components |

### Component Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | str | **Yes** | Component type name |
| `name` | str | No | Instance name (auto-generated from type if omitted) |
| `description` | str | No | Role in the assembly |
| `priority` | int | **REQUIRED for active** | Task priority |
| `stack_size` | int | **REQUIRED for active** | Primary stack size (bytes) |
| `secondary_stack_size` | int | **REQUIRED for active** | Secondary stack size |
| `generic_types` | str[] | No | Generic parameter resolution |
| `discriminant` | str[] | No | Record discriminant values |
| `init_base` | str[] | No | Base init: queue size, arrayed connector counts |
| `set_id_bases` | str[] | No | Component ID base overrides (auto-assigned if omitted) |
| `init` | str[] | No | Implementation-specific init params |
| `map_data_dependencies` | map[] | No | Map data dependencies to external data products |
| `subtasks` | map[] | No | Internal subtask definitions |

**CRITICAL -- Component Naming Rules**:

1. **Component `name` MUST differ from its `type`**. Convention: append `_Instance` suffix.
2. **Use instance NAMES (not type names) in `init_base` expressions**:

```yaml
# WRONG
  init_base:
    - "Queue_Size => 5 * Rate_Group.Get_Max_Queue_Element_Size"
# CORRECT
    - "Queue_Size => 5 * Rate_Group_Instance.Get_Max_Queue_Element_Size"
```

⚠️ **Active components REQUIRE priority/stack fields**: Event_Text_Logger, Command_Router, and ANY active component MUST have `priority:`, `stack_size:`, and `secondary_stack_size:`. These are **assembly-only fields** -- never in component YAML.

⚠️ **Event_Text_Logger build path caveat**: The `event_to_text` package is auto-generated in `build/src/`. If linking fails with `"Assembly_Name_Event_To_Text" is undefined`, run `redo build/src/assembly_name_event_to_text.adb` first.

### Subtask Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | str | **Yes** | Subtask name |
| `priority` | int | **Yes** | Subtask priority |
| `stack_size` | int | **Yes** | Stack size (bytes) |
| `secondary_stack_size` | int | **Yes** | Secondary stack size |
| `disabled` | bool | No | Skip starting this subtask (default: `false`) |

### Data Dependency Mapping Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `data_dependency` | str | **Yes** | Must exactly match name from component's `.data_dependencies.yaml` |
| `data_product` | str | **Yes** | Target: `"Instance_Name.Data_Product_Name"` |
| `stale_limit_us` | int | **Yes** | Microseconds before stale (0 = never) |

### Connection Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from_component` | str | **Yes** | Source component instance name |
| `from_connector` | str | **Yes** | Source connector name |
| `from_index` | int (1–65535) | No | Array index for arrayed send connectors |
| `to_component` | str | **Yes** | Destination (or `ignore`) |
| `to_connector` | str | **Yes** | Destination connector (or `ignore`) |
| `to_index` | int (1–65535) | No | Array index for arrayed receive connectors |

## Connection Wiring Rules

### Connector Count Parameters (init_base)

Arrayed connectors require a `_Count` in `init_base` matching the number of wired connections:
```yaml
init_base:
  - "Tick_T_Send_Count => 3"        # Must wire indices 1, 2, 3
  - "Command_T_Send_Count => 16"
  - "T_Send_Count => 4"             # Splitter: 4 outputs
```

**Rule**: Count MUST exactly match connection count. Mismatches cause compile errors or runtime crashes.

### Connector Kinds

| Pattern | Usage |
|---------|-------|
| Send → Recv_Sync | Caller blocks until handler completes (same task) |
| Send → Recv_Async | Enqueued to receiver's task queue (non-blocking) |
| Get → Return | Synchronous request/response (e.g. Sys_Time) |
| Request → Service | Client/server fetch (e.g. Data_Product_Fetch) |

### Get/Return Wiring Direction

**CRITICAL**: `Get` connector is the INVOKER (from), `Return` is the INVOKEE (to). Connection flows from requester TO provider:
```yaml
  - from_component: My_Component          # Requesting time
    from_connector: Sys_Time_T_Get
    to_component: Gps_Time_Instance       # Providing time
    to_connector: Sys_Time_T_Return
```
**Many agents wire this backwards** -- double-check get/return directions.

### Sync vs Async Selection

| Pattern | When to use |
|---------|-------------|
| `Recv_Sync` | Passive components, time-critical paths |
| `Recv_Async` | Active components receiving from different task contexts |

Active components receive ticks via `Recv_Async`; passive components ticked by rate groups use `Recv_Sync`.

### Queue Type Selection

- **Standard queue** (all `recv_async` connectors same priority): `"Queue_Size => 5 * Instance.Get_Max_Queue_Element_Size"`
- **Priority queue** (different priorities on async connectors): `"Priority_Queue_Depth => 100"` (integer count, NOT size expression)

### Ignoring Unconnected Connectors

```yaml
  - from_component: Rate_Group_Instance
    from_connector: Pet_T_Send
    to_component: ignore
    to_connector: ignore
```

⚠️ **CRITICAL**: `ignore` connections must reference connectors that **actually exist**. Check [framework-components](../adamant-framework-components/SKILL.md) for connector lists. **If unsure whether a connector exists, leave it unwired** -- warnings are non-fatal; invented names are fatal.

### Generic Component Connectors

Generic components use generic parameter names, NOT instantiated type names:
```yaml
# Splitter with "T => Event.T" has T_Recv_Sync and T_Send (NOT Event_T_Recv_Sync)
  - to_component: Event_Splitter_Instance
    to_connector: T_Recv_Sync
```

## Rate Group Configuration

### Single Rate (Minimal)

```yaml
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
```

### Multi-Rate with Tick_Divider

```yaml
preamble: |
  Dividers : aliased Component.Tick_Divider.Divider_Array_Type := [1 => 1, 2 => 10, 3 => 5];
```
Divisor array: index 1 = first rate group, etc. From 5Hz base: `1` → 5Hz, `5` → 1Hz, `10` → 0.5Hz.

### Priority Strategy

```
Priority 11: Fault_Correction
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

File naming: `views/<view_name>.<assembly_name>.view.yaml`

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
```

Filter types: `component_name`, `component_type`, `component_execution`, `connector_name`, `connector_type`, `connector_kind`. Combine with `&` (AND) or `|` (OR).

Build: `redo build/svg/assembly.svg` (full) or `redo views/build/svg/<view_name>.svg`.

## Multi-Assembly Projects

Multiple independent assemblies can share the same component library under `src/assembly/`. Each gets its own directory, generated packages, and `main/` procedure. They share component source via `.all_path` markers.

For splitting a single assembly into reusable pieces, see [subassemblies](../adamant-subassemblies/SKILL.md).

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

**CRITICAL**: `Start_Components` BEFORE `Set_Up_Components`. Use `delay until` (Ravenscar). Ada procedure name MUST match filename (without `.adb`).

## Build Commands

```bash
redo build/svg/assembly.svg             # Diagram
redo all                                # Build
redo run                                # Build and run (from main/)
```

Assembly build cache: run `redo clean` in BOTH assembly dir AND main dir to regenerate.

## Critical Assembly YAML Rules

### Component Field Restrictions

- **`execution:` is NOT an assembly YAML field** -- it's defined in component YAML only.
- **Always check component YAML for init signatures** before using framework components. See [framework-components](../adamant-framework-components/SKILL.md).
- **Do NOT specify `init:` when component has no init section** -- causes `"init" does not exist` error.
- **`init: []` required when component defines init params** -- even with defaults. "Default" values in component YAML are documentation only; generated Ada has NO defaults. ALL init params must be explicitly provided.

### Connection Rules

- **Don't wire same send connector in both subassembly and parent** -- choose one location.

### Product Packets Configuration

- **Product_packets entries are dicts not strings**: Each `data_products:` entry must be `- name: Component_Instance.Data_Product_Name`.

## Framework Component Init Quick Reference

For full connector lists and details, see [framework-components](../adamant-framework-components/SKILL.md).

| Component | init | discriminant | init_base | Notes |
|-----------|------|--------------|-----------|-------|
| command_router | `Max_Number_Of_Commands => N` | -- | Queue_Size, Command_T_Send_Count, Command_Response_T_To_Forward_Send_Count | Self-loopback required |
| event_text_logger | -- | `Event_To_Text => Assembly_Event_To_Text.Event_To_Text'Access` | Queue_Size | ACTIVE, discriminant includes assembly name |
| product_database | `Minimum/Maximum_Data_Product_Id` | -- | -- | Uses `init:` NOT init_base |
| product_packetizer | `init: []` | `Packet_List => Assembly_Product_Packets.Packet_List'Access` | -- | Empty init required |
| rate_group | `Ticks_Per_Timing_Report` | -- | Queue_Size, Tick_T_Send_Count | Count MUST match connections |
| splitter (generic) | -- | -- | `T_Send_Count => N` | Type is `Splitter`, needs `generic_types` |
| ticker | -- | `Period_Us` | -- | Wire Sys_Time_T_Get |
| tick_divider | `Dividers => Dividers'Access` | -- | Tick_T_Send_Count | Preamble defines array |

⚠️ **Splitter is Generic**: Type is `Splitter` (not `Event_Splitter`). Must include `generic_types: ["T => Event.T"]`.

⚠️ **Product_Database Uses init**: `Minimum/Maximum_Data_Product_Id` go in `init:`, NOT `init_base:`.

## Assembly-Generated Packages

- `{Assembly}_Commands` -- `Number_Of_Commands`
- `{Assembly}_Events` -- `Minimum_Event_Id`, `Maximum_Event_Id`
- `{Assembly}_Data_Products` -- `Minimum/Maximum_Data_Product_Id`
- `{Assembly}_Product_Packets` -- `Packet_List`
- `{Assembly}_Event_To_Text` -- `Event_To_Text` function
- `{Assembly}_Components` -- component list for monitors

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Count mismatch | `Tick_T_Send_Count => 3` but 4 connections | Match count to actual connections |
| Missing Sys_Time | Unwired `Sys_Time_T_Get` | Wire EVERY Get → time provider. Unwired = silent crash |
| Wrong connector on generic | `Event_T_Recv_Sync` on Splitter | Use `T_Recv_Sync` (generic name) |
| Fault_T to Event_T | Different types | Leave unconnected or wire to Fault_Correction |
| Missing router self-loop | `Command_Response_T_To_Forward_Send` unwired | Wire back to router's `Command_Response_T_Recv_Async` |
| Stack too small | < 2000 bytes | Minimum 2000; typical 50000 |
| Missing map_data_dependencies | Component has data_dependencies.yaml | Every such component MUST have mapping in assembly |

## Key Pitfalls

- **`set_id_bases` is optional** -- omit for auto-assignment. Only use on components with ID-bearing features.
- **`id_bases` values must be positive** (>= 1).
- **System time provider** is `Gps_Time` (NOT `System_Time`).
- **`Ccsds_Socket_Interface`** is a TCP CLIENT -- connects TO a ground server.
- **ALL Event_T_Send** must wire to Event_Splitter. Missing = lost events.
- **ALL Data_Product_T_Send** must wire to Product_Database. Missing = lost telemetry.
- **Arrayed connector indices** must be sequential starting from 1.
- **Every component with `commands.yaml`** MUST wire `Command_T_Recv_Sync` to Command_Router.

## Running an Assembly

```bash
source /home/user/<project>/env/activate
cd src/assembly/<name>/main
redo build/bin/Linux/main.elf
./build/bin/Linux/main.elf 2>&1         # Events to stderr
```

## Style

Run `redo style` on assembly and `main/` directories. See [adamant-style](../adamant-style/SKILL.md).

## References
- [references/assembly-yaml-examples.md](references/assembly-yaml-examples.md) -- Full YAML examples
- [references/runtime-monitoring.md](references/runtime-monitoring.md) -- Running, monitoring, debugging

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Framework components**: [adamant-framework-components](../adamant-framework-components/SKILL.md)
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md)
- **Subassemblies**: [adamant-subassemblies](../adamant-subassemblies/SKILL.md)
- **COSMOS integration**: [adamant-cosmos-integration](../adamant-cosmos-integration/SKILL.md)
- **Style**: [adamant-style](../adamant-style/SKILL.md)
