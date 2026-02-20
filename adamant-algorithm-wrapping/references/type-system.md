# Type System Patterns for Algorithm Wrapping

## Packed Record YAML Schema

```yaml
---
#  typedef struct {
#      float timeTag;
#      float r_BN_N[3];
#      float v_BN_N[3];
#  } NavTransMsgF32Payload;
description: Navigation translational state message payload
fields:
  - name: Time_Tag
    type: Short_Float
    format: F32
    description: "[s] Message timestamp"
  - name: R_Bn_N
    type: Packed_F32x3.T
    description: "[m] Position vector in inertial frame"
  - name: V_Bn_N
    type: Packed_F32x3.T
    description: "[m/s] Velocity vector in inertial frame"
```

## Type Mapping Table

### Scalar types (MUST have `format:`)

| C type | Adamant type | Format |
|--------|-------------|--------|
| `float` | `Short_Float` | `F32` |
| `double` | `Long_Float` | `F64` |
| `uint32_t` | `Interfaces.Unsigned_32` | `U32` |
| `int32_t` | `Interfaces.Integer_32` | `I32` |
| `uint8_t` | `Interfaces.Unsigned_8` | `U8` |

### Array types (NO `format:` field)

| C type | Adamant type |
|--------|-------------|
| `float x[3]` | `Packed_F32x3.T` |
| `float x[9]` | `Packed_F32x9.T` |
| `double x[3]` | `Packed_F64x3.T` |

### Field naming: C camelCase -> Ada Pascal_Case

| C field | Ada field | Reasoning |
|---------|-----------|-----------|
| `sigma_BN` | `Sigma_Bn` | BN -> Bn (first letter cap) |
| `omega_BN_B` | `Omega_Bn_B` | BN -> Bn, B stays (single letter) |
| `r_BN_N` | `R_Bn_N` | r -> R, BN -> Bn, N stays |
| `timeTag` | `Time_Tag` | camelCase split |

## Algorithm-Specific Struct Example

C struct:
```c
typedef struct {
    float slewTime;
    float slewAngle;
    int slewRotAxis;
} SlewProperties;
```

Packed record YAML (`src/types/slew_properties.record.yaml`):
```yaml
---
description: Structure defining properties for a sun search slew maneuver
fields:
  - name: Slew_Time
    type: Short_Float
    format: F32
    description: "[s] Total time for the maneuver"
  - name: Slew_Angle
    type: Short_Float
    format: F32
    description: "[rad] Total angle sweep around one axis"
  - name: Slew_Rot_Axis
    type: Interfaces.Integer_32
    format: I32
    description: "[-] Axis about which to perform the search"
```

## Using Packed Records in Ada Bindings

```ada
with Slew_Properties.C;

procedure Set_Slew_Properties
  (Self  : Foo_Algorithm_Access;
   Props : Slew_Properties.C.U_C)
  with Import => True, Convention => C,
       External_Name => "FooAlgorithm_setSlewProperties";
```

The `.C` child package provides `U_C` (C-compatible unpacked), `U_C_Access`, `To_C`, and `To_Ada` conversions.