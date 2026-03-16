# Decision Point Methodology

Outcome-aligned measurement for skill effectiveness. Measures whether agent OUTPUT matches skill prescriptions, regardless of whether the skill was explicitly read.

## Defining Decision Points

For any repeatable task (component creation, assembly wiring, test writing):

1. **Enumerate** every moment where a skill prescribes a specific action
2. **Document** each with:
   - **ID**: Short identifier (D1, D2, ...)
   - **Description**: What the agent must decide
   - **Skill source**: Which SKILL.md section prescribes the correct action
   - **Correct action**: What the skill says to do
   - **Failure mode**: What agents do wrong when they miss this point

3. **Score** each agent iteration by examining output artifacts and session history (via `sessions_history`)

## Tracking Template

```markdown
| DP | Description | Skill | i1 | i2 | i3 | Classification |
|----|-------------|-------|----|----|----|----------------|
| D1 | Build method | build-system | HIT | HIT | HIT | STABLE HIT |
| D2 | Target discovery | selector | MISS | MISS | MISS | SKILL GAP |
| D3 | YAML correctness | component-dev | HIT | HIT | HIT | STABLE HIT |
```

## Classification Rules

| Pattern | Classification | Action |
|---------|---------------|--------|
| All agents HIT | STABLE HIT | None needed |
| 3+ agents MISS on same point | SKILL GAP | Fix the skill immediately |
| Mixed HIT/MISS | UNSTABLE | Skill exists but unclear; restructure |
| Agent MISS then self-corrects | MISS->FIX | Still a gap; prevention > recovery |
| No skill covers correct pattern | GAP | Create new skill content |

## Interpreting Hit Ratios

- **Hit ratio = HITs / total decision points per iteration**
- MISS->FIX counts as MISS for ratio purposes
- N/A (decision point not exercised) excluded from ratio

Track over iterations:
- **Rising ratio**: Skills are improving
- **Flat ratio**: Skills are plateau'd -- need structural change, not incremental fix
- **Falling ratio**: Regression -- new changes broke working patterns

## Prioritizing Skill Fixes

Rank by **miss frequency across independent agents**:

1. 100% miss rate (all agents miss) = highest priority, definite skill gap
2. 50-99% miss rate = high priority, unclear or buried guidance
3. <50% miss rate = medium priority, edge case or ambiguous

**Never attribute stable misses to agent quality.** If 3+ independent cold-start agents make the same mistake, the skill is wrong. This is the fundamental rule.

## Integration with Campaign Tiers

During campaign validation (T-series):
1. Define decision points BEFORE running iterations
2. Score each iteration against the decision points post-hoc
3. Apply skill fixes between iterations (not at the end)
4. Re-score subsequent iterations to confirm fixes are effective
5. Track the decision-point matrix alongside the standard iteration scratchpad

## Example: Component Creation Task

Decision points for "create a passive component with parameters, faults, events, DPs, commands, and tests":

| DP | Description | Skill Source |
|----|-------------|-------------|
| D1 | Build execution method (adamant_env.sh exec) | build-system |
| D2 | Target discovery (redo what) | skill-selector |
| D3 | Component YAML structural correctness | component-dev |
| D4 | Test file creation (template copy vs scratch) | testing |
| D5 | Update_Parameters ordering (before param reads) | component-dev |
| D6 | Style-clean Ada on first write | style |
| D7 | Send_Dropped history expectations | testing |
| D8 | Parameter 3-step test flow | testing |
| D9 | No prohibited actions (git, scope) | AGENTS.md |
| D10 | Unused with clauses (aggregate resolution) | component-dev |

This taxonomy was developed empirically from T-REDO S1 (5 iterations, Sonnet cold-start agents creating pressure_regulator component). Decision points D5 and D7 were identified as skill gaps and fixed; D2 was identified as potentially misguided guidance requiring further analysis.
