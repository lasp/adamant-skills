<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Template Analysis: Code Generation Edge Cases

Key patterns from Jinja2 templates in `adamant/gen/templates/component/` not fully documented elsewhere.

## `with` Clause Generation

- **Base class spec**: Only `Interfaces` and `Connector_Types` get automatic `use` clauses
- **Base class body**: No automatic `use` clauses (conservative)
- **Implementation template**: Minimal includes — enforces the "don't with framework packages" rule
- **Tester reciprocals**: Use `pragma Warnings` to suppress unused package warnings; only `Connector_Types` gets `use`

## Abstract vs Concrete Generation

**Abstract (must override):**
- `Init` — only if YAML has `init:` section
- All invokee connector handlers (`recv_sync`, `recv_async`, `modify`, `service`, `return`)
- All `*_Send_Dropped` handlers for `send` connectors
- Per-command handler functions + `Invalid_Command` (when commands.yaml exists)

**Concrete (framework provides):**
- `*_Send_If_Connected`, `*_Send`, `Is_*_Connected` for invoker connectors
- `Sys_Time_T_Get` for get connectors
- `Set_Id_Bases`, `Map_Data_Dependencies`, `Init_Base`

## Array Connector Edge Cases

- **count: 0**: Dynamic sizing by assembly. Uses `Array_Access` (pointer). Index type: `subtype Name_Index is Connector_Index_Type`
- **count: 1 or omitted**: No index parameter. Direct instance storage.
- **count: N > 1**: Fixed array. Range: `First .. First + N - 1`
- Testers always use single index (`First .. First`) for invokee connectors

## Parameter Protected Object

When `parameters.yaml` exists, base body generates:
- Staged vs active parameter distinction
- Protected staging/fetching per parameter
- Table ID tracking, ready-to-update flag management

## Tester Data Dependencies

Components with data dependencies get non-zero default system time (`(10000, 0)`) to avoid staleness errors in tests. Others get `(0, 0)`.

## Generic Component Handling

- `common` connectors use `renames` in tester reciprocals (efficiency)
- Non-common connectors use generic instantiation
- Generic components get extra `pragma Warnings` in tester code

## Compile-Time Size Checking

Commands package generates compile-time errors if argument types exceed buffer:
```ada
pragma Compile_Time_Error (
   My_Type.Size_In_Bytes > Command_Types.Command_Arg_Buffer_Type'Length,
   "Command argument type too large for Command.T buffer.");
```
