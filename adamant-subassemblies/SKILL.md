---
name: adamant-subassemblies
description: Splitting large Adamant assemblies into reusable subassemblies. Use when decomposing a monolithic assembly YAML, creating shared component groups, or managing multi-assembly projects with common subsystems.
---

# Adamant Subassemblies

Subassemblies split a large assembly YAML into smaller, reusable pieces. Each subassembly is a standard `.assembly.yaml` file that gets merged into a parent assembly at model load time.

<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->

## When to Use Subassemblies

- **Large assemblies** (50+ components) that are hard to navigate as a single file
- **Reuse** -- share a common subsystem (e.g., telemetry pipeline, command routing) across multiple assemblies
- **Team workflow** -- different engineers own different subsystems in separate files
- **Incremental integration** -- build and validate subsystems independently before combining

Subassemblies are a **modeling construct** for breaking assemblies into manageable pieces. Per the user guide: "subassemblies are purely a modeling concept. A subassembly is not reflected in any of the output products including the autocode." Subassembly content is flattened into the parent assembly -- the generated code, IDs, and binary are identical whether you define everything in one file or split across multiple subassembly files. There is no difference in output products. Subassemblies aid design and separation of concerns at the model level only. The parent assembly's `with:` list must reference the TOP-LEVEL assembly's generated packages (e.g., `Parent_Assembly_Commands`, `Parent_Assembly_Event_To_Text`), NOT per-subassembly ones. Components in subassemblies get their IDs from the parent assembly's ID allocation.

**Key properties:**
- Allow sharing component groups between different build targets (e.g., a common telemetry pipeline used by multiple assemblies)
- Enable state-based decomposition (idle, safe, monitor, etc.) where a master flight assembly includes all states
- All connections within a subassembly are self-contained in that subassembly's file
- Cross-subassembly wiring goes in the parent (or importing) assembly

## File Structure

Two patterns work. Both require `.all_path` in every directory containing YAML files.

### Pattern 1: Co-located (most common in real projects)

Subassembly YAML files live in the SAME directory as the parent assembly. This is how ceres_fsw, titan_fsw, and bot_station organize their subassemblies. The parent directory's `.all_path` covers all files.

```
src/assembly/
├── my_assembly/
│   ├── .all_path                    # Covers ALL yaml in this dir
│   ├── my_assembly.assembly.yaml    # Parent assembly
│   ├── core.assembly.yaml           # Subassembly: co-located with parent
│   ├── comm.assembly.yaml           # Subassembly: co-located with parent
│   └── main/
│       ├── .all_path
│       └── main.adb
```

### Pattern 2: Separate directories

Subassembly YAML files live in sibling directories. Each directory MUST have its own `.all_path` -- without it, the model loader cannot find the subassembly and you get: `Could not load model for subassembly 'core'. Make sure the model exists in the path.`

```
src/assembly/
├── my_assembly/
│   ├── .all_path
│   ├── my_assembly.assembly.yaml    # Parent assembly
│   └── main/
│       ├── .all_path
│       └── main.adb
├── core/
│   ├── .all_path                    # REQUIRED -- without this, core is invisible
│   └── core.assembly.yaml
├── comm/
│   ├── .all_path                    # REQUIRED
│   └── comm.assembly.yaml
└── gnc/
    ├── .all_path                    # REQUIRED
    └── gnc.assembly.yaml
```

**Verified:** The model loader calls `model_loader.try_load_model_by_name(name, "assembly")` which searches the model database built from `.all_path`-marked directories (`redo/database/_setup.py:105`). Location relative to the parent does not matter -- only `.all_path` presence. Source: T4-S1 hypothesis testing, confirmed by Docker builds.

## Parent Assembly YAML

Reference subassemblies with the `subassemblies:` field:

```yaml
description: Full flight software assembly
subassemblies:
  - core
  - comm
  - gnc

# Parent can also define its own components, connections, preamble, etc.
# These merge WITH (not replace) the subassembly contents.
components:
  - type: Watchdog
    priority: 11
    stack_size: 50000
    secondary_stack_size: 10000

connections:
  # Cross-subassembly wiring goes here
  - from_component: Telemetry_Router_Instance
    from_connector: Packet_T_Send
    from_index: 3
    to_component: Gnc_Packetizer_Instance
    to_connector: Packet_T_Recv_Async
```

Each entry in `subassemblies:` is a **name**, not a filename. The entry `core` loads `core.assembly.yaml` from the build path.

## Subassembly YAML

⚠️ **CRITICAL: There is NO `is_subassembly` field.** The subassembly YAML schema is IDENTICAL to a regular assembly YAML. Subassembly status is determined entirely by the parent's `subassemblies:` list -- it is NOT declared with any field inside the subassembly file itself. Do NOT add `is_subassembly: True` or any similar field -- it does not exist in the schema and will cause an immediate validation error:
```
Key 'is_subassembly' was not defined. Path: ''
```

A subassembly is a normal assembly YAML file. It uses the same schema:

```yaml
# core.assembly.yaml
description: Core infrastructure subsystem

preamble: |
  Dividers : aliased Component.Tick_Divider.Divider_Array_Type := [1 => 1, 2 => 5];

id_bases:
  - "Event_Id_Base => 1"

components:
  - type: Ticker
    priority: 10
    stack_size: 50000
    secondary_stack_size: 10000
    discriminant:
      - "Period_Us => 200000"

  - type: Rate_Group
    name: Core_Rate_Group_Instance
    priority: 9
    stack_size: 50000
    secondary_stack_size: 10000
    init_base:
      - "Queue_Size => 3 * Core_Rate_Group_Instance.Get_Max_Queue_Element_Size"
      - "Tick_T_Send_Count => 2"

connections:
  - from_component: Ticker_Instance
    from_connector: Tick_T_Send
    to_component: Core_Rate_Group_Instance
    to_connector: Tick_T_Recv_Async
```ada

## How Merging Works

When the parent assembly loads, each subassembly is loaded and its contents merge into the parent in this order:

| What | Merge behavior |
|------|---------------|
| `components` | All subassembly components added to parent. **Duplicate names = fatal error.** |
| `connections` | All subassembly connections appended to parent's connection list. |
| `with` (includes) | Subassembly includes extend the parent's include list. |
| `preamble` | Subassembly preambles **prepend** to parent preamble (subassembly code appears first). |
| `prepreamble` | Same as preamble -- subassembly prepreambles prepend. |
| `id_bases` | Merged into parent. **Duplicate id_base names = fatal error.** |
| Submodel files | Extended from subassemblies into parent. |

**Load order matters for preamble**: subassemblies are processed in the order listed, and their preamble content appears before the parent's own preamble in the generated Ada.

## Build Path Requirements

Subassembly `.assembly.yaml` files must be discoverable in the build path. Each subassembly needs:

1. **Its own directory** with an `.all_path` marker (required -- do NOT co-locate with the parent)
2. Or a **shared location** in a common library directory (for cross-project reuse), still in its own directory

The model loader calls `model_loader.try_load_model_by_name(name, "assembly")` to find subassembly files. If the file isn't in any build path directory, you get:

```
Could not load model for subassembly 'core'. Make sure the model exists in the path.
```

## ID Base Management

⚠️ **CRITICAL CONSTRAINT**: ID base keys must be **globally unique**. The same key name (e.g., `Event_Id_Base`) CANNOT appear in multiple subassemblies. This means you cannot give each subassembly its own `Event_Id_Base`.

**Primary pattern**: Omit `id_bases` entirely and let auto-assignment handle it. Use `set_id_bases` on individual components when you need specific values (e.g., `set_id_bases: ["Packet_Id_Base => 98"]` on Event_Packetizer).

**If you need explicit id_bases**: Define them in the parent assembly only. Do NOT define id_bases in subassemblies -- duplicate key names across files cause fatal errors. Values must be positive (>= 1, NOT 0).

```yaml
# WRONG: Same id_base key in multiple subassemblies
# core.assembly.yaml
id_bases:
  - "Event_Id_Base => 1"        # FATAL ERROR: duplicate key

# comm.assembly.yaml  
id_bases:
  - "Event_Id_Base => 500"      # FATAL ERROR: duplicate key

# CORRECT: Omit id_bases (auto-assignment) with per-component overrides
# safe_mode.assembly.yaml
components:
  - type: Ccsds_Event_Packetizer
    name: Event_Packetizer_Instance
    set_id_bases: ["Packet_Id_Base => 98"]   # Override specific component

# ALSO CORRECT: All id_bases in parent only
# parent.assembly.yaml
id_bases:
  - "Event_Id_Base => 1"
  - "Command_Id_Base => 1"

subassemblies:
  - core
  - comm
  - gnc
```ada

**Rules:**
- Each id_base name must end with `_Id_Base` (e.g., `Event_Id_Base`, `Command_Id_Base`)
- Values must be positive integers
- **ID base keys must be globally unique** across ALL subassemblies and the parent
- If you need assembly-wide id_bases, define them in the parent assembly ONLY
- Subassemblies should NOT contain `id_bases:` sections

**Strategy:** Plan ID ranges at the parent level and document the allocation in comments. Component IDs will be auto-assigned sequentially starting from the base values.

## Connection Scoping Rules

⚠️ **CRITICAL**: Each subassembly must be able to act as a standalone assembly. Connections defined in a subassembly can ONLY reference components defined in that subassembly (or its own nested subassemblies). A subassembly CANNOT wire to components in a sibling subassembly or the parent.

**Where connections go:**

1. **Intra-subassembly connections** go in the subassembly file (wiring between components within the same subassembly)
2. **Cross-subassembly connections** go in the parent assembly (wiring between components in different subassemblies, or between parent components and subassembly components)

**Rule for Event_T_Send and Data_Product_T_Send (bus fan-in):** These connect every component to a central hub (Event_Splitter or Product_Database). If the source component and the hub destination are in DIFFERENT subassemblies, the connection MUST go in the parent assembly. In practice, since Event_Splitter and Product_Database receive inputs from ALL subassemblies, ALL Event_T_Send and Data_Product_T_Send connections belong in the parent assembly (or the subassembly that contains both the source AND the hub). The clearest design: put Event_Splitter and Product_Database in the PARENT assembly alongside the rate groups and system time, then wire everything there.

Since all components merge into a single namespace at the parent level, the parent's connections can reference any component regardless of which subassembly defined it:

```yaml
# Parent assembly connections -- wiring between subsystems
connections:
  # Core rate group ticks a GNC component
  - from_component: Core_Rate_Group_Instance    # defined in core.assembly.yaml
    from_connector: Tick_T_Send
    from_index: 2
    to_component: Nav_Filter_Instance            # defined in gnc.assembly.yaml
    to_connector: Tick_T_Recv_Async

  # Comm sends commands to GNC
  - from_component: Command_Router_Instance      # defined in comm.assembly.yaml
    from_connector: Command_T_Send
    from_index: 5
    to_component: Nav_Filter_Instance            # defined in gnc.assembly.yaml
    to_connector: Command_T_Recv_Async
```ada

**Rule:** Intra-subsystem connections MUST be in the subassembly file. Inter-subsystem connections MUST be in the parent. This is not just best practice -- the model loader enforces that subassembly connections only reference components within that subassembly.

⚠️ **CRITICAL - Cross-Subassembly Data Dependencies**: If a component in subassembly A has data dependencies that need to map to data products from components in subassembly B, the `map_data_dependencies` resolver CANNOT find them. The mapper only searches at the subassembly level, not across subassemblies.

**SOLUTIONS** (in order of preference):
1. Move the component with data dependencies to the PARENT assembly (gives mapper full visibility)
2. Move the data product SOURCE component to the same subassembly as the consumer
3. Do NOT remove data dependencies to work around this -- they are a core feature. Restructure the subassembly instead.

## View System Interaction

Views work on the **merged** (flattened) assembly. When generating views:

- The view model receives all components and connections from all subassemblies
- Subassembly boundaries are not visible in views -- components appear as if they were all in one file
- Filter by `component_name` or `component_type` to create subsystem-focused views
- The view system internally clears the `subassemblies` field to avoid reloading during view construction

To create a view showing only one subassembly's components, use a component name or type filter that matches the components from that subassembly.

## Limitations and Gotchas

### Deep Nesting (3+ levels) and event_to_text
Nesting is structurally supported but deeply nested assemblies (3+ levels) can trigger `event_to_text` code generation failures -- the generated event-to-text function may reference undefined packages or produce `None` values. The assembly YAML and wiring are correct; it's a code generator limitation. **Recommendation:** Limit nesting to 2 levels (parent + subassembly) for production use. If 3+ levels are needed, avoid Event_Text_Logger and be prepared to work around event_to_text compilation errors.

### Subassembly _components.ads Missing With Clauses
The code generator produces a `<subassembly>_components.ads` file for each subassembly, but the `with` clause population (`components_ads_includes`) is gated behind `if not self.is_subassembly:` in `gen/models/assembly.py` (L768). This means the subassembly's `_components.ads` is generated with NO component `with` clauses (the list stays empty).

**Why it usually works:** The parent's `_components.ads` includes all component packages from all subassemblies. The final binary compiles through the parent, so the subassembly's empty `_components.ads` is harmless -- **as long as it doesn't end up in the parent's build directory**.

**When it fails:** If the subassembly YAML is **co-located with the parent** (same directory), the subassembly's generated `_components.ads` lands in the parent's `build/src/` and the compiler tries to compile it, producing `"Component" is undefined` errors on every component instance declaration.

**Fix:** Put each subassembly in its **own directory** with its own `.all_path` marker. This ensures the subassembly's generated files go to a separate `build/` directory that is not compiled as part of the parent assembly. See the File Structure section above. **Never co-locate subassembly YAML with the parent assembly YAML.**

### Duplicate Component Names
Component instance names must be unique across ALL subassemblies and the parent. If `core.assembly.yaml` and `comm.assembly.yaml` both define a component named `Rate_Group_Instance`, you get:

```
Duplicate component 'Rate_Group_Instance' not allowed. Found in files: [...]
```ada

**Fix:** Use distinct names like `Core_Rate_Group_Instance` and `Comm_Rate_Group_Instance`.

### Duplicate ID Bases
⚠️ **CRITICAL**: The same `id_base` key cannot appear in multiple subassemblies:

```
Duplicate id_base 'Event_Id_Base' found in comm.assembly.yaml.
```ada

**Fix:** Define ALL id_bases in the parent assembly only. Do NOT use id_bases in subassemblies.

### Subassembly Connections
Subassemblies SHOULD define internal connections when components within the subassembly need to be wired together (e.g., Ticker -> Tick_Divider -> Rate_Group, CCSDS pipeline, event routing chains). This makes the subassembly self-contained and reusable.

If a subassembly has NO internal connections (all wiring is cross-subassembly and goes in the parent), omit the `connections:` key entirely. A `connections:` key with only comments (no actual entries) causes `TypeError: 'NoneType' object is not iterable`.

```yaml
# WRONG: Empty connections field
connections:
  # No actual connections, just comments

# CORRECT for subassembly with internal wiring:
connections:
  - from_component: Ticker_Instance
    from_connector: Tick_T_Send
    to_component: Rate_Group_Instance
    to_connector: Tick_T_Recv_Async

# CORRECT for subassembly with no internal wiring:
# (simply omit the connections: key)
description: Sensor subsystem
components:
  - type: Sensor_Reader
    # ...
```ada

### Parent With No Components
A parent assembly can omit `components:` entirely when ALL components live in subassemblies. The parent then contains only `subassemblies:`, `with:`, and `connections:` (cross-subassembly wiring):

```yaml
# Parent with no direct components
description: Full assembly
with:
  - Assembly_Commands
subassemblies:
  - path: safe_mode.assembly.yaml    # Foundation -- all infrastructure
  - path: nominal.assembly.yaml      # Application components
  - path: degraded.assembly.yaml     # Active observation + GNC
connections:
  # Cross-subassembly wiring only
  - from_component: Command_Router_Instance   # in safe_mode
    from_connector: Command_T_Send
    to_component: Temp_Limit_Checker_Instance  # in nominal
    to_connector: Command_T_Recv_Async
```

### Foundation Subassembly Pattern
One subassembly owns ALL infrastructure (ticker, rate groups, command router, CCSDS, events, product database). Other subassemblies contain only application components. The foundation subassembly defines arrayed connector counts (e.g., `Tick_T_Send_Count`) large enough to cover all subassemblies, then indices are split across files:

```yaml
# safe_mode.assembly.yaml -- foundation, owns Fast_Rate_Group
# Wires indices 6-8 to its own components internally

# parent.assembly.yaml -- wires remaining indices
# Fast_Rate_Group indices 1-5 -> nominal components
# Fast_Rate_Group indices 9-22 -> degraded components
```

### Minimal Subassemblies Are Valid
A subassembly can contain only `description:` and `components:` with no connections, id_bases, or preamble. This is common for leaf subsystems where all wiring is cross-subassembly and done in the parent:

```yaml
# Minimal valid subassembly
description: Standalone sensor collection
components:
  - type: Temperature_Sensor
    name: Temp_Sensor_Instance
  - type: Pressure_Sensor  
    name: Pressure_Sensor_Instance
# No connections, id_bases, preamble, etc. - all handled by parent
```ada

### Preamble Ordering
Subassembly preambles are concatenated in list order before the parent's preamble. If a parent preamble references a type declared in a subassembly preamble, it works (subassembly code appears first). But if a subassembly preamble references something from the parent's preamble, it won't be visible yet.

### Nested Subassemblies Are Supported
Subassemblies are loaded as `assembly(is_subassembly=True)` which runs the full assembly load, including processing of their own `subassemblies:` field. This means **nesting works** -- a subassembly can reference further subassemblies. Use this to organize by system state with subsystem groupings within each state.

### Connector Count Coordination
If a component in the parent has an arrayed connector (e.g., `Tick_T_Send_Count => 5`), some of those connections may target components in subassemblies. The count must match the total number of wired connections regardless of which file defines the target components.

### Subassembly Standalone Constraint
Per the user guide: "each subassembly must also be able to act as a standalone assembly. Specifically, any connections defined in an assembly must be between components defined in that assembly or one of that assembly's subassemblies." This is a **model validity** constraint -- a subassembly's connections can only reference its own components. It does NOT mean a subassembly can produce a standalone binary (it has no `main/` directory).

**Build note:** `redo all` in the assembly directory generates source code (including subassembly sources) into `build/src/`. The ELF binary is built from `main/`: `cd main && redo run`. If `redo all` fails at the gprbuild step, the generated Ada source may still be fine -- build the ELF from `main/` to verify.

## Example: Splitting a Monolithic Assembly

### Before (single file, 80+ components)

```yaml
# flight_sw.assembly.yaml -- everything in one file
components:
  # Core infrastructure (15 components)
  - type: Ticker
    ...
  - type: Rate_Group
    name: Fast_Rate_Group_Instance
    ...
  - type: Rate_Group
    name: Slow_Rate_Group_Instance
    ...
  # Communication (20 components)
  - type: Command_Router
    ...
  - type: Ccsds_Socket_Interface
    ...
  # GNC (25 components)
  - type: Nav_Filter
    ...
  - type: Attitude_Controller
    ...
  # ... 20+ more components

connections:
  # 100+ connections all in one list
  ...
```

### After (split into subassemblies)

Each subassembly lives in its own directory:
```
src/assembly/
├── my_assembly/
│   ├── .all_path
│   └── my_assembly.assembly.yaml
├── core/
│   ├── .all_path
│   └── core.assembly.yaml
├── comm/
│   ├── .all_path
│   └── comm.assembly.yaml
└── gnc/
    ├── .all_path
    └── gnc.assembly.yaml
```

**Parent (`my_assembly/my_assembly.assembly.yaml`):**
```yaml
description: Top-level assembly
subassemblies:
  - core
  - comm
  - gnc

# Only cross-subsystem connections here
connections:
  - from_component: Command_Router_Instance    # defined in comm
    from_connector: Command_T_Send
    from_index: 10
    to_component: Nav_Filter_Instance           # defined in gnc
    to_connector: Command_T_Recv_Async
```

**Core subassembly (`core/core.assembly.yaml`):**
```yaml
description: Core infrastructure -- timing and rate groups

preamble: |
  Dividers : aliased Component.Tick_Divider.Divider_Array_Type := [1 => 1, 2 => 10];

components:
  - type: Ticker
    priority: 10
    stack_size: 50000
    secondary_stack_size: 10000
  - type: Tick_Divider
    init_base:
      - "Tick_T_Send_Count => 2"

connections:
  - from_component: Ticker_Instance
    from_connector: Tick_T_Send
    to_component: Tick_Divider_Instance
    to_connector: Tick_T_Recv_Sync
```

**Leaf subassembly with no internal connections (`gnc/gnc.assembly.yaml`):**
```yaml
description: Guidance, navigation, and control subsystem
components:
  - type: Nav_Filter
    name: Nav_Filter_Instance
# No connections: key -- all wiring is cross-subsystem, done in the parent
```

## Quick Reference

| Question | Answer |
|----------|--------|
| How do I reference a subassembly? | Add its name to `subassemblies:` list in parent |
| Can subassemblies nest? | Yes -- subassemblies can reference further subassemblies |
| Can I wire between subassemblies? | Yes, but only from the parent assembly |
| Can a subassembly wire to a sibling's component? | No -- subassembly connections are scoped to its own components |
| Where should cross-subsystem connections go? | In the parent assembly (required, not just recommended) |
| Where should intra-subsystem connections go? | In the subassembly file |
| Can two subassemblies define the same component name? | No -- fatal error |
| Can two subassemblies set the same id_base? | No -- fatal error |
| Is bare `init:` (null) valid? | Yes -- equivalent to `init: []`, both mean no init params |
| Do views know about subassembly boundaries? | No -- views see the flattened assembly |
| Can a subassembly be built standalone? | No binary (no `main/`), but must be model-valid standalone (connections only reference own components) |

## Related Skills

- **Assembly development**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md) -- full assembly YAML reference, connection patterns, rate groups
- **Framework components**: [adamant-framework-components](../adamant-framework-components/SKILL.md) -- catalog of components to include in subassemblies
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md) -- build path setup for subassembly discovery
