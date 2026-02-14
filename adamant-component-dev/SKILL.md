---
name: adamant-component-dev
description: Patterns and workflows for developing components in the Adamant embedded software framework
---

# Adamant Component Development

Components are isolated units with typed connectors. YAML models define interfaces; code generation creates Ada structure; handwritten implementation provides behavior.

## File Structure

```
component_name/
├── .all_path                                    # Build path marker (0 bytes, REQUIRED)
├── component_name.component.yaml                # Component model (REQUIRED)
├── component_name.commands.yaml                 # Commands (optional)
├── component_name.events.yaml                   # Events (optional)
├── component_name.data_products.yaml            # Data products (optional)
├── component_name.data_dependencies.yaml        # Data dependencies (optional)
├── component_name.parameters.yaml               # Parameters (optional)
├── component_name.faults.yaml                   # Faults (optional)
├── component_name.packets.yaml                  # Packets (optional)
├── component-component_name-implementation.ads  # Handwritten spec
├── component-component_name-implementation.adb  # Handwritten body
└── test/                                        # See adamant-testing skill
```

**CRITICAL**: Do NOT create a `build/` directory manually.

## Workflow

```bash
redo templates && cp build/template/* .   # Generate and copy stubs
redo all                                  # Build
redo test                                 # Run tests
```

## Component Model (YAML)

```yaml
description: What this component does
execution: passive|active|either
with:                              # ONLY for preamble code visibility
  - "Interfaces"                   # Only include if preamble uses the package
preamble: |
  use Interfaces;
  subtype Custom_Type is Unsigned_8 range 1 .. 100;
connectors:
  - description: Purpose
    kind: recv_sync|recv_async|send|get|provide|service|modify|request|return
    type: Ada_Type
    return_type: Ada_Return_Type   # For service/request/get
    count: 0                       # 0=assembly-sized, 1=single (default), N=fixed
    priority: 0-255                # recv_async only
generic:
  parameters:
    - name: T
      formal_type: "type T is private;"
discriminant:
  parameters:
    - name: "Max_Count"
      type: "Natural"
init:
  parameters:
    - name: "Param"
      type: "Natural"
      default: "10"
      description: What this parameter does
interrupts:
  - name: Timer_Interrupt
subtasks:
  - name: Listener
```

## Feature Model Formats

```yaml
# commands.yaml — requires Command.T recv_sync + Command_Response.T send connectors
commands:
  - name: Set_Value
    description: Set the value
    arg_type: Packed_U32.T            # Omit for no-arg commands

# events.yaml — requires Event.T send connector
events:
  - name: Value_Changed
    description: The value was changed
    param_type: Packed_U32.T          # Omit for no-param events. MUST be packed type (not raw enums)

# data_products.yaml — requires Data_Product.T send connector
data_products:
  - name: Current_Value
    type: Packed_U32.T

# data_dependencies.yaml — requires Data_Product_Fetch.T/Return.T request + Sys_Time.T get
data_dependencies:
  - name: Sensor_Reading
    type: Sensor_Data.T

# parameters.yaml — requires Parameter_Update.T modify connector
parameters:
  - name: Start_Count
    type: Packed_U16.T
    default: "(Value => 0)"           # REQUIRED

# faults.yaml — requires Fault.T send connector
faults:
  - name: Bad_Value_Fault
    param_type: Packed_U32.T          # Optional

# packets.yaml
packets:
  - name: Status_Packet
    id: 7
    type: Status_Data.T

# enums.yaml
enums:
  - name: My_State
    literals:
      - name: Off
        value: 0
```

**Feature connectors are NOT auto-generated** — you MUST list them in component.yaml.

## Required Connectors for Feature Models

| Feature YAML | Required Connectors |
|---|---|
| `commands.yaml` | `Command.T` recv_sync + `Command_Response.T` send |
| `events.yaml` | `Event.T` send |
| `data_products.yaml` | `Data_Product.T` send |
| `faults.yaml` | `Fault.T` send |
| `parameters.yaml` | `Parameter_Update.T` modify |
| `data_dependencies.yaml` | `Data_Product_Fetch.T`/`Data_Product_Return.T` request + `Sys_Time.T` get |

## Connector Compatibility

```
send → recv_sync | recv_async    request → service
get  → return                    provide → modify
```

## Implementation Spec Pattern (Mandatory)

```ada
with Tick;        -- Only with connector/custom types you actually use
with Command;     -- Only if component has commands
package Component.My_Component.Implementation is
   type Instance is new My_Component.Base_Instance with private;  -- PUBLIC: opaque
   overriding procedure Init (Self : in out Instance; Param : in Natural);  -- IFF YAML has init:
private
   type Instance is new My_Component.Base_Instance with record    -- PRIVATE: fields
      My_Field : Interfaces.Unsigned_32 := 0;
   end record;
   -- Connector handlers
   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T);
   -- Command handlers (IFF commands.yaml exists)
   overriding procedure Command_T_Recv_Sync (Self : in out Instance; Arg : in Command.T);
   overriding function Set_Value (Self : in out Instance; Arg : in Packed_U32.T)
      return Command_Execution_Status.E;
   overriding procedure Invalid_Command (Self : in out Instance; Cmd : in Command.T;
      Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);
   -- Dropped handlers (EVERY send connector, can be "is null")
   overriding procedure Event_T_Send_Dropped (Self : in out Instance; Arg : in Event.T) is null;
end Component.My_Component.Implementation;
```

## Command_T_Recv_Sync Pattern (Required IFF commands.yaml)

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

## Command Handler Pattern

```ada
overriding function Set_Value (Self : in out Instance; Arg : in Packed_U32.T)
   return Command_Execution_Status.E is
   use Command_Execution_Status;
   The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
begin
   Self.Value := Arg.Value;
   Self.Event_T_Send_If_Connected (Self.Events.Value_Changed (The_Time, Arg));
   Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Current_Value (The_Time, Arg));
   return Success;
end Set_Value;
```

Commands with `arg_type:` get `Arg : in <arg_type>` parameter; without get no extra parameter.

## Generated Code API (Quick Reference)

See [references/generated-api.md](references/generated-api.md) for full details.

- Events: `Self.Event_T_Send_If_Connected (Self.Events.Name (The_Time, (Value => X)));`
- Data products: `Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Name (The_Time, Val));`
- Faults: `Self.Fault_T_Send_If_Connected (Self.Faults.Name (The_Time));`
- Time: `The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;`
- Send: use `*_Send_If_Connected` (safe) vs `*_Send` (asserts connected)

## Data Dependencies API

```ada
Status := Self.Get_Foo (Value => out_var, Stale_Reference => time, Timestamp => out_time);
-- Returns Data_Product_Enums.Data_Dependency_Status.E (Success | Not_Available | Stale | Error)
-- Need: use Data_Product_Enums; use Data_Product_Enums.Data_Dependency_Status;
```

Overrides (BOTH abstract, MUST implement):
```ada
overriding function Get_Data_Dependency (Self : in out Instance;
   Id : in Data_Product_Types.Data_Product_Id) return Data_Product_Return.T
   is (Self.Data_Product_Fetch_T_Request ((Id => Id)));
overriding procedure Invalid_Data_Dependency (Self : in out Instance;
   Id : in Data_Product_Types.Data_Product_Id; Ret : in Data_Product_Return.T);
```

## Parameter Overrides (ALL abstract IFF parameters.yaml exists)

```ada
overriding procedure Invalid_Parameter (Self : in out Instance; Par : in Parameter.T;
   Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);
-- Note: Par is Parameter.T, NOT Parameter_Update.T
overriding function Validate_Parameters (Self : in out Instance;
   P1 : P1_Type.U; P2 : P2_Type.U) return Parameter_Validation_Status.E
   is (Parameter_Validation_Status.Valid);
overriding procedure Update_Parameters_Action (Self : in out Instance) is null;
```

Call `Self.Update_Parameters` explicitly (e.g., in Tick handler).

## Execution Model

- **Passive**: Synchronous processing. Only has Init if YAML defines `init:` section.
- **Active**: Message queue. Init MUST call `Self.Init_Base(Queue_Size)` (bytes) — actually, queue setup is via `init_base` in assembly YAML, NOT a component Init procedure. Has `{Type}_T_Recv_Async` handlers and `{Type}_T_Recv_Async_Dropped` overflow handlers.
- Command connectors stay `recv_sync` even on active components.

## Auto-Provided Packages (Do NOT `with` these)

`Command_Execution_Status`, `Command_Response_Status`, `Unsigned_32`, `Parameter_Validation_Status`, `Command_Response`, `Event`, `Data_Product`, `Fault`, `Sys_Time`, `Basic_Types`, `Interfaces` (when commands/features use it).

Exception: If your component has no commands but needs Unsigned types, add `with Interfaces; use Interfaces;`.

## Framework Type Fields

Do NOT invent fields. Key types:
- `Packet.Header.Id` is `Packet_Types.Packet_Id` (Natural subtype, NOT Unsigned_16). Need `with Packet_Types; use type Packet_Types.Packet_Id;` for operators. Cast to `Unsigned_16` for packed params.
- `Command.Header.Id` is `Command_Types.Command_Id` (distinct type). Need `with Command_Types; use Command_Types;`
- `Packet_Header.T`: Time, Id, Sequence_Count (mod 2**14), Buffer_Length (Natural). NO Priority.
- `Event_Header.T`: Time, Id (U16), Param_Buffer_Length (U8). NO Severity.

**General rule:** Framework distinct types need `use type` for operator visibility (=, /=, <, etc.).

## Connector Count (Array Connectors)

`count: 0` or N = one-to-many fan-out with index:
- Generated index type: `<Type>_T_Send_Index`
- **Indices are 1-based** (`Connector_Index_Type'First = 1`). Map from 0-based with offset.
- Send: `Self.Packet_T_Send_If_Connected(Index, Arg)`
- Loop: `for I in Packet_T_Send_Index'Range loop`
- Dropped: takes extra `Index` parameter
- Two connectors of same type get numbered: `Event_T_Send` (1st), `Event_T_Send_2` (2nd)

## Pre-Flight Checklist

1. [ ] Spec uses `with private` / private full record pattern
2. [ ] `Init` override present IFF YAML has `init:` section
3. [ ] `Invalid_Command` (procedure, 4 params) present IFF `commands.yaml` exists
4. [ ] `Command_T_Recv_Sync` present IFF `commands.yaml` exists
5. [ ] ALL `*_Send_Dropped` handlers overridden for every send connector
6. [ ] NO `with` for auto-provided packages (see list above)
7. [ ] NO `build/` directory created manually
8. [ ] Empty `.all_path` file present
9. [ ] Entity names unique across events, data products, commands, faults, parameters
10. [ ] `use Command_Execution_Status;` INSIDE package body, not before it
11. [ ] `get` connectors: `return_type:` only. `request`: both `type:` and `return_type:`
12. [ ] Custom record fields have `format:` specified (see adamant-type-system)
13. [ ] Qualify ambiguous literals: `Command_Execution_Status.Success`
14. [ ] No `Packed_U8` — use `Packed_Byte.T`
15. [ ] No dynamic allocation (Ravenscar profile)
16. [ ] Active + recv_async: override `{Type}_T_Recv_Async_Dropped`
17. [ ] Parameter overrides: `Invalid_Parameter`, `Validate_Parameters`, `Update_Parameters_Action`
18. [ ] Data dependency overrides: `Get_Data_Dependency`, `Invalid_Data_Dependency`
19. [ ] Faults use event-like API: `Self.Fault_T_Send_If_Connected(Self.Faults.Name(Time))`
20. [ ] No `with Command_Response_Status` (not standalone — available through base class)
21. [ ] Component name doesn't collide with ~55 framework components
22. [ ] Custom type YAML filenames (e.g., `quaternion.record.yaml`) don't collide with framework types -- prefix with project/component name if needed
23. [ ] Use `or else` / `and then` (short-circuit) for ALL boolean expressions (Ada style requirement)
24. [ ] No trailing whitespace in Ada or YAML files
25. [ ] All YAML files start with `---` document start marker
26. [ ] Only `with` packages you actually reference -- unused `with` is a style warning
27. [ ] Verify with `redo style` -- all warnings must be resolved
28. [ ] Use `[]` for array aggregates: `[others => 0]` not `(others => 0)` (Ada 2022 syntax). Record aggregates MUST use `()`. Nested array-of-records: `[others => (others => <>)]`
29. [ ] Space before `(` in type conversions: `Unsigned_32 (X)` not `Unsigned_32(X)`
30. [ ] `then` on its own line for multi-line if conditions
31. [ ] Don't add `with Interfaces; use Interfaces;` to impl spec if base class already provides it (components with commands/init/data deps get it automatically). Note: some generated component specs have REDUNDANT `use Interfaces;` that triggers `-gnatwr` -- this is unfixable (code gen artifact, not your code).
32. [ ] No `pragma Unreferenced` unless variable is genuinely needed but intentionally unused
33. [ ] See `adamant-style` skill for full style reference
34. [ ] `Packed_F32.T.Value` is `Short_Float` (Ada 32-bit float), NOT `Interfaces.IEEE_Float_32` -- use `Short_Float` for F32 record fields and arithmetic

## Related Skills

- **Types**: [adamant-type-system](../adamant-type-system/SKILL.md)
- **Testing**: [adamant-testing](../adamant-testing/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
- **Algorithm wrapping**: [adamant-algorithm-wrapping](../adamant-algorithm-wrapping/SKILL.md)
