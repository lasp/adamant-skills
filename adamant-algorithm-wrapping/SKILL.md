---
name: adamant-algorithm-wrapping
description: Complete pipeline for wrapping C++ algorithms into Adamant passive components with C shims, Ada bindings, and unit tests. Use when integrating external C/C++ code, creating FFI boundaries, or building Adamant components around existing algorithm libraries.
---

# Adamant Algorithm Wrapping Pipeline

```ada
C++ Algorithm -> C Shim (.h/.cpp) -> Ada Bindings (.ads) -> Packed Records -> Component YAML -> Implementation -> Tests
```

Seven deterministic steps. Each step has one correct output given the inputs. Follow in order.

## Step 1: Create C Shim

**Input:** C++ algorithm class (`FooAlgorithm` in `fooAlgorithm.h/.cpp`)
**Output:** `fooAlgorithm_c.h` + `fooAlgorithm_c.cpp` (+ optional `fooTypes.h`)

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
- Use `reinterpret_cast`, `new`/`delete`

> Full patterns: [references/c-shim-patterns.md](references/c-shim-patterns.md)

## Step 2: Create Ada Bindings

**Input:** C shim header (`fooAlgorithm_c.h`)
**Output:** `foo_algorithm_c.ads` in component directory

Use h2ads, then transform:

1. Remove `_H` suffix from package name and filename
2. Make opaque type `limited private`, move `null record` to private section
3. Create named access type: `type Foo_Algorithm_Access is access all Foo_Algorithm;`
4. Remove type name prefix from functions: `Foo_Algorithm_Create` -> `Create`
5. Replace `access Type` with `Type_Access` throughout
6. DELETE all h2ads-generated C struct types (see Step 3 for packed records)
7. Replace payload package references with Adamant types (`.C.U_C`)
8. Add `pragma Assert` for any `#define` constant validation

> Full transformation rules: [references/ada-binding-transforms.md](references/ada-binding-transforms.md)

## Step 3: Create Packed Record Types

**Input:** C struct definitions from shim headers or shared types
**Output:** YAML files in `src/types/`

### C-to-Adamant type mapping

| C type | Adamant type | Format |
|--------|-------------|--------|
| `float` | `Short_Float` | `F32` |
| `double` | `Long_Float` | `F64` |
| `uint32_t` | `Interfaces.Unsigned_32` | `U32` |
| `int32_t` | `Interfaces.Integer_32` | `I32` |
| `float x[3]` | `Packed_F32x3.T` | (none) |

NEVER use `Natural` for C unsigned types. Scalar primitives MUST have `format:`. Array types do NOT.

### Field naming: C camelCase -> Ada Pascal_Case

- `sigma_BN` -> `Sigma_Bn` (multi-letter -> first-cap only)
- `omega_BN_B` -> `Omega_Bn_B` (single letter stays uppercase)

> Full patterns: [references/type-system.md](references/type-system.md)

## Step 4: Create Component YAML Files

**Input:** Algorithm interface analysis
**Output:** `.component.yaml`, `.data_dependencies.yaml`, `.data_products.yaml`, optionally `.parameters.yaml`

### Component YAML template

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

> Full templates: [references/yaml-templates.md](references/yaml-templates.md)

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
```

### Type conversion chain

- **Input:** `Ada .T` -> `Unpack` -> `Ada .U` -> `To_C` -> `C.U_C` -> pass `'Unchecked_Access`
- **Output:** `C.U_C` -> `To_Ada` -> `Ada .U` -> `Pack` -> `Ada .T`

> Full implementation patterns: [references/implementation-patterns.md](references/implementation-patterns.md)

## C/C++ Compilation and Linking

**The Ada build system does NOT automatically compile `.c` or `.cpp` files** in component directories. C/C++ stub files must be compiled separately:

1. **Via CMake/Makefile**: Compile into a static library (e.g., `libgncAlgorithms.a`) and link via the project `.gpr` file
2. **Via project GPR**: Add the `.c` file to the project's GPR `Source_Dirs` and ensure `for Languages use ("Ada", "C");`

Without this step, you will get `undefined reference` linker errors for all C functions called from Ada bindings.

## Step 6: Build and Verify

```bash
cd src/components/<component_name>
redo
```

MUST compile with ZERO warnings and ZERO errors.

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
- Call `Destroy` before re-initializing for multiple configurations

> Full test patterns: [references/unit-test-patterns.md](references/unit-test-patterns.md)

## Alternative: Direct Get Connectors (F64 Types)

When input types contain F64 fields (Packed_F64x3, Long_Float), use **direct get connectors** instead of data dependencies to avoid the F64 packed type endian bug.

Key differences:
- Component YAML: `return_type: Type.T` + `kind: get` (NOT `type:` + `kind: request`)
- No `data_dependencies.yaml` file
- Implementation: `Self.Input_T_Get` directly instead of dependency fetch
- Tester needs manual field + return function override

> Full patterns: [references/direct-connectors.md](references/direct-connectors.md)

## Known Issues and Workarounds

### Packed_F64x3 Endian Bug
On little-endian systems, `.C.Unpack(T)` and `.C.To_C(U)` produce CONSTRAINT_ERROR for F64 arrays. Workaround: manual field-by-field copy through native `U` type.

### Init Parameter Types
Use `Short_Float` (not `Packed_F32.T`) for scalar init parameters. Packed types as init params generate code with literal float defaults that don't type-check.

### Interfaces.C Boolean Ambiguity
`use Interfaces.C;` at body level makes `False` ambiguous. Use qualified `Interfaces.C.C_float(...)` calls instead of `use` clause.

### Data Product Buffer Size Limit
The framework `data_product_header.record.yaml` hardcodes `Buffer_Length` as `format: U8`, capping `data_product_buffer_size` at 255. If you change `data_product_buffer_size`, you must: `redo clear_cache` + `redo clean` on `adamant/src/types/data_product/` + `redo clean_all`.

## Reference Corpus

- [references/c-shim-patterns.md](references/c-shim-patterns.md) -- C shim templates, shared types, Eigen conversion
- [references/ada-binding-transforms.md](references/ada-binding-transforms.md) -- h2ads transformation rules, before/after example
- [references/type-system.md](references/type-system.md) -- Packed record YAML patterns (consolidated)
- [references/yaml-templates.md](references/yaml-templates.md) -- Component YAML templates (consolidated)
- [references/implementation-patterns.md](references/implementation-patterns.md) -- Ada implementation with/without parameters
- [references/unit-test-patterns.md](references/unit-test-patterns.md) -- Test templates, common pitfalls
- [references/direct-connectors.md](references/direct-connectors.md) -- Direct get connectors, F64 endian workaround (consolidated)

## Related Skills

- **Type system**: [adamant-type-system](../adamant-type-system/SKILL.md) -- packed record creation for C interop types
- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md) -- component YAML and implementation patterns  
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md) -- Ada binding generation via h2ads