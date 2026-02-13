# COSMOS (OpenC3) Integration Reference

Adamant auto-generates COSMOS configuration from assembly YAML models. This reference covers the output format and integration setup.

## Generated Output

Assembly `redo what` lists buildable COSMOS targets. Run via `cosmos_config.do`:
```
build/cosmos/plugin/{assembly}_ccsds_cosmos_commands.txt   # Command definitions
build/cosmos/plugin/{assembly}_ccsds_cosmos_telemetry.txt  # Telemetry definitions
```

Install script: `gnd/cosmos/install_cosmos_plugin.sh <assembly.yaml> <cosmos-plugin-dir>`

## COSMOS Command Format (generated)

```
COMMAND <TARGET> <CMD_NAME> BIG_ENDIAN "<description>"
  PARAMETER    CCSDSVER        0   3  UINT  0     0   0 "CCSDS version"
  PARAMETER    CCSDSTYPE       3   1  UINT  1     1   1 "Packet type"
  PARAMETER    CCSDSSHF        4   1  UINT  0     0   0 "Secondary header flag"
  ID_PARAMETER CCSDSAPID       5  11  UINT  0  2047 <apid> "Application process id"
  PARAMETER    CCSDSSEQFLAGS  16   2  UINT  3     3   3 "Sequence flags"
  PARAMETER    CCSDSSEQCNT    18  14  UINT  0 16383   0 "Sequence count"
  PARAMETER    CCSDSLENGTH    32  16  UINT  0 65535   0 "Packet length"
  ID_PARAMETER PKTID          48  16  UINT  0 65535 <id> "Packet id"
  PARAMETER    <ARG>          64  <bits> <TYPE> <min> <max> <default> "<desc>"
    STATE <name> <value>                    # Enum states
    UNITS <full_name> <abbreviation>        # Engineering units
```

Keywords: `PARAMETER` (fixed position), `APPEND_PARAMETER` (auto-position), `ID_PARAMETER` (identification).
Types: `UINT`, `INT`, `FLOAT`, `STRING`, `BLOCK`.

## COSMOS Telemetry Format (generated)

```
TELEMETRY <TARGET> <PKT_NAME> BIG_ENDIAN "<description>"
  ITEM CCSDSVER           0  3 UINT     "CCSDS version"
  ...
  APPEND_ITEM <FIELD>    <bits> <TYPE>    "<description>"
    POLY_READ_CONVERSION <c0> <c1>         # Raw-to-engineering polynomial
    UNITS <full_name> <abbreviation>
    FORMAT_STRING "%0.3f"
    LIMITS DEFAULT 1 ENABLED <rl> <yl> <yh> <rh> [<gl> <gh>]
    STATE <name> <value> [<color>]          # GREEN/YELLOW/RED
```

Keywords: `ITEM` (fixed position), `APPEND_ITEM` (auto-position), `ID_ITEM` (identification), `APPEND_ARRAY_ITEM`.

## Adamant Protocol Files

Located in `adamant/gnd/cosmos/`, copied into COSMOS plugin `targets/<TARGET>/lib/`:

| File | Purpose | Key Detail |
|------|---------|------------|
| `crc_sync_protocol.rb` | CRC verification + sync word | Strips 4-byte sync on read, verifies CRC32 |
| `cmd_checksum.rb` | Command XOR checksum | XOR all bytes with 0xFF seed |
| `cmd_sync_checksum.rb` | Sync prefix + checksum | Prepends `FED4AFEE` sync word |

## Plugin Configuration (`plugin.txt`)

TCP server interface (COSMOS listens, assembly connects):
```
Variable target_name Assembly_Name
Variable crc_parameter_name CRC
Variable checksum_parameter_name Checksum
Variable port_w 2003
Variable port_r 2003

Target Assembly_Name <%= target_name %>
Interface <%= target_name %>_INT tcpip_server_interface.rb <%= port_w %> <%= port_r %> 10.0 nil Length 32 16 7
  Map_Target <%= target_name %>
  Protocol Read crc_protocol.rb <%= crc_parameter_name %> false "ERROR" -16 16
  Protocol Write cmd_checksum.rb <%= checksum_parameter_name %>
```

For serial connections or sync-word protocols, use `crc_sync_protocol.rb` and `cmd_sync_checksum.rb` instead.

**See `adamant-cosmos-integration` skill for complete CCSDS pipeline setup.**

## Scripting API (commanding and telemetry)

```ruby
# Ruby
cmd("TARGET CMD with PARAM1 val1, PARAM2 val2")
value = tlm("TARGET PKT ITEM")              # Converted value
raw   = tlm_raw("TARGET PKT ITEM")          # Raw binary
fmt   = tlm_formatted("TARGET PKT ITEM")    # String with units
```

```python
# Python
cmd("TARGET CMD with PARAM1 val1, PARAM2 val2")
value = tlm("TARGET PKT ITEM")
raw   = tlm_raw("TARGET PKT ITEM")
```

## Type Mapping (Adamant -> COSMOS)

| Adamant Format | COSMOS Type | Notes |
|---------------|-------------|-------|
| U8/U16/U32/U64 | UINT | Unsigned integer |
| I8/I16/I32 | INT | Signed integer |
| F32/F64 | FLOAT | IEEE 754 |
| E1/E2/E8 | UINT + STATE | Enum as UINT with state dictionary |
| String | STRING | Variable-length |
| Byte array | BLOCK | Raw binary data |
