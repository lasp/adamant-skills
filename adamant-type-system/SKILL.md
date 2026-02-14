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

## Format Codes (Quick Reference)

Details: [references/format-codes-and-examples.md](references/format-codes-and-examples.md)

- **Unsigned**: U3, U5, U8, U11, U14, U16, U32, U64
- **Signed**: I3, I8, I16, I32, I64
- **Enum**: E1, E2, E8 (bit width)
- **Float**: F32 (`Short_Float`), F64 (`Long_Float`) — NOT `IEEE_Float_32`
- **Byte arrays**: U8xN (Jinja2: `U8x{{ size }}`)

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

## Available Packed Types

Unsigned: `Packed_Byte.T`, `Packed_U16.T`, `Packed_U32.T`, `Packed_U64.T`
Float: `Packed_F32.T`, `Packed_F64.T`
Special: `Packed_Boolean.T`, `Packed_Natural.T`

**No Packed_U8** — use `Packed_Byte.T`.

## Key Validation Rules

1. Records must be byte-aligned (total bits % 8 == 0)
2. Only ONE variable-length field, must be LAST
3. Every field MUST have `format:` — missing = build error
4. `Natural` needs 31 bits — does NOT fit U16. Use `Unsigned_16`.
5. Field names must NOT shadow package names in `with` list
6. Enum names must differ from parent package name
7. Do NOT use `Boolean` as packed field — use `Unsigned_8`/U8 with 0/1
8. Sub-byte fields MUST use `mod` types defined in preamble

## Build Commands

```bash
redo all                          # Build type
redo build/html/type_name.html    # HTML docs
redo build/svg/type_name.svg      # Bit layout diagram
```

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md) — using types in components
