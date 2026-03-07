# Model-Based COSMOS Test Derivation

Derive all COSMOS command names, telemetry packet names, and telemetry item
names directly from the Adamant YAML models. Never guess names or read the
generated cmd.txt/tlm.txt -- the naming is fully deterministic.

## Source Models

For any assembly, the test-relevant information comes from these files:

1. **Assembly YAML** (`*.assembly.yaml`) -- component instances + their types
2. **Product packets YAML** (`*.product_packets.yaml`) -- telemetry packet definitions
3. **Component commands YAML** (`*.commands.yaml`) -- available commands per component
4. **Component data products YAML** (`*.data_products.yaml`) -- DP names and types
5. **Component events YAML** (`*.events.yaml`) -- event definitions
6. **Component parameters YAML** (`*.parameters.yaml`) -- parameter definitions
7. **Component faults YAML** (`*.faults.yaml`) -- fault definitions

## Deriving COSMOS Command Names

**Template rule:** `TARGET Instance_Name-Command_Name`

The COSMOS generator iterates all commands from all components in the assembly.
Each command becomes:

```
COMMAND <target> <instance_name>-<command_name> ...
```

Where:
- `<target>` = plugin target name (from plugin.txt, typically assembly name)
- `<instance_name>` = the `name:` field of the component in assembly YAML
- `<command_name>` = the command name from the component's `commands.yaml`

### Example

Assembly YAML:
```yaml
components:
  - type: Command_Router
    name: Command_Router_Instance
```

Command_Router has built-in commands: `Noop`, `Noop_Arg`, `Noop_Response`

COSMOS commands:
```
cmd("TARGET Command_Router_Instance-Noop")
cmd("TARGET Command_Router_Instance-Noop_Arg with Value 42")
```

### Framework Component Commands (always present)

These framework components have commands that appear in every assembly:

| Component | Instance Name (from assembly) | Commands |
|-----------|-------------------------------|----------|
| Command_Router | (as named) | Noop, Noop_Arg, Noop_Response, Reset_Data_Products |
| Event_Packetizer | (as named) | Send_Packet, Disable_Packet, Enable_Packet, Set_Packet_Period, Enable_Packet_On_Change |
| Product_Packetizer | (as named) | Send_Packet, Disable_Packet, Enable_Packet, Set_Packet_Period, Enable_Packet_On_Change |
| Product_Database | (as named) | Dump, Dump_Poly_Type, Clear_Override, Clear_Override_For_All |
| Ccsds_Command_Depacketizer | (as named) | Reset_Counts |
| Parameters | (as named, if present) | Update_Parameter, Dump_Parameters |

### Custom Component Commands

Read the component's `commands.yaml`:

```yaml
commands:
  - name: Set_Threshold
    description: "Set temperature threshold"
    arg_type: Packed_U32.T
```

COSMOS command: `cmd("TARGET Instance_Name-Set_Threshold with Value <u32>")`

**Command argument naming:**
- If `arg_type` is a simple type: single parameter named `Value`
- If `arg_type` is a packed record: parameters named by the record's fields
  (flattened with `.` separators)
- If no `arg_type`: command takes no parameters

## Deriving COSMOS Telemetry Packet Names

**Template rule:** `TELEMETRY <target> <packet_name>`

Packet names come from `product_packets.yaml`:

```yaml
packets:
  - name: Safe_Mode_Thermal_Packet
    id: 1
    description: "SAFE state thermal telemetry"
    items:
      - component: Safe_Survival_Heater_Ctrl_Instance
        data_product: Temperature
      - component: Safe_Temperature_Watchdog_Instance
        data_product: Temperature
```

COSMOS packet name: `Safe_Mode_Thermal_Packet` (exactly as written in YAML)

### Standard Packets (always present)

| Packet | Source | Contents |
|--------|--------|----------|
| Events_Packet | Event_Packetizer | Variable-length event subpackets |
| Dump_Packet | Product_Database | On-demand DP dumps |
| Active_Parameters | Parameters (if present) | Current parameter values |
| Error_Packet | (if configured) | Error event subpackets |

## Deriving COSMOS Telemetry Item Names

**Template rule:** `Instance_Name.Dp_Name.Field_Path.Value`

Each item in a product packet maps to a data product from a specific component
instance. The COSMOS item name is:

```
<instance_name>.<dp_name>.<field>.Value
```

Where:
- `<instance_name>` = component instance name from assembly YAML
- `<dp_name>` = data product name from the component's `data_products.yaml`
- `<field>` = for simple types, this is empty; for packed records, the field path

### Simple Type Example

Component `data_products.yaml`:
```yaml
data_products:
  - name: Temperature
    type: Packed_F32.T
```

Assembly instance name: `Safe_Survival_Heater_Ctrl_Instance`

COSMOS telemetry:
```python
tlm("TARGET Packet_Name Safe_Survival_Heater_Ctrl_Instance.Temperature.Value")
```

### Packed Record Example

If the DP type is a packed record with fields:
```yaml
# record: Thermal_Status.T
fields:
  - name: Temperature
    type: Packed_F32.T
  - name: Status_Flag
    type: Packed_U8.T
```

COSMOS telemetry items (flattened):
```python
tlm("TARGET Packet_Name Instance.Thermal_Status.Temperature.Value")
tlm("TARGET Packet_Name Instance.Thermal_Status.Status_Flag.Value")
```

### Standard Header Items (every packet)

Every CCSDS telemetry packet includes these auto-generated items:
- `Version` (3 bits)
- `Packet_Type` (1 bit)
- `Secondary_Header` (1 bit)
- `Apid` (11 bits) -- matches packet `id:` from product_packets.yaml
- `Sequence_Flag` (2 bits)
- `Sequence_Count` (14 bits) -- **key for flow verification** (increments each send)
- `Packet_Length` (16 bits)
- `Seconds` (32 bits) -- GPS time
- `Subseconds` (16 bits)
- `CRC` (16 bits)

Flow test pattern:
```python
seq1 = tlm("TARGET Packet_Name Sequence_Count")
wait(3)
seq2 = tlm("TARGET Packet_Name Sequence_Count")
assert seq2 > seq1, "Packet not flowing"
```

## Deriving Test Cases from Component Models

### From commands.yaml -> Command Acceptance Tests

For each command in each component:
```python
def test_{instance}_{command}_accepted(self):
    cmd("TARGET Instance-Command")
    # Verify via sequence count or data product change
```

### From data_products.yaml -> Telemetry Verification Tests

For each data product in each product packet:
```python
def test_{instance}_{dp}_in_range(self):
    val = tlm("TARGET Packet Instance.Dp.Value")
    assert lo <= val <= hi  # range from type definition
```

### From events.yaml -> Event Flow Tests

Events appear in the Events_Packet as subpackets. Test indirectly:
```python
def test_{instance}_emits_events(self):
    seq1 = tlm("TARGET Events_Packet Sequence_Count")
    cmd("TARGET Event_Packetizer_Instance-Send_Packet with Id 0")
    wait(3)
    seq2 = tlm("TARGET Events_Packet Sequence_Count")
    assert seq2 > seq1
```

### From parameters.yaml -> Parameter Update Tests

```python
def test_{instance}_parameter_update(self):
    cmd("TARGET Parameters_Instance-Update_Parameter with ...")
    # Verify via Active_Parameters packet or component behavior change
```

### From faults.yaml -> Fault Injection Tests (if testable)

Faults are typically triggered by component logic, not direct commands.
Test by manipulating inputs that should trigger the fault condition.

## Workflow Summary

```
1. Read assembly YAML
   -> Extract: all component instances (name + type)
   -> Extract: product_packets.yaml reference

2. Read product_packets.yaml
   -> Extract: packet names + item mappings (instance + dp_name)

3. For each component type, read its YAML files:
   -> commands.yaml -> available commands
   -> data_products.yaml -> DP names and types
   -> events.yaml -> event names (for indirect verification)
   -> parameters.yaml -> parameter entries

4. Apply naming rules to derive ALL COSMOS names

5. Write tests using ONLY derived names
   -> Command tests: one per command
   -> Telemetry tests: one per packet (flow) + one per item (range)
   -> Parameter tests: one per parameter entry
   -> Infrastructure tests: Noop, event flush, product dump
```

## Instance Name Convention

The assembly YAML `name:` field for each component becomes the COSMOS
instance name. Common patterns:

- Framework components: `Command_Router_Instance`, `Event_Packetizer_Instance`, etc.
- Custom components: `Safe_Survival_Heater_Ctrl_Instance` or just the component
  name as-is (depends on how the assembly author named them)

**Always read the actual assembly YAML** to get the exact instance names.
The component type name and the instance name may differ.
