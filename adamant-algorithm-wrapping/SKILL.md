---
name: adamant-algorithm-wrapping
description: Complete pipeline for wrapping C++ algorithms into Adamant passive components with C shims, Ada bindings, and unit tests
---

# Adamant Algorithm Wrapping Pipeline

```
C++ Algorithm → C Shim (.h/.cpp) → Ada Bindings (.ads) → Packed Records → Component YAML → Implementation → Tests
```

## 1. C Shim Pattern

### File Structure
- `<algo>Algorithm_c.h` — Pure C header (no C++ keywords)
- `<algo>Algorithm_c.cpp` — C shim implementation (uses `reinterpret_cast`)
- `msgPayloadDef/<Type>MsgF32Payload.h` — Shared POD structs (included by both C++ algo and C shim)

### Opaque Handle Pattern
Every wrapped algorithm uses an opaque forward-declared struct as its handle:

```c
// Header (.h)
#ifdef __cplusplus
extern "C" {
#endif

typedef struct FooAlgorithm FooAlgorithm;

// Lifecycle
FooAlgorithm* FooAlgorithm_create(void);
void FooAlgorithm_destroy(FooAlgorithm* self);

// Core update
OutputPayload FooAlgorithm_update(FooAlgorithm* self, const InputPayload* input);

// Setters/getters for tunable parameters
void FooAlgorithm_setGainP(FooAlgorithm* self, float p);
float FooAlgorithm_getGainP(FooAlgorithm* self);

// Reset (for stateful algorithms)
void FooAlgorithm_reset(FooAlgorithm* self, uint64_t callTime);

#ifdef __cplusplus
}
#endif
```

### C Shim Implementation
```cpp
// Implementation (.cpp)
#include "fooAlgorithm_c.h"
#include "fooAlgorithm.h"  // C++ class header
#include <Eigen/Core>

FooAlgorithm* FooAlgorithm_create(void) {
    return reinterpret_cast<FooAlgorithm*>(new ::FooAlgorithm());
}

void FooAlgorithm_destroy(FooAlgorithm* self) {
    delete reinterpret_cast<::FooAlgorithm*>(self);
}

OutputPayload FooAlgorithm_update(FooAlgorithm* self, const InputPayload* input) {
    return reinterpret_cast<::FooAlgorithm*>(self)->update(*input);
}
```

### POD Conversion for Eigen Types
Eigen types cannot cross the C boundary. Use flat POD structs:

```c
typedef struct { float data[3]; } Vector3f_c;

// In .cpp, convert at boundary:
void FooAlgorithm_setVector(FooAlgorithm* self, Vector3f_c vec) {
    Eigen::Vector3f v;
    v << vec.data[0], vec.data[1], vec.data[2];
    reinterpret_cast<::FooAlgorithm*>(self)->setVector(v);
}

Vector3f_c FooAlgorithm_getVector(FooAlgorithm* self) {
    Eigen::Vector3f v = reinterpret_cast<::FooAlgorithm*>(self)->getVector();
    Vector3f_c out;
    out.data[0] = v[0]; out.data[1] = v[1]; out.data[2] = v[2];
    return out;
}
```

### Shared Payload Structs
Payload structs live in `msgPayloadDef/` and are pure C POD. Both C++ algorithm internals and C shim include them directly. These map 1:1 to Adamant YAML record types.

```c
// msgPayloadDef/AttGuidMsgF32Payload.h
typedef struct {
    float sigma_BR[3];
    float omega_BR_B[3];
    float omega_RN_B[3];
    float domega_RN_B[3];
} AttGuidMsgF32Payload;
```

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
2. **Opaque handle → limited private:**
   ```ada
   type Foo_Algorithm is limited private;
   type Foo_Algorithm_Access is access all Foo_Algorithm;
   -- ...
   private
      type Foo_Algorithm is null record;
   ```
3. **Function rename:** Strip algorithm prefix. `Foo_Algorithm_Create` → `Create`
4. **Payload types:** Replace h2ads-generated C structs with Adamant `.C.U_C` types
5. **Access parameters:** Use `Type.C.U_C_Access` for pointer args (already defined by Adamant type system)
6. **Style/warning suppression:** Add pragmas at top and bottom

### Complete Ada Binding Spec Template
```ada
pragma Ada_2012;
pragma Style_Checks (Off);
pragma Warnings     (Off, "-gnatwu");

with Interfaces.C; use Interfaces; use Interfaces.C;
with Input_Type.C;
with Output_Type.C;

package Foo_Algorithm_C is

   type Foo_Algorithm is limited private;
   type Foo_Algorithm_Access is access all Foo_Algorithm;

   function Create return Foo_Algorithm_Access
     with Import => True, Convention => C,
          External_Name => "FooAlgorithm_create";

   procedure Destroy (Self : Foo_Algorithm_Access)
     with Import => True, Convention => C,
          External_Name => "FooAlgorithm_destroy";

   function Update
     (Self     : Foo_Algorithm_Access;
      Input_In : Input_Type.C.U_C_Access)
     return Output_Type.C.U_C
     with Import => True, Convention => C,
          External_Name => "FooAlgorithm_update";

   procedure Set_Gain_P (Self : Foo_Algorithm_Access; P : Short_Float)
     with Import => True, Convention => C,
          External_Name => "FooAlgorithm_setGainP";

private
   type Foo_Algorithm is null record;
end Foo_Algorithm_C;

pragma Style_Checks (On);
pragma Warnings     (On, "-gnatwu");
```

### Constant Validation in Ada
Validate C-side constants match Ada-side definitions at elaboration:
```ada
NUM_SLEWS : constant := 3;
function Get_Num_Slews return Unsigned_32
  with Import => True, Convention => C, External_Name => "FooAlgorithm_getNumSlews";
pragma Assert (Unsigned_32 (NUM_SLEWS) = Get_Num_Slews);
```

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
| `float[3]` | `Packed_F32x3.T` | — | Vectors (3D) |
| `float[4]` | `Packed_F32x4.T` | — | Quaternions |
| `float[9]` | `Packed_F32x9.T` | — | 3×3 matrices (row-major) |
| `Eigen::Vector3f` | `Packed_F32x3.T` | — | Via `Vector3f_c` POD shim |
| `Eigen::Matrix3f` | `Packed_F32x9.T` | — | Via flat `float[9]` POD |
| `bool` | `Interfaces.C.unsigned_char` | — | C `_Bool` maps oddly; use int |
| Payload struct | Custom `.record.yaml` | — | 1:1 field mapping |

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
- `adamant/src/types/packed_arrays/` — `Packed_F32x3`, `Packed_F32x9`, etc.
- `adamant/src/types/` — `Packed_F32`, `Packed_U32`, etc.
- Project `src/types/` — Domain-specific records (`att_guid.record.yaml`, `nav_att.record.yaml`, etc.)

## 4. Component YAML Model

### Basic Wrapper (no parameters)
```yaml
description: Wraps FooAlgorithm for attitude guidance computation.
execution: passive
init:
  description: Creates algorithm handle and sets initial config.
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
```

### With Runtime-Tunable Parameters
Add a `modify` connector and parameters YAML:
```yaml
connectors:
  # ... same as above, plus:
  - description: The parameter update connector.
    type: Parameter_Update.T
    kind: modify
```

### With Events
```yaml
connectors:
  # ... plus:
  - description: Events.
    type: Event.T
    kind: send
```

### With System Time
```yaml
connectors:
  # ... plus:
  - description: System time.
    return_type: Sys_Time.T
    kind: get
```
Note: `get` connectors use `return_type:` only, NOT `type:`.

### Data Dependencies YAML
```yaml
description: Data dependencies for Foo component.
data_dependencies:
  - name: Attitude_Reference
    type: Att_Ref.T
    description: Reference attitude for tracking
  - name: Navigation_Attitude
    type: Nav_Att.T
    description: Current navigation attitude estimate
```

### Parameters YAML
```yaml
description: Parameters for the Rate Control component
parameters:
  - name: Derivative_Gain_P
    description: "[N*m*s] Rate error feedback gain"
    type: Packed_F32.T
    default: "(Value => 0.0)"
  - name: Spacecraft_Inertia
    description: "[kg m^2] Spacecraft inertia (3x3 row-major)"
    type: Packed_F32x9.T
    default: "[others => 0.0]"
```

## 5. Memory Management

### Create/Destroy Lifecycle
All wrapped algorithms use heap allocation via C shim:

```ada
-- In Init:
Self.Alg := Create;  -- Calls C++ new via shim

-- In Destroy (must be called at teardown):
Destroy (Self.Alg);  -- Calls C++ delete via shim
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

### Spec
```ada
with Foo_Algorithm_C; use Foo_Algorithm_C;

package Component.Foo.Implementation is
   type Instance is new Foo.Base_Instance with private;
   overriding procedure Init (Self : in out Instance);
   not overriding procedure Destroy (Self : in out Instance);
private
   type Instance is new Foo.Base_Instance with record
      Alg : Foo_Algorithm_Access := null;
   end record;
   overriding procedure Set_Up (Self : in out Instance) is null;
   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T);
   overriding procedure Data_Product_T_Send_Dropped (Self : in out Instance; Arg : in Data_Product.T) is null;
   overriding function Get_Data_Dependency (Self : in out Instance; Id : in Data_Product_Types.Data_Product_Id)
     return Data_Product_Return.T is (Self.Data_Product_Fetch_T_Request ((Id => Id)));
   overriding procedure Invalid_Data_Dependency
     (Self : in out Instance; Id : in Data_Product_Types.Data_Product_Id; Ret : in Data_Product_Return.T);
end Component.Foo.Implementation;
```

### Body — Basic Wrapper
```ada
with Input_Type.C;
with Output_Type.C;
with Algorithm_Wrapper_Util;

package body Component.Foo.Implementation is

   overriding procedure Init (Self : in out Instance) is
   begin
      Self.Alg := Create;
   end Init;

   not overriding procedure Destroy (Self : in out Instance) is
   begin
      Destroy (Self.Alg);
   end Destroy;

   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
      use Data_Product_Enums.Data_Dependency_Status;
      use Algorithm_Wrapper_Util;
      Input_Dep : Input_Type.T;
      Status : constant Data_Dependency_Status.E :=
         Self.Get_My_Input (Value => Input_Dep, Stale_Reference => Arg.Time);
   begin
      if Is_Dep_Status_Success (Status) then
         declare
            Input_C : aliased Input_Type.C.U_C := Input_Type.C.To_C (Input_Type.Unpack (Input_Dep));
            Output_C : constant Output_Type.C.U_C := Update (Self.Alg, Input_C'Unchecked_Access);
         begin
            Self.Data_Product_T_Send (Self.Data_Products.Result (
               Arg.Time, Output_Type.Pack (Output_Type.C.To_Ada (Output_C))));
         end;
      end if;
   end Tick_T_Recv_Sync;

   overriding procedure Invalid_Data_Dependency (...) is
      pragma Annotate (GNATSAS, Intentional, "subp always fails", "intentional assertion");
   begin
      pragma Assert (False);
   end Invalid_Data_Dependency;

end Component.Foo.Implementation;
```

### Body — With Parameters (Rate Control Pattern)
```ada
overriding procedure Parameter_Update_T_Modify (Self : in out Instance; Arg : in out Parameter_Update.T) is
begin
   Self.Process_Parameter_Update (Arg);
end Parameter_Update_T_Modify;

overriding procedure Update_Parameters_Action (Self : in out Instance) is
begin
   Set_Gain_P (Self.Alg, Self.Gain_P.Value);
   -- Push all parameter values to C++ algorithm state
end Update_Parameters_Action;
```
Call `Self.Update_Parameters` at the top of `Tick_T_Recv_Sync` to apply staged params before each update cycle.

### Algorithm_Wrapper_Util
Shared utility for data dependency status checking:
```ada
function Is_Dep_Status_Success (Status : Data_Product_Enums.Data_Dependency_Status.E) return Boolean;
-- Returns True for Success, False for Not_Available/Stale, asserts False for Error
```

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
Every wrapper MUST implement this — asserts False since invalid IDs indicate a configuration bug:
```ada
overriding procedure Invalid_Data_Dependency (...) is
   pragma Annotate (GNATSAS, Intentional, "subp always fails", "intentional assertion");
begin
   pragma Assert (False);
end Invalid_Data_Dependency;
```

### Invalid Parameter Handler (for parameterized components)
Same pattern:
```ada
overriding procedure Invalid_Parameter (...) is
   pragma Annotate (GNATSAS, Intentional, "subp always fails", "intentional assertion");
begin
   pragma Assert (False);
end Invalid_Parameter;
```

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
# Compile Ada component
redo all

# Run tests (links against C++ library)
cd test/ && redo test
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
```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Init;  -- Creates C++ handle
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;

overriding procedure Tear_Down_Test (Self : in out Instance) is
begin
   Self.Tester.Component_Instance.Destroy;  -- Frees C++ handle
   Self.Tester.Final_Base;
end Tear_Down_Test;
```

### Writing Test Cases
```ada
overriding procedure Test (Self : in out Instance) is
   T : Component.Foo.Implementation.Tester.Instance_Access renames Self.Tester;
begin
   -- Set data dependencies (tester provides these):
   T.My_Input := (Sigma_Bn => [0.25, -0.45, 0.75], ...);

   -- Tick the component:
   T.Tick_T_Send ((Time => T.System_Time, Count => 0));

   -- Verify output data products:
   Natural_Assert.Eq (T.Data_Product_T_Recv_Sync_History.Get_Count, 1);
   Natural_Assert.Eq (T.Result_History.Get_Count, 1);
   Result_Assert.Eq (T.Result_History.Get (1), Expected_Value, Epsilon => 0.001);
end Test;
```

### Key Testing Rules
- Use `T.System_Time` for tick timestamps — `(0, 0)` causes staleness failures
- Use `Epsilon` for floating-point comparisons across FFI
- Array aggregates use bracket syntax: `[x, y, z]`
- The tester auto-generates history connectors for each data product
- Data dependency values are set directly on the tester record fields

### Verifying Parameter Updates
```ada
-- Set parameter, then tick:
T.Parameters := (Gain_P => (Value => 1.5), Inertia => [...]);
T.Parameter_Update_T_Send ((Operation => Set, Status => Success));
T.Tick_T_Send ((Time => T.System_Time, Count => 0));
-- Verify output reflects new parameter values
```

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
| `inertial_3d` | Inertial3D | No | — → att_ref |
| `ephem_nav_converter` | EphemNavConverter | No | ephemeris → nav_trans |
| `sun_search` | SunSearch | Yes | nav_att, css → sun_heading |
| `average_mimu_data` | AverageMimuData | Yes | mimu_data → averaged output |
| `stepper_motor_controller` | StepperMotor | Yes | commands → step outputs |

See [references/real-examples.md](references/real-examples.md) for full annotated code from these components.
