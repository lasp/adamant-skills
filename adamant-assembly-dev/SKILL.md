---
name: adamant-assembly-dev
description: Patterns and workflows for creating assemblies and system architectures in the Adamant framework
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

**CRITICAL**: Both `assembly_name/` AND `main/` need `.all_path` files. The main procedure file name must be unique across the entire build path. If the project shares build roots with another project that has `main.adb`, use a unique name like `station_main.adb` / `procedure Station_Main`. The build system discovers source files by filename — collisions are fatal.

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
| `priority` | int | Active only | Task priority number |
| `stack_size` | int | Active only | Primary stack size in bytes |
| `secondary_stack_size` | int | Active only | Secondary stack for unconstrained return types |
| `generic_types` | str[] | No | Generic parameter resolution (e.g. `"T => Event.T"`) |
| `discriminant` | str[] | No | Record discriminant values (e.g. `"Period_Us => 200000"`) |
| `init_base` | str[] | No | Base init params: queue size, arrayed connector counts |
| `set_id_bases` | str[] | No | Component ID base overrides (auto-assigned if omitted) |
| `init` | str[] | No | Implementation-specific init params |
| `map_data_dependencies` | map[] | No | Map data dependencies to external data products |
| `subtasks` | map[] | No | Internal subtask definitions |

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
| `data_dependency` | str | **Yes** | Component's data dependency name |
| `data_product` | str | **Yes** | Target: `"Instance_Name.Data_Product_Name"` |
| `stale_limit_us` | int | **Yes** | Microseconds before stale (0 = never stale) |

### Connection Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | str | No | What this connection is for |
| `from_component` | str | **Yes** | Source component instance name |
| `from_connector` | str | **Yes** | Source connector name |
| `from_index` | int (1–65535) | No | Array index for arrayed send connectors |
| `to_component` | str | **Yes** | Destination component (or `ignore`) |
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

### Non-Guarded (Sync) vs Guarded (Async)

| Pattern | When to use |
|---------|-------------|
| `Recv_Sync` | Passive components, time-critical paths, command handlers on passive components |
| `Recv_Async` | Active components receiving from different task contexts, rate group ticks |

**Key**: Active components typically receive ticks via `Recv_Async` (into their queue), but passive components ticked by a rate group use `Recv_Sync` (runs on rate group's task).

### Ignoring Unconnected Connectors

Suppress warnings for intentionally unconnected send connectors:
```yaml
  - from_component: Rate_Group_Instance
    from_connector: Pet_T_Send
    to_component: ignore
    to_connector: ignore
```

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
```

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
```

Filter types: `component_name`, `component_type`, `component_execution`, `connector_name`, `connector_type`, `connector_kind`. Combine with `&` (AND) or `|` (OR) in `rule`.

Build: `redo build/svg/assembly.svg` (full) or `redo views/build/svg/<view_name>.svg`.

## Multi-Assembly Projects

A project can have multiple independent assemblies sharing the same component library. Example: `adamant_bot_station` has `station_assembly` (full CCSDS ground system) and `mini_assembly` (minimal standalone).

### How They Coexist

- Each assembly has its own directory under `src/assembly/`
- Each generates its own packages: `Station_Assembly_Commands`, `Mini_Assembly_Commands`, etc.
- Each has its own `main/` with a separate main procedure
- They share the same component source via build path (`.all_path` markers)
- `with:` sections reference assembly-specific generated packages

### Main Procedure Naming

If both assemblies have `main/main.adb`, filename collision occurs. Solutions:
1. Use unique names: `station_main.adb` with `procedure Station_Main`
2. Keep only one `main.adb` and exclude the other from build path

### Subassemblies

For splitting a single large assembly into reusable pieces (NOT the same as separate assemblies):
```yaml
subassemblies:
  - core        # loads core.assembly.yaml
  - comm        # loads comm.assembly.yaml
```
Subassembly files must be in the build path. Components and connections merge into the parent.

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

**CRITICAL**: `Start_Components` BEFORE `Set_Up_Components`. Use `delay until` (Ravenscar — no `delay 0.1`).

## Build Commands

```bash
redo build/svg/assembly.svg             # Diagram
redo all                                # Build
redo run                                # Build and run (from main/)
```

Assembly build cache: run `redo clean` in BOTH assembly dir AND main dir to regenerate.

## Common Assembly Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Count mismatch | `Tick_T_Send_Count => 3` but 4 connections wired | Match count to actual connection count |
| Missing Sys_Time | Component has `Sys_Time_T_Get` but no connection | Wire EVERY `Sys_Time_T_Get` → time provider. Unwired = silent crash, zero ticks |
| Duplicate instance name | Two components with same `name` | Use unique names |
| Wrong connector name on generic | Using `Event_T_Recv_Sync` on Splitter | Use `T_Recv_Sync` (generic param name) |
| Fault_T to Event_T | Wiring `Fault_T_Send` to `Event_T_Recv` | These are different types — leave unconnected or wire to `Fault_Correction` |
| No `with` for generated pkg | `Station_Assembly_Commands` not in `with:` | Add to `with:` list |
| `execution:` on non-either | Setting `execution: active` when component isn't `either` | Remove `execution:` field |
| `init_base` on simple passive | Adding `init_base` to a passive component without queues | Only use `init_base` for components with arrayed connectors or queues |
| Command_Response not wired | Component has `Command_Response_T_Send` but no connection | Wire to Command_Router or `ignore` |
| Missing router self-loop | `Command_Response_T_To_Forward_Send` not connected | Wire back to router's `Command_Response_T_Recv_Async` |
| Stack too small | Stack size < 2000 bytes | Minimum is 2000; use 50000 for typical components |

## Framework Component Init Requirements

Common framework components and their REQUIRED configuration in assembly YAML:

| Component | init | discriminant | init_base | Notes |
|-----------|------|--------------|-----------|-------|
| command_router | `Max_Number_Of_Commands => N` | -- | Queue_Size | Self-loopback required (from_index: 1) |
| event_packetizer | `Num_Internal_Packets => N`, `Partial_Packet_Timeout => T` | -- | -- | NO init_base |
| event_text_logger | -- | `Event_To_Text => Assembly_Event_To_Text.Event_To_Text'Access` | Queue_Size | NO Sys_Time_T_Get |
| product_database | `Minimum_Data_Product_Id => M`, `Maximum_Data_Product_Id => N` | -- | -- | IDs from assembly-generated package |
| product_packetizer | `init: []` (empty) | `Packet_List => Assembly_Product_Packets.Packet_List'Access` | -- | Empty init required even when all params optional |
| ticker | -- | -- | -- | Wire Sys_Time_T_Get (easy to forget) |
| rate_group | -- | -- | Queue_Size | Arrayed Tick_T_Send: count MUST match connections |
| tick_divider | -- | `Divider_List => Dividers'Access` | -- | Preamble defines Divider_Array_Type |
| splitter (generic) | -- | -- | -- | Use `T_Recv_Sync` not `Event_T_Recv_Sync` |

## Assembly-Generated Packages

Auto-generated from the assembly model:
- `{Assembly}_Commands` — `Number_Of_Commands`
- `{Assembly}_Events` — `Minimum_Event_Id`, `Maximum_Event_Id`
- `{Assembly}_Data_Products` — `Minimum_Data_Product_Id`, `Maximum_Data_Product_Id`
- `{Assembly}_Product_Packets` — `Packet_List` (for Product_Packetizer discriminant)
- `{Assembly}_Event_To_Text` — `Event_To_Text` function (for Event_Text_Logger)
- `{Assembly}_Components` — component list for monitors

## Key Pitfalls

- **`set_id_bases` is optional** — omit for auto-assignment. Don't use `"Auto"` as a value.
- **`Rate_Group` `Tick_T_Send_Count`** must EXACTLY match connected component count.
- **System time provider** is `Gps_Time` (NOT `System_Time`). Instance name is conventional.
- **`Product_Database`** (NOT `Data_Product_Database`) is the built-in DP store.
- **`Command_Router` needs** `Command_Response_T_To_Forward_Send_Count >= 1`.
- **`with:` packages** must exist in build path — unknown packages silently fail.
- **`Ccsds_Socket_Interface`** is a TCP CLIENT — connects TO a ground server.
- **ALL Event_T_Send** connectors must wire to Event_Splitter (or directly to Event_Packetizer). Missing = lost events.
- **ALL Data_Product_T_Send** connectors must wire to Product_Database. Missing = lost telemetry.
- **Arrayed connector indices** must be sequential starting from 1. `Tick_T_Send_Count => 3` needs exactly indices 1, 2, 3.

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

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md)
- **Style**: [adamant-style](../adamant-style/SKILL.md)
- **COSMOS integration**: [adamant-cosmos-integration](../adamant-cosmos-integration/SKILL.md)
