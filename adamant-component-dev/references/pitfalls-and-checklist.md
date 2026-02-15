# Component Development Pitfalls & Checklist Details

## Checklist Explanations (Supplemental)

### Init override
Active components do NOT override Init with Queue_Size — queue setup is via `init_base` in assembly YAML. Only override Init if YAML has `init:` section with parameters.

### Invalid_Command details
Missing produces "type must be declared abstract" error. It's a PROCEDURE (not function) with 4 parameters.

### Send_Dropped handlers
EVERY send connector generates a `*_Send_Dropped` procedure that MUST be overridden (even as `is null`). Forgetting one produces: "type must be declared abstract or X overridden".

### Active component testing
Active components have async receive connectors with queues. In tests, `T.Packet_T_Send(...)` enqueues but does NOT process. You MUST call `T.Dispatch_All` to process queued messages. Without it, async handlers never execute and coverage is 0%. Passive components process synchronously -- no `Dispatch_All` needed (and calling it is a compile error).

### gcov limitation with active components
Some active components produce 0% coverage even with passing tests due to GNAT Ada task cleanup not flushing gcov data. The .gcda files are never written because the Ada task's finalization prevents clean process exit. This is a known GNAT/gcov limitation -- not a test quality issue.

### .all_path file
0 bytes marker file. NO content inside. Helper: `bash scripts/mk_all_path.sh /path/to/component/dir`.

### Parameter accessor returns .U
`Self.<Param_Name>` returns `.U` — convert to `.T` for events: `My_Type.T (Self.My_Param)`.
`Validate_Parameters` takes INDIVIDUAL args (one per parameter), NOT a combined record.
Param type package must NOT match param name (collision).
`Parameter_Update_Status` lives in `Parameter_Enums.Parameter_Update_Status`.

### No Packed_U8
Use `Packed_Byte.T` for 8-bit values. Add `with Packed_Byte;` in body when constructing aggregates.

### No Event.T send for forwarding
Tester's Dispatch_Event calls `Local_Event_Id_Type'Val(Evnt.Header.Id)` on ALL received Event.T, crashing on non-component event IDs. Use Packet.T for routing instead.

## Command_Execution_Status vs Command_Response_Status

Two different enums in `Command_Enums`:
- `Command_Execution_Status.E` — returned by `Execute_*` command handlers (Success/Failure)
- `Command_Response_Status.E` — in `Command_Response.T.Status` field (Success/Failure/Dropped)

When testing commands, comparing `Cmd_Response.Status` requires `use type Command_Enums.Command_Response_Status.E;` — NOT `Command_Execution_Status.E`. These are different types. Using the wrong `use type` gives: "operator for type E is not directly visible".

## Command Handler Details

- Function names match YAML `name:` EXACTLY (no `_Execute` suffix)
- `arg_type` is the YAML field (not `type` or `parameters`)
- For no-argument commands, OMIT `arg_type` entirely

## Framework Type Header Fields

Do NOT invent fields. Actual fields:
- `Packet_Header.T`: Time, Id (U16), Sequence_Count (mod 2**14, NOT Unsigned_16), Buffer_Length (Natural). NO Priority.
- `Event_Header.T`: Time, Id (U16), Param_Buffer_Length (U8). NO Severity (assembly-level concept).
- `Command_Header.T`: Source_Id, Id (Command_Types.Command_Id — distinct type). Need `with Command_Types; use Command_Types;`.

## Packed Record Field Notes

- `Natural` needs 31 bits — does NOT fit `U16`. Use `Interfaces.Unsigned_16`.
- Enum literal names must NOT collide with framework package names (e.g., `Fault` → use `Faulted`).
- Packed `.T` types can't be used as simple record aggregates for default init. Store scalar fields.

## Init Parameter Types

Use standard Ada types: `Positive`, `Natural`, `Boolean`, `Interfaces.Unsigned_32`.
NOT `Interfaces.IEEE_Float_32` — use `Short_Float` or `Long_Float` for floats.

## Target Hardware Abstraction

Same interface, target-specific body via build path:
```
component/
├── hardware_action.ads            # Shared spec
├── linux/hardware_action.adb      # Dev no-op (.Linux_path)
└── pico/hardware_action.adb       # Real hardware (.Pico_path)
```
