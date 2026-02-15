# Adamant Agent Skills

Skills for AI-assisted development with the [Adamant](https://github.com/lasp/adamant) embedded software framework. Every pattern validated by compilation against a real GNAT/GNATprove toolchain.

## Quick Start

Read `adamant-skill-selector/SKILL.md` first. It routes your task to the right 1-2 skills.

## Skill Inventory (14 skills, ~10700+ lines with refs)

| Skill | SKILL.md | Refs | Purpose |
|-------|----------|------|---------|
| `adamant-skill-selector` | 166 | -- | **Read first.** Maps tasks to skills. |
| `adamant-component-dev` | 330 | 1070 | Components: YAML models, generated API, implementation patterns, LASEL |
| `adamant-testing` | 356 | 1870 | Test harness, History API, assertions, coverage, advanced patterns |
| `adamant-framework-components` | 300 | 170 | Catalog of all 55 built-in components + audit |
| `adamant-assembly-dev` | 371 | 750 | Assemblies: scheduling, routing, ID assignment, runtime monitoring |
| `adamant-type-system` | 354 | 180 | YAML type definitions, format codes, Ada type hierarchy |
| `adamant-style` | 342 | 660 | Ada/YAML/Python style rules enforced by `redo style` |
| `adamant-algorithm-wrapping` | 334 | 560 | C++ -> C shim -> Ada bindings -> Adamant component pipeline |
| `adamant-build-system` | 316 | 900 | Redo commands, code gen, build paths, SPARK prove |
| `adamant-cosmos-integration` | 330 | 180 | CCSDS pipeline, COSMOS plugin build/load |
| `adamant-project-setup` | 363 | -- | New project scaffolding, env/activate, Docker, config |
| `adamant-skill-creation` | 225 | 90 | Creating, validating, and refactoring Adamant skills |
| `high-assurance-design` | 206 | -- | Design-by-invariant, non-goals, formal verification |
| `knowledge-acquisition` | 212 | -- | Systematic codebase study with sub-agents |

**Totals:** ~3900 SKILL.md lines + ~7000 reference lines = ~10800 lines

## Key Principles

- **Framework-specific only.** Generic Ada/SPARK knowledge excluded.
- **Compiler-validated.** 30+ rounds of build-test-fix cycles across 100+ components + unit tests. Components compile clean on first try when skills are followed.
- **Selector-driven.** Load 1-2 skills per task, not all 14.
- **Three-tier prompt strategy:** This file (CLAUDE.md) -> skill-selector -> deep skills.
- **~300 line SKILL.md target.** Dense patterns in SKILL.md, detailed examples in references/.
- **No project-specific content.** Generic skills contain zero project names or paths. Project-specific guidance lives in the project repo.
- **No commits/push instructions.** Skills are agent-level -- orchestrators handle git.
- **No structural coverage ceiling.** All paths are coverable with proper testing techniques.
- **All style warnings are fixable.** No "template artifacts" -- every warning has a solution.

## Validation Results

- **Style:** 221/221 directories, 0 failures
- **Coverage:** 89%+ aggregate across 100+ components
- **Invalid_Command tests:** 63/63 components passing
- **Cold-start:** Fresh agents produce compiling components with 0-2 errors
- **Component lifecycle:** New component from YAML to passing tests validated 19+ times
- **Convergence:** Round 19 achieved zero errors from cold-start agent

## Critical Build Rules

- **`redo clean` is always safe** on any directory (framework or project). If redo state corrupts (STORAGE_ERROR), run `redo clean_all` on BOTH adamant and project dirs.
- **NEVER manually delete build directories** (`rm -rf build`, `rm -rf */build`, etc.). Use `redo clean` or `redo clean_all`. Bulk-deleting build dirs corrupts redo state and may require container recreation to recover.
- **`redo coverage` requires `redo clean` first** (stale .gcda contamination).
- **`source project/env/activate`** (not `adamant/env/activate`) -- sets BUILD_ROOTS correctly.
