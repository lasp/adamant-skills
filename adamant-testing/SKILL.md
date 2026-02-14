---
name: adamant-testing
description: Comprehensive testing patterns and infrastructure for Adamant embedded software framework components
---

# Adamant Testing Framework

Auto-generated reciprocal testers with history capture and white-box component access.

## Test Structure

```
component_name/test/
├── component_name.tests.yaml                              # Test model (REQUIRED)
├── test.adb                                               # AUnit runner (from template)
├── env.py                                                 # Build path (REQUIRED, NOT auto-generated)
├── component-component_name-implementation-tester.ads/adb # Generated tester (from template)
└── component_name_tests-implementation.ads/adb            # Handwritten tests
```

**CRITICAL rules:**
- Test dirs use `env.py`, NOT `.all_path` (causes duplicate conflicts)
- File naming: `{component_name}.tests.yaml`, NOT bare `tests.yaml`
- Test spec (`*_tests-implementation.ads`) MUST come from `redo templates`
- `tests.yaml` MUST be in `test/` dir, NOT component dir

Setup: `bash scripts/mk_test_env.sh [test_names...]` (from component directory)

## Workflow

```bash
redo templates                              # Generate tester stubs
cp build/template/component-*-tester.ads build/template/component-*-tester.adb .
cp build/template/*_tests-implementation.ads .   # ONLY spec, NOT .adb (overwrites tests!)
cp build/template/test.adb .
redo test                                   # Build and run
rm -rf build && redo coverage               # Coverage (MUST clean first)
```

**Adding tests:** Add to tests.yaml → `redo templates` → copy ONLY the `*_tests-implementation.ads` → add implementation in `.adb` → `redo test`.

## Test Model

```yaml
tests:
  - name: Test_Nominal
    description: Test nominal behavior
  - name: Test_Error_Paths
```

## env.py (Minimum)

```python
from environments import test  # noqa: F401
```

## Tester Architecture (Brief)

Testers are **reciprocal components** with inverted connectors:
- Component sends → tester receives (captures in histories)
- Component receives → tester sends (provides stimuli)
- White-box access via `T.Component_Instance`

## Test Lifecycle

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;                          -- (Queue_Size => N for active)
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Init (Param => 42);  -- IFF YAML has init:
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;

overriding procedure Tear_Down_Test (Self : in out Instance) is
begin
   Self.Tester.Final_Base;
end Tear_Down_Test;

overriding procedure Test_Name (Self : in out Instance) is
   T : Component.Name.Implementation.Tester.Instance_Access renames Self.Tester;
begin
   T.Tick_T_Send ((Time => (0, 0), Count => 1));
   Natural_Assert.Eq (T.Event_T_Recv_Sync_History.Get_Count, 1);
end Test_Name;
```

## Sending Stimuli

```ada
T.Tick_T_Send ((Time => (0, 0), Count => 1));
T.Command_T_Send (T.Commands.My_Command ((Field => Value)));   -- with args
T.Command_T_Send (T.Commands.My_Noop_Command);                 -- no args

-- Parameters (3-step + tick):
Status := T.Stage_Parameter (T.Parameters.Param_Name ((Field => Value)));
Status := T.Validate_Parameters;
Status := T.Update_Parameters;
T.Tick_T_Send (The_Tick);  -- component applies in tick handler
```

**ALWAYS use `T.Commands` / `T.Parameters`** — never create local instances (wrong ID bases).

## History Verification

**Dual-level capture:** raw connector history + individual typed histories.

```ada
-- Raw (all events/DPs/faults)
Natural_Assert.Eq (T.Event_T_Recv_Sync_History.Get_Count, 3);
-- Typed (specific event/DP/fault)
Natural_Assert.Eq (T.My_Event_History.Get_Count, 1);
-- Access (1-indexed)
Packed_U32_Assert.Eq (T.Counter_History.Get (1), (Value => 42));
-- Clear between phases
T.Event_T_Recv_Sync_History.Clear;
```

**Named connectors:** `name: Spi_Data` on send → `Spi_Data_T_Recv_Sync_History` in tester.

## Assertion Hierarchy (Most → Least Preferred)

1. **Packed type assertions:** `Packed_U32_Assert.Eq(...)` — type-safe, clear errors
2. **Basic_Assertions:** `Natural_Assert.Eq(...)`, `Boolean_Assert.Eq(...)` — counts, flags
3. **pragma Assert:** `pragma Assert (condition);` — simple checks
4. **AUnit Assert:** `Assert(condition, "message")` — fallback

Do NOT call `Smart_Assert.Eq(...)` directly — requires generic instantiation first.

```ada
with Basic_Assertions; use Basic_Assertions;
with Packed_U32.Assertion; use Packed_U32.Assertion;
with Command_Enums; use type Command_Enums.Command_Response_Status.E;
```

## Visibility in Tests

- Command response: `Command_Enums.Command_Response_Status.E` (not standalone)
- Command ID: `T.Commands.Get_Reset_Counter_Id` (getter function, not field)
- `use type` needed for `=` on enums: `use type Command_Enums.Command_Response_Status.E;`

## Common Errors (One-Liners)

Details: [references/common-errors-detail.md](references/common-errors-detail.md)

1. Use `T.*_T_Send` to stimulate, NOT `T.*_T_Recv_Sync` (that's capture)
2. History `.Get(N)` returns packed `.T` directly — use typed assertions
3. Init params → `Component_Instance.Init(...)`, NOT `Init_Base`
4. Typed histories don't auto-clear when raw history is cleared
5. History depth is 100 — clear mid-test to avoid overflow
6. `Dispatch_All` is a FUNCTION returning Natural — capture the return
7. Copy tester files from `build/template/`, never hand-write them
8. `*_tests-implementation.ads` MUST come from template (has correct base)
9. History naming: `{entity_name}_History` (not `_Event_History`)
10. No `Packed_U8` — use `Packed_Byte.T`

## Coverage

See [references/coverage-guide.md](references/coverage-guide.md). Key: `rm -rf build` before `redo coverage`. Focus on `component-*-implementation.adb`, not aggregate total (~80-85% ceiling due to null handlers).

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
