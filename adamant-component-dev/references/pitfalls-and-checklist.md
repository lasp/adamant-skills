# Component Development Pitfalls & Checklist Details

## Pre-Flight Checklist (Detailed Explanations)

### 1. Spec uses `with private` pattern
Public part has opaque `type Instance is new Base_Instance with private;`. Private section has full record + all overriding declarations.

### 2. Init override present IFF component YAML has `init:` section
Active components do NOT override Init with Queue_Size -- queue setup is via `init_base` in assembly YAML. Only override Init if YAML has `init:` section with parameters.

### 3-4. Invalid_Command and Command_T_Recv_Sync present IFF commands.yaml exists
Missing either produces "type must be declared abstract" error.

`Invalid_Command` is a PROCEDURE (not function) with 4 parameters:
```ada
overriding procedure Invalid_Command (Self : in out Instance; Cmd : in Command.T;
   Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);
```

`Command_T_Recv_Sync` standard pattern:
```ada
overriding procedure Command_T_Recv_Sync (Self : in out Instance; Arg : in Command.T) is
   Stat : constant Command_Response_Status.E := Self.Execute_Command (Arg);
begin
   Self.Command_Response_T_Send_If_Connected ((
      Source_Id => Arg.Header.Source_Id,
      Registration_Id => Self.Command_Reg_Id,
      Command_Id => Arg.Header.Id,
      Status => Stat));
end Command_T_Recv_Sync;
```
Use `Self.Execute_Command(Arg)` (NOT `Self.Process_Command`). Returns `Command_Response_Status.E`.

### 5. All `*_Send_Dropped` handlers overridden
EVERY send connector generates a `*_Send_Dropped` procedure that MUST be overridden (even as `is null`). Forgetting one produces: "type must be declared abstract or X overridden".

### 6. NO `with` for auto-provided packages
Do NOT `with`: `Command_Execution_Status`, `Command_Response_Status`, `Unsigned_32`, `Parameter_Validation_Status`, `Command_Response`, `Event`, `Data_Product`, `Fault`, `Sys_Time`, `Basic_Types`, `Interfaces` (when commands exist).

Exception: `Interfaces` is only auto-provided when commands or other features use it. If your component has no commands but uses Unsigned types, add `with Interfaces; use Interfaces;` in the implementation spec.

### 7. NO build/ directory
Build system generates it. Creating it manually prevents redo from running code generation.

### 8. Empty .all_path file
0 bytes marker file. NO content inside. Helper: `bash scripts/mk_all_path.sh /path/to/component/dir`.

### 9. Entity names unique
ALL names (events, data products, commands, faults, parameters) must be unique across the component.

### 10. `use Command_Execution_Status;` placement
INSIDE package body, NEVER before `package body` line:
```ada
package body Component.Foo.Implementation is
   use Command_Execution_Status;  -- HERE
```

### 11-12. get vs request connector YAML
- `get`: uses `return_type:` only (NO `type:`)
- `request`: uses BOTH `type:` and `return_type:`

### 13. Custom record format codes required
Every field MUST have `format:` (`F32` for Short_Float, `U32` for Unsigned_32, etc.). Missing = build error.

### 14. Qualify ambiguous literals
Use `Parameter_Validation_Status.Valid`, `Command_Execution_Status.Success` (bare names can be ambiguous).

### 15. Parameter accessor returns .U
`Self.<Param_Name>` returns `.U` -- convert to `.T` for events: `My_Type.T (Self.My_Param)`.

### 16. Faults use event-like API
Correct: `Self.Fault_T_Send_If_Connected (Self.Faults.Name (The_Time))`
Wrong: `Self.Name.Set_Status(...)`

### 17. Invalid_Parameter override for parameters
Abstract, MUST override. Signature: `procedure Invalid_Parameter (Self : in out Instance; Par : in Parameter.T; Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type)`
Note: Par is `Parameter.T`, NOT `Parameter_Update.T`.

### 18. No Packed_U8
Use `Packed_Byte.T` for 8-bit values. Add `with Packed_Byte;` in body when constructing aggregates.

### 19. Data dependency overrides
Both `Get_Data_Dependency` and `Invalid_Data_Dependency` are abstract, MUST override:
```ada
overriding function Get_Data_Dependency (Self : in out Instance;
   Id : in Data_Product_Types.Data_Product_Id) return Data_Product_Return.T
   is (Self.Data_Product_Fetch_T_Request ((Id => Id)));
overriding procedure Invalid_Data_Dependency (Self : in out Instance;
   Id : in Data_Product_Types.Data_Product_Id; Ret : in Data_Product_Return.T);
```

### 20. Active component Init
Queue setup via `init_base` in assembly YAML, NOT a component Init procedure.

### 21. No dynamic allocation
Ravenscar profile: no `new`, no `access` types, no `Final`/destructors. Use fixed-size arrays.

### 22. Init param storage
Init body copies param values into record fields. Record must HAVE those fields.

### 23. No `with Command_Response_Status`
Not a standalone package. Available through generated base class.

### 24. Recv_Async_Dropped for active components
Active components with `recv_async` connectors MUST override `{Type}_T_Recv_Async_Dropped` in spec.

### 25. No Event.T send for forwarding
Tester's Dispatch_Event calls `Local_Event_Id_Type'Val(Evnt.Header.Id)` on ALL received Event.T, crashing on non-component event IDs. Use Packet.T for routing instead.

---

## Required Connectors for Feature Models

Each feature YAML requires matching connectors in component YAML (NOT auto-generated):

| Feature YAML | Required Connectors |
|---|---|
| `commands.yaml` | `Command.T` recv_sync + `Command_Response.T` send |
| `events.yaml` | `Event.T` send |
| `data_products.yaml` | `Data_Product.T` send |
| `faults.yaml` | `Fault.T` send |
| `parameters.yaml` | `Parameter_Update.T` modify |
| `data_dependencies.yaml` | `Data_Product_Fetch.T`/`Data_Product_Return.T` request + `Sys_Time.T` get |

Validation script: `bash scripts/check_connectors.sh` (run from component directory).

## Command Handler Details

- Function names match YAML `name:` EXACTLY (no `_Execute` suffix)
- Commands with `arg_type:` get `Arg : in <arg_type>` parameter; without get no extra parameter
- `arg_type` is the YAML field (not `type` or `parameters`)
- For no-argument commands, OMIT `arg_type` entirely

## Parameter Details

- Parameters REQUIRE `default` in YAML (schema-enforced)
- `Self.Update_Parameters` must be called explicitly (e.g., in Tick handler)
- `Validate_Parameters` takes INDIVIDUAL args (one per parameter), NOT a combined record
- `Update_Parameters_Action` is abstract -- must override even if just `is null`
- Param type package must NOT match param name (collision). Bad: `My_Params.T` for param `My_Params`
- `Parameter_Update_Status` lives in `Parameter_Enums.Parameter_Update_Status`
- No combined `Component_Name_Parameters.U` record type

## Data Dependencies API

Generated API for each dependency named "Foo":
```ada
Status := Self.Get_Foo (Stale_Reference => time, Timestamp => out_time, Value => out_var);
-- Returns Data_Product_Enums.Data_Dependency_Status.E (Success | Not_Available | Stale | Error)
-- Need: use Data_Product_Enums; use Data_Product_Enums.Data_Dependency_Status;
```

## Duplicate Connector Types

Two connectors of same type get numbered: `Event_T_Send` (1st), `Event_T_Send_2` (2nd). Each gets its own `*_Dropped` handler.

## Framework Type Header Fields

Do NOT invent fields. Actual fields:
- `Packet_Header.T`: Time, Id (U16), Sequence_Count (mod 2**14, NOT Unsigned_16), Buffer_Length (Natural). NO Priority.
- `Event_Header.T`: Time, Id (U16), Param_Buffer_Length (U8). NO Severity (assembly-level concept).
- `Command_Header.T`: Source_Id, Id (Command_Types.Command_Id -- distinct type). Need `with Command_Types; use Command_Types;`.

## Implementation Spec With Clauses

- Only `with` connector types and custom types you actually use
- Generated base includes `with Interfaces` when component has init params, commands, or features referencing Interfaces types
- For simple components needing Unsigned types without commands: add `with: ["Interfaces"]` in component YAML
- Components with commands auto-get `use Command_Enums;`

## Implementation Spec Structure (Mandatory Pattern)

```ada
with Tick;        -- Only with connector/custom types you actually use
with Command;     -- Only if component has commands
with Interfaces; use Interfaces;  -- REQUIRED if record uses Unsigned types AND no commands

package Component.My_Component.Implementation is
   type Instance is new My_Component.Base_Instance with private;  -- PUBLIC: opaque
private
   type Instance is new My_Component.Base_Instance with record    -- PRIVATE: fields
      My_Field : Interfaces.Unsigned_32 := 0;
   end record;
   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T);
end Component.My_Component.Implementation;
```

## Packed Record Field Notes

- `Natural` needs 31 bits -- does NOT fit `U16`. Use `Interfaces.Unsigned_16`.
- Enum literal names must NOT collide with framework package names (e.g., `Fault` -> use `Faulted`).
- Packed `.T` types can't be used as simple record aggregates for default init. Store scalar fields.

## Init Parameter Types

Use standard Ada types: `Positive`, `Natural`, `Boolean`, `Interfaces.Unsigned_32`.
NOT `Interfaces.IEEE_Float_32` -- use `Short_Float` or `Long_Float` for floats.

## Connector Count (Array Connectors)

`count: 0` or N = one-to-many fan-out with index:
- Generated index type: `<Type>_T_Send_Index`
- Send: `Self.Packet_T_Send_If_Connected(Index, Arg)`
- Loop: `for I in Packet_T_Send_Index'Range loop`
- Dropped: `overriding procedure Packet_T_Send_Dropped(Self : in out Instance; Index : in Packet_T_Send_Index; Arg : in Packet.T)`
- Check: `Self.Is_Packet_T_Send_Connected(Index)`

## Target Hardware Abstraction

Same interface, target-specific body via build path:
```
component/
├── hardware_action.ads            # Shared spec
├── linux/hardware_action.adb      # Dev no-op (.Linux_path)
└── pico/hardware_action.adb       # Real hardware (.Pico_path)
```
