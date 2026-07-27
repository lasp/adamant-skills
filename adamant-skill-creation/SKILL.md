---
name: adamant-skill-creation
description: Create, validate, and refactor Adamant framework skills. Use when building new skills for Adamant development, refactoring existing skills, separating project-specific from generic content, or validating skill accuracy via cold-start sub-agent exercises.
---

# Adamant Skill Creation

Guide for creating and maintaining Adamant framework skills that enable cold-start agents to build components, assemblies, tests, and types in any Adamant project.

## Skill Architecture

### Three-Tier Loading
1. **Skill selector** (~160 lines, always loaded first): Routes tasks to 1-2 skills
2. **SKILL.md** (~300 lines each): Core procedures, checklists, rules
3. **references/** (unlimited): Detailed examples, corpus, audit data

An agent loads selector -> reads 1-2 SKILL.md files -> reads references only when needed. Context is precious -- every line must justify its token cost.

### Current Skill Inventory (16 skills)

| Skill | Purpose | SKILL.md | References |
|-------|---------|----------|------------|
| adamant-skill-selector | Task routing | ~160 | -- |
| adamant-component-dev | Component YAML + Ada | ~320 | ~1100 |
| adamant-testing | Test patterns + assertions | ~350 | ~1500 |
| adamant-assembly-dev | Assembly wiring + scheduling | ~365 | ~700 |
| adamant-type-system | Packed types, enums, arrays | ~355 | ~300 |
| adamant-build-system | Redo, code gen, prove | ~310 | ~900 |
| adamant-framework-components | 58 built-in components catalog | ~295 | -- |
| adamant-cosmos-integration | Ground system (OpenC3) | ~325 | ~400 |
| adamant-algorithm-wrapping | C++ -> C shim -> Ada -> Adamant | ~325 | ~110 |
| adamant-project-setup | New project bootstrap | ~365 | -- |
| adamant-style | Ada/YAML/Python style rules | ~340 | ~660 |
| high-assurance-design | Design-by-invariant methodology | ~205 | -- |
| knowledge-acquisition | Study repos, create skills | ~210 | -- |
| adamant-subassemblies | Subassembly patterns + nesting | ~450 | -- |
| adamant-skill-creation | This skill | ~300 | ~200 |

Total: ~5600 SKILL.md + ~8500 references = ~14000 lines

## Creating a New Adamant Skill

### When to Create vs Extend
- **New skill**: Distinct domain that an agent would need independently (e.g., COSMOS is separate from assembly-dev)
- **Extend existing**: Additional patterns within an existing domain (e.g., new test pattern -> testing skill)
- **New reference file**: Detailed examples/corpus that supports an existing skill

### Skill Structure

```
adamant-<name>/
  SKILL.md          # 250-350 lines. Procedures, checklists, rules
  references/       # Detailed examples, corpus, patterns
    <topic>.md      # Named by what it contains
```

### SKILL.md Template

```markdown
---
name: adamant-<name>
description: <What it does>. <When to use it -- specific triggers>.
---

# <Title>

<1-2 sentence overview>

## Quick Start
<Minimal steps to accomplish the most common task>

## <Domain Section 1>
### <Subsection>
<Rules, patterns, YAML/Ada examples>

## <Domain Section N>

## Checklist
<Numbered steps an agent follows to complete the task>

## Common Errors
<Errors that cold-start agents hit repeatedly, with fixes>

## References
- `references/<file>.md` -- <when to read it>
```ada

### Writing Rules

1. **Imperative voice**: "Create the file" not "You should create the file"
2. **Code over prose**: Show the YAML/Ada, don't describe it
3. **No project-specific content**: Use `<project_dir>`, `<component_name>`, `<assembly_name>` placeholders
4. **Checklist-driven**: Agents follow numbered steps. Every step must be actionable
5. **Error-first**: Common errors section is mandatory. Source from validation exercises
6. **No commits/push instructions**: Skills teach Adamant patterns, not git workflow
7. **Cross-reference sparingly**: Each skill should be mostly self-contained. Mention other skills only when genuinely needed
8. **Target 300 lines**: Upper cap ~350. Move detail to references/
9. **Challenge each addition for token cost -- and pair imperatives with their reason**.
   Context window is shared across system prompt, all loaded skills, and conversation.
   Before adding a paragraph, ask:
   - Does the agent already know this from training?
   - Does this teach Adamant-specific behavior, or generic programming knowledge?
   - Would removing this paragraph harm a cold-start agent's first-attempt success?

   Only add content that survives all three. When the answer is "keep it", pair the rule
   with a brief reason. Bare imperatives ("Do X") are easier for agents to skim or hand-wave
   past than imperatives with motivation ("Do X because Y"). A single clause is usually
   enough -- the goal is enough context for the agent to apply judgment in edge cases, not
   a lecture. Reasons let the agent reapply the rule in situations the skill didn't anticipate.
10. **Classify every directive -- invariant, convention, or judgment call -- and write it
    to match.** *Invariants* are facts of the domain (build-state corruption, generated-code
    contracts, buffer/ABI limits, CI gates): state them absolutely, with the consequence
    ("NEVER X -- corrupts Y"). *Conventions* are choices this ecosystem standardized
    (naming, layout, assertion style): state them with their rationale so agents can apply
    them to cases the skill didn't anticipate. *Judgment calls* (how much to explore, what
    to verify, response shape): state the goal and the constraint, not a step sequence --
    highly capable models produce worse output when choreography replaces goals, while
    less capable models still get their guardrail from the stated constraint. A directive
    that exists only because some model once got it wrong -- not because the domain demands
    it -- is generation-scoped: flag it for removal when validation moves to a newer model
    generation (see `adamant-skill-campaign` -- validation results are generation-scoped).

### Description Field (Critical for Triggering)

The `description` in YAML frontmatter is how the skill-selector and agents decide when to load the skill. Include:
- What the skill does (first clause)
- Specific trigger phrases/scenarios (second clause)
- Example: "Patterns and workflows for developing components in the Adamant embedded software framework. Use when creating component YAML models, writing implementation specs/bodies, defining connectors, commands, events, data products, parameters, or faults."

## Validating Skills

### Cold-Start Validation (Gold Standard)

The most reliable way to test a skill is having a fresh agent use it from scratch.

1. **Spawn isolated sub-agent** with only the skill(s) being tested
2. **Task**: Build a specific component/assembly/type from scratch using only the skills
3. **Measure**: Count compile errors, test failures, style violations
4. **Feed back**: Every error becomes a skill fix

```
Task template:
"You are working in an Adamant project at <path>. Using ONLY the skills
provided, create a <passive/active> component named <name> that <spec>.
Include tests. Build with: docker exec <container> bash -c '...'
Do NOT use prior Adamant knowledge -- follow the skills exactly."
```ada

### Validation Metrics

| Metric | Target | Action if missed |
|--------|--------|------------------|
| Compile errors | 0 | Fix checklist/examples in skill |
| Test failures (logic) | 0 | Fix test pattern examples |
| Style violations | 0 | Fix style skill or align code-producing skills |
| Missing files | 0 | Fix checklist (e.g., missing .all_path, env.py) |

### Decision Point Analysis

Error counts alone don't reveal WHY agents fail. **Decision points** are moments where a skill prescribes a specific action. Track whether the agent's OUTPUT matches the prescription, regardless of whether the skill was explicitly read.

**Classifications:**
- **HIT**: Agent output matches skill prescription
- **MISS**: Agent improvised or got it wrong where a skill had the answer
- **MISS->FIX**: Agent got it wrong, then self-corrected within the same session
- **GAP**: No skill covers the correct pattern (skill deficiency, not agent deficiency)

**Defining decision points for a task (MUST be done BEFORE first iteration):**
1. List every moment where the skill prescribes a specific action (build method, file creation order, API usage pattern, naming convention)
2. Each decision point has: description, skill source, correct action, failure mode
3. Score each agent iteration against the decision points by examining output artifacts and session history

**Why before, not after:** Retroactive scoring from summaries can't distinguish clean first attempts from unreported self-corrections. Formal upfront decision points produce actionable skill fixes; pass/fail scoring produces nothing. T-REDO S1 (with decision points) found 2 skill gaps; S2-S5 (without) found 0 despite having unstable patterns.

**Interpreting results:**
- **Stable HIT** (all agents get it right): Skill is effective here. No action needed.
- **Stable MISS** (3+ agents get it wrong): This is a SKILL GAP, not agent failure. The skill is missing, unclear, or buried. Fix the skill.
- **Unstable** (some agents hit, some miss): Skill content exists but may be insufficiently prominent or ambiguous. Restructure for clarity.
- **MISS->FIX** (agent self-corrects): The skill didn't prevent the error but the agent recovered. Still counts as a skill gap -- prevention beats recovery.

**Critical rule:** Never attribute stable misses to agent quality. If 3+ independent cold-start agents make the same mistake, the skill is wrong. This prevents sycophantic measurement where you blame the agent instead of improving the skill.

### Convergence Tracking

Track validation rounds:
- **Round N**: X errors (list each)
- **Round N+1**: Y errors (should decrease)
- **Convergence**: 0 errors on cold start = skill is production-ready

Track decision point hit ratios per iteration. Plot the ratio over iterations to distinguish:
- Skills that converge (hit ratio increases as skills improve)
- Skills that plateau (hit ratio stays flat -- fundamentally unclear or wrong approach)
- Skills that regress (new changes break previously-working patterns)

Historical data: Skills went from ~20 errors/round to 0 errors over 19 rounds of iteration.

### Cross-Skill Experience Propagation

Errors found in one skill often reveal gaps in others. After each validation round:
1. Classify each error: does it affect only this skill, or also related skills?
2. Propagate fixes to all affected skills in the same commit
3. Log cross-skill errors in a shared error file (see `references/refinement-methodology.md`)

This prevents the "branch isolation" problem where a lesson learned during component-dev
testing never reaches the testing or assembly-dev skills.

### Population-Wide Quality Floor

Track not just best-case performance but worst-case across all skills. The reliability
of the skill set is bounded by its weakest member. Report the floor (worst cold-start
error count across all skills) and prioritize driving it to zero.

## Separating Project-Specific Content

### The Rule
Generic Adamant skills contain ZERO project-specific names, paths, or component references. Project-specific guidance lives in the project's own repo.

### What Is Project-Specific
- Component naming conventions (e.g., `station_` prefix)
- Assembly topology (which components wire to which)
- Custom type libraries unique to the project
- Docker container names and paths
- COSMOS plugin configuration for specific telemetry
- Coverage baselines and targets

### What Is Generic
- YAML schema fields and their meanings
- Ada implementation patterns (Set_Up, Execute, command handlers)
- Connector kinds and compatibility rules
- Build system commands and targets
- Test infrastructure patterns (tester, assertions, dispatch)
- Style rules

### Refactoring Process
1. `grep -rn "<project_name>\|<component_prefix>" --include="*.md"` across all skills
2. For each hit, decide: generic pattern with project example, or truly project-specific?
3. **Generic pattern**: Replace project names with `<placeholder>` names
4. **Project-specific**: Move to project repo's `docs/` or `skills/` directory
5. Verify clean: `grep` should return zero hits for project names
6. Commit with clear message explaining the separation

### Project-Specific Skill Location
```
<project_repo>/
  skills/           # or docs/agent-guide/
    project.md      # Project conventions, naming, topology
    coverage.md     # Coverage targets and baselines
```

Reference from the skill-selector:
> Generic Adamant skills provide the *how*. Project skills provide the *what* and *where*.

## Validation Loop

### Sub-Agent → Main Agent Workflow
The standard validation loop for skill changes (run it in-session with the Workflow tool -- see [adamant-skill-campaign](../adamant-skill-campaign/SKILL.md)):

1. **Sub-agent** creates or modifies skill files (SKILL.md, references/)
2. **Main agent** runs `admt style` to check style compliance
3. **Main agent** runs `admt test` to verify tests pass
4. **Main agent** runs `admt coverage` to check coverage targets

Sub-agents MUST NOT run redo commands directly. Only the main agent validates.

### Concurrent redo Is Unsafe
All redo operations must be serialized. Never run `admt style` and `admt test` in parallel -- redo uses shared build state and concurrent runs cause data corruption or spurious failures.

### Skill Selector Regeneration
After adding or modifying skills, regenerate the routing table:
```bash
bash scripts/generate_selector.sh /path/to/skills/
```ada
See [adamant-skill-selector/scripts/](../adamant-skill-selector/scripts/) for the generator script.

## Maintaining Skills

### Fix Isolation Rule
Apply ONE skill fix per convergence cycle. Run iterations until that specific fix is observed resolved across multiple consecutive clean runs before applying the next fix. This isolates each change and prevents interaction effects where one fix masks a regression from another. Many iterations per task is expected and necessary.

When multiple gaps are found in one iteration, prioritize the most impactful gap, fix it alone, verify convergence, then fix the next.

### When to Update
- After every cold-start validation that finds errors
- After discovering new framework behavior (e.g., generated code changes)
- After style rule changes
- When a sub-agent makes the same mistake 3+ times (pattern = skill gap)

### Update Process
1. Identify the gap (compile error, wrong pattern, missing step)
2. Find the responsible skill (use selector routing table)
3. Fix the SKILL.md or reference file
4. If the fix affects code examples in other skills, update those too (especially style alignment)
5. Run a cold-start validation to confirm the fix works

### Skill Health Indicators
- **Healthy**: Cold-start agents produce 0 compile errors
- **Degrading**: Same error appears in 2+ validation runs without being fixed
- **Stale**: Skill references framework behavior that has changed
- **Bloated**: SKILL.md exceeds 400 lines (split to references)

## Consistency Checks

Run these checks periodically across all skills:

### Structural
```bash
# Orphaned references (files not mentioned in SKILL.md)
for d in adamant-*/; do
  for ref in "$d/references/"*.md; do
    bn=$(basename "$ref")
    grep -q "$bn" "$d/SKILL.md" || echo "ORPHAN: $d$bn"
  done
done

# Missing cross-references
for d in adamant-*/; do
  grep -q '../adamant-' "$d/SKILL.md" || echo "NO CROSS-REFS: $d"
done

# Project-specific contamination
grep -rn '<project_name>\|<component_prefix>' --include="*.md" adamant-*/
```

### Content
- **Description fields**: All should have "Use when..." trigger phrases
- **Em dashes**: Use `--` not unicode em dashes
- **Error sections**: All code-producing skills need Common Errors
- **References sections**: All skills with references/ dir need a References section listing files
- **CLAUDE.md**: Update line counts and skill count after changes
- **Contradictions**: Cross-check rules stated in multiple skills (especially connector patterns, init sequences, style rules)

### Style Alignment
- Code examples in all skills must follow adamant-style rules
- Record aggregates use `()`, arrays use `[]`
- `and then` / `or else` (not `and` / `or`)
- No trailing whitespace
- YAML files start with `---`

## Adding to Skill Selector

After creating a new skill, add it to `adamant-skill-selector/SKILL.md`:

1. Add a routing entry in the Task Routing Table
2. Add to "Also load if needed" lists where appropriate
3. Update the skill count in the header

## Typical Development Workflow

Based on 14 skills developed over 20+ sessions:

### Phase 1: Knowledge Acquisition
1. Study the framework source (use `knowledge-acquisition` skill for systematic approach)
2. Build several components/assemblies by hand to understand patterns
3. Document what you learn in scratch notes

### Phase 2: Initial Skill Draft
1. Create SKILL.md with core procedures and checklists
2. Keep it under 200 lines initially -- add detail after validation
3. Include at least 2-3 code examples (YAML + Ada)
4. Write the Common Errors section from known pitfalls

### Phase 3: Cold-Start Validation
1. Spawn sub-agent with ONLY the new skill
2. Task: build a specific component from scratch
3. Count errors. Feed EVERY error back into the skill
4. Repeat until zero errors (typically 3-5 rounds for a new skill)

### Phase 4: Reference Expansion
1. After core SKILL.md is validated, extract detailed patterns to references/
2. Add real code examples from working components (anonymized -- no project names)
3. Target: SKILL.md ~300 lines, references as large as needed

### Phase 5: Cross-Skill Integration
1. Add cross-references to/from related skills
2. Update skill-selector routing table
3. Update CLAUDE.md with new skill entry
4. Check for contradictions with existing skills

### Phase 6: Ongoing Maintenance
1. Every cold-start exercise that finds errors triggers a skill update
2. Periodic consistency checks (see above)
3. Style alignment after style rule changes
4. Reference updates when framework behavior changes

## Common Skill Anti-Patterns

1. **Explaining what the model already knows**: Don't teach Ada syntax. Teach Adamant-specific patterns
2. **Walls of prose**: Use code blocks. An agent reads YAML/Ada faster than English
3. **Deeply nested references**: Keep all references one level deep from SKILL.md
4. **Missing error section**: If cold-start agents hit it, document it
5. **Stale examples**: Examples that don't compile are worse than no examples
6. **Project contamination**: Any project name in a generic skill is a bug
7. **Time-pinned references in skill body**: Dates, version numbers, "after X lands" notes,
   and PR numbers in skill body rot quickly and become noise. State the post-change contract
   directly rather than describing the transition. When migration guidance is genuinely
   useful (callers crossing a breaking change), pin the contrast in a "Current API" /
   "Old API" subsection rather than as inline dates or PR references. Leave the upgrade
   narrative for PR descriptions and commit messages, which are the right home for it.
   - Avoid: "After PR NNN merges, Validation will take bytes."
   - Prefer: "Validation takes a `Serialization.Byte_Array` parameter."
8. **Terminology drift across skills**: Pick one term per concept and use it everywhere.
   Adamant convention examples: "connector" not "port" or "channel"; "rate group" not
   "scheduler slot"; "data product" not "telemetry point" (telemetry-point is COSMOS-side
   vocabulary). When introducing a new term, grep existing skills for synonyms and pick
   the dominant one before committing. Drift is hard to spot in review and confuses
   agents that load multiple skills with conflicting vocabularies.
9. **Over-prescription for capable models**: Step-by-step choreography where a goal plus
   constraints would do. The most capable current model generations measurably produce
   *worse* output when over-constrained -- they follow stale steps literally instead of
   exercising judgment -- while the invariants those steps were protecting still hold.
   Keep the invariant, drop the choreography. The symmetric failure also exists:
   less capable models under-perform when conventions are implied rather than stated.
   Cross-tier validation (see `adamant-skill-campaign`) finds both edges. When one skill
   must serve both tiers, state invariants and conventions explicitly and leave execution
   order to the agent -- unless order is load-bearing, in which case say why it is.

## References
- [references/validation-history.md](references/validation-history.md) -- Convergence data from 19 rounds of skill validation
- [references/refinement-methodology.md](references/refinement-methodology.md) -- Stress test design, experience pool, ancestor tracking
- [references/evolution-plan.md](references/evolution-plan.md) -- Plan for continued improvement beyond per-skill convergence
- [references/decision-point-methodology.md](references/decision-point-methodology.md) -- Outcome-aligned measurement for skill effectiveness via decision point tracking
- [references/framework-verified-skill-correction.md](references/framework-verified-skill-correction.md) -- Study -> hypothesize -> build/verify -> fix -> campaign-test -> escalate loop for correcting skills against framework source code
- [references/framework-extension-methodology.md](references/framework-extension-methodology.md) -- Creating skills for patterns the framework supports but no component demonstrates (post-convergence escalation)

### Framework Extension (Beyond Templates)

Once skills covering existing framework patterns converge (5+ consecutive clean), escalate to EXTENSION scenarios -- patterns the framework's architecture supports but no existing component demonstrates. See `references/framework-extension-methodology.md` for the full methodology.

**Key principle**: The framework's base classes, discovery mechanisms, and dependency infrastructure define a capability space larger than what existing components exercise. Skills should teach agents to reason from architecture, not just follow recipes.

**Difficulty spectrum**:
- Levels 1-3: Follow/combine/adapt existing patterns (framework-verified correction)
- Levels 4-6: Infer/compose/design from architecture (framework extension)

Extension scenarios test whether skills teach UNDERSTANDING, not just PROCEDURES.

## Related Skills
- **Skill selector**: [adamant-skill-selector](../adamant-skill-selector/SKILL.md)
- **Knowledge acquisition**: [knowledge-acquisition](../knowledge-acquisition/SKILL.md)
- **Running validation as a campaign**: [adamant-skill-campaign](../adamant-skill-campaign/SKILL.md) -- in-session Workflow orchestration of the cold-start validation loop described here
