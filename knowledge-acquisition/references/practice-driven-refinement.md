# Practice-Driven Skill Refinement

Pattern for improving skills by building real artifacts and capturing the gaps that compilation/testing reveals.

## When to Use

After initial skill creation (via knowledge-acquisition), shift to this pattern when:
- Skills cover the major concepts but lack precise API details
- You need to verify correctness against real toolchains
- Diminishing returns from reading more source code
- Want to discover unknown unknowns (things you didn't know to look for)

## Process

### 1. Pick a Build Target

Choose something that exercises the skill gaps you want to test:
- **Simple component**: connectors, commands, events, data products (validates core patterns)
- **Component with faults**: fault connector, fault handler generation
- **Component with data deps**: request connector, Get_{Name} pattern, staleness checking
- **Component with enums**: standalone enums.yaml vs preamble enums (different Ada patterns)
- **Component with parameters**: runtime-updateable configuration
- **Assembly**: wiring, scheduling, ID assignment, view filters

### 2. Build Using Only Skills

Write all YAML and Ada files referencing only the skill documentation. Do NOT look at existing framework code unless you hit a compiler error. This is the test.

### 3. Iterate on Compiler Errors

Each error reveals a gap:
```
Error: "Thermal_Controller_Enums" not found
  -> Lesson: preamble enums live in the packed type package, not a separate _Enums package

Error: no selector "Data_Product_Fetch_T_Request"
  -> Lesson: data deps need request connector (not get), and the connector name
     depends on the type name in the YAML

Error: data product name collision with type name
  -> Lesson: data product functions are in scope alongside types; avoid name overlap

Warning: use clause has no effect
  -> Lesson: base class already `with`s certain packages; redundant `use` is harmless
```

### 4. Update Skills Immediately

After each fix, update the relevant skill with the correct pattern. Do NOT batch -- update as you go so the lesson is precise and fresh.

### 5. Save Lessons After Each Component

Update the relevant skill files with any new patterns or corrections discovered during this build.

### 6. Escalate Complexity

Progress through increasingly complex builds:
1. Passive component, no deps, no faults (baseline)
2. Passive with faults and custom packed types
3. Passive with data dependencies and enums
4. Active component with async connectors
5. Assembly wiring multiple components
6. Tests for a custom component

Each level exposes new API patterns the skills need to cover.

## What to Capture

For each compilation error or unexpected behavior:
- **What you expected** (what the skill said or implied)
- **What actually happened** (the compiler error or runtime behavior)
- **The correct pattern** (what the generated code actually does)
- **Which skill to update** (type-system, component-dev, assembly-dev, build-system)

## Diversity-to-Progress Conversion

Multiple validation rounds produce diverse error discoveries. The key insight (from
group-evolution research) is that diversity alone is insufficient -- it must be
*consolidated* into the shared artifact (the skill) to produce cumulative progress.

**Transient diversity** (wasted): Sub-agent discovers a pattern, reports it, but the
lesson stays in the session transcript. Next sub-agent rediscovers it independently.

**Consolidated diversity** (progress): Each discovery is immediately written into the
skill. Every subsequent agent benefits from all prior agents' discoveries. The skill
becomes the shared experience pool.

Metrics to watch:
- **Ancestor count**: How many independent sessions contributed to this skill?
  Higher = more robust. Skills with only 1 ancestor are fragile.
- **Cross-skill propagation rate**: What fraction of errors affected multiple skills?
  Track this to ensure lessons don't stay isolated in one skill.
- **Rediscovery rate**: How often do new sub-agents hit errors that were already found
  and fixed in other skills? Non-zero means propagation is incomplete.

## Automated Refinement Campaigns

For systematic skill validation at scale, run automated multi-tier campaigns with
escalating complexity. This extends the manual practice-driven loop into a
self-driving refinement engine.

### Campaign Structure

Organize scenarios into tiers of increasing difficulty:

| Tier | Focus | Example |
|------|-------|---------|
| T1-T8 | Single concern (types, serialization) | Packed record round-trip |
| T9 | Algorithm wrapping (C -> Ada -> component) | CRC-16 calculator + SPARK |
| T10 | Multi-component interaction | 3-component command pipeline |
| T11 | Subassembly + SPARK + algorithm | GNC estimator subsystem |
| T12 | Adversarial (name collisions, edge cases) | Redundant sensor voter |

Each tier has multiple scenarios (2-3). Each scenario runs iterations until
convergence (N consecutive clean runs, typically 5).

### Phased Execution (Context Budget Management)

A full pipeline (types + C code + bindings + component + tests + assembly + SPARK)
can overflow a 200k context window in a single sub-agent session. Split into phases:

- **Phase A**: Types + C code + bindings + component + tests (build + test verification)
- **Phase B**: Assembly + SPARK proofs (integration verification)

Each phase is a separate sub-agent spawn. Phase B only runs if Phase A is clean.
This keeps each sub-agent well within context limits.

**Adapt granularity to model capability.** Sonnet (~200k context) can handle a single
component with tests in one phase, but struggles when that component has many features
(parameters + events + data products + faults) combined with type creation. When phases
fail repeatedly due to context exhaustion (not skill gaps), split further:

- **Coarse (Opus or simple components)**: Phase A (all components + tests) + Phase B (assembly)
- **Medium (Sonnet, multi-component)**: A1/A2/A3 (one component per phase) + B (assembly)
- **Fine (Sonnet, complex components)**: A0 (types only) + A1/A2/A3 (one component per phase) + B (assembly)

Signs you need finer splits:
- Sub-agent hits 200k tokens before completing tests
- Tests left incomplete or missing files (env.py, test.adb, tester files)
- Agent reports "environment issues" that are actually context exhaustion artifacts

Finer phases also improve post-run error attribution -- you know exactly which
component or type caused a failure without untangling multi-component output.

Match the split to model + complexity, and adjust dynamically when a granularity
level shows repeated context-limit failures.

### Convergence Criteria

- **Clean run**: both phases complete with 0 errors (build, style, test, prove all pass)
- **Convergence**: N consecutive clean runs (default 5) for a given scenario
- **Skill fix**: if an error reveals a skill gap, fix the skill AND reset the
  consecutive clean counter to 0
- **Tier completion**: all scenarios in the tier converged

### Campaign State Tracking

Maintain a state file (JSON) tracking:
```json
{
  "currentTier": 10,
  "currentScenario": 1,
  "currentIteration": 3,
  "consecutiveClean": 2,
  "totalIterations": 25,
  "tierHistory": {
    "T9-S1": {"attempts": 8, "consecutiveClean": 5, "completed": true, "skillFixes": 1}
  },
  "skillFixes": ["algorithm-wrapping: _h.ads naming convention"]
}
```

Use a cron job (every 5 min) as a campaign driver to check state, process results,
and spawn the next phase. The driver must check for running sub-agents before
spawning to avoid concurrent redo conflicts.

### Cleanup Between Iterations

During convergence testing, `git rm` all exercise files between iterations and commit.
This ensures each iteration starts from a clean slate -- the sub-agent must
recreate everything from skills alone, not from leftover files.

**After convergence**: keep the final clean iteration's output. Do NOT delete
converged scenario code -- it represents validated, tested artifacts built
entirely from skills. Commit and retain in the project.

**Restoring across scenarios**: each scenario produces unique components (different
names, different types). Converged scenarios can coexist in the same project
without conflicts. Accumulate validated components as the campaign progresses.

### Rate Limit Resilience

Sub-agents that hit API rate limits (429) die mid-run, leaving partial files.
Before re-spawning:
1. Check for partial files (`git status`)
2. Clean up (`git rm` partial files, or `git checkout -- .` + `git clean -fd`)
3. Re-spawn the failed phase

Rate-limited runs do NOT count as failures -- don't reset the consecutive clean counter.

### Model Tiering as Quality Signal

Running campaigns on different models tests skill robustness:
- **Opus**: stronger reasoning, can compensate for vague skills
- **Sonnet**: follows instructions more literally, exposes skill gaps Opus masks

If a campaign converges on Opus but fails on Sonnet, the skills are relying on
model capability rather than explicit documentation. Fix the skills until Sonnet
converges too. This is a stronger quality bar.

Consider re-running earlier tiers on Sonnet after initial Opus convergence to
validate skill quality at the weaker model level.

### Escalation Rules

- If a tier converges with 0 skill fixes across all scenarios, consider designing
  harder variant scenarios -- the tier may not be testing skill boundaries
- If a scenario consistently fails on the same error pattern, that's a skill gap --
  fix immediately rather than burning iterations
- Track total skill fixes per tier to measure skill maturity

## Anti-Patterns

- **Don't look at framework source first**: the whole point is to test the skills
- **Don't skip the skill update**: lessons must be captured immediately
- **Don't build trivial components**: each build should exercise something new
- **Don't ignore warnings**: they often reveal incorrect assumptions about Ada visibility
- **Don't batch lessons**: update skills immediately while context is fresh
- **Don't let discoveries die in transcripts**: every lesson goes into a skill file, not just the session log
