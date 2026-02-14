---
name: adamant-component-dev
description: Patterns and workflows for developing components in the Adamant embedded software framework
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

**CRITICAL**: Do NOT create a `build/` directory manually.

## Workflow

```bash
redo templates && cp build/template/* .   # Generate and copy stubs
redo all                                  # Build
redo test                                 # Run tests
```

## Component Model (YAML)

```yaml
description: What this component does
execution: passive|active|either
with:
  - "Custom_Types"                 # ONLY custom packages (NOT connector types)
preamble: |
  subtype Custom_Type is Natural range 1 .. 100;
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
      default: "10"
      description: What this parameter does
interrupts:
  - name: Timer_Interrupt
subtasks:
  - name: Listener
```

## Feature Model Formats

```yaml
# commands.yaml — requires Command.T recv_sync + Command_Response.T send connectors
commands:
  - name: Set_Value
    description: Set the value
    arg_type: Packed_U32.T            # Omit for no-arg commands

# events.yaml — requires Event.T send connector
events:
  - name: Value_Changed
    description: The value was changed
    param_type: Packed_U32.T          # Omit for no-param events

# data_products.yaml — requires Data_Product.T send connector
data_products:
  - name: Current_Value
    type: Packed_U32.T

# data_dependencies.yaml — requires Data_Product_Fetch.T/Return.T request + Sys_Time.T get
data_dependencies:
  - name: Sensor_Reading
    type: Sensor_Data.T

# parameters.yaml — requires Parameter_Update.T modify connector
parameters:
  - name: Start_Count
    type: Packed_U16.T
    default: "(Value => 0)"           # REQUIRED

# faults.yaml — requires Fault.T send connector
faults:
  - name: Bad_Value_Fault
    param_type: Packed_U32.T          # Optional

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

**Feature connectors are NOT auto-generated** — you MUST list them in component.yaml. Validation: `bash scripts/check_connectors.sh`.

## Connector Compatibility

```
send → recv_sync | recv_async    request → service
get  → return                    provide → modify
```

## Generated Code API (Quick Reference)

See [references/generated-api.md](references/generated-api.md) for full details.

- Events: `Self.Event_T_Send_If_Connected (Self.Events.Name (The_Time, (Value => X)));`
- Data products: `Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Name (The_Time, Val));`
- Faults: `Self.Fault_T_Send_If_Connected (Self.Faults.Name (The_Time));`
- Commands: implement `overriding function Cmd_Name (...) return Command_Execution_Status.E;`
- Time: `The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;`
- Send: use `*_Send_If_Connected` (safe) vs `*_Send` (asserts connected)

## Execution Model

- **Passive**: Synchronous processing. Only has Init if YAML defines `init:` section.
- **Active**: Message queue. Init MUST call `Self.Init_Base(Queue_Size)` (bytes). Has `{Type}_T_Recv_Async` handlers and `{Type}_T_Recv_Async_Dropped` overflow handlers.
- Command connectors stay `recv_sync` even on active components.

## Pre-Flight Checklist

Details for each item: [references/pitfalls-and-checklist.md](references/pitfalls-and-checklist.md)

1. [ ] Spec uses `with private` / private full record pattern
2. [ ] `Init` override present IFF YAML has `init:` section
3. [ ] `Invalid_Command` (procedure, 4 params) present IFF `commands.yaml` exists
4. [ ] `Command_T_Recv_Sync` present IFF `commands.yaml` exists
5. [ ] ALL `*_Send_Dropped` handlers overridden for every send connector
6. [ ] NO `with` for auto-provided packages (Event, Sys_Time, Command_Execution_Status, etc.)
7. [ ] NO `build/` directory created manually
8. [ ] Empty `.all_path` file present (helper: `bash scripts/mk_all_path.sh <dir>`)
9. [ ] Entity names unique across events, data products, commands, faults, parameters
10. [ ] `use Command_Execution_Status;` INSIDE package body, not before it
11. [ ] `get` connectors: `return_type:` only. `request`: both `type:` and `return_type:`
12. [ ] Custom record fields have `format:` specified (see adamant-type-system)
13. [ ] Qualify ambiguous literals: `Command_Execution_Status.Success`
14. [ ] No `Packed_U8` — use `Packed_Byte.T`
15. [ ] No dynamic allocation (Ravenscar profile)
16. [ ] Active + recv_async: override `{Type}_T_Recv_Async_Dropped`
17. [ ] Parameter overrides: `Invalid_Parameter`, `Parameter_Update_T_Modify`, `Update_Parameters_Action`
18. [ ] Data dependency overrides: `Get_Data_Dependency`, `Invalid_Data_Dependency`
19. [ ] Faults use event-like API, NOT `Set_Status`
20. [ ] No `with Command_Response_Status` (not standalone)
21. [ ] Component name doesn't collide with ~55 framework components (`bash scripts/check_name_collision.sh <name>`)

## Related Skills

- **Types**: [adamant-type-system](../adamant-type-system/SKILL.md)
- **Testing**: [adamant-testing](../adamant-testing/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
- **Algorithm wrapping**: [adamant-algorithm-wrapping](../adamant-algorithm-wrapping/SKILL.md)
