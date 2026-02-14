---
name: adamant-algorithm-wrapping
description: Complete pipeline for wrapping C++ algorithms into Adamant passive components with C shims, Ada bindings, and unit tests
---

# Adamant Algorithm Wrapping Pipeline

```
C++ Algorithm → C Shim → Ada Bindings → Packed Records → Component YAML → Implementation → Tests
```

## Component YAML (Typical Wrapper)

```yaml
description: Wraps FooAlgorithm
execution: passive
init:
  description: Creates algorithm handle.
connectors:
  - description: Run algorithm on tick.
    type: Tick.T
    kind: recv_sync
  - description: Fetch data product.
    type: Data_Product_Fetch.T
    return_type: Data_Product_Return.T
    kind: request
  - description: Data product output.
    type: Data_Product.T
    kind: send
  - description: Events.
    type: Event.T
    kind: send
  - description: System time.
    return_type: Sys_Time.T
    kind: get
```

Add `Parameter_Update.T` modify only if runtime-tunable config needed.

## C Shim Pattern

### File Structure
- `<algorithm>Algorithm_c.h` — C shim header (MUST be pure C, no C++ keywords)
- `<algorithm>Algorithm_c.cpp` — C shim implementation
- `<algorithm>Types.h` — Shared types header (DRY: both C++ and C shim include this)

### Opaque Handle Pattern
```c
typedef struct FooAlgorithm FooAlgorithm;
FooAlgorithm* FooAlgorithm_create(void);
void FooAlgorithm_destroy(FooAlgorithm* self);
OutputPayload FooAlgorithm_update(FooAlgorithm* self, const InputPayload* input);
```

### POD Conversion (Eigen types)
```c
typedef struct { float data[3]; } Vector3f_c;
```

### Constant Validation
Export getters for `#define` constants (never `static inline`):
```c
uint32_t FooAlgorithm_getMaxCount(void);
```

## Ada Bindings (h2ads)

```bash
h2ads --compiler gcc -I <algorithms_dir> -b <algo_dir> <algo>Algorithm_c.h
```

### Transformation Rules
1. **Package rename:** `Foo_Algorithm_C_H` → `Foo_Algorithm_C`
2. **Opaque handle:** Make `limited private` with `null record` in private section
3. **Function rename:** `Foo_Algorithm_Create` → `Create`
4. **Payload types:** Replace h2ads-generated structs with Adamant `.C.U_C` types

### Constant Validation in Ada
```ada
NUM_SLEWS : constant := 3;
function Get_Num_Slews return Unsigned_32
  with Import => True, Convention => C, External_Name => "FooAlgorithm_getNumSlews";
pragma Assert (Unsigned_32 (NUM_SLEWS) = Get_Num_Slews);
```

## Type Mapping (C → Ada YAML)

| C Type | Ada Type | Format |
|--------|----------|--------|
| `float` | `Short_Float` | `F32` |
| `double` | `Long_Float` | `F64` |
| `uint32_t` | `Interfaces.Unsigned_32` | `U32` |
| `int32_t` | `Interfaces.Integer_32` | `I32` |
| `float[3]` | `Packed_F32x3.T` | (none — array types have no format) |

Field names: Pascal_Case with underscores. `sigma_BN` → `Sigma_Bn`, `timeTag` → `Time_Tag`.

## Type Conversion Chain

```
Packed.T (wire) → Unpack → .U (Ada record) → .C.To_C → .C.U_C (C-compatible)
```
Reverse: `.C.To_Ada → Pack → .T`

`.C.U_C` only exists for types with explicit `-c.ads` child package. For custom YAML records, use `access constant Type.T` in binding specs.

## Implementation Pattern

```ada
-- Spec
with Foo_Algorithm_C; use Foo_Algorithm_C;
package Component.Foo.Implementation is
   type Instance is new Foo.Base_Instance with private;
   overriding procedure Init (Self : in out Instance);
private
   type Instance is new Foo.Base_Instance with record
      Alg : Foo_Algorithm_Access := null;
   end record;
end;

-- Body
overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
   use Data_Product_Enums.Data_Dependency_Status;
   Input : Input_Type.T;
   Status : constant Data_Dependency_Status.E :=
      Self.Get_Nav_Attitude (Value => Input, Stale_Reference => Arg.Time);
begin
   if Status = Success then
      declare
         Input_C : constant Input_Type.C.U_C :=
            Input_Type.C.To_C (Input_Type.Unpack (Input));
         Output_C : constant Output_Type.C.U_C :=
            Update (Self.Alg, Input_C'Unchecked_Access);
      begin
         Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Result (
            Arg.Time, Output_Type.Pack (Output_Type.C.To_Ada (Output_C))));
      end;
   end if;
end;
```

## Input Strategy: Parameters vs Data Dependencies

- **Parameters** (modify connector): fixed properties, tunable gains, config. Changed infrequently.
- **Data Dependencies** (request connector): dynamic telemetry from other components. Fetched each tick, staleness-checked.
- **Stateful algorithms**: track config state, call algorithm reset in `Update_Parameters_Action`.

## Testing Pattern

```ada
overriding procedure Test (Self : in out Instance) is
   T : Component.Foo.Implementation.Tester.Instance_Access renames Self.Tester;
begin
   T.Tick_T_Send ((Time => T.System_Time, Count => 0));  -- NOT (0,0)!
   Natural_Assert.Eq (T.Result_History.Get_Count, 1);
end;
```

Use `T.System_Time` for ticks (avoids staleness). Array aggregates: `[x, y, z]` directly.

## Common Pitfalls

- C `float` → `Short_Float` (F32), C `double` → `Long_Float` (F64). Never swap.
- Tick timestamp `(0, 0)` causes data dependency staleness failures
- `get` connector uses `return_type:` only, NOT `type:`
- Every send connector needs `*_Send_Dropped` override
- Check existing framework packed types (`Packed_F32x3`, etc.) before creating new ones
- Zero warnings required for safety-critical code
- Verify C++ library linkage: `nm libAlgorithms.a | grep <name>`

## Build

```bash
redo all                # Compile component
cd test/ && redo test   # Run tests
redo style              # Style check before finalizing
```

See [adamant-style](../adamant-style/SKILL.md) for full style rules (array syntax, short-circuit operators, with-clause hygiene).
