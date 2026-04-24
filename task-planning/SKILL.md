---
name: task-planning
description: Meta-skill for executing complex multi-step tasks under time pressure. Use when a task has 5+ deliverables, a timeout constraint, or risk of getting stuck debugging one issue. Teaches upfront planning, time-boxing, progress tracking, and honest reporting.
---

# Task Planning

Execute complex tasks systematically under time constraints. This skill is
about HOW to work, not WHAT to build.

## When to Use

- Task has 5+ discrete deliverables (components, files, tests)
- Session has a timeout (any spawned sub-agent)
- Work is repetitive (build N things following the same pattern)
- Prior attempts timed out or got stuck debugging one item

## Step 1: Inventory (first 2 minutes)

Before writing ANY code, enumerate every deliverable:

```
# Example: "Build 20 components with tests"
PLAN:
- [ ] Component 1: survival_heater_controller (yaml, impl, test)
- [ ] Component 2: temperature_watchdog (yaml, impl, test)
- [ ] ...
- [ ] Component 20: science_thermal_telemetry (yaml, impl, test)
- [ ] admt style --all (all components)
- [ ] admt test --all (all components)
Total: 20 components x 3 files = 60 files + 2 verification steps
```

Write this to a scratch file (`/tmp/task_plan.md`) so you can track progress.

## Step 2: Time Budget

Calculate time per item:

```
Timeout: 30 minutes
Items: 20 components + style + test
Budget: 30 min / 22 items = ~80 seconds each
Reserve: 5 min for unexpected issues
Adjusted: 25 min / 22 items = ~68 seconds each
```

If the math says you can't finish, say so immediately. Propose splitting
the work ("I can do 10 components in this session, need a second session
for the rest").

## Step 3: Execute in Batches

Don't build one component end-to-end then the next. Batch by operation:

**Round 1: All YAML files** (fastest, most mechanical)
- Create all component.yaml, commands.yaml, events.yaml, data_products.yaml
- This is the foundation -- errors here cascade, so get it right

**Round 2: All implementations**
- Write all .ads and .adb files
- Follow the same pattern for each -- don't over-engineer individual components

**Round 3: All test files**
- Create test dirs, env.py, tests.yaml, test implementations
- Use the same test structure for each component

**Round 4: Verify**
- `admt style` on each component
- `admt test` on each component
- Record pass/fail per component

Batching is faster because you stay in the same mental context and can
copy-paste patterns.

## Step 4: Time-Box Problems

When something breaks:

```
IF time_spent_on_this_item > 2x budget:
    Note the error in scratch file
    Move to next item
    Come back IF time remains at the end
```

**Never spend more than 3 minutes debugging a single item.** Note the error
message, skip it, keep building. You can always come back. You can't get
time back.

Common traps:
- Style warning on one file -- note it, fix later in batch
- Compilation error in one component -- might be a typo, note and move on
- Test failure -- record the assertion, move on
- Unfamiliar framework pattern -- read the skill once, apply everywhere, don't research per-component

## Step 5: Progress Checkpoints

Every 5 items (or every 5 minutes), update your scratch file:

```
PROGRESS (12 min elapsed, 18 min remaining):
- [x] Components 1-8: yaml + impl + test done
- [ ] Components 9-20: yaml done, impl in progress
- [!] Component 3: style warning "redundant with clause"
- [ ] Style check: pending
- [ ] Test run: pending
```

This prevents the "where was I?" problem after a long debugging detour.

## Step 6: Report Honestly

When finished (or when time runs out), report:

```
COMPLETED: 18/20 components (yaml + impl + test)
PASSED: style 18/18, test 18/18
INCOMPLETE:
  - Component 3: compilation error "missing semicolon line 42"
  - Component 17: test assertion failure "expected 5, got 0"
SKIPPED: none
TIME: 28 min / 30 min budget
```

**Never claim success if items are incomplete.** The orchestrator needs
accurate information to decide next steps.

## Anti-Patterns

### The Rabbit Hole
Spending 15 minutes debugging one style warning while 19 components
remain unbuilt. **Fix: time-box at 3 minutes, skip and return.**

### The Perfectionist
Writing 6 elaborate tests per component when 2-3 focused tests would
suffice and you have 20 components to build. **Fix: consistent depth
across all items, not deep on some and absent on others.**

### The Silent Timeout
Running out of time without reporting what's done vs what's not.
**Fix: checkpoint every 5 minutes, always end with a status report.**

### The Scope Creep
Adding features not in the spec ("this component should also handle X").
**Fix: build exactly what's asked, note enhancement ideas in the report.**

### The Rewrite Loop
Rebuilding component 1 three times to get it perfect before starting
component 2. **Fix: good enough on first pass, polish in a final pass
if time permits.**

## Template: Scratch File

Create this at session start:

```markdown
# Task Plan
Timeout: {N} minutes
Items: {count}
Budget: {seconds} per item ({minutes} min reserve)

## Deliverables
- [ ] Item 1
- [ ] Item 2
...

## Issues
(note problems here with item name + error message)

## Checkpoints
- {time}: {status}
```

## Scaling Rules

| Items | Strategy |
|-------|----------|
| 1-4   | No planning needed, just build |
| 5-10  | Light planning, batch by type |
| 11-20 | Full planning, strict time-boxing |
| 20+   | Request split into multiple sessions |

## Integration with Other Skills

This skill is a meta-layer. It doesn't replace technical skills -- it
organizes how you apply them:

1. Read task-planning FIRST (this file)
2. Read technical skills (component-dev, testing, etc.)
3. Make your plan
4. Execute using technical skill patterns
5. Track progress per this skill's guidance
