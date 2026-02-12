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

```
VARIABLE target_name ASSEMBLY_NAME
TARGET ASSEMBLY_NAME <%= target_name %>

INTERFACE FLIGHT_INT tcpip_client_interface.rb host.docker.internal 7779 7779 10.0 nil LENGTH 32 16 7 1 BIG_ENDIAN 0 nil nil true
  MAP_TARGET <%= target_name %>
  PROTOCOL READ_WRITE crc_sync_protocol.rb nil false ERROR -32 32 BIG_ENDIAN

# For serial:
INTERFACE SERIAL_INT serial_interface.rb /dev/ttyUSB0 115200 NONE 1 10.0 nil LENGTH 32 16 7 1 BIG_ENDIAN 0
  MAP_TARGET <%= target_name %>
  PROTOCOL READ crc_sync_protocol.rb nil true ERROR -32 32 BIG_ENDIAN
  PROTOCOL WRITE cmd_sync_checksum.rb CHECKSUM
```

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
