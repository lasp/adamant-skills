---
name: adamant-formal-verification
description: SPARK formal verification for Adamant components and standalone packages. Use when adding SPARK contracts, running GNATprove, writing preconditions/postconditions, proving absence of runtime errors, or integrating formal verification into the Adamant build pipeline.
---

# SPARK Formal Verification in Adamant

SPARK is a subset of Ada with contracts (preconditions, postconditions, data dependencies) that enables mathematical proof of program correctness. Adamant integrates GNATprove through `admt prove`.

## Quick Start

1. Add `SPARK_Mode => On` to package spec and body
2. Write contracts (Pre, Post, Global, Depends)
3. Create `all.prove.yaml` in the component/package directory (optional -- defaults: level 2, mode gold)
4. Run `admt prove` from that directory

## SPARK Mode

### Enabling SPARK

Apply to entire package:

```ada
package My_Package with SPARK_Mode => On is
   -- All declarations here are SPARK-checked
end My_Package;

package body My_Package with SPARK_Mode => On is
   -- All bodies here are SPARK-checked
end My_Package;
```

### SPARK Mode and the Adamant Dependency Scanner

The aspect form on a package declaration is safe. Writing `package Foo_Logic with SPARK_Mode => On, Pure is` wraps the `is` keyword onto its own line, and the dependency scanner resolves it: it matches package declarations against comment-stripped, semicolon-split statements rather than a single line, so a multi-line or aspect-decorated declaration still registers the component's source directory. Use the aspect form the rest of this skill recommends; no pragma-in-the-body or shim workaround is needed.

### Selective SPARK Mode

Disable for specific subprograms that can't satisfy SPARK restrictions:

```ada
package body My_Component with SPARK_Mode => On is

   procedure Pure_Computation (X : in out Integer) is
   begin
      X := X + 1;  -- Provable
   end Pure_Computation;

   procedure Handle_Command (Self : in out Instance; Cmd : in Command.T)
      with SPARK_Mode => Off  -- Complex command handling
   is
   begin
      -- Access types, exception handlers, etc.
   end Handle_Command;

end My_Component;
```

### What SPARK Disallows
- Access types (pointers) -- use in `SPARK_Mode => Off` regions
- Exception handlers -- use preconditions instead
- Tasking beyond Ravenscar profile
- Side effects in functions (functions must be pure)
- General aliasing

## Using This Skill With the Vendor GNATprove Skill

When a `gnatprove` skill from the toolchain vendor is available alongside this one, it is
authoritative for raw tool mechanics (invocation, proof levels, counterexamples, SPARK
language idioms, floating-point and overflow references). This skill is authoritative for
everything Adamant-specific: logic-package factoring, `all.prove.yaml`, `admt prove`
integration, and the framework's own type/generation constraints. Read the vendor skill for
the tool; read this one for how the tool meets the framework.

One documented override applies when following the vendor guidance:

**Specified saturation is not proof-convenience clamping.** General SPARK guidance warns
against introducing clamps to make proofs discharge, and for ordinary application logic that
warning is correct: a `Min`/`Max` bolted on to silence a prover hides a real precondition.
The warning does not apply when the bound is part of the specification. Hardware registers,
device models, protocol fields, and configured limits saturate by design, and a faithful
implementation must reproduce the clamped value (and any status flag) exactly.

Discriminating question: **is this bound in the specification, or did I add it to make the
prover happy?**

| Case | Treatment |
|------|-----------|
| Clamp as proof convenience | Anti-pattern. Remove it and state the real precondition. |
| Clamp as specified behavior | Model it. Express the saturating branch in the postcondition so the bound is proved, not hidden. |

Express specified saturation as a multi-branch postcondition (`Contract_Cases`, or a
conditional expression per case) so the clamp becomes a proved case split:

```ada
function Allocate (Requested : Count_T; Limit : Count_T) return Count_T
   with Global => null,
        Post => Allocate'Result <= Limit
                and then (if Requested <= Limit then Allocate'Result = Requested)
                and then (if Requested > Limit then Allocate'Result = Limit);
```

The three-branch signed-saturation shapes in `references/contract-patterns.md` are the same
idea for `Integer_32` corrections.

## Contract Patterns

### Preconditions and Postconditions

```ada
procedure Increment (X : in out Integer)
   with Pre  => X < Integer'Last,       -- Caller must guarantee
        Post => X = X'Old + 1;          -- Implementation must guarantee

function Clamp (Val, Lo, Hi : Integer) return Integer
   with Pre  => Lo <= Hi,
        Post => Clamp'Result >= Lo and then Clamp'Result <= Hi;
```

### State the equivalence when code branches on the property

A property a caller will *branch on* -- cull or keep, saturate or pass, accept or reject -- must
be stated as an **equivalence**, not a one-way implication. The implication is the trap because it
is true and it proves, so the contract looks finished while the direction the caller needs is
absent:

```ada
-- Weaker than it looks: proves, but a caller deciding NOT to act gets nothing.
Post => (if A > Threshold then Square (A) > Square (Threshold));

-- Decision-supporting: holds in both directions.
Post => (Square (A) > Square (Threshold)) = (A > Threshold);
```

Same shape as a saturation flag, specified `Flag = (out of range)` and not
`(if out of range then Flag)`: a model that over-reports the flag satisfies the implication and is
still wrong. The question when writing the contract is **"is anything going to branch on this?"** --
if so, write `P = Q` (one equivalence) rather than paired `if` implications, so the symmetry is
visible and cannot be half-updated later. The equivalence is usually no harder to prove; nonlinear
ones like the squared-magnitude case discharge with null-body lemmas just as the implication would.

### Data Dependencies (Global and Depends)

```ada
procedure Process (Input : Integer; Output : out Integer)
   with Global  => (Input  => Config_Table,       -- Reads global
                    In_Out => Statistics_Counter), -- Reads and writes global
        Depends => (Output             => (Input, Config_Table),
                    Statistics_Counter => Statistics_Counter);
```

`Global => null` means no global state accessed. Prefer this -- it makes proofs simpler.

### Expression Functions

Expression functions are automatically inlined by the prover -- no ghost lemma needed:

```ada
function Is_Valid (X : Integer) return Boolean is
   (X >= 0 and then X <= 1000);

procedure Use_Valid (X : Integer)
   with Pre => Is_Valid (X);  -- Prover inlines the definition
```

### Ghost Code

Ghost entities exist only for proof -- compiled away in production:

```ada
function Is_Sorted (Arr : Array_Type) return Boolean
   with Ghost;

Original : constant Array_Type := Data with Ghost;  -- Ghost variable

pragma Assert (Is_Sorted (Data));  -- Ghost assertion
```

### Loop Invariants

Required for loops -- the prover cannot reason about loops without them:

```ada
for I in Arr'Range loop
   Arr (I) := Arr (I) + 1;
   pragma Loop_Invariant (I >= Arr'First);
   pragma Loop_Invariant
      (for all J in Arr'First .. I => Arr (J) = Arr'Loop_Entry (J) + 1);
end loop;
```

### Ghost Lemma Pattern

When the prover cannot deduce that `f(A) = f(B)` when `A = B` for non-expression functions, use a ghost lemma with confined `pragma Assume`:

```ada
procedure Lemma_Substitution (A : String; B : String)
   with Ghost,
        Pre  => A = B and then <bounds>,
        Post => My_Predicate (A) = My_Predicate (B)
is
begin
   -- Expression functions prove automatically (inlined).
   -- Non-expression functions need confined assumes:
   pragma Assume (My_Predicate (A) = My_Predicate (B),
                  "Pure function determinism: A = B implies f(A) = f(B)");
end Lemma_Substitution;
```

Rules:
- 0 assumes in business logic -- confine all to ghost lemmas
- Each assume must be mathematically sound and documented
- Ghost lemmas are compiled away -- zero runtime cost

## Proof Strategy for Adamant Components

### Typical SPARK Scope in an Adamant Component

Most Adamant component code touches framework types (tagged records, access types, protected objects) that are outside SPARK. The provable surface is:

1. **Pure computation procedures** -- arithmetic, validation, transformation
2. **Type invariants** -- range checks, state machine transitions
3. **Algorithm correctness** -- pre/post on domain-specific logic
4. **Absence of runtime errors** -- overflow, division by zero, index out of range

### What to Prove vs What to Test

| Prove (SPARK) | Test (AUnit) |
|---------------|--------------|
| No overflow in arithmetic | Correct functional behavior |
| Array indices in bounds | Command/response sequences |
| State machine transitions valid | Integration with framework |
| Preconditions satisfiable | Timing and scheduling |
| Data dependency correctness | Coverage of error paths |

### Proof Chain Pattern

Used when validation in one function must be visible to callers through an opaque type:

1. Define shared predicates as expression functions (auto-inlined by prover)
2. Validation function checks predicates, returns on failure
3. Constructor's postcondition guarantees `Accessor(Result) = Input`
4. Query functions call same predicates on `Accessor(Value)`
5. Ghost lemma bridges non-expression predicate substitution
6. Caller's postcondition follows by substitution

## GNATprove Configuration

### all.prove.yaml

Place in the component or package directory:

```yaml
---
description: GNATprove configuration for <component_name>
level: 2
mode: "silver"
```

All fields are optional. Defaults: level 2, mode gold.

### Level (0-4)

| Level | Timeout | Provers | Counterexamples |
|-------|---------|---------|-----------------|
| 0 | 1s | cvc4 | off |
| 1 | 1s | cvc4, z3, altergo | off |
| 2 | 5s | cvc4, z3, altergo | on |
| 3 | 20s | cvc4, z3, altergo | on |
| 4 | 60s | cvc4, z3, altergo | on |

### Mode

| Mode | What It Checks |
|------|----------------|
| `check` / `stone` | Basic syntax/type checking |
| `check_all` | Extended checking (unused variables) |
| `flow` / `bronze` | Data and control flow analysis |
| `silver` | Flow + proof of easy conditions |
| `prove` / `all` / `gold` | Comprehensive analysis |

Start with `silver` level 1-2. Escalate to `gold` level 3-4 for critical paths.

### Environment Override

```bash
admt env exec "cd /home/user/<project>/<component> && PROVE_SWITCHES='--level=4 --mode=gold' redo prove"
```

### Output

Results go to `build/prove/prove.txt`.

### Keep the Silver-to-Gold boundary visible: count the assumes

`pragma Assume` is the one construct that can make an unproved property look proved, so the
proof gate should report how many exist, every run, alongside the unproved-subprogram count:

```bash
grep -c "pragma Assume" *.adb
```

Print both numbers whenever the gate runs. A codebase that does not count its assumes drifts
from Gold to "Gold with exceptions" invisibly; a counted one makes assume creep show up the
moment it lands. Each surviving assume must be confined to ghost code and carry a written
mathematical justification (see the ghost lemma pattern above).

## Build System Integration

> **Prefer `admt prove`.** It compiles the SPARK sources and runs GNATprove for you; you should not
> need to invoke `gnatprove` or `gprbuild` directly, hand-build `SOURCE_DIRS`, or work around the
> dependency scanner. If a build-system shortcoming ever does force a naked tool call, flag it and
> report it to the user as a candidate Adamant issue, quoting the exact command and the gap it works
> around, rather than treating the naked invocation as the intended interface.

### `admt prove`

`admt prove` compiles the SPARK sources in the directory and runs GNATprove over them. It works the same for a standalone SPARK package and for an Adamant component: in a component directory it analyzes the component's sources, including the autocoded child units (`component-<name>.ads` and the `*-representation` units), and proves the directory in place, writing the summary beside the component at `build/prove/gnatprove/gnatprove.out`. Run it from the directory you want proved.

**Read the summary; exit status is not proof.** A clean run prints no findings, and so does a
run that analyzed nothing you cared about. Open the summary and check the Unproved column:

```
Summary of SPARK analysis
  Run-time Checks        6    .    6 (Z3)    .    .
  Assertions             1    .    1 (Z3)    .    .
  Functional Contracts   1    .    1 (Z3)    .    .
  Total                 10    2 (20%)  8 (80%)  .   .
```

Confirm the Detailed analysis report names the subprograms you expected, with `0 pragma Assume statements`.

### Other Build Targets

```bash
admt style    # Style check (includes Ada warnings)
admt test     # Unit tests
admt coverage # Coverage analysis
```

### GNAT Body Discovery: Pure Packages Must Have Bodies

When `gnatprove` scans source directories, GNAT's naming convention infers that `foo_logic.ads` should have a corresponding `foo_logic.adb`. If the package contains ONLY expression functions and `pragma Pure`, Ada semantics say no body is allowed -- but GNAT still looks for one by naming convention and reports:

```
error: package "Foo_Logic" does not allow a body
error: remove incorrect body in file "foo_logic.adb"
```

This error appears even when the `.adb` file does not exist. The fix: **always provide at least one non-expression-function subprogram** so a body is required. Move expression functions to non-expression form with matching postconditions:

```ada
-- Spec: non-expression function forces body requirement
function Should_Forward (Channel : Index; Active : Index; Broadcast : Boolean) return Boolean
with Global => null,
     Post => Should_Forward'Result = (Broadcast or else Channel = Active);

-- Body: trivial implementation matching postcondition
function Should_Forward (Channel : Index; Active : Index; Broadcast : Boolean) return Boolean is
begin
   return Broadcast or else Channel = Active;
end Should_Forward;
```

Expression functions that remain in the spec (alongside the non-expression ones) are still auto-inlined by the prover.

## Common Proof Failures

| Message | Cause | Fix |
|---------|-------|-----|
| "precondition might fail" | Caller doesn't guarantee Pre | Add check before call, or strengthen caller's Pre |
| "postcondition might fail" | Implementation doesn't satisfy Post | Add assertions, strengthen implementation, or weaken Post |
| "overflow check might fail" | Arithmetic may exceed type range | Add range Pre, use wider intermediate type, or add assertion |
| "divide by zero might fail" | Divisor could be 0 | Add `Divisor /= 0` Pre |
| "index check might fail" | Array index may be out of bounds | Add bounds Pre or assertion |
| "loop invariant not preserved" | Invariant doesn't hold after iteration | Strengthen invariant or add intermediate assertions |
| "loop invariant not established" | Invariant doesn't hold on first iteration | Fix initial condition or invariant expression |

### Float Overflow in Subtraction

Float subtraction `A - B` overflows when operands have opposite signs near type extremes. Fix: define a bounded float subtype that guarantees `A - B` fits:

```ada
-- Max range / 4 ensures a-b never overflows Short_Float
subtype Bounded_Float is Short_Float range -1.0E+37 .. 1.0E+37;
subtype Positive_Float is Short_Float range Short_Float'Succ (0.0) .. 1.0E+37;

function Abs_Error (Target : Bounded_Float; Current : Bounded_Float) return Short_Float
  with Global => null,
       Post => Abs_Error'Result >= 0.0;
```

This is saturation-by-subtype: narrower input range eliminates the overflow class entirely, no restrictive Pre needed.

### Integer Conversion Range in mod Expressions

`Unsigned_16 (X mod Period)` fails when Period is Unsigned_32 -- the mod result can exceed U16 range. Fix: make Period the same width as the target type:

```ada
-- BAD: Period is U32, mod result can be up to U32'Last-1
function F (Tick : Unsigned_32; Period : Unsigned_32) return Unsigned_16
  with Pre => Period > 0;  -- mod result still can exceed U16

-- GOOD: Period is U16, mod result guaranteed <= U16'Last
function F (Tick : Unsigned_32; Period : Unsigned_16) return Unsigned_16
  with Pre => Period > 0;
```

### Escalation Strategy

1. Read counterexample (level >= 2 enables them)
2. Add `pragma Assert` before the failing point to narrow the gap
3. Add loop invariants for any loop the prover must reason through
4. Try higher level (`--level=3` or `--level=4`)
5. If a non-expression function blocks proof, consider ghost lemma
6. Last resort: `pragma Assume` with documented justification (confine to ghost code)

## Adamant-Specific SPARK Notes

### Memory Maps and Register Maps

Framework auto-generates memory/register map packages with `SPARK_Mode => On`. This detects bit-constrained types that would be dangerous in hardware-mapped memory (corrupted value outside range = mission-ending failure). These are analyzed by GNATprove during `admt prove` on the generated packages.

### Component Implementation

Standard Adamant components are Ada 2012, NOT SPARK by default. SPARK is opt-in per package or per subprogram. The typical pattern:

1. Factor provable logic into a separate package (e.g., `my_component_logic.ads/.adb`)
2. Apply `SPARK_Mode => On` to that package
3. Call from the component implementation (which may be `SPARK_Mode => Off`)
4. Create `all.prove.yaml` in the component directory
5. `admt prove` analyzes all SPARK-mode sources in that directory

### Packed Types

Packed type assertion packages (generated `*-assertion.adb`) are excluded from prove analysis. The prove build rule filters out assertion objects automatically.

## Logic Package Conventions

When creating SPARK logic packages for Adamant components:

1. **Pure** on all logic packages -- they must have no state, no side effects. This also enables `Global => null` on everything. Use the **aspect form** on the package declaration: `package Foo_Logic with SPARK_Mode => On, Pure is` -- do NOT use a standalone `pragma Pure;` before the package declaration (it must come after the package name, and the aspect form is cleaner).
2. **Expression functions** for predicates and simple computations -- prover inlines them automatically, giving stronger postconditions with zero proof effort.
3. **Saturation over restrictive Pre** -- prefer `if X < T'Last then X := X + 1` over `Pre => X < T'Last`. Callers should not need to check preconditions for safe counter increments.
4. **Signed integer saturation** -- for `Integer_32` (offsets, corrections), saturate at both `Integer_32'First` and `Integer_32'Last`. The postcondition needs three branches: positive correction, negative correction, zero.
5. **Bitwise operation postconditions** -- `Apply_Mask` can prove `(Result and (not Mask)) = 0` (no bits outside mask). XOR proves `Result = 0` when inputs are equal.
6. **Unconstrained array types** in logic packages when needed -- avoids coupling to specific buffer sizes. BUT: if the array index is `Natural range <>`, the prover cannot bound `Buffer'Length` (it could be `Natural'Last + 1` which overflows). Fix: define a bounded index subtype (e.g., `subtype Buffer_Index is Natural range 0 .. 255`) and use that as the array index range. This gives the prover a concrete upper bound.
7. **No framework dependencies** -- logic packages import only `Interfaces` (or nothing). Never `with` Adamant framework packages.
8. **Float arithmetic stays outside SPARK** -- float addition/subtraction can overflow (`Short_Float'Last + Short_Float'Last`), and the prover CANNOT verify float saturation guards even when mathematically sound (e.g., `if A > Short_Float'Last - B then saturate` -- the prover can't prove `A + B` is safe in the else branch because float arithmetic isn't monotone in its model, AND the guard subtraction `Last - B` may itself overflow). Three options in decreasing preference: (a) prove only `Clamp_Float(V, Lo, Hi)` which has no arithmetic, letting the component body do float math outside SPARK; (b) use bounded float subtypes restricting the domain; (c) use `pragma Annotate (GNATprove, False_Positive, ...)` AFTER the offending return statement. See contract-patterns.md "Float Saturation: Avoid Arithmetic in Guards" for all three patterns.
9. **Conditional conservation postconditions** -- when saturation breaks exact arithmetic (e.g., `delta_valid + delta_invalid = delta_total`), gate the conservation clause on the non-saturation case: `if all inputs < T'Last then exact_equality`. The prover can verify this conditional form.
10. **Bounded subtypes for loop counters** -- when counting elements in a bounded array (e.g., "how many are stale?"), define the counter as a subtype of the array's index/length range. Then `Count <= I` is a valid loop invariant and the postcondition `Result <= N` proves automatically. Example: `subtype Sensor_Count is Natural range 0 .. Max_Sensors;` with the counter and N both being `Sensor_Count`. Without this, the prover cannot bound `Count + 1` against `Natural'Last`.
11. **No `implies` keyword** -- the Adamant Docker GNAT does not support Ada 2022's `implies`. Use `A or else (not B)` for `(not A) implies B`, i.e., rewrite `X implies Y` as `(not X) or else Y`. This applies to postconditions, assertions, and ghost code.
12. **64-bit intermediate for rate calculations** -- for percentage/permille (e.g., `errors * 1000 / total`), cast to `Unsigned_64` before multiplying to avoid overflow. Clamp result to the valid range (0..100 or 0..1000) and the postcondition `Result <= Bound` proves cleanly.

## Checklist

1. Identify provable surface (pure computation, validation, state transitions)
2. Factor into separate package if component implementation uses non-SPARK features
3. Add `SPARK_Mode => On` to spec and body
4. Write contracts: Pre, Post, Global (prefer `Global => null`)
5. Add loop invariants for every loop
6. Create `all.prove.yaml` (start: level 2, mode silver)
7. Run `admt prove`
8. Fix failures using escalation strategy
9. Escalate to gold mode when silver passes clean
10. Document any `pragma Assume` with mathematical justification

## References
- `references/contract-patterns.md` -- Advanced contract patterns, ghost code examples, and proof chain walkthrough
- `references/integer-logic-conversion.md` -- Read when converting existing integer arithmetic
  (especially a body defended by `pragma Assert`) into a proved logic package: extraction
  boundary, what modular register types do to your proof obligations, clamp-then-narrow,
  writing postconditions as properties, and the four verification fronts a conversion needs
- `references/proof-mechanics.md` -- Read when a proof will not discharge or will not even run:
  the loop-invariant "non-scalar object declared before loop-invariant" restriction (and using
  it as a prompt to unroll a domain-fixed loop), variable-exponentiation nonlinearity (a product
  with `2 ** N` defeats the provers; the failure surfaces in dependents, not at the cause; prefer
  a divisor), and the compile-time-first ladder for discharging a fact (`Compile_Time_Error` over
  derived constants, which `--mode=check` does not evaluate)
- `references/fixed-point-proofs.md` -- Read when the numeric code is (or could be) fixed-point
  rather than float: declaring a type that means the hardware format (`delta`, explicit
  `Small`, `Size`), the `universal_fixed` conversion, widening products in the body AND the
  contract, saturation-with-flag, and modelling per-operation scale/selector in the contract.
  Fixed-point lowers to linear integer arithmetic and proves where float does not, so
  "fixed-point vs float" is a proof decision worth making before committing to float
