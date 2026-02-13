---
name: adamant-type-system
description: Comprehensive guide to Adamant YAML-driven type system with records, arrays, enums, packed types, validation rules, and code generation patterns
---

# Adamant Type System

YAML-driven type modeling with multi-target code generation. One YAML model generates Ada packages, Python ground classes, MATLAB interfaces, HTML docs, and more.

## Type Categories

### Record Types (*.record.yaml)
Bit-level packed structures with format codes:
```yaml
description: GPS time stamp with seconds and subseconds since epoch
preamble: |                        # Ada code injected into generated spec
  subtype Five_Bit_Integer is mod 2**5;
  type My_Color is (Red, Green, Blue);
with:                              # Ada dependencies
  - Interfaces
fields:
  - name: Seconds
    description: Number of seconds elapsed since epoch
    type: Interfaces.Unsigned_32
    format: U32                    # Format: U3/U8/U16/U32/U64 (unsigned)
    default: "0"                   # Field default when record instantiated
  - name: Version
    type: My_Color
    format: E8                     # E1/E2/E8 (enum bit width)
  - name: Velocity
    type: Short_Float
    format: F32                    # F32/F64 (floating point)
```

### Format Code Reference
- **Unsigned integers**: U3, U5, U8, U11, U14, U16, U32, U64
- **Signed integers**: I3, I8, I16, I32, I64
- **Enums**: E1, E2, E8 (bit width matches enum representation)
- **Floats**: F32 (`Short_Float`), F64 (`Long_Float`). Do NOT use `Interfaces.IEEE_Float_32` -- it's not recognized by the type system.
- **Byte arrays**: U8x{{ size }} (Jinja2 template for config variables)

### Variable Length Fields
```yaml
fields:
  - name: Length
    type: Interfaces.Unsigned_8
    format: U8
  - name: Buffer
    type: Buffer_Type
    format: U8x20                  # Fixed buffer size
    variable_length: Length        # Length field controls "used" length
    variable_length_offset: 0      # Offset applied to length (CCSDS uses 1)
```
**Constraint**: Only ONE variable-length field allowed, must be LAST field.

### Nested Record Types
```yaml
fields:
  - name: Header
    type: Command_Header.T          # Nested packed record (no format needed)
  - name: Arg_Buffer
    type: Command_Types.Command_Arg_Buffer_Type
    format: U8x{{ command_buffer_size }}    # Config variable interpolation
    variable_length: Header.Arg_Buffer_Length  # Nested field reference
```

### Array Types (*.array.yaml)
Fixed-size homogeneous collections:
```yaml
description: 3D velocity vector as 32-bit floats
preamble: subtype Velocity_Component is Short_Float range -1000.0 .. 1000.0;
type: Velocity_Component           # Element type
format: F32                       # Element format (unless another packed type)
length: 3                         # Fixed array length
```

### Enum Types (*.enums.yaml -- NOTE: plural "enums" not "enum")
```yaml
description: Basic state enumerations used throughout Adamant
enums:
  - name: Enable_Disable_Type
    description: Enable/disable state enumeration
    literals:
      - name: Disabled
        value: 0                   # Explicit values (optional, defaults near zero)
        description: The state is disabled
      - name: Enabled
        value: 1
        description: The state is enabled
```

**Generated Ada pattern for standalone enums:**
```ada
-- From basic_enums.enums.yaml:
package Basic_Enums is
   package Enable_Disable_Type is
      type E is (Disabled, Enabled);       -- The enum type is always named E
      for E use (Disabled => 0, Enabled => 1);
   end Enable_Disable_Type;
end Basic_Enums;

-- Usage in Ada code:
State : Basic_Enums.Enable_Disable_Type.E := Basic_Enums.Enable_Disable_Type.Enabled;
-- Or with use clause:
use Basic_Enums.Enable_Disable_Type;
State : E := Enabled;
```

**In record YAML, reference enum types as `Package.Enum_Name.E`:**
```yaml
fields:
  - name: State
    type: Basic_Enums.Enable_Disable_Type.E
    format: E8
```

**Preamble enums** (defined inside a record YAML preamble) are different -- they live directly in the generated packed type package, not as child packages with type `E`.

**Name collision warning:** Data product names must not collide with packed type names in scope. If you have a `Power_Status.T` type, do not name a data product `Power_Status` -- rename it (e.g., `Power_Telemetry`).

## Special Field Attributes

### Validation Control
```yaml
fields:
  - name: Address
    type: System.Address
    format: U32
    skip_validation: True          # Skip autocode validation (platform-specific)
    byte_image: True               # Print as byte array instead of Ada 'Image
```
**When to use skip_validation**: Platform-specific types (System.Address), raw binary data (CRCs), hardware register values.

### Hardware Interface Attributes  
```yaml
fields:
  - name: Control_Register
    type: Hardware_Control.Register_Type
    format: U32
    volatile: True                 # Hardware-mapped, value can change externally
```

## Generated Ada Type Hierarchy

From each YAML model, the generator creates layered type systems:

### Core Types
```ada
package Sys_Time is
   -- Constants
   Size : constant Positive := 64;                    -- Total bits
   Size_In_Bytes : constant Positive := 8;           -- Bytes (rounded up)
   Num_Fields : constant Positive := 2;              -- Field count

   -- Unpacked type (natural Ada record)
   type U is record
      Seconds : Interfaces.Unsigned_32 := 0;
      Subseconds : Interfaces.Unsigned_32 := 0;
   end record;
   
   -- Packed types  
   type T is ...;                                     -- Big-endian packed
   type T_Le is ...;                                  -- Little-endian packed

   -- Hardware variants (by-reference)
   type Volatile_T is ...;                           -- Volatile semantics
   type Atomic_T is ...;                             -- Atomic operations  
   type Register_T is ...;                           -- Memory-mapped register
```

### Conversion Functions
```ada
   -- Pack/Unpack between representations
   function Pack (Src : in U) return T with Inline => True;
   function Unpack (Src : in T) return U with Inline => True;
   function Pack (Src : in U) return T_Le with Inline => True;
   function Unpack (Src : in T_Le) return U with Inline => True;
   
   -- Endianness conversion
   function Swap_Endianness (Src : in T) return T_Le with Inline => True;
   function Swap_Endianness (Src : in T_Le) return T with Inline => True;

   -- Serialization for network/storage  
   package Serialization is new Serializer (T);
   package Serialization_Le is new Serializer (T_Le);
   
   function Serialized_Length (Src : in T; Num_Bytes_Serialized : out Natural) 
      return Serialization_Status with Inline => True;
end Sys_Time;
```

### Generated Child Packages
Each type generates supporting packages:
- **Main package** (`sys_time.ads/adb`): Core type definitions and operations
- **Representation** (`sys_time-representation.ads/adb`): String conversion and debugging
- **Assertion** (`sys_time-assertion.ads/adb`): Specialized testing support (hand-written)

## Validation Rules (Enforced by Model)

### Structural Constraints
1. **Byte alignment**: Records must be byte-aligned (total size multiple of 8 bits)
2. **Single variable length**: Only ONE variable-length field allowed, must be LAST field  
3. **Variable-length alignment**: Variable-length array elements must be byte-aligned
4. **No nested variable**: Cannot nest variable-length types
5. **Volatile consistency**: If ANY field is volatile, ALL fields must be volatile
6. **Endianness guarantee**: Array components >8 bits must use packed arrays for endianness
7. **Consistent endianness**: Nested packed records must use consistent endianness
8. **Field name shadowing**: Field names must NOT match package names used in the same record's `with` list. In Ada, the field name shadows the package within the record declaration. Example: a field named `sensor_id` with type `Sensor_Id.Sensor_Id_Type.E` will fail -- rename the field to `id` or similar.
9. **Sub-byte field types**: Fields smaller than 8 bits MUST use `mod` types (e.g., `type Bit_Type is mod 2**1;`) defined in `preamble`. Do NOT use `Interfaces.Unsigned_8` with a sub-byte format code -- Ada cannot pack Unsigned_8 into fewer than 8 bits.
10. **Enum name vs package name**: Enum names in `.enums.yaml` MUST differ from the parent package name. Example: in `subsystem_id.enums.yaml`, do NOT name the enum `Subsystem_Id` (creates `Subsystem_Id.Subsystem_Id` which fails Ada name resolution). Use a distinct name like `Subsystem_Id_Type` instead.

### CCSDS Example (Complex Bit Packing)
```yaml
# ccsds_primary_header.record.yaml - 48 bits total (6 bytes)
fields:
  - name: Version
    type: Three_Bit_Version_Type     # Range 0..7
    format: U3                       # 3 bits
  - name: Packet_Type  
    type: Ccsds_Enums.Ccsds_Packet_Type.E
    format: E1                       # 1 bit enum
  - name: Secondary_Header
    type: Ccsds_Enums.Ccsds_Secondary_Header_Indicator.E  
    format: E1                       # 1 bit enum
  - name: Apid
    type: Ccsds_Apid_Type            # mod 2**11
    format: U11                      # 11 bits  
  - name: Sequence_Flag
    type: Ccsds_Enums.Ccsds_Sequence_Flag.E
    format: E2                       # 2 bit enum
  - name: Sequence_Count
    type: Ccsds_Sequence_Count_Type  # mod 2**14
    format: U14                      # 14 bits
  - name: Packet_Length
    type: Interfaces.Unsigned_16
    format: U16                      # 16 bits
# Total: 3+1+1+11+2+14+16 = 48 bits = 6 bytes ✓
```

## Packed Type Hierarchy

Framework provides standard packed types in `src/types/packed_types/`:

### Basic Integers
- **Unsigned**: packed_u8, packed_u16, packed_u32, packed_u64
- **Signed**: packed_i8, packed_i16, packed_i32, packed_i64

### Constrained Integers  
- **Natural variants**: packed_natural, packed_natural_32, packed_natural_length, packed_natural_duration
- **Positive variants**: packed_positive, packed_positive_16, packed_positive_32, packed_positive_length, packed_positive_f32

### Floating Point
- **Standard**: packed_f32, packed_f64

### Special Purpose
- **Boolean**: packed_boolean (single bit)
- **Bytes**: packed_byte (8-bit container)
- **Enums**: packed_enable_disable_type  
- **Indices**: packed_connector_index
- **Polynomials**: packed_poly_type, packed_poly_32_type, packed_poly_64_type

All packed types follow single-field pattern:
```yaml
description: Single component record for holding packed unsigned 32-bit value
fields:
  - name: Value
    type: Interfaces.Unsigned_32
    format: U32
```

## Domain-Specific Type Organization

Types organized by functional domains:

### Basic Types (`src/types/basic_types/`)
- **basic_enums.enums.yaml**: Enable_Disable_Type, On_Off_Type

### CCSDS (`src/types/ccsds/`)
- **Packet headers**: ccsds_primary_header, ccsds_command_header, ccsds_command_secondary_header
- **Space packets**: ccsds_space_packet, ccsds_primary_and_command_secondary_header  
- **Error handling**: invalid_packet_crc_info, invalid_packet_length, unexpected_sequence_count
- **Enums**: ccsds_enums.enums.yaml (packet types, sequence flags, etc.)

### Command System (`src/types/command/`)
- **Core**: command.record.yaml, command_header.record.yaml
- **Identifiers**: command_id.record.yaml, command_id_status.record.yaml  
- **Registration**: command_registration.record.yaml, command_registration_request.record.yaml
- **Responses**: command_response.record.yaml, invalid_command_info.record.yaml
- **Enums**: command_enums.enums.yaml (status types, response codes)

### Data Products (`src/types/data_product/`)
- **Core**: data_product.record.yaml, data_product_header.record.yaml
- **Management**: data_product_id.record.yaml, data_product_update.record.yaml
- **Error handling**: invalid_data_product_length.record.yaml

### System Time (`src/types/sys_time/`)
- **Core**: sys_time.record.yaml (GPS time: seconds + subseconds since epoch)
- **Deltas**: delta_time.record.yaml, signed_delta_time.record.yaml  
- **Arithmetic**: sys_time/arithmetic/ (hand-written time math functions)
- **Pretty printing**: sys_time/pretty/ (human-readable time formatting)

### Memory Management (`src/types/memory/`)
- **Regions**: virtual_memory_region.record.yaml, memory_region.record.yaml (32bit/, 64bit/ variants)
- **Operations**: virtual_memory_region_write.record.yaml, virtual_memory_region_crc.record.yaml
- **Error handling**: invalid_virtual_memory_region_length.record.yaml
- **Enums**: memory_enums.enums.yaml (copy status, operation types)

### Other Domains
- **Events**: event_header.record.yaml, event.record.yaml, packed_event_id.record.yaml
- **Parameters**: parameter.record.yaml, parameter_header.record.yaml, parameter_update.record.yaml  
- **Packets**: packet_header.record.yaml, ccsds_packet_header.record.yaml
- **Faults**: fault.record.yaml, fault_header.record.yaml
- **Sequences**: sequence_header.record.yaml, sequence_load.record.yaml

## Multi-Target Code Generation

One YAML model generates outputs for many targets:

### Ada Packages
- **Complete type hierarchy**: U, T, T_Le, Volatile_T, Atomic_T, Register_T
- **Conversion functions**: Pack, Unpack, Swap_Endianness  
- **Serialization support**: To_Byte_Array, From_Byte_Array
- **Child packages**: -Representation (debugging), -Assertion (testing)

### Ground Support Integration
- **Python classes**: `redo build/py/type_name.py` for ground software interfaces
- **MATLAB interfaces**: `redo build/m/type_name.m` for analysis tools
- **COSMOS config**: `redo build/cosmos/type_name_commands.txt` for command/telemetry definitions

### Documentation and Visualization  
- **HTML docs**: `redo build/html/type_name.html` with field descriptions and layout
- **SVG diagrams**: `redo build/svg/type_name.svg` showing bit layout and field boundaries
- **LaTeX**: Formal documentation generation for requirements/specifications

### Building Types
```bash
redo all                          # Build type and all dependencies
redo build/html/type_name.html    # Generate HTML documentation
redo build/svg/type_name.svg      # Generate layout diagram  
redo build/py/type_name.py        # Generate Python ground class
```

## Testing and Validation Support

### Generated Assertion Packages
```ada
-- sys_time-assertion.ads
package Sys_Time.Assertion is
   package Sys_Time_Assert is
      procedure Eq (T1, T2 : in Sys_Time.T; Eps : in Ada.Real_Time.Time_Span);
      procedure Lt, Le, Gt, Ge (T1, T2 : in Sys_Time.T);
   end Sys_Time_Assert;
   
   -- Field-specific assertions
   package Seconds_Assert is new Smart_Assert.Basic (Seconds_Type, Seconds_Image);
   package Subseconds_Assert is new Smart_Assert.Basic (Subseconds_Type, Subseconds_Image);
end Sys_Time.Assertion;
```

### Generated Representation Packages  
```ada
-- sys_time-representation.ads  
package Sys_Time.Representation is
   -- Byte-level debugging
   function To_Byte_String (R : in T) return String;      -- Hex dump
   function To_Byte_String (R : in T_Le) return String;   
   
   -- Human-readable display
   function Image (R : in U) return String;               -- Unpacked
   function Image (R : in T) return String;               -- Big-endian packed
   function Image (R : in T_Le) return String;            -- Little-endian packed
   
   -- Field-specific formatting
   function Seconds_Image (S : Seconds_Type) return String;
   function Subseconds_Image (S : Subseconds_Type) return String;
end Sys_Time.Representation;
```

## Framework Packed Types (built-in)

Available integer packed types: `Packed_Byte.T`, `Packed_U16.T`, `Packed_U32.T`, `Packed_U64.T`
Also: `Packed_F32.T`, `Packed_Boolean.T`, `Packed_Natural.T`, `Packed_Poly_Type.T`

**There is NO Packed_U8.** Use `Packed_Byte.T` for 8-bit values.

## Sub-Byte Packed Fields (CRITICAL)

For fields smaller than 8 bits, the base Ada type MUST fit in the allocated bits. `Interfaces.Unsigned_8` does NOT work for U3 -- Ada cannot fit 8-bit type in 3 bits.

Solutions:
1. **`preamble` with constrained subtypes**: Define in YAML preamble section
   ```yaml
   preamble: |
     subtype Three_Bit_Type is Interfaces.Unsigned_8 range 0 .. 7;
     type Apid_Type is mod 2**11;
     type Sequence_Count_Type is mod 2**14;
   ```
2. **Use `mod` types** for arbitrary bit widths: `type My_Field_Type is mod 2**N;`
3. **Use enum types** with `E1`, `E2`, etc. format for 1-bit/2-bit enums

Field type must be small enough for the format:
- U1-U7: Use `mod 2**N` or constrained subtype in preamble
- U8: `Interfaces.Unsigned_8`
- U9-U15: `mod 2**N` in preamble
- U16: `Interfaces.Unsigned_16`
- U17-U31: `mod 2**N` in preamble
- U32: `Interfaces.Unsigned_32`

Example (CCSDS header pattern from framework):
```yaml
preamble: |
  subtype Three_Bit_Version_Type is Interfaces.Unsigned_8 range 0 .. 7;
  type Ccsds_Apid_Type is mod 2**11;
fields:
  - name: Version
    type: Three_Bit_Version_Type
    format: U3
  - name: Apid
    type: Ccsds_Apid_Type
    format: U11
```

## Common Pitfalls

- **Do NOT use `Boolean` as a packed record field type** -- causes schema validation errors in documentation generation. Use `Interfaces.Unsigned_8` with `format: U8` and 0/1 defaults instead. Or use `packed_boolean.T` from the framework types.
- **`Natural` needs 31 bits** -- does NOT fit U16 format. Use `Interfaces.Unsigned_16` for U16 fields.

## Usage in Components

Types integrate with component development workflow:

```yaml
# In component YAML
fields:
  - name: timestamp
    type: Sys_Time.T                    # Use generated packed type
  - name: sensor_data  
    type: Sensor_Reading.T              # Custom packed record
```

```ada
-- In component Ada implementation
procedure Process_Data (Self : in out Instance; Arg : in Sys_Time.T) is
   Time_U : constant Sys_Time.U := Sys_Time.Unpack (Arg);
begin
   -- Work with unpacked natural Ada record
   if Time_U.Seconds > Some_Threshold then
      Self.Event_T_Send_If_Connected (Self.Events.Timeout_Detected (Arg));
   end if;
end Process_Data;
```

See [adamant-component-dev](../adamant-component-dev/SKILL.md) for component integration patterns.