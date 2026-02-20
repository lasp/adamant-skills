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

Subassemblies are NOT separate executables. They merge into a single assembly producing one Ada package and one binary.

## File Structure

```
my_assembly/
├── .all_path
├── my_assembly.assembly.yaml        # Parent assembly (references subassemblies)
├── core.assembly.yaml               # Subassembly: core infrastructure
├── comm.assembly.yaml               # Subassembly: communication subsystem
├── gnc.assembly.yaml                # Subassembly: guidance/navigation/control
├── main/
│   ├── .all_path
│   └── main.adb
└── views/
```

Subassembly files can live in the same directory as the parent or anywhere in the build path. The model loader finds them by name.

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
```

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

Subassembly `.assembly.yaml` files must be discoverable in the build path. Options:

1. **Same directory** as the parent assembly (simplest)
2. **Separate directory** with an `.all_path` marker so the build system includes it
3. **Shared location** in a common library directory (for cross-project reuse)

The model loader calls `model_loader.try_load_model_by_name(name, "assembly")` to find subassembly files. If the file isn't in any build path directory, you get:

```
Could not load model for subassembly 'core'. Make sure the model exists in the path.
```

## ID Base Management

⚠️ **CRITICAL CONSTRAINT**: ID base keys must be **globally unique**. The same key name (e.g., `Event_Id_Base`) CANNOT appear in multiple subassemblies. This means you cannot give each subassembly its own `Event_Id_Base`.

**SOLUTION**: Define ALL id_bases in the parent assembly only. Do NOT define id_bases in subassemblies. Values must be positive (>= 1, NOT 0).

```yaml
# WRONG: Same id_base key in multiple subassemblies
# core.assembly.yaml
id_bases:
  - "Event_Id_Base => 1"        # FATAL ERROR: duplicate key

# comm.assembly.yaml  
id_bases:
  - "Event_Id_Base => 500"      # FATAL ERROR: duplicate key

# CORRECT: All id_bases in parent only
# parent.assembly.yaml
id_bases:
  - "Event_Id_Base => 1"
  - "Command_Id_Base => 1"
  - "Data_Product_Id_Base => 1"
  - "Fault_Id_Base => 1"

subassemblies:
  - core
  - comm
  - gnc
```

**Rules:**
- Each id_base name must end with `_Id_Base` (e.g., `Event_Id_Base`, `Command_Id_Base`)
- Values must be positive integers
- **ID base keys must be globally unique** across ALL subassemblies and the parent
- If you need assembly-wide id_bases, define them in the parent assembly ONLY
- Subassemblies should NOT contain `id_bases:` sections

**Strategy:** Plan ID ranges at the parent level and document the allocation in comments. Component IDs will be auto-assigned sequentially starting from the base values.

## Cross-Subassembly Connections

Components defined in different subassemblies can be wired together. The connections can go in:

1. **The parent assembly** (recommended for cross-subassembly wiring)
2. **Either subassembly** (works but harder to track)

Since all components merge into a single namespace, any connection can reference any component regardless of which file defined it:

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
```

**Best practice:** Keep intra-subsystem connections in the subassembly file. Put inter-subsystem connections in the parent. This makes the integration points explicit.

⚠️ **CRITICAL - Cross-Subassembly Data Dependencies**: If a component in subassembly A has data dependencies that need to map to data products from components in subassembly B, the `map_data_dependencies` resolver CANNOT find them. The mapper only searches at the subassembly level, not across subassemblies.

**SOLUTION**: Move the component with cross-subassembly data dependencies to the parent assembly instead of keeping it in a subassembly. This gives the mapper access to all component data products during resolution.

## View System Interaction

Views work on the **merged** (flattened) assembly. When generating views:

- The view model receives all components and connections from all subassemblies
- Subassembly boundaries are not visible in views -- components appear as if they were all in one file
- Filter by `component_name` or `component_type` to create subsystem-focused views
- The view system internally clears the `subassemblies` field to avoid reloading during view construction

To create a view showing only one subassembly's components, use a component name or type filter that matches the components from that subassembly.

## Limitations and Gotchas

### Duplicate Component Names
Component instance names must be unique across ALL subassemblies and the parent. If `core.assembly.yaml` and `comm.assembly.yaml` both define a component named `Rate_Group_Instance`, you get:

```
Duplicate component 'Rate_Group_Instance' not allowed. Found in files: [...]
```

**Fix:** Use distinct names like `Core_Rate_Group_Instance` and `Comm_Rate_Group_Instance`.

### Duplicate ID Bases
⚠️ **CRITICAL**: The same `id_base` key cannot appear in multiple subassemblies:

```
Duplicate id_base 'Event_Id_Base' found in comm.assembly.yaml.
```

**Fix:** Define ALL id_bases in the parent assembly only. Do NOT use id_bases in subassemblies.

### Empty Connections Field Crash
A `connections:` key with only comments (no actual connections) results in `TypeError: 'NoneType' object is not iterable`. 

**Fix:** Omit the `connections:` key entirely if there are no intra-subassembly connections:

```yaml
# WRONG: Empty connections field
connections:
  # No actual connections, just comments

# CORRECT: No connections field at all
description: Sensor subsystem
components:
  - type: Sensor_Reader
    # ...
```

### Minimal Subassemblies Are Valid
A subassembly can contain only `description:` and `components:` with no connections, id_bases, or preamble. This is common for leaf subsystems where all wiring is done in the parent:

```yaml
# Minimal valid subassembly
description: Standalone sensor collection
components:
  - type: Temperature_Sensor
    name: Temp_Sensor_Instance
  - type: Pressure_Sensor  
    name: Pressure_Sensor_Instance
# No connections, id_bases, preamble, etc. - all handled by parent
```

### Preamble Ordering
Subassembly preambles are concatenated in list order before the parent's preamble. If a parent preamble references a type declared in a subassembly preamble, it works (subassembly code appears first). But if a subassembly preamble references something from the parent's preamble, it won't be visible yet.

### Nested Subassemblies Are Supported
Subassemblies are loaded as `assembly(is_subassembly=True)` which runs the full assembly load, including processing of their own `subassemblies:` field. This means **nesting works** -- a subassembly can reference further subassemblies. Use this to organize by system state with subsystem groupings within each state.

### Connector Count Coordination
If a component in the parent has an arrayed connector (e.g., `Tick_T_Send_Count => 5`), some of those connections may target components in subassemblies. The count must match the total number of wired connections regardless of which file defines the target components.

### Subassembly Files Are Not Independent Assemblies
A subassembly file can't be built on its own -- it has no `main/` directory and won't generate a standalone binary. It only has meaning when included by a parent assembly.

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

**Parent (`flight_sw.assembly.yaml`):**
```yaml
description: Flight software top-level assembly

subassemblies:
  - flight_sw_core
  - flight_sw_comm
  - flight_sw_gnc

with:
  - Flight_Sw_Commands

# Only cross-subsystem connections here
connections:
  - description: Route commands to GNC components
    from_component: Command_Router_Instance
    from_connector: Command_T_Send
    from_index: 10
    to_component: Nav_Filter_Instance
    to_connector: Command_T_Recv_Async
  # ... other cross-subsystem wiring
```

**Core subassembly (`flight_sw_core.assembly.yaml`):**
```yaml
description: Core infrastructure -- timing, watchdog, system time

preamble: |
  Dividers : aliased Component.Tick_Divider.Divider_Array_Type := [1 => 1, 2 => 10];

id_bases:
  - "Event_Id_Base => 1"

components:
  - type: Ticker
    priority: 10
    stack_size: 50000
    secondary_stack_size: 10000
  - type: Tick_Divider
    discriminant:
      - "Divider_List => Dividers'Access"
    init_base:
      - "Tick_T_Send_Count => 2"
  - type: Rate_Group
    name: Fast_Rate_Group_Instance
    priority: 9
    stack_size: 50000
    secondary_stack_size: 10000
    init_base:
      - "Queue_Size => 3 * Fast_Rate_Group_Instance.Get_Max_Queue_Element_Size"
      - "Tick_T_Send_Count => 8"

connections:
  - from_component: Ticker_Instance
    from_connector: Tick_T_Send
    to_component: Tick_Divider_Instance
    to_connector: Tick_T_Recv_Sync
  # ... internal core connections
```

**Comm subassembly (`flight_sw_comm.assembly.yaml`):**
```yaml
description: Command and telemetry communication subsystem

id_bases:
  - "Event_Id_Base => 500"

components:
  - type: Command_Router
    priority: 8
    stack_size: 50000
    secondary_stack_size: 10000
    init_base:
      - "Queue_Size => 10 * Command_Router_Instance.Get_Max_Queue_Element_Size"
      - "Command_T_Send_Count => 20"
      - "Command_Response_T_To_Forward_Send_Count => 1"
    init:
      - "Max_Number_Of_Commands => Flight_Sw_Commands.Number_Of_Commands"
  # ... other comm components

connections:
  # Internal comm wiring
  ...
```

**GNC subassembly (`flight_sw_gnc.assembly.yaml`):**
```yaml
description: Guidance, navigation, and control subsystem

id_bases:
  - "Event_Id_Base => 1000"

components:
  - type: Nav_Filter
    name: Nav_Filter_Instance
    priority: 9
    stack_size: 100000
    secondary_stack_size: 10000
  # ... other GNC components

connections:
  # Internal GNC wiring
  ...
```

## Quick Reference

| Question | Answer |
|----------|--------|
| How do I reference a subassembly? | Add its name to `subassemblies:` list in parent |
| Can subassemblies nest? | Yes -- subassemblies can reference further subassemblies |
| Can I wire between subassemblies? | Yes -- all components share one namespace after merge |
| Where should cross-subsystem connections go? | In the parent assembly |
| Can two subassemblies define the same component name? | No -- fatal error |
| Can two subassemblies set the same id_base? | No -- fatal error |
| Do views know about subassembly boundaries? | No -- views see the flattened assembly |
| Can a subassembly be built standalone? | No -- it needs a parent with `main/` |

## Related Skills

- **Assembly development**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md) -- full assembly YAML reference, connection patterns, rate groups
- **Framework components**: [adamant-framework-components](../adamant-framework-components/SKILL.md) -- catalog of components to include in subassemblies
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md) -- build path setup for subassembly discovery
