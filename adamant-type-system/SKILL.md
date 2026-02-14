---
name: adamant-type-system
description: Comprehensive guide to Adamant YAML-driven type system with records, arrays, enums, packed types, validation rules, and code generation patterns
---

# Adamant Type System

YAML-driven type modeling → Ada packages, Python, MATLAB, COSMOS config, HTML docs, SVG diagrams.

## Record Types (*.record.yaml)

```yaml
description: GPS time stamp
preamble: |
  subtype Three_Bit_Type is Interfaces.Unsigned_8 range 0 .. 7;
with:
  - Interfaces
fields:
  - name: Seconds
    type: Interfaces.Unsigned_32
    format: U32
    default: "0"
  - name: State
    type: Basic_Enums.Enable_Disable_Type.E
    format: E8
  - name: Velocity
    type: Short_Float
    format: F32
```

## Format Code Quick-Reference Table

| Format | Bits | Ada Type | Notes |
|--------|------|----------|-------|
| U1-U7 | 1-7 | `mod 2**N` | Must define in preamble |
| U8 | 8 | `Interfaces.Unsigned_8` | |
| U11 | 11 | `mod 2**11` | Common for CCSDS APID |
| U14 | 14 | `mod 2**14` | Common for CCSDS sequence count |
| U16 | 16 | `Interfaces.Unsigned_16` | |
| U32 | 32 | `Interfaces.Unsigned_32` | |
| U64 | 64 | `Interfaces.Unsigned_64` | |
| I8-I64 | 8-64 | Signed integer | Same bit rules as unsigned |
| E1 | 1 | Enum with 2 values | |
| E2 | 2 | Enum with 3-4 values | |
| E8 | 8 | Enum with up to 256 values | |
| F32 | 32 | `Short_Float` | NOT `Interfaces.IEEE_Float_32` |
| F64 | 64 | `Long_Float` | |
| U8xN | N*8 | Byte array | Jinja2: `U8x{{ size }}` |

See [references/format-codes-and-examples.md](references/format-codes-and-examples.md) for complex packing examples.

## Array Types (*.array.yaml)

```yaml
description: 3D velocity vector
type: Short_Float
format: F32
length: 3
```

## Enum Types (*.enums.yaml — NOTE: plural)

```yaml
enums:
  - name: Enable_Disable_Type
    literals:
      - name: Disabled
        value: 0
      - name: Enabled
        value: 1
```

Generated Ada: `Package_Name.Enum_Name.E` (type is always `E`).
Usage: `Basic_Enums.Enable_Disable_Type.Enabled` or `use Basic_Enums.Enable_Disable_Type;`

## Generated Types (Ada)

Each YAML generates: `.U` (unpacked record), `.T` (packed big-endian), `.T_Le` (little-endian).
Conversions: `Pack(U) → T`, `Unpack(T) → U`, `Swap_Endianness`.

```ada
package My_Type is
   Size : constant Positive := 64;         -- Total bits
   Size_In_Bytes : constant Positive := 8;
   type U is record ... end record;         -- Unpacked
   type T is ...;                           -- Packed big-endian
   type T_Le is ...;                        -- Packed little-endian
   function Pack (Src : in U) return T;
   function Unpack (Src : in T) return U;
   package Serialization is new Serializer (T);
end My_Type;
```

### Generated Child Packages
- **Representation** (`-representation.ads`): `Image`, `To_Byte_String`
- **Assertion** (`-assertion.ads`): Type-safe test assertions
- **Validation** (`-validation.ads`): Field range validation
- **C** (`-c.ads`): C-compatible bindings (for algorithm wrapping)

## Sub-Byte Fields (CRITICAL)

Fields < 8 bits MUST use `mod` types. `Unsigned_8` does NOT fit in U3.

```yaml
preamble: |
  type Apid_Type is mod 2**11;
fields:
  - name: Apid
    type: Apid_Type
    format: U11
```

## Variable-Length Fields

```yaml
fields:
  - name: Length
    type: Interfaces.Unsigned_8
    format: U8
  - name: Buffer
    type: Buffer_Type
    format: U8x20
    variable_length: Length
    variable_length_offset: 0        # CCSDS uses 1
```

Only ONE variable-length field allowed, must be LAST field. Cannot nest variable-length types.

## Available Packed Types

Unsigned: `Packed_Byte.T`, `Packed_U16.T`, `Packed_U32.T`, `Packed_U64.T`
Signed: `Packed_I8.T`, `Packed_I16.T`, `Packed_I32.T`, `Packed_I64.T`
Float: `Packed_F32.T`, `Packed_F64.T`
Special: `Packed_Boolean.T`, `Packed_Natural.T`

**No Packed_U8** — use `Packed_Byte.T`.

## Special Field Attributes

```yaml
skip_validation: True    # Platform-specific types (System.Address)
byte_image: True         # Print as byte array
volatile: True           # Hardware-mapped register
```

## Key Validation Rules

1. Records must be byte-aligned (total bits % 8 == 0)
2. Only ONE variable-length field, must be LAST
3. Every field MUST have `format:` — missing = build error
4. `Natural` needs 31 bits — does NOT fit U16. Use `Unsigned_16` instead.
5. Field names must NOT shadow package names in `with` list
6. Enum names must differ from parent package name
7. Do NOT use `Boolean` as packed field — use `Unsigned_8`/U8 with 0/1
8. Sub-byte fields MUST use `mod` types defined in preamble
9. If ANY field volatile, ALL must be volatile
10. Nested packed records must use consistent endianness

## Build Commands

```bash
redo all                          # Build type
redo build/html/type_name.html    # HTML docs
redo build/svg/type_name.svg      # Bit layout diagram
redo build/py/type_name.py        # Python class
```

## Common Patterns

### Record with Enum Field
```yaml
with:
  - Basic_Enums
fields:
  - name: Mode
    type: Basic_Enums.Enable_Disable_Type.E
    format: E8
  - name: Count
    type: Interfaces.Unsigned_16
    format: U16
```

### Record with Nested Packed Type
```yaml
with:
  - Packed_F32x3
fields:
  - name: Position
    type: Packed_F32x3.T
    description: "[m] 3D position vector"
  - name: Timestamp
    type: Interfaces.Unsigned_32
    format: U32
```
Array types used as fields do NOT have a `format` field.

### Aggregates in Ada
```ada
-- Unpacked (.U)
Val : My_Type.U := (Seconds => 100, State => Enabled, Velocity => 1.5);
-- Pack for wire
Packed_Val : My_Type.T := My_Type.Pack (Val);
-- Unpack from wire
Unpacked : My_Type.U := My_Type.Unpack (Packed_Val);
```

### Using in Events/Data Products
```ada
-- Simple packed type
Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Counter (The_Time, (Value => 42)));
-- Custom record (must pack if sending .U)
Self.Event_T_Send_If_Connected (Self.Events.Status_Changed (The_Time, My_Record.Pack (My_Val)));
```

## Type Organization in Projects

```
src/types/
├── my_custom_types/              # .all_path in each
│   ├── .all_path
│   ├── my_record.record.yaml
│   ├── my_enums.enums.yaml
│   └── my_array.array.yaml
```

Each type directory needs its own `.all_path`. File names must be unique across entire build path.

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md) — using types in components
