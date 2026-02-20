---
name: adamant-component-dev
description: Patterns and workflows for developing components in the Adamant embedded software framework. Use when creating component YAML models, writing implementation specs/bodies, defining connectors, commands, events, data products, parameters, or faults.
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

⚠️ **CRITICAL -- Implementation File Naming**: Files MUST be `component-<name>-implementation.ads/.adb` (with `component-` prefix and hyphens). Package declaration MUST be `Component.<Name>.Implementation`. The generated base class is `Component.<Name>`, NOT `<Name>`.

**CRITICAL**: Do NOT create a `build/` directory manually.

## Workflow

```bash
redo templates && cp build/template/* .   # Generate and copy stubs
redo all                                  # Build
redo test                                 # Run tests (see adamant-testing)
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
      default: "10"              # MUST be a string (quoted), even for integers
      description: What this parameter does
interrupts:
  - name: Timer_Interrupt
subtasks:
  - name: Listener
```

**CRITICAL -- `with` Field**: Only include packages used in **preamble/generated code**. Types used only in implementation `.ads/.adb` should be `with`'d there.

## Feature Model Formats

```yaml
# commands.yaml -- requires Command.T recv_sync + Command_Response.T send connectors
commands:
  - name: Set_Value
    description: Set the value
    arg_type: Packed_U32.T            # Omit for no-arg. Field is 'arg_type' NOT 'type'

# events.yaml -- requires Event.T send connector
# events use 'param_type', commands use 'arg_type' -- NEITHER uses plain 'type'
events:
  - name: Value_Changed
    description: The value was changed
    param_type: Packed_U32.T          # Omit for no-param. MUST be packed type

# data_products.yaml -- requires Data_Product.T send connector
# Do NOT add 'id:' fields -- IDs are auto-assigned. Only packets.yaml uses explicit 'id:'
data_products:
  - name: Current_Value
    type: Packed_U32.T

# data_dependencies.yaml -- requires Data_Product_Fetch.T/Return.T request + Sys_Time.T get
data_dependencies:
  - name: Sensor_Reading
    type: Sensor_Data.T

# parameters.yaml -- requires Parameter_Update.T modify connector
parameters:
  - name: Start_Count
    type: Packed_U16.T
    default: "(Value => 0)"           # REQUIRED - uses UNPACKED record syntax

# faults.yaml -- requires Fault.T send connector
faults:
  - name: Bad_Value_Fault
    param_type: Packed_U32.T          # Optional -- MUST fit within Fault.T buffer (~8-16 bytes)

# packets.yaml
packets:
  - name: Status_Packet
    id: 7
    type: Status_Data.T
```

**⚠️ CRITICAL -- Feature connectors are NOT auto-generated** -- you MUST explicitly list ALL required connectors in `component.yaml`. See table below.

## Required Connectors for Feature Models

| Feature YAML | Required Connectors |
|---|---|
| `commands.yaml` | `Command.T` recv_sync + `Command_Response.T` send |
| `events.yaml` | `Event.T` send |
| `data_products.yaml` | `Data_Product.T` send |
| `faults.yaml` | `Fault.T` send |
| `parameters.yaml` | `Parameter_Update.T` modify |
| `data_dependencies.yaml` | `Data_Product_Fetch.T`/`Data_Product_Return.T` request + `Sys_Time.T` get |

## Connector Kind Field Rules

| Kind | `type:` | `return_type:` |
|------|---------|----------------|
| `recv_sync`, `recv_async`, `send`, `provide`, `modify` | **required** | **forbidden** |
| `get`, `return` | **forbidden** | **required** |
| `request`, `service` | **required** | **required** |

**⚠️ COMMON PITFALL**: `get`/`return` use `return_type:` ONLY. Writing `type:` is a build error.

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

Use `Self.Execute_Command(Arg)` (NOT `Self.Process_Command`).

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

## Generated Code API (Quick Reference)

See [references/generated-api.md](references/generated-api.md) for full details.

- Events: `Self.Event_T_Send_If_Connected (Self.Events.Name (The_Time, (Value => X)));`
- Data products: `Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Name (The_Time, Val));`
- Faults: `Self.Fault_T_Send_If_Connected (Self.Faults.Name (The_Time));`
- Time: `The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;`
- Send: use `*_Send_If_Connected` (safe) vs `*_Send` (asserts connected)
- Connector call syntax: `Self.{Type}_T_{Kind}` (e.g., `Self.Sys_Time_T_Get`, `Self.Data_Product_Fetch_T_Request ((Id => Dp_Id))`)

## Data Dependencies API

```ada
-- Two overloads:
Status := Self.Get_Foo (Stale_Reference => time, Timestamp => out_time, Value => out_var);
Status := Self.Get_Foo (Stale_Reference => time, Value => out_var);  -- no timestamp
-- Returns Data_Product_Enums.Data_Dependency_Status.E (Success | Not_Available | Stale | Error)
```

**CRITICAL**: Body MUST include `with Data_Product_Enums; use Data_Product_Enums; use type Data_Product_Enums.Data_Dependency_Status.E;` for `=` operator visibility on status comparison.

Required overrides (BOTH abstract, MUST implement):
```ada
overriding function Get_Data_Dependency (Self : in out Instance;
   Id : in Data_Product_Types.Data_Product_Id) return Data_Product_Return.T
   is (Self.Data_Product_Fetch_T_Request ((Id => Id)));
overriding procedure Invalid_Data_Dependency (Self : in out Instance;
   Id : in Data_Product_Types.Data_Product_Id; Ret : in Data_Product_Return.T);
```

## Active Component Overrides

Active components MUST override abstract `Cycle` procedure. Every `recv_async` connector generates an abstract `*_Dropped` handler that MUST be overridden:

```ada
overriding procedure Cycle (Self : in out Instance);
overriding procedure Tick_T_Recv_Async_Dropped (Self : in out Instance; Arg : in Tick.T) is null;
```

Command connectors stay `recv_sync` even on active components. Queue size set via `init_base` in assembly YAML (see adamant-assembly-dev).

## Spec vs Body `with` Clauses

Only `with` in spec if the spec references the type. All others go in body. The implementation child package does NOT inherit `with`/`use` from the generated base class.

```ada
-- SPEC: with for types in declarations/signatures
with Tick; with Command;
-- BODY: with for implementation-only usage
with Sys_Time;
with Event_Types; use Event_Types;  -- 'use' needed for operator visibility on typed IDs
```

## Parameter Overrides (ALL abstract IFF parameters.yaml exists)

```ada
overriding procedure Parameter_Update_T_Modify (Self : in out Instance; Arg : in out Parameter_Update.T) is
begin Self.Process_Parameter_Update (Arg); end Parameter_Update_T_Modify;

overriding procedure Invalid_Parameter (Self : in out Instance; Par : in Parameter.T;
   Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);
overriding function Validate_Parameters (Self : in out Instance;
   P1 : P1_Type.U; P2 : P2_Type.U) return Parameter_Validation_Status.E
   is (Parameter_Validation_Status.Valid);
overriding procedure Update_Parameters_Action (Self : in out Instance) is null;
```

**Key rules:**
- `Self.<Param_Name>` returns `.U` (unpacked), NOT `.T`
- `Self.Update_Parameters` takes NO arguments — call in Tick handler
- Parameter `default:` uses unpacked syntax, NOT `Type.Pack(...)`
- Access via `Self.Kp` or `Self.Get_Kp` — NOT `Self.Parameters.Kp`
- **Parameter lifecycle**: `Process_Parameter_Update` validates then updates internal storage. After it returns, `Self.<Param>` reflects the new value immediately -- no tick required. `Update_Parameters_Action` is called at the END of the update cycle (use it for side effects like recalculating derived state). For passive/tickless components, parameters take effect as soon as the modify connector is invoked.

## Framework Type Fields & Common Pitfalls

- `Packet_Header.T`: Time, Id (`Packet_Types.Packet_Id` = Natural subtype), Sequence_Count (mod 2**14), Buffer_Length. NO Priority.
- `Event_Header.T`: Time, Id (U16), Param_Buffer_Length (U8). NO Severity.
- `Command.Header.Id` is `Command_Types.Command_Id` (distinct type). Need `use Command_Types;` for operators.
- ⚠️ `Packed_Byte.T` NOT `Packed_U8.T` — framework has no `Packed_U8`
- ⚠️ `Packed_F32.T.Value` is `Short_Float`, NOT `Interfaces.IEEE_Float_32`
- ⚠️ Math: use `Ada.Numerics.Elementary_Functions` (Long_Float) or `Generic_Elementary_Functions` (Short_Float). `Interfaces` has NO math.
- Record fields with plain Ada types accessed directly; only `Packed_*` types have `.Value`
- `Natural` needs 31 bits — does NOT fit U16 format. Use `Interfaces.Unsigned_16`.
- Enum literals must NOT collide with framework package names (e.g., `Fault` → `Faulted`)

## Auto-Provided Packages (Do NOT `with` these)

`Command_Execution_Status`, `Command_Response_Status`, `Unsigned_32`, `Parameter_Validation_Status`, `Command_Response`, `Event`, `Data_Product`, `Fault`, `Sys_Time`, `Basic_Types`, `Interfaces` (when commands/features use it).

**HOWEVER**: Implementation child package does NOT inherit these — `with` explicitly if your code references them directly.

## Connector Count (Array Connectors)

- `count: 0` or N = one-to-many with index. Index type: `<Type>_T_Send_Index`, **1-based**.
- Send: `Self.Packet_T_Send_If_Connected(Index, Arg)`
- Two connectors of same type get numbered: `Event_T_Send` (1st), `Event_T_Send_2` (2nd) — each needs its own `*_Dropped` handler

## Pre-Flight Checklist

1. [ ] Spec: `with private` / private full record pattern
2. [ ] `Init` override IFF YAML has `init:`; `Cycle` override IFF active component
3. [ ] `Set_Up` override (optional) — for post-init work (command registration, initial DPs)
4. [ ] `Invalid_Command` + `Command_T_Recv_Sync` IFF `commands.yaml` exists
5. [ ] ALL `*_Send_Dropped` handlers for every send connector; `*_Recv_Async_Dropped` for every recv_async
6. [ ] NO `with` for auto-provided packages; NO `build/` dir; empty `.all_path` present
7. [ ] Entity names unique across events/DPs/commands/faults/parameters
8. [ ] `get`: `return_type:` only. `request`: both `type:` and `return_type:`
9. [ ] Custom record fields have `format:` (see adamant-type-system)
10. [ ] No `Packed_U8` (use `Packed_Byte.T`); no `Packed_Bool` (use `Packed_Boolean.T`); no dynamic allocation (Ravenscar)
11. [ ] Component name must NOT match any of ~58 framework built-in names (see adamant-framework-components catalog). E.g., `command_sequencer`, `event_filter`, `fault_counter` are taken.
11. [ ] Parameter overrides: `Parameter_Update_T_Modify`, `Invalid_Parameter`, `Validate_Parameters`, `Update_Parameters_Action`
12. [ ] Data dep overrides: `Get_Data_Dependency`, `Invalid_Data_Dependency`; names must match YAML exactly
13. [ ] Faults API: `Self.Fault_T_Send_If_Connected(Self.Faults.Name(Time))`
14. [ ] Component/type names globally unique — no collision with ~58 framework components
15. [ ] Style: `or else`/`and then`, no trailing whitespace, `---` YAML start, `[]` for arrays, space before `(` in conversions, `then` on own line, `use Command_Execution_Status;` INSIDE body
16. [ ] `Ignore : Type renames Arg;` for unused params (not `pragma Unreferenced`)
17. [ ] See `adamant-style` skill for full style reference; `redo style` to verify

## References
- [references/generated-api.md](references/generated-api.md) — Generated code API details
- [references/implementation-patterns.md](references/implementation-patterns.md) — Ada patterns from real components
- [references/lasel-reference.md](references/lasel-reference.md) — LASEL command sequence language
- [references/template-analysis.md](references/template-analysis.md) — Code generation edge cases

## Related Skills

- **Types**: [adamant-type-system](../adamant-type-system/SKILL.md)
- **Testing**: [adamant-testing](../adamant-testing/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
- **Build**: [adamant-build-system](../adamant-build-system/SKILL.md)
- **Algorithm wrapping**: [adamant-algorithm-wrapping](../adamant-algorithm-wrapping/SKILL.md)
