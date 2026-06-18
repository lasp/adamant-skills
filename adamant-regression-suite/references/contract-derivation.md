# Deriving the test surface from the interface contract

How to learn every command, telemetry packet, item, ID, range, and enum a regression test needs --
all from `.yaml`/`.py`, never from flight-software source.

## The generation chain

```
Adamant YAML models (in the flight-software repo)
  per component:  <name>.commands.yaml      (commands: name, description, arg_type)
                  <name>.events.yaml         (events: name, description, param_type)
                  <name>.data_products.yaml  (data products: name, description, type)
                  <name>.packets.yaml        (packets: optional explicit id/APID, optional type)
                  <name>.parameters.yaml     (parameters: type, default)
                  <name>.faults.yaml         (faults: optional static id, param_type)
  assembly:       <assembly>.assembly.yaml   (collects all suites; assigns numeric IDs)
  config:         <project>.configuration.yaml (buffer sizes and similar constants)
        |
        |  build
        +--> generated ground-side Python (the authoritative runtime interface):
        |       <assembly>_commands.py, _events.py, _data_products.py, _packets.py,
        |       _parameters.py, _faults.py   -- numeric ID constants + name<->id lookups
        |       (events also expose typed event classes for decoding)
        |       <type>.py                    -- packed-type classes (records/arrays/enums)
        |
        +--> generated COSMOS command/telemetry dictionary -- the cmd/tlm names tests reference
```

The numeric IDs are NOT in the per-component YAML; the **assembly** generator assigns them (lowest
free 16-bit IDs, optionally floored by id bases). So read the generated `<assembly>_*.py` for the
actual numbers, and the per-component YAML for the *semantics* (descriptions, ranges, enum states).

## What each readable artifact gives you

| Need | Read |
|------|------|
| Exact COSMOS command/telemetry/item names + parameters | the generated COSMOS dictionary |
| Command/event/data-product/packet/fault/parameter numeric IDs | `<assembly>_*.py` |
| Typed event classes (to decode event sub-packets) | `<assembly>_events.py` |
| Packed-type field layouts (to build/parse a buffer) | the generated `<type>.py` classes |
| Field ranges, defaults, enum states, descriptions | the component `.yaml` models |
| Buffer sizes and similar constants | `<project>.configuration.yaml` |
| CCSDS header/CRC layout | framework + IR CCSDS YAML (see below) |

## The naming transform (model name -> COSMOS name)

A regression test references names as `cmd("<TARGET> <Component_Instance>-<Command_Name>", {...})`
and `tlm("<TARGET> <Packet> <item path>")`. Those names are derived mechanically from the model:

- **TARGET** is the COSMOS target name the plugin assigns to the assembly (one per assembly).
- **Command name** is `<Component_Instance>-<Command_Name>` (the instance and command joined; `.` in
  a nested name becomes `-`).
- **Telemetry item** is the dotted path of the data product and field, lowercased/dashed, under the
  packet, e.g. `<Component_Instance>-<Data_Product>-<Field>[-<SubField>]`.
- Projects commonly run these through a **ground-software naming layer** that maps the model name to
  a final (often ALL-CAPS) operator-facing name. Because that mapping is project-defined, **always
  take the authoritative name from the generated dictionary** rather than reconstructing it. Use the
  model-derived form only to *locate* the entry, never as the literal string in a `cmd`/`tlm` call.

## Numeric IDs and packed types

The generated `<assembly>_*.py` modules expose ID constants and `name<->id` maps; import them
directly rather than hardcoding numbers:

```python
from <assembly>_events import <Component_Instance>_<Event_Name>   # an int ID
from <assembly>_data_products import <Component_Instance>_<Data_Product>  # an int ID
```

Packed-type classes (`<type>.py`) serialize/deserialize records the same way the flight types do.
Adamant builds these Python dependencies with a packaging step (the framework's `pydep`) before they
can be imported; the project's plugin build does this for you. Use them to build command payloads or
to parse a dumped telemetry buffer -- never reconstruct a byte layout by hand from source.

## CCSDS framing (all in YAML)

- **Primary header (6 bytes):** Version (3 bits), Packet_Type (1), Secondary_Header flag (1),
  APID (11), Sequence_Flag (2), Sequence_Count (14), Packet_Length (16).
- **Command secondary header:** a function-code field plus a checksum (an XOR-8 over the packet).
- **Telemetry secondary header:** a time code; telemetry packets end with a 2-byte CRC-16 trailer.
- COSMOS auto-exposes the standard CCSDS items (`CCSDS_SEQ_COUNT`, `CCSDS_APID`, `CCSDS_LENGTH`,
  ...). Read sequence counts with `type="RAW"` for integers. Use a wrap-safe delta for the 14-bit
  sequence count: `(after - before) % 16384`.

## The command-response contract

Every command produces exactly one command response, and the command router maintains success and
failure counts plus the last successful/failed command id. This is the backbone of acceptance tests:

- **Accepted:** the success count increments (and the last-successful-command id matches).
- **Rejected:** the failure count increments. `Command_Response_Status`: `Success=0, Failure=1,
  Id_Error=2, Validation_Error=3, Length_Error=4, Dropped=5`.
- **Invalid-command info** (for rejection-cause tests): an id, an errant-field number (0 = unknown
  field; a sentinel = length error), and the errant field bytes.

## Event and fault sub-packets

Event and fault packets pack multiple entries after a leading timestamp. Each entry has a header
(timestamp + 16-bit id + parameter-buffer length) followed by the serialized parameter record.
Decode with the generated typed event classes; when those are unavailable, verify events indirectly
via the data-product state changes they cause.

## Read-order checklist (for one procedure)

1. **Generated COSMOS dictionary** -- the exact command/telemetry/item names and parameter types/ranges.
2. **Component `.yaml` models** -- descriptions, value ranges, enum states, which data products a
   component publishes.
3. **Generated `<assembly>_*.py`** -- numeric IDs and the packed-type classes you will import.
4. **Project `lib/` helpers** -- the sim-time wait and command-and-verify primitives to reuse.
5. **`<project>.configuration.yaml`** -- buffer sizes and similar constants; derive, never hardcode.

If any fact seems to require reading `.ads/.adb/.cpp/.c/.h`, stop: it is in one of the artifacts
above (or it is a constant in the configuration YAML). Needing source is the signal you are looking
in the wrong place.
