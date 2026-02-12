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
with_spark: true                      # Enable SPARK for generated code (optional)
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
#   Validate_Parameters(Self, Param_Name : Param_Type.U) -> Valid/Invalid
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

From component YAML, the generator produces these packages (all in `build/src/`):

### Base Class (`Component.{Name}`)

```ada
type Base_Instance is abstract new Component.Core_Instance with private;

-- Init: abstract, signature from init.parameters in YAML
not overriding procedure Init (Self : in out Base_Instance; ...) is abstract;

-- Set_Id_Bases: called by assembly to assign global ID ranges
not overriding procedure Set_Id_Bases (Self : in out Base_Instance;
   Command_Id_Base : Command_Types.Command_Id_Base;
   Data_Product_Id_Base : Data_Product_Types.Data_Product_Id_Base;
   Event_Id_Base : Event_Types.Event_Id_Base;
   Packet_Id_Base : Packet_Types.Packet_Id_Base);

-- Invokee connector primitives: abstract, override in implementation
not overriding procedure {Connector_Name} (Self : in out Base_Instance; Arg : in {Type}.T) is abstract;
-- Hook accessor for wiring:
not overriding function {Connector_Name}_Access (Self : in Base_Instance; ...) return not null {Connector}_Connector.Invokee_Hook;

-- Invoker connector methods (private section, usable by child):
not overriding procedure {Connector}_Send_If_Connected (Self : in out Base_Instance; Arg : in {Type}.T; ...);
not overriding procedure {Connector}_Send (Self : in out Base_Instance; Arg : in {Type}.T; ...);  -- asserts connected
not overriding function Is_{Connector}_Connected (Self : in Base_Instance) return Boolean;
-- For get connectors:
not overriding function Sys_Time_T_Get (Self : in Base_Instance) return Sys_Time.T;

-- Dropped handler: abstract, override in implementation (can be "is null")
not overriding procedure {Connector}_Send_Dropped (Self : in out Base_Instance; Arg : in {Type}.T) is abstract;

-- Base record (private) contains:
--   Connector_{Name} : {Connector}.Instance;  -- one per invoker connector
--   Events : {Name}_Events.Instance;
--   Data_Products : {Name}_Data_Products.Instance;
--   Packets : {Name}_Packets.Instance;
--   Command_Id_Base : Command_Types.Command_Id := 1;
```

### Events Package (`{Name}_Events`)

```ada
-- Local IDs (enumeration with rep clause):
type Local_Event_Id_Type is (Value_Changed_Id, Error_Detected_Id, ...);
for Local_Event_Id_Type use (Value_Changed_Id => 0, Error_Detected_Id => 1, ...);

-- Creation functions -- call via Self.Events:
function Value_Changed (Self : Instance; Timestamp : Sys_Time.T; Param : in Packed_U32.T) return Event.T;
function Error_Detected (Self : Instance; Timestamp : Sys_Time.T) return Event.T;  -- no param

-- ID getters:
function Get_Value_Changed_Id (Self : Instance) return Event_Types.Event_Id;
```

**Usage in implementation:**
```ada
The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
Self.Event_T_Send_If_Connected (Self.Events.Value_Changed (The_Time, (Value => 42)));
Self.Event_T_Send_If_Connected (Self.Events.Error_Detected (The_Time));  -- no param
```

### Data Products Package (`{Name}_Data_Products`)

```ada
-- Creation functions:
function Current_Value (Self : Instance; Timestamp : Sys_Time.T; Item : in Packed_U32.T) return Data_Product.T;

-- ID getters:
function Get_Current_Value_Id (Self : Instance) return Data_Product_Types.Data_Product_Id;
```

**Usage:** `Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Current_Value (The_Time, (Value => N)));`

### Commands Package (`{Name}_Commands`)

```ada
-- Local IDs:
type Local_Command_Id_Type is (Set_Value_Id, Reset_Id, ...);

-- Creation functions (for tests, not usually needed in implementation):
function Set_Value (Self : Instance; Arg : in Packed_U32.T) return Command.T;

-- ID getters:
function Get_Set_Value_Id (Self : Instance) return Command_Types.Command_Id;
```

**Command handler pattern in implementation:**
```ada
-- Base class auto-generates Execute_Command which dispatches to your handlers.
-- You implement one function per command:
overriding function Set_Value (Self : in out Instance; Arg : in Packed_U32.T) return Command_Execution_Status.E is
   use Command_Execution_Status;
begin
   Self.Value := Arg.Value;
   -- Send event/data product...
   return Success;  -- or Failure
end Set_Value;

-- Also implement Invalid_Command for bad argument handling:
overriding procedure Invalid_Command (Self : in out Instance; Cmd : in Command.T;
   Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);

-- Command_T_Recv_Sync connector dispatches automatically:
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

### Implementation Spec Pattern

```ada
package Component.{Name}.Implementation is
   type Instance is new {Name}.Base_Instance with private;

   -- Override Init from base:
   overriding procedure Init (Self : in out Instance; ...);

   -- Optional: Set_Up runs once after all components wired and started
   -- Use for: initial data product sends, command registration
   overriding procedure Set_Up (Self : in out Instance);

private
   type Instance is new {Name}.Base_Instance with record
      -- Your component state here:
      Counter : Natural := 0;
      Algorithm_Handle : Algorithm_Access := null;
   end record;

   -- Override connector handlers:
   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T);
   overriding procedure Command_T_Recv_Sync (Self : in out Instance; Arg : in Command.T);

   -- Dropped handlers (can be "is null" for non-critical):
   overriding procedure Event_T_Send_Dropped (Self : in out Instance; Arg : in Event.T) is null;

   -- Command handlers:
   overriding function Set_Value (Self : in out Instance; Arg : in Packed_U32.T) return Command_Execution_Status.E;
   overriding procedure Invalid_Command (Self : in out Instance; Cmd : in Command.T;
      Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);
end Component.{Name}.Implementation;
```

### Timestamp Pattern

Always get time from the Sys_Time connector, never from Arg:
```ada
The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
-- Use The_Time for all events and data products in this handler
Self.Event_T_Send_If_Connected (Self.Events.Something (The_Time));
Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Something (The_Time, Value));
```

Exception: Tick handlers may use `Arg.Time` from the tick itself if appropriate.

### Assembly Lifecycle (generated)

`Init_Base` -> `Set_Id_Bases` -> `Map_Data_Dependencies` -> `Connect_Components` -> `Init_Components` -> `Set_Up_Components` -> `Start_Components`

Component instances declared in `{Assembly}_Components` package. Task objects for active components with synchronization.

### Type Generation (from record/array/enum YAML)

- **U** (unpacked), **T** (packed big-endian), **T_Le** (packed little-endian) types
- `Pack(U) return T` / `Unpack(T) return U` conversion
- `To_Byte_Array` / `From_Byte_Array` serialization
- `Valid(U) return Boolean` field validation
- `-Representation`, `-Validation`, `-Assertion`, `-C` child packages
- Python and MATLAB ground classes

See [references/implementation-patterns.md](references/implementation-patterns.md) for Ada implementation idioms (connector usage, thread safety, command handlers, lifecycle hooks, change detection).

See [references/lasel-reference.md](references/lasel-reference.md) for the LASEL command sequence language (used with command_sequencer component).

See [adamant-testing](../adamant-testing/SKILL.md) skill for test setup, History API, async dispatch, assertions, error injection, and data dependency testing patterns.

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
- **Active**: Message queue for async connectors (routers, command handlers)
  - `Init` MUST call `Self.Init_Base(Queue_Size)` to allocate the queue
  - Async handler: `{Type}_T_Recv_Async` (called by auto-generated `Cycle` after dequeue)
  - Overflow handler: `{Type}_T_Recv_Async_Dropped` (called when queue full)
  - Command connectors stay `recv_sync` even on active components
- **Active + Subtasks**: Isolate blocking I/O (serial/socket interfaces)

## Formal Verification

```bash
redo prove                                    # Prove current component
redo prove_all                               # Recursive proof
PROVE_SWITCHES="--level=4" redo prove        # Higher effort
PROVE_SWITCHES="--timeout=30" redo prove     # Longer per-VC timeout
```

## C/C++ Algorithm Wrapping (Opaque Handle Pattern)

The full integration chain for GNC algorithms (e.g., attitude_tracking_error):

**C header** (fp32-fsw-xmera): opaque handle + POD types
```c
typedef struct AttTrackingErrorAlgorithm AttTrackingErrorAlgorithm;
AttTrackingErrorAlgorithm* AttTrackingErrorAlgorithm_create(void);
void AttTrackingErrorAlgorithm_destroy(AttTrackingErrorAlgorithm* self);
AttGuidMsgF32Payload AttTrackingErrorAlgorithm_update(
    AttTrackingErrorAlgorithm* self,
    AttRefMsgF32Payload* attRefIn, NavAttMsgF32Payload* attNavIn);
```

**Ada binding** (handwritten or via `-fdump-ada-spec`):
```ada
type Att_Tracking_Error_Algorithm is limited private;  -- opaque
type Att_Tracking_Error_Algorithm_Access is access all Att_Tracking_Error_Algorithm;
function Create return Att_Tracking_Error_Algorithm_Access
  with Import => True, Convention => C, External_Name => "...";
```

**Component implementation**: stores handle, creates in Init, destroys in Destroy:
```ada
type Instance is new Base_Instance with record
   Alg : Att_Tracking_Error_Algorithm_Access := null;
end record;
```

**Type conversion in Tick handler**: Ada Packed -> Unpack -> To_C -> algorithm -> To_Ada -> Pack
```ada
Ref_C : aliased Att_Ref.C.U_C := Att_Ref.C.To_C (Att_Ref.Unpack (Ref));
Guid  : constant Att_Guid.C.U_C := Update (Self.Alg, 0, Ref_C'Unchecked_Access, Nav_C'Unchecked_Access);
Self.Data_Product_T_Send (Self.Data_Products.Attitude_Guidance (
   Arg.Time, Att_Guid.Pack (Att_Guid.C.To_Ada (Guid))));
```

**Data dependencies** validate freshness before calling algorithm:
```ada
Ref_Status : constant Data_Dependency_Status.E :=
   Self.Get_Attitude_Reference (Value => Ref, Stale_Reference => Arg.Time);
if Is_Dep_Status_Success (Ref_Status) and then Is_Dep_Status_Success (Nav_Status) then
   -- call algorithm
```

## Common Pitfalls

**Connector YAML:**
- `get` kind CANNOT have `type` field -- only `return_type` and `kind`
- `count` must be a literal integer, not a reference (e.g., `count: 4`, never `count: "Init.N"`)
- `request` kind DOES use both `type` (outgoing) and `return_type` (incoming)

**Commands YAML:**
- Field is `arg_type`, not `type` or `parameters` (those are NOT valid keys)
- Command arguments must be a separate packed record type, not inline fields

**Packed record fields:**
- `Natural` needs 31 bits -- does NOT fit `U16` format. Use `Interfaces.Unsigned_16` for U16 fields.
- Packed `.T` types inherit serialization fields -- cannot be used as simple record aggregates for default initialization. Store individual scalar fields instead.

**Visibility:**
- `Interfaces` package is NOT auto-with'd. Add `with: ["Interfaces"]` in component YAML or `with Interfaces;` in handwritten files.
- Use `use type Interfaces.Unsigned_32;` for arithmetic operators.
- No `Invalid_Command_Received` event unless you explicitly define it in events.yaml.

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
