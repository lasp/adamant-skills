# Adamant Agent Skills

Skills for AI-assisted development with the [Adamant](https://github.com/lasp/adamant) embedded software framework. Every pattern validated by compilation against a real GNAT/GNATprove toolchain.

## Project Precedence

These skills describe the Adamant framework generically. **When you are working in a project that provides its own instructions or skills — a project `CLAUDE.md`/`AGENTS.md`, an `agents/` skill directory, or any project-local guidance — those take precedence over anything here.** Use the project's guidance for every task it covers, and do not fall back to a generic skill the project has superseded. These generic skills remain the authority only for framework tasks the project does not cover.

## Agent Configuration Files

This repo contains three agent instruction files. Copy the ones your tooling uses to your project root:
- **CLAUDE.md** (this file) -- the Claude Code entry point: build rules, skill inventory, Claude-specific load order. Functionally the Claude Code counterpart to `AGENTS.md`.
- **AGENTS.md** -- vendor-neutral agent instructions ([agents.md](https://agents.md/) convention): the same build rules + skill inventory for any coding agent or tool.
- **SUBAGENT_CONTRACT.md** -- handoff contract for an orchestrated/headless build subagent: a scoped posture (no questions, no git, output filtering, quality gates) layered on top of the shared instructions.

## Running Commands in the Adamant Environment

**Use [`admt`](https://github.com/Jbsco/admt) (The Adamant Multitool) as the primary entry point for all Adamant work.** admt wraps redo, docker compose, and env activation behind one CLI. Run it from the host, on or below a registered project root; it forwards into the container automatically.

```bash
admt what               # List buildable targets in the current dir
admt build              # redo all
admt test               # redo test (add --all for test_all)
admt style              # redo style
admt templates          # redo templates + optional stub copy
admt env start          # Start the container
admt env exec "<cmd>"   # Arbitrary command inside the container
```

**Prefer admt everywhere.** The `adamant_env.sh exec` form remains as a fallback for operations admt has not yet absorbed (MVP is complete; post-MVP will keep closing the gap):

```bash
# Fallback only -- when admt does not cover the case.
bash docker/adamant_env.sh exec "cd /home/user/<project>/path/to/dir && <command>"
```

**`admt what`** is what you run first in any directory to discover what can be built. It replaces `redo what`.

**admt is self-describing.** `admt --help` lists every command and global flag; `admt <command> --help` shows command-specific options (e.g. `admt env --help`, or `admt templates --help`, which reveals `--undo`). The tables below are a quick reference, not exhaustive -- when you need an advanced or unlisted subcommand or flag, run `--help` rather than guessing or defaulting to the fallback.

### admt is new -- report gaps, don't silently work around them

admt's MVP just landed; post-MVP work is ongoing. Gaps and bugs exist. If admt errors on a case you expected it to handle, or its output is visibly wrong:

1. **Fall back to `adamant_env.sh exec` (or the equivalent inside `admt env exec`) to unblock the task.** Don't get stuck.
2. **Surface the gap in your final report.** Include:
   - The admt command you tried
   - The error or observed deviation (copy the exact message when possible)
   - The fallback form that worked
   - admt version from `admt --version`

   The user can then file an issue at <https://github.com/Jbsco/admt/issues>.

Silent fallback is worse than no fallback -- it hides the signal that admt needs fixing. Verbose fallback keeps admt improving.

### redo target -> admt command

| Legacy (`adamant_env.sh exec "... redo X"`) | admt form |
|---|---|
| `redo what` | `admt what` |
| `redo all` | `admt build` |
| `redo <target>` | `admt build <target>` |
| `redo test` / `redo test_all` | `admt test` / `admt test --all` |
| `redo style` / `redo style_all` | `admt style` / `admt style --all` |
| `redo analyze` / `redo analyze_all` | `admt analyze` / `admt analyze --all` |
| `redo clean` / `redo clean_all` | `admt clean` / `admt clean --all` |
| `redo coverage` / `redo coverage_all` | `admt coverage` / `admt coverage --all` |
| `redo prove` | `admt prove` |
| `redo publish` / `redo publish_all` | `admt publish` / `admt publish --all` |
| `redo templates` | `admt templates` (plus stub copy / `--undo`) |
| `DEBUG=1 redo ...` | `admt -d ...` |

Every passthrough command also accepts an optional path argument -- `admt build src/components/foo` is equivalent to `cd src/components/foo && admt build`. Resolved against cwd, symlinks canonicalized, must fall under a registered volume mount.

### admt env subcommands

| Operation | admt form |
|---|---|
| Start / stop / restart the container | `admt env start` / `stop` / `restart` |
| Interactive shell | `admt env login` |
| Arbitrary command inside the container | `admt env exec "<cmd>"` |
| Rebuild cached env snapshot | `admt env refresh` |
| Container status | `admt env status` |
| Register a project | `admt env init [path]` |
| Switch active project | `admt env use <name>` |
| List registered projects | `admt env list` |
| Remove container (+ volumes / image) | `admt env rm [--volumes \| --image \| --remove-all]` |

**NEVER `source env/activate` or `source project/env/activate` directly.** admt (and the `adamant_env.sh exec` fallback) handles activation automatically via a cached snapshot.

## Quick Start

Read `adamant-skill-selector/SKILL.md` first. It routes your task to the right 1-2 skills.

## Skill Inventory (25 skills + 1 meta-skill = 26 total, ~25400 lines with refs)

| Skill | Lines | Purpose |
|-------|-------|---------|
| `adamant-skill-selector` | 403 | **Read first.** Maps tasks to skills. |
| `adamant-testing` | 2647 | Test harness, History API, assertions, coverage, advanced patterns |
| `adamant-tools` | 2221 | API inspector, component scaffolder, YAML validator (Python scripts) |
| `adamant-component-dev` | 2302 | Components: YAML models, generated API, implementation patterns, LASEL |
| `adamant-assembly-dev` | 1455 | Assemblies: scheduling, routing, ID assignment, runtime monitoring |
| `adamant-cosmos-integration` | 1955 | CCSDS pipeline, COSMOS plugin build/load |
| `adamant-style` | 1152 | Ada/YAML/Python style rules enforced by `redo style` |
| `adamant-formal-verification` | 1528 | SPARK contracts, GNATprove, ghost lemmas, proof chains |
| `adamant-build-system` | 1057 | Redo commands, code gen, build paths |
| `adamant-debugging` | 1129 | Three-layer debugging: GDB (tests/assemblies), post-mortem LCH/stack-trace triage + symbolizer script, target/compiler pitfalls |
| `adamant-skill-creation` | 1341 | Creating, validating, and refactoring Adamant skills |
| `adamant-skill-campaign` | 425 | Cold-start skill-validation campaigns in-session via the Workflow tool (HIT/MISS/GAP) |
| `adamant-cosmos-testing` | 1043 | Integration test scripts via COSMOS scripting API |
| `adamant-cosmos-suite-results` | 133 | COSMOS suite execution (openc3cli / Script Runner REST API) + result verification |
| `adamant-regression-suite` | 700 | Black-box Python regression suites driven through the COSMOS cmd/tlm interface (source-blind) |
| `adamant-cosmos-tool-creation` | 638 | Custom COSMOS web UI tools + widgets: decision ladder (screen/widget/tool/microservice), build contract, data feeds |
| `adamant-framework-components` | 675 | Catalog of all 58 built-in components + audit |
| `adamant-type-system` | 931 | YAML type definitions, format codes, Ada type hierarchy |
| `adamant-subassemblies` | 546 | Splitting assemblies into reusable subassemblies, nesting, wiring rules |
| `adamant-project-setup` | 546 | New project scaffolding, adamant_env.sh, Docker, config |
| `knowledge-acquisition` | 699 | Systematic codebase study with sub-agents |
| `adamant-code-review` | 362 | Component, test, type, assembly review checklists, design assessment |
| `adamant-framework-internals` | 441 | Framework Python model internals, code gen debugging, `is` vs `==` pitfall |
| `adamant-generator-dev` | 672 | Custom generators: Ada source, YAML types, HTML docs, ground artifacts from YAML |
| `high-assurance-design` | 304 | Design-by-invariant, non-goals, formal verification |

**Total:** ~25000 lines (SKILL.md + references)

## Meta-Skills

| Skill | Lines | Purpose |
|-------|-------|---------|
| `task-planning` | 193 | Time-boxing, progress tracking, batch execution for large tasks |

**Read `task-planning/SKILL.md` FIRST** for any task with 5+ deliverables or 10+ components. It teaches how to manage time, track progress, and avoid rabbit holes.

## Key Principles

- **Framework-specific only.** Generic Ada/SPARK knowledge excluded.
- **Compiler-validated.** 30+ rounds of build-test-fix cycles across 100+ components + unit tests. Components compile clean on first try when skills are followed.
- **Selector-driven.** Load 1-2 skills per task, not all 24.
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

- **`admt clean` is always safe** on any directory (framework or project). If redo state corrupts (STORAGE_ERROR), run `admt clean --all` on BOTH the project root AND the framework root (see scope note below).
- **`admt clean --all` is per-directory, not workspace-wide.** It runs `redo clean_all` recursively under the cwd's container path only. Other volume mounts in the active project's compose -- the framework at `/home/user/adamant`, sibling component repos -- are NOT cleaned by the same invocation. To clean another mount, `cd` into it on the host first; admt's path mapper accepts any host path under the active project's volume mounts. Example: `cd ~/cs/adamant && admt clean --all` cleans the framework tree when the active project mounts it.
- **NEVER manually delete build directories** (`rm -rf build`, `rm -rf */build`, etc.). Use `admt clean` or `admt clean --all`. Bulk-deleting build dirs corrupts redo state and may require container recreation (`admt env rm --volumes && admt env start`) to recover.
- **`admt coverage`** runs from the component's `test/` directory. No `admt clean` needed.
- **Do not `source env/activate` directly.** admt handles environment activation via a cached snapshot; `adamant_env.sh exec` does too for the fallback case.
- **Never run concurrent builds** in the same container -- corrupts redo state. admt serializes per-invocation; do not spawn multiple `admt build` / `admt test` runs at once.
