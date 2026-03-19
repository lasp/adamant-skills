# Framework-Verified Skill Correction

Pattern for fixing skills by studying the framework source code, forming testable hypotheses, building minimal artifacts to verify them, and then campaign-testing the corrected skills with cold-start agents.

## When to Use

- A skill pattern is suspected to be wrong but nobody is sure
- Cold-start agents keep failing in ways that suggest the skill is misleading
- A skill was written from documentation/examples but never verified against the framework source
- Subassembly/assembly/type mechanics need clarification that only the model code can provide

## The Loop

```
Study -> Hypothesize -> Build/Verify -> Fix Skill -> Campaign-Test -> Escalate
  ^                                                                      |
  +----------------------------------------------------------------------+
```

Each step has a specific deliverable. Skipping steps produces skills that look correct but aren't verified.

### 1. Study

Read the framework source code for the mechanism in question. Not documentation -- actual Python models, generators, schemas, and redo infrastructure.

**Priority reading order:**
1. Schema YAML (`gen/schemas/`) -- what fields exist, what's required
2. Model Python (`gen/models/`) -- how YAML is loaded, validated, and merged
3. Generator Python (`gen/generators/`) -- what code is produced
4. Build infrastructure (`redo/`) -- how files are discovered and indexed
5. Existing project usage -- how real assemblies use the mechanism

**Write notes as you go.** Create `memory/advanced-campaign/<campaign>/hypotheses.md` with raw observations before forming hypotheses.

### 2. Hypothesize

Form testable claims. Each hypothesis must be:
- **Specific**: "A subassembly YAML in a directory without `.all_path` will not be found by the model database" (not "subassemblies need to be in the right place")
- **Falsifiable**: There must be a build test that proves it true or false
- **Documented**: Write it down BEFORE testing

**Format:**
```
H<N>: <claim>
Source: <file:line where you found evidence>
Test: <what to build to verify>
Status: UNTESTED | CONFIRMED | REFUTED | MODIFIED
```

### 3. Build/Verify

Create minimal build tests inside the Docker container. Each test exercises one hypothesis.

**Rules:**
- One hypothesis per test (isolation)
- Minimal components (2-3 max, just enough to exercise the mechanism)
- Build from scratch -- don't reuse existing assemblies
- Record exact commands run and exact output
- A hypothesis is CONFIRMED only when the build succeeds/fails as predicted
- A REFUTED hypothesis is MORE valuable than a confirmed one -- it means the skill was wrong

**Test structure:**
```
src/test_hypotheses/
  h1_subasm_no_allpath/     # expect: build failure (can't find subassembly)
  h2_subasm_separate_dir/   # expect: build success (with .all_path)
  h3_nested_subasm/         # expect: build success (sub-sub)
```

Clean up after verification -- these are throwaway tests, not permanent fixtures.

### 4. Fix Skill

Update the skill with VERIFIED patterns only. Every claim in the skill must trace to a confirmed hypothesis or a working build artifact.

**Fix rules:**
- Remove patterns that were refuted by build tests
- Add patterns that were confirmed by build tests
- Mark uncertain areas explicitly ("Untested: nested subassemblies beyond 2 levels")
- Include the verification source ("Verified: `.all_path` required per `redo/database/_setup.py:105`")
- Commit skill fixes immediately -- don't batch

### 5. Campaign-Test

Spawn cold-start sub-agents with LOOSE prompts to test the corrected skill.

**Campaign rules (mandatory):**
- Define decision points BEFORE the first iteration
- DP audit on EVERY iteration (full session history, table format)
- Failures are the product -- MISS results show where skills need more work
- 3+ agents miss the same point = skill gap, fix immediately between iterations
- Apply fixes between iterations so subsequent agents benefit
- 5 consecutive clean iterations to converge

**Prompt rules:**
- Loose only -- no skill names, no YAML field lists, no build commands
- The agent must derive everything from skills
- Example: "Design and build a thermal subsystem with 3 subassemblies organized by function. Build in Docker."

### 6. Escalate

After convergence, INCREASE DIFFICULTY. Do not declare victory.

**Escalation patterns:**
- More components (5 -> 10 -> 20)
- More subassemblies (2 -> 3 -> nested)
- Cross-cutting concerns (shared types, request/provide across boundaries)
- Combine with other skills (subassemblies + COSMOS, subassemblies + SPARK)
- Refactor existing flat assembly into subassemblies (harder than greenfield)

**Escalation triggers:**
- 5 consecutive clean at current difficulty -> escalate
- Hit rate plateaus at 100% -> the task is too easy, escalate
- All agents make the same design choices -> add constraints to force different paths

**Never say "production ready."** Say "no gaps found at this complexity level."

## Tracking

### Hypothesis Ledger

```markdown
# Hypotheses: <scenario>

| ID | Claim | Source | Test | Status | Skill Impact |
|----|-------|--------|------|--------|-------------|
| H1 | `.all_path` required for discovery | _setup.py:105 | h1_no_allpath/ | CONFIRMED | subassemblies: added requirement |
| H2 | Separate dir works with `.all_path` | model_loader.py:114 | h2_separate/ | CONFIRMED | subassemblies: added pattern |
| H3 | Nesting supported | assembly.py:686 | h3_nested/ | UNTESTED | -- |
```

### Campaign State

```json
{
  "campaign": "T4",
  "current_scenario": "S1",
  "current_phase": "build-verify",
  "hypotheses": { "confirmed": 3, "refuted": 1, "untested": 5 },
  "skill_fixes": 2,
  "campaign_iterations": 0,
  "consecutive_clean": 0,
  "difficulty_level": 1,
  "escalations": 0
}
```

## Integration with Existing Methodology

This pattern composes with:
- **Decision point methodology** (references/decision-point-methodology.md): DPs defined from verified hypotheses, not guesses
- **Knowledge acquisition** (knowledge-acquisition skill): Study phase uses same systematic reading pattern
- **Practice-driven refinement** (references/practice-driven-refinement.md): Build/verify is the hypothesis-testing version of "build and see what breaks"
- **Campaign progression ladder**: Study/verify feeds the "Escalate" step with harder tasks grounded in known framework behavior

## Anti-Patterns

- **Skipping the build step**: Reading source code and "knowing" the answer without building is how wrong skills get written in the first place
- **Testing too many things at once**: Compound build tests that exercise 5 hypotheses give ambiguous results
- **Fixing skills from summaries, not session history**: Always fetch full session history for DP audit. Summaries hide self-corrections
- **Stopping at convergence**: 5 clean iterations means the CURRENT difficulty is solved. Escalate.
- **Attributing failures to agents**: If 3+ cold-start agents fail the same DP, the skill is wrong. Period.
