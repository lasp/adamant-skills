# Adamant Agent Skills

Skills for AI-assisted development with the [Adamant](https://github.com/lasp/adamant) embedded software framework. Every pattern validated by compilation against a real GNAT/GNATprove toolchain.

## Quick Start

Read `adamant-skill-selector/SKILL.md` first. It routes your task to the right 1-2 skills.

## Skill Inventory (9 skills, ~3470 lines with refs)

| Skill | Lines | Purpose |
|-------|-------|---------|
| `adamant-skill-selector` | 119 | **Read first.** Maps tasks to skills. |
| `adamant-component-dev` | 401+refs | Components: YAML models, generated API, implementation patterns |
| `adamant-assembly-dev` | 317+refs | Assemblies: scheduling, routing, ID assignment |
| `adamant-build-system` | 292 | Redo commands, code gen pipeline, build paths |
| `adamant-framework-components` | 281 | Catalog of all 55 built-in components |
| `adamant-type-system` | 451 | YAML type definitions, format codes, Ada type hierarchy |
| `adamant-testing` | 360+refs | Test harness, History API, assertions |
| `adamant-algorithm-wrapping` | 218+refs | C++ -> C shim -> Ada bindings -> Adamant component pipeline |
| `adamant-project-setup` | 187 | New project scaffolding, env/activate, Docker, config |

## Key Principles

- **Framework-specific only.** Generic Ada/SPARK knowledge excluded.
- **Compiler-validated.** 24+ rounds of build-test-fix cycles. Every pitfall is a real compilation error.
- **Selector-driven.** Load 1-2 skills per task, not all 9.

## Non-Adamant Skills

- `high-assurance-design` -- Design-by-invariant, non-goals, proof strategies
- `knowledge-acquisition` -- Systematic codebase study and skill creation methodology
