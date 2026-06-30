---
name: knowledge-acquisition
description: Systematic study of codebases, frameworks, or domains using isolated Sonnet sessions to produce reusable skills. Use when asked to learn a repo, study a framework, gain expertise on a codebase, or create skills from existing knowledge. Covers scoping, delegation, incremental note-taking, quality gates, and skill consolidation.
---

# Knowledge Acquisition

Pattern for using cheaper model sessions (Sonnet) to study large codebases and produce reusable skills.

## Tool-Agnostic Core

The knowledge acquisition process is tool-agnostic. The core loop is:

1. **Scope** the target (file count, structure, complexity)
2. **Read systematically** (README first, then by priority)
3. **Write notes incrementally** (don't rely on memory alone)
4. **Create/improve skills** from what you learn
5. **Validate** skills via cold-start exercises
6. **Consolidate** and update long-term memory

This pattern works with any agent framework, IDE, or CLI that can read files, spawn sub-sessions, and write output.

## When to Use

- "Learn this repo" / "become an expert on X"
- "Create skills from this codebase"
- "Study this framework and document what you find"
- Improving existing skills with deeper knowledge

## Process

### 1. Scope the Study

Before spawning anything, assess the target:

```bash
# Size the repo
find <path> -type f -not -path '*/.git/*' | wc -l
find <path> -type f -not -path '*/.git/*' -exec wc -c {} + | tail -1

# Understand structure
find <path> -maxdepth 2 -type d | sort
ls <path>/
```

**Budget rules:**
- Under 50 files: single session, 10-15 min timeout
- 50-200 files: single session, 30-60 min timeout
- 200+ files: multiple sessions by directory, or one long session (60+ min)
- Large repos: read README/docs first in main session, then delegate deep reads

### 2. Prepare the Scratch File

Create a notes file BEFORE spawning. The study session MUST write to it incrementally.

```bash
# Create scratch file
echo "# Study Notes: <target>" > /path/to/workspace/memory/<target>-notes.md
echo "" >> /path/to/workspace/memory/<target>-notes.md
echo "## Structure" >> /path/to/workspace/memory/<target>-notes.md
```ada

### 3. Spawn the Study Session

Spawn a study agent (the Agent tool for one subagent, or a Workflow for several in parallel) with these mandatory elements:

**Task prompt template:**
```
Study <target> at <path>. Write incremental notes to <scratch-file> after each
major section -- do NOT rely on context alone, it will compact and you will
lose early reads.

Read systematically:
1. README and top-level docs first
2. <specific directories in priority order>
3. <specific files or patterns to focus on>

After reading, create/improve skills at <skills-path>.
Use the skill-creator scripts at <scripts-path>:
- init_skill.py to initialize (use --path flag, single level only)
- quick_validate.py to validate
- package_skill.py to package

Skill guidelines:
- Only include knowledge the model would NOT already have
- Prefer improving existing skills over creating new ones
- No generic boilerplate -- every line must be framework-specific
- No emoji in frontmatter metadata
- Validate all skills before finishing

Report what you learned and what skills you created/modified.
```ada

**Agent parameters:**
- Model: pick a cheaper model for bulk reading (e.g. Sonnet) via the spawn tool's `model` parameter
- Scope/timeout: match to the scope assessment (see budget rules above)
- Isolated context: a subagent has its own context window, so bulk reading does not pollute the main session

### 4. Quality Gate

When the study session finishes, the main session MUST review before accepting:

**Check for these failure modes:**

- [ ] **Generic filler**: Does the skill contain boilerplate the model already knows? (e.g., generic ARM register layouts, basic Ada syntax, standard Python patterns). Remove it.
- [ ] **Scope inflation**: Did it create skills that overlap significantly? Consolidate.
- [ ] **Double nesting**: Check `find skills/<name> -name SKILL.md` -- should be exactly one level deep.
- [ ] **Unverified claims**: Did it claim "comprehensive study" but only read a handful of files? Spot-check against actual repo contents.
- [ ] **Missing specifics**: Are YAML examples, file paths, and commands from the actual repo, or fabricated?

**Consolidation rules:**
- If two skills share >30% content, merge them
- If a skill is <100 lines, consider merging into a related skill
- If a skill is >500 lines, split into SKILL.md + references/

**Context budget awareness:**
Skills are loaded into the agent's context window before task execution. A skill
that consumes too much context leaves insufficient room for the actual work.
- SKILL.md alone: aim for 150-350 lines (sweet spot for most tasks)
- SKILL.md + all references combined: stay under ~800 lines total
- Only reference files explicitly linked from SKILL.md are loaded
- Dense tasks (multi-file code generation) need MORE free context -- keep skills leaner
- Shallow tasks (lookup, quick answers) tolerate larger skills
- When in doubt, move detailed examples to references/ and keep SKILL.md as an index
- Test by asking: "Can a model ingest this skill AND still do a complex task?"

### 5. Practice-Driven Refinement

After initial skill creation, shift to building real artifacts to discover gaps. See [references/practice-driven-refinement.md](references/practice-driven-refinement.md) for the full pattern. Key idea: build using only skills as reference, let compiler errors reveal what's missing, update skills immediately.

**Study generated output, not just source.** For code generation frameworks, the generated files ARE the API contract. Read `build/src/`, `build/template/`, and every output directory. The generated base class, event/command/data product packages, and template stubs define the exact function signatures, naming conventions, and type paths your implementation must use. Reading only the generator source or YAML schemas gives you the input format but not the output contract.

**Automated campaigns**: For systematic validation at scale, run multi-tier campaigns with escalating complexity, phased execution (to stay within context limits), and convergence criteria, orchestrated in-session with the Workflow tool. See [adamant-skill-campaign](../adamant-skill-campaign/SKILL.md) for the harness, and the "Automated Refinement Campaigns" section in [references/practice-driven-refinement.md](references/practice-driven-refinement.md).

**Adaptive phase granularity**: When a phase fails repeatedly due to context exhaustion (not skill errors), split it further rather than retrying at the same granularity. Separating type definitions from component implementation, or component creation from test setup, gives Sonnet enough headroom. Finer phases also improve error attribution. Adjust dynamically based on observed failures.

**Token-efficiency optimization**: After convergence, optimize skills to reduce token consumption via **structural changes only** (phase consolidation, deterministic read order, conditional reference loading, pipeline shape). Wording-level changes are not measurable -- run-to-run variance dominates. Re-run the SAME scenario with before/after CSV tracking. See "Token-Efficiency Optimization" and "Structural vs Wording Optimization" in [references/practice-driven-refinement.md](references/practice-driven-refinement.md).

**Campaign progression ladder**: Converge -> Optimize -> Relax -> Escalate. If skills converge with detailed prompts, optimize token efficiency. If efficient, relax prompts (high-level descriptions instead of field-by-field specs) to test whether skills guide design, not just implementation. If converged with relaxed prompts, increase difficulty. See "Integration with Campaigns" and "Prompt Relaxation" in [references/practice-driven-refinement.md](references/practice-driven-refinement.md).

**Decision point analysis**: Beyond error counts, track individual decision points where skills prescribe specific actions. Score agent output against these points to distinguish skill gaps (all agents miss) from unstable guidance (some agents miss) and stable patterns (all agents hit). Apply fixes between iterations, not at the end. See [adamant-skill-creation/references/decision-point-methodology.md](../adamant-skill-creation/references/decision-point-methodology.md) for the full methodology.

### 5b. Experience Pool Aggregation

When running multiple study or validation sessions, aggregate discoveries across sessions
rather than letting each session's findings remain isolated.

**The problem:** Sub-agent A discovers that Tick.T needs Unsigned_32 for Count. Sub-agent B,
working on a different skill, hits the same error independently. Without aggregation, each
session rediscovers the same facts.

**The solution:**
1. After each sub-agent finishes, extract cross-cutting lessons (not just skill-specific ones)
2. Propagate to all affected skills before spawning the next sub-agent
3. Track which sessions contributed to each skill ("ancestor tracking")
4. Skills with diverse ancestry (fixes from multiple independent sessions) are more robust

See `adamant-skill-creation/references/refinement-methodology.md` for the full
experience pool pattern and state file format.

### 6. Update Memory

After consolidation, update MEMORY.md with:
- What was studied and when
- Key architectural patterns learned
- Skills created/modified
- Lessons learned about the study process itself

## Budget Awareness

Bulk reading is the main cost of study sessions, so manage it deliberately:

- **Use a cheaper model for bulk reading** (e.g. Sonnet) via the spawn tool's `model`
  parameter; reserve the stronger model for synthesis. A subagent that fills its context
  window has consumed its full budget for that pass.
- **Size scope to the context window**: smaller, focused sessions beat one massive session
  -- easier to spot-check, and less is lost to compaction. Split a target that repeatedly
  exhausts context rather than retrying at the same granularity.
- **Check results between spawns**, not just at the end; kill a session early if its scratch
  file shows it has gone off-track.
- **Ask before large spend**: if a multi-session study will run well past the user's comfort
  threshold, confirm first. A Workflow exposes a token budget (`budget.spent()` /
  `budget.remaining()`) for in-session campaigns.

## Build Validation Notes

### Long-Running redo Commands
`admt style --all`, `admt test --all`, and `admt coverage --all` are long-running commands that can take many minutes. **Ctrl+C typically does NOT stop them** -- the process continues inside the Docker container. If you need to abort, restart the container:
```bash
docker restart <container_name>
```

### Validation Responsibility
The **primary agent** (not sub-agents) runs `admt style`, `admt test`, and `admt coverage` for validation. Sub-agents create/modify files; the main agent validates them. This prevents concurrent redo conflicts and keeps the validation loop visible.

## Anti-Patterns

**Do not:**
- Spawn a study session without a scratch file directive
- Trust "study complete" without spot-checking
- Create skills for generic knowledge (the model already knows Ada, Python, Docker basics)
- Let sub-agents create unbounded numbers of skills
- Skip the consolidation pass

**Watch for:**
- Context compaction destroying early reads (mitigated by scratch file)
- Sub-agent hallucinating framework-specific details it never read
- Emoji and non-standard metadata in skill frontmatter

## Skill Quality Checklist

Before accepting any skill output:

- [ ] Every code example is from the actual codebase (not fabricated)
- [ ] File paths reference real files in the repo
- [ ] YAML structures match the actual schema
- [ ] Commands are tested or verified against docs
- [ ] No overlap with existing skills
- [ ] Validates with quick_validate.py
- [ ] Frontmatter has only name and description

---

## Spawning Study Agents

Delegate isolated study to subagents so bulk reading does not consume the main session's
context:

- **One target**: the Agent tool spawns a single subagent with its own context window.
- **Several in parallel**: a Workflow fans out one study agent per area and collects their
  notes (the same fan-out [adamant-skill-campaign](../adamant-skill-campaign/SKILL.md)
  applies to skill validation).
- **Model**: pass a cheaper model (e.g. Sonnet) via the spawn tool's `model` parameter for
  bulk reading; reserve the stronger model for synthesis.
- **Scratch files**: have each agent write incremental notes to `memory/<target>-notes.md`
  -- context compacts, and unwritten early reads are lost.
- **Budget**: size each agent's scope to its context window; split a target that repeatedly
  exhausts context into finer study sessions rather than retrying at the same granularity.
