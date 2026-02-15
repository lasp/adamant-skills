---
name: adamant-algorithm-wrapping
description: Complete pipeline for wrapping C++ algorithms into Adamant passive components with C shims, Ada bindings, and unit tests. Use when integrating external C/C++ code, creating FFI boundaries, or building Adamant components around existing algorithm libraries.
---

# Adamant Algorithm Wrapping Pipeline

```
C++ Algorithm → C Shim (.h/.cpp) → Ada Bindings (.ads) → Packed Records → Component YAML → Implementation → Tests
```

## 1. C Shim Pattern

### File Structure
- `<algo>Algorithm_c.h` -- Pure C header (no C++ keywords)
- `<algo>Algorithm_c.cpp` -- C shim implementation (uses `reinterpret_cast`)
- `msgPayloadDef/<Type>MsgF32Payload.h` -- Shared POD structs (included by both C++ algo and C shim)

### Opaque Handle Pattern
Every wrapped algorithm uses an opaque forward-declared struct as its handle. The header declares `typedef struct FooAlgorithm FooAlgorithm;` with lifecycle (`create`/`destroy`), core `update`, and setter/getter functions inside `extern "C"` guards.

> Full template: [references/code-templates.md §1 -- Opaque Handle Pattern](references/code-templates.md#opaque-handle-pattern-header)

### C Shim Implementation
The `.cpp` file includes both the C header and C++ class header. Each function casts via `reinterpret_cast<::FooAlgorithm*>(self)` and delegates to the C++ method.

> Full template: [references/code-templates.md §1 -- C Shim Implementation](references/code-templates.md#c-shim-implementation)

### POD Conversion for Eigen Types
Eigen types cannot cross the C boundary. Use flat POD structs (e.g., `struct { float data[3]; } Vector3f_c`) and convert at the boundary in the `.cpp` shim.

> Full template: [references/code-templates.md §1 -- POD Conversion](references/code-templates.md#pod-conversion-for-eigen-types)

### Shared Payload Structs
Payload structs live in `msgPayloadDef/` and are pure C POD. Both C++ algorithm internals and C shim include them directly. These map 1:1 to Adamant YAML record types.

> Full template: [references/code-templates.md §1 -- Shared Payload Struct](references/code-templates.md#shared-payload-struct-example)

### Constant Export Pattern
Export `#define` or `constexpr` constants via getter functions (never `static inline`):
```c
uint32_t FooAlgorithm_getMaxCount(void);
```

## 2. Ada Binding Spec

### h2ads Workflow
```bash
h2ads --compiler gcc -I <algorithms_dir> -b <algo_dir> <algo>Algorithm_c.h
```
The generated spec requires manual cleanup:

### Transformation Rules (h2ads → hand-written)
1. **Package rename:** `Foo_Algorithm_C_H` → `Foo_Algorithm_C`
2. **Opaque handle → limited private:** `type Foo_Algorithm is limited private;` with `null record` in private part
3. **Function rename:** Strip algorithm prefix. `Foo_Algorithm_Create` → `Create`
4. **Payload types:** Replace h2ads-generated C structs with Adamant `.C.U_C` types
5. **Access parameters:** Use `Type.C.U_C_Access` for pointer args (already defined by Adamant type system)
6. **Style/warning suppression:** Add pragmas at top and bottom

> Full template: [references/code-templates.md §2 -- Complete Ada Binding Spec](references/code-templates.md#complete-ada-binding-spec)

### Constant Validation in Ada
Validate C-side constants match Ada-side definitions at elaboration using `pragma Assert` on imported getter functions.

> Full template: [references/code-templates.md §2 -- Constant Validation](references/code-templates.md#constant-validation)

## 3. Type Mapping

### C/C++ → Ada Type Table

| C/C++ Type | Ada Type | YAML Format | Notes |
|---|---|---|---|
| `float` | `Short_Float` | `F32` | Most algorithm values |
| `double` | `Long_Float` | `F64` | Rare in F32 algorithms |
| `uint8_t` | `Interfaces.Unsigned_8` | `U8` | |
| `uint16_t` | `Interfaces.Unsigned_16` | `U16` | |
| `uint32_t` | `Interfaces.Unsigned_32` | `U32` | |
| `int32_t` | `Interfaces.Integer_32` | `I32` | |
| `uint64_t` | `Interfaces.Unsigned_64` | `U64` | Time stamps |
| `float[3]` | `Packed_F32x3.T` | -- | Vectors (3D) |
| `float[4]` | `Packed_F32x4.T` | -- | Quaternions |
| `float[9]` | `Packed_F32x9.T` | -- | 3×3 matrices (row-major) |
| `Eigen::Vector3f` | `Packed_F32x3.T` | -- | Via `Vector3f_c` POD shim |
| `Eigen::Matrix3f` | `Packed_F32x9.T` | -- | Via flat `float[9]` POD |
| `bool` | `Interfaces.C.unsigned_char` | -- | C `_Bool` maps oddly; use int |
| Payload struct | Custom `.record.yaml` | -- | 1:1 field mapping |

### Type Conversion Chain
```
Packed.T (wire format) → Unpack → .U (Ada record) → .C.To_C → .C.U_C (C-compatible)
```
Reverse: `.C.To_Ada → Pack → .T`

`.C.U_C` and `.C.U_C_Access` only exist for types with an explicit `-c.ads` child package (auto-generated from YAML records). For custom YAML records, use `access constant Type.T` in binding specs only if no `.C` package exists.

### Field Naming Convention
C `camelCase` → Ada `Pascal_Case` with underscores. `sigma_BN` → `Sigma_Bn`, `timeTag` → `Time_Tag`, `omega_RN_B` → `Omega_Rn_B`.

### YAML Record from C Struct
```yaml
# /* typedef struct { float timeTag; float r_BN_N[3]; } NavTransPayload; */
fields:
  - name: Time_Tag
    type: Short_Float
    format: F32
    description: "[s] Time tag"
  - name: R_Bn_N
    type: Packed_F32x3.T
    description: "[m] Position vector in inertial frame"
```

### Check Existing Types First
- `adamant/src/types/packed_arrays/` -- `Packed_F32x3`, `Packed_F32x9`, etc.
- `adamant/src/types/` -- `Packed_F32`, `Packed_U32`, etc.
- Project `src/types/` -- Domain-specific records (`att_guid.record.yaml`, `nav_att.record.yaml`, etc.)

## 4. Component YAML Model

### Basic Wrapper (no parameters)
`execution: passive` with connectors: `recv_sync` (Tick.T), `request` (Data_Product_Fetch.T → Data_Product_Return.T), `send` (Data_Product.T).

### Optional Connectors
- **Parameters**: Add `modify` connector (Parameter_Update.T) + parameters YAML
- **Events**: Add `send` connector (Event.T)
- **System Time**: Add `get` connector with `return_type: Sys_Time.T` (NOT `type:`)

Note: `get` connectors use `return_type:` only, NOT `type:`.

### Data Dependencies YAML
List `data_dependencies:` with `name`, `type` (e.g., `Att_Ref.T`), and `description`.

### Parameters YAML
List `parameters:` with `name`, `type` (e.g., `Packed_F32.T`), `default` (Ada aggregate syntax), and `description`.

## 5. Memory Management

### Create/Destroy Lifecycle
All wrapped algorithms use heap allocation via C shim:
```ada
Self.Alg := Create;   -- In Init: calls C++ new via shim
Destroy (Self.Alg);   -- In Destroy: calls C++ delete via shim
```
The component record holds `Alg : Foo_Algorithm_Access := null;` (pointer, initialized to null).

### Stack vs Heap
- **Algorithm instance**: Always **heap** (C++ `new`/`delete` via shim). Adamant components can't stack-allocate C++ objects.
- **Input/output payloads**: Always **stack**. Declared as local variables in `Tick_T_Recv_Sync`, converted via `To_C`/`To_Ada` in place.
- **Access parameters**: Use `'Unchecked_Access` on stack-local `aliased` variables to pass pointers to C functions. These pointers are valid only for the duration of the call.

```ada
-- Stack-allocated, passed by pointer to C:
Ref_C : aliased Att_Ref.C.U_C := Att_Ref.C.To_C (Att_Ref.Unpack (Ref));
Result := Update (Self.Alg, Ref_C'Unchecked_Access);
```

### Destroy is NOT Automatic
Adamant has no destructor mechanism. Components with C++ handles MUST:
1. Declare a `not overriding procedure Destroy` in the spec
2. Call it in test `Tear_Down_Test`
3. Call it in assembly shutdown (if applicable)

## 6. Implementation Pattern

The implementation spec declares `Instance` extending `Base_Instance` with a private `Alg` handle, overriding `Init`, `Tick_T_Recv_Sync`, `Get_Data_Dependency`, and `Invalid_Data_Dependency`. A `not overriding procedure Destroy` handles C++ cleanup.

> Full spec template: [references/code-templates.md §6 -- Spec](references/code-templates.md#spec)

### Body -- Basic Wrapper
`Init` calls `Create`, `Tick_T_Recv_Sync` fetches dependencies, converts to C types via `To_C`, calls `Update`, converts back via `To_Ada`, and sends the data product. `Invalid_Data_Dependency` asserts False.

> Full body template: [references/code-templates.md §6 -- Body -- Basic Wrapper](references/code-templates.md#body--basic-wrapper)

### Body -- With Parameters
Add `Parameter_Update_T_Modify` (delegates to `Process_Parameter_Update`) and `Update_Parameters_Action` (pushes parameter values to C++ via setters). Call `Self.Update_Parameters` at the top of `Tick_T_Recv_Sync`.

> Full template: [references/code-templates.md §6 -- Body -- With Parameters](references/code-templates.md#body--with-parameters-rate-control-pattern)

### Algorithm_Wrapper_Util
Shared utility: `Is_Dep_Status_Success` returns True for Success, False for Not_Available/Stale, asserts False for Error.

> Full template: [references/code-templates.md §6 -- Algorithm_Wrapper_Util](references/code-templates.md#algorithm_wrapper_util)

## 7. Input Strategy: Parameters vs Data Dependencies

| Mechanism | Connector | Use For | Staleness |
|---|---|---|---|
| **Parameters** | `modify` (Parameter_Update.T) | Fixed config, tunable gains | N/A |
| **Data Dependencies** | `request` (Data_Product_Fetch.T) | Dynamic telemetry from other components | Checked each tick |
| **Direct input** | `recv_sync` (custom type) | If algorithm IS the data source | N/A |

- **Stateful algorithms**: Track config state, call `Algorithm_Reset` in `Update_Parameters_Action` if parameters change algorithm mode.
- **Multiple dependencies**: Check ALL statuses before calling algorithm. Use `and then` (short-circuit) for combining.

## 8. Error Handling Across FFI Boundary

### Data Dependency Failures
```ada
if Is_Dep_Status_Success (Status_A) and then Is_Dep_Status_Success (Status_B) then
   -- Call algorithm
else
   null;  -- Skip this tick; algorithm runs on next successful fetch
end if;
```

### Invalid Data Dependency Handler
Every wrapper MUST implement this -- asserts False since invalid IDs indicate a configuration bug:
```ada
overriding procedure Invalid_Data_Dependency (...) is
   pragma Annotate (GNATSAS, Intentional, "subp always fails", "intentional assertion");
begin
   pragma Assert (False);
end Invalid_Data_Dependency;
```

### Invalid Parameter Handler (for parameterized components)
Same pattern as above with `Invalid_Parameter`.

### C++ Exception Safety
C++ algorithms MUST NOT throw exceptions across the FFI boundary. The C shim layer is the firewall. If the C++ algorithm can throw, catch in the `.cpp` shim and return an error code or sentinel value. Ada has no mechanism to catch C++ exceptions.

### Send Dropped Handlers
Every `send` connector requires a `*_Send_Dropped` override (typically `is null` for wrappers).

## 9. Build Integration

### C++ Side (fp32-fsw-xmera)
C++ algorithms are built separately via CMake into a static library (`libAlgorithms.a`):
```cmake
# algorithms/attTrackingError/CMakeLists.txt
set(module "fp32.attTrackingErrorF32")
xmera_add_swig_module("${module}")
target_sources("${module}" PRIVATE
  attTrackingError.cpp
  attTrackingErrorAlgorithm.cpp
)
target_link_libraries("${module}" PRIVATE Eigen3::Eigen)
```

The C shim `.cpp` files are compiled as part of this library. The shared payload headers in `msgPayloadDef/` are included by both sides.

### Ada Side (adamant-xmera-components)
Adamant uses `redo` build system. The Ada binding `.ads` files live alongside the component. The pre-built C++ static library is linked at the `redo` ELF step:
```bash
redo all           # Compile Ada component
cd test/ && redo test  # Run tests (links against C++ library)
```

### Verifying Linkage
```bash
nm libAlgorithms.a | grep FooAlgorithm_create
# Should show T (text/code) symbol
```

If symbols are missing, the C shim wasn't compiled into the library, or `extern "C"` was forgotten.

## 10. Testing Wrapped Components

### Test Structure
```
component_dir/
  test/
    test.adb                          -- Test driver (auto-generated)
    foo_tests-implementation.adb      -- Test cases
    component-foo-implementation-tester.adb  -- Tester glue (auto-generated)
```

### Test Lifecycle
`Set_Up_Test` calls `Init_Base`, `Connect`, `Init`, `Set_Up`. `Tear_Down_Test` calls `Destroy` then `Final_Base`.

> Full template: [references/code-templates.md §10 -- Test Lifecycle](references/code-templates.md#test-lifecycle)

### Writing Test Cases
Set data dependencies on tester fields, tick the component via `Tick_T_Send`, then verify output via history connectors with epsilon-tolerant assertions.

> Full template: [references/code-templates.md §10 -- Writing Test Cases](references/code-templates.md#writing-test-cases)

### Key Testing Rules
- Use `T.System_Time` for tick timestamps -- `(0, 0)` causes staleness failures
- Use `Epsilon` for floating-point comparisons across FFI
- Array aggregates use bracket syntax: `[x, y, z]`
- The tester auto-generates history connectors for each data product
- Data dependency values are set directly on the tester record fields

### Verifying Parameter Updates
Set parameters on tester, send `Parameter_Update_T`, tick, and verify output reflects new values.

> Full template: [references/code-templates.md §10 -- Verifying Parameter Updates](references/code-templates.md#verifying-parameter-updates)

## 11. Common Pitfalls

- C `float` → `Short_Float` (F32), C `double` → `Long_Float` (F64). **Never swap.**
- Tick timestamp `(0, 0)` causes data dependency staleness failures
- `get` connector uses `return_type:` only, NOT `type:`
- Every `send` connector needs `*_Send_Dropped` override
- Check existing packed types before creating new ones
- Zero warnings required for safety-critical code
- Verify C++ library linkage: `nm libAlgorithms.a | grep <name>`
- Always call `Destroy` in `Tear_Down_Test` or you leak C++ heap memory
- `extern "C"` forgotten in shim header → linker errors (mangled names)
- Payload struct field order must match exactly between C and YAML record
- `pragma Assert (False)` handlers need `GNATSAS` annotation to suppress analysis warnings

## 12. Build & Style

```bash
redo all                # Compile component
cd test/ && redo test   # Run tests
redo style              # Style check before finalizing
```

See [adamant-style](../adamant-style/SKILL.md) for full style rules.

## 13. Real Examples (xmera-components)

| Component | Algorithm | Has Params | Dependencies |
|---|---|---|---|
| `attitude_tracking_error` | AttTrackingError | No (sigma_R0R set in Init) | att_ref, nav_att → att_guid |
| `rate_control` | RateControl | Yes (gain_P, inertia) | att_guid → torque_cmd |
| `inertial_3d` | Inertial3D | No | -- → att_ref |
| `ephem_nav_converter` | EphemNavConverter | No | ephemeris → nav_trans |
| `sun_search` | SunSearch | Yes | nav_att, css → sun_heading |
| `average_mimu_data` | AverageMimuData | Yes | mimu_data → averaged output |
| `stepper_motor_controller` | StepperMotor | Yes | commands → step outputs |

See [references/real-examples.md](references/real-examples.md) for full annotated code from these components.

## References
- [references/code-templates.md](references/code-templates.md) -- YAML, Ada, and CMake templates for each pipeline stage
- [references/c-shim-bindings.md](references/c-shim-bindings.md) -- C shim patterns and Ada binding generation details
- [references/implementation-details.md](references/implementation-details.md) -- Deep implementation patterns and edge cases
- [references/real-examples.md](references/real-examples.md) -- Annotated code from xmera-components
