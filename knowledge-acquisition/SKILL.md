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
```

### 3. Spawn the Study Session

Use sessions_spawn or cron with these mandatory elements:

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
```

**Session parameters:**
- Model: anthropic/claude-sonnet-4-20250514 (cheaper for bulk reading)
- Timeout: match to scope assessment (see budget rules above)
- sessionTarget: isolated (own context, no main session pollution)

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

### 6. Update Memory

After consolidation, update MEMORY.md with:
- What was studied and when
- Key architectural patterns learned
- Skills created/modified
- Lessons learned about the study process itself

## Usage Tracking and Budget Awareness

### Checking Current Usage

Before spawning study sessions, check current spend:

```bash
# Quick usage report (all sessions, estimated cost)
python3 {baseDir}/scripts/usage_report.py

# JSON output for scripting
python3 {baseDir}/scripts/usage_report.py --format json
```

The script reads the OpenClaw session store and estimates cost per session based
on model and total tokens consumed. Costs are blended estimates (input+output
averaged); real cost depends on the input/output token ratio.

### Per-Session Status

Use `session_status` tool to check individual session usage (tokens, model,
context window fill). For sub-agent sessions, pass their sessionKey.

Use `sessions_list` to see all active sessions with token counts:
- `totalTokens` = how much of the context window has been consumed
- A session at 200,000 tokens has maxed its context (compacted at least once)

### Budget Rules

**Before spawning:**
1. Run usage_report.py to see cumulative spend
2. Estimate new session cost: (timeout_minutes / 10) * model_rate_per_MTk is a rough upper bound
   - Sonnet: ~$1.20 per maxed-out 200k context session
   - Opus: ~$6.00 per maxed-out 200k context session
3. If cumulative spend exceeds the user's comfort threshold, ask before proceeding

**During multi-session studies:**
- Check usage between spawns, not just at the end
- If a session maxes context (200k tokens), it consumed its full budget
- Four Sonnet sessions maxing context = ~$4.80
- Stagger sessions and check results before spawning more

**Cost optimization:**
- Always use Sonnet for bulk reading (6x cheaper than Opus)
- Set realistic timeouts -- a 60min timeout on a 20-file repo wastes budget
- Smaller, focused sessions > one massive session (easier to spot-check, less waste on compaction)
- Kill sessions early if scratch file shows they have gone off-track

### Model Cost Reference (approximate blended $/MTk)

| Model | Blended $/MTk |
|-------|--------------|
| claude-opus-4 | ~$30 |
| claude-sonnet-4 | ~$6 |
| claude-haiku-3.5 | ~$1.60 |

These are rough. Actual cost depends on input:output ratio. Output tokens cost
3-5x more than input tokens for most models.

## Build Validation Notes

### Long-Running redo Commands
`redo style_all`, `redo test_all`, and `redo coverage_all` are long-running commands that can take many minutes. **Ctrl+C typically does NOT stop them** -- the process continues inside the Docker container. If you need to abort, restart the container:
```bash
docker restart <container_name>
```

### Validation Responsibility
The **primary agent** (not sub-agents) runs `redo style`, `redo test`, and `redo coverage` for validation. Sub-agents create/modify files; the main agent validates them. This prevents concurrent redo conflicts and keeps the validation loop visible.

## Anti-Patterns

**Do not:**
- Spawn a study session without a scratch file directive
- Trust "study complete" without spot-checking
- Create skills for generic knowledge (the model already knows Ada, Python, Docker basics)
- Let sub-agents create unbounded numbers of skills
- Skip the consolidation pass

**Watch for:**
- Context compaction destroying early reads (mitigated by scratch file)
- Model override not taking effect in cron (use session_status to force)
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

## Appendix: OpenClaw Integration

When using this skill within OpenClaw:

- **Session spawning**: Use `sessions_spawn` or cron for study sessions. Sonnet is preferred for bulk reading (6x cheaper than Opus).
- **Scratch files**: Direct study sessions to write to `memory/<target>-notes.md` incrementally.
- **Session parameters**: Set `sessionTarget: isolated` for sub-agent study sessions.
- **Usage tracking**: Run `usage_report.py` before spawning to check cumulative spend.
- **Session status**: Use `session_status` to check context window fill; sessions at 200k tokens have maxed context.
- **Model override**: Verify model override takes effect with `session_status` after spawn.
