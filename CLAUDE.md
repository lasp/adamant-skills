# Adamant Agent Skills

Skills for AI-assisted development with the [Adamant](https://github.com/lasp/adamant) embedded software framework. Every pattern validated by compilation against a real GNAT/GNATprove toolchain.

## Quick Start

Read `adamant-skill-selector/SKILL.md` first. It routes your task to the right 1-2 skills.

## Skill Inventory (9 skills, ~3534 lines with refs)

| Skill | Lines | Purpose |
|-------|-------|---------|
| `adamant-skill-selector` | 119 | **Read first.** Maps tasks to skills. |
| `adamant-component-dev` | 425+453 ref | Components: YAML models, generated API, implementation patterns |
| `adamant-assembly-dev` | 317+104 ref | Assemblies: scheduling, routing, ID assignment |
| `adamant-build-system` | 292 | Redo commands, code gen pipeline, build paths |
| `adamant-framework-components` | 281 | Catalog of all 55 built-in components |
| `adamant-type-system` | 451 | YAML type definitions, format codes, Ada type hierarchy |
| `adamant-testing` | 372+179 ref | Test harness, History API, assertions, common errors |
| `adamant-algorithm-wrapping` | 243+111 ref | C++ -> C shim -> Ada bindings -> Adamant component pipeline |
| `adamant-project-setup` | 187 | New project scaffolding, env/activate, Docker, config |

## Key Principles

- **Framework-specific only.** Generic Ada/SPARK knowledge excluded.
- **Compiler-validated.** 30+ rounds of build-test-fix cycles across 10 demo components + unit tests. Components compile clean on first try when skills are followed.
- **Selector-driven.** Load 1-2 skills per task, not all 9.
- **Three-tier prompt strategy:** This file (CLAUDE.md) -> skill-selector -> deep skills. Agents read CLAUDE.md to orient, skill-selector to route, then exactly the needed deep skills.

## Validation Status

- Component generation: ~95% first-try compile rate (4/4 clean in latest round)
- Testing: test stimulus API and history comparison patterns now documented
- Algorithm wrapping: C shim pattern validated; custom vs xmera type handling clarified
- Assembly integration: 10-component assembly links to 3.7MB ELF

## Non-Adamant Skills

- `high-assurance-design` -- Design-by-invariant, non-goals, proof strategies
- `knowledge-acquisition` -- Systematic codebase study and skill creation methodology
