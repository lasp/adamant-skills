---
name: high-assurance-design
description: Engineering discipline for high-assurance system design. Use when designing new systems, reviewing architecture, writing specifications, scoping projects, defining invariants and non-goals, planning multi-language interop, structuring formal verification, or advising on project organization. Applies to any project where correctness, scope discipline, and architectural clarity matter.
---

# High-Assurance Design

Engineering principles for building systems with provable correctness, minimal scope, and clean architecture. Derived from practice building formally verified multi-language systems.

## Core Discipline

### Invariants First

Define invariants before writing code. Invariants are not guidelines -- violations are bugs.

1. State what must always be true
2. Design outward from invariants
3. Enforce invariants through types, contracts, or tests
4. Document invariants where they are checked, not where they are assumed

### Non-Goals Are Load-Bearing

Document what the system will NOT do. Non-goals prevent scope creep and communicate intent.

1. Write non-goals before goals
2. Non-goals are enforced, not aspirational -- reject work that conflicts with them
3. Review non-goals when requirements change; do not silently expand scope

### Scope as a Feature

Constraint is the feature, not the limitation.

1. Define scope honestly: what ships and what does not, decided before work begins
2. Resist expansion once work feels productive
3. A finished system with clear boundaries beats an ambitious prototype that never ships
4. Every excluded feature should be documented, not forgotten

## Architecture Patterns

### Integrity Allocation

Assign integrity levels to components based on their security/correctness impact.

```
High integrity:   Security-critical logic, validation, crypto
                  -> Formal verification, proven contracts
Supporting:       IO, composition, networking, storage
                  -> Property tests, conservative dependencies
```

Each language/tool does what it does best. Do not force one tool to do everything.

### Thin Interop

Multi-language boundaries must be minimal and frozen.

1. Export the fewest possible functions across the boundary
2. Use simple types at the boundary (C strings, integers, explicit lengths)
3. Version the interface with a constant; freeze test enforces no signature changes across releases
4. All memory is caller-allocated; no hidden allocations across the boundary
5. Document what is verified and what is not at the boundary

### Split by Trust Profile

Separate components by their exposure to untrusted input.

- Public-facing components carry minimal dependencies
- Write-path components (validation, creation) are separate from read-path (lookup, redirect)
- The component exposed to untrusted traffic should have the smallest trusted computing base

## Formal Verification Strategy

### Contract-First Development

Write contracts (preconditions, postconditions) before implementation.

- If you cannot state the postcondition, you do not understand the function
- Contracts define trust boundaries: downstream consumers rely on proven guarantees
- Preconditions on types enforce call ordering (e.g., Valid_URL can only come from successful validation)

### Confine Assumptions

When assumptions are unavoidable:

1. Isolate them in ghost/proof code, not business logic
2. Document the mathematical justification
3. Keep them in a single auditable location
4. Minimize count; each assumption is a proof debt

### Proof Architecture

See [references/proof-patterns.md](references/proof-patterns.md) for the ghost lemma pattern, shared predicates, and expression function strategies.

## Project Organization

### Build and Test

- Dependency-based build systems (redo, make) over script collections
- Property tests over unit tests: generators find edge cases humans miss
  - Write generators for each input class: valid inputs, boundary inputs, explicitly-invalid inputs
  - Test rejection as rigorously as acceptance (private IPs, credentials, malformed schemes each get their own generator)
  - Idempotency and round-trip properties are high-value: `canonicalize(canonicalize(x)) == canonicalize(x)`
  - Determinism properties: same input + same key = same output, always
- Single-threaded execution for FFI calls unless thread safety is proven
- Freeze tests for API stability: compile-time or test-time check that exported function signatures have not changed

### Documentation

- README: what it is, how to use it, security model, threat model, assurance model
- Non-goals in README, not buried in issues
- Whitepapers for design philosophy (separate from API docs)
- Proper third-party license attribution

### Sprint Discipline

For time-bounded projects:

1. Define the problem in one sentence
2. Write non-goals before goals
3. Set a hard deadline; do not move it
4. Phase the work (prototype -> extraction -> hardening)
5. Ship something real, even if small
