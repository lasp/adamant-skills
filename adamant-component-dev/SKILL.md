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
├── component-component_name-implementation.ads  # Generated stub (admt templates), then edited
├── component-component_name-implementation.adb  # Generated stub (admt templates), then edited
└── test/                                        # See adamant-testing skill
```

⚠️ **CRITICAL -- Implementation File Naming**: The YAML `name:` field (snake_case) maps to a CamelCase Ada identifier. File names use the **lowered CamelCase** with hyphens as separators:
- YAML name `safe_survival_heater_ctrl` -> Ada identifier `Safe_Survival_Heater_Ctrl` -> package `Component.Safe_Survival_Heater_Ctrl`
- File: `component-safe_survival_heater_ctrl-implementation.ads/.adb`
- Package declaration: `package Component.Safe_Survival_Heater_Ctrl.Implementation is`
- End statement: `end Component.Safe_Survival_Heater_Ctrl.Implementation;`

**The Ada identifier preserves underscores from the YAML name.** Do NOT remove underscores (e.g., `SafeSurvivalHeaterCtrl` is WRONG -- it becomes a different Ada identifier and the file name won't match). The YAML snake_case name IS the Ada identifier (with first-letter capitalization of each word). Getting this wrong is the #1 cold-start error.

**CRITICAL**: Do NOT create a `build/` directory manually.

**The `*-implementation.{ads,adb}` files start as stubs generated from the YAML by `admt templates`** (or by the one-shot `adamant_scaffold.py` tool from `adamant-tools`, which produces YAML + impl stubs in one step from a spec). You edit the body to add logic. Do NOT hand-write them from scratch -- the package declaration, base-class derivation, and connector handler signatures are derived from `*.component.yaml`, and writing them manually risks signature drift from the generated base class.

## Workflow

The component lifecycle goes YAML -> generated stubs -> edited impl -> build/test:

```bash
# 1. Write *.component.yaml (and any feature YAMLs: commands, events, data_products, ...).
# 2. Generate impl spec + body stubs from the YAML and copy them into the component dir.
#    Required after the YAML stabilizes -- do NOT hand-write .ads/.adb from scratch.
admt -y templates                         # redo templates + admt's stub copy

# 3. Edit component-<name>-implementation.adb to fill in handler bodies.
# 4. Build and test.
admt build                                # redo all
admt test                                 # redo test (run from test/ dir)
```

**⚠️ CRITICAL -- Always start from generated templates**: Run `admt templates` and copy the generated `.ads/.adb` stubs BEFORE writing any implementation code. The templates contain required comments, formatting, and exact procedure signatures. Never write implementation spec/body files from scratch -- always edit the generated stubs. Skipping this step is a common source of missing comments, wrong signatures, and formatting mismatches.

If you use the `adamant_scaffold.py` tool (see `adamant-tools`), it produces YAML and impl stubs in one step from a spec file -- equivalent to step 1 + step 2 combined. After that, jump to step 3.

Re-run `admt templates` whenever you change the YAML in a way that affects the generated impl signature (new connectors, new commands, new event handlers). admt backs up the existing impl and copies the new stubs; use `admt templates --undo` to restore if needed.

## Component Model (YAML)

```yaml
description: What this component does
execution: passive|active|either
with:                              # ONLY for preamble code visibility
  - "Interfaces"                   # Only include if preamble uses the package
without:                           # Remove auto-deduced with statements (rare)
  - "Some_Package"                 # Use when generator adds unwanted dependency
preamble: |                        # Omit entirely if not needed (do NOT use `preamble: | null;`)
  use Interfaces;
  subtype Custom_Type is Unsigned_8 range 1 .. 100;
connectors:
  - description: Purpose
    kind: recv_sync|recv_async|send|get|provide|service|modify|request|return
    type: Ada_Type
    return_type: Ada_Return_Type   # For service/request/get
    count: 0                       # 0=assembly-sized, 1=single (default), N=fixed
    # count: 0 → generates init_base *_Count param (assembly sets size)
    # count: N (N>0) → fixed at compile time, NO init_base param, NO *_Count in assembly
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
```ada

**CRITICAL -- Component YAML `with` Field**: Only include types that are directly used in the **GENERATED** base class spec (usually in the preamble). Types used only in your implementation `.ads/.adb` should be `with`'d there instead:

```yaml
# CORRECT: Only include packages used in preamble/generated code
with:
  - "Interfaces"                   # Used in preamble for Unsigned_8
  
# WRONG: Including packages only used in implementation
with:
  - "Ada.Numerics.Elementary_Functions"  # Only used in implementation body
```ada

This avoids unreferenced package warnings and keeps generated code clean.

**Plain ASCII only in model text**: Every `description:` in component and feature model YAML must be plain ASCII. Text pasted from ICDs or datasheets often carries curly quotes, em dashes, and micro signs -- replace them with `"`, `'`, `--`, and `u`. These descriptions flow into generated command/telemetry definitions that ground tooling (OpenC3 COSMOS) validates as US-ASCII and rejects.

## Feature Model Formats

```yaml
# commands.yaml -- requires Command.T recv_sync + Command_Response.T send connectors
commands:
  - name: Set_Value
    description: Set the value
    arg_type: Packed_U32.T            # Omit for no-arg commands. FIELD IS 'arg_type' NOT 'type'

# events.yaml -- requires Event.T send connector
# NOTE: events use 'param_type', commands use 'arg_type' -- NEITHER uses plain 'type'
events:
  - name: Value_Changed
    description: The value was changed
    param_type: Packed_U32.T          # Omit for no-param events. MUST be packed type (not raw enums)

# data_products.yaml -- requires Data_Product.T send connector
# NOTE: Do NOT add 'id:' fields to commands, events, data_products, or faults -- IDs are auto-assigned.
# Only packets.yaml uses explicit 'id:' fields.
data_products:
  - name: Current_Value
    type: Packed_U32.T
# CONSTRAINT: DP types must be FIXED-SIZE and their serialized byte size must fit
# within `data_product_buffer_size` (set in assembly config, typically 32 bytes).
# Variable-length packed types CANNOT be used as data products.

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
    param_type: Packed_U32.T          # Optional -- MUST fit within Fault.T buffer

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

**⚠️ CRITICAL -- Feature connectors are NOT auto-generated** -- you MUST explicitly list ALL required connectors in `component.yaml` `connectors:` section. Having `commands.yaml` does NOT add a `Command.T recv_sync` connector automatically. You must write it yourself. Same for events, data products, faults, parameters, and data dependencies. See table below.

**CRITICAL -- Fault Param Size Limit**: Fault argument types (`param_type`) must fit within the `Fault.T` buffer (typically ~8-16 bytes). Large packed records (e.g., 10+ bytes) will cause a compile error:
```
Error: Size of parameter buffer exceeds Fault.T buffer size
```ada
Use small types like `Packed_U16.T`, `Packed_U32.T`, or custom packed types < 8 bytes.

**CRITICAL -- Event Param Size Limit**: Event `param_type` types must serialize to <= the event buffer size (typically ~32 bytes). Large packed records will cause a compile error similar to faults. Use a smaller summary type or omit `param_type` for events that would exceed the buffer.

## Required Connectors for Feature Models

| Feature YAML | Required Connectors |
|---|---|
| `commands.yaml` | `Command.T` recv_sync + `Command_Response.T` send |
| `events.yaml` | `Event.T` send |
| `data_products.yaml` | `Data_Product.T` send |
| `faults.yaml` | `Fault.T` send |
| `parameters.yaml` | `Parameter_Update.T` modify |
| `data_dependencies.yaml` | `Data_Product_Fetch.T`/`Data_Product_Return.T` request + `Sys_Time.T` get |

**`Sys_Time.T` get is required by almost every component** -- events, data products, faults, and commands all call `Self.Sys_Time_T_Get`. Always include it in your connector list. The only components that might omit it are pure data-pass-through components with no timestamped outputs.

## Connector Design Guidelines

When designing a component's connector topology, choose the right connector kind for each data flow:

- **`send` -> `recv_sync`/`recv_async`**: Use for **inter-component data flow**. When component A produces data that component B must process, A needs a `send` connector and B needs a `recv_sync` or `recv_async`. This is the primary mechanism for wiring components together in an assembly.
- **Data products** (`Data_Product.T send`): Use for **ground observability and telemetry**. Data products are stored in the Product_Database for ground retrieval. They are NOT a substitute for inter-component data flow. If another component needs your output, use a `send` connector.
- **`request`/`provide`**: Use for **on-demand queries** where the requester controls timing. The provider serves data when asked, not when it changes.
- **`get`/`return`**: Use for **simple lookups** (typically Sys_Time).

**Common design mistake**: Using data products as the only output mechanism. If your component produces results consumed by another component, you MUST have a `send` connector for that data in addition to any data products. Data products go to the ground; send connectors go to downstream components. A component that only publishes data products cannot be wired to consumers in an assembly.

## Connector Kind Field Rules

| Kind | `type:` field | `return_type:` field |
|------|--------------|---------------------|
| `recv_sync` | **required** | **forbidden** |
| `recv_async` | **required** | **forbidden** |
| `send` | **required** | **forbidden** |
| `provide` | **required** | **forbidden** |
| `modify` | **required** | **forbidden** |
| `get` | **forbidden** | **required** |
| `return` | **forbidden** | **required** |
| `request` | **required** | **required** |
| `service` | **required** | **required** |

**⚠️ COMMON PITFALL**: `get` and `return` connectors use `return_type:` ONLY. Writing `type:` on a `get` or `return` connector is a build error ("Connector is of kind 'return' which forbids the field: 'type'"). Only `request` and `service` use BOTH `type:` and `return_type:`.

## Connector Call Syntax

```ada
-- send: Self.Event_T_Send_If_Connected (Arg);
-- get (no argument): The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
-- request (takes argument): Result := Self.Data_Product_Fetch_T_Request ((Id => Dp_Id));
```

## Connector Compatibility

```
send → recv_sync | recv_async    request → service
get  → return                    provide → modify
```ada

## Implementation Spec Pattern (Mandatory)

```ada
with Tick;        -- Only with connector/custom types you actually use
with Command;     -- Only if component has commands
with My_Enums;    -- Custom enum packages need explicit with

-- ⚠️ ENUM TYPE PATTERN: Adamant enums use nested package + .E suffix.
-- Declaration: `My_Enums.My_State.E` (NOT `My_Enums.My_State`)
-- Pos/Val: `My_Enums.My_State.E'Pos(X)`, `My_Enums.My_State.E'Val(N)`
-- Use clause: `use My_Enums.My_State;` makes literals (Off, On) visible unqualified
-- Record field type: `My_Enums.My_State.E := My_Enums.My_State.Off`

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

## Implementation Body -- Context Clauses

**⚠️ Do NOT blindly copy `with Interfaces; use Interfaces;` from existing components.** Components with commands or parameters auto-provide `with Interfaces; use Interfaces;` in the generated base class. Adding it again in your body causes a `-gnatwr` redundant use-clause warning that fails style checks.

**Quick rule:** If your component has `commands.yaml` or `parameters.yaml`, `Interfaces` is already visible -- do NOT add it to your implementation body. If your component has NEITHER and needs Unsigned types, add `with Interfaces; use Interfaces;` in the body. See the decision table in "Auto-Provided Packages" below for the full matrix.

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
```ada

Use `Self.Execute_Command(Arg)` (NOT `Self.Process_Command`). Returns `Command_Response_Status.E` (visible via `use Command_Enums;` in generated base -- do NOT add `with Command_Response_Status;`, it is not a standalone package).

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
```ada

Commands with `arg_type:` get `Arg : in <arg_type>` parameter; without get no extra parameter.

**Variable-length command args**: When a command's `arg_type` is a variable-length type (has a variable-size field), the generated handler signature changes: instead of `function Handler_Name (Self : in out Instance; Arg : in My_Type.T) return Command_Execution_Status.E`, you get `function Handler_Name (Self : in out Instance; Arg : in Command.T) return Command_Execution_Status.E` with raw `Command.T`. You must deserialize manually:
```ada
declare
   use My_Type.Serialization;
   Deser_Arg : My_Type.T;
   Bytes_Used : Natural;
   Status : constant Serialization_Status := From_Byte_Array (
      Arg.Arg_Buffer (Arg.Arg_Buffer'First .. Arg.Arg_Buffer'First + Arg.Header.Arg_Buffer_Length - 1),
      Deser_Arg, Bytes_Used);
begin
   if Status /= Success then return Command_Execution_Status.Failure; end if;
   -- use Deser_Arg...
end;
```

**`use Command_Execution_Status` scope**: The generated base class may already `use Command_Execution_Status` in the body scope. If adding `use Command_Execution_Status;` inside your handler causes a "has no effect" warning, remove it -- the parent scope already provides it. When in doubt, qualify: `Command_Execution_Status.Success`.

## Generated Code API (Quick Reference)

See [references/generated-api.md](references/generated-api.md) for full details.

- Events: `Self.Event_T_Send_If_Connected (Self.Events.Name (The_Time, (Value => X)));`
- Data products: `Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Name (The_Time, Val));`
- Faults: `Self.Fault_T_Send_If_Connected (Self.Faults.Name (The_Time));`
- Time: `The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;`
- Send: use `*_Send_If_Connected` (safe) vs `*_Send` (asserts connected)

## Data Dependencies API

```ada
-- Two overloads:
Status := Self.Get_Foo (Stale_Reference => time, Timestamp => out_time, Value => out_var);
Status := Self.Get_Foo (Stale_Reference => time, Value => out_var);  -- no timestamp
-- Stale_Reference is IN (you provide it), Value is OUT, Timestamp is OUT
-- Returns Data_Product_Enums.Data_Dependency_Status.E (Success | Not_Available | Stale | Error)
```

**CRITICAL -- Data Dependency Status Checking**: `Data_Dependency_Status` is defined in `Data_Product_Enums`. Your component implementation body MUST include:

```ada
with Data_Product_Enums; use Data_Product_Enums; use type Data_Product_Enums.Data_Dependency_Status.E;
```

The `use type` is required for `=` operator visibility on status comparison. Compare against `Data_Dependency_Status.Success`:

```ada
if Status = Data_Dependency_Status.Success then
  -- Process valid data
end if;
```

Overrides (BOTH abstract, MUST implement):
```ada
overriding function Get_Data_Dependency (Self : in out Instance;
   Id : in Data_Product_Types.Data_Product_Id) return Data_Product_Return.T
   is (Self.Data_Product_Fetch_T_Request ((Id => Id)));
overriding procedure Invalid_Data_Dependency (Self : in out Instance;
   Id : in Data_Product_Types.Data_Product_Id; Ret : in Data_Product_Return.T);
```ada

## Active Component Overrides

Active components have a `Cycle` procedure that runs on their task's schedule. It is abstract and MUST be overridden:

```ada
overriding procedure Cycle (Self : in out Instance);
```ada

Use `Cycle` for periodic background work (polling, housekeeping). Most active components also receive ticks via `recv_sync` connectors for rate-group-driven work -- `Cycle` is separate from tick handling.

## Implementation Patterns Quick Reference

**Deserializing packed types from byte arrays** -- use the generated `Serialization` package, never manual byte extraction:
```ada
-- CORRECT:
Val : constant Packed_U16.T := Packed_U16.Serialization.From_Byte_Array (Data (0 .. 1));
-- WRONG: manual Shift_Left/or
Val := Unsigned_16 (Shift_Left (Unsigned_16 (Data (0)), 8) or Unsigned_16 (Data (1)));
```

**Memory deallocation** -- never use `Ada.Unchecked_Deallocation` (violates Ravenscar). Use `Safe_Deallocator.Deallocate_If_Testing` which frees in test builds, is null on bareboard:
```ada
procedure Free is new Safe_Deallocator.Deallocate_If_Testing (My_Array, My_Array_Access);
Free (Self.Buffer);
```

**Standalone helper packages** -- use `tagged limited private` for the Instance type so callers can use dot notation (`Self.Buffer.Create (Size)` vs `My_Pkg.Create (Self.Buffer, Size)`).

**Assertions** -- no string messages (saves binary space). Put explanation in a comment above:
```ada
-- Destinations must not be null:
pragma Assert (Entry.Destinations /= null);
```

**Data product counters** -- use `Interfaces.Unsigned_32` (matches `Packed_U32.T` directly, no type conversion needed). Use `@` syntax: `Self.Count := @ + 1;`

**Dispatching on an enumeration** -- use `case`, never an `if`/`elsif` chain of equality tests. Handler bodies dispatch on enums constantly (command status, connector status, mode and state enums), and a `case` is compiler-checked for totality: a literal added to the YAML enum later breaks every unhandled dispatch instead of falling silently into `else`:
```ada
-- CORRECT: adding a literal to the enum breaks this until handled
case Status is
   when Success => ...
   when Stale => ...
   when Not_Available | Error => ...
end case;
-- WRONG: silently absorbs a future literal
if Status = Success then ... elsif Status = Stale then ... else ... end if;
```
Avoid `when others` on an enum case for the same reason. An `if`/`elsif` chain is correct only where `case` is not legal -- matching against non-static values such as configured limits or stored ids -- and in that shape, return a decision enum so callers `case` over it. See `adamant-style` for the full rule.

See `references/implementation-patterns.md` for detailed examples of each pattern.

## Spec vs Body `with` Clauses

Only `with` packages in the **spec** (`.ads`) if the spec references them (e.g., type declarations, overriding subprogram parameter types). All other `with` clauses go in the **body** (`.adb`). Unused `with` in either file triggers a style warning (`-gnatwr`).

**Ada child packages inherit parent `with`/`use` visibility.** The implementation child package CAN see packages `with`'d by the generated base class spec. However, only add `with` in your spec for types you declare in signatures; add `with` in your body for types only used in the body. Do NOT re-`with`/`use` packages already visible from the base class (e.g., `Interfaces` when the base already has it) -- this causes redundant `-gnatwr` warnings.

**Types in feature YAMLs are auto-visible via generated API.** Types referenced in `data_products.yaml`, `events.yaml`, `faults.yaml`, etc. are accessed through the generated `Self.Data_Products.*`, `Self.Events.*`, `Self.Faults.*` functions. You do NOT need to `with` these types in your implementation body -- the generated base class already imports them. Adding an explicit `with` for a type only used via `Self.Data_Products.Name(...)` will trigger an unused unit warning.

```ada
-- SPEC (.ads): with packages for types used in declarations/signatures
with Tick;            -- needed for Tick_T_Recv_Sync signature
with Command;         -- needed for Command_T_Recv_Sync signature

-- BODY (.adb): with packages used only in implementation
with Sys_Time;        -- used in body logic
with Event_Types; use Event_Types;  -- need 'use' for operator visibility on typed IDs
-- Do NOT re-with packages already with'd in spec
-- When comparing framework typed IDs (Event_Id, Command_Id, etc.), you need
-- 'use <Type_Package>;' to make comparison operators visible.

-- GNAT warning: "modified by call, but value might not be referenced"
-- Triggered when a data dependency out-parameter is declared in the declarative
-- region but only used conditionally. Fix: move the Get call into the statements
-- section, or use the value unconditionally (e.g., store to a record field).
```ada

## Parameter Overrides (ALL abstract IFF parameters.yaml exists)

Components with `parameters.yaml` generate a `modify` connector that MUST be overridden:

```ada
-- REQUIRED: modify connector handler (abstract, must override)
overriding procedure Parameter_Update_T_Modify (Self : in out Instance; Arg : in out Parameter_Update.T) is
begin
   Self.Process_Parameter_Update (Arg);
end Parameter_Update_T_Modify;
```

Additional abstract overrides:
```ada
overriding procedure Invalid_Parameter (Self : in out Instance; Par : in Parameter.T;
   Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);
-- Note: Par is Parameter.T, NOT Parameter_Update.T
overriding function Validate_Parameters (Self : in out Instance;
   My_Param_1 : My_Param_1_Type.U; My_Param_2 : My_Param_2_Type.U) return Parameter_Validation_Status.E
   is (Parameter_Validation_Status.Valid);
-- NOTE: Parameter names match YAML parameter names exactly (not P1/P2). Types are unpacked (.U).
-- ⚠️ CRITICAL: Use the EXACT YAML parameter name -- no abbreviations, no prefix stripping.
-- Example: if YAML names a parameter `Pressure_High_Limit`, the Validate_Parameters argument
-- MUST be `Pressure_High_Limit : Packed_F32.U`, NOT `High_Limit` or `Limit`. The same exact
-- name is used to access it in the body: `Self.Pressure_High_Limit` (not `Self.High_Limit`).
-- When overriding with a body instead of expression function and Self is unused:
--   pragma Unreferenced (Self);  -- CORRECT
--   Ignore : constant Instance := Self;  -- WRONG: Instance is limited, violates Ravenscar
overriding procedure Update_Parameters_Action (Self : in out Instance) is null;
```ada

**Parameter access returns UNPACKED (.U)**: `Self.<Param_Name>` returns `<Type>.U` (unpacked), NOT `<Type>.T` (packed). Use `.U` for local variables when reading parameters:
```ada
Gain_Value : Packed_F32.U := Self.Gain;  -- CORRECT: .U (unpacked)
-- WRONG: Gain_Value : Packed_F32.T := Self.Gain;  -- type mismatch!
```

**Parameter lifecycle**: `Process_Parameter_Update` handles staging and validation. However, staged parameters are NOT applied until `Self.Update_Parameters` is called. Components MUST call `Self.Update_Parameters` at the start of their primary processing handler -- Tick handler for active/ticked components, recv_sync handler for passive/tickless components. Without this call, parameter updates will never take effect. `Update_Parameters_Action` is called at the END of the update cycle (use it for side effects like recalculating derived state).

⚠️ **CRITICAL -- Self.Update_Parameters ordering**: Components with parameters MUST call `Self.Update_Parameters` BEFORE reading any parameter values. This applies to Tick handlers, recv_sync handlers, and any handler that uses parameter values. Without this call, parameter updates staged via the tester's 3-step protocol (Stage/Validate/Update) will NEVER take effect. This is the #1 missed step in parameter-using components.

**Ada constraint:** Constants declared in the declarative region (before `begin`) capture values at elaboration time -- BEFORE any statements execute. If you declare `Kp : constant := Self.Kp.Value;` in the declarative region, it captures the STALE pre-update value.

```ada
-- WRONG: parameter read in declarative region captures stale value
overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
   Kp : constant Short_Float := Self.Kp.Value;  -- STALE!
begin
   Self.Update_Parameters;  -- Too late, Kp already captured
end Tick_T_Recv_Sync;

-- RIGHT: use a declare block AFTER Update_Parameters
overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
begin
   Self.Update_Parameters;  -- MUST be first statement
   declare
      Kp : constant Short_Float := Self.Kp.Value;  -- Fresh value
   begin
      -- Use Kp here
   end;
end Tick_T_Recv_Sync;

-- ALSO RIGHT: read directly in expressions (no constant needed)
overriding procedure Packed_F32_T_Recv_Sync (Self : in out Instance; Arg : in Packed_F32.T) is
begin
   Self.Update_Parameters;
   if Arg.Value > Self.Pressure_High_Limit.Value then  -- Always fresh
      -- ...
   end if;
end Packed_F32_T_Recv_Sync;
```

⚠️ **CRITICAL - Parameter Defaults Use Unpacked Syntax**: Parameter `default:` values use the unpacked record syntax directly (e.g., `"(Kp => (Value => 1.0), Ki => (Value => 0.1))"`), NOT `Type.Pack(...)`. The code generation wraps the packing automatically:

```yaml
# CORRECT: Use unpacked record syntax in defaults
parameters:
  - name: Pid_Gains
    type: Pid_Gains.T
    default: "(Kp => (Value => 1.0), Ki => (Value => 0.1))"

# WRONG: Do not use Type.Pack in defaults
    default: "Pid_Gains.Pack((Kp => (Value => 1.0), Ki => (Value => 0.1)))"
```ada

**CRITICAL -- Parameter Access Pattern**: Parameters are NOT accessed via `Self.Parameters`. They are accessed via generated getter functions. The accessor name is the **exact YAML parameter name** -- no abbreviations, no prefix stripping:

```ada
-- WRONG: Parameters record does not exist
Value := Self.Parameters.Kp;

-- WRONG: Abbreviating a compound name
-- If YAML says `Pressure_High_Limit`, this is WRONG:
if Arg.Value > Self.High_Limit.Value then ...

-- CORRECT: Generated getter uses exact YAML name
Value := Self.Kp;                          -- for param named `Kp`
Value := Self.Pressure_High_Limit.Value;   -- for param named `Pressure_High_Limit`
-- OR (alternate form)
Value := Self.Get_Kp;
```ada

Parameters with defaults can be retrieved without initialization. Parameters without defaults must be set via parameter update before access.

## Execution Model

- **Passive**: Synchronous processing. Only has Init if YAML defines `init:` section.
- **Active**: Has message queue. Queue size is set via `init_base` in **assembly YAML** (not component Init). Has `{Type}_T_Recv_Async` handlers and `{Type}_T_Recv_Async_Dropped` overflow handlers.
- Command connectors stay `recv_sync` even on active components.

**CRITICAL -- Active Component Dropped Handlers**: Every `recv_async` connector generates an abstract `*_Dropped` handler that MUST be overridden. Common pattern:

```ada
overriding procedure Tick_T_Recv_Async_Dropped (Self : in out Instance; Arg : in Tick.T) is null;
overriding procedure Data_Product_T_Recv_Async_Dropped (Self : in out Instance; Arg : in Data_Product.T) is null;
```yaml

Failure to override these results in abstract subprogram compile errors.

## Auto-Provided Packages (Do NOT `with` these)

`Command_Execution_Status`, `Command_Response_Status`, `Unsigned_32`, `Parameter_Validation_Status`, `Command_Response`, `Event`, `Data_Product`, `Fault`, `Sys_Time`, `Basic_Types`, `Interfaces` (when the generated base class references Interfaces types -- e.g., command args use Unsigned_32, or data deps use Interfaces types).

Exception: `Interfaces` is NOT auto-provided merely because `init:` exists. It is only auto-provided when the generated base class actually references Interfaces types (commands with Unsigned args, certain features). If your component has no commands but needs Unsigned types (including init with only `Natural` params), add `with Interfaces; use Interfaces;`.

**Decision table -- when is `Interfaces` auto-provided?**
| Has commands with Unsigned args? | Has data deps using Interfaces types? | Has features referencing Interfaces? | Auto-provided? |
|---|---|---|---|
| Yes | any | any | YES |
| No | Yes | any | YES |
| No | No | Yes | YES |
| No | No | No | **NO** -- add `with Interfaces; use Interfaces;` manually |

If your component has NONE of {commands, init with typed Interfaces params, data dependencies using Interfaces types, features referencing Interfaces}, then `Interfaces` is NOT auto-provided.

**CRITICAL -- Math Functions**: Ada's `Interfaces` package has NO math functions (Sqrt, Sin, Cos, etc.). Use:
- `Ada.Numerics.Elementary_Functions` for `Long_Float` (64-bit) math
- `Ada.Numerics.Generic_Elementary_Functions` instantiated for `Short_Float` (32-bit)

```ada
-- For Long_Float:
with Ada.Numerics.Elementary_Functions;
Result := Ada.Numerics.Elementary_Functions.Sqrt (Value);

-- For Short_Float:
with Ada.Numerics.Generic_Elementary_Functions;
package Short_Float_Math is new Ada.Numerics.Generic_Elementary_Functions (Short_Float);
Result := Short_Float_Math.Sqrt (Value);
```ada

## Framework Type Fields

Do NOT invent fields. Key types:
- `Packet.Header.Id` is `Packet_Types.Packet_Id` (Natural subtype, NOT Unsigned_16). Need `with Packet_Types; use type Packet_Types.Packet_Id;` for operators. Cast to `Unsigned_16` for packed params.
- `Command.Header.Id` is `Command_Types.Command_Id` (distinct type). Need `with Command_Types; use Command_Types;`
- `Packet_Header.T`: Time, Id, Sequence_Count (mod 2**14), Buffer_Length (Natural). NO Priority.
- `Event_Header.T`: Time (Sys_Time.T), Id (`Event_Types.Event_Id`, distinct type -- cast to `Unsigned_16` for packed params), Param_Buffer_Length (`Natural` subtype, NOT U8 -- cast to `Unsigned_8` if needed). NO Severity. Need `with Event_Types;` for `Event_Id`.
- `Fault_Header.T`: Time (Sys_Time.T), Id (Fault_Types.Fault_Id, U16), Param_Buffer_Length (U8). Access via `Arg.Header.Id`, `Arg.Header.Time`.
- `Fault.T`: Header (Fault_Header.T) + Param_Buffer (variable-length byte buffer). Need `with Fault_Types;` for `Fault_Id`.

⚠️ **CRITICAL - Packed_U8 Does Not Exist**: The framework type is `Packed_Byte.T` (NOT `Packed_U8.T`). Sub-agents consistently get this wrong:

```yaml
# WRONG: Packed_U8 does not exist
param_type: Packed_U8.T

# CORRECT: Use Packed_Byte.T
param_type: Packed_Byte.T
```

**General rule:** Framework distinct types need `use type` for operator visibility (=, /=, <, etc.).

### Record Type Field Access

- **Record type fields vs packed type fields**: Custom record types defined in `*.record.yaml` with plain Ada types (Short_Float, Interfaces.Unsigned_16, etc.) produce record fields that are accessed directly (e.g., `My_Record.Temperature`). Only Packed_* types (Packed_F32.T, Packed_U16.T, etc.) have a `.Value` accessor. Do NOT use `.Value` on plain record fields.

## Named Connectors (Custom Names)

When `name:` is specified on a connector, it **replaces the entire auto-generated name** (NOT just a prefix):
```yaml
  - name: High_Priority       # Custom name
    kind: send
    type: Packet.T
```
Generated API uses the custom name directly:
- Send method: `Self.High_Priority(Arg)` / `Self.High_Priority_If_Connected(Arg)`
- Dropped handler: `High_Priority_Dropped(Self, Arg)`
- Tester history: `High_Priority_Reciprocal_History` (named connectors use `_Reciprocal_History`, NOT `_Recv_Sync_History`)
- Connection check: `Self.Is_High_Priority_Connected`

**NOT** `High_Priority_T_Send_If_Connected` -- the `_T_Send` suffix only appears on auto-named connectors.

Named `return` connectors follow the same pattern -- the override is just the name:
```yaml
  - name: Channel_Count        # Custom name
    kind: return
    type: Packed_U16.T
```
Generated override: `overriding function Channel_Count (Self : in out Instance) return Packed_U16.T;`

**Direction reminder**: `return` = your component PROVIDES data to others. `get` = your component FETCHES data from others. Compatibility: `get` wires to `return`.

## Connector Count (Array Connectors)

`count: 0` or N = one-to-many fan-out with index:
- Generated index type: `<Type>_T_Send_Index` (send) or `<Type>_T_Recv_Async_Index` (recv_async)
- **Indices are 1-based** (`Connector_Index_Type'First = 1`). Map from 0-based with offset.
- Send: `Self.Packet_T_Send_If_Connected(Index, Arg)`
- **Arrayed recv_async handler signature**: `(Self : in out Instance; Index : in <Type>_T_Recv_Async_Index; Arg : in <Type>.T)` -- **Index comes BEFORE Arg**
- **Arrayed recv_sync handler signature**: Same pattern -- single procedure with Index parameter: `(Self : in out Instance; Index : in <Type>_T_Recv_Sync_Index; Arg : in <Type>.T)` -- NOT separate _1, _2, _3 procedures
- Loop: `for I in Packet_T_Send_Index'Range loop`
- **Arrayed send dropped handler signature**: `(Self : in out Instance; Index : in <Type>_T_Send_Index; Arg : in <Type>.T)` -- same Index-before-Arg pattern as recv_async
- Arrayed recv_async dropped also takes Index: `(Self : in out Instance; Index : in <Type>_T_Recv_Async_Index; Arg : in <Type>.T)`
- Two connectors of same type get numbered: `Event_T_Send` (1st), `Event_T_Send_2` (2nd)
- **⚠️ Each numbered send connector needs its own `*_Dropped` handler**: `Event_T_Send_Dropped` AND `Event_T_Send_2_Dropped` -- missing either causes "type must be declared abstract" error

## Pre-Flight Checklist

1. [ ] Spec uses `with private` / private full record pattern
2. [ ] `Init` override present IFF YAML has `init:` section
2a. [ ] Active components: `Cycle` override MUST be present (abstract in base class)
3. [ ] `Set_Up` override (optional but RECOMMENDED) -- include `overriding procedure Set_Up (Self : in out Instance) is null;` in spec unless you need real logic. Generated base class always has it; overriding as `is null` is idiomatic. Called AFTER `Start_Components` in assembly.
4. [ ] `Invalid_Command` (procedure, 4 params) present IFF `commands.yaml` exists
4. [ ] `Command_T_Recv_Sync` present IFF `commands.yaml` exists
5. [ ] ALL `*_Send_Dropped` handlers overridden for every send connector
6. [ ] NO `with` for auto-provided packages (see list above)
7. [ ] NO `build/` directory created manually
8. [ ] Empty `.all_path` file present
9. [ ] Entity names unique across events, data products, commands, faults, parameters
10. [ ] `use Command_Execution_Status;` INSIDE package body, not before it
11. [ ] `get` connectors: `return_type:` only. `request`: both `type:` and `return_type:`
12. [ ] Custom record fields have `format:` specified (see adamant-type-system). Enum fields use `E8`/`E16` (NOT `U8`); primitives use `U8`/`U16`/`F32`/etc.
13. [ ] Qualify ambiguous literals: `Command_Execution_Status.Success`
14. [ ] No `Packed_U8` (use `Packed_Byte.T`); no `Packed_Bool` (use `Packed_Boolean.T`)
15. [ ] No dynamic allocation (Ravenscar profile)
16a. [ ] Component name must NOT match any of ~58 framework built-in names (see adamant-framework-components catalog). E.g., `command_sequencer`, `sequence_store`, `event_filter`, `fault_counter` are taken. When in doubt, prefix with project/domain name (e.g., `tst_seq_store`).
16b. [ ] Enum literals and type names must NOT collide with framework PACKAGE names that are `with`'d into the generated base class. Dangerous names include: `Fault`, `Event`, `Command`, `Data_Product`, `Parameter_Update`, `Packet`, `Tick`, `Sys_Time`, `Connector_Types`. The compiler error is "`package name cannot be used as operand`". Workaround: use suffixed names (e.g., `Faulted` instead of `Fault`, `Cmd_Event` instead of `Event`).
16. [ ] Active + recv_async: override `{Type}_T_Recv_Async_Dropped`
17. [ ] Parameter overrides: `Parameter_Update_T_Modify`, `Invalid_Parameter`, `Validate_Parameters`, `Update_Parameters_Action`
18. [ ] Data dependency overrides: `Get_Data_Dependency`, `Invalid_Data_Dependency`
18a. [ ] Data dependency names in assembly YAML `map_data_dependencies` must exactly match names from `.data_dependencies.yaml` -- no renaming
19. [ ] Faults use event-like API: `Self.Fault_T_Send_If_Connected(Self.Faults.Name(Time))`
20. [ ] No `with Command_Response_Status` (not standalone -- available through base class)
21. [ ] Component name doesn't collide with ~58 framework components
22. [ ] Custom type YAML filenames (e.g., `quaternion.record.yaml`) don't collide with framework types -- prefix with project/component name if needed
22a. [ ] Verify component and type model names don't collide with existing names anywhere in the project or framework. Model names must be globally unique across all build paths -- two `.record.yaml` files with the same base name in different directories WILL conflict
23. [ ] Use `or else` / `and then` (short-circuit) for ALL boolean expressions (Ada style requirement)
24. [ ] No trailing whitespace in Ada or YAML files (applies to ALL files -- YAML, Ada, Python)
24a. [ ] Init parameter `default:` values MUST be quoted strings (`"10"` not `10`)
25. [ ] All YAML files start with `---` document start marker
26. [ ] Only `with` packages you actually reference -- unused `with` is a style warning
27. [ ] Verify with `admt style` -- all warnings must be resolved
28. [ ] Use `[]` for array aggregates: `[others => 0]` not `(others => 0)` (Ada 2022 syntax). Record aggregates MUST use `()`. Nested array-of-records: `[others => (others => <>)]`
29. [ ] Space before `(` in type conversions: `Unsigned_32 (X)` not `Unsigned_32(X)`
30. [ ] `then` on its own line for multi-line if conditions
31. [ ] Ada child packages DO inherit parent `with`/`use` visibility. The generated base class may `with Interfaces` without `use Interfaces` -- in that case, fully qualified names (`Interfaces.Unsigned_8`) work but short names (`Unsigned_8`) do NOT. To use short names, add `use Interfaces;` in your implementation body's context clause (NOT `with` -- it's already `with`'d). If the base class has BOTH `with Interfaces; use Interfaces;`, do NOT add either -- it causes a `-gnatwr` style warning. Rule: `Interfaces` is auto-provided (at least `with`'d) when the base class references Interfaces types (command args, certain features) -- NOT merely because `init:` exists. Components with only `Natural` init params and no commands need explicit `with Interfaces; use Interfaces;`. **CAVEAT**: Adding `use Pkg;` at body context-clause level still requires `with Pkg;` there -- a spec-level `with` makes the package *visible* in the body but does NOT satisfy a context-level `use` without a corresponding `with`. When in doubt, add both `with X; use X;` in the body.
31a. [ ] When doing arithmetic on `Interfaces` types (`Unsigned_32`, etc.), add `use Interfaces;` in the body to make operators (`+`, `-`, etc.) visible. Otherwise use qualified calls: `Interfaces."+"(Self.Count, 1)`.
32. [ ] Use `Ignore : Type renames Arg;` pattern for unused connector handler parameters (preferred for new code; `pragma Unreferenced (Arg);` is also valid and common in existing code):
    ```ada
    overriding procedure Parameter_Update_T_Modify (Self : in out Instance; Arg : in out Parameter_Update.T) is
       -- Arg is used by Process_Parameter_Update, so no Ignore needed here
    ```
32a. [ ] Avoid redundant type conversions -- `Unsigned_32 (X)` when X is already `Unsigned_32` triggers `-gnatwr`
32b. [ ] Ada does NOT allow `constant` in renames declarations. For `in` mode parameters, just use `Cfg : Foo renames Arg;` -- the `in` mode already makes it read-only. Do NOT write `constant` in a renames.
33. [ ] See `adamant-style` skill for full style reference
34. [ ] `Packed_F32.T.Value` is `Short_Float` (Ada 32-bit float), NOT `Interfaces.IEEE_Float_32` -- use `Short_Float` for F32 record fields and arithmetic
35. [ ] **Custom type visibility in implementation body**: The generated base spec (`component-<name>.ads`) only `with`s types used in connectors, commands, parameters, etc. If your implementation body (`.adb`) references project-specific types that are NOT in those YAML files (e.g., a packed record type used only for data product formatting or unchecked conversion), you MUST add an explicit `with <Type_Package>;` in the body's context clause. The base spec's `with` clauses do NOT automatically cover all types your body might need.

## References

**Load selectively based on task complexity.** Not every component needs every reference.

| Reference | When to load |
|-----------|-------------|
| [references/generated-api.md](references/generated-api.md) | Components with request/provide connectors, data dependencies, or async queues. **Skip for simple passive** (recv_sync + send only) -- the main SKILL.md covers basic connector patterns. |
| [references/implementation-patterns.md](references/implementation-patterns.md) | Active components, FFI, complex state machines. **Skip for simple passive components** (recv_sync -> send, no queues, no C interop). |
| [references/lasel-reference.md](references/lasel-reference.md) | Only when building LASEL command sequence components |
| [references/pitfalls-and-checklist.md](references/pitfalls-and-checklist.md) | Always -- error patterns and checklist |
| [references/template-analysis.md](references/template-analysis.md) | Only when debugging code generation issues |

## Related Skills

- **Types**: [adamant-type-system](../adamant-type-system/SKILL.md)
- **Testing**: [adamant-testing](../adamant-testing/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
