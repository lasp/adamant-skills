# Component YAML Templates

## component.yaml (without parameters)

```yaml
---
description: <Brief description of what the component does>.
execution: passive
init:
  description: Initializes the <algorithm name> algorithm.
connectors:
  - description: Run the algorithm up to the current time.
    type: Tick.T
    kind: recv_sync
  - description: Fetch a data product item from the database.
    type: Data_Product_Fetch.T
    return_type: Data_Product_Return.T
    kind: request
  - description: The data product invoker connector
    type: Data_Product.T
    kind: send
```

## component.yaml (with parameters)

```yaml
---
description: <Brief description of what the component does>.
execution: passive
init:
  description: Initializes the <algorithm name> algorithm.
connectors:
  - description: Run the algorithm up to the current time.
    type: Tick.T
    kind: recv_sync
  - description: Fetch a data product item from the database.
    type: Data_Product_Fetch.T
    return_type: Data_Product_Return.T
    kind: request
  - description: The data product invoker connector
    type: Data_Product.T
    kind: send
  - description: The parameter update connector.
    type: Parameter_Update.T
    kind: modify
```

**IMPORTANT**: If component has `.parameters.yaml`, MUST add `Parameter_Update.T` connector.

Event and Sys_Time connectors are NOT needed for simple algorithm wrappers that only fetch dependencies and produce data products.

## data_dependencies.yaml

```yaml
---
description: Data dependencies for the <Component Name> component.
data_dependencies:
  - name: <Input_Name>
    type: <Type>.T
    description: <Brief description>
```

### Type mapping (C++ to Adamant data dependencies)

| C++ input type | Adamant dependency type |
|---------------|----------------------|
| `EphemerisMsgF32Payload` | `Ephemeris.T` |
| `NavAttMsgF32Payload` | `Nav_Att.T` |
| `NavTransMsgF32Payload` | `Nav_Trans.T` |
| `AttRefMsgF32Payload` | `Att_Ref.T` |
| `AttGuidMsgF32Payload` | `Att_Guid.T` |

### Buffer size constraint

Data dependencies are fetched through the data product system with a fixed buffer size (typically 128 bytes, configured in `config/*.configuration.yaml` field `data_product_buffer_size`). If an input type's serialized size exceeds this, it CANNOT be a data dependency.

## data_products.yaml

```yaml
---
description: Data products for the <Component Name> component.
data_products:
  - name: <Output_Name>
    type: <Type>.T
    description: <Brief description>.
```

## parameters.yaml

Only create if component has configuration values that change infrequently.

```yaml
---
description: Parameters for the <Component Name> component
parameters:
  - name: <Parameter_Name>
    description: "[units] Description of parameter"
    type: <Type>.T
    default: "<Ada aggregate syntax>"
```

### Common parameter types

| Parameter type | Adamant type | Default example |
|---------------|-------------|-----------------|
| Single float | `Packed_F32.T` | `(Value => 0.0)` |
| 3-element float array | `Packed_F32x3.T` | `[0.0, 0.0, 0.0]` |
| 9-element float array | `Packed_F32x9.T` | `[others => 0.0]` |
| Single unsigned 32 | `Packed_U32.T` | `(Value => 0)` |

### Buffer size constraint

If parameter size > `parameter_buffer_size` in config, increase it:
```yaml
parameter_buffer_size: 40  # Must be >= largest parameter size
```
(e.g., `Packed_F32x9.T` is 36 bytes)

## Parameters vs Data Dependencies Decision

### Use Parameters when:
- Configuration data changing infrequently (gains, inertia, calibration)
- Set during initialization or via ground command
- Does not change every control cycle

### Use Data Dependencies when:
- Changes frequently (every control cycle)
- Computed by another component
- Dynamic state (attitude, position, sensor readings)

### Checklist for Parameters:
- [ ] Create `<name>.parameters.yaml`
- [ ] Add `Parameter_Update.T` connector to component YAML
- [ ] Call `Self.Update_Parameters;` at start of `Tick_T_Recv_Sync`
- [ ] Implement `Update_Parameters_Action`
- [ ] Implement `Invalid_Parameter` with assertion
- [ ] Verify `parameter_buffer_size` in config

## Complete Example: sunline_ephem

### component.yaml
```yaml
---
description: Sunline ephemeris algorithm computes the direction to the sun in the spacecraft body frame.
execution: passive
init:
  description: Initializes the sunline ephemeris algorithm.
connectors:
  - description: Run the algorithm up to the current time.
    type: Tick.T
    kind: recv_sync
  - description: Fetch a data product item from the database.
    type: Data_Product_Fetch.T
    return_type: Data_Product_Return.T
    kind: request
  - description: The data product invoker connector
    type: Data_Product.T
    kind: send
```

### data_dependencies.yaml
```yaml
---
description: Data dependencies for the Sunline Ephem component.
data_dependencies:
  - name: Sun_Ephemeris
    type: Ephemeris.T
    description: Sun ephemeris state (position and velocity)
  - name: Spacecraft_Position
    type: Nav_Trans.T
    description: Spacecraft translational navigation state
  - name: Spacecraft_Attitude
    type: Nav_Att.T
    description: Spacecraft attitude navigation state
```

### data_products.yaml
```yaml
---
description: Data products for the Sunline Ephem component.
data_products:
  - name: Sunline_Body_Frame
    type: Nav_Att.T
    description: Sunline direction vector in spacecraft body frame.
```

## Complete Example: rate_control (with parameters)

### parameters.yaml
```yaml
---
description: Parameters for the Rate Control component
parameters:
  - name: Derivative_Gain_P
    description: "[N*m*s] Rate error feedback gain applied"
    type: Packed_F32.T
    default: "(Value => 0.0)"
  - name: Spacecraft_Inertia
    description: "[kg m^2] Spacecraft inertia matrix (3x3 row-major, 9 elements)"
    type: Packed_F32x9.T
    default: "[others => 0.0]"
```
