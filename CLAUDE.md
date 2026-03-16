# Adamant Agent Skills

Skills for AI-assisted development with the [Adamant](https://github.com/lasp/adamant) embedded software framework. Every pattern validated by compilation against a real GNAT/GNATprove toolchain.

## Agent Configuration Files

This repo contains three agent prompt files. Copy them to your project root:
- **CLAUDE.md** -- Claude Code CLI system prompt (build rules, skill inventory)
- **AGENTS.md** -- OpenClaw subagent workspace rules (task scope, docker exec, quality gates)
- **SOUL.md** -- OpenClaw subagent voice and disposition (technical, no filler, scoped)

## Running Commands in the Adamant Environment

All adamant and redo commands must be run inside the adamant environment container. Use the `adamant_env.sh exec` function from the project's `docker/` directory:

```bash
bash docker/adamant_env.sh exec "cd /home/user/<project>/path/to/dir && redo what"
bash docker/adamant_env.sh exec "cd /home/user/<project>/path/to/dir && redo test"
```

**`redo what`** lists all available build targets in any directory. Agents should run `redo what` first to discover what can be built before attempting builds.

**NEVER use `source env/activate` or `source project/env/activate`.** The `adamant_env.sh exec` function handles environment activation automatically via a cached snapshot, and is the only supported method for agents.

## Quick Start

Read `adamant-skill-selector/SKILL.md` first. It routes your task to the right 1-2 skills.

## Skill Inventory (20 skills, ~19300 lines with refs)

| Skill | Lines | Purpose |
|-------|-------|---------|
| `adamant-skill-selector` | 267 | **Read first.** Maps tasks to skills. |
| `adamant-testing` | 2515 | Test harness, History API, assertions, coverage, advanced patterns |
| `adamant-tools` | 2216 | API inspector, component scaffolder, YAML validator (Python scripts) |
| `adamant-component-dev` | 1960 | Components: YAML models, generated API, implementation patterns, LASEL |
| `adamant-algorithm-wrapping` | 1896 | C++ -> C shim -> Ada bindings -> Adamant component pipeline |
| `adamant-assembly-dev` | 1416 | Assemblies: scheduling, routing, ID assignment, runtime monitoring |
| `adamant-cosmos-integration` | 1254 | CCSDS pipeline, COSMOS plugin build/load |
| `adamant-style` | 1078 | Ada/YAML/Python style rules enforced by `redo style` |
| `adamant-formal-verification` | 609 | SPARK contracts, GNATprove, ghost lemmas, proof chains |
| `adamant-build-system` | 973 | Redo commands, code gen, build paths |
| `adamant-skill-creation` | 839 | Creating, validating, and refactoring Adamant skills |
| `adamant-cosmos-testing` | 687 | Integration test scripts via COSMOS scripting API |
| `adamant-framework-components` | 675 | Catalog of all 58 built-in components + audit |
| `adamant-type-system` | 567 | YAML type definitions, format codes, Ada type hierarchy |
| `adamant-subassemblies` | 504 | Splitting assemblies into reusable subassemblies, nesting, wiring rules |
| `adamant-project-setup` | 484 | New project scaffolding, adamant_env.sh, Docker, config |
| `knowledge-acquisition` | 471 | Systematic codebase study with sub-agents |
| `adamant-code-review` | ~170 | Component, test, type, assembly review checklists, design assessment |
| `adamant-framework-internals` | 441 | Framework Python model internals, code gen debugging, `is` vs `==` pitfall |
| `high-assurance-design` | 304 | Design-by-invariant, non-goals, formal verification |

**Total:** ~19100 lines (includes tool scripts)

## Meta-Skills

| Skill | Lines | Purpose |
|-------|-------|---------|
| `task-planning` | ~180 | Time-boxing, progress tracking, batch execution for large tasks |

**Read `task-planning/SKILL.md` FIRST** for any task with 5+ deliverables or 10+ components. It teaches how to manage time, track progress, and avoid rabbit holes.

## Key Principles

- **Framework-specific only.** Generic Ada/SPARK knowledge excluded.
- **Compiler-validated.** 30+ rounds of build-test-fix cycles across 100+ components + unit tests. Components compile clean on first try when skills are followed.
- **Selector-driven.** Load 1-2 skills per task, not all 18.
- **Three-tier prompt strategy:** This file (CLAUDE.md) -> skill-selector -> deep skills. Load order matters for cache efficiency:
  1. This file -- loaded automatically as system prompt
  2. `adamant-skill-selector/SKILL.md` -- always the first skill read
  3. Task-specific skills -- in the order the selector specifies
  4. Task request / user content -- always last
- **~300-500 line SKILL.md target.** Dense patterns in SKILL.md, detailed examples in references/.
- **Cache-optimized structure.** Stable content (skills) forms a cacheable prefix; variant content (task requests) goes last. Deterministic read order in the skill selector enables cross-call cache hits. See README.md for full analysis.
- **No project-specific content.** Generic skills contain zero project names or paths. Project-specific guidance lives in the project repo.
- **No commits/push instructions.** Skills are agent-level -- orchestrators handle git.
- **No structural coverage ceiling.** All paths are coverable with proper testing techniques.
- **All style warnings are fixable.** No "template artifacts" -- every warning has a solution.

## Validation Results

- **Style:** 221/221 directories, 0 failures
- **Coverage:** 89%+ aggregate across 100+ components
- **Invalid_Command tests:** 63/63 components passing
- **Cold-start:** Fresh agents produce compiling components with 0 errors (stress-tested 2026-02-20)
- **Formal verification:** SPARK proof chain pattern, ghost lemma discipline, GNATprove integration
- **Component lifecycle:** New component from YAML to passing tests validated 19+ times
- **Convergence:** Systematic stress testing across all generative skills -- 0 cold-start errors
- **Subassemblies:** 10-round iteration, R10 achieved zero errors from cold-start agent

## Multi-Phase Workflow Rules

When building as part of a phased pipeline (types -> components -> assembly):
- **Read prior-phase artifacts, don't rewrite them.** If types and components already exist, use them as-is. Your job is to wire them, not redesign them.
- **Respect read-only boundaries.** If the task lists directories as read-only, do not modify, rename, or delete files in those directories.
- **Delete before creating from scratch.** If the task says "create from scratch" but files already exist from a prior iteration, delete them first (only in YOUR phase's directory, never prior phases).
- **Don't delete unrelated files.** Other scenarios' components in the same repo are not yours to touch.

## Critical Build Rules

- **`redo clean` is always safe** on any directory (framework or project). If redo state corrupts (STORAGE_ERROR), run `redo clean_all` on BOTH adamant and project dirs.
- **NEVER manually delete build directories** (`rm -rf build`, `rm -rf */build`, etc.). Use `redo clean` or `redo clean_all`. Bulk-deleting build dirs corrupts redo state and may require container recreation to recover.
- **`redo coverage`** runs from the component's `test/` directory. No `redo clean` needed.
- **Use `bash docker/adamant_env.sh exec "command"`** to run all build commands. Never use `source env/activate` directly.
- **Never run concurrent redo processes** in the same container -- corrupts redo state.
