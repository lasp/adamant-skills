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

Add this connector:
```yaml
  - description: The parameter update connector.
    type: Parameter_Update.T
    kind: modify
```

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

### Parameters vs Data Dependencies Decision

**Use Parameters when:**
- Configuration data changing infrequently (gains, inertia, calibration)
- Set via ground command

**Use Data Dependencies when:**
- Changes every control cycle
- Computed by another component
- Dynamic state (attitude, position, sensor readings)