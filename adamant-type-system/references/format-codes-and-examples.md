# Type System Format Codes & Detailed Examples

## Complete Format Code Table

| Format | Bits | Ada Type | Notes |
|--------|------|----------|-------|
| U1-U7 | 1-7 | `mod 2**N` or constrained subtype | Must define in preamble |
| U8 | 8 | `Interfaces.Unsigned_8` | |
| U9-U15 | 9-15 | `mod 2**N` | Must define in preamble |
| U11 | 11 | `mod 2**11` | Common for CCSDS APID |
| U14 | 14 | `mod 2**14` | Common for CCSDS sequence count |
| U16 | 16 | `Interfaces.Unsigned_16` | |
| U32 | 32 | `Interfaces.Unsigned_32` | |
| U64 | 64 | `Interfaces.Unsigned_64` | |
| I3-I64 | 3-64 | Signed integer | Same bit rules as unsigned |
| E1 | 1 | Enum with 2 values | |
| E2 | 2 | Enum with 3-4 values | |
| E8 | 8 | Enum with up to 256 values | |
| F32 | 32 | `Short_Float` | NOT `Interfaces.IEEE_Float_32` |
| F64 | 64 | `Long_Float` | |
| U8xN | N*8 | Byte array | Jinja2: `U8x{{ size }}` |

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
# Total: 3+1+1+11+2+14+16 = 48 bits = 6 bytes ✓
```

## Variable Length Fields

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

Constraints: Only ONE variable-length field allowed, must be LAST field. Cannot nest variable-length types.

## Generated Ada Type Hierarchy

From each YAML model:

```ada
package My_Type is
   -- Constants
   Size : constant Positive := 64;         -- Total bits
   Size_In_Bytes : constant Positive := 8;

   -- Unpacked (natural Ada record)
   type U is record ... end record;

   -- Packed types
   type T is ...;                           -- Big-endian
   type T_Le is ...;                        -- Little-endian

   -- Hardware variants
   type Volatile_T is ...;
   type Atomic_T is ...;
   type Register_T is ...;

   -- Conversions
   function Pack (Src : in U) return T;
   function Unpack (Src : in T) return U;
   function Swap_Endianness (Src : in T) return T_Le;

   -- Serialization
   package Serialization is new Serializer (T);
end My_Type;
```

### Generated Child Packages
- **Representation** (`-representation.ads`): `Image`, `To_Byte_String`
- **Assertion** (`-assertion.ads`): Type-safe test assertions

## Domain-Specific Type Organization

### Framework Type Domains
- `src/types/basic_types/` — Enable_Disable_Type, On_Off_Type
- `src/types/ccsds/` — Packet headers, space packets
- `src/types/command/` — Command, Command_Header, Command_Response
- `src/types/data_product/` — Data_Product, Data_Product_Header
- `src/types/sys_time/` — Sys_Time, Delta_Time
- `src/types/memory/` — Virtual_Memory_Region variants
- `src/types/packed_types/` — Packed_U16, Packed_U32, Packed_F32, etc.

### Available Packed Types
Unsigned: `Packed_Byte.T`, `Packed_U16.T`, `Packed_U32.T`, `Packed_U64.T`
Signed: `Packed_I8.T`, `Packed_I16.T`, `Packed_I32.T`, `Packed_I64.T`
Float: `Packed_F32.T`, `Packed_F64.T`
Special: `Packed_Boolean.T`, `Packed_Natural.T`, `Packed_Poly_Type.T`

**No Packed_U8** — use `Packed_Byte.T`.

## Multi-Target Code Generation

One YAML generates: Ada packages, Python ground classes, MATLAB interfaces, COSMOS config, HTML docs, SVG bit-layout diagrams, LaTeX.

```bash
redo all                          # Build type
redo build/html/type_name.html    # HTML docs
redo build/svg/type_name.svg      # Bit layout diagram
redo build/py/type_name.py        # Python class
```

## Special Field Attributes

```yaml
skip_validation: True    # Platform-specific types (System.Address)
byte_image: True         # Print as byte array
volatile: True           # Hardware-mapped register
```

## Validation Rules

1. Records must be byte-aligned (total bits % 8 == 0)
2. Only ONE variable-length field, must be LAST
3. If ANY field volatile, ALL must be volatile
4. Field names must NOT shadow package names in `with` list
5. Sub-byte fields MUST use `mod` types (not Unsigned_8)
6. Enum names must differ from parent package name
7. Nested packed records must use consistent endianness
