---
name: adamant-spark-logic-packages
description: Extract provable logic from Adamant components into small SPARK packages beside the implementation, with the silver-by-default proof posture and the idioms that recur in review. Use when adding SPARK to a component, choosing a proof level, or reworking a SPARK extraction after review feedback.
---

# SPARK Logic Packages

Component implementations stay outside SPARK; provable logic is factored into small
sibling packages beside the component implementation and proved there. The component body
calls into them. This skill covers the extraction shape, the proof posture, and the idioms
that review feedback keeps producing. `adamant-formal-verification` covers the contract
mechanics, ghost code, and proof debugging; read it for how to prove, this for what shape
to prove and at what level.

## Package shape

- One package per concern, named for the component and the concern
  (`<component>_<topic>.ads`), living in the component directory so `admt prove` picks it
  up with the component's `all.prove.yaml`.
- `SPARK_Mode => On` on the spec (and body, when one exists), and `Global => null` on every
  function; expression functions then prove with no further contracts. Add `Pure` only when
  the package withs nothing generated: a Pure unit cannot depend on a non-Pure unit, and the
  generated packed-record and register packages are not Pure, so a package that uses their
  types or constants cannot be.
- Memory overlays, address imports, connector calls, and other non-SPARK mechanics stay in
  the component implementation, or in a subprogram body marked `SPARK_Mode => Off` that
  delegates to a proved function.

## Proof posture: silver by default

The framework default when `all.prove.yaml` omits `mode` is gold, so state the posture
explicitly:

```yaml
---
description: GNATprove configuration for the <component> proved logic packages
level: 2
mode: "silver"
```

- Silver (absence of runtime errors) is the default and is normally enough. Escalating to
  gold is reserved for a critical property that must be functionally proved, needs a very
  good reason, and is a decision to raise with the project owner before making it. Record
  the reason with the change.
- Read the summary, not the exit status: the Unproved column must be zero and the
  `pragma Assume` count must be zero. Never introduce a `pragma Assume` without explicit
  approval (see `adamant-formal-verification`, the assume gate).

## Idioms that recur in review

- **Derive constants from the generated type packages.** Generated packed-record constants
  and types are directly usable from SPARK: write
  `Num_Words : constant := <Record>.Size_In_Bytes / 4;` rather than pinning a magic number
  and guarding it with a compile-time coverage check. Such a package cannot be `Pure`, as
  the package shape above states.
- **Do not restate an expression function in its postcondition.** The prover inlines the
  body; a `Post` that repeats it adds nothing and costs review attention.
- **When the only caller is outside SPARK, a precondition is just a runtime check.**
  Prefer a plain assertion at the call site when that communicates the intent better; keep
  contracts for what the proof itself needs.
- **Generated functions with `out` parameters carry `Side_Effects`** (`Valid`,
  `Serialized_Length`, the serializer entry points) as of adamant #217, so SPARK code can
  call them. On a framework pin older than that change, keep such calls outside the SPARK
  package; generated constants and types work on any pin.
- **Prefer an inline constant aggregate over a helper function** when a value is built
  once at its use site.

## Checklist

1. Factor the provable logic into a sibling package; leave overlays and connectors behind.
2. `SPARK_Mode => On`, `Global => null` on every function, and `Pure` only when the package
   withs nothing generated. Expression functions where possible.
3. `all.prove.yaml` with `mode: "silver"`, `level: 2`, stated explicitly.
4. `admt prove` from the component directory: zero unproved, zero assumes.
5. Sweep the idioms above before requesting review.
6. Escalating past silver: raise it first, record the reason with the change.
