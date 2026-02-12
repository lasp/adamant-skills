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
with:                                 # Extra Ada "with" dependencies
  - "Package_Name"
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

# Data dependencies require a request connector in the component YAML:
#   - description: Fetch a data product item from the database.
#     type: Data_Product_Fetch.T
#     return_type: Data_Product_Return.T
#     kind: request
# And this override in the implementation spec (from generated template):
#   overriding function Get_Data_Dependency (Self : in out Instance;
#     Id : in Data_Product_Types.Data_Product_Id) return Data_Product_Return.T
#     is (Self.Data_Product_Fetch_T_Request ((Id => Id)));
# The generator creates Self.Get_{Dep_Name}(Value => out_var, Stale_Reference => time)
# which returns Data_Product_Enums.Data_Dependency_Status.E

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

## Available Data Structures (src/data_structures/)

| Package | Generic Params | Key Operations | Use Case |
|---------|---------------|----------------|----------|
| Binary_Tree | Element_Type, <, > | Add, Search (O(log n)), Remove | Static lookup tables |
| Fifo | T | Push, Pop, Peek, Get_Count | Simple typed queues |
| Circular_Buffer | (byte-based) | Push, Pop, Peek, Num_Bytes_Free | Streaming byte data |
| Queue | (extends Circular_Buffer) | Push, Pop with length prefix | Variable-length elements |
| Priority_Queue | | Push with priority, Pop highest | Priority scheduling |
| Protected_Circular_Buffer | | Thread-safe Push/Pop | Shared byte buffers |
| Protected_Priority_Queue | | Thread-safe priority ops | Shared priority queues |
| Database | | Key-value storage | Configuration data |

Binary_Tree is a sorted array underneath (O(log n) search, O(n) insert). Best for data inserted once at startup.

## Connector Kind Compatibility

Connectors wire in pairs by direction:
```
send        -> recv_sync | recv_async     (invoker -> invokee)
request     -> service                     (invoker -> invokee, returns value)
get         -> return                      (invoker -> invokee, returns value)
provide     -> modify                      (invokee -> invoker, bidirectional)
```

Array connector (`count: 0` or `count: N`): one-to-many fan-out with index.
Mixed async priorities on a single component -> automatic priority queue.

## Hardware Interface Models

```yaml
# system_registers.register_map.yaml -- Memory-mapped register definitions
items:
  - address: 0x4000_0004
    name: First_Register
    type: Packed_U32.Register_T
  - address: 0x4000_0010
    name: Second_Register
    type: Packed_Poly_32_Type.Register_T

# nonvolatile_store.memory_map.yaml -- Sequential memory layout
start_address: 0x0600000
length: 2097152                          # 2MB
items:
  - name: Time
    type: Sys_Time.T
  - name: Counter
    type: Packed_U32.T
```


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

## Formal Verification

```bash
redo prove                                    # Prove current component
redo prove_all                               # Recursive proof
PROVE_SWITCHES="--level=4" redo prove        # Higher effort
PROVE_SWITCHES="--timeout=30" redo prove     # Longer per-VC timeout
```

## C/C++ Algorithm Wrapping

For wrapping C++ algorithms (GNC, etc.) into Adamant components, see the dedicated [adamant-algorithm-wrapping](../adamant-algorithm-wrapping/SKILL.md) skill. It covers the full pipeline: C shim creation, Ada binding generation, packed record conversion, component YAML patterns, type conversion chain (T -> U -> C.U_C), and unit testing.

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
- The generated base class already has `with` + `use` for: `Command_Response`, `Event`, `Data_Product`, `Fault`, `Sys_Time`, `Packed_*` types, `Basic_Types`, `Interfaces`, `Command_Enums`, `Command_Types`, `Data_Product_Types`, `Event_Types`. It also has `use Interfaces;` making `Unsigned_32` etc. directly visible, and `use Command_Enums;` making `Command_Execution_Status` visible.
- Do NOT add `with` for ANY of these -- they are NOT standalone packages and/or are already visible: `Command_Execution_Status`, `Unsigned_32`, `Parameter_Validation_Status`, `Command_Response_Status`, `Command_Response`, `Event`, `Data_Product`, `Fault`, `Sys_Time`, `Basic_Types`, `Interfaces`

**Get connectors are NOT overridden:**
- `Sys_Time_T_Get` is a get connector -- the base class provides it. Do NOT override it.
- You CALL `Self.Sys_Time_T_Get` in your code, you don't implement it.

**Send connectors are NOT overridden:**
- `Event_T_Send`, `Data_Product_T_Send`, etc. are procedures you CALL, not override.
- Only the `*_Dropped` handlers are overridden.

**Command dispatch:**
- Use `Self.Execute_Command(Arg)` to dispatch commands (NOT `Self.Process_Command`).
- Returns `Command_Response_Status.E` (not `Command_Execution_Status.E`).

**Invalid_Command is REQUIRED** when commands.yaml exists. Missing it causes "type must be declared abstract" error.

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

**Events YAML:**
- No `level` field in schema -- events are typed by their `param_type` only
- Omit `param_type` for events with no parameter

**Packed record fields:**
- `Natural` needs 31 bits -- does NOT fit `U16` format. Use `Interfaces.Unsigned_16` for U16 fields.
- Packed `.T` types inherit serialization fields -- cannot be used as simple record aggregates for default initialization. Store individual scalar fields instead.

**Parameters:**
- `Validate_Parameters` takes INDIVIDUAL unpacked (`.U`) arguments, one per parameter -- NOT a combined record
- Parameters REQUIRE `default` in YAML (schema-enforced)
- `Self.Update_Parameters` must be called explicitly (typically in Tick handler) to apply staged values
- Negative defaults for `Interfaces.Integer_32` fields break generated code (unary minus visibility issue)
- `Parameter_Update_Status` type lives in `Parameter_Enums.Parameter_Update_Status`

**Visibility:**
- `Interfaces` package is NOT auto-with'd. Add `with: ["Interfaces"]` in component YAML or `with Interfaces;` in handwritten files.
- Use `use type Interfaces.Unsigned_32;` for arithmetic operators.
- `Errant_Field_Number` in Invalid_Command/Invalid_Parameter is `Unsigned_32` (NOT `Basic_Types.Unsigned_32` or `Interfaces.Unsigned_32`). The base class imports Interfaces and renames it.
- No `Invalid_Command_Received` event unless you explicitly define it in events.yaml.

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

**Testing:**
- Test directories need `env.py` containing `from environments import test`
- `Self.Tester` is `Instance_Access` (pointer), NOT `Instance` -- use `Instance_Access renames`
- `Tick.T` requires both `Time : Sys_Time.T` and `Count` fields: `(Time => (0, 0), Count => 1)`
- Test flow: `Init_Base` -> `Connect` -> component `Init` -> `Set_Up` -> send stimuli -> check histories
- `Packet.T` header has `Time`, `Id`, `Sequence_Count`, `Buffer_Length` -- all required

## Target Hardware Abstraction

Same interface, target-specific body via build path:
```
component/
├── hardware_action.ads            # Shared spec
├── linux/hardware_action.adb      # Dev no-op (.Linux_path)
└── pico/hardware_action.adb       # Real hardware (.Pico_path)
```
