---
name: adamant-skill-campaign
description: Run cold-start skill-validation campaigns in-session with the Workflow tool. Use when validating new or changed Adamant skills, testing project-specific skills, sandbox/regression-checking skills, or observing where cold-start agents deviate from skill prescriptions (HIT/MISS/GAP) -- the modern Workflow/ultracode replacement for external cron + `claude -p` campaign harnesses.
---

# Adamant Skill Campaign

Validate skills by having fresh agents use them from scratch, then scoring where the
output deviates from what the skills prescribe. This skill is the **harness** -- how to
run that loop in-session with the Workflow tool. The **measurement theory** (decision
points, convergence, fix-isolation) lives in [adamant-skill-creation](../adamant-skill-creation/SKILL.md);
read it for the *why*, read this for the *how to run it*.

Earlier campaigns used an external `cron` + `claude -p --permission-mode bypassPermissions`
+ `state.json` heartbeat to spawn cold-start agents autonomously. The Workflow tool plus
auto-permission modes do that in-session, observably, with no external bookkeeping. Keep
only the two reusable assets: **relaxed prompts** and the **decision-point audit**.

## Quick Start

One cold-start validation = a two-phase Workflow: a build agent, then an audit agent.

```js
export const meta = {
  name: 'skill-campaign-smoke',
  description: 'Cold-start build of a relaxed spec, then DP audit',
  phases: [{ title: 'Build' }, { title: 'Audit' }],
}
const SKILLS = '<skills_repo>'        // dir holding the SKILL.md files under test
const PROJECT = '<project_dir>'       // an Adamant project to build into
const COMPONENT = 'campaign_<scratch>'  // a non-colliding scratch name

phase('Build')
const build = await agent(`You are a COLD-START agent. Use ONLY these skills; do not
use prior Adamant knowledge. Read in order:
  ${SKILLS}/adamant-skill-selector/SKILL.md
  ${SKILLS}/adamant-component-dev/SKILL.md
  ${SKILLS}/adamant-component-dev/references/pitfalls-and-checklist.md
  ${SKILLS}/adamant-testing/SKILL.md
TASK: <relaxed spec -- WHAT to build, never HOW>. Build into ${PROJECT}.
BUILD ENV (scaffolding, not skill content): <build/test commands, see Targeting>.
RULES: create only under .../src/components/${COMPONENT}/; do not modify other
components; run NO git commands; report honest error counts.`,
  { schema: BUILD_SCHEMA, effort: 'high' })

phase('Audit')
const audit = await agent(`Score this cold-start run's decision points per
${SKILLS}/adamant-skill-creation/SKILL.md. Read the created files and the prescribing
skills. For each DP return HIT / MISS / GAP with file:line evidence. Build report:
${JSON.stringify(build, null, 2)}`, { schema: AUDIT_SCHEMA, effort: 'high' })

return { build, audit }
```

After it returns: read the audit, reset the project tree (below), and -- only on a
**stable** miss -- fix the skill (one fix per cycle).

## The Loop, Ported to a Workflow

| External harness (cron/`claude -p`) | Workflow / ultracode |
|---|---|
| `cron */5` + `/heartbeat` driver | Workflow control flow (deterministic, in-session) |
| `claude -p --cwd P --permission-mode bypassPermissions` spawn | `agent(prompt, {...})` under the session's auto mode |
| `state.json` (tier/phase/iteration/pid) | JS variables + the run journal (resume via `resumeFromRunId`) |
| `results/*.log` | `agent()` structured return (JSON schema) |
| `audits/*.md` DP scoring | an Audit-phase `agent()` (verify stage) |
| "5x consecutive_clean -> converged" | loop-until-count / loop-until-dry pattern |
| "3+ misses -> fix skill, commit" | synthesis stage proposes the edit; apply inline |

No `state.json`, no `pid` tracking, no cron. The Workflow *is* the state machine.

## Relaxed Prompts (specify intent, never the convention)

A campaign tests whether the **skills** carry the framework *conventions* -- so the prompt
reads like a request from someone who knows the *system* but not the framework idioms. The
line is **intent vs convention**, not "construct named or not":

- **Allowed -- specify intent (including the interface)**: behavior in system terms; active
  vs passive; structure / decomposition; subassembly-pattern intent; "wrap algorithm X";
  complete coverage / "include tests"; a chosen component name; **and the interface
  elements themselves when you want them** -- "publish a data product reporting the status",
  "emit an event on the transition", "a configurable `<limit>` parameter", "consume a
  sampled `<value>`", "a command to reset". Naming a data product / event / parameter /
  data dependency / command is a legitimate human requirement, not contamination.
- **Build scaffolding** (NOT skill content): build/test command (see Targeting), project
  path, scratch name, cold-start rule. *How to invoke the build*, not how to design it.
- **NEVER prescribe the convention** (that is the skill's job and the audit's signal):
  connector **kinds** (`recv_sync` / `request` / `modify` / `get` / `send`), YAML field
  layouts and **format codes** (`E8`, `U16`, ...), type/package naming and collision
  rules, `Set_Up` vs `Init` and call ordering (e.g. `Update_Parameters` first),
  packed-record byte layout, explicit file lists. Supplying any of these makes that
  decision point a forced HIT -- contaminated.

**Convention vs contamination (same data product):**
- OK (intent): "publish a data product reporting the sample, the limit, and the in/out-of-
  limit status."
- CONTAMINATED (convention): "...via a `send` connector; the report record's enum field
  uses `format: E8`; name the data product differently from its type package."

The first lets the skills decide connector kind, record layout, and naming -- the signal.
The second hands them over. **If the spec omits a construct entirely, the convention is the
guiding force** -- the skills decide whether it should even be a data product, event, etc.

**Two relaxation levels, both valid:**
- *Specify the construct* ("a data product for X", "an event on Y") -> tests how the skills
  *realize* it (connector kind, layout, naming, ordering).
- *Omit the construct* ("report the status", "flag the transition") -> additionally tests
  whether the skills *choose* the right construct. Use this to exercise construct-choice too.

**Skill pathing.** Most human: point the agent at the skills repo and the
**skill-selector** and let it route itself -- this also validates the selector's routing.
Give an explicit deterministic read-order only when isolating one skill (skips the routing
test but is prompt-cache-stable). Keep stable parts (paths, rules) at the front of the
prompt, variant parts (iteration number) at the end, for cache hits.

## Decision-Point Audit

The audit agent is a verify stage. It scores each decision point HIT / MISS / GAP against
the skills (full definitions and the "never blame the agent for a stable miss" rule are in
[adamant-skill-creation](../adamant-skill-creation/SKILL.md)). Make it:

- **Read the artifacts on disk**, not just the build agent's self-report (self-reports
  hide unreported self-corrections -- a MISS->FIX still counts as a MISS).
- **Cite evidence** (`file:line` or the artifact) for every verdict.
- **Define DPs from the skill, not the output**: connector kinds (parameter -> `modify`,
  data dependency -> `request` not `get`, data product -> `send`), naming rules (DP name
  != type name; parameter type package != parameter name; standalone enum = `Pkg.Enum.E`),
  required files (`.all_path`, test `env.py`), `Set_Up` vs `Init`, tester/assertion
  patterns.

For a stronger signal, run the **same** relaxed spec through N cold-start agents in
parallel and aggregate: a DP that 3+ independent agents MISS is a skill gap, not agent
noise.

```js
const N = 3
const runs = (await parallel(Array.from({ length: N }, (_, i) => () =>
  buildAgent(i).then(b => auditAgent(b))))).filter(Boolean)
// stable MISS across >=3 runs on the same DP -> fix that skill (one fix per cycle)
```

## Convergence

Iterate until the skill produces clean cold-start output. Reset the project tree between
iterations so each agent starts fresh.

```js
const TARGET = 5, MAX = 12
let clean = 0
for (let i = 1; clean < TARGET && i <= MAX; i++) {
  const r = await runIteration(i)          // build + audit
  const ok = r.build.error_count === 0 && r.audit.decision_points.every(d => d.verdict !== 'MISS')
  clean = ok ? clean + 1 : 0
  log(`iter ${i}: ${ok ? 'clean' : 'dirty'} (${clean}/${TARGET})`)
  resetTree()                              // see Sandboxing -- between iterations only
}
```

Convergence target = 5 consecutive clean (configurable). Track the DP hit-ratio across
iterations to tell convergence (rising) from a plateau (fundamentally unclear skill).

## Sandboxing and Safety

Cold-start agents build real artifacts; keep the blast radius zero:

- **Build inside the container** via `admt`/`adamant_env.sh` -- never on the host.
- **Scoped scratch name**: create only `src/components/campaign_<scratch>/` (and shared
  types only if required). The agent must not modify or rename other components.
- **No git from agents**: agents never `commit`, `push`, or `checkout`. The orchestrator
  (you) owns version control.
- **Reset between iterations** (orchestrator, not the agent, to avoid mid-run races):
  ```bash
  git -C <project> checkout -- . && git -C <project> clean -fd
  ```
- **Leave artifacts for the audit**: do not reset *before* the audit agent reads the files.
- **Bounded agents**: Workflow agents are time/▢-bounded; a failed build drops that item to
  `null` -- filter with `.filter(Boolean)`.

## Targeting

Point the read-order at the skills you want to validate -- **generic** skills
(`<skills_repo>/adamant-*`) or a project's **own** skills
(`<project>/skills/` or `<project>/agents/*/SKILL.md`). The campaign is identical either way.

Build scaffolding depends on how the target project is wired:

- **admt-registered project** (preferred): `export ADMT_ENV=<project> ADMT_NONINTERACTIVE=1`;
  `admt env start` (with `ADMT_NONINTERACTIVE=1` set, no prompt; `--yes` is not an `admt env start` option);
  `admt build <path>`; `admt test <path>/test`; `admt style <path>`.
- **Legacy / unregistered**: `bash <project>/docker/adamant_env.sh exec "cd /home/user/<project> && redo <target>"`.

Discover which projects are registered with `admt env list`. A project whose container is
`not-found` must be started first; budget for the one-time container build.

## Checklist

1. Pick the skill(s) under test and the build-ready target project (`admt env list`).
2. Write a **relaxed** spec -- specification + build scaffolding only, no how-to.
3. Define the decision points up front (from the skills, before running).
4. Author the two-phase Workflow (Build -> Audit); use `effort: 'high'` for both agents.
5. Run it; read the audit; inspect the created files on disk.
6. For a confident gap signal, re-run N-parallel or iterate to convergence.
7. On a **stable** MISS (3+), fix the one responsible skill, re-run, confirm it resolves.
8. Reset the project tree; commit only the *skill* change (the orchestrator, never an agent).

## Common Errors

- **Contaminated prompt**: putting connector kinds / file lists / naming rules in the task
  prompt. Then every DP is a forced HIT and the test proves nothing. Spec + scaffolding only.
- **Scoring from the self-report**: agents under-report their own corrections. Audit the
  files on disk; a MISS->FIX is still a MISS.
- **Blaming the agent**: a stable miss across independent cold-start agents is a *skill*
  gap, not agent quality. Fix the skill.
- **Resetting before audit**: wiping the tree before the audit agent reads the artifacts.
  Reset *between iterations*, after the audit.
- **Concurrent builds in one container**: two agents building the same project's container
  at once corrupts redo state. Serialize (one build agent per project per moment), or give
  each parallel agent a separate project/container.
- **Multiple fixes per cycle**: batching skill edits hides which one resolved the miss.
  One fix, re-run, confirm, then the next.
- **Dead target env**: spawning a build agent against a `not-found`/broken container burns
  the whole agent on env wrangling. Pre-flight the env (`admt env status` / a trivial
  build) before the campaign.
- **Stale framework build state / admt quirks**: a corrupt framework redo state surfaces as
  cascading "size for ... too small" errors on *framework* types -- fix with `admt clean
  --all` on the framework root and pre-flight it. `admt env start` takes no `--yes` flag
  (set `ADMT_NONINTERACTIVE=1`), and `admt templates` in noninteractive mode generates stubs
  but does not copy them (copy them manually). These are env/tool gotchas, not skill gaps --
  keep them out of the DP scoring.
- **Calling an all-HIT N=1 run "done"**: one clean cold start proves little. A real baseline
  needs N-parallel (for *stable* misses) and escalating difficulty; treat a findings-free
  run as a prompt that wasn't hard enough.
- **Permission-gated shared edits**: a build/wrapping workflow may require editing a *shared*
  build file outside the scratch scope (e.g. registering a new source in a shared
  `CMakeLists`, or adding a build-path entry), which may be permission-gated. Pre-authorize
  it in the build scaffolding, or the run stalls at the link step. A link-only failure (clean
  compile, undefined symbols) is an env/BLOCKED condition, not a decision-point MISS.

## References
- [references/workflow-harness.md](references/workflow-harness.md) -- full annotated Workflow
  script (build + audit + N-parallel + convergence) and how to interpret a run.

## Related Skills
- **Skill creation / validation theory**: [adamant-skill-creation](../adamant-skill-creation/SKILL.md) -- decision points, convergence, fix-isolation, project-vs-generic separation
- **Task routing**: [adamant-skill-selector](../adamant-skill-selector/SKILL.md) -- the read-order a cold-start agent should follow
- **Systematic study**: [knowledge-acquisition](../knowledge-acquisition/SKILL.md)
