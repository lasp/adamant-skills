# Adamant Agent Skills

Skills for AI-assisted development with the [Adamant](https://github.com/lasp/adamant) embedded software framework. Every pattern validated by compilation against a real GNAT/GNATprove toolchain.

## Quick Start

Read `adamant-skill-selector/SKILL.md` first. It routes your task to the right 1-2 skills.

## Skill Inventory (16 skills, ~12200 lines with refs)

| Skill | Lines | Purpose |
|-------|-------|---------|
| `adamant-skill-selector` | 200 | **Read first.** Maps tasks to skills. |
| `adamant-testing` | 2221 | Test harness, History API, assertions, coverage, advanced patterns |
| `adamant-component-dev` | 1581 | Components: YAML models, generated API, implementation patterns, LASEL |
| `adamant-algorithm-wrapping` | 1487 | C++ -> C shim -> Ada bindings -> Adamant component pipeline |
| `adamant-assembly-dev` | 1071 | Assemblies: scheduling, routing, ID assignment, runtime monitoring |
| `adamant-skill-creation` | 839 | Creating, validating, and refactoring Adamant skills |
| `adamant-build-system` | 808 | Redo commands, code gen, build paths, SPARK prove |
| `adamant-type-system` | 542 | YAML type definitions, format codes, Ada type hierarchy |
| `adamant-cosmos-integration` | 510 | CCSDS pipeline, COSMOS plugin build/load |
| `adamant-framework-components` | 477 | Catalog of all 58 built-in components + audit |
| `adamant-subassemblies` | 463 | Splitting assemblies into reusable subassemblies, nesting, wiring rules |
| `adamant-framework-internals` | 441 | Framework Python model internals, code gen debugging, `is` vs `==` pitfall |
| `adamant-style` | 426 | Ada/YAML/Python style rules enforced by `redo style` |
| `adamant-project-setup` | 381 | New project scaffolding, env/activate, Docker, config |
| `knowledge-acquisition` | 370 | Systematic codebase study with sub-agents |
| `high-assurance-design` | 304 | Design-by-invariant, non-goals, formal verification |

**Total:** ~12200 lines (SKILL.md files trimmed for density, reference files at full depth)

## Key Principles

- **Framework-specific only.** Generic Ada/SPARK knowledge excluded.
- **Compiler-validated.** 30+ rounds of build-test-fix cycles across 100+ components + unit tests. Components compile clean on first try when skills are followed.
- **Selector-driven.** Load 1-2 skills per task, not all 16.
- **Three-tier prompt strategy:** This file (CLAUDE.md) -> skill-selector -> deep skills.
- **~300-500 line SKILL.md target.** Dense patterns in SKILL.md, detailed examples in references/.
- **No project-specific content.** Generic skills contain zero project names or paths. Project-specific guidance lives in the project repo.
- **No commits/push instructions.** Skills are agent-level -- orchestrators handle git.
- **No structural coverage ceiling.** All paths are coverable with proper testing techniques.
- **All style warnings are fixable.** No "template artifacts" -- every warning has a solution.

## Validation Results

- **Style:** 221/221 directories, 0 failures
- **Coverage:** 89%+ aggregate across 100+ components
- **Invalid_Command tests:** 63/63 components passing
- **Cold-start:** Fresh agents produce compiling components with 0 errors (stress-tested 2026-02-20)
- **Component lifecycle:** New component from YAML to passing tests validated 19+ times
- **Convergence:** Systematic stress testing across all generative skills -- 0 cold-start errors
- **Subassemblies:** 10-round iteration, R10 achieved zero errors from cold-start agent

## Critical Build Rules

- **`redo clean` is always safe** on any directory (framework or project). If redo state corrupts (STORAGE_ERROR), run `redo clean_all` on BOTH adamant and project dirs.
- **NEVER manually delete build directories** (`rm -rf build`, `rm -rf */build`, etc.). Use `redo clean` or `redo clean_all`. Bulk-deleting build dirs corrupts redo state and may require container recreation to recover.
- **`redo coverage`** runs from the component's `test/` directory. No `redo clean` needed.
- **`source project/env/activate`** (not `adamant/env/activate`) -- sets BUILD_ROOTS correctly.
- **Never run concurrent redo processes** in the same container -- corrupts redo state.
