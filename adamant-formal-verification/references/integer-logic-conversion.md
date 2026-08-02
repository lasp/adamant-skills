# Converting Existing Integer Logic to a Proved Logic Package

How to take arithmetic that already works, runs in a component body, and defends itself with
`pragma Assert`, and turn it into a SPARK logic package whose properties are proved once at
build time. Written from conversions actually performed; every rule below either discharged a
proof or caught a defect.

## Why this conversion is worth doing

Runtime asserts on a flight target are a crash path: a violated assert reaches the last chance
handler and takes the system down, in flight, at the worst moment. The same property proved
statically costs nothing at runtime and cannot be violated. So the highest-value conversion
candidates are not the most complex algorithms, they are the ones already carrying asserts.

**Find candidates by grepping for the asserts.** Any body with `pragma Assert` over integer
quantities is a package that has already told you what its invariants are; the author wrote
the postcondition and put it in the wrong place.

Integer logic is also the tractable case. Obligations over bounded integers lower to linear
integer arithmetic, which is decidable, so these proofs usually discharge automatically at
`silver`/level 2 with no manual proof engineering. Contrast float, which is proof-hostile (see
the main skill, Logic Package Conventions item 8).

## The extraction boundary

Draw the line so the logic package imports nothing from the framework:

| Stays in the component body | Moves to the logic package |
|---|---|
| Register-aligned generated types (`*_Register.T_Le`) | Plain `Interfaces` types and subtypes of them |
| Address overlays, `Import`/`Convention` aspects | Pure value computation |
| `Self`, component state, counters | Inputs passed by value |
| Framework calls, connectors, events | Nothing |
| Conversions between the two worlds | Nothing |

The left column is not a SPARK limitation. Adamant's generated packed-record packages are
SPARK-analyzable -- `admt prove` on a component directory analyzes the autocoded child units
(`component-<name>.ads`, the `*-representation` packages) as a matter of course, and the
framework generates memory/register-map packages with `SPARK_Mode => On` precisely so they are
checked. Register types stay in the component body for proof *shape*, not legality: their
fields are narrow modular types whose wrap semantics complicate the obligations (next
section), and the overlay/`Import` machinery around them is what is genuinely outside SPARK.

The component body then reads as: convert in, call the proved function, convert out. If the
conversion at the boundary is the only remaining arithmetic, the extraction is complete.

**Do not `with` a generated register-type package from a logic package**, even for a numeric
subtype it happens to declare. Redeclare the bound locally as a named number with a comment
naming the field width, and take the widened type as the parameter. This keeps the logic
package framework-free (Logic Package Conventions item 7) and, more importantly, makes the
width an explicit stated assumption rather than an inherited one.

```ada
-- In the logic package: the field width is a documented constant, not an import.
Max_Ramp_Step_Count : constant := 4095;   -- 2**12 - 1: the register field width
subtype Ramp_Step_Count is Unsigned_16 range 0 .. Max_Ramp_Step_Count;
```

## Modular types change what you must prove

Generated register types are almost always **modular** (`type Unsigned_N is mod 2**N`). This
has three consequences that catch people converting from Ada to SPARK:

**1. There are no overflow checks to prove.** Modular `+`, `-`, and `*` wrap by definition, so
the prover raises no overflow obligation. Absence of overflow findings does not mean the
arithmetic is safe; it means the language declined to ask. The real obligations are **range
checks on conversions and subtype assignments**, plus whatever your postconditions state.
Wraparound bugs are invisible unless a postcondition forbids them.

**2. Guard idioms borrowed from signed arithmetic are dead code.** This is a no-op:

```ada
-- WRONG on a modular type: the subtraction has already wrapped to a huge value,
-- so 'Max returns that value unchanged and defends nothing.
Steady := Unsigned_16'Max (Total - (Up + Down), 0);
```

The correct move is to prove the property the guard was pretending to enforce:

```ada
-- Postcondition on the function makes the underflow impossible instead of unchecked.
Post => ... Result.Up + Result.Down <= Total ...
```

Then the plain subtraction is safe, and provably so. When you find such a guard during a
conversion, treat it as a signal that the author knew a property was needed and had no way to
state it.

**3. Widen before combining, or the intermediate wraps.** Two `Unsigned_12` values added
together are added *in* `Unsigned_12`, wrapping at 4096, even when the result is immediately
converted to a wider type. The conversion happens after the damage:

```ada
-- WRONG: the addition is Unsigned_12 arithmetic; it wraps before the widening.
Capacity : constant Unsigned_16 := Unsigned_16 (Limit_A + Limit_B);

-- RIGHT: widen each operand first, then add in the wider type.
Capacity : constant Unsigned_16 := Unsigned_16 (Limit_A) + Unsigned_16 (Limit_B);
```

This exact pattern was a live defect in converted flight code: two 12-bit configured limits
summing past 4096 wrapped to a small capacity, which inverted a downstream branch and produced
a grossly over-commanded output. **Audit every `Wider (A + B)` you meet during a conversion**;
the correct form is `Wider (A) + Wider (B)`.

## Asserts that validate themselves

A runtime assert written in the same wrapped domain as the bug cannot detect the bug. In the
defect above the conservation check was:

```ada
pragma Assert (Total = Unsigned_16 (Up + Down) + Steady);
```

`Up + Down` wraps in the narrow type exactly as the capacity computation did, and `Steady` was
derived from the same wrapped quantity, so both sides agreed and the assert passed on inputs
that produced badly wrong output. The proved postcondition catches it because the prover
reasons about the mathematical values, not the wrapped expressions the code happens to write.

**Rule: when converting an assert into a postcondition, do not transcribe the expression.
Restate the property.** Ask what the assert was trying to guarantee, then write that.

## Clamp in the wider type, narrow afterwards

Ordering the clamp and the narrowing changes the proof obligation from conditional to trivial.

```ada
-- Narrow-then-clamp: the conversion can fail, so the obligation is conditional on
-- whatever guarantees the input is small, and needs an assert to document it.
if Split_Possible then
   Result := Unsigned_12'Min (Unsigned_12 (Half + Extra), Limit);
```

```ada
-- Clamp-then-narrow: the result is bounded by Limit, which is already in range,
-- so the subtype assignment proves unconditionally and the assert disappears.
Result : constant Ramp_Step_Count :=
   (if Split_Possible then Unsigned_16'Min (Half + Extra, Limit) else Limit);
```

Generalized: **perform min/max in the widest type in play, and let a subtype constraint do the
narrowing.** The prover then discharges the range check from the clamp alone.

## Writing the postconditions

State properties, in roughly this order of value:

1. **Conservation** -- outputs account for the input exactly (`Total = A + B + C`). This is
   usually the property the original asserts were reaching for, and the one that catches
   wraparound.
2. **Bound respect** -- each output stays within its configured or field limit. This is what
   makes the downstream narrowing safe.
3. **The enabling lemma** -- any intermediate inequality the safety of the body depends on
   (`A + B <= Total` so a subtraction cannot underflow). Stating it in the postcondition both
   proves it and documents why the body is correct.
4. **Specified saturation** -- the behavior past the limit, as a conditional clause. See the
   clamping carve-out in the main skill: a specified clamp is modelled, not removed.

```ada
Post =>
   Result.A <= A_Limit
   and then Result.B <= B_Limit
   and then Result.A + Result.B <= Total
   and then Total = Result.A + Result.B + Result.Remainder
   and then (if Total > A_Limit + B_Limit then
                Result.A = A_Limit and then Result.B = B_Limit);
```

Avoid postconditions that merely restate the implementation (`Result.A = Min (X, Limit)`).
They prove trivially and assert nothing a reader could not read off the body. A good
postcondition is one you would have written as a requirement.

## Verify on more than one front

Proof establishes that the implementation cannot fail and that it satisfies what you stated.
It does not establish that you stated the right thing, and it says nothing about the code that
used to be there. Run all of these:

1. **`gnatprove` clean**, summary read (not just exit status), 0 unproved, 0 assumes.
2. **Existing unit tests pass** -- the behavioral regression net.
3. **A differential sweep old-vs-new** -- model both the original expression and the new
   function, exhaustively over the input range where feasible, and diff. This is what proves a
   conversion is behavior-preserving, and it is the only front that will tell you *where* the
   old code was wrong. Report the divergence set and its cause, never just a count.
4. **Style clean** on the touched directories.

If the sweep shows divergence, do not assume the new code is at fault and do not silently
adopt the old behavior. Characterize the divergent inputs, decide which behavior is correct,
and record the decision. A conversion that fixes a defect is a better outcome than one that
preserves it, but only if the change is stated loudly rather than buried in a refactor.

## Checklist

1. Grep the target body for `pragma Assert` over integer quantities; those are your candidates.
2. Draw the extraction boundary: framework types out, plain values in.
3. Redeclare field widths as named numbers with a comment; never import a generated type.
4. Audit every `Wider (A + B)` for a narrow-domain wrap; rewrite as `Wider (A) + Wider (B)`.
5. Delete guards that cannot work on modular types; replace with a proved postcondition.
6. Reorder clamps ahead of narrowing.
7. Write postconditions as properties (conservation, bounds, enabling lemma, saturation).
8. Prove at silver/level 2; read the summary.
9. Rewire the caller so it only converts, builds, tests, and styles clean.
10. Run the differential sweep and account for every divergence.
