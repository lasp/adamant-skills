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
  AND post-phase test audit passes (see below)
- **Convergence**: N consecutive clean runs (default 5) for a given scenario
- **Skill fix**: if an error reveals a skill gap, fix the skill AND reset the
  consecutive clean counter to 0
- **Tier completion**: all scenarios in the tier converged

### Post-Phase Test Audit

After each component phase (A1/A2/A3), the campaign driver should read the test
`.adb` file and verify test quality before advancing. A phase is not "clean" if
tests are shallow. Check for:

1. **Value assertions**: tests must assert specific output values, not just that
   calls didn't crash. Every output connector should have its history checked
   with concrete expected values.
2. **Spec coverage**: every behavior listed in the task spec must have a
   corresponding assertion. If the spec says "verify Mode_Changed event with
   Science param", the test must assert the event history contains Science.
3. **Edge case coverage**: where the spec lists edge cases (idempotent behavior,
   boundary values, mode transitions), tests must exercise them with assertions.

If tests are shallow (e.g., only checking history counts without value assertions,
or missing spec-required behaviors), treat the phase as failed. Record "shallow
tests" as the error and reset the iteration. This prevents false convergence on
components that compile and "pass" but aren't actually validated.

This audit is lightweight -- read one file, check assertion density. Adds ~30s
per component phase. The cost of NOT doing it is false convergence: 5 "clean"
iterations that never actually tested the component logic.

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

### Commit Strategy: Atomic Iterations

Sub-agents must NOT commit or push. They only build, test, and report results.

The campaign driver owns all git operations:

1. **During phases**: sub-agents create/modify files but do not `git add` or
   `git commit`. Phase task prompts must NOT include commit instructions.
2. **After all phases complete clean** (including post-phase test audit):
   the campaign driver creates a single atomic commit covering the entire
   iteration's output (types + components + tests + assembly).
   Commit message: `T10-S3-i5: mode_telemetry (mode_controller + telemetry_selector + packet_builder + assembly)`
3. **Push only on clean iterations**: `git push` after the atomic commit.
4. **Failed iterations**: `git checkout -- . && git clean -fd` to reset the
   working tree. No junk commits from partial work.

This ensures every commit in the repo represents a complete, validated build.
Per-phase commits are meaningless if a later phase fails -- they create orphaned
partial state in the history.

### Cleanup Between Iterations

Before each iteration, delete all exercise directories (`rm -rf`) and let the
sub-agent rebuild from scratch. This tests cold-start skill quality. The A0
phase task prompt should include the deletion step.

**After convergence**: keep the final clean iteration's output (it's already
committed via the atomic commit strategy above).

**Restoring across scenarios**: each scenario produces unique components (different
names, different types). Converged scenarios can coexist in the same project
without conflicts. Accumulate validated components as the campaign progresses.

### Rate Limit Resilience

Sub-agents that hit API rate limits (429) die mid-run, leaving partial files.
Before re-spawning:
1. Check for partial files (`git status`)
2. Clean up (`git checkout -- . && git clean -fd`)
3. Re-spawn the failed phase

Since sub-agents don't commit, cleanup is just resetting the working tree.

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

## Token-Efficiency Optimization

Skills affect not just correctness but *efficiency* -- how many tokens a sub-agent
consumes to complete a known-solvable task. Token count is a measurable, objective
metric for skill quality: better skills guide agents to solutions faster with less
exploration, backtracking, and re-reading.

### Methodology

1. **Baseline**: run a known task (one that converges cleanly) and record token usage
   per phase. This is the baseline cost.
2. **Hypothesize**: identify skill sections that are verbose, redundant, or poorly
   organized. Predict which changes will reduce token consumption.
3. **Refine**: make a targeted skill edit (consolidate examples, reorder sections,
   add decision trees, remove duplication, front-load critical patterns).
4. **Measure**: re-run the same task and compare token usage. Record delta.
5. **Validate**: run the modified skill on *different* task types to confirm no
   regressions. A skill that's efficient on one task but breaks others is worse,
   not better.
6. **Iterate**: repeat until diminishing returns.

### What to Measure

- **Tokens per phase**: prompt/cache + output tokens for each sub-agent run
- **Total tokens per iteration**: sum across all phases
- **Token trend across iterations**: should decrease as skills improve
- **Error rate**: must remain 0 -- efficiency gains that increase errors are invalid

### Optimization Levers

- **Front-load critical patterns**: put the most common error-causing patterns
  (parameter testing, test template workflow, env.py) at the top of relevant sections
- **Decision trees over prose**: "if passive, do X; if active, do Y" is faster to
  parse than a paragraph explaining both
- **Reduce redundancy across skills**: if component-dev and testing both explain
  parameter staging, consolidate into one authoritative location
- **Concrete examples over abstract rules**: agents spend fewer tokens when they can
  pattern-match against examples
- **Remove stale content**: outdated patterns that no longer apply cause confusion
  and wasted exploration

### Validation Protocol

After any efficiency-motivated skill edit:
1. Re-run the optimized task -- must still converge with 0 errors
2. Run at least 2 *different* task types that exercise the modified skill section
3. Compare token usage: optimized task should decrease, others should not increase
   significantly (< 10% regression tolerance)
4. If regressions detected, revert and try a different optimization approach

### Empirical Results (2026-02-27)

A controlled trial on the Adamant skills tested this methodology on a converged T10-S2
scenario (Sensor Fusion, 5-phase split). Changes: quick decision tree in component-dev,
"load only what you need" guidance on references, fast paths in the selector.

**Result: the optimized branch was worse.**

| Metric | Baseline (main) | Optimized | Delta |
|--------|-----------------|-----------|-------|
| Output tokens | 53.6k | 65.0k | +21% |
| Prompt/cache | 379.0k | 385.5k | +2% |
| Runtime | ~20m | ~26m | +30% |
| Errors | 0 | 0 | -- |

**Why it failed**: the additions (decision trees, load guidance) increased agent
verbosity without reducing reference loading. Agents read what they read regardless
of routing hints. Output variance between runs (~20%) dominates any signal from
small skill wording changes.

**Lesson**: token micro-optimization at the skill text level does not work. Real
efficiency gains would require structurally smaller skills or fewer references, which
risks correctness -- the thing convergence campaigns optimize for. Do not pursue
token optimization via skill wording changes. The methodology above is theoretically
sound but practically ineffective at the margin sizes achievable with text edits.

The correct priority order is: **correct > robust > efficient**. Efficiency is a
third-order concern that should not drive skill edits.

### Structural vs Wording Optimization

The 2026-02-27 trial showed that **wording-level** changes (decision trees, routing
hints, "load only what you need" guidance) don't reduce tokens -- agents read what
they read. But **structural** changes produce measurable, reproducible gains:

| Category | Example | Expected Impact |
|----------|---------|-----------------|
| **Phase consolidation** | Merge 3 simple phases into 1 agent | -40% spawns, -28% output, -37% prompt |
| **Deterministic read order** | Skill selector emits exact file list | Stable cache prefix across iterations |
| **Conditional reference loading** | Skip impl-patterns.md for passive components | -20-40k prompt for simple phases |
| **Connector discovery** | Assembly agents read YAML files directly | Shorter task prompts, less stale data |
| **Script-based extraction** | Executable script returns only needed API surface | Potential large prompt reduction (untested) |

**Rule: if a change is structural (fewer files loaded, fewer spawns, different
pipeline shape), measure it. If it's wording (reordering paragraphs, adding hints),
don't bother -- variance between runs dominates the signal.**

### Empirical Results (2026-03-01, Structural Optimization)

T12-S2 (Sensor Fusion Controller, maximum difficulty) with structural changes:
3-phase pipeline (was 5-phase), deterministic read order, conditional reference loading.

| Metric | S2 Baseline (5-phase) | S3 Optimized (3-phase) | Delta |
|--------|----------------------|----------------------|-------|
| Spawns | 5 | 3 | -40% |
| Total output tokens | ~121k avg | 87.2k | -28% |
| Total prompt/cache | ~421k avg | 266.8k | -37% |
| Total runtime | ~38m avg | 29m27s | -22% |
| Skill reads | 17 | 11 | -35% |
| Error rate | 0% | 0% | same |

Unlike wording changes, these are consistent and reproducible across iterations.
Prompt token variance < 3% when using deterministic read order.

### Integration with Campaigns

**Campaign progression follows a strict ladder:**

1. **Convergence**: fix skills until N consecutive clean cold-start runs (typically 5).
   This is the only phase that matters. Skills that don't converge are broken.

2. **Efficiency**: once converged, optimize token usage via structural changes.
   Re-run the SAME scenario to measure before/after. Only structural changes
   (phase consolidation, conditional loading, pipeline shape) are worth testing.
   Wording changes are not measurable.

3. **Difficulty escalation**: once converged AND efficient, increase task complexity.
   The goal is skills that enable correct results on harder tasks, not just cheaper
   results on easy ones. Design new tiers that exercise untested patterns.

**The decision at each tier:**
- Skills NOT converging? -> Fix skills (correctness gaps).
- Skills converging but expensive? -> Optimize structure (efficiency).
- Skills converging AND efficient? -> Relax prompts (autonomy).
- Skills converging with relaxed prompts? -> Increase difficulty (capability).

Never skip ahead. Efficiency without convergence is waste. Difficulty without
efficiency means you're burning tokens on solved problems while testing new ones.

### Prompt Relaxation

When skills converge with detailed prompts (field-by-field specs, exact connector
lists, numbered test cases), the next step is NOT increasing difficulty -- it's
reducing prompt detail. Detailed prompts test whether skills can guide *implementation*.
Relaxed prompts test whether skills can guide *design*.

**Progression:**
1. **Detailed prompts**: every field, connector, test case specified (implementation test)
2. **Relaxed prompts**: high-level description + constraints + quality requirements (design test)
3. **Minimal prompts**: one-sentence task description (full autonomy test)

**Relaxed prompt template:**
```
Build a [system description] using Adamant.

Requirements:
- [key constraints: SPARK, C FFI, subassemblies, active/passive]
- [quality: tests with N% coverage, admt style clean, admt test passing]

Use the Adamant skills. Make design decisions for types, connectors,
fault thresholds, test cases, and assembly topology.
```

The agent must:
- Choose appropriate packed record types and field sizes
- Design connector topology (which connectors, what types)
- Decide fault detection thresholds and latching behavior
- Write meaningful test cases (not just the ones listed in a prompt)
- Wire the assembly with correct infrastructure

**Why this matters**: a user should be able to describe what they want at a
requirements level and get a correct, well-designed Adamant system. If skills
only work with field-by-field prompts, they're implementation checklists, not
engineering knowledge.

**Measuring prompt relaxation**: compare prompt token counts (should drop 50-80%),
output quality (must remain correct), and error rate (may initially increase --
that's expected and reveals design-level skill gaps).

**Tracking**: maintain a CSV with per-phase metrics (runtime, prompt tokens, output
tokens, result, notes) across all iterations and optimization variants. This is the
ground truth for all decisions. Without data, you're guessing.

## Anti-Patterns

- **Don't look at framework source first**: the whole point is to test the skills
- **Don't skip the skill update**: lessons must be captured immediately
- **Don't build trivial components**: each build should exercise something new
- **Don't ignore warnings**: they often reveal incorrect assumptions about Ada visibility
- **Don't batch lessons**: update skills immediately while context is fresh
- **Don't let discoveries die in transcripts**: every lesson goes into a skill file, not just the session log
