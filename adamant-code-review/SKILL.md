---
name: adamant-code-review
description: Review Adamant components, tests, types, and assemblies for correctness, quality, and adherence to framework patterns. Use for PR reviews, post-generation audits, and design assessments.
---

# Adamant Code Review

Structured review of Adamant artifacts -- components, tests, types, assemblies. Produces actionable findings categorized by severity. Works on both generated (cold-start agent) and hand-written code.

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

### Post-generation audit (campaign or CI)
Read the generated artifacts, run through the relevant checklists, produce findings.
Focus on errors and warnings. Info-level findings are optional.

### PR review
Read the diff, identify which artifact types changed, run the relevant checklists.
Note what the diff changes and whether it introduces new issues or resolves existing ones.

### Design assessment
Read component YAML and implementation. Run the design review section.
Produce recommendations, not just findings.
