# SUBAGENT_CONTRACT.md - Adamant Build-Subagent Handoff Contract

You are a build subagent working on an Adamant embedded software project -- spawned by an orchestrator to do a scoped piece of work and report back. This file is the **handoff contract**: the posture and guardrails for that role. It is *not* the general repo instructions; for the shared build rules and skill overview, read `AGENTS.md` (the vendor-neutral instructions, or `CLAUDE.md`, its Claude Code counterpart).

## Canonical References

- `AGENTS.md` (or `CLAUDE.md`): build rules, skill inventory, critical patterns -- the shared instructions every agent in this repo uses
- `adamant-skill-selector/SKILL.md`: routes your task to the right skills

## Orientation

1. Read `AGENTS.md` for build rules and skill overview
2. Read the skill files specified in your task prompt (in order)
3. Do the work. Report results.

## Rules

- **Read skills before writing code.** The skills contain hard-won patterns validated by compilation. Don't improvise when a skill covers the pattern.
- **Follow the task scope exactly.** Build what's asked. Don't redesign prior-phase artifacts, don't delete unrelated files, don't add unrequested features.
- **Read-only means read-only.** If directories are listed as read-only, do not modify them. Read component YAML to discover connectors and types, then wire them as-is.
- **Delete before recreating.** If told to build from scratch and files exist, delete YOUR phase's directory first. Never delete prior phases or other scenarios.
- **No git operations.** Don't commit, push, or branch. The orchestrator handles version control.
- **No concurrent builds.** Never run multiple `admt build` / `admt test` invocations in the same container -- corrupts redo state.
- **`admt clean`, never `rm -rf build`.** Use `admt clean` or `admt clean --all` for cleanup. Manual deletion of build directories corrupts redo state.
- **Report precisely.** State what was created, what passed, what failed, and any warnings. Include ELF size for assembly builds.

## Exec Pattern

**Use [`admt`](https://github.com/Jbsco/admt) for all builds, tests, and container operations.** admt is the primary entry point -- it wraps redo, docker compose, and env activation.

```bash
admt <build-command> [path]       # build / test / style / analyze / coverage / prove / publish / templates / clean
admt env exec "<command>"         # Arbitrary command inside the container (non-redo work)
admt env login                    # Interactive shell
```

**admt is self-describing -- discover, don't guess.** The patterns above cover the common cases. For anything not listed, ask admt directly rather than guessing or falling back prematurely:

```bash
admt --help            # all commands + global flags (-v/-q/-d/-y/-f)
admt <command> --help  # command-specific options, e.g. `admt env --help`, `admt templates --help` (--undo)
```

The `AGENTS.md` tables are a quick reference, not exhaustive -- e.g. `admt env --help` lists subcommands (`pull`, `push`, `env build`) the table omits.

The `bash docker/adamant_env.sh exec "..."` form remains as a fallback for operations admt has not yet absorbed (MVP is complete; post-MVP will keep closing the gap). See `AGENTS.md` for the full redo -> admt translation table.

**admt is new -- if it errors on something it should handle, fall back to `bash docker/adamant_env.sh exec` AND report the gap in your final report** (admt command tried, exact error, fallback form that worked, `admt --version`). See `AGENTS.md` §"admt is new" for the full rule. Silent fallback hides the signal that admt needs fixing.

## Build Output Filtering

Redo produces verbose output (target lists, recompilation warnings). admt's streaming output is already scoped (``build`` verbs highlighted, depth paths preserved), and ``-q`` / ``--quiet`` suppresses successful output entirely while still printing the command + full output on failure. Prefer ``admt -q`` for agent-driven builds where you only care about pass/fail + diagnostics.

```bash
# Agent-friendly default: silent on success, full diagnostic on failure.
admt -q <build-command> [path]; echo "EXIT=$?"
```

For cases where you need to filter the streaming output yourself (e.g., when using the fallback form), the ANSI + noise filter still applies:

```bash
# Use with the adamant_env.sh fallback when admt is not applicable.
FILTER="sed 's/\x1b\[[0-9;]*m//g' | { grep -vE '^redo |^warning:.*should be recompiled|^$|^Any style messages' || true; }"
```

### Style check
```bash
admt -q style <path>; echo "EXIT=$?"
```
On success: only `EXIT=0`. On failure: admt prints ``Failed (exit N): docker exec ...`` plus redo's diagnostic. Also check the style log for errors: ``cat <path>/build/style/style.log``

### Test
```bash
admt -q test <path>; echo "EXIT=$?"
```
On success: only `EXIT=0`. On failure: test framework `FAIL` lines + assertion messages. Drop ``-q`` to see ``OK <test_name>`` lines on success.

### Assembly ELF build
```bash
admt -q build <path>/main/build/bin/Linux/main.elf; echo "EXIT=$?"
```
admt's passthrough accepts a file target as the positional argument. On success: only `EXIT=0`. On failure: compiler/linker errors.

### ELF size
```bash
admt env exec "stat -c %s <path>/main/build/bin/Linux/<name>.elf"
```

### Fallback on failure
If ``admt -q`` shows EXIT != 0 but the diagnostic is terse, re-run without ``-q`` (or with ``-v`` for the underlying docker command too) to get the full build output.

```bash
# Full output:
admt build <path>/style
# Or with the docker compose exec line echoed:
admt -v build <path>/style
```

### Do NOT paste full build logs
In your final report, include only:
- Pass/fail status and exit code
- Specific error messages (if any)
- Test result summary (OK/FAIL lines + totals)
- ELF size (for assembly phases)

## Quality Gates

Every phase must pass before reporting success:
- `redo style`: exit 0 (boundary-connector warnings acceptable for assemblies)
- `redo test`: all tests pass (component phases)
- ELF builds (assembly phases)

## What Not To Do

- Don't send messages to channels or users
- Don't run background tasks or set up cron jobs
- Don't modify files outside your task scope
- Don't ask questions -- make reasonable decisions using the skills
