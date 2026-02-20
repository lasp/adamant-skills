<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# SPARK Formal Verification in Adamant

## Adding SPARK to a Component

1. Add `SPARK_Mode => On` to package spec and body
2. Create `all.prove.yaml` in component directory
3. Run `redo prove`

The prove target uses `Linux_Prove`, sets `SAFE_COMPILE=True`, runs GNATprove, outputs to `build/prove/prove.txt`.

## all.prove.yaml Reference

```yaml
---
description: GNATprove configuration
level: 2        # 0-4, proof effort
mode: "silver"  # Analysis mode
```

### Levels

| Level | Timeout | Provers | Counterexamples |
|-------|---------|---------|-----------------|
| 0 | 1s | cvc4 | off |
| 1 | 1s | cvc4,z3,altergo | off |
| 2 | 5s | cvc4,z3,altergo | on |
| 3 | 20s | cvc4,z3,altergo | on |
| 4 | 60s | cvc4,z3,altergo | on |

### Modes

| Mode | Purpose |
|------|---------|
| `check`/`stone` | Basic syntax/type checking |
| `flow`/`bronze` | Data and control flow analysis |
| `silver` | Flow + proof of easy conditions (**recommended start**) |
| `prove`/`gold` | Comprehensive proof (**default**) |
| `all` | Both flow and proof |

Override: `PROVE_SWITCHES="--level=4 --mode=gold" redo prove`

## SPARK Contract Patterns

```ada
-- Preconditions/Postconditions
procedure Increment (X : in out Integer)
   with Pre => X < Integer'Last,
        Post => X = X'Old + 1;

-- Data Dependencies
procedure Process (Input : Integer; Output : out Integer)
   with Global => (Input => Some_Const, In_Out => Some_Var),
        Depends => (Output => Input, Some_Var => (Some_Var, Input));

-- Ghost Code for proof assistance
function Is_Sorted (Arr : Array_Type) return Boolean with Ghost;
```

## SPARK Gotchas

1. **Access types not allowed** — Use nested `package Accesses with SPARK_Mode => Off` for pointers
2. **Command handlers** — May need `SPARK_Mode => Off` if they use complex global state or access types
3. **Tasking restrictions** — Complex tasking patterns may need `SPARK_Mode => Off`
4. **No exception handling** — Use preconditions instead of `exception when`
5. **File I/O** — Not provable; put in `SPARK_Mode => Off` regions

## Common Proof Failures

| Message | Fix |
|---------|-----|
| "precondition might fail" | Add stronger precondition or runtime check |
| "postcondition might fail" | Strengthen implementation or weaken postcondition |
| "overflow check might fail" | Add range constraints or preconditions |
| "divide by zero might fail" | Add `Divisor /= 0` precondition |

## Best Practices

- Start with `mode: "silver"`, `level: 2`; escalate as contracts improve
- Use `SPARK_Mode => Off` selectively for non-provable parts
- Ghost variables/assertions help provers understand intent
- SPARK proves absence of runtime errors, not functional correctness — still test
