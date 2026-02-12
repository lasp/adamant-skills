---
name: adamant-skill-selector
description: Route Adamant framework tasks to the correct skill(s). Load this FIRST for any Adamant work -- it tells you which specific skills to read.
---

# Adamant Skill Selector

You have 6 Adamant skills totaling ~2200 lines. Loading all of them wastes context. This skill maps your task to the 1-2 skills you actually need.

**After reading this file, read the skill(s) indicated for your task. Do not load skills you don't need.**

## Task Routing Table

### Building a new component
**Load:** `adamant-component-dev`
- YAML model definitions (component, commands, events, data products, faults, parameters, data dependencies)
- Connector kinds and compatibility
- Generated code API (base class, events, commands, data products packages)
- Implementation spec/body patterns
- Parameter modify connector, active component queues, C++ FFI wrapping

**Also load if needed:**
- `adamant-type-system` -- if defining custom packed records, arrays, or enums
- `adamant-testing` -- if writing tests for the component

### Writing component tests
**Load:** `adamant-testing`
- Reciprocal tester generation, History API, async dispatch
- Data dependency mocking, error injection, assertion patterns

**Also load:** `adamant-component-dev` (for the generated API signatures your tests call)

### Defining custom types (records, arrays, enums)
**Load:** `adamant-type-system`
- YAML field types and format codes
- Preamble enums vs standalone enums (different Ada generation patterns)
- Variable-length records, validation rules, default values
- Generated Ada type hierarchy (U, T, T_Le, Pack/Unpack)

### Building an assembly (wiring components together)
**Load:** `adamant-assembly-dev`
- Assembly YAML structure, component instantiation
- Multi-rate scheduling (rate groups, tick connectors)
- Command routing, event bifurcation, ID assignment
- View filters, validation rules

**Also load:** `adamant-framework-components` (catalog of all 55 built-in components to select from)

### Selecting framework components for a design
**Load:** `adamant-framework-components`
- Catalog of all 55 built-in components organized by subsystem
- Command routing, telemetry, sequencing, fault management, parameters, etc.

### Build system, compilation, code generation
**Load:** `adamant-build-system`
- Redo commands (build, test, prove, clean)
- Build path system (.all_path, target-specific)
- Code generation pipeline (YAML -> Python/Jinja2 -> Ada)
- Generated file map per YAML model type
- Cross-compilation, Docker environment, SPARK prove config

### COSMOS ground system integration
**Load:** `adamant-assembly-dev` (references/cosmos-integration.md)
- Generated command/telemetry config files
- Protocol files, plugin structure, scripting API

## Common Task Combinations

| Task | Primary Skill | Secondary |
|------|--------------|-----------|
| New component from scratch | component-dev | type-system |
| Add tests to existing component | testing | component-dev |
| Wire components into assembly | assembly-dev | framework-components |
| Debug build failure | build-system | -- |
| Define new packed types | type-system | -- |
| Choose components for a subsystem | framework-components | assembly-dev |
| Full component lifecycle (build+test) | component-dev | testing |
| SPARK verification | build-system (prove section) | component-dev |

## Naming Conventions (quick reference)

These patterns cause compilation errors if violated:
- **Data product names != type names** in scope (e.g., don't name a DP `Power_Status` if you have `Power_Status.T`)
- **Parameter type package != parameter name** (base record field shadows package)
- **Standalone enums**: Ada type is `Package.Enum_Name.E`, not `Package.Enum_Name`
- **Preamble enums**: live in the packed type package directly (different from standalone)
- **Data dependencies**: require `request` connector (`Data_Product_Fetch.T`), NOT `get`
- **Parameters**: require `modify` connector, NOT `recv_sync`

## When NOT to Use This Selector

- **General Ada/SPARK questions**: These skills are Adamant-specific. Generic Ada knowledge is already in the model.
- **hadlink or other projects**: Use `high-assurance-design` instead.
- **Learning Adamant from scratch**: Use `knowledge-acquisition` to study the framework first.
