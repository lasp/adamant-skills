---
name: adamant-algorithm-wrapping
description: Complete pipeline for wrapping C++ algorithms into Adamant passive components with C shims, Ada bindings, and unit tests. Use when integrating external C/C++ code, creating FFI boundaries, or building Adamant components around existing algorithm libraries.
---

# Adamant Algorithm Wrapping Pipeline

```
C++ Algorithm -> C Shim (.h/.cpp) -> Ada Bindings (.ads) -> Packed Records -> Component YAML -> Implementation -> Tests
```

Seven deterministic steps. Each step has one correct output given the inputs. Follow in order.

## Step 1: Create C Shim

**Input:** C++ algorithm class (`FooAlgorithm` in `fooAlgorithm.h/.cpp`)
**Output:** `fooAlgorithm_c.h` + `fooAlgorithm_c.cpp` (+ optional `fooTypes.h`)

### Check for shared types FIRST

If the C++ algorithm defines structs or `#define` constants in its public API, create a shared `*Types.h` header to avoid duplication between C++ and C shim. See [references/c-shim-patterns.md](references/c-shim-patterns.md#shared-types-header).

### File structure

- `fooAlgorithm_c.h` -- pure C header (no C++ keywords), `extern "C"` guarded
- `fooAlgorithm_c.cpp` -- implementation using `reinterpret_cast`
- `fooTypes.h` -- shared POD structs/constants (optional, when DRY needed)

### Mandatory API functions

```c
FooAlgorithm* FooAlgorithm_create(void);
void FooAlgorithm_destroy(FooAlgorithm* self);
OutputPayload FooAlgorithm_update(FooAlgorithm* self, const InputPayload* input);
```

Add `_reset`, `_setX`, `_getX` as needed. For `#define` constants, add getter functions for Ada elaboration-time validation.

### Rules

- Headers MUST be pure C (no C++ keywords, templates, classes)
- `const` correctness on all input-only parameters
- Opaque handle: `typedef struct FooAlgorithm FooAlgorithm;`
- Eigen types: convert to POD (`Vector3f_c { float data[3]; }`) at the boundary
- Message payloads from `msgPayloadDef/`: pass through directly (already POD)
- Naming: `ClassName_methodName` (PascalCase class, camelCase method)
- No exception catching in shim layer
- Use `new`/`delete`, not `malloc`/`free`

> Full templates and examples: [references/c-shim-patterns.md](references/c-shim-patterns.md)

## Step 2: Create Ada Bindings

**Input:** C shim header (`fooAlgorithm_c.h`)
**Output:** `foo_algorithm_c.ads` in component directory

### h2ads workflow

```bash
cd /home/user/adamant_bot_station/src/components/<component_name>
h2ads --compiler gcc \
  -I /home/user/fp32-fsw-xmera/algorithms \
  -b /home/user/fp32-fsw-xmera/algorithms/<algorithm_name> \
  /home/user/fp32-fsw-xmera/algorithms/<algorithm_name>/<algo>Algorithm_c.h
```

Delete ALL generated files except `<algo>_algorithm_c_h.ads`. Then transform:

### Transformation checklist

1. Remove `_H` suffix from package name and filename
2. Make opaque type `limited private`, move `null record` to private section
3. Create named access type: `type Foo_Algorithm_Access is access all Foo_Algorithm;`
4. Remove type name prefix from functions: `Foo_Algorithm_Create` -> `Create`
5. Replace `access Type` with `Type_Access` throughout
6. DELETE all h2ads-generated C struct types (see Step 3 for packed records)
7. Replace payload package references with Adamant types (`.C.U_C`)
8. Add `pragma Assert` for any `#define` constant validation
9. Format with aligned `=>` operators and Doxygen-style `--*` comments
10. Delete ALL `*_h.ads` files when done

### Type mapping (h2ads -> Adamant)

| h2ads type | Adamant type | With clause |
|------------|-------------|-------------|
| `Nav_Att_Msg_F32_Payload_H.Nav_Att_Msg_F32_Payload` | `Nav_Att.C.U_C` | `with Nav_Att.C;` |
| `access constant <Payload>` | `<Payload>.C.U_C_Access` | same |
| `Vector3f_C` (POD helper) | `Packed_F32x3_Record.C.U_C` | `with Packed_F32x3_Record.C;` |
| Algorithm-specific structs | Create packed record (Step 3) | `with <Type>.C;` |

> Full transformation rules and complete example: [references/ada-binding-transforms.md](references/ada-binding-transforms.md)

## Step 3: Create Packed Record Types

**Input:** C struct definitions from shim headers or shared types
**Output:** YAML files in `src/types/`

Before creating: check if type already exists (`ls src/types/*.record.yaml | grep -i <name>`).

### C-to-Adamant type mapping

| C type | Adamant type | Format |
|--------|-------------|--------|
| `float` | `Short_Float` | `F32` |
| `double` | `Long_Float` | `F64` |
| `uint32_t` | `Interfaces.Unsigned_32` | `U32` |
| `int32_t` | `Interfaces.Integer_32` | `I32` |
| `float x[3]` | `Packed_F32x3.T` | (none) |
| `float x[9]` | `Packed_F32x9.T` | (none) |

NEVER use `Natural` for C unsigned types. Scalar primitives MUST have `format:`. Array types do NOT.

### Field naming: C camelCase -> Ada Pascal_Case

- `sigma_BN` -> `Sigma_Bn` (multi-letter -> first-cap only)
- `omega_BN_B` -> `Omega_Bn_B` (single letter stays uppercase)
- `r_BN_N` -> `R_Bn_N`

Include original C struct as YAML comment. See [references/packed-record-patterns.md](references/packed-record-patterns.md).

## Step 4: Create Component YAML Files

**Input:** Algorithm interface analysis
**Output:** `.component.yaml`, `.data_dependencies.yaml`, `.data_products.yaml`, optionally `.parameters.yaml`

### Decision: Parameters vs Data Dependencies

**Parameters** (`.parameters.yaml`): configuration that changes infrequently (gains, inertia, calibration). Updated via ground command.
**Data Dependencies** (`.data_dependencies.yaml`): dynamic state changing every cycle (attitude, position, sensor readings). Fetched from data product database.

### component.yaml template

```yaml
---
description: <Brief description>
execution: passive
init:
  description: Initializes the <algorithm> algorithm.
connectors:
  - description: Run the algorithm up to the current time.
    type: Tick.T
    kind: recv_sync
  - description: Fetch a data product item from the database.
    type: Data_Product_Fetch.T
    return_type: Data_Product_Return.T
    kind: request
  - description: The data product invoker connector
    type: Data_Product.T
    kind: send
```

If component has parameters, add: `- { description: Parameter update, type: Parameter_Update.T, kind: modify }`

### data_dependencies.yaml

```yaml
---
description: Data dependencies for <Component>
data_dependencies:
  - name: <Input_Name>
    type: <Type>.T
    description: <what it represents>
```

### data_products.yaml

```yaml
---
description: Data products for <Component>
data_products:
  - name: <Output_Name>
    type: <Type>.T
    description: <what it represents>
```

> Full templates with parameters: [references/component-yaml-templates.md](references/component-yaml-templates.md)

## Step 5: Generate Templates and Implement

```bash
cd src/components/<component_name>
redo templates
cp build/template/*.ad[sb] .
```

### Implementation spec (.ads) modifications

1. Add `with <Algorithm>_C; use <Algorithm>_C;`
2. Add `not overriding procedure Destroy (Self : in out Instance);`
3. Set instance record: `Alg : <Algorithm>_Access := null;`

### Implementation body (.adb) pattern

```ada
with <Type_1>.C;
with Algorithm_Wrapper_Util;

package body Component.<Name>.Implementation is

   overriding procedure Init (Self : in out Instance) is
   begin
      Self.Alg := Create;
   end Init;

   not overriding procedure Destroy (Self : in out Instance) is
   begin
      Destroy (Self.Alg);
   end Destroy;

   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
      use Data_Product_Enums; use Data_Product_Enums.Data_Dependency_Status;
      use Algorithm_Wrapper_Util;
      Dep_1 : Type_1.T;
      Dep_1_Status : constant Data_Dependency_Status.E :=
         Self.Get_Dep_Name (Value => Dep_1, Stale_Reference => Arg.Time);
   begin
      Self.Update_Parameters;  -- ONLY if component has parameters
      if Is_Dep_Status_Success (Dep_1_Status) then
         declare
            Dep_1_C : aliased Type_1.C.U_C := Type_1.C.To_C (Type_1.Unpack (Dep_1));
            Output : constant Out_Type.C.U_C := Algorithm_C.Update (
               Self.Alg, Input => Dep_1_C'Unchecked_Access);
         begin
            Self.Data_Product_T_Send (Self.Data_Products.Output_Name (
               Arg.Time, Out_Type.Pack (Out_Type.C.To_Ada (Output))));
         end;
      end if;
   end Tick_T_Recv_Sync;

end Component.<Name>.Implementation;
```

### Type conversion chain

- **Input:** `Ada .T` -> `Unpack` -> `Ada .U` -> `To_C` -> `C.U_C` -> pass `'Unchecked_Access`
- **Output:** `C.U_C` -> `To_Ada` -> `Ada .U` -> `Pack` -> `Ada .T`

### If component has parameters

Implement `Update_Parameters_Action` to apply parameters to the C algorithm:
```ada
overriding procedure Update_Parameters_Action (Self : in out Instance) is
begin
   Set_Gain (Self.Alg, Self.Gain_Param.Value);
end Update_Parameters_Action;
```

> Full implementation patterns: [references/implementation-patterns.md](references/implementation-patterns.md)

## Step 6: Build and Verify

```bash
cd src/components/<component_name>
redo
```

MUST compile with ZERO warnings and ZERO errors. Fix all `-gnatwu`, `-gnatwk` warnings.

## Step 7: Create Unit Tests

```bash
cd src/components/<component_name>/test
# Create env.py, tests.yaml, then:
redo templates
cp build/template/*.ad[sb] .
```

### Test pattern

```ada
overriding procedure Test (Self : in out Instance) is
   T : Component.<Name>.Implementation.Tester.Instance_Access renames Self.Tester;
   type Test_Vector is record
      Input : Type_1.T;
      Expected : Out_Type.T;
   end record;
   Cases : constant array (1 .. N) of Test_Vector := [...];
begin
   for I in Cases'Range loop
      T.<Dep_Name> := Cases (I).Input;
      T.Tick_T_Send ((Time => T.System_Time, Count => 0));
      Natural_Assert.Eq (T.<Output>_History.Get_Count, I);
      declare
         Output : constant Out_Type.T := T.<Output>_History.Get (I);
      begin
         <Type>_Assert.Eq (Output.<Field>, Cases (I).Expected.<Field>, Epsilon => 0.0001);
      end;
   end loop;
end Test;
```

### Critical test rules

- ALWAYS use `T.System_Time` for Tick timestamp (NOT `(0, 0)`)
- Work with `.T` (packed) types, NOT `.U` (unpacked)
- Array aggregates: `[x, y, z]` NOT `(Value => [x, y, z])`
- Use T rename pattern: `T : ... renames Self.Tester;`
- Call `Destroy` before re-initializing for multiple configurations
- Select 3-5 representative cases from Python tests for integration validation

> Full test templates and troubleshooting: [references/unit-test-patterns.md](references/unit-test-patterns.md)

## Containing Shims in Project Repository

When wrapping xmera algorithms for a project (e.g., adamant_bot_station), keep shims and wrapper components inside the project repo to avoid modifying the upstream xmera repos:

```
adamant_bot_station/
  src/
    components/<component_name>/         # Adamant wrapper component
      <component_name>_algorithm_c.ads   # Ada bindings
      component-*-implementation.ads/adb # Implementation
    types/                               # Packed record YAMLs
  xmera_shims/                           # C shim files (local copy)
    <algorithm_name>/
      <algo>Algorithm_c.h
      <algo>Algorithm_c.cpp
```

The C++ algorithms remain read-only in `fp32-fsw-xmera/`. Only the C shims and Ada code live in the project.

## Reference Corpus

- [references/c-shim-patterns.md](references/c-shim-patterns.md) -- C shim templates, shared types, Eigen conversion
- [references/ada-binding-transforms.md](references/ada-binding-transforms.md) -- h2ads transformation rules, complete before/after example
- [references/packed-record-patterns.md](references/packed-record-patterns.md) -- YAML schema, type mapping, field naming
- [references/component-yaml-templates.md](references/component-yaml-templates.md) -- Component/dependency/product/parameter YAML
- [references/implementation-patterns.md](references/implementation-patterns.md) -- Ada implementation with/without parameters
- [references/unit-test-patterns.md](references/unit-test-patterns.md) -- Test templates, T rename, common pitfalls
