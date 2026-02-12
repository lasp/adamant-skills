---
name: adamant-algorithm-wrapping
description: Complete pipeline for wrapping C++ algorithms into Adamant passive components with C shims, Ada bindings, and unit tests
---

# Adamant Algorithm Wrapping Pipeline

Complete workflow from C++ algorithm to production Adamant component. The pipeline has 7 stages, each requiring specific patterns and validation.

## Overview Pipeline

```
C++ Algorithm -> C Shim -> Ada Bindings -> Packed Records -> Component YAML -> Implementation -> Unit Tests
```

**Locations:**
- **C++ algorithms:** `~/fp32-fsw-xmera/algorithms/<algorithm_name>/`
- **C shims:** Same directory as C++ algorithm
- **Ada components:** `~/adamant-xmera-components/src/components/<component_name>/`
- **Packed records:** `~/adamant-xmera-components/src/types/`

## Stage 1: C Shim Creation

### Critical Requirements

**Header purity:** `.h` files MUST be pure C (no C++ keywords, templates, or includes).

**DRY principle:** NEVER duplicate types between C++ and C. Create shared `*Types.h` headers:
```c
// Create fooTypes.h for shared definitions
#ifndef F32XIMERA_FOO_TYPES_H
#define F32XIMERA_FOO_TYPES_H

#define MAX_COUNT 10

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float param1;
    int param2;
} FooProperties;

#ifdef __cplusplus
}
#endif

#endif
```

**Include pattern:** C++ algorithm includes shared types header, C shim includes shared types header. No manual conversion code needed.

**Const correctness:** All input-only parameters MUST be declared `const`.

**Exception handling:** Do NOT catch exceptions in C shim. Let them propagate to Ada.

### File Structure

**Required files:**
- `<algorithm>Algorithm_c.h` - C shim header
- `<algorithm>Algorithm_c.cpp` - C shim implementation
- `<algorithm>Types.h` - Shared types (if needed)

**Opaque handle pattern:**
```c
// In C header
typedef struct FooAlgorithm FooAlgorithm;

FooAlgorithm* FooAlgorithm_create(void);
void FooAlgorithm_destroy(FooAlgorithm* self);
OutputPayload FooAlgorithm_update(FooAlgorithm* self,
                                  const InputPayload* input);
```

**POD conversion pattern (for Eigen types only):**
```c
typedef struct {
    float data[3];
} Vector3f_c;
```

**Constant validation pattern:**
```c
// Never static inline - must be linkable
uint32_t FooAlgorithm_getMaxCount(void);
```

### Implementation Patterns

**Lifecycle management:**
```cpp
FooAlgorithm* FooAlgorithm_create(void) {
    return reinterpret_cast<FooAlgorithm*>(new ::FooAlgorithm());
}

void FooAlgorithm_destroy(FooAlgorithm* self) {
    delete reinterpret_cast<::FooAlgorithm*>(self);
}
```

**Function call pattern:**
```cpp
OutputPayload FooAlgorithm_update(FooAlgorithm* self,
                                  uint64_t callTime,
                                  const InputPayload* input) {
    return reinterpret_cast<::FooAlgorithm*>(self)->update(callTime, *input);
}
```

**Eigen conversion (when needed):**
```cpp
void FooAlgorithm_setVector(FooAlgorithm* self, Vector3f_c vec) {
    Eigen::Vector3f eigenVec;
    eigenVec << vec.data[0], vec.data[1], vec.data[2];
    reinterpret_cast<::FooAlgorithm*>(self)->setVector(eigenVec);
}
```

### Validation

**Pre-commit compliance:** Run `pre-commit run --from develop --to HEAD` and fix all formatting issues.

## Stage 2: Ada Bindings Generation

### h2ads Tool Usage

**Command template:**
```bash
cd ~/adamant-xmera-components/src/components/<component_name>

h2ads --compiler gcc \
  -I ~/fp32-fsw-xmera/algorithms \
  -b ~/fp32-fsw-xmera/algorithms/<algorithm_name> \
  ~/fp32-fsw-xmera/algorithms/<algorithm_name>/<algorithm_name>Algorithm_c.h
```

**Critical flags:**
- `--compiler gcc` - Required for system headers
- `-I` parent directory - Finds `msgPayloadDef/` subdirectory
- `-b` algorithm directory - Sets scope boundary

**Clean up generated files:**
Delete ALL generated files EXCEPT the algorithm binding (`<algorithm_name>_algorithm_c_h.ads`).

### Transformation Rules

**Package naming:**
```ada
-- h2ads output
package Foo_Algorithm_C_H is

-- Transform to
package Foo_Algorithm_C is
```

**Type visibility:**
```ada
-- WRONG (h2ads output)
type Foo_Algorithm is null record;

-- CORRECT (Adamant style)
type Foo_Algorithm is limited private;
type Foo_Algorithm_Access is access all Foo_Algorithm;

private
   type Foo_Algorithm is null record;
```

**Function naming:**
```ada
-- h2ads output
function Foo_Algorithm_Create return access Foo_Algorithm;

-- Transform to
function Create return Foo_Algorithm_Access;
```

### Payload Type Mapping

**System mapping table:**
```ada
-- h2ads -> Adamant
Nav_Att_Msg_F32_Payload_H.Nav_Att_Msg_F32_Payload -> Nav_Att.C.U_C
Nav_Trans_Msg_F32_Payload_H.Nav_Trans_Msg_F32_Payload -> Nav_Trans.C.U_C
Ephemeris_Msg_F32_Payload_H.Ephemeris_Msg_F32_Payload -> Ephemeris.C.U_C
```

**With clause transformation:**
```ada
-- h2ads output
with Nav_Att_Msg_F32_Payload_H;

-- Transform to
with Nav_Att.C;
```

### Constant Validation Pattern

**CRITICAL:** Use runtime validation for ALL `#define` constants:
```ada
-- Define constant with comment
NUM_SLEWS : constant := 3;

-- Import validation function
function Get_Num_Slews return Unsigned_32
  with Import => True, Convention => C,
       External_Name => "FooAlgorithm_getNumSlews";

-- Runtime validation at elaboration
pragma Assert (Unsigned_32 (NUM_SLEWS) = Get_Num_Slews);
```

### C POD Type Replacement

**CRITICAL RULE:** DELETE all h2ads-generated C struct types. Convert to Adamant packed records.

**Identify types to replace:**
- `Vector3f_C` (Eigen POD helpers)
- Algorithm-specific structs from shared types headers
- Any struct used in algorithm API

**Replacement process:**
1. Check if packed record exists: `ls ~/adamant-xmera-components/src/types/<type_name>*.yaml`
2. If not, create packed record YAML (see Stage 3)
3. Replace in bindings: `with <Packed_Type>.C;`
4. Use `<Packed_Type>.C.U_C` in function signatures

## Stage 3: C Struct to Packed Record Conversion

### Type Mapping Rules

**Scalar types (require `format` field):**
```yaml
# C -> Adamant -> Format
float -> Short_Float -> F32
double -> Long_Float -> F64
uint32_t -> Interfaces.Unsigned_32 -> U32
int32_t -> Interfaces.Integer_32 -> I32
```

**Array types (NO `format` field):**
```yaml
# C -> Adamant
float[3] -> Packed_F32x3.T
double[3] -> Packed_F64x3.T
float[9] -> Packed_F32x9.T
```

**NEVER use `Natural` for unsigned C integers** - use `Interfaces.Unsigned_*`.

### Field Name Conversion

**Pascal_Case rules:**
- Capitalize ONLY first letter of each word
- Join with underscores
- Single letters stay uppercase

**Examples:**
```yaml
# C field -> Ada field
sigma_BN -> Sigma_Bn      # NOT Sigma_BN
omega_BN_B -> Omega_Bn_B  # NOT Omega_BN_B
timeTag -> Time_Tag
```

### YAML Structure

```yaml
---
#  /*! Original C struct comment preserved as reference */
#  typedef struct {
#      float timeTag;
#      float r_BN_N[3];
#  } SomeStruct;
fields:
  - name: Time_Tag
    type: Short_Float
    format: F32
    description: "[s] Time tag"
  - name: R_Bn_N
    type: Packed_F32x3.T
    description: "[m] Position vector"
```

**Critical points:**
- Comment entire C struct with `#  ` prefix
- Use 2-space indentation
- Array types do NOT include `format` field
- Preserve field order from C struct

## Stage 4: Component YAML Models

### Component Model Pattern

**Basic wrapper component:**
```yaml
---
description: Algorithm computes X from Y inputs.
execution: passive
init:
  description: Initializes the algorithm.
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

**With parameters (add this connector):**
```yaml
  - description: The parameter update connector.
    type: Parameter_Update.T
    kind: modify
```

### Data Dependencies Model

**CRITICAL:** Check buffer size constraint. Data dependencies must fit in `data_product_buffer_size` (typically 128 bytes) from `adamant_xmera_components.configuration.yaml`.

```yaml
---
description: Data dependencies for the Component.
data_dependencies:
  - name: Algorithm_Input_1
    type: Nav_Att.T
    description: Navigation attitude state
  - name: Algorithm_Input_2  
    type: Ephemeris.T
    description: Ephemeris data
```

### Data Products Model

```yaml
---
description: Data products for the Component.
data_products:
  - name: Algorithm_Output
    type: Nav_Att.T
    description: Computed navigation solution.
```

### Parameters Model (Optional)

**Create ONLY if algorithm has configuration values that change infrequently.**

```yaml
---
description: Parameters for the Component.
parameters:
  - name: Control_Gain
    description: "[rad/s] Proportional control gain"
    type: Packed_F32.T
    default: "(Value => 0.0)"
  - name: Inertia_Matrix
    description: "[kg m^2] Spacecraft inertia (3x3 row-major)"
    type: Packed_F32x9.T
    default: "[others => 0.0]"
```

**Configuration note:** Ensure `parameter_buffer_size` in config is >= largest parameter size.

## Stage 5: Component Implementation

### Specification Pattern

```ada
with <Algorithm_Name>_C; use <Algorithm_Name>_C;

package Component.<Component_Name>.Implementation is
   type Instance is new <Component_Name>.Base_Instance with private;

   overriding procedure Init (Self : in out Instance);
   not overriding procedure Destroy (Self : in out Instance);

private
   type Instance is new <Component_Name>.Base_Instance with record
      Alg : <Algorithm_Name>_Access := null;
   end record;
```

### Implementation Patterns

**Required with clauses:**
```ada
with <Input_Type>.C;
with <Output_Type>.C;
with Algorithm_Wrapper_Util;  -- For Is_Dep_Status_Success
```

**Lifecycle management:**
```ada
overriding procedure Init (Self : in out Instance) is
begin
   Self.Alg := Create;
end Init;

not overriding procedure Destroy (Self : in out Instance) is
begin
   Destroy (Self.Alg);
end Destroy;
```

**Main algorithm execution:**
```ada
overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
   use Algorithm_Wrapper_Util;
   use Data_Product_Enums.Data_Dependency_Status;
   
   Input_1 : Input_Type.T;
   Input_1_Status : constant Data_Dependency_Status.E :=
      Self.Get_Input_1 (Value => Input_1, Stale_Reference => Arg.Time);
begin
   -- Update parameters if component has them
   Self.Update_Parameters;  -- ONLY if parameters exist
   
   if Is_Dep_Status_Success (Input_1_Status) then
      declare
         Input_1_C : constant Input_Type.C.U_C := 
            Input_Type.C.To_C (Input_Type.Unpack (Input_1));
         Output : constant Output_Type.C.U_C := 
            Update (Self.Alg, Input_1_C'Unchecked_Access);
      begin
         Self.Data_Product_T_Send (Self.Data_Products.Algorithm_Output (
            Arg.Time, Output_Type.Pack (Output_Type.C.To_Ada (Output))
         ));
      end;
   end if;
end Tick_T_Recv_Sync;
```

**Parameter handling (if parameters exist):**
```ada
overriding procedure Update_Parameters_Action (Self : in out Instance) is
begin
   Set_Control_Gain (Self.Alg, Self.Control_Gain.Value);
   -- For arrays: Packed_F32x9.C.To_C (Self.Inertia_Matrix)
end Update_Parameters_Action;
```

### Error Handlers

**Invalid data dependency (always include):**
```ada
overriding procedure Invalid_Data_Dependency 
  (Self : in out Instance; Id : in Data_Product_Types.Data_Product_Id;
   Ret : in Data_Product_Return.T) is
   pragma Annotate (GNATSAS, Intentional, "subp always fails", "intentional assertion");
begin
   pragma Assert (False);
end Invalid_Data_Dependency;
```

**Invalid parameter (if parameters exist):**
```ada
overriding procedure Invalid_Parameter 
  (Self : in out Instance; Par : in Parameter.T;
   Errant_Field_Number : in Unsigned_32;
   Errant_Field : in Basic_Types.Poly_Type) is
   pragma Annotate (GNATSAS, Intentional, "subp always fails", "intentional assertion");
begin
   pragma Assert (False);
end Invalid_Parameter;
```

## Stage 6: Unit Testing

### Prerequisites

**Build path inclusion:**
```bash
touch .all_path  # In component directory
```

**fp32-fsw-xmera integration:** Add algorithm to `CMakeLists.txt` and rebuild library.

**Test environment:**
```python
# test/env.py
from environments import test
```

### Test Model

```yaml
---
description: Unit test suite for the Component.
tests:
  - name: Test
    description: Run algorithm to ensure integration is sound.
```

### Template Generation

```bash
cd test/
redo templates
cp build/template/*.ad[sb] .
```

### Test Implementation Pattern

**Critical patterns:**
- Use **T rename** for concise code
- Work with **`.T` packed types**, NOT `.U` unpacked types
- Use **`T.System_Time`** for Tick timestamp (never `(0, 0)`)
- Array aggregates use **`[x, y, z]`** not `(Value => [x, y, z])`

```ada
overriding procedure Test (Self : in out Instance) is
   T : Component.<Component_Name>.Implementation.Tester.Instance_Access renames Self.Tester;

   type Test_Vector is record
      Input_1 : Input_Type.T;
      Expected_Output : Output_Type.T;
   end record;

   Test_Cases : constant array (1 .. 3) of Test_Vector := [
      (Input_1 => (Field_1 => [1.0, 0.0, 0.0], ...),
       Expected_Output => (Field_1 => [0.0, 1.0, 0.0], ...)),
      -- ... more test cases from Python reference
   ];
begin
   for I in Test_Cases'Range loop
      T.Input_1 := Test_Cases (I).Input_1;
      
      T.Tick_T_Send ((Time => T.System_Time, Count => 0));
      
      Natural_Assert.Eq (T.Algorithm_Output_History.Get_Count, I);
      
      declare
         Output : constant Output_Type.T := T.Algorithm_Output_History.Get (I);
      begin
         Output_Type_Assert.Eq (Output, Test_Cases (I).Expected_Output, Epsilon => 0.0001);
      end;
   end loop;
end Test;
```

## Stage 7: Build Validation

### Compilation Requirements

**ZERO warnings policy:** Safety-critical code must compile without warnings.

```bash
cd component_directory/
redo                  # Must succeed with zero warnings
redo test            # Unit tests must pass
redo style           # No style violations
```

**Common warning fixes:**
- Remove unused `with` clauses
- Change variables to `constant` where possible
- Use `[]` array syntax, not `()`

### Integration Validation

**Test C++ library linkage:**
```bash
nm ~/fp32-fsw-xmera/build/linux-gcc-debug/lib/libgncAlgorithms.a | grep <algorithm_name>
```

**Verify generated types exist:**
```bash
ls ~/adamant-xmera-components/src/types/<packed_type>*.ads
```

## Common Pitfalls

**C struct duplication:** Creating separate Ada packages for C structs instead of packed records. Always use packed records for C structs.

**Type precision mismatch:** Using F64 for C `float` types. C `float` -> `Short_Float` (F32), C `double` -> `Long_Float` (F64).

**Wrong array syntax:** Using `(Value => [...])` for Packed_F32x3.T fields. Use direct arrays: `[x, y, z]`.

**Missing validation:** Not using `pragma Assert` for constant validation. Always validate `#define` constants at elaboration time.

**Tick timestamp errors:** Using `(0, 0)` for Tick time instead of `T.System_Time`. Causes data dependency staleness issues.

**Build path omission:** Forgetting `.all_path` file causes template generation failures.

**Library integration:** Not adding algorithm to CMakeLists.txt causes linking failures.

## Reference Implementations

**Complete examples:**
- `~/adamant-xmera-components/src/components/attitude_tracking_error/` (Eigen vectors)
- `~/adamant-xmera-components/src/components/rate_control/` (parameters)
- `~/adamant-xmera-components/src/components/sunline_ephem/` (basic wrapper)

**C shim examples:**
- `~/fp32-fsw-xmera/algorithms/sunSearch/` (shared types header pattern)
- `~/fp32-fsw-xmera/algorithms/attTrackingError/` (Eigen conversion pattern)