# Skill Refinement Methodology
<!-- validated: methodology v1 2026-02-20 -->

## Overview

Systematic process for squeezing maximum competency out of each skill through:
1. Consistency audit (cross-skill alignment)
2. Zero-to-complete stress tests (cold-start sub-agent builds from nothing)
3. Error-driven skill improvement (fix what breaks)
4. Script generation for sticking points (automate what agents get wrong)

## Phase 1: Consistency Audit

Quick pass over all skills checking:
- [ ] Cross-references between skills are accurate (connector kinds, type names, etc.)
- [ ] No contradictions between SKILL.md files
- [ ] Component count, format codes, connector types match framework reality
- [ ] Reference files have version tags
- [ ] Scripts are executable and tested

## Phase 2: Stress Test Design

Each skill gets a "zero-to-complete" test exercise:

| Skill | Exercise | Validation |
|-------|----------|------------|
| component-dev | Create new component from scratch (YAML + impl + env.py) | `redo style && redo test` |
| testing | Write full test suite for existing component | `redo coverage` |
| assembly-dev | Create mini assembly with 3+ components | `redo build/bin/Linux/main.elf` |
| subassemblies | Create assembly with 2+ subassemblies | ELF builds clean |
| type-system | Create packed type + enum + array + record | `redo style` on types dir |
| algorithm-wrapping | Wrap a C function into Adamant component | `redo test` on wrapped component |
| build-system | Set up build for new source directory | `redo` succeeds |
| style | Fix intentionally messy files | `redo style` passes |
| framework-components | Select components for a given requirement set | Correct selections verified |
| cosmos-integration | Generate COSMOS plugin config | Valid plugin YAML |
| project-setup | Bootstrap new project directory structure | `redo` from clean state |

## Phase 3: Iteration Loop

```
for each skill:
  1. Spawn sub-agent with ONLY that skill + selector
  2. Give it the exercise from Phase 2
  3. Sub-agent creates files in bot_station repo (test/ area)
  4. Build with redo in Docker
  5. Collect errors
  6. Classify errors:
     a. Skill gap -> update SKILL.md or reference
     b. Repeated mistake -> create script
     c. Context limit -> split skill or trim references
  7. Commit skill fixes
  8. Repeat until 0 errors from cold start
```

## Phase 4: Script Generation

When agents repeatedly fail at the same step, create a script:

```bash
# Example: agents forget .all_path in source dirs
adamant-component-dev/scripts/mk_all_path.sh  # already exists

# Potential new scripts:
adamant-testing/scripts/gen_test_scaffold.sh    # generate test dir structure
adamant-assembly-dev/scripts/validate_wiring.sh # check connection consistency
adamant-type-system/scripts/check_packed.sh     # validate packed type sizes
```

Script criteria:
- Agent gets it wrong >2 times across rounds
- The check/generation is mechanical (not creative)
- Script output is deterministic and verifiable

## Phase 5: Regression

After all skills pass individually, run combined exercises:
1. New component + test + assembly integration (3 skills combined)
2. Algorithm wrap + type creation + assembly (3 skills combined)
3. Full project: types + components + tests + assembly + subassemblies (5+ skills)

## Metrics

Track per skill:
- Round number
- Error count
- Error categories (YAML schema, Ada syntax, build system, connector wiring, etc.)
- Time to completion
- Context tokens used

Convergence target: 0 errors on cold start for 2 consecutive rounds.

## Scheduling

Use cron to spawn iteration rounds automatically:
- One round every 30 minutes during active refinement
- Each round targets ONE skill (rotate through skills)
- Results logged to memory/skill-refinement/SKILL-NAME-RN.md
- Main session notified on completion via Signal

## State File

State file (project-specific, not in skills repo):
```json
{
  "currentSkill": "component-dev",
  "round": 1,
  "phase": "stress-test",
  "results": {
    "component-dev": {"rounds": 0, "lastErrors": null, "converged": false},
    "testing": {"rounds": 0, "lastErrors": null, "converged": false},
    ...
  },
  "schedule": "every-30-min"
}
```
