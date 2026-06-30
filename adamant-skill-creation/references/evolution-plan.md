# Skill Evolution Plan
<!-- Based on GEA (arxiv 2602.04837) group-evolution concepts -->

## Current State

Skills converged to 0 cold-start errors via iterative stress testing (19+ rounds).
But convergence was measured per-skill in isolation. The next frontier is
*cross-skill* and *multi-model* robustness.

## Phase 1: Baseline Measurement (next)

Establish the population-wide quality floor:

1. Run cold-start validation on ALL 10 generative skills (not just one at a time)
2. Use a DIFFERENT model than previous testing (e.g., Haiku instead of Sonnet)
3. Record per-skill error counts and create the state file with ancestor tracking
4. Identify the floor (worst skill) and ceiling (best skill)

Deliverable: `memory/skill-refinement/skill-refinement-state.json` with full
ancestor and error data for all skills.

## Phase 2: Cross-Skill Propagation Audit

Systematic check for "branch isolation" in existing skills:

1. Extract all Common Errors sections from every skill
2. For each error, check: does it also apply to other skills?
3. Flag unpropagated errors (found in one skill, relevant to others)
4. Propagate and commit

Expected yield: 5-15 cross-skill fixes based on historical error patterns.

## Phase 3: Multi-Model Validation

GEA showed improvements transfer across GPT and Claude families because they
target workflow/tools, not model-specific prompting. Test the same for skills:

1. Validate with Sonnet (current baseline)
2. Validate with Haiku (cheaper, less capable -- exposes fragile patterns)
3. Validate with Opus (more capable -- may reveal over-specification)

Skills that work across all three are truly robust. Skills that only work with
Sonnet may be implicitly relying on Sonnet-specific capabilities.

## Phase 4: Combined-Task Stress Tests

Individual skill convergence != combined convergence. GEA's key insight is that
group-level evolution (multiple skills simultaneously) reveals integration failures.

Exercises:
1. **Full pipeline**: types + component + tests + assembly (4 skills)
2. **Algorithm integration**: wrap + types + component + tests + assembly (5 skills)
3. **Subassembly decomposition**: assembly + subassemblies + components (3 skills)
4. **Ground integration**: assembly + COSMOS + project-setup (3 skills)

Each exercise uses a fresh sub-agent with ALL relevant skills loaded.
Errors go into cross-skill-errors.md with propagation to all affected skills.

## Phase 5: Novelty-Driven Exploration

Once the floor is at 0 across all skills and model variants, shift to
novelty-driven exploration:

1. Identify framework features NOT covered by any skill
2. Prioritize by: (a) how often users might need them, (b) how likely
   an agent is to get them wrong without a skill
3. Create targeted exercises that push beyond current skill boundaries
4. New patterns discovered become skill extensions

Candidates from framework audit:
- SPARK prove workflow (partially covered in build-system, no dedicated exercises)
- Register map components (specialized, low-usage but complex)
- LASEL command sequences (documented but never stress-tested end-to-end)
- Multi-target builds (Linux + Pico + ARM in same project)
- Custom code generation (extending generators with project-specific templates)

## Phase 6: Automated Refinement Loop

Goal: continuous automated validation -- run in-session with the Workflow tool (see [adamant-skill-campaign](../../adamant-skill-campaign/SKILL.md)), not an external scheduler.

```
Schedule: Every 6 hours during active development periods
1. Select skill by performance-novelty priority
2. Spawn Sonnet sub-agent with cold-start exercise
3. Collect errors, propagate cross-skill fixes
4. Update state file with ancestor tracking
5. If floor > 0, notify main session
6. If floor == 0 for 1 week, switch to novelty exploration (Phase 5)
```

This is the open-ended loop. Unlike GEA's 30-iteration fixed budget, this runs
indefinitely with diminishing cost (fewer errors = faster rounds = less spend).

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Per-skill cold-start errors | 0 (Sonnet) | 0 (Sonnet + Haiku + Opus) |
| Cross-skill propagation rate | unmeasured | >90% |
| Rediscovery rate | unmeasured | <5% |
| Combined-task errors | 0 (3-skill) | 0 (5-skill) |
| Ancestor count per skill | 1-5 | 3+ for all generative skills |
| Quality floor | 0 (per-skill) | 0 (population-wide, multi-model) |
