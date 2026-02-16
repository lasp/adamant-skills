# Packed Record Patterns

## YAML Schema

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
| `uint8_t` | `Interfaces.Unsigned_8` | `U8` |
| `uint16_t` | `Interfaces.Unsigned_16` | `U16` |
| `uint32_t` | `Interfaces.Unsigned_32` | `U32` |
| `uint64_t` | `Interfaces.Unsigned_64` | `U64` |
| `int8_t` | `Interfaces.Integer_8` | `I8` |
| `int16_t` | `Interfaces.Integer_16` | `I16` |
| `int32_t` | `Interfaces.Integer_32` | `I32` |
| `int64_t` | `Interfaces.Integer_64` | `I64` |

### Array types (NO `format:` field)

| C type | Adamant type |
|--------|-------------|
| `float x[3]` | `Packed_F32x3.T` |
| `float x[4]` | `Packed_F32x4.T` |
| `float x[9]` | `Packed_F32x9.T` |
| `double x[3]` | `Packed_F64x3.T` |

### NEVER use

- `Natural` for C unsigned types (signed, wrong range)
- `Integer` for C integer types (use Interfaces.Integer_32)

## Field Naming: C to Ada

### Rules

1. Split on underscores and camelCase transitions
2. Capitalize ONLY first letter of each word, rest lowercase
3. Join with underscores
4. Single letters stay uppercase

### Examples

| C field | Ada field | Reasoning |
|---------|-----------|-----------|
| `sigma_BN` | `Sigma_Bn` | BN -> Bn (first letter cap) |
| `omega_BN_B` | `Omega_Bn_B` | BN -> Bn, B stays (single letter) |
| `r_BN_N` | `R_Bn_N` | r -> R, BN -> Bn, N stays |
| `vehSunPntBdy` | `Veh_Sun_Pnt_Bdy` | camelCase split, each word capitalized |
| `timeTag` | `Time_Tag` | camelCase split |
| `coM_B` | `Co_M_B` | co -> Co, M stays, B stays |
| `massSc` | `Mass_Sc` | mass -> Mass, sc -> Sc |
| `currentAdcsstate` | `Current_Adcsstate` | Ambiguous compound -> keep together |

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
#  typedef struct {
#      float slewTime;       /*!< [s] total time */
#      float slewAngle;      /*!< [rad] angle sweep */
#      int slewRotAxis;      /*!< [-] rotation axis */
#  } SlewProperties;
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

## Existing Common Types

Check before creating: `ls src/types/*.record.yaml`

Common framework types:
- `packed_f32x3.T` / `packed_f32x3_record.T` -- 3-element float array
- `packed_f32x4.T` -- 4-element float array
- `packed_f32x9.T` -- 9-element float array (3x3 matrix row-major)
- `packed_f64x3.T` -- 3-element double array

Common xmera message payload types:
- `nav_att.record.yaml` -- Navigation attitude message
- `nav_trans.record.yaml` -- Navigation translation message
- `ephemeris.record.yaml` -- Ephemeris message
- `att_ref.record.yaml` -- Attitude reference message
- `att_guid.record.yaml` -- Attitude guidance message
- `cmd_torque_body.record.yaml` -- Torque command message
- `vehicle_config.record.yaml` -- Vehicle configuration message

## Using Packed Records in Ada Bindings

After creating the YAML, reference in bindings as:

```ada
with Slew_Properties.C;

procedure Set_Slew_Properties
  (Self  : Foo_Algorithm_Access;
   Props : Slew_Properties.C.U_C)
  with Import => True, Convention => C,
       External_Name => "FooAlgorithm_setSlewProperties";
```

The `.C` child package is auto-generated from the YAML and provides `U_C` (C-compatible unpacked), `U_C_Access`, `To_C`, and `To_Ada` conversions.
