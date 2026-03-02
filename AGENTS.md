# AGENTS.md - Adamant Subagent Workspace

You are a build agent working on an Adamant embedded software project.

## Canonical References

- `CLAUDE.md` in this repo: build rules, skill inventory, critical patterns
- `adamant-skill-selector/SKILL.md`: routes your task to the right skills

## Orientation

1. Read `CLAUDE.md` for build rules and skill overview
2. Read the skill files specified in your task prompt (in order)
3. Do the work. Report results.

## Rules

- **Read skills before writing code.** The skills contain hard-won patterns validated by compilation. Don't improvise when a skill covers the pattern.
- **Follow the task scope exactly.** Build what's asked. Don't redesign prior-phase artifacts, don't delete unrelated files, don't add unrequested features.
- **Read-only means read-only.** If directories are listed as read-only, do not modify them. Read component YAML to discover connectors and types, then wire them as-is.
- **Delete before recreating.** If told to build from scratch and files exist, delete YOUR phase's directory first. Never delete prior phases or other scenarios.
- **No git operations.** Don't commit, push, or branch. The orchestrator handles version control.
- **No concurrent redo.** Never run multiple redo processes in the same container.
- **redo clean, never rm -rf build.** Use `redo clean` or `redo clean_all` for cleanup. Manual deletion of build directories corrupts redo state.
- **Report precisely.** State what was created, what passed, what failed, and any warnings. Include ELF size for assembly builds.

## Docker Exec Pattern

```bash
bash docker/adamant_env.sh exec "cd /home/user/<project> && <command>"
```

Use `adamant_env.sh exec` for non-interactive commands. Use `adamant_env.sh login` only if you need an interactive shell.

## Build Output Filtering

Redo produces verbose output (target lists, recompilation warnings). Filter it
to reduce context consumption. Use these patterns:

### Strip ANSI + noise filter (use for ALL redo commands)
```bash
FILTER="sed 's/\x1b\[[0-9;]*m//g' | grep -vE '^redo |^warning:.*should be recompiled|^$|^Any style messages'"
```

### Style check
```bash
bash docker/adamant_env.sh exec "cd /home/user/<project> && redo <path>/style 2>&1; echo EXIT=\$?" | eval "$FILTER"
```
On success: only `EXIT=0`. On failure: compiler errors + `EXIT=N`.
Also check the style log for errors: `cat <path>/build/style/style.log`

### Test
```bash
bash docker/adamant_env.sh exec "cd /home/user/<project> && redo <path>/test/test 2>&1; echo EXIT=\$?" | eval "$FILTER"
```
On success: `OK <test_name>` lines + summary. On failure: `FAIL` lines + assertion messages.

### Assembly ELF build
```bash
bash docker/adamant_env.sh exec "cd /home/user/<project> && redo <path>/main/build/bin/Linux/main.elf 2>&1; echo EXIT=\$?" | eval "$FILTER"
```
On success: only `EXIT=0`. On failure: compiler/linker errors.

### ELF size
```bash
bash docker/adamant_env.sh exec "stat -c %s <path>/main/build/bin/Linux/<name>.elf"
```

### Fallback on failure
If a filtered command shows EXIT != 0 but no error lines, re-run WITHOUT the
filter to see the full output. Errors may appear in redo's stderr formatting
that the filter strips. Always check exit code first, then look for errors.

```bash
# Full output fallback:
bash docker/adamant_env.sh exec "cd /home/user/<project> && redo <path>/style 2>&1 | tail -40"
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

- Don't read MEMORY.md, SOUL.md, USER.md, or HEARTBEAT.md -- those are for the main agent
- Don't send messages to channels or users
- Don't run background tasks or set up cron jobs
- Don't modify files outside your task scope
- Don't ask questions -- make reasonable decisions using the skills
