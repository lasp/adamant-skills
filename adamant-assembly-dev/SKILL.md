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

**CRITICAL**: Both `assembly_name/` AND `main/` need `.all_path` files. The main procedure file name must be unique across the entire build path. If the project shares build roots with another project that has `main.adb`, use a unique name like `station_main.adb` / `procedure Station_Main`. The build system discovers source files by filename -- collisions are fatal.

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
  # Ignore (suppress warnings for intentionally unconnected sends)
  - from_component: My_Rate_Group
    from_connector: Pet_T_Send
    to_component: ignore
    to_connector: ignore
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

**CRITICAL**: `Start_Components` BEFORE `Set_Up_Components`. Use `delay until` (Ravenscar — no `delay 0.1`).
Assembly API is package-level procedures, NOT instance methods. Multiple assemblies: main procedure names must differ.

## Build Commands

```bash
redo build/svg/assembly.svg             # Diagram
redo all                                # Build
redo run                                # Build and run (from main/)
```

Assembly build cache: must `rm -rf build/` in BOTH assembly dir AND main dir to regenerate.

## Key Pitfalls (with Explanations)

- **Custom passive components: NO `init_base`** — only framework components with arrayed connectors need it (e.g., Splitter, Rate_Group). Your simple passive components don't use init_base at all.
- **Active components NEED `init_base`** with `Queue_Size` and `priority`/`stack_size` at component level.
- **`set_id_bases` is optional** — omit for auto-assignment. Don't use `"Auto"` as a value.
- **Don't put `execution:` in assembly** unless component YAML says `either`.
- **`Rate_Group` `Tick_T_Send_Count`** must EXACTLY match number of connected components.
- **`Sys_Time_T_Get` must be wired** for EVERY component that has it — silent crash if not.
- **Don't invent connectors** on framework components — check the component YAML first.
- **System time provider** is `Gps_Time` (NOT `System_Time`).
- **`Product_Database`** (NOT `Data_Product_Database`) is the built-in DP store.
- **`Command_Router` needs** `Command_Response_T_To_Forward_Send_Count >= 1`, MUST be connected.
- **Init params with defaults** still need `init:` in assembly YAML.
- **`with:` packages** must exist in build path — unknown packages silently fail. Include auto-generated packages (`{Assembly}_Event_To_Text`, `{Assembly}_Data_Products`, etc.) when referenced in discriminants or init params. Include custom type packages used in init params (e.g., `Sensor_Id`).
- **Ignoring unconnected send connectors**: Use `to_component: ignore` / `to_connector: ignore` to suppress warnings for intentionally unconnected sends (e.g., `Pet_T_Send` when no watchdog).
- **Generic component connectors** use generic parameter names, NOT instantiated type names. Splitter with `T => Event.T` has connectors `T_Recv_Sync` and `T_Send`, not `Event_T_Recv_Sync`.
- **Fault.T is NOT Event.T** — never wire `Fault_T_Send` to `Event_T_Recv`. Leave unconnected if no `Fault_Correction`.

## Multi-Rate Scheduling

```
Ticker (base rate, e.g. 5Hz/200ms)
    |
Tick_Divider [D1, D2, D3]
    ├── Rate_Group_1 (base/D1 Hz)  -- index 0 = highest priority
    ├── Rate_Group_2 (base/D2 Hz)
    └── Rate_Group_3 (base/D3 Hz)
```

- Divisors array in preamble: `Dividers : aliased Component.Tick_Divider.Divider_Array_Type := [1 => 1, 2 => 10];`
- Init: `"Dividers => Dividers'Access"`
- Lower array index = higher execution priority

### Typical Rate Assignment
| Rate | Usage |
|------|-------|
| 5Hz | Application logic, data product packetizer |
| 1Hz | Task watchdog, housekeeping |
| 0.5Hz | Event packetizer, monitors (CPU, queue, stack) |

## Task Priority Guidelines

```
Priority 11: Fault_Correction (immediate response)
Priority 10: Ticker, Watchdog_Rate_Group
Priority 9:  Application rate groups
Priority 8:  Command_Router
Priority 6:  Socket_Interface (I/O)
Priority 3:  Parameter system
Priority 1:  Event_Text_Logger, background
```

1-5 background, 6-10 normal, 11-15 high-priority RT, 16-20 critical, 21+ interrupt.

## Assembly Validation (Auto)

Generator validates: connector type/kind matching, unique instance names, array index bounds, global ID uniqueness, stack minimums (2000), priority conflicts.

## Assembly-Generated Constants

Auto-generated packages: `Assembly_Commands`, `Assembly_Events`, `Assembly_Data_Products` with `Number_Of_Commands`, `Minimum_Event_Id`, `Maximum_Event_Id`, etc.

## Event Flow Architecture (Dual-Path)

```
All Components --> Event_Splitter
                    ├── [unfiltered] Event_Post_Mortem_Logger (ALL events)
                    └── [filtered]  Event_Filter --> Event_Limiter --> Event_Packetizer
```

- Post-mortem path preserves ALL events for crash analysis
- Filtered path prevents downlink saturation
- Event_Limiter: rate-limits per event ID

## CCSDS Pipeline (Brief)

```
Downlink: Components → Event/Product_Packetizer → Ccsds_Packetizer → Socket → COSMOS
Uplink:   COSMOS → Socket → Ccsds_Command_Depacketizer → Command_Router → Components
```

CRITICAL: `Ccsds_Socket_Interface` is a TCP CLIENT — connects TO a ground server. Without a server, ground tools can't receive telemetry. For dev without COSMOS, use `Event_Text_Logger` stderr output.

## Runtime Health Monitoring

- **Task Watchdog**: Pet-based, runs on 1Hz rate group. Per-component config: limit, action (warn/fault), critical flag.
- **Stack Monitor**: Pattern-based (0xCC fill), reports percentage per task.
- **Queue Monitor**: Reports current and high-water-mark queue percentages.
- **Cycle Slip Detection**: Rate_Group checks queue depth after execution; if > 0 pending ticks, rate group is too slow.

## Connector Strategy

- **Async**: Rate groups, most data producers (can't block)
- **Sync**: Time-critical paths, command responses
- **Get**: Time service (Sys_Time), data product fetch

## Running an Assembly

```bash
# In Docker:
source /home/user/<project>/env/activate
cd src/assembly/<name>/main
redo build/bin/Linux/main.elf
./build/bin/Linux/main.elf 2>&1         # Events to stderr
./build/bin/Linux/main.elf 2>events.log &  # Background with log
```

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
```

Filter types: `component_name`, `component_type`, `component_execution`, `connector_name`, `connector_type`, `connector_kind`, etc.

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md)
- **COSMOS integration**: [adamant-cosmos-integration](../adamant-cosmos-integration/SKILL.md)
