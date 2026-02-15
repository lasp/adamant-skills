---
name: adamant-type-system
description: Comprehensive guide to Adamant YAML-driven type system with records, arrays, enums, packed types, validation rules, and code generation patterns
---

# Adamant Type System

YAML-driven type modeling → Ada packages, Python, MATLAB, COSMOS config, HTML docs, SVG diagrams, LaTeX.

## Type Kinds Overview

| Kind | File Suffix | YAML Root Keys | Description |
|------|-------------|----------------|-------------|
| Record | `.record.yaml` | `fields:` (required) | Packed record with named fields |
| Array | `.array.yaml` | `type:`, `format:`, `length:` | Fixed-length homogeneous array |
| Enums | `.enums.yaml` (plural!) | `enums:` (list of enums) | One or more named enumerations |

All three kinds also support optional: `description:`, `preamble:`, `with:`.

## Complete YAML Field Reference

### Record (*.record.yaml)

```yaml
---
description: string           # Optional description
preamble: |                   # Optional inline Ada declarations
  type My_Mod is mod 2**4;
with:                         # Optional additional with-clauses
  - Package_Name
fields:                       # REQUIRED, min 1 field
  - name: Field_Name          # REQUIRED
    description: string       # Optional
    type: Ada_Type_Name       # REQUIRED
    format: U8                # Required for primitive types, omit for packed types (.T)
    default: "0"              # Optional default value (string, always quoted)
    variable_length: Length    # Optional, only on LAST field
    variable_length_offset: 0 # Optional integer offset for variable_length
    byte_image: False         # Optional, print as byte array
    skip_validation: False    # Optional, skip range validation
```

### Array (*.array.yaml)

```yaml
---
description: string           # Optional
preamble: |                   # Optional
with:                         # Optional
  - Package_Name
type: Short_Float             # REQUIRED, element Ada type
format: F32                   # Required for primitive types, omit for packed types
length: 3                     # REQUIRED, integer ≥ 1
byte_image: False             # Optional
skip_validation: False        # Optional
```

### Enums (*.enums.yaml)

```yaml
---
description: string           # Optional
preamble: |                   # Optional
with:                         # Optional
enums:                        # REQUIRED, min 1 enum
  - name: My_Enum_Type        # REQUIRED
    description: string       # Optional
    literals:                 # REQUIRED, min 1 literal
      - name: First           # REQUIRED
        value: 0              # Optional (auto-increments from 0)
        description: string   # Optional
      - name: Second
        value: 1
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

No format needed when field type is another packed type (e.g., `Packed_F32.T`, `My_Record.T`).

See [references/format-codes-and-examples.md](references/format-codes-and-examples.md) for complex packing examples.

## Sub-Byte Bitfields (CRITICAL)

Fields < 8 bits MUST use `mod` types or `subtype ... range` in the preamble. `Unsigned_8` does NOT fit in U3.

**mod types** (for unsigned bitfields):
```yaml
preamble: |
  type Apid_Type is mod 2**11;      # 11-bit unsigned
  type Nibble is mod 2**4;          # 4-bit unsigned
  type Bit_Type is mod 2**1;        # 1-bit flag
```

**subtype range types** (for constrained sub-byte values):
```yaml
preamble: |
  subtype Three_Bit_Type is Interfaces.Unsigned_8 range 0 .. 7;    # fits U3
  subtype Four_Bit_Type is Interfaces.Unsigned_8 range 0 .. 15;    # fits U4
```

Both work. `mod` types do NOT need `with: [Interfaces]`. `subtype ... is Interfaces.Unsigned_8 range` DOES need it.

**Boolean packing**: Do NOT use Ada `Boolean` in packed fields. Use `mod 2**1` with format `U1`, or use an enum with E1 format.

## Packed Type Bit Layout Rules

- Fields are packed **contiguously** in declaration order, MSB first (big-endian `.T`)
- Total bit count MUST be byte-aligned (divisible by 8) -- pad with reserved fields if needed
- Generator produces `.T` (big-endian), `.T_Le` (little-endian), and `.U` (unpacked)
- Nested packed types (e.g., `Packed_F32.T` as a field) inherit the parent's bit position
- No implicit padding -- you must add explicit padding fields for alignment

### Padding Example
```yaml
preamble: |
  type Six_Bit_Type is mod 2**6;
fields:
  - name: Status
    type: My_Enums.Status_Type.E
    format: E2                       # 2 bits
  - name: Reserved
    type: Six_Bit_Type
    format: U6                       # 6 bits padding → byte-aligned
```

## Generated Code Structure

### Record → 12+ files
| File | Contents |
|------|----------|
| `name.ads` | Package spec: types `U`, `T`, `T_Le`, `Pack`/`Unpack`, `Swap_Endianness`, `Serialization` |
| `name.adb` | Package body: Pack/Unpack implementations |
| `name-representation.ads` | `Image` function spec |
| `name-representation.adb` | `Image` function body, `To_Byte_String` |
| `name-validation.ads` | `Valid` function spec (field range checks) |
| `name-validation.adb` | `Valid` function body |
| `name-assertion.ads` | Type-safe assertion procedures for unit tests |
| `name-assertion.adb` | Assertion implementations |
| `name-c.ads` | C-compatible type bindings spec |
| `name-c.adb` | C-compatible type bindings body |
| `name.py` | Python ground system class |
| `name_type_ranges.adb` | Type range registration |
| `name.m` | MATLAB interface (CamelCase filename) |
| `name.html` | HTML documentation |
| `name.tex` | LaTeX documentation |

### Array → same file set as Record

### Enums → 7 files
| File | Contents |
|------|----------|
| `name.ads` | Enum type `E` in child package per enum, with `E_First`, `E_Last` |
| `name-representation.ads/.adb` | `Image` function |
| `name-assertion.ads` | Type-safe assertions |
| `name.py` | Python enum class |
| `name.html` | HTML documentation |
| `name.tex` | LaTeX documentation |

### Ada Package Structure
```ada
-- Record: my_type.ads
package My_Type is
   Size : constant Positive := 64;         -- Total bits
   Size_In_Bytes : constant Positive := 8;
   type U is record ... end record;         -- Unpacked
   type T is ...;                           -- Packed big-endian
   type T_Le is ...;                        -- Packed little-endian
   function Pack (Src : in U) return T;
   function Unpack (Src : in T) return U;
   function Swap_Endianness (Src : in T) return T_Le;  -- and reverse
   package Serialization is new Serializer (T);
end My_Type;

-- Enum: my_enums.ads (multiple enums per file)
package My_Enums is
   package Status_Type is
      type E is (Ok, Error);
   end Status_Type;
end My_Enums;
-- Usage: My_Enums.Status_Type.E, My_Enums.Status_Type.Ok
```

## Assertion Package Usage

Auto-generated `-assertion.ads` provides type-safe test helpers:
```ada
with My_Type.Assertion; use My_Type.Assertion;
-- Compare two unpacked records field-by-field:
My_Type.Assertion.My_Type_Assert_Eq (Expected, Actual);
```

For enums: `My_Enums.Assertion.Status_Type_Assert_Eq (Expected, Actual);`

## `with:` Rules

**When to add `with:`:**
- Field type references an external package (e.g., `Basic_Enums.Enable_Disable_Type.E` → `with: [Basic_Enums]`)
- Preamble uses `Interfaces.Unsigned_8` → `with: [Interfaces]`
- Field uses another packed type (e.g., `Packed_F32.T` → `with: [Packed_F32]`)

**When NOT needed:**
- `mod 2**N` types in preamble (no dependency)
- `Short_Float`, `Long_Float`, `Natural`, `Integer` (built-in Ada types)
- Types defined in the same preamble

**Common mistake**: Adding `with: [Interfaces]` when preamble only uses `mod` types -- harmless but generates unused `with Interfaces;` warning.

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
    variable_length_offset: 0        # CCSDS uses -1
```

Only ONE variable-length field allowed, must be LAST field. Cannot nest variable-length types.

## Available Framework Packed Types

Unsigned: `Packed_Byte.T`, `Packed_U16.T`, `Packed_U32.T`, `Packed_U64.T`
Signed: `Packed_I8.T`, `Packed_I16.T`, `Packed_I32.T`, `Packed_I64.T`
Float: `Packed_F32.T`, `Packed_F64.T`
Special: `Packed_Boolean.T`, `Packed_Natural.T`
Arrays: `Packed_F32x3.T`, `Packed_F64x3.T`

**No Packed_U8** -- use `Packed_Byte.T`.

## Special Field Attributes

```yaml
skip_validation: True    # Platform-specific types (System.Address)
byte_image: True         # Print as byte array instead of typed Image
```

## Key Validation Rules

1. Records must be byte-aligned (total bits % 8 == 0)
2. Only ONE variable-length field, must be LAST
3. Every primitive field MUST have `format:` -- missing = build error
4. Packed type fields (`.T`) must NOT have `format:` -- the size comes from the type
5. `Natural` needs 31 bits -- does NOT fit U16. Use `Unsigned_16` instead
6. Field names must NOT shadow package names in `with` list or match their own type name
7. Enum names must differ from parent package name
8. Do NOT use `Boolean` as packed field -- use `mod 2**1`/U1 or enum E1
9. Sub-byte fields MUST use `mod` or `subtype range` types defined in preamble
10. Enum literal `value:` is optional -- auto-increments from 0 if omitted

## Common Type Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "not byte aligned" | Total bits not divisible by 8 | Add padding field |
| "format required" | Primitive field missing `format:` | Add correct format code |
| Missing `with` | Field references external package | Add to `with:` list |
| "does not fit" | Type too large for format (e.g., `Unsigned_8` in U3) | Use `mod 2**3` in preamble |
| Unused `with Interfaces` warning | Preamble uses only `mod` types | Remove `Interfaces` from `with:` (or ignore) |
| Field name collision | Field named same as `with`'d package | Rename the field |
| Enum `E` not found | Using `.enums.yaml` but forgot `.E` suffix | Type is `Pkg.Enum_Name.E` |
| "overlayable" violation | Variable-length field not last | Move to last position |

## Build Commands

```bash
redo all                          # Build everything
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

### Record with Nested Packed Type (no format!)
```yaml
with:
  - Packed_F32
fields:
  - name: Temperature
    type: Packed_F32.T
    description: "[degC] Sensor temperature"
  - name: Timestamp
    type: Interfaces.Unsigned_32
    format: U32
```

### Aggregates in Ada
```ada
Val : My_Type.U := (Seconds => 100, State => Enabled, Velocity => 1.5);
Packed_Val : My_Type.T := My_Type.Pack (Val);
Unpacked : My_Type.U := My_Type.Unpack (Packed_Val);
```

### Using in Events/Data Products
```ada
Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Counter (The_Time, (Value => 42)));
Self.Event_T_Send_If_Connected (Self.Events.Status_Changed (The_Time, My_Record.Pack (My_Val)));
```

## Type Organization in Projects

```
src/types/
├── my_custom_types/              # Each dir needs .all_path
│   ├── .all_path
│   ├── my_record.record.yaml
│   ├── my_enums.enums.yaml
│   └── my_array.array.yaml
```

Each type directory needs its own `.all_path`. File names must be unique across entire build path.

## Style

Type YAML files must start with `---`. Generated Ada files may produce style warnings (e.g., `with Interfaces` unreferenced) -- all warnings are fixable. See [adamant-style](../adamant-style/SKILL.md).

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md) -- using types in components
- **Style**: [adamant-style](../adamant-style/SKILL.md)
