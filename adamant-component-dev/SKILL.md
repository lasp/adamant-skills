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

## Packed Type Model

```yaml
# name.record.yaml
description: Bit-level packed record
preamble: |
  subtype My_Range is Interfaces.Unsigned_8 range 0 .. 7;
fields:
  - name: Version
    type: My_Range
    format: U3           # Format codes: U3/U8/U16/U32 (unsigned),
  - name: Packet_Type    #   E1/E2 (enum), U8x{{ size }} (byte array, Jinja2)
    type: My_Enum.E
    format: E8
    default: "My_Enum.Default_Value"   # Field default when record instantiated
    byte_image: true                   # Print as unsigned_8 array (no Ada 'Image)
    skip_validation: true              # Skip autocode validation
  - name: Payload
    type: Byte_Array
    variable_length: "Header.Length"   # Length determined by another field
    variable_length_offset: -4         # Apply offset to length calculation

# name.array.yaml
description: Packed array type
type: My_Element_Type
format: U32                           # For primitive types
length: 10                            # Fixed array length
byte_image: false                     # Print using element 'Image (default)
skip_validation: false                # Enable validation (default)
```

## Packed Type Validation Rules (Enforced by Model)

- Records must be byte-aligned (total size multiple of 8 bits)
- Only ONE variable-length field allowed, must be LAST field
- Variable-length array elements must be byte-aligned
- Cannot nest variable-length types
- If ANY field is volatile, ALL fields must be volatile
- Array components >8 bits must use packed arrays for endianness guarantee
- Nested packed records must use consistent endianness (big/little/either)

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

## Generated Code: What You Get for Free

From component YAML, the generator creates:
- **Base class** (`Component-Name.ads/adb`): connectors, queue management, lifecycle
- **Implementation stubs** (`Component-Name-Implementation.ads/adb`): developer extends these
- **Feature model packages**: `Self.Events.*`, `Self.Data_Products.*`, `Self.Commands.*`, `Self.Faults.*`, `Self.Parameters.*`

Key generated methods on `Self`:
- `Self.Event_T_Send_If_Connected(...)` -- always use `_If_Connected` variant
- `Self.Data_Product_T_Send_If_Connected(...)`
- `Self.Sys_Time_T_Get` -- system time service
- `Self.Is_{Connector}_Connected(Index)` -- check before sending on arrayed connectors

From assembly YAML, the generator creates:
- Assembly package with lifecycle: `Init_Base` -> `Set_Id_Bases` -> `Map_Data_Dependencies` -> `Connect_Components` -> `Init_Components` -> `Set_Up_Components` -> `Start_Components`
- Component instance declarations in `{Assembly}_Components` package
- Task objects for active components with synchronization

From record YAML, the generator creates:
- **U** (unpacked), **T** (packed big-endian), **T_Le** (packed little-endian) types
- `Pack(U) return T` / `Unpack(T) return U` conversion
- `To_Byte_Array` / `From_Byte_Array` serialization
- `Valid(U) return Boolean` field validation
- `-Representation`, `-Validation`, `-Assertion`, `-C` child packages
- Python and MATLAB ground classes

See [references/implementation-patterns.md](references/implementation-patterns.md) for Ada implementation idioms (connector usage, thread safety, command handlers, lifecycle hooks, change detection).

See [references/lasel-reference.md](references/lasel-reference.md) for the LASEL command sequence language (used with command_sequencer component).

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

## Target Hardware Abstraction

Same interface, target-specific body via build path:
```
component/
├── hardware_action.ads            # Shared spec
├── linux/hardware_action.adb      # Dev no-op (.Linux_path)
└── pico/hardware_action.adb       # Real hardware (.Pico_path)
```
