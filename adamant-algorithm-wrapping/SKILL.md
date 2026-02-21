---
name: adamant-algorithm-wrapping
description: Complete pipeline for wrapping C++ algorithms into Adamant passive components with C shims, Ada bindings, and unit tests. Use when integrating external C/C++ code, creating FFI boundaries, or building Adamant components around existing algorithm libraries.
---

# Adamant Algorithm Wrapping Pipeline

```ada
C++ Algorithm -> C Shim (.h/.cpp) -> Ada Bindings (.ads) -> Packed Records -> Component YAML -> Implementation -> Tests
```

Seven deterministic steps. Each step has one correct output given the inputs. Follow in order.

**Pure C shortcut:** If the algorithm is already pure C (not C++), skip Step 1 entirely -- the C header IS the shim. Go directly to Step 2 (Ada Bindings) using `pragma Import (C, ...)` on the C function signatures. No `extern "C"` or `reinterpret_cast` needed.

## Project Directory Layout

C/C++ libraries live in subdirectories within or alongside the component directory. Each directory containing source files needs an `.all_path` marker (0-byte file) so redo discovers it.

```
src/components/my_component/
  my_component.component.yaml
  component-my_component-implementation.ads/.adb
  c_lib/                        # C/C++ source + C shim
    .all_path                   # Required for redo discovery
    algorithm.h / algorithm.c   # Pure C algorithm (or C++ original)
    algorithm_c.h / algorithm_c.cpp  # C shim (if wrapping C++)
    algorithm_c_h.ads           # Ada binding (hand-written or -fdump-ada-spec)
    c_dep/                      # Optional: C/C++ dependencies
      .all_path
      dependency.h / dependency.c
```

For **pure C** algorithms, the C source IS the library -- no shim needed. Place `.h`, `.c`, and `.ads` binding directly in the lib directory.

For **C++ with C shim**, both the original C++ and the C shim go in the same directory. The Ada binding imports from the C shim only.

The Ada binding file (`*_h.ads` or `*_c_h.ads`) uses `pragma Import (C, ...)` and `Convention => C_Pass_By_Copy` for struct types. It can be generated via `gcc -fdump-ada-spec` or hand-written.

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
```ada

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
cd /home/user/your_project/src/components/<component_name>
h2ads --compiler gcc \
  -I /home/user/fp32-fsw-xmera/algorithms \
  -b /home/user/fp32-fsw-xmera/algorithms/<algorithm_name> \
  /home/user/fp32-fsw-xmera/algorithms/<algorithm_name>/<algo>Algorithm_c.h
```ada

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
```ada

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
```ada

> Full templates with parameters: [references/component-yaml-templates.md](references/component-yaml-templates.md)

## Step 5: Generate Templates and Implement

```bash
cd src/components/<component_name>
redo templates
cp build/template/*.ad[sb] .
```ada

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
```ada

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
```ada

> Full implementation patterns: [references/implementation-patterns.md](references/implementation-patterns.md)

## C/C++ Compilation and Linking

**The Ada build system does NOT automatically compile `.c` or `.cpp` files** in component directories. C/C++ stub files must be compiled separately:

1. **Via CMake/Makefile**: Compile into a static library (e.g., `libgncAlgorithms.a`) and link via the project `.gpr` file
2. **Via project GPR**: Add the `.c` file to the project's GPR `Source_Dirs` or `Source_Files` and ensure `for Languages use ("Ada", "C");`

Without this step, you will get `undefined reference` linker errors for all C functions called from Ada bindings.

## Step 6: Build and Verify

```bash
cd src/components/<component_name>
redo
```ada

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
```ada

### Critical test rules

- ALWAYS use `T.System_Time` for Tick timestamp (NOT `(0, 0)`)
- Work with `.T` (packed) types, NOT `.U` (unpacked)
- Array aggregates: `[x, y, z]` NOT `(Value => [x, y, z])`
- Use T rename pattern: `T : ... renames Self.Tester;`
- Call `Destroy` before re-initializing for multiple configurations
- Select 3-5 representative cases from Python tests for integration validation

### C test stub pattern

For unit testing without the full C++ toolchain, create a pure C reimplementation of the algorithm's C shim API. The test stub provides the same function signatures but uses simplified math (or hardcoded outputs). Place in the component's test directory and link instead of the real library:

```c
// test/vec3_math_c_stub.c -- pure C, no C++ dependency
#include "vec3_math_c.h"
Vec3Math* vec3_math_create(void) { return (Vec3Math*)1; }  // dummy handle
void vec3_math_destroy(Vec3Math* self) { (void)self; }
void vec3_math_cross(Vec3Math* self, const float* a, const float* b, float* out) {
    out[0] = a[1]*b[2] - a[2]*b[1];  // real math, no C++ needed
    out[1] = a[2]*b[0] - a[0]*b[2];
    out[2] = a[0]*b[1] - a[1]*b[0];
}
```

This enables `redo test` without requiring the C++ algorithm library to be built or mounted.

> Full test templates and troubleshooting: [references/unit-test-patterns.md](references/unit-test-patterns.md)

## Simplified Wrapping: Flattened C Shim + Direct Ada Bindings

For algorithms with complex C++ types (Eigen matrices, message payload structs, std::array), the fastest approach skips h2ads entirely:

1. **C shim flattens all complex types to primitives** -- `float[]`, `int[]`, `double` at the boundary
2. **Ada bindings declare C arrays directly** -- `type Float_Array_Rw is array (0 .. 35) of aliased C_float;`
3. **Component converts between Packed types and C arrays** with explicit loops

This avoids needing `.C.U_C` types, `To_C`/`To_Ada` chains, and the entire xmera type infrastructure. Trade-off: manual conversion loops in the Ada body, but much simpler to get right.

### Example: RW-type algorithms (mrpFeedback, mrpSteering, rwMotorTorque, etc.)

```c
// C shim: flatten RW message types to simple arrays
void algo_update(Algo* self, const float sigma_BR[3], const float wheelSpeeds[RW_EFF_CNT],
                 const int wheelAvailability[RW_EFF_CNT], float torque_out[3]);
```

```ada
-- Ada binding: declare C array types directly
type Float_Array_3 is array (0 .. 2) of aliased C_float;
type Float_Array_Rw is array (0 .. Rw_Eff_Cnt - 1) of aliased C_float;
type Int_Array_Rw is array (0 .. Rw_Eff_Cnt - 1) of aliased int;
```

```ada
-- Component body: convert Packed -> C -> call -> C -> Packed
Cmd : constant Packed_F32x3.U := Packed_F32x3.Unpack (Self.Input_T_Get);
Input : constant Float_Array_3 := [C_float (Cmd (0)), C_float (Cmd (1)), C_float (Cmd (2))];
```ada

### When to use h2ads workflow vs flattened approach

- **h2ads**: When xmera-components already defines the packed types and `.C` child packages
- **Flattened**: When wrapping new algorithms, especially those with RW/thruster array types that would need many new packed record definitions

## Containing Shims in Project Repository

When wrapping xmera algorithms for a project, keep shims and wrapper components inside the project repo to avoid modifying the upstream xmera repos:

```
your_project/
  src/
    components/<component_name>/         # Adamant wrapper component
      <component_name>_algorithm_c.ads   # Ada bindings
      component-*-implementation.ads/adb # Implementation
    types/                               # Packed record YAMLs
  xmera_shims/                           # C shim files (local copy)
    <algorithm_name>/
      <algo>Algorithm_c.h
      <algo>Algorithm_c.cpp
```ada

The C++ algorithms remain read-only in `fp32-fsw-xmera/`. Only the C shims and Ada code live in the project.

## Alternative: Direct Get Connectors (Instead of Data Dependencies)

When input types contain F64 fields (Packed_F64x3, Long_Float), use **direct get connectors** instead of data dependencies to avoid the F64 packed type endian bug. See [references/direct-connector-patterns.md](references/direct-connector-patterns.md) for full patterns.

Key differences:
- Component YAML: `return_type: Type.T` + `kind: get` (NOT `type:` + `kind: request`)
- No `data_dependencies.yaml` file
- No `Algorithm_Wrapper_Util` or `Data_Product_Fetch.T` connector
- Tester needs manual field + return function override (generated tester returns uninitialized data)
- Implementation: `Self.Input_T_Get` directly instead of `Self.Get_Input_Name(Value => ...)`

## Known Issues and Workarounds

### Packed_F64x3 Endian Bug
On little-endian systems, `.C.Unpack(T)` and `.C.To_C(U)` produce CONSTRAINT_ERROR for F64 arrays. Workaround: manual field-by-field copy through native `U` type. See [references/direct-connector-patterns.md](references/direct-connector-patterns.md#f64-packed-type-endian-workaround).

### Packed_F32.T Parameter Defaults
`Packed_F32.T` is a record `(Value => Short_Float)`. YAML defaults must use record syntax: `"(Value => 0.15)"`. For `Packed_F32x3.T` (array), use `"[others => 0.0]"` (brackets, not parentheses -- parentheses triggers obsolescent syntax warning).

### Init Parameter Types
Use `Short_Float` (not `Packed_F32.T`) for scalar init parameters. Packed types as init params generate code with literal float defaults that don't type-check.

### Interfaces.C Boolean Ambiguity
`use Interfaces.C;` at body level makes `False` ambiguous (both `Standard.False` and `Interfaces.C.C_bool` false). Use qualified `Interfaces.C.C_float(...)` calls instead of `use` clause. For assertions: `pragma Assert (Standard.False);`.

### Update Name Collision
If the C binding has an `Update` procedure and the component also has parameter update infrastructure, the name `Update` may collide with `Parameter_Enums.Update`. Qualify the call: `Algorithm_C.Update(Self.Alg, ...)`.

### Unsigned_64 Arithmetic
When computing `Call_Time` from `Sys_Time.T` fields, use `use Interfaces;` for clean arithmetic:
```ada
with Interfaces; use Interfaces;
...
Call_Time : constant Unsigned_64 := Unsigned_64 (Arg.Time.Seconds) * 1_000_000_000 + Unsigned_64 (Arg.Time.Subseconds);
```ada
Qualified `Interfaces.Unsigned_64(...)` without `use` can cause type mismatch errors on the `*` operator.

### Data Product Buffer Size Limit
The framework `data_product_header.record.yaml` hardcodes `Buffer_Length` as `format: U8`, capping `data_product_buffer_size` at 255. Large array types like `Packed_F32x36.T` (144 bytes) fit, but check your config before using large output types. If you change `data_product_buffer_size`, you must: `redo clear_cache` + `redo clean` on `adamant/src/types/data_product/` + `redo clean_all` on both framework and project.

### Singular Matrix in Zero-Config Algorithms
Algorithms using pseudo-inverse (e.g., rwNullSpace) will produce NaN if configured with zero effectors. Always initialize with at least a minimal valid configuration (e.g., 3 orthogonal wheels for rwNullSpace).

### Missing Utility Dependencies
Some algorithms (e.g., oeStateEphem) depend on utility libraries (`orbitalMotion.cpp`, `ephemerisUtilities.cpp`) not compiled in the base library. Check for undefined reference errors and compile missing sources into `libgncAlgorithms.a`.

### xmera Library Build (Freestanding Eigen)
The CMake freestanding build (`-include all_freestanding.hpp`) may fail with `std::complex` errors. Workaround: compile without the freestanding include header:
```bash
g++ -c -g -O0 -std=c++23 -fPIC -I algorithms -I . -I /path/to/eigen -I /path/to/xmera/src [file.cpp]
ar rcs build/linux-gcc-debug/lib/libgncAlgorithms.a build/linux-gcc-debug/obj/*.o
```
Note: `-I /path/to/xmera/src` needed for `<architecture/msgPayloadDef/RWAvailabilityMsgPayload.h>` and similar headers that live in the xmera repo, not fp32-fsw-xmera.

## Existing Reference Implementations

Before writing a new wrapper, check these repos for existing patterns:
- **fp32-fsw-xmera/algorithms/**: Existing C shims (`*_c.h`, `*_c.cpp`)
- **adamant-xmera-components/src/components/**: Existing Ada wrappers
- **adamant-xmera-components/src/types/**: Existing packed record types (att_guid, vehicle_config, etc.)
- **xmera/src/fswAlgorithms/**: Full C++ algorithm implementations

Reuse types from xmera-components when available (att_guid, att_ref, nav_att, nav_trans, vehicle_config, packed_f32x3_record, packed_f32x9).

## Reference Corpus

- [references/c-shim-patterns.md](references/c-shim-patterns.md) -- C shim templates, shared types, Eigen conversion
- [references/ada-binding-transforms.md](references/ada-binding-transforms.md) -- h2ads transformation rules, complete before/after example
- [references/packed-record-patterns.md](references/packed-record-patterns.md) -- YAML schema, type mapping, field naming
- [references/component-yaml-templates.md](references/component-yaml-templates.md) -- Component/dependency/product/parameter YAML
- [references/implementation-patterns.md](references/implementation-patterns.md) -- Ada implementation with/without parameters
- [references/unit-test-patterns.md](references/unit-test-patterns.md) -- Test templates, T rename, common pitfalls
- [references/direct-connector-patterns.md](references/direct-connector-patterns.md) -- Direct get connectors, F64 endian workaround, tester pattern

## Related Skills

- **Type system**: [adamant-type-system](../adamant-type-system/SKILL.md) -- packed record creation for C interop types
- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md) -- component YAML and implementation patterns
- **Testing**: [adamant-testing](../adamant-testing/SKILL.md) -- unit test patterns for wrapped components
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md) -- Ada binding generation via `-fdump-ada-spec`
