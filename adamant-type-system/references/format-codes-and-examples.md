# Type System Format Codes & Detailed Examples

The format code quick-reference table is in SKILL.md. This file has complex packing examples.

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

## Framework Type Domains

- `src/types/basic_types/` — Enable_Disable_Type, On_Off_Type
- `src/types/ccsds/` — Packet headers, space packets
- `src/types/command/` — Command, Command_Header, Command_Response
- `src/types/data_product/` — Data_Product, Data_Product_Header
- `src/types/sys_time/` — Sys_Time, Delta_Time
- `src/types/memory/` — Virtual_Memory_Region variants
- `src/types/packed_types/` — Packed_U16, Packed_U32, Packed_F32, etc.

## Multi-Target Code Generation

One YAML generates: Ada packages, Python ground classes, MATLAB interfaces, COSMOS config, HTML docs, SVG bit-layout diagrams, LaTeX.
