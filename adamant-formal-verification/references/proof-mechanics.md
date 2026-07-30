# Proof Mechanics: restrictions, nonlinearity, and where to discharge a fact

Three things that cost time when proving real packages, each with the verbatim symptom and the
fix. All were reproduced against the Adamant GNAT/GNATprove toolchain; the error strings below
are what it actually prints. Read alongside `integer-logic-conversion.md` and
`fixed-point-proofs.md`; this file is the "why won't it prove / why won't it even run" companion.

## Loop-invariant declaration restriction (and what it tells you)

A loop body that declares a **record or array** object *before* its `pragma Loop_Invariant`
stops GNATprove with a hard error, not a triageable check:

```
error: non-scalar object declared before loop-invariant is not yet supported
```

(The full GNAT form also covers "object with address clause".) Analysis halts entirely, and the
message suggests no remedy. Try these in order:

1. **Hoist the declaration out of the loop, often out of the subprogram.** A constant lookup
   table or mapping usually belongs in the package spec anyway. Moving a
   component-to-flag-bit mapping to the spec both clears the error and improves the design,
   because a caller decoding the flag word needs that mapping beside the bit definitions.
2. **Ask whether the loop should exist at all** -- this is the higher-value move. The
   restriction firing on a per-iteration record is a prompt to check whether the iteration
   count is fixed by the domain. A device with exactly three accumulators has a loop count set
   by hardware, not chosen by the model; writing the three cases out removes the loop, removes
   the invariant obligation, and is more faithful than a loop whose invariant only re-derives
   what the domain already guarantees.
3. Only then keep the loop and move the declaration after the invariant, or into a nested block
   following it.

The lesson beyond the workaround: **a tool restriction can be diagnostic.** When GNATprove
objects to a loop, "is this iteration count fixed by the domain?" is worth asking before
engineering around the objection; a fixed count usually means the loop was a writing-style
artifact, and unrolling it is both provable and more honest.

## Variable exponentiation is nonlinear, and the failure surfaces away from the cause

`2 ** N` with a **variable** `N` is a nonlinear term. Whether it defeats the provers depends on
what has to be reasoned about its magnitude:

- A bare division by it often proves. `D / (2 ** Shift)` with `Shift` in `0 .. 15` discharges
  its division check cleanly -- the result is bounded by `D` regardless of the divisor's value.
- A **product** involving it does not. `X * (2 ** Shift)`, even with `X <= 100` and `Shift <= 15`
  (so the mathematical result fits comfortably), fails:

```
medium: overflow check might fail, cannot prove upper bound for X * (2 ** Shift)
```

The prover cannot bound the product without bounding `2 ** Shift`, and it will not reason
through the nonlinear term to do so, sometimes reaching the time limit first.

**The symptom misdirects.** A second failure can surface in a lemma or caller whose contract
merely *mentions* the offending function; that dependent looks like the problem, and
strengthening it cannot help because the cause is upstream. When several checks fail together,
look for one shared nonlinear term and fix it at the source rather than triaging the failures
separately.

**Fix: take a divisor, not a shift exponent.** Division by a positive value is linear:

```ada
subtype Divisor is Positive range 1 .. 2 ** 15;
function Bucket (D : Natural; G : Divisor) return Natural is (D / G)
   with Post => Bucket'Result <= D;
```

Call sites pass a static constant, so nothing is lost and the shift amount can survive as a
comment. A static exponent (`2 ** 12` with a literal) is also fine -- it folds to a constant. It
is specifically the *variable* exponent inside a bound the prover must establish that is the trap.

## Where to discharge a fact: the compile-time-first ladder

When a relationship must hold, discharge it as early as its inputs allow. Strongest first:

| Where | Applies when | Cost of a violation |
|-------|--------------|---------------------|
| Compile time (`pragma Compile_Time_Error`) | both sides are static | build fails; cannot ship |
| Prover (`Pre`/`Post`/`Assert`) | depends on run-time inputs | check message; must be triaged |
| Run-time validation routine | values arrive at run time | failure in the field |
| Comment | -- | none; erodes silently |

For a static relationship between *derived* constants, a compile-time clause turns the
single-source-of-truth discipline from intended into enforced:

```ada
   Frac_Bits    : constant := 12;
   Operands     : constant := 3;                              -- three-term accumulation
   Operand_Max  : constant := 8;                              -- integer budget of a 1.3.12 term
   Accum_Bound  : constant := Operands * Operand_Max * Operand_Max;   -- derived
   Register_Cap : constant := 4096;                           -- the device's wide register
   pragma Compile_Time_Error (Accum_Bound > Register_Cap,
      "row-accumulator bound exceeds the device register capacity");
```

Two uses this makes possible: it justifies the *absence* of an overflow branch (if the derived
bound provably fits the accumulator, the overflow flag is unreachable and the model needs no
branch for it -- documented rather than assumed), and it makes a later format change that broke
the relationship fail the build instead of quietly widening a proof obligation.

**Verification caveat, worth knowing:** `Compile_Time_Error` is a front-end pragma. It fires
during actual compilation and fails the build, but `gnatprove --mode=check` (fast legality
checking) does **not** evaluate it, so testing the clause only through a prove-check run makes a
satisfied and a violated clause look identical. Confirm the clause by compiling the unit
(`gcc -c -gnatc <unit>.ads`): the violated form reports `error: <your message>`, the satisfied
form compiles clean.

## Two reproducibility notes

- **Version-control the proof switches.** A proof result is only meaningful with the switches
  that produced it. Semantic switches (`--level`, `--mode`, `--report`) belong in the project's
  proof configuration (`all.prove.yaml` here, or a `Prove` package in a raw GPR), not on the
  command line, so they do not drift between runs or developers. Leave only machine-specific
  choices such as parallelism (`-j`) on the command line.
- **For work whose product is a proof, the prover version is part of the evidence.** Proof
  outcomes depend on the prover version, so a dependency manifest that permits a version *range*
  lets a fresh checkout resolve a different prover and get different results silently. Pin it,
  and keep the lock file in version control even where a normal build would omit it.
