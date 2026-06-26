# Workflow Campaign Harness -- Full Script

The complete Workflow script for a cold-start skill-validation campaign. Generic
placeholders (`<skills_repo>`, `<project>`, `<scratch>`) -- substitute for your run. This
is the expanded form of the Quick Start in [../SKILL.md](../SKILL.md).

## Single validation (Build -> Audit)

```js
export const meta = {
  name: 'skill-campaign',
  description: 'Cold-start build of a relaxed spec, then decision-point audit',
  phases: [{ title: 'Build' }, { title: 'Audit' }],
}

const SKILLS = '<skills_repo>'
const PROJECT = '<project_dir>'
const COMPONENT = 'campaign_<scratch>'

// Relaxed spec -- specify INTENT, not the CONVENTION. Naming interface elements (a
// configurable limit, a sampled input, a status report, a transition flag -- or "a data
// product"/"an event" outright) is legitimate. Do NOT prescribe connector kinds, format
// codes, naming, or ordering: the skills supply those, and the audit scores whether they
// did. Exercises parameter + data-dependency + data-product + event + tests. See
// ../SKILL.md "Relaxed Prompts (specify intent, never the convention)".
const SPEC = `A passive component named "${COMPONENT}" that monitors a sampled value
against a configurable limit: on each Tick it fetches the latest sample (data dependency)
and compares it to a limit (parameter); publishes a data product with sample/limit/status;
emits an event on transition to out-of-limit. Include tests for in-limit, out-of-limit,
and the transition.`

const BUILD_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    env_ok: { type: 'boolean' },
    component_name: { type: 'string' },
    files_created: { type: 'array', items: { type: 'string' } },
    build_clean: { type: 'boolean' }, style_clean: { type: 'boolean' }, tests_pass: { type: 'boolean' },
    error_count: { type: 'integer' },
    errors: { type: 'array', items: { type: 'string' } },
    key_decisions: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['env_ok', 'component_name', 'build_clean', 'style_clean', 'tests_pass', 'error_count', 'key_decisions', 'notes'],
}

const AUDIT_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    decision_points: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: {
        dp: { type: 'string' }, skill_source: { type: 'string' },
        verdict: { type: 'string' }, evidence: { type: 'string' },
      }, required: ['dp', 'skill_source', 'verdict', 'evidence'],
    } },
    compile_errors: { type: 'integer' },
    skill_gaps: { type: 'array', items: { type: 'string' } },
    recommendation: { type: 'string' },
    summary: { type: 'string' },
  }, required: ['decision_points', 'compile_errors', 'skill_gaps', 'summary'],
}

phase('Build')
const build = await agent(`You are a COLD-START Adamant agent. Use ONLY the skills below;
do NOT rely on prior Adamant knowledge. Read in order:
  ${SKILLS}/adamant-skill-selector/SKILL.md
  ${SKILLS}/adamant-component-dev/SKILL.md
  ${SKILLS}/adamant-component-dev/references/pitfalls-and-checklist.md
  ${SKILLS}/adamant-testing/SKILL.md

TASK (build into ${PROJECT}): ${SPEC}

BUILD ENV (scaffolding, not skill content):
- export ADMT_ENV=<project> ADMT_NONINTERACTIVE=1
- admt env start   (ADMT_NONINTERACTIVE=1 is set, so no prompt; do NOT pass --yes -- not
  an option in admt 0.1.0. If the container is 'not-found' and cannot come up, STOP and
  report env_ok=false with the error -- do not hang)
- build: admt build ${PROJECT}/src/components/${COMPONENT}
- style: admt style ${PROJECT}/src/components/${COMPONENT}
- tests: admt test ${PROJECT}/src/components/${COMPONENT}/test
- never run concurrent redo/admt; use admt clean, never rm -rf build

RULES: create only under .../src/components/${COMPONENT}/ (shared types only if required);
do NOT modify other components; run NO git commands; leave files for audit; report honest
error counts and the concrete choices you made in key_decisions.`,
  { label: 'cold-start:build', phase: 'Build', schema: BUILD_SCHEMA, effort: 'high' })

phase('Audit')
const audit = await agent(`Audit this cold-start run's decision points per
${SKILLS}/adamant-skill-creation/SKILL.md. Read the files on disk at
${PROJECT}/src/components/${COMPONENT}/ and the prescribing skills. Score each DP
HIT / MISS / GAP with file:line evidence. Never blame the agent for a stable miss.
Build report: ${JSON.stringify(build, null, 2)}`,
  { label: 'audit:decision-points', phase: 'Audit', schema: AUDIT_SCHEMA, effort: 'high' })

return { build, audit }
```

After the run: read `audit`; inspect the files; then
`git -C <project> checkout -- . && git -C <project> clean -fd` to reset.

## Convergence sample (N parallel cold starts)

Stronger signal: run the same spec through N independent agents, aggregate the misses. A
DP missed by 3+ agents is a skill gap.

```js
const N = 3
const results = (await parallel(Array.from({ length: N }, (_, i) => () =>
  agent(buildPrompt(i), { label: `build:${i}`, phase: 'Build', schema: BUILD_SCHEMA, effort: 'high' })
    .then(b => agent(auditPrompt(b), { label: `audit:${i}`, phase: 'Audit', schema: AUDIT_SCHEMA, effort: 'high' }))
))).filter(Boolean)

// Tally MISS verdicts per DP across runs; >= 3 on the same DP -> fix that skill.
const misses = {}
for (const r of results) for (const d of r.decision_points)
  if (d.verdict === 'MISS') misses[d.dp] = (misses[d.dp] || 0) + 1
```

WARNING: N parallel agents building the **same** project's container corrupt redo state.
Either serialize the build phase, or give each agent a **distinct** project/container.

## Convergence loop (iterate to clean)

```js
const TARGET = 5, MAX = 12
let clean = 0
for (let i = 1; clean < TARGET && i <= MAX; i++) {
  const r = await runIteration(i)   // one Build+Audit
  const ok = r.build.error_count === 0 && r.audit.decision_points.every(d => d.verdict !== 'MISS')
  clean = ok ? clean + 1 : 0
  log(`iter ${i}: ${ok ? 'clean' : 'dirty'} -> ${clean}/${TARGET}`)
  resetTree()                       // between iterations only, after the audit
}
```

`resetTree()` shells out to `git checkout -- . && git clean -fd` on the project. Apply a
skill fix only between iterations, one at a time, and confirm it resolves before the next.

## Worked Run

A single cold-start validation (this script; relaxed spec for a passive limit-monitor --
configurable limit, a sampled input, a status report, a transition flag, with tests).

Outcome: **0 compile errors, all tests pass, 100% line coverage, style clean.** Every
*realization* decision point HIT from the conventions alone -- connector kinds (parameter
-> `modify`, data dependency -> `request`, time -> `get`, data product/event -> `send`),
DP-name vs type-package, enum-vs-record base-name collision, standalone-enum `Pkg.Enum.E`
+ `E8`, project-prefixed type names, byte-aligned record under buffer, no `format` on
packed fields, `.all_path` vs test `env.py`, `Init` iff `init:`, `Set_Up is null`,
`Update_Parameters` first, `.Value` access, `*_Send_Dropped` handlers, no redundant
`with`s, typed `.Assertion` full-record tests.

Findings the run surfaced (each is a "success" -- it tells us what to fix):
- **Stale framework build state** broke the whole project first (cascading "size for ...
  too small" on framework types) until `admt clean --all` on the framework root. Pre-flight
  a framework clean, or the first agent burns time diagnosing the env.
- **Inherited tester field (MISS->FIX):** the agent re-added a base-class-inherited field to
  the generated tester (the tester body references it, so it looked dropped), hit a
  conflict, reverted. A MISS->FIX is still a gap -> the testing skill should state the field
  is inherited and must not be re-declared.
- **admt 0.1.0 quirks:** `env start` takes no `--yes`; `templates` in noninteractive mode
  generates but does not copy stubs (copy the generated stubs manually).

Prompt-design lesson: this spec *named* the constructs, so it tested how the skills
*realize* them but not whether the skills *choose* them. A harder run omits the constructs
(and escalates to active components, subassemblies, algorithm wrapping) to push
construct-choice and surface more gaps. **An all-HIT N=1 run is not "done" -- push harder.**
