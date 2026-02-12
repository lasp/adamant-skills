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

discriminant:                         # Compile-time record discriminants
  parameters:
    - name: "Max_Count"
      type: "Natural"

init:                                 # Runtime initialization parameters
  description: What these parameters configure
  parameters:
    - name: "Param"
      type: "Natural"
      default: "10"
      description: What this parameter does
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

# component_name.tests.yaml
tests:
  - name: Nominal_Test
    description: Test nominal behavior
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
