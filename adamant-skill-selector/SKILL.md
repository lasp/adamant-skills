---
name: adamant-skill-selector
description: Route Adamant framework tasks to the correct skill(s). Load this FIRST for any Adamant work -- it tells you which specific skills to read.
---

# Adamant Skill Selector

You have 19 Adamant skills totaling ~19300 lines (with references). Loading all of them wastes context. This skill maps your task to the 1-2 skills you actually need.

**After reading this file, read the skill(s) indicated for your task. Do not load skills you don't need.**

## Read Order Rule

Always read skills in the order listed in the routing table below -- primary skill first, then secondary. Within a multi-skill task, do not reorder reads based on your own judgment. Consistent read order across sessions enables prompt cache hits, reducing cost and latency.

If your task matches a sequence in "Deterministic Read Order" at the bottom of this file, use that exact sequence.

## CRITICAL: All Builds Require Docker

Adamant builds MUST run inside the project's Docker container. **Never build locally on the host.** Check for `ADAMANT_ENVIRONMENT_SET=yes` -- if not set, use `docker exec` to run all redo/build/test commands inside the container. See `adamant-build-system` for the Docker exec pattern and `TOOLS.md` for project-specific container names.

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

**Also load:** `adamant-framework-components` (catalog of all 58 built-in components to select from)
**Also load if needed:** `adamant-subassemblies` -- if splitting a large assembly into reusable subassemblies

### Splitting assemblies into subassemblies
**Load:** `adamant-subassemblies`
- Decomposing monolithic assembly YAML into reusable pieces
- Subassembly merge behavior (components, connections, preamble, id_bases)
- Cross-subassembly wiring patterns
- ID base range allocation across subassemblies
- Build path requirements for subassembly discovery

**Also load:** `adamant-assembly-dev` (for full assembly YAML reference and connection patterns)

### Selecting framework components for a design
**Load:** `adamant-framework-components`
- Catalog of all 58 built-in components organized by subsystem
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

### COSMOS integration test scripts
**Load:** `adamant-cosmos-testing`
- Test script patterns for exercising a running assembly via COSMOS
- Command acceptance, telemetry verification, mode transitions, fault injection
- Parameter update lifecycle, rate verification, stress/edge cases
- Suite organization (Group/Suite hierarchy), wait/check API patterns
- pydep integration for using Adamant packed records in test scripts
- Disconnect mode for offline script validation

**Also load:** `adamant-cosmos-integration` (for plugin structure, CCSDS wiring, cmd/tlm definitions)

### Debugging framework code generation bugs
**Load:** `adamant-framework-internals`
- Python model object identity pitfall (`is` vs `==`, `base.__eq__` by filename)
- Assembly load sequence and `set_assembly()` callback timing
- Custom model override pattern (`gen/models/` per component)
- Connection graph traversal for per-instance type resolution
- Debug workflow: identify generator -> find model class -> trace connections -> verify with `redo clear_cache`

**Also load:** `adamant-build-system` (for generator dispatch and code gen pipeline context)

### SPARK formal verification
**Load:** `adamant-formal-verification`
- Adding SPARK contracts (Pre, Post, Global, Depends) to components or standalone packages
- Running GNATprove via `redo prove`
- `all.prove.yaml` configuration (level, mode)
- Ghost code, loop invariants, ghost lemma pattern
- Proof chain pattern for opaque type boundaries
- Absence-of-runtime-errors proofs
- Memory map / register map SPARK analysis

**Also load if needed:**
- `adamant-component-dev` -- if adding SPARK to a component's logic
- `adamant-build-system` -- if debugging prove build path issues

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
| New component from scratch | component-dev | tools, type-system, style |
| Scaffold + validate before building | tools | component-dev |
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
| Review generated or hand-written code | code-review | component-dev |
| PR review (Adamant artifacts) | code-review | testing |
| SPARK verification | formal-verification | component-dev |
| Wrap C++ algorithm into Adamant component | algorithm-wrapping | component-dev |
| Ground system integration (COSMOS) | cosmos-integration | assembly-dev |
| COSMOS integration test scripts | cosmos-testing | cosmos-integration |
| Memory-mapped register interface | type-system | component-dev |
| Split assembly into subassemblies | subassemblies | assembly-dev |
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

### Inspecting generated API, scaffolding components, validating YAML
**Load:** `adamant-tools`
- `adamant_inspect.py` -- extract generated API summary after first build
- `adamant_scaffold.py` -- generate all component files from a spec YAML
- `adamant_validate_yaml.py` -- pre-flight YAML validation without Docker

**Use alongside:** `adamant-component-dev` and `adamant-testing`

### Reviewing Adamant code (PR review, post-generation audit, design assessment)
**Load:** `adamant-code-review`
- Component, test, type, and assembly review checklists
- Assertion quality and coverage assessment
- Design review (decomposition, connector topology, SPARK candidacy)
- Finding severity levels (error/warning/info) and structured output format

**Also load if needed:**
- `adamant-component-dev` -- for generated API reference when reviewing implementations
- `adamant-testing` -- for test pattern reference when reviewing test quality

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

## Deterministic Read Order (for cache-stable automation)

When tasks specify "read skills in order," use these exact sequences. The order matters for prompt cache stability -- identical read order across spawns enables cache hits.

### Component + Tests (simple passive, no FFI)
1. `adamant-skill-selector/SKILL.md` (this file)
2. `adamant-component-dev/SKILL.md`
3. `adamant-component-dev/references/pitfalls-and-checklist.md`
4. `adamant-testing/SKILL.md`

Skip `generated-api.md` and `implementation-patterns.md` for simple passive components (recv_sync + send only). The main SKILL.md covers basic connector patterns.

### Component + Tests (active, commands, request/provide, or complex state)
1. `adamant-skill-selector/SKILL.md` (this file)
2. `adamant-component-dev/SKILL.md`
3. `adamant-component-dev/references/generated-api.md`
4. `adamant-component-dev/references/implementation-patterns.md`
5. `adamant-component-dev/references/pitfalls-and-checklist.md`
6. `adamant-testing/SKILL.md`

### Types only
1. `adamant-skill-selector/SKILL.md` (this file)
2. `adamant-type-system/SKILL.md`

### Types + Simple Components + Tests (consolidated phase)
1. `adamant-skill-selector/SKILL.md` (this file)
2. `adamant-type-system/SKILL.md`
3. `adamant-component-dev/SKILL.md`
4. `adamant-component-dev/references/pitfalls-and-checklist.md`
5. `adamant-testing/SKILL.md`

Skip `generated-api.md` for consolidated phases with only simple passive components.

### Assembly + Subassemblies
1. `adamant-skill-selector/SKILL.md` (this file)
2. `adamant-assembly-dev/SKILL.md`
3. `adamant-subassemblies/SKILL.md`

### Algorithm Wrapping (C/C++ -> Adamant)
1. `adamant-skill-selector/SKILL.md` (this file)
2. `adamant-algorithm-wrapping/SKILL.md`
3. `adamant-component-dev/SKILL.md`
4. `adamant-component-dev/references/generated-api.md`
5. `adamant-component-dev/references/implementation-patterns.md`
6. `adamant-testing/SKILL.md`

## When NOT to Use This Selector

- **General Ada/SPARK questions**: These skills are Adamant-specific. Generic Ada knowledge is already in the model.
- **hadlink or other projects**: Use `high-assurance-design` instead.
- **Learning Adamant from scratch**: Use `knowledge-acquisition` to study the framework first.
