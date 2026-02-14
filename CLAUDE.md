# Adamant Agent Skills

Skills for AI-assisted development with the [Adamant](https://github.com/lasp/adamant) embedded software framework. Every pattern validated by compilation against a real GNAT/GNATprove toolchain.

## Quick Start

Read `adamant-skill-selector/SKILL.md` first. It routes your task to the right 1-2 skills.

## Skill Inventory (11 skills, ~3900+ lines with refs)

| Skill | Lines | Purpose |
|-------|-------|---------|
| `adamant-skill-selector` | 146 | **Read first.** Maps tasks to skills. |
| `adamant-component-dev` | 317+514 ref | Components: YAML models, generated API, implementation patterns |
| `adamant-testing` | 304+276 ref | Test harness, History API, assertions, coverage |
| `adamant-framework-components` | 281 | Catalog of all 55 built-in components |
| `adamant-assembly-dev` | 254+425 ref | Assemblies: scheduling, routing, ID assignment, runtime |
| `adamant-type-system` | 235+50 ref | YAML type definitions, format codes, Ada type hierarchy |
| `adamant-style` | 187 | Ada/YAML/Python style rules enforced by `redo style` |
| `adamant-algorithm-wrapping` | 179+74 ref | C++ -> C shim -> Ada bindings -> Adamant component pipeline |
| `adamant-build-system` | 151+35 ref | Redo commands, code gen pipeline, build paths |
| `adamant-cosmos-integration` | 130+179 ref | CCSDS pipeline, COSMOS plugin build/load |
| `adamant-project-setup` | 120 | New project scaffolding, env/activate, Docker, config |

## Key Principles

- **Framework-specific only.** Generic Ada/SPARK knowledge excluded.
- **Compiler-validated.** 30+ rounds of build-test-fix cycles across 100+ demo components + unit tests. Components compile clean on first try when skills are followed.
- **Selector-driven.** Load 1-2 skills per task, not all 11.
- **Three-tier prompt strategy:** This file (CLAUDE.md) -> skill-selector -> deep skills. Agents read CLAUDE.md to orient, skill-selector to route, then exactly the needed deep skills.
- **Style-aware.** The `adamant-style` skill is referenced from all other skills. Load it alongside any code-producing skill.

## Validation Status

- Component generation: ~95% first-try compile rate (PID controller with data deps, commands, params, events, faults: 1 error on cold start)
- Testing: 5/5 first-try for thruster_interface, 6/6 for PID controller
- Algorithm wrapping: C shim pattern validated; custom vs xmera type handling clarified
- Assembly integration: 100-component station + mini-assembly both link and run
- COSMOS integration: Plugin validated and loaded into OpenC3 6.10.4
- Style: 100-component style campaign -- all 17 common error patterns documented with actual frequency data
- Best practice: spawn component + tests together for highest test accuracy

## Non-Adamant Skills

- `high-assurance-design` -- Design-by-invariant, non-goals, proof strategies
- `knowledge-acquisition` -- Systematic codebase study and skill creation methodology
