# Adamant Agent Skills

Skills for AI-assisted development with the [Adamant](https://github.com/lasp/adamant) embedded software framework. Every pattern validated by compilation against a real GNAT/GNATprove toolchain.

## Quick Start

Read `adamant-skill-selector/SKILL.md` first. It routes your task to the right 1-2 skills.

## Skill Inventory (13 skills, ~8500+ lines with refs)

| Skill | SKILL.md | Refs | Purpose |
|-------|----------|------|---------|
| `adamant-skill-selector` | 146 | -- | **Read first.** Maps tasks to skills. |
| `adamant-component-dev` | 320 | 608 | Components: YAML models, generated API, implementation patterns |
| `adamant-testing` | 351 | 1366 | Test harness, History API, assertions, coverage guide |
| `adamant-framework-components` | 289 | -- | Catalog of all 55 built-in components |
| `adamant-assembly-dev` | 346 | 749 | Assemblies: scheduling, routing, ID assignment, runtime |
| `adamant-type-system` | 354 | 207 | YAML type definitions, format codes, Ada type hierarchy |
| `adamant-style` | 341 | 662 | Ada/YAML/Python style rules enforced by `redo style` |
| `adamant-algorithm-wrapping` | 326 | 559 | C++ -> C shim -> Ada bindings -> Adamant component pipeline |
| `adamant-build-system` | 307 | 322 | Redo commands, code gen pipeline, build paths |
| `adamant-cosmos-integration` | 326 | 182 | CCSDS pipeline, COSMOS plugin build/load |
| `adamant-project-setup` | 363 | 63 | New project scaffolding, env/activate, Docker, config |
| `high-assurance-design` | 206 | 98 | Design-by-invariant, non-goals, formal verification |
| `knowledge-acquisition` | 212 | 81 | Systematic codebase study with sub-agents |

**Totals:** ~3887 SKILL.md lines + ~4677 reference lines = ~8564 lines

## Key Principles

- **Framework-specific only.** Generic Ada/SPARK knowledge excluded.
- **Compiler-validated.** 30+ rounds of build-test-fix cycles across 100+ components + unit tests. Components compile clean on first try when skills are followed.
- **Selector-driven.** Load 1-2 skills per task, not all 13.
- **Three-tier prompt strategy:** This file (CLAUDE.md) -> skill-selector -> deep skills. Agents read CLAUDE.md to orient, skill-selector to route, then exactly the needed deep skills.
- **~300 line SKILL.md target.** Dense patterns in SKILL.md, detailed examples in references/.
- **No commits/push instructions.** Skills are agent-level -- orchestrators handle git operations.
- **No structural coverage ceiling.** All paths (Invalid_Command, Send_Dropped, Recv_Async_Dropped) are coverable with proper testing techniques.

## Validation Results

- **Style:** 221/221 directories, 0 failures (5 full runs)
- **Coverage:** 79% aggregate across 100 components (pre-Invalid_Command campaign)
- **Invalid_Command tests:** 63 components, 59/63 pass on first batch (4 fixed = 63/63)
- **Cold-start:** Fresh Sonnet agents produce compiling components with 0-2 errors
- **Component lifecycle:** New component from YAML to passing tests validated 19+ times

## Critical Build Rules

- **`redo clean` is always safe** on any directory (framework or project). Redo only rebuilds what changed. If redo state corrupts (STORAGE_ERROR), run `redo clean_all` on BOTH adamant and project dirs.
- **NEVER `rm -rf build`.** Use `redo clean` or `redo clean_all`.
- **`redo coverage` requires `redo clean` first** (stale .gcda contamination).
- **`source project/env/activate`** (not `adamant/env/activate`) -- sets BUILD_ROOTS correctly.
