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
| component-dev | Create new component from scratch (YAML + impl + env.py) | `admt style && admt test` |
| testing | Write full test suite for existing component | `admt coverage` |
| assembly-dev | Create mini assembly with 3+ components | `admt build build/bin/Linux/main.elf` |
| subassemblies | Create assembly with 2+ subassemblies | ELF builds clean |
| type-system | Create packed type + enum + array + record | `admt style` on types dir |
| algorithm-wrapping | Wrap a C function into Adamant component | `admt test` on wrapped component |
| build-system | Set up build for new source directory | `redo` succeeds |
| style | Fix intentionally messy files | `admt style` passes |
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

## Experience Pool (Group-Evolution Pattern)

Inspired by group-evolving agents (GEA): treat validation rounds across skills as a
shared experience pool rather than isolated branches.

### Cross-Skill Experience Aggregation

After each validation round, extract lessons that apply beyond the tested skill:

```
Round result for component-dev:
  Error: "Tick.T needs Count => N (Unsigned_32 not Unsigned_16)"
  -> Primary fix: component-dev SKILL.md
  -> Cross-skill propagation: testing skill (tester stimulus patterns),
     assembly-dev (rate group tick types)
```

Maintain a shared error log across all skills:
```
memory/skill-refinement/cross-skill-errors.md
  # Errors discovered in one skill that affect others
  ## <date> component-dev R5
  - Tick.T Count type: also affects testing, assembly-dev [PROPAGATED]
  - Connector call syntax (get=no args): also affects algorithm-wrapping [PROPAGATED]
```

### Ancestor Tracking

Track which validation sessions contributed to each skill's current state.
Skills with more diverse ancestry (fixes from multiple independent rounds/agents)
are empirically more robust than those refined in a single session.

Add to state file per skill:
```json
{
  "component-dev": {
    "rounds": 5,
    "ancestors": ["R1-opus-2026-02-12", "R3-sonnet-2026-02-15", "R5-sonnet-2026-02-20"],
    "ancestorCount": 3,
    "converged": true
  }
}
```

Skills with ancestorCount < 2 are candidates for additional stress testing with
a different model or task complexity level.

### Performance-Novelty Selection

When choosing which skill to validate next, balance:
- **Performance**: error rate in most recent round (lower = better performing)
- **Novelty**: how long since last validation, or how much the skill changed since last test

Priority formula (informal):
```
priority = (days_since_last_test * lines_changed_since_test) / (1 + recent_error_rate)
```

High priority = untested changes accumulating. Low priority = recently validated, few changes.

### Population-Wide Quality

Don't just track best-case (best agent on best skill). Track worst-case:
- What is the worst cold-start error count across ALL skills?
- Which skill produces the most errors from a fresh agent?
- The floor matters more than the ceiling for reliability.

Report format:
```
Skill Health (worst-case across all skills):
  Worst: assembly-dev (2 errors, last tested 2026-02-18)
  Best:  type-system (0 errors, last tested 2026-02-20)
  Floor: 2 errors  <- this is the number to drive to zero
```

## Scheduling

Drive iteration rounds with the Workflow tool (see [adamant-skill-campaign](../../adamant-skill-campaign/SKILL.md)) -- its control flow runs the rounds in-session, with no external scheduler:
- Each round targets ONE skill (rotate through skills)
- Each round's results come back as the agent's structured return
- Serialize build phases (one build agent per project at a time) to avoid concurrent redo conflicts

## State File

State file (project-specific, not in skills repo):
```json
{
  "currentSkill": "component-dev",
  "round": 1,
  "phase": "stress-test",
  "results": {
    "component-dev": {
      "rounds": 5,
      "lastErrors": 0,
      "converged": true,
      "ancestors": ["R1-opus-2026-02-12", "R3-sonnet-2026-02-15", "R5-sonnet-2026-02-20"],
      "lastTested": "2026-02-20",
      "linesChangedSinceTest": 0
    },
    "testing": {
      "rounds": 3,
      "lastErrors": 0,
      "converged": true,
      "ancestors": ["R1-sonnet-2026-02-15", "R2-sonnet-2026-02-18"],
      "lastTested": "2026-02-18",
      "linesChangedSinceTest": 12
    }
  },
  "schedule": "every-30-min",
  "crossSkillErrors": "memory/skill-refinement/cross-skill-errors.md",
  "worstCaseFloor": 0
}
```
