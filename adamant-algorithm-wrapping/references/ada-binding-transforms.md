# Ada Binding Transformation Rules

## h2ads to Adamant Transformation

### Package Naming
- Remove `_H` suffix: `Sunline_Ephem_Algorithm_C_H` -> `Sunline_Ephem_Algorithm_C`
- File: lowercase with underscores: `sunline_ephem_algorithm_c.ads`

### Function Naming
- Remove type name prefix: `Sunline_Ephem_Algorithm_Create` -> `Create`
- Ada-style: `Create`, `Destroy`, `Update_State`, `Set_Gain`, `Get_Gain`

### Type Visibility
```ada
-- PUBLIC section:
type Foo_Algorithm is limited private;
type Foo_Algorithm_Access is access all Foo_Algorithm;

-- PRIVATE section:
type Foo_Algorithm is null record;
```

Replace ALL `access Type_Name` with `Type_Name_Access`.

### Payload Type Mapping

| h2ads package | Adamant package | Type access | Type value |
|--------------|----------------|-------------|------------|
| `Nav_Att_Msg_F32_Payload_H` | `Nav_Att.C` | `Nav_Att.C.U_C_Access` | `Nav_Att.C.U_C` |
| `Nav_Trans_Msg_F32_Payload_H` | `Nav_Trans.C` | `Nav_Trans.C.U_C_Access` | `Nav_Trans.C.U_C` |
| `Ephemeris_Msg_F32_Payload_H` | `Ephemeris.C` | `Ephemeris.C.U_C_Access` | `Ephemeris.C.U_C` |

### C POD Type Replacement

DELETE all h2ads-generated struct types. Replace with Adamant packed records:

| h2ads struct | Adamant replacement |
|-------------|-------------------|
| `Vector3f_C` (3-float array) | `Packed_F32x3_Record.C.U_C` |
| `Matrix3f_C` (3x3 float) | `Packed_F32x9_Record.C.U_C` |
| Algorithm-specific structs | Create packed record YAML, use `<Type>.C.U_C` |

### With Clauses
```ada
with Interfaces.C; use Interfaces; use Interfaces.C;
with Ephemeris.C;
with Nav_Att.C;
```
Remove `with System;` if unused.

### Constant Validation
```ada
NUM_SLEWS : constant := 3;  -- Must match sunSearchTypes.h:11

function Get_Num_Slews return Unsigned_32
  with Import => True, Convention => C,
       External_Name => "SunSearchAlgorithm_getNumSlews";

pragma Assert (Unsigned_32 (NUM_SLEWS) = Get_Num_Slews);
```

### Documentation Comments
```ada
--* @brief Compute ephemeris-based sunline heading.
--* @param Self    The algorithm instance.
--* @param Sun_Pos Pointer to sun ephemeris payload.
--* @return Navigation message with sunline direction.
function Update_State
  (Self    : Foo_Algorithm_Access;
   Sun_Pos : Ephemeris.C.U_C_Access)
  return Nav_Att.C.U_C
  with Import       => True,
       Convention   => C,
       External_Name => "FooAlgorithm_updateState";
```

### Float Types
- `float` -> `Short_Float` (not `Interfaces.C.C_Float`)
- `double` -> `Long_Float`

## Complete Before/After Example

### h2ads output (DELETE THIS):
```ada
with Interfaces.C; use Interfaces.C;
with Ephemeris_Msg_F32_Payload_H;
with Nav_Att_Msg_F32_Payload_H;

package Sunline_Ephem_Algorithm_C_H is

   type Sunline_Ephem_Algorithm is null record;

   function Sunline_Ephem_Algorithm_Create return access Sunline_Ephem_Algorithm
   with Import => True, Convention => C,
        External_Name => "SunlineEphemAlgorithm_create";

   procedure Sunline_Ephem_Algorithm_Destroy (
      Self : access Sunline_Ephem_Algorithm)
   with Import => True, Convention => C,
        External_Name => "SunlineEphemAlgorithm_destroy";

   function Sunline_Ephem_Algorithm_Update_State (
      Self : access constant Sunline_Ephem_Algorithm;
      Sun_Pos : access constant Ephemeris_Msg_F32_Payload_H.Ephemeris_Msg_F32_Payload)
      return Nav_Att_Msg_F32_Payload_H.Nav_Att_Msg_F32_Payload
   with Import => True, Convention => C,
        External_Name => "SunlineEphemAlgorithm_updateState";

end Sunline_Ephem_Algorithm_C_H;
```

### Adamant style (CORRECT):
```ada
with Interfaces.C; use Interfaces; use Interfaces.C;
with Ephemeris.C;
with Nav_Att.C;

package Sunline_Ephem_Algorithm_C is

   type Sunline_Ephem_Algorithm is limited private;
   type Sunline_Ephem_Algorithm_Access is access all Sunline_Ephem_Algorithm;

   function Create
     return Sunline_Ephem_Algorithm_Access
     with Import       => True,
          Convention   => C,
          External_Name => "SunlineEphemAlgorithm_create";

   procedure Destroy
     (Self : Sunline_Ephem_Algorithm_Access)
     with Import       => True,
          Convention   => C,
          External_Name => "SunlineEphemAlgorithm_destroy";

   function Update_State
     (Self    : Sunline_Ephem_Algorithm_Access;
      Sun_Pos : Ephemeris.C.U_C_Access)
     return Nav_Att.C.U_C
     with Import       => True,
          Convention   => C,
          External_Name => "SunlineEphemAlgorithm_updateState";

private

   type Sunline_Ephem_Algorithm is null record;

end Sunline_Ephem_Algorithm_C;
```