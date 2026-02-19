---
name: adamant-skill-selector
description: Route Adamant framework tasks to the correct skill(s). Load this FIRST for any Adamant work -- it tells you which specific skills to read.
---

# Adamant Skill Selector

You have 15 Adamant skills totaling ~11100 lines (with references). Loading all of them wastes context. This skill maps your task to the 1-2 skills you actually need.

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

### Measuring or improving test coverage
**Load:** `adamant-testing` (see `references/coverage-guide.md`)
- `redo coverage` workflow, gcov stamp mismatch troubleshooting
- `impl_coverage.sh` script for filtering to implementation .adb
- Full path coverage techniques (Invalid_Command, Send_Dropped, Recv_Async_Dropped)
- Adding tests to existing components (YAML + template regeneration)

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

### Setting up a new Adamant project
**Load:** `adamant-project-setup`
- Project directory structure, .do file setup, env/activate script
- Configuration YAML (buffer sizes, stack margin)
- Docker integration (compose override, build commands)
- .gitignore, .all_path requirements, common pitfalls

### Build system, compilation, code generation
**Load:** `adamant-build-system`
- Redo commands (build, test, prove, clean)
- Build path system (.all_path, target-specific)
- Code generation pipeline (YAML -> Python/Jinja2 -> Ada)
- Generated file map per YAML model type
- Cross-compilation, Docker environment, SPARK prove config

### Wrapping C++ algorithms into Adamant components
**Load:** `adamant-algorithm-wrapping`
- Complete 7-stage pipeline: C shim -> Ada bindings -> packed records -> component implementation -> unit tests
- C shim patterns (shared types headers, opaque handles, POD conversions)
- h2ads tool usage and Ada binding transformation rules
- C struct to packed record YAML conversion
- Component YAML models for algorithm wrappers
- Integration testing patterns comparing against Python reference tests

**Also load if needed:**
- `adamant-component-dev` -- for understanding component implementation patterns
- `adamant-type-system` -- if creating new packed record types not covered in the examples

### COSMOS ground system integration
**Load:** `adamant-cosmos-integration`
- CCSDS pipeline architecture (Socket, Depacketizer, Packetizer components)
- Assembly wiring for command uplink and telemetry downlink
- Product packets model (YAML), plugin structure, build/install workflow
- COSMOS CLI operations (plugin load, script run)

**Also load:** `adamant-assembly-dev` (for assembly YAML patterns and validation rules)

### Debugging framework code generation bugs
**Load:** `adamant-framework-internals`
- Python model object identity pitfall (`is` vs `==`, `base.__eq__` by filename)
- Assembly load sequence and `set_assembly()` callback timing
- Custom model override pattern (`gen/models/` per component)
- Connection graph traversal for per-instance type resolution
- Debug workflow: identify generator -> find model class -> trace connections -> verify with `redo clear_cache`

**Also load:** `adamant-build-system` (for generator dispatch and code gen pipeline context)

### Code style checking and compliance
**Load:** `adamant-style`
- Ada style rules (gnat warnings, whitespace, short-circuit operators, casing)
- YAML lint rules (document start, indentation)
- Python style (env.py format)
- Component YAML `with:` section rules
- All style warnings are fixable (no "template artifacts" -- common misconception)
- Style checklist

**Always load alongside other skills** when writing any Adamant code. Style rules apply to components, tests, types, and assemblies.

## Common Task Combinations

| Task | Primary Skill | Secondary |
|------|--------------|-----------|
| New component from scratch | component-dev | type-system, style |
| Add tests to existing component | testing | component-dev |
| Measure/improve test coverage | testing (coverage guide) | component-dev |
| Wire components into assembly | assembly-dev | framework-components |
| Debug build failure | build-system | -- |
| Debug code generation producing wrong output | framework-internals | build-system |
| Fix bug in framework Python model | framework-internals | -- |
| Extend framework with custom model override | framework-internals | component-dev |
| Define new packed types | type-system | -- |
| Choose components for a subsystem | framework-components | assembly-dev |
| Full component lifecycle (build+test) | component-dev | testing |
| SPARK verification | build-system (prove section) | component-dev |
| Wrap C++ algorithm into Adamant component | algorithm-wrapping | component-dev |
| Ground system integration (COSMOS) | cosmos-integration | assembly-dev |
| Memory-mapped register interface | type-system | component-dev |
| Create system architecture from scratch | assembly-dev | framework-components |
| Start a new Adamant project | project-setup | build-system |
| Run/monitor assembly at runtime | assembly-dev (runtime ref) | -- |
| Debug running assembly (events, queues) | assembly-dev (runtime ref) | -- |
| Use Python ground tools | assembly-dev (runtime ref) | cosmos-integration |
| Multi-rate scheduling design | assembly-dev (runtime ref) | framework-components |

## Naming Conventions (quick reference)

These patterns cause compilation errors if violated:
- **Data product names != type names** in scope (e.g., don't name a DP `Power_Status` if you have `Power_Status.T`)
- **Parameter type package != parameter name** (base record field shadows package)
- **Standalone enums**: Ada type is `Package.Enum_Name.E`, not `Package.Enum_Name`
- **Preamble enums**: live in the packed type package directly (different from standalone)
- **Data dependencies**: require `request` connector (`Data_Product_Fetch.T`), NOT `get`
- **Parameters**: require `modify` connector, NOT `recv_sync`

### Creating or improving Adamant skills
**Load:** `adamant-skill-creation`
- Skill structure, writing rules, validation methodology
- Cold-start testing, convergence tracking
- Separating project-specific from generic content
- Maintaining skill health and preventing anti-patterns

## Project-Specific Skills

Generic Adamant skills must contain NO project-specific content (no project names, component names, assembly names, or paths). If a project needs specialized guidance beyond generic Adamant patterns, create a **project-specific skill** in the project's own repo (e.g., `<project>/skills/` or `<project>/docs/agent-skill.md`).

Examples of project-specific content:
- Component naming conventions (e.g., `station_` prefix)
- Assembly topology and wiring specifics
- Custom type libraries unique to the project
- Build/deployment recipes specific to the project's Docker setup
- COSMOS plugin configuration for the project's telemetry

Generic Adamant skills provide the *how*. Project skills provide the *what* and *where*.

## Regenerating the Routing Table

This routing table can be regenerated from skill metadata:
```bash
bash scripts/generate_selector.sh /path/to/skills/
```

Last generated: 2026-02-19

## When NOT to Use This Selector

- **General Ada/SPARK questions**: These skills are Adamant-specific. Generic Ada knowledge is already in the model.
- **hadlink or other projects**: Use `high-assurance-design` instead.
- **Learning Adamant from scratch**: Use `knowledge-acquisition` to study the framework first.
