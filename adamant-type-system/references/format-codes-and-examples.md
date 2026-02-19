<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Type System Format Codes & Detailed Examples

The format code quick-reference table is in SKILL.md. This file has complex packing examples and practical patterns.

## CCSDS Primary Header Example (Complex Bit Packing)

```yaml
# ccsds_primary_header.record.yaml - 48 bits total (6 bytes)
preamble: |
  subtype Three_Bit_Version_Type is Interfaces.Unsigned_8 range 0 .. 7;
  type Ccsds_Apid_Type is mod 2**11;
  type Ccsds_Sequence_Count_Type is mod 2**14;
fields:
  - name: Version
    type: Three_Bit_Version_Type
    format: U3                       # 3 bits
  - name: Packet_Type
    type: Ccsds_Enums.Ccsds_Packet_Type.E
    format: E1                       # 1 bit enum
  - name: Secondary_Header
    type: Ccsds_Enums.Ccsds_Secondary_Header_Indicator.E
    format: E1                       # 1 bit enum
  - name: Apid
    type: Ccsds_Apid_Type
    format: U11                      # 11 bits
  - name: Sequence_Flag
    type: Ccsds_Enums.Ccsds_Sequence_Flag.E
    format: E2                       # 2 bit enum
  - name: Sequence_Count
    type: Ccsds_Sequence_Count_Type
    format: U14                      # 14 bits
  - name: Packet_Length
    type: Interfaces.Unsigned_16
    format: U16                      # 16 bits
# Total: 3+1+1+11+2+14+16 = 48 bits = 6 bytes
```

## Sub-Byte Bitfield Pattern (Sensor Status)

```yaml
# sensor_status.record.yaml - mixed enum + modular types
preamble: |
  type Stale_Count_Type is mod 2**4;
  type Bit_Type is mod 2**1;
  type Two_Bit_Type is mod 2**2;
with:
  - Sensor_Id
fields:
  - name: Id
    type: Sensor_Id.Sensor_Id_Type.E
    format: E8
    default: "Sensor_Id.Sensor_Id_Type.Temperature_1"
  - name: Stale_Count
    type: Stale_Count_Type
    format: U4
    default: "0"
  - name: Enabled
    type: Bit_Type
    format: U1
    default: "1"
  - name: Valid
    type: Bit_Type
    format: U1
    default: "1"
  - name: Padding
    type: Two_Bit_Type
    format: U2
    default: "0"
# Total: 8+4+1+1+2 = 16 bits = 2 bytes
```

**Key**: Sub-byte fields MUST use `mod` types (`type X is mod 2**N;`), NOT range types. Range types like `Natural range 0 .. 15` occupy 31 bits, not 4.

## Float Record Pattern (PID Gains)

```yaml
# pid_gains.record.yaml - all F32 fields
fields:
  - name: Kp
    type: Short_Float
    format: F32
    description: "Proportional gain"
  - name: Ki
    type: Short_Float
    format: F32
    description: "Integral gain"
  - name: Kd
    type: Short_Float
    format: F32
    description: "Derivative gain"
# Total: 32+32+32 = 96 bits = 12 bytes
```

**Key**: Use `Short_Float` (Ada 32-bit float) for F32, NOT `Interfaces.IEEE_Float_32`.

## Nested Record with Enum + Packed Subrecord

```yaml
# thruster_telemetry.record.yaml
preamble: |
  subtype Six_Bit_Type is Interfaces.Unsigned_8 range 0 .. 63;
with:
  - Packed_F32
  - Packed_U16
  - Valve_State_Enums
  - Fault_Flags
  - Interfaces
fields:
  - name: Valve_State
    type: Valve_State_Enums.Valve_State_Type.E
    format: E2
  - name: Reserved_Padding
    type: Six_Bit_Type
    format: U6
  - name: Chamber_Pressure
    type: Packed_F32.T
  - name: Thrust_Level
    type: Packed_U16.T
  - name: Faults
    type: Fault_Flags.T
```

When a field type is itself a packed record (e.g., `Fault_Flags.T`), NO format code needed -- the field inherits the nested type's packing.

## Enum-Wrapping Pattern (Packed Enum for Parameters)

To use an enum as a command `arg_type`, event `param_type`, or parameter `type`, wrap it in a packed record:

```yaml
# packed_subsystem_id.record.yaml
with:
  - Subsystem_Id
fields:
  - name: Id
    type: Subsystem_Id.Subsystem_Id_Type.E
    format: E8
```

Raw enums cannot be used directly as connector types -- they need packed wrappers.

## Framework Packed Types (Available Without Custom YAML)

From `adamant/src/types/packed_types/`:
- `Packed_Byte.T` -- 8-bit unsigned (NO `Packed_U8`)
- `Packed_U16.T` -- 16-bit unsigned
- `Packed_U32.T` -- 32-bit unsigned
- `Packed_F32.T` -- 32-bit float (`.Value` is `Short_Float`)
- `Packed_Natural.T` -- Natural (31-bit)
- `Packed_Positive.T` -- Positive (31-bit, min 1)
- `Packed_Boolean.T` -- Boolean (8-bit packed)

From `adamant/src/types/packed_types/` (arrays):
- `Packed_F32x3.T` -- 3-element Short_Float array

## Framework Type Domains

- `src/types/basic_types/` -- Enable_Disable_Type, On_Off_Type
- `src/types/ccsds/` -- Packet headers, space packets
- `src/types/command/` -- Command, Command_Header, Command_Response
- `src/types/data_product/` -- Data_Product, Data_Product_Header
- `src/types/sys_time/` -- Sys_Time, Delta_Time
- `src/types/memory/` -- Virtual_Memory_Region variants
- `src/types/packed_types/` -- Packed_U16, Packed_U32, Packed_F32, etc.

## Multi-Target Code Generation

One YAML generates: Ada packages, Python ground classes, MATLAB interfaces, COSMOS config, HTML docs, SVG bit-layout diagrams, LaTeX.

## Common Type Pitfalls

1. **Natural doesn't fit U16** -- `Natural` is 31 bits. Use `Interfaces.Unsigned_16` for 16-bit fields.
2. **`Packed_U8` doesn't exist** -- use `Packed_Byte.T`
3. **`Packed_F32.T.Value` is `Short_Float`** -- NOT `Interfaces.IEEE_Float_32`
4. **Enum format code**: `EN` where N = number of BITS, not number of literals. 4 literals need E2 (2 bits = 4 values).
5. **`with:` in type YAML** is for Ada visibility only -- include packages whose types you reference in fields
6. **`preamble:` types must fit their format** -- `subtype X is Unsigned_8 range 0 .. 63` fits U6 (6 bits)
7. **Bit total must be byte-aligned** -- total bits must be divisible by 8. Add padding fields to align.
8. **Enum type path**: `My_Enums.My_Enum_Type.E` (three levels: package.type.discriminant)
9. **Record aggregates use `()`**, array aggregates use `[]` (Ada 2022). Nested: `[others => (others => <>)]`
10. **Type YAML filenames**: `my_type.record.yaml` or `my_type.enums.yaml`. The stem becomes the Ada package name. Don't collide with framework type names (e.g., `quaternion` already exists).
