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
```ada

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

### Format Code Syntax Rules

- **Record field format strings**: The `format:` field in record YAML uses Adamant format codes (F32, U16, U32, I8, E16, etc.), NOT printf-style format strings. Format codes follow the regex `^[uUiIfFeE][0-9]+(x[0-9]+)?$`. Examples: `F32` for float, `U16` for unsigned 16-bit, `I32` for signed 32-bit.

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
```ada

Both work. `mod` types do NOT need `with: [Interfaces]`. `subtype ... is Interfaces.Unsigned_8 range` DOES need it.

**Boolean packing**: Do NOT use Ada `Boolean` in packed fields. Use `mod 2**1` with format `U1`, or use an enum with E1 format.

## Packed Type Bit Layout Rules

- Fields are packed **contiguously** in declaration order, MSB first (big-endian `.T`)
- Total bit count MUST be byte-aligned (divisible by 8) -- pad with reserved fields if needed
- Generator produces `.T` (big-endian packed record), `.T_Le` (little-endian), and `.U` (unpacked record with native-typed fields)
- **CAVEAT**: `T_Le` and `Swap_Endianness` are only generated for records containing at least one primitive-format field (U8, U16, U32, F32, E8, etc.). Records where ALL fields are nested packed types (e.g., all `Packed_F32.T`) only generate `T` and `U` -- no `T_Le`, no `Swap_Endianness`.
- `.T` is a **record type** with named fields -- NOT a byte array. Initialize with named aggregates: `(Field_1 => X, Field_2 => Y)`, never `(others => 0)`
- `.U` fields use **unpacked** subtypes: nested packed types become their `.U` equivalent (e.g., a `Packed_F32.T` field becomes `Packed_F32.U` in the parent `.U`, accessed via `.Value`). Nested enums become the enum type directly. Primitive fields (e.g., `Unsigned_16`) become their Ada type directly.
- **Nested field access on `.U` is direct** -- no secondary `Unpack` call needed:
  ```ada
  -- Given: Outer contains Middle contains Inner (all packed records)
  Outer_U : Outer_Record.U := Outer_Record.Unpack (Packed_Val);
  -- Access nested fields directly on .U:
  Status : Inner_Enums.Status_Type.E := Outer_U.Middle.Inner.Status;
  Seq    : Unsigned_16 := Outer_U.Middle.Sequence;
  -- WRONG: Middle_Record.Unpack(Outer_U.Middle) -- .U fields are already unpacked
  ```
- **Building nested `.U` aggregates for `Pack()`**: nested record fields must be `.U` type:
  ```ada
  Val : Outer_Record.T := Outer_Record.Pack ((
     Middle    => (Inner => (Flag_Bits => 5, Status => Active),
                   Mode  => Normal, Sequence => 42),
     Timestamp => 1000,
     Counter   => 1));
  -- Each nested level uses the inner .U aggregate syntax, NOT .T values
  ```
- For `=` on packed types in Ada, need `use type My_Type.T;` to get operator visibility
- Nested packed types (e.g., `Packed_F32.T` as a field) inherit the parent's bit position
- **Reserved/padding fields ARE included in `.U`**: Fields named `Reserved` appear in BOTH `.T` (packed) and `.U` (unpacked) records. You MUST include them in `Pack()` aggregates (e.g., `Reserved => 0`). The code generator does NOT filter them out.
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
```ada

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

**Array generated types**: For `my_array.array.yaml` with `length: 8`:
```ada
package My_Array is
   subtype Constrained_Index_Type is Natural range 0 .. 7;  -- 0-based
   subtype Unconstrained_Index_Type is Natural range Natural'First .. Natural'Last;
   type T is array (Constrained_Index_Type) of Element_Type.T;   -- packed
   type U is array (Constrained_Index_Type) of Element_Type.U;   -- unpacked
   -- Plus Pack/Unpack/Serialization same as records
end My_Array;
-- Element access: My_Arr (0), My_Arr (My_Array.Constrained_Index_Type'Last)
-- .U elements are unpacked: fields accessible directly (e.g., My_Arr_U(0).Field_Name)
```

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
   -- Serialization is a CHILD instantiation, NOT a standalone package.
   -- Access via My_Type.Serialization, NEVER `with Serialization;`
   -- For fixed-size types: a separate .ads file IS generated (my_type-serialization.ads)
   --   so `with My_Type.Serialization;` works but is unnecessary if parent already visible.
   -- For variable-length types: Serialization is declared INLINE in the parent .ads (NO separate file).
   --   `with My_Type.Serialization;` will FAIL. Just use `My_Type.Serialization.*` directly.
end My_Type;

-- Serialization API (from Serializer generic) -- FIXED-SIZE types only:
--   subtype Byte_Array_Index is Natural range 0 .. (Serialized_Length - 1);
--   subtype Byte_Array is Basic_Types.Byte_Array (Byte_Array_Index);
--   function To_Byte_Array (Src : in T) return Byte_Array;
--   procedure To_Byte_Array (Src : in T; Dst : out Basic_Types.Byte_Array);
--   function From_Byte_Array (Src : in Basic_Types.Byte_Array) return T;
-- Usage: My_Type.Serialization.To_Byte_Array (Packed_Val)
-- Note: `My_Type.Serialization.Byte_Array` is the constrained (exact-size) subtype.
-- Use it as the parameter type when calling `{packet_name}_Bytes` packet-creation
-- subprograms so the compiler enforces the length match statically.

-- Variable-length types use Variable_Serializer (NOT Serializer):
--   package Serialization is new Variable_Serializer (T, Serialized_Length);
-- API is fundamentally different:
--   function To_Byte_Array (
--      Dest      : out Basic_Types.Byte_Array;
--      Src       : in T;
--      Num_Bytes : out Natural
--   ) return Serialization_Status;
--   function From_Byte_Array (
--      Src       : in Basic_Types.Byte_Array;
--      Dest      : out T;
--      Num_Bytes : out Natural
--   ) return Serialization_Status;
-- Returns Serialization_Status (Success/Failure), writes Num_Bytes actually used.
-- Serialization_Status is in package Serializer_Types: `with Serializer_Types; use Serializer_Types;`
-- NEVER use fixed-size Serialization API on variable-length types -- it won't compile.

-- Enum: my_enums.ads (multiple enums per file)
package My_Enums is
   package Status_Type is
      type E is (Ok, Error);
   end Status_Type;
end My_Enums;
-- Usage: My_Enums.Status_Type.E, My_Enums.Status_Type.Ok
-- CRITICAL: `with My_Enums;` (the PARENT package), NEVER `with My_Enums.Status_Type;`
-- The child packages are declared inside the parent .ads, not as separate compilation units.
-- To get operator visibility: `use type My_Enums.Status_Type.E;`
-- To get literal visibility: `use My_Enums.Status_Type;`

-- Enum child package types ARE supported in YAML models. The framework
-- uses them extensively (86 YAML files reference Enums.* types).
-- Example from adamant_example:
--   type: Parameter_Manager_Enums.Parameter_Table_Copy_Type.E
-- Example from framework:
--   type: Command_Protector_Enums.Armed_State.E
-- The enum .ads file must be discoverable via .all_path in the build roots.
-- If redo can't find an enum type, check that the enum's directory has
-- .all_path and is in a BUILD_ROOTS path (via env/activate).
```ada

## Representation and Validation Child Packages -- Visibility

`.Representation`, `.Validation`, and `.C` are **separate Ada child packages** (separate compilation units).
You MUST add explicit `with` clauses to use them:
```ada
with My_Type.Representation;  -- required for Image
with My_Type.Validation;      -- required for Valid, Get_Field
with My_Type.C;               -- required for To_C, To_Ada
```
Dot-notation like `My_Type.Representation.Image(...)` is NOT automatic -- Ada requires the `with`.

## Representation Child Package

`Representation.Image` has **3 overloads** for record types: `Image(U)`, `Image(T)`, `Image(T_Le)`.
This causes **ambiguity** when calling `Image(Pack(...))` inline because `Pack` returns `T` but the
compiler sees multiple candidates. Fix: use an intermediate typed variable:
```ada
-- WRONG (ambiguous):
Msg : constant String := My_Type.Representation.Image (My_Type.Pack (Val));
-- RIGHT:
Packed_Val : constant My_Type.T := My_Type.Pack (Val);
Msg : constant String := My_Type.Representation.Image (Packed_Val);
```

## C Interface Child Package

The `-c.ads/.adb` child package provides `To_C`/`To_Ada` conversion functions.
These use a separate `U_C` type (C-compatible layout), NOT `.U` or `.T`:
```ada
package My_Type.C is
   type U_C is record ... end record with Convention => C_Pass_By_Copy;
   function To_C (Src : in U) return U_C;    -- Ada unpacked -> C layout
   function To_Ada (Src : in U_C) return U;  -- C layout -> Ada unpacked
end My_Type.C;
```
Round-trip: `Ada_Val := My_Type.C.To_Ada (My_Type.C.To_C (Ada_Unpacked));`
From packed: unpack first: `C_Val := My_Type.C.To_C (My_Type.Unpack (Packed_Val));`
Nested records: inner `U_C` types are used (e.g. `Inner_Type.C.U_C` for nested fields).

## Validation Child Package

**Always generated** for every record type -- no special YAML key needed. Provides:
```ada
package My_Type.Validation is
   function Valid (R : in My_Type.T; Errant_Field : out Interfaces.Unsigned_32) return Boolean;
end My_Type.Validation;
```
- Returns `True` if all fields are in range (uses Ada `'Valid` on constrained subtypes)
- `Errant_Field` is `Interfaces.Unsigned_32` -- set to the 1-based field index of the first failing field (0 if all valid)
- Constrained subtypes are generated from preamble range types and enum ranges
- There is no `valid_ranges` YAML key -- validation is automatic from field type constraints

### Testing with Invalid Packed Records

To test `Validation.Valid`, inject out-of-range values via `Unchecked_Conversion`:
```ada
with Ada.Unchecked_Conversion;
-- Create a byte array matching the packed size:
subtype Raw_Bytes is Basic_Types.Byte_Array (0 .. My_Type.Size_In_Bytes - 1);
function To_Packed is new Ada.Unchecked_Conversion (Raw_Bytes, My_Type.T);
-- Construct bytes with an invalid field value:
Bad_Bytes : Raw_Bytes := (0 => 255, others => 0);  -- e.g., 255 exceeds Throttle range 0..100
Bad_Record : constant My_Type.T := To_Packed (Bad_Bytes);
-- Now test:
Valid : Boolean;
Field : Natural;
Valid := My_Type.Validation.Valid (Bad_Record, Field);
-- Valid = False, Field = 1 (first errant field)
```
This is the standard pattern for validation testing since `Pack()` enforces valid values.

## Initializing Packed Types

To create a zero/default `.T` value (e.g., for clearing a data product):
```ada
-- Build a .T by packing an unpacked aggregate:
Empty : constant My_Type.T := My_Type.Pack ((Field_1 => 0, Field_2 => 0.0, Field_3 => My_Enum.Idle));
-- Do NOT leave .T variables uninitialized -- GNAT warns (-gnatwv)
```

## Assertion Package Usage

Auto-generated `-assertion.ads` provides type-safe test helpers:
```ada
with My_Type.Assertion; use My_Type.Assertion;
-- Compare two unpacked records field-by-field:
My_Type.Assertion.My_Type_Assert_Eq (Expected, Actual);
```ada

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
```yaml

Only ONE variable-length field allowed, must be LAST field. Cannot nest variable-length types.

**Sub-byte field restriction**: Variable-length records cannot contain fields with sizes that are not a multiple of 8 bits. If you need sub-byte bitfields (U1, U3, E2, etc.) in a variable-length record, wrap them in a separate fixed-size packed record and reference that record type as a field instead.

**Variable-length types CANNOT be used as data products** -- Adamant's DP system requires fixed-size serialization. If you need a DP for data that is conceptually variable-length, create a parallel fixed-size record type (max-sized payload, no `variable_length` field) for the DP, and use the variable-length type only for connector transport.

**DP buffer size constraint** -- ALL data product types must serialize to <= `data_product_buffer_size` bytes (configured in assembly YAML, typically 32). A record with total packed size exceeding this limit will fail at build time. Design DP record sizes accordingly (e.g., U8x23 payload + 9-byte header = 32 bytes for a 32-byte buffer).

**Buffer type definition** -- define the backing array in the preamble:
```yaml
preamble: |
  type Buffer_Type is array (Natural range 0 .. 19) of Interfaces.Unsigned_8;
with:
  - Interfaces
```

The array upper bound = max bytes - 1 (zero-indexed). `variable_length` counts buffer elements (bytes for U8 arrays).

**Multi-record buffers**: To pack N records into a variable-length field, use a byte buffer sized to max_records * record_byte_size. The length field counts bytes, not records -- compute as `record_count * Bytes_Per_Record`. There is no tagged union / discriminated record in the packed type system; use separate message types or a byte buffer with a count field.

**Enum format sizing**: Prefer E8 (byte-aligned) for command arguments and fields where future expansion is likely. Use E2/E4 only in telemetry records where bandwidth is constrained and the enum is stable. E8 avoids padding and simplifies byte alignment.

## Available Framework Packed Types

Unsigned: `Packed_Byte.T`, `Packed_U16.T`, `Packed_U32.T`, `Packed_U64.T`
Signed: `Packed_I8.T`, `Packed_I16.T`, `Packed_I32.T`, `Packed_I64.T`
Float: `Packed_F32.T`, `Packed_F64.T`
Special: `Packed_Boolean.T` (E8 format, 8 bits -- NOT 1 bit; unpacked `.Value` field is Ada `Boolean`, not an enum), `Packed_Natural.T`
Arrays: `Packed_F32x3.T`, `Packed_F64x3.T`

**No Packed_U8** -- use `Packed_Byte.T`.

## Special Field Attributes

```yaml
skip_validation: True    # Platform-specific types (System.Address)
byte_image: True         # Print as byte array instead of typed Image
```ada

## Key Validation Rules

1. Records must be byte-aligned (total bits % 8 == 0)
2. Only ONE variable-length field, must be LAST
3. Every primitive field MUST have `format:` -- missing = build error
4. Packed type fields (`.T`) must NOT have `format:` -- the size comes from the type
5. `Natural` needs 31 bits -- does NOT fit U16. Use `Unsigned_16` instead
6. Field names must NOT shadow package names in `with` list, AND must not match their own enum type name (e.g., a field named `Msg_Type` of type `Msg_Type.E` collides -- rename to `Message_Type`)
7. Enum names must differ from parent package name
8. Do NOT use `Boolean` as packed field -- use `mod 2**1`/U1 or enum E1
9. Sub-byte fields MUST use `mod` or `subtype range` types defined in preamble
10. Arrays are ALWAYS fixed-length -- `variable_length` applies only to record fields, not array definitions
10. Enum literal `value:` is optional -- auto-increments from 0 if omitted

## Common Type Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "not byte aligned" | Total bits not divisible by 8 | Add padding field |
| "format required" | Primitive field missing `format:` | Add correct format code |
| Missing `with` | Field references external package | Add to `with:` list |
| "does not fit" | Type too large for format (e.g., `Unsigned_8` in U3) | Use `mod 2**3` in preamble |
| Unused `with Interfaces` warning | Preamble uses only `mod` types | Remove `Interfaces` from `with:` (or ignore) |
| Field name collision | Field named same as `with`'d package or own enum type | Rename the field |
| DP name vs type collision | Data product named same as type package (e.g., DP `Validation_Counts` + type `Validation_Counts`) | Rename the DP (e.g., `Val_Counts`) |
| Enum `E` not found | Using `.enums.yaml` but forgot `.E` suffix | Type is `Pkg.Enum_Name.E` |
| "overlayable" violation | Variable-length field not last | Move to last position |

## Build Commands

```bash
redo all                          # Build everything
redo build/html/type_name.html    # HTML docs
redo build/svg/type_name.svg      # Bit layout diagram
redo build/py/type_name.py        # Python class
```ada

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
```ada

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
```ada

## Type Organization in Projects

```
src/types/
├── my_custom_types/              # Each dir needs .all_path
│   ├── .all_path
│   ├── my_record.record.yaml
│   ├── my_enums.enums.yaml
│   └── my_array.array.yaml
```

Each type directory needs its own `.all_path`. File names must be **globally unique** across the entire build path (all `BUILD_ROOTS`). Two `.record.yaml` files with the same base name (e.g., `sensor_reading.record.yaml`) in different directories WILL conflict at build time — both produce the same Ada spec file (`sensor_reading-c.ads`). Prefix with project or component name if needed (e.g., `bot_station_sensor_reading.record.yaml`).

**CRITICAL**: An `.enums.yaml` and `.record.yaml` with the **same base name** in the same directory also collide — both generate the same `.ads` package. For example, `bitfield_config.enums.yaml` and `bitfield_config.record.yaml` both try to produce `bitfield_config.ads`. Solution: give the enums file a distinct name (e.g., `bitfield_config_enums.enums.yaml`).

## Style

Type YAML files must start with `---`. Generated Ada files may produce style warnings (e.g., `with Interfaces` unreferenced) -- all warnings are fixable. See [adamant-style](../adamant-style/SKILL.md).

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md) -- using types in components
- **Style**: [adamant-style](../adamant-style/SKILL.md)
