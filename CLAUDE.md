# Adamant Agent Skills

Skills for AI-assisted development with the [Adamant](https://github.com/lasp/adamant) embedded software framework. Every pattern validated by compilation against a real GNAT/GNATprove toolchain.

## Quick Start

Read `adamant-skill-selector/SKILL.md` first. It routes your task to the right 1-2 skills.

## Skill Inventory (10 skills, ~3900 lines with refs)

| Skill | Lines | Purpose |
|-------|-------|---------|
| `adamant-skill-selector` | 119 | **Read first.** Maps tasks to skills. |
| `adamant-component-dev` | 443+453 ref | Components: YAML models, generated API, implementation patterns |
| `adamant-assembly-dev` | 317+104 ref | Assemblies: scheduling, routing, ID assignment |
| `adamant-build-system` | 292 | Redo commands, code gen pipeline, build paths |
| `adamant-framework-components` | 281 | Catalog of all 55 built-in components |
| `adamant-type-system` | 451 | YAML type definitions, format codes, Ada type hierarchy |
| `adamant-testing` | 415+179 ref | Test harness, History API, assertions, common errors |
| `adamant-algorithm-wrapping` | 243+111 ref | C++ -> C shim -> Ada bindings -> Adamant component pipeline |
| `adamant-cosmos-integration` | ~400 | CCSDS pipeline, COSMOS plugin build/load, CLI ops |
| `adamant-project-setup` | 187 | New project scaffolding, env/activate, Docker, config |

## Key Principles

- **Framework-specific only.** Generic Ada/SPARK knowledge excluded.
- **Compiler-validated.** 30+ rounds of build-test-fix cycles across 10 demo components + unit tests. Components compile clean on first try when skills are followed.
- **Selector-driven.** Load 1-2 skills per task, not all 10.
- **Three-tier prompt strategy:** This file (CLAUDE.md) -> skill-selector -> deep skills. Agents read CLAUDE.md to orient, skill-selector to route, then exactly the needed deep skills.

## Validation Status

- Component generation: ~90% first-try compile rate (sensor_mux clean, mode_manager_v2 1 fix, limit_checker 2 fixes, orbit_propagator 5 fixes in latest round)
- Testing: sensor_mux 3/3 passing first try; test compilation reliable, assertion logic still needs careful component-behavior matching
- Algorithm wrapping: C shim pattern validated; custom vs xmera type handling clarified
- Assembly integration: 10-component + CCSDS pipeline assembly links to 7.5MB ELF
- COSMOS integration: Plugin validated and loaded into OpenC3 6.10.4; cmd/tlm auto-generated
- Common fix categories: command naming (no _Execute suffix), Invalid_Command procedure signature, format: on custom record fields, qualifying ambiguous literals, .U->.T parameter conversion
- **Best practice**: Spawn component + tests in single agent for highest test accuracy (3/3 vs ~50% when separate)
- Best practice: spawn component + tests together for highest test accuracy (3/3 vs ~50% when tests spawned separately)

## Non-Adamant Skills

- `high-assurance-design` -- Design-by-invariant, non-goals, proof strategies
- `knowledge-acquisition` -- Systematic codebase study and skill creation methodology
