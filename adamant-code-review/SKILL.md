---
name: adamant-code-review
description: Review Adamant components, tests, types, and assemblies for correctness, quality, and adherence to framework patterns. Use for PR reviews, post-generation audits, and design assessments.
---

# Adamant Code Review

Structured review of Adamant artifacts -- components, tests, types, assemblies. Produces actionable findings categorized by severity. Works on any Adamant code: hand-written, AI-generated, or mixed. Use for PR reviews, design assessments, pre-merge quality gates, or post-build audits.

## Review Scope

A review covers one or more of these artifact types:

| Artifact | Key files | What to check |
|----------|-----------|---------------|
| Component | `.component.yaml`, `-implementation.ads/.adb` | YAML model correctness, connector usage, state management, error handling |
| Tests | `*_tests-implementation.adb`, `tester.ads/.adb` | Assertion quality, coverage, test isolation, stimulus correctness |
| Types | `*.record.yaml`, `*.enums.yaml`, `*.array.yaml` | Field sizing, alignment, naming, packed type constraints |
| Assembly | `*.assembly.yaml`, `main.adb` | Wiring correctness, infrastructure completeness, ID conflicts, fault responses |

## Finding Severity

| Level | Meaning | Examples |
|-------|---------|---------|
| **error** | Will not compile, or produces incorrect runtime behavior | Missing connector, wrong type on send, uninitialized state |
| **warning** | Compiles but violates framework patterns or has latent risk | Shallow assertions, missing error path tests, oversized types |
| **info** | Style or design preference, not a defect | Naming choices, alternative decomposition, unused features |

## Component Review Checklist

### YAML Model
- [ ] `execution` matches design intent (active vs passive)
- [ ] All connectors have correct `kind` (recv_sync, recv_async, send, get, provide, request)
- [ ] Arrayed connectors have correct `count` and are 1-indexed
- [ ] `recv_async` connectors specify `priority` when multiple exist (active components)
- [ ] Commands use `arg_type` (not `type`) and avoid Ada reserved words
- [ ] Events have appropriate parameters (not just bare notifications)
- [ ] Faults carry diagnostic information (source index, error code)
- [ ] Data products use appropriately sized types (not oversized for the data)
- [ ] `with` section includes all packages used in implementation that aren't auto-generated

### Implementation
- [ ] All `recv_async` / `recv_sync` handlers implemented
- [ ] `Cycle` override present if component has tick input (active with periodic behavior)
- [ ] `Parameter_Update_T_Modify` overridden when parameters.yaml exists
- [ ] State initialized in component body or via Init procedure
- [ ] No unprotected shared state in active components (all state accessed through message handlers)
- [ ] Error conditions raise faults or fire events (not silently ignored)
- [ ] `Command_Response` sent for every command path (success and failure)
- [ ] Named connectors use correct generated accessor names
- [ ] No use of Ada.Text_IO or other forbidden packages in flight code

### Ada Quality
- [ ] State type is a record, not loose variables in the body
- [ ] Enums used for state machines (not magic integers)
- [ ] Loop bounds are compile-time deterministic or bounded by type range
- [ ] No dynamic allocation (Ravenscar compliance)
- [ ] Subtypes used to constrain ranges where appropriate
- [ ] Pure logic separated from connector dispatch where feasible (SPARK candidate)

### Active Component Patterns
- [ ] `recv_async` connectors have explicit `priority` when multiple exist (higher = dequeued first)
- [ ] Tick input is `recv_async` for active components (not `recv_sync` -- sync runs in caller's task, not component's). Exception: tick that ONLY publishes data products is acceptable as recv_sync (lightweight, no queuing needed)
- [ ] `init_base` queue depth matches expected load (sum of all async connector depths)
- [ ] Priority ordering is intentional (e.g., tick > data, or data > tick depending on design)
- [ ] No blocking operations in async handlers (would block the component's task)

### Common Naming Issues
- [ ] `Abort` is an Ada reserved word -- use `Abort_Sequence`, `Cancel`, or `Seq_Abort`
- [ ] Fault names in fault_responses.yaml match component YAML exactly (not `_Fault` suffix if not declared)
- [ ] Named connector accessor: `{Name}_T_Send` for typed, just `{Name}` for named connectors (check generated API)
- [ ] Command arg type field is `arg_type` not `type`

## Test Review Checklist

### Structure
- [ ] Test directory has `env.py` (NOT `.all_path`)
- [ ] `tests.yaml` lists all test procedures
- [ ] `test.adb` and tester files copied from `build/template/` (not hand-written from scratch)
- [ ] Tester `.ads/.adb` properly override service connectors (e.g., `Sys_Time_T_Return`)

### Assertion Quality
- [ ] Assertions check specific output VALUES, not just call counts
- [ ] Each test has >= 3 assertions (meaningful, not padding)
- [ ] Packed type fields compared directly (not via `.Value` accessor on history items)
- [ ] History indices are correct (typed histories accumulate across tests unless cleared)
- [ ] Event parameters verified (not just event count)
- [ ] Command response status verified (Success vs Failure)
- [ ] Fault parameters verified (source index, error code)
- [ ] Data product values verified against expected computation

### Coverage
- [ ] Normal / happy path tested
- [ ] Error / rejection path tested (invalid commands, bad input)
- [ ] Boundary conditions tested (empty input, max capacity, zero values)
- [ ] State transitions tested (for state machine components)
- [ ] Parameter update tested (if component has parameters)
- [ ] Each fault condition has a dedicated test or test section

### Test Isolation
- [ ] Each test starts from known initial state
- [ ] History counts account for accumulation from prior tests (or histories cleared)
- [ ] No test depends on side effects from a previous test

## Type Review Checklist

- [ ] Record total size is byte-aligned (no padding surprises)
- [ ] Field sizes match the data range (U8 for 0-255, not U32)
- [ ] Enum literals don't collide with Ada reserved words or type names
- [ ] Array element count matches design (not off-by-one)
- [ ] Variable-length records have `Buffer_Length` in header if needed
- [ ] Packed type fits within data product buffer size (project config)

## Assembly Review Checklist

- [ ] All component connectors are wired or explicitly documented as unconnected
- [ ] `Command_T_Send_Count` matches actual number of command targets
- [ ] Rate group tick type matches component's declared recv kind (sync vs async)
- [ ] Fault response names match exactly what the component YAML declares
- [ ] Parameter table entries reference correct component instance and parameter names
- [ ] ID bases don't overlap across subassemblies
- [ ] Subassembly used for application components (if task requires it)
- [ ] `init_base` queue depth specified for active components
- [ ] `init` parameters match component's Init procedure signature
- [ ] Linux target specified (or correct target for the project)
- [ ] Main procedure uses correct assembly package name

### Common Assembly Mistakes
- [ ] Subassembly used when design requires it (flattening to avoid event_to_text style warnings is not a valid reason -- the ELF is unaffected)
- [ ] Parameter_Store included when any component has parameters (requires companion Parameters component)
- [ ] Prior-phase artifacts (types, components) not modified during assembly wiring
- [ ] No unrelated files deleted or renamed
- [ ] Fault response commands reference valid command names on the target instance (e.g., `Noop` on Command_Router)
- [ ] `Queue_Size` vs `Priority_Queue_Depth` -- use `Priority_Queue_Depth` when component has multiple recv_async with different priorities

## Multi-Component Interaction Checklist

When reviewing systems with 2+ custom components that interact:

### Connector Consistency
- [ ] Service/request connector pairs use the same type on both sides
- [ ] Connector names match exactly between provider and requester YAML
- [ ] Shared types are in a common types directory (not duplicated per component)
- [ ] Request connectors have corresponding service connectors (not dangling)

### Cross-Component Data Flow
- [ ] Data passed between components is correctly typed (no implicit conversions)
- [ ] Timestamp fields use consistent units across all components (seconds vs milliseconds)
- [ ] Default/initial values are consistent (e.g., calibration store defaults match what consumers expect)
- [ ] Error propagation: what happens if a service request returns stale/invalid data?

### Assembly Wiring
- [ ] All service/request pairs actually connected in assembly YAML
- [ ] Connection direction correct: `from_component` is the requester, `to_component` is the provider
- [ ] No circular dependencies (A requests from B which requests from A)
- [ ] Multiple requesters to one provider: verify the provider is reentrant or protected

### Test Coverage for Interactions
- [ ] Each component tested in isolation with mock service responses
- [ ] Tester overrides `*_T_Service` return to provide controlled test data
- [ ] Fetch_Status verified (Success vs error conditions)
- [ ] Edge cases: what if service returns default/zero values? Stale timestamps?

## Scope Compliance Checklist (Multi-Phase Pipelines)

When reviewing artifacts built in a phased pipeline (e.g., Phase A = component, Phase B = assembly):

- [ ] No files modified outside the current phase's directories
- [ ] No framework code modified (gen/, adamant/ repo)
- [ ] Prior-phase artifacts untouched (read-only dirs respected)
- [ ] No git operations performed (commit, push, branch)
- [ ] Workarounds use documented approaches (e.g., YAML `with:` field), not patches to framework internals
- [ ] Assembly phase reads component YAML to discover connectors (doesn't invent connector names)

## Review Output Format

```
## Review: {component_or_assembly_name}

### Errors
- [{file}:{line}] {description}

### Warnings
- [{file}] {description}

### Info
- {observation}

### Summary
- Errors: N
- Warnings: N
- Info: N
- Verdict: PASS | PASS_WITH_WARNINGS | FAIL
```

**PASS**: No errors, warnings are acceptable (e.g., known framework limitations).
**PASS_WITH_WARNINGS**: No errors, but warnings indicate quality gaps worth addressing.
**FAIL**: Errors present -- code will not compile correctly or has runtime defects.

## Design Review (Optional)

For higher-level assessment beyond checklist items:

- **Decomposition**: Is the component doing too much? Should it be split?
- **Connector topology**: Are the right connector kinds used? Could request/provide replace polling?
- **Type efficiency**: Are packed types sized appropriately for the wire format?
- **Testability**: Is the design easy to test, or does tight coupling make testing difficult?
- **SPARK candidacy**: Which logic is pure enough for formal verification?
- **Framework alignment**: Does the design follow Adamant conventions, or fight them?

## Using This Skill

### PR review
Read the diff, identify which artifact types changed, run the relevant checklists.
Note what the diff changes and whether it introduces new issues or resolves existing ones.

### Post-build audit (CI, agent output, or manual build)
Read the built artifacts, run through the relevant checklists, produce findings.
Focus on errors and warnings. Info-level findings are optional.

### Design assessment
Read component YAML and implementation. Run the design review section.
Produce recommendations, not just findings.

### Self-review before commit
Run the relevant checklists against your own changes before committing.
Catch naming issues, missing tests, and wiring mistakes before they reach review.
