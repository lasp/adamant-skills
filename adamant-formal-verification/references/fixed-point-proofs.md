# Fixed-Point Proofs

Fixed-point types are scaled integers, so their proof obligations lower to linear integer
arithmetic: decidable, and exactly what GNATprove discharges automatically. For DSP, sensor,
control, and hardware-modelling code, "use fixed-point instead of float" is often the single
highest-leverage proof decision available. The main skill (Logic Package Conventions item 8)
explains the other half: float is proof-hostile, because the prover cannot verify float
saturation guards even when they are mathematically sound. This reference is the tractable
alternative it points toward.

Every mechanical claim below was verified against GNATprove (silver, level 2) on a small
worked package; the proof summary is in the last section. The worked example models a
fixed-point geometry coprocessor of the kind documented for 1990s consumer hardware, whose
numeric formats are public and exact.

## Why fixed-point proves well

An ordinary fixed-point value is an integer times a fixed scale (`'Small`). Arithmetic on it
is integer arithmetic, so:

- overflow and range obligations are linear integer facts the SMT solvers close in a few steps;
- there is no "not monotone in its model" problem as with float, so saturation guards and
  order comparisons prove;
- an error bound on a computation is derivable exactly from the formats, not tuned as an
  epsilon. A product of a `p.q` and an `r.s` value truncated back to `q` fractional bits has a
  worst-case error of one `'Small`, statable and provable rather than estimated.

Prefer fixed-point when you control the type choice and the dynamic range is bounded. Cross-link
`integer-logic-conversion.md` (the same widen-before-combining discipline applies) and the
vendor `gnatprove` skill's floating-point reference (the contrast case).

## Declare a type that means what the hardware means

Use ordinary fixed-point with an *explicit* `Small` (a power of two for a binary register
format) rather than relying on the implementation-chosen default, and pin `Size` to the
register width. A 16-bit `1.3.12` format (1 sign bit, 3 integer bits, 12 fractional bits) is:

```ada
   Frac_Bits : constant := 12;
   type Q3_12 is delta 2.0 ** (-Frac_Bits) range -8.0 .. 8.0 - 2.0 ** (-Frac_Bits)
      with Small => 2.0 ** (-Frac_Bits), Size => 16;
```

The `range` states the integer-bit budget (`2**3 = 8`), the `delta`/`Small` state the
fractional resolution, and `Size` forces the 16-bit representation. The same shape maps every
documented format directly: a `1.19.12` colour value is `range -2**19 .. 2**19 - 2.0**(-12)`
with the same `Small`; a `1.31.0` translation value is an integer format (`delta 1.0`); a
`1.27.4` value uses `Small => 2.0**(-4)`. One type per documented format, named for it.

Declaring `Small` explicitly is not cosmetic: it makes the wire meaning of the stored bits a
checked property of the type, so a value read from or written to the register is correct by
construction rather than by a scaling comment.

## The universal_fixed multiply/divide conversion

Fixed-point `*` and `/` yield the anonymous type `universal_fixed`, which has no operations of
its own and must be converted to a named fixed type at the use site:

```ada
   Product : constant Wide_Q := Wide_Q (X) * Wide_Q (C);   -- required conversion
   -- Product := X * C;   -- illegal: universal_fixed is not Wide_Q
```

The conversion noise is correct, not a smell: it is the point at which you choose the result
type, and therefore the point at which the prover gets a target range to check the product
against. Multiply-heavy fixed-point code is a sequence of these deliberate conversions.

## Division floors on the device, truncates in Ada

A device that shifts right to divide is doing **floor** division. Ada's `/` truncates **toward
zero**. They disagree for every negative value that is not an exact multiple of the divisor, and
the disagreement is silent because both are "a division":

```
   -1 / 16     =  0    -- Ada: truncate toward zero
   -1 >> 4     = -1    -- device: arithmetic shift right = floor
```

The harm escalates with where the result lands. A projected coordinate divided with `/` sits one
unit off the hardware, on one side of centre only, invisible in review. Inside an operation family
the same displacement hits every negative operand. Worst is when the result feeds a
**clamp-and-flag**: an intensity of `-1` floors to `-1`, which clamps to zero *and sets the
saturation flag*, where Ada's `/` yields `0` and reports no clamp. Same stored value, different
flag word, and a differential test against a reference that does not model flags cannot see it.
Corollary worth stating in any device model: **status bits are outputs; a reference that omits
them cannot defend them.**

The fix is not "use floor division everywhere" but **test the sign before dividing**, so the model
depends on no language's rounding direction:

```ada
   --  Sign first: the device floors, so every negative intensity clamps and flags,
   --  including the ones an Ada division would round up to zero.
   if V < 0 then
      return Colour_Result'(Value => 0, Saturated => True);
   end if;
   --  The remaining division sees only non-negative operands, where floor and
   --  truncation agree and the question cannot arise.
```

Where a negative range genuinely flows through with no clamp, write floor explicitly and prove its
*defining property* rather than restating the shift:

```ada
   function Floor_Shift (V : Numer_Value) return Long_Long_Integer is
     (if V >= 0 then V / Divisor else -((-V + Divisor - 1) / Divisor))
   with Post => Floor_Shift'Result * Divisor <= V
               and then V < (Floor_Shift'Result + 1) * Divisor;
```

The bracketing postcondition holds whatever expression computes the result, and downstream
monotonicity and exactness lemmas lean on it rather than on the shift. The same toward-zero-versus-
floor split applies to plain integer shifts; the vendor gnatprove skill's overflow-pattern
reference is the companion.

## Bound products before summing, in the body AND the contract

A product needs more integer bits than its operands: a `1.3.12` times a `1.3.12` can reach
almost `8 * 8 = 64`, which needs 6 integer bits, not 3. Declare a wider fixed type with the
product's range and widen the operands *before* multiplying, so the multiply cannot overflow:

```ada
   type Wide_Q is delta 2.0 ** (-Frac_Bits) range -64.0 .. 64.0
      with Small => 2.0 ** (-Frac_Bits);
   ...
   Product : constant Wide_Q := Wide_Q (X) * Wide_Q (C);
```

This is the fixed-point form of the `Wider (A) * Wider (B)` rule from
`integer-logic-conversion.md`: widen the operands, never narrow the result of a narrow product.

The companion for accumulation: **bound the accumulator from the format parameters and require
it to fit the device's register.** Derive the bound (`Operands * Operand_Max**2` for a dot
product of `Operand_Max`-bounded terms) and, when both sides are static, pin it with a
`Compile_Time_Error` so a later format correction moves the bound and fails the build rather than
silently widening a proof obligation. See the compile-time-first ladder in `proof-mechanics.md`.

**The same widening is required in the contract, and this bites.** A postcondition that names
the raw product raises an overflow obligation the prover cannot discharge:

```ada
   -- medium: overflow check might fail, cannot prove lower bound for X * C
   Post => Result.Saturated = (X * C > Q3_12'Last or else X * C < Q3_12'First);
```

The fix is to widen in the contract exactly as in the body, which means **the wide type must be
declared in the spec** so the postcondition can name it:

```ada
   Post =>
      Result.Saturated =
         (Wide_Q (X) * Wide_Q (C) > Wide_Q (Q3_12'Last)
          or else Wide_Q (X) * Wide_Q (C) < Wide_Q (Q3_12'First));
```

A private intermediate type is a common instinct; here it forces the wide type into the visible
part. That is the right call: the intermediate width is part of the operation's specified
numeric behaviour, not a hidden implementation detail.

## Saturation with a flag

Hardware that saturates at a documented bound *and records the event in a status flag* is a
distinct pattern from "avoid overflow": the saturating result is the specified behaviour, and
the flag is part of the postcondition. This is the fixed-point instance of the specified-
saturation carve-out in the main skill; state it as a proved multi-branch postcondition rather
than removing the clamp:

```ada
   type Saturating_Result is record
      Value     : Q3_12   := 0.0;
      Saturated : Boolean := False;
   end record;

   function Scale_Saturating (X : Q3_12; C : Q3_12) return Saturating_Result
      with Global => null,
           Post =>
              Scale_Saturating'Result.Saturated =
                 (Wide_Q (X) * Wide_Q (C) > Wide_Q (Q3_12'Last)
                  or else Wide_Q (X) * Wide_Q (C) < Wide_Q (Q3_12'First))
              and then (if not Scale_Saturating'Result.Saturated then
                           Wide_Q (Scale_Saturating'Result.Value) = Wide_Q (X) * Wide_Q (C));
```

The body clamps to `Q3_12'Last`/`Q3_12'First` and sets the flag; the prover discharges both the
flag equivalence and the exact-value case. Compare with the integer three-branch signed
saturation in `contract-patterns.md`: same shape, scaled type.

## A composed status word: state it as an expression function

The pattern above returns one flag beside a value. An operation whose result includes a **word
composed from several flags** needs one more step, or a caller cannot reason about the word.
Leaving the word to the body -- pinning the value outputs and proving each flag's cause separately
-- is true and provable, and forecloses nothing until a caller needs a property *of the word* ("in
this domain the word is zero") and has no contract to prove it from.

State the word as an **expression function** and pin it by equality:

```ada
   function Flag_Word_Of (...) return Flag_Word is
     ((if Cause_1 then Bit (Flag_Bit (1)) else 0)
      or (if Cause_2 then Bit (Flag_Bit (2)) else 0)
      or ...);

   function Operation (...) return Op_Result
      with Post => ... and then Operation'Result.Flags = Flag_Word_Of (...);
```

Three consequences, observed rather than predicted:

* The operation's own postcondition is trivial to discharge: the body returns the same expression
  the contract names.
* Word-level properties become *evaluable*. "The whole flag word is zero in this domain" is a lemma
  proved by showing each cause false and letting the expression fold to zero. The per-bit
  alternative -- quantified `Is_Set` biconditionals over an OR-fold -- pushes provers into bitvector
  reasoning for every consumer.
* The flag word joins the value outputs as *specified* rather than incidental, which is what a
  device model owes its callers: the equivalence rule from the main skill (state `P = Q` when a
  caller will branch on it), applied to a whole word at once.

## Device operations: the contract carries what the name does not

Two modelling hazards recur when a fixed-point device's operations are parameterised, and both
are invisible to the type checker because a wrong scale or a wrong operand still produces a
value of the right type:

- **Per-operation scale selectors belong in the contract, not a global constant.** If most
  operations apply a `>>N` shift but one does not, a package-level scale constant models the
  exception wrong and nothing catches it. Make the scale a parameter (or discriminant) and let
  the postcondition mention it: `Post => Result = Product / Scale`. A wrong scale is then a
  proof failure.
- **Selector-parameterised operations must be modelled as a family.** If one instruction
  encoding selects among several matrices/vectors via selector fields, model it with the
  selector as a parameter and state the postcondition over the selected operand. Modelling the
  common case and treating the rest as variants invites a provable-but-wrong specification.

Both reduce to the same rule: an operation's identity is not fully given by its name; whatever
the encoding also chooses (scale, rounding, operand) must appear in the contract.

## When not to use fixed-point

Fixed-point is the wrong tool for genuinely wide dynamic range (many orders of magnitude in one
quantity), transcendental functions, and interop with a float-typed external API. In those
cases keep the float math outside SPARK per the main skill, or accept the float proof
limitations knowingly. Fixed-point earns its place where the range is bounded and known, which
is most register-level and control arithmetic.

## What the worked package proved

GNATprove silver, level 2, `--checks-as-errors=on`, on the `Scale_Saturating` package above:
every run-time check proved (the widened product's overflow and range checks, the narrowing
range check on the clamped result), the `Global => null` flow verified, and the two-clause
saturation postcondition proved, with 0 unproved and 0 `pragma Assume`. The only obligation
that did not discharge on the first attempt was the contract's raw `X * C`, which is the
widen-in-the-contract lesson above; widening it closed the proof.
