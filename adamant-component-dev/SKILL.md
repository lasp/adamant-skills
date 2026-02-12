---
name: adamant-component-dev
description: Patterns and workflows for developing components in the Adamant embedded software framework
---

# Adamant Component Development

Components are isolated units with typed connectors. YAML models define interfaces; code generation creates Ada structure; handwritten implementation provides behavior.

## File Structure

```
component_name/
├── .all_path                                    # Build path inclusion
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
└── test/
    ├── component_name.tests.yaml                # Test model
    ├── test.adb                                 # Test main (from template)
    ├── component-component_name-implementation-tester.ads/adb
    └── component_name_tests-implementation.ads/adb
```

**CRITICAL**: Do NOT create a `build/` directory. The build system generates it. Creating it manually (even with correct-looking files) prevents redo from running code generation.

## Development Workflow

```bash
redo templates && cp build/template/* .   # Generate and copy stubs
redo all                                  # Build
redo test                                 # Run tests
redo build/svg/comp.svg                   # Diagram
```

## Component Model (YAML)

```yaml
description: What this component does
execution: passive|active|either
# SPARK: add all.prove.yaml in component dir + pragma SPARK_Mode in Ada files
with:                                 # Extra Ada "with" (ONLY custom packages, NOT connector types)
  - "My_Custom_Types"                 # Do NOT list Tick, Command, Event, etc. -- auto-deduced
preamble: |                           # Ada code injected into generated spec
  subtype Custom_Type is Natural range 1 .. 100;

without:                              # Remove auto-deduced "with" dependencies
  - "Unused_Package"

connectors:
  - description: Human-readable purpose of this connector
    kind: recv_sync|recv_async|send|get|provide|service|modify|request|return
    type: Ada_Type                    # Data type (omit for get/return if only return_type)
    return_type: Ada_Return_Type      # For service/request/get
    name: Custom_Connector_Name       # Override auto-generated name (optional)
    count: 0                          # 0=assembly-sized, 1=single (default), N=fixed
    priority: 0-255                   # recv_async only; mixed priorities -> priority queue

generic:                              # Ada generic type parameters
  parameters:
    - name: T
      formal_type: "type T is private;"
      optional: true                  # Only valid if formal_type has a default

discriminant:                         # Compile-time record discriminants
  parameters:
    - name: "Max_Count"
      type: "Natural"
      not_null: true                  # Reject null access values

init:                                 # Runtime initialization parameters
  description: What these parameters configure
  parameters:
    - name: "Param"
      type: "Natural"
      default: "10"
      not_null: true                  # Also available here
      description: What this parameter does

interrupts:                           # Interrupt services (for interrupt_servicer etc.)
  - name: Timer_Interrupt
    description: Handles periodic timer

subtasks:                             # Internal subtasks (assembly must configure priority/stack)
  - name: Listener
    description: Background listener task
```

## Feature Model Formats

```yaml
# component_name.commands.yaml
commands:
  - name: Set_Value
    description: Set the value
    arg_type: Packed_U32.T            # Omit for no-arg commands

# component_name.events.yaml
events:
  - name: Value_Changed
    description: The value was changed
    param_type: Packed_U32.T          # Omit for no-param events

# component_name.data_products.yaml
data_products:
  - name: Current_Value
    type: Packed_U32.T

# component_name.data_dependencies.yaml
data_dependencies:
  - name: Sensor_Reading
    type: Sensor_Data.T
    description: Required sensor input

# Data dependencies require TWO things in component YAML:
#   1. A Sys_Time.T get connector (for stale reference)
#   2. A request connector:
#     - description: Fetch data product from database
#       type: Data_Product_Fetch.T
#       return_type: Data_Product_Return.T
#       kind: request
# Implementation spec MUST override:
#   overriding function Get_Data_Dependency (Self : in out Instance;
#     Id : in Data_Product_Types.Data_Product_Id) return Data_Product_Return.T
#     is (Self.Data_Product_Fetch_T_Request ((Id => Id)));
#   overriding procedure Invalid_Data_Dependency (Self : in out Instance;
#     Id : in Data_Product_Types.Data_Product_Id; Ret : in Data_Product_Return.T);
# Generated API for each dependency named "Foo":
#   Status := Self.Get_Foo (Stale_Reference => time, Value => out_var);
#   -- Returns Data_Product_Enums.Data_Dependency_Status.E
#   -- Need: use Data_Product_Enums.Data_Dependency_Status; for = operator

# component_name.packets.yaml
packets:
  - name: Status_Packet
    id: 7
    type: Status_Data.T

# component_name.parameters.yaml
parameters:
  - name: Start_Count
    description: The value to start counting at.
    type: Packed_U16.T
    default: "(Value => 0)"             # Ada-syntax default initializer

# Parameters require a modify connector in component YAML:
#   - description: The parameter update connector.
#     kind: modify
#     type: Parameter_Update.T
# Implementation overrides:
#   Parameter_Update_T_Modify: call Self.Process_Parameter_Update(Arg)
#   Update_Parameters_Action: hook called AFTER params applied (emit event, update HW)
#   Validate_Parameters(Self, Param1 : Type1.U, Param2 : Type2.U, ...) -> Valid/Invalid
# Access current values: Self.{Param_Name}.{Field} (e.g., Self.Start_Count.Value)
# Call Self.Update_Parameters periodically (e.g., in Tick) to apply staged params.
# NAMING: param type package must NOT match param name (collision with base record field).
#   Bad: param "My_Params" with type "My_Params.T". Good: type "Packed_My_Params.T".

# component_name.faults.yaml
faults:
  - name: Discontinuous_Time_Fault
    description: A discontinuous time was detected.
    param_type: Packed_U32.T            # Optional typed context with fault
  - name: Zero_Time_Fault
    description: A time restart at zero was detected.
                                        # No param_type = no context data

**Fault API (generated from faults.yaml):**
Faults follow the SAME pattern as events -- create a `Fault.T` record and send it:
```ada
-- Send a fault report (correct):
Self.Fault_T_Send_If_Connected (Self.Faults.Undervoltage_Fault (The_Time));
-- With param_type:
Self.Fault_T_Send_If_Connected (Self.Faults.Bad_Value_Fault (The_Time, (Value => X)));
```
Do NOT use `Self.Undervoltage_Fault.Set_Status(...)` -- that API does not exist.
`Self.Faults` is a generated package instance (like `Self.Events` and `Self.Data_Products`).
No `with Fault_Types;` needed in implementation spec -- `Fault` is auto-provided.

# component_name.requirements.yaml
requirements:
  - text: The component shall send a packet whenever it is scheduled to run.
    description: Traceability and verification context.

# component_name.tests.yaml
tests:
  - name: Nominal_Test
    description: Test nominal behavior

# name.enums.yaml -- standalone enumeration definitions
enums:
  - name: My_State
    description: Operating states
    literals:
      - name: Off
        value: 0                        # Explicit value (optional; defaults to near-zero)
      - name: On
        value: 1
      - name: Error
        value: 255
```

## Packed Types

Component models reference packed types for data structures. See [adamant-type-system](../adamant-type-system/SKILL.md) for complete type system documentation.

**Quick reference:**
```yaml
# In component feature models (commands.yaml, events.yaml, etc.)
commands:
  - name: Set_Value
    arg_type: Packed_U32.T            # Use framework packed type
events:  
  - name: Value_Changed
    param_type: Custom_Record.T       # Use custom packed record
```

**Component-specific packed types**: Place `name.record.yaml`, `name.array.yaml`, or `name.enums.yaml` in component directory for component-specific types.

## Connector Kind Compatibility

```
send    -> recv_sync | recv_async    request -> service
get     -> return                    provide -> modify
```
Array connector (`count: 0` or N): one-to-many fan-out with index.


## Generated Code API Reference

See [references/generated-api.md](references/generated-api.md) for the full generated code API: base class, events/commands/data products packages, implementation spec pattern, timestamp pattern, assembly lifecycle, and type generation.

Key usage patterns (quick reference):
- Events: `Self.Event_T_Send_If_Connected (Self.Events.Name (The_Time, (Value => X)));`
- Data products: `Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Name (The_Time, Val));`
- Commands: implement `overriding function Cmd_Name (...) return Command_Execution_Status.E;`
- Time: `The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;`
- Send: `*_Send_If_Connected` (safe) vs `*_Send` (asserts connected)

## Tester Component Generation

`redo templates` generates a reciprocal tester with inverse connectors (sends become recvs). Tester forces all invokee connectors synchronous (no queues in test). White-box access to component internals via tester instance.

```
component_name/test/
├── component_name.tests.yaml
├── component-component_name-implementation-tester.ads/adb   # Generated tester
└── component_name_tests-implementation.ads/adb              # Handwritten test cases
```

## Execution Model Selection

- **Passive**: Synchronous processing (filters, dividers, counters, algorithm wrappers)
  - Only has `Init` if component YAML defines `init:` section with parameters
  - Do NOT add `overriding procedure Init` unless YAML has init params
- **Active**: Message queue for async connectors (routers, command handlers)
  - `Init` MUST call `Self.Init_Base(Queue_Size)` to allocate the queue
  - Async handler: `{Type}_T_Recv_Async` (called by auto-generated `Cycle` after dequeue)
  - Overflow handler: `{Type}_T_Recv_Async_Dropped` (called when queue full)
  - Command connectors stay `recv_sync` even on active components
  - If active but NO recv_async connectors: must override `Cycle` procedure (task body)
  - Consider passive if you only have recv_sync connectors (no own task needed)
- **Active + Subtasks**: Isolate blocking I/O (serial/socket interfaces)

## Related Skills
- **Formal verification**: See `adamant-build-system` (prove section)
- **C++ algorithm wrapping**: See `adamant-algorithm-wrapping`

## Pre-Flight Checklist (verify before submitting)

1. [ ] Spec uses `with private` pattern (public opaque, private full record + overrides)
2. [ ] `Init` override present IFF component YAML has `init:` section
3. [ ] `Invalid_Command` override present IFF `commands.yaml` exists
4. [ ] `Command_T_Recv_Sync` override present IFF `commands.yaml` exists
5. [ ] All `*_Send_Dropped` handlers overridden for every send connector
6. [ ] NO `with` for auto-provided packages (Interfaces, Event, Data_Product, Sys_Time, etc.)
7. [ ] NO `build/` directory created
8. [ ] Empty `.all_path` file present
9. [ ] All entity names unique across events, data products, commands, faults, parameters
10. [ ] `use Command_Execution_Status;` INSIDE package body (not before it)
11. [ ] `get` connectors use `return_type:` NOT `type:` in YAML
12. [ ] `request` connectors have both `type:` and `return_type:` in YAML
13. [ ] Custom record YAML fields have `format:` specified (e.g., `format: F32` for `Short_Float`, `format: U32` for `Unsigned_32`). Missing format = "is NOT a packed type" build error.
14. [ ] Qualify ambiguous literals: `Parameter_Validation_Status.Valid`, `Command_Execution_Status.Success` (bare `Valid`/`Success` can be invisible or ambiguous)
15. [ ] Parameter accessor `Self.<Param_Name>` returns `.U` -- convert to `.T` when passing to events: `My_Type.T (Self.My_Param)`

## Common Pitfalls

**Required connectors for feature models:**
Each feature YAML file requires matching connectors in the component YAML:
- `commands.yaml` -> `Command.T` recv_sync + `Command_Response.T` send
- `events.yaml` -> `Event.T` send
- `data_products.yaml` -> `Data_Product.T` send
- `faults.yaml` -> `Fault.T` send
- `parameters.yaml` -> `Parameter_Update.T` modify
- `data_dependencies.yaml` -> `Data_Product_Fetch.T` / `Data_Product_Return.T` request
Missing any of these causes code generation errors.

**Implementation spec with clauses:**
- Only `with` what's needed: typically `Tick`, `Command`, `Parameter_Update` (for modify connector), and any CUSTOM types used in your private record (e.g. `My_Custom_Type`)
- The generated base class includes `with Interfaces; use Interfaces;` when the component has init params, commands, or other features referencing Interfaces types. It is NOT always present. If your component has no init/commands but needs Unsigned types, add `with: ["Interfaces"]` in the component YAML. The base always has `with` for connector types (`Sys_Time`, `Event`, `Data_Product`, `Fault` if used, `Basic_Types`). Components with commands also get `use Command_Enums;`.
- **CRITICAL**: Do NOT `with` any of these (already visible or not standalone packages): `Command_Execution_Status`, `Command_Response_Status`, `Unsigned_32`, `Parameter_Validation_Status`, `Command_Response`, `Event`, `Data_Product`, `Fault`, `Sys_Time`, `Basic_Types`, `Interfaces`. Adding `with Command_Execution_Status;` is a COMPILATION ERROR.
- For components with commands: add `use Command_Execution_Status;` in the body to use bare `Success`/`Failure`.
- Custom enumeration types used in instance record fields must be declared in the public part of the implementation spec.

**Implementation spec structure (MANDATORY pattern):**
```ada
with Tick;        -- Only with connector/custom types you actually use
with Command;     -- Only if component has commands

package Component.My_Component.Implementation is
   type Instance is new My_Component.Base_Instance with private;  -- PUBLIC: opaque
private
   type Instance is new My_Component.Base_Instance with record    -- PRIVATE: fields
      My_Field : Interfaces.Unsigned_32 := 0;
   end record;
   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T);
   -- All overriding declarations go in private section
end Component.My_Component.Implementation;
```
The `with private` in public + full record in `private` is REQUIRED. Putting the record directly in the public part is a compilation error.

**Get connectors are NOT overridden:**
- `Sys_Time_T_Get` is a get connector -- the base class provides it. Do NOT override it.
- You CALL `Self.Sys_Time_T_Get` in your code, you don't implement it.

**Send connectors are NOT overridden:**
- `Event_T_Send`, `Data_Product_T_Send`, etc. are procedures you CALL, not override.
- Only the `*_Dropped` handlers are overridden.

**Command_T_Recv_Sync is REQUIRED** when commands.yaml exists. This is the entry point for all commands. Standard pattern:
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
- Use `Self.Execute_Command(Arg)` to dispatch commands (NOT `Self.Process_Command`).
- Returns `Command_Response_Status.E` (not `Command_Execution_Status.E`).

**Command handler function names match the YAML command name EXACTLY:**
- YAML `name: Set_Mode` -> `overriding function Set_Mode (Self : in out Instance; Arg : in ...) return Command_Execution_Status.E;`
- Do NOT append `_Execute` or any suffix. The generated abstract function uses the exact YAML command name.
- Commands with `arg_type:` get `Arg : in <arg_type>` parameter. Commands without get no extra parameter.

**Invalid_Command is REQUIRED** when commands.yaml exists. Missing it causes "type must be declared abstract" error. It is a PROCEDURE (not a function) with 4 parameters:
```ada
overriding procedure Invalid_Command (Self : in out Instance; Cmd : in Command.T; Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);
```
Do NOT make it `function ... return Command_Execution_Status.E` -- that's a different signature and won't override.

**Init parameter types:**
- Use standard Ada types for init params: `Positive`, `Natural`, `Boolean`, `Interfaces.Unsigned_32`
- NOT `Interfaces.IEEE_Float_32` -- use `Short_Float` or `Long_Float` for floats
- For typed data, use packed record types (e.g., `Packed_F32.T`)

**Data product values must be packed (.T), not unpacked (.U):**
- `Self.Data_Products.Foo (Time, Packed_F32.T'(Value => X))` -- correct
- `Self.Data_Products.Foo (Time, (Value => X))` -- WRONG if it resolves to .U

**Parameters require overrides in implementation spec:**
- `Validate_Parameters`: takes INDIVIDUAL parameter arguments (one per parameter), NOT a combined record:
  ```ada
  overriding function Validate_Parameters (
     Self : in out Instance;
     Param_A : in Packed_U16.U;   -- one arg per parameter in YAML
     Param_B : in Packed_U32.U
  ) return Parameter_Validation_Status.E;
  ```
  The template default returns `Valid`. Override only if cross-parameter validation needed.
- `overriding procedure Invalid_Parameter (Self : in out Instance; Par : in Parameter.T; Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);`
  Note: Par is `Parameter.T`, NOT `Parameter_Update.T`.
- `overriding procedure Parameter_Update_T_Modify (Self : in out Instance; Arg : in out Parameter_Update.T);`
  Call `Self.Process_Parameter_Update(Arg)` in the body.
- Missing any of these produces "type must be declared abstract" error
- There is NO combined `Component_Name_Parameters.U` record type. Parameters package only has creation functions.
- `Update_Parameters_Action` is abstract -- must override even if just `is null`

**Connector YAML:**
- `get` kind CANNOT have `type` field -- only `return_type` and `kind`
- `count` must be a literal integer, not a reference (e.g., `count: 4`, never `count: "Init.N"`)
- `request` kind DOES use both `type` (outgoing) and `return_type` (incoming)

**Commands YAML:**
- Field is `arg_type`, not `type` or `parameters` (those are NOT valid keys)
- For no-argument commands, OMIT `arg_type` entirely (don't use `arg_type: None`)
- Command arguments must be a separate packed record type, not inline fields

**Entity name uniqueness:**
- ALL entity names (events, data products, commands, faults, parameters) must be unique across the component. An event named `Foo` and a data product named `Foo` causes a code generation error.

**Events YAML:**
- No `level` field in schema -- events are typed by their `param_type` only
- Omit `param_type` for events with no parameter

**Custom record types (*.record.yaml):**
- EVERY field MUST have a `format:` code (`F32` for Short_Float, `U16`/`U32` for unsigned, `E8` for enums). Missing format = build error "is NOT a packed type".
- See `adamant-type-system` skill for full format reference.

**Packed record fields:**
- `Natural` needs 31 bits -- does NOT fit `U16` format. Use `Interfaces.Unsigned_16` for U16 fields.
- **There is NO `Packed_U8`.** Use `Packed_U16.T` for small integers or `Packed_Byte.T` for 8-bit values.
- Enum literal names must NOT collide with framework package names (e.g., `Fault` conflicts with `Fault` package -- use `Faulted` instead).
- Packed `.T` types inherit serialization fields -- cannot be used as simple record aggregates for default initialization. Store individual scalar fields instead.

**Parameters (additional):**
- Parameters REQUIRE `default` in YAML (schema-enforced)
- `Self.Update_Parameters` must be called explicitly (in Tick handler) to apply staged values
- Negative defaults for `Interfaces.Integer_32` break generated code (unary minus visibility)
- `Parameter_Update_Status` lives in `Parameter_Enums.Parameter_Update_Status`

**Visibility:**
- `Interfaces` is auto-with'd when init params, commands, or other features use Interfaces types. For simple components without these, add `with: ["Interfaces"]` in YAML if you need Unsigned types.
- `Errant_Field_Number` in Invalid_Command/Invalid_Parameter is `Unsigned_32` (base renames from Interfaces).
- No `Invalid_Command_Received` event unless explicitly defined in events.yaml.

**Duplicate connector types get numbered:**
- Two `Event.T` send connectors become `Event_T_Send` (1st) and `Event_T_Send_2` (2nd)
- Each gets its own `*_Dropped` handler that MUST be overridden
- Common pattern: forwarded data on connector 1, component events on connector 2
- Use `Self.Event_T_Send_If_Connected` for first, `Self.Event_T_Send_2_If_Connected` for second

**Component naming: avoid framework collisions:**
- The adamant framework has ~55 built-in components (event_filter, command_router, etc.)
- Your component names must NOT match any framework component name
- Check `adamant/src/components/` before naming. Name collisions cause "conflicting source files" errors.

**Send connector dropped handlers:**
- EVERY send connector generates a `*_Send_Dropped` procedure that MUST be overridden (even as `is null`).
- If you add `Command_Response_T_Send`, you MUST add `Command_Response_T_Send_Dropped`.
- Forgetting one produces: "type must be declared abstract or X overridden".

**Testing:** See `adamant-testing` skill for full patterns. Key gotcha: test dirs use `env.py` (NOT `.all_path`).

## Target Hardware Abstraction

Same interface, target-specific body via build path:
```
component/
├── hardware_action.ads            # Shared spec
├── linux/hardware_action.adb      # Dev no-op (.Linux_path)
└── pico/hardware_action.adb       # Real hardware (.Pico_path)
```
