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

## Tester Architecture

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

**Order:** `Init_Base` → `Connect` → `Component_Instance.Init` → `Set_Up`. Init params go to `Component_Instance.Init`, NOT `Init_Base`.

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

**CRITICAL:** Clearing raw history does NOT clear typed histories. Use cumulative counts or clear typed histories explicitly: `T.My_Event_History.Clear;`

## Active Component Testing (Async Dispatch)

```ada
-- Send to async connectors (queued, not processed yet)
T.Async_Data_Send (data1);
T.Async_Data_Send (data2);
Natural_Assert.Eq (T.Output_History.Get_Count, 0);  -- Nothing yet

-- Dispatch processes the queue (FUNCTION returning Natural)
Natural_Assert.Eq (T.Dispatch_All, 2);  -- Must capture return value
Natural_Assert.Eq (T.Output_History.Get_Count, 2);

-- Queue overflow testing
-- Use small Queue_Size in Init_Base (e.g., 100 bytes) for overflow tests
-- CRITICAL: Expect_*_Dropped auto-resets to False after each drop
for I in 1 .. N loop
   T.Expect_Async_Data_Send_Dropped := True;  -- Must set before EVERY send
   T.Async_Data_Send (overflow_data);
end loop;
Natural_Assert.Gt (T.Async_Data_Send_Dropped_Count, 0);
```

## Command Response Verification

```ada
Natural_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get_Count, 1);
Command_Response_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get (1), (
   Source_Id => 0,
   Registration_Id => expected_reg_id,
   Command_Id => T.Commands.Get_Set_Value_Id,  -- Use ID getter
   Status => Success));
```

Use `Command_Enums.Command_Response_Status.E` for response status (NOT `Command_Execution_Status`).
Need `use type Command_Enums.Command_Response_Status.E;` for `=` operator visibility.

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

## Data Dependency Testing

The tester generates named fields for each data dependency. Set them directly:
```ada
-- CRITICAL: Use non-zero timestamps! (0,0) causes staleness failures.
Test_Time : constant Sys_Time.T := (100, 0);

-- In Set_Up_Test:
T.System_Time := Test_Time;
T.Data_Dependency_Timestamp_Override := Test_Time;

-- Set mock values (field names match data_dependencies.yaml names)
T.Setpoint := (Value => 50.0);          -- Packed_F32.T
T.Process_Value := (Value => 45.0);     -- Packed_F32.T
T.Tick_T_Send ((Time => Test_Time, Count => 0));  -- Match timestamps!
-- Component calls Self.Get_Setpoint(...) which reads T.Setpoint

-- Test stale data (override timestamp returned by tester)
T.Data_Dependency_Timestamp_Override := (50, 0);  -- Old timestamp
T.Tick_T_Send ((Time => (100, 0), Count => 0));

-- Test missing data (override return status)
T.Data_Dependency_Return_Status_Override := Id_Out_Of_Range;
T.Tick_T_Send ((Time => (100, 0), Count => 0));
```

**Implementation needs:** `with Data_Product_Enums; use Data_Product_Enums; use Data_Product_Enums.Data_Dependency_Status;` in the component body for status checks.

## Test Body With-Clauses

Test bodies need explicit `with` for any types referenced directly:
```ada
with Tick;                                          -- If creating Tick.T values
with Interfaces; use Interfaces;                    -- For Unsigned_32 casts (ONLY if base class lacks it)
with Basic_Assertions; use Basic_Assertions;        -- Natural_Assert, Boolean_Assert
with Packed_F32.Assertion; use Packed_F32.Assertion; -- Typed assertions
with Command_Enums;                                 -- For command response checks
with Data_Product_Enums;                            -- For data dependency status
with My_Custom_Type;                                -- Custom project types used in params/DPs
use type Command_Enums.Command_Response_Status.E;   -- For = operator
```

**Rule:** If you reference ANY type in a test body (creating values, comparing history entries), you MUST have a `with` for its package. This includes custom project types from `src/types/`.

**Style rule:** Only `with` what you actually use. Remove `with Tick;` if you inline the aggregate. Remove `with Smart_Assert;` if you use `Basic_Assertions` instead. `redo style` flags all unused imports.

## Common Errors (with Explanations)

1. **Wrong stimulus API:** Use `T.*_T_Send` to stimulate, NOT `T.*_T_Recv_Sync` (that's capture)
2. **History .Get returns packed .T:** Compare with typed assertions like `Packed_U32_Assert.Eq`
3. **Init params → `Component_Instance.Init`**, NOT `Init_Base` (Init_Base takes only Queue_Size)
4. **Typed histories don't auto-clear** when raw history is cleared — most common mistake
5. **History depth is 100** — clear mid-test to avoid overflow (each tick sending 2 DPs = 2 slots)
6. **`Dispatch_All` is a FUNCTION** returning Natural — must capture: `Count := T.Dispatch_All;`
7. **Copy tester files from `build/template/`**, never hand-write them
8. **`*_tests-implementation.ads` MUST come from template** (has correct base class)
9. **History naming:** `{entity_name}_History` (not `_Event_History` or `_Data_Product_History`)
10. **No `Packed_U8`** — use `Packed_Byte.T`
11. **Tick.T.Count is Unsigned_32** — use `Interfaces.Unsigned_32(I)` for loop casts
12. **Change detection initial state:** First tick fires extra DP because shadow differs from computed value
13. **Packet.T Header has NO Priority field** — only Time, Id, Sequence_Count, Buffer_Length
14. **Named Event.T send connectors crash** on non-component event IDs — remove `Dispatch_Event` from tester override
15. **Instance record names like `Queue` conflict** with generated base class -- use prefixed names
16. **Unused `Status` variable** in parameter tests -- use `pragma Unreferenced (Status);` or check it
17. **Test spec `with Tester`** and **`unnecessary with of ancestor`** warnings -- generated template artifacts, cannot fix without modifying templates (would be overwritten by `redo templates`)
18. **Use `[]` for array aggregates** -- `[others => 0]` not `(others => 0)`. Record aggregates stay `()`
19. **`use Command_Execution_Status.E;`** is useless -- the `use type` in generated code already provides operator visibility
20. **`Dispatch_All` result must be captured or discarded** -- if you don't check the count, call bare `T.Dispatch_All;` without `Count :=`
21. **`then` on its own line** for multi-line if/elsif conditions (Ada style `-gnatyi`)

22. **`AUnit.Assertions` removal caution:** GNAT reports "no entities referenced" even when bare `Assert(...)` is called via `use` clause. Only remove if ALL assertions use qualified names (`Natural_Assert.Eq`, `Packed_U32_Assert.Eq`). Grep for bare `Assert (` before removing.
23. **`Dispatch_All` only exists on active component testers** -- passive components process synchronously, no queue, no `Dispatch_All`. Calling it on a passive tester is a compile error.
24. **Removing `with` clauses:** `use X;` makes operators and subprograms directly visible -- removing `with X;` breaks those even if GNAT says the `with` is unused. Grep body for types/operators from the package before removing.

## Invalid Command Testing

```ada
Invalid_Cmd : Command.T := T.Commands.Set_Value ((Value => 0));
Invalid_Cmd.Header.Arg_Buffer_Length := 0;  -- Wrong length
T.Command_T_Send (Invalid_Cmd);
-- Verify Length_Error response
Command_Response_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get (1), (
   Source_Id => 0, Registration_Id => expected_reg_id,
   Command_Id => T.Commands.Get_Set_Value_Id, Status => Length_Error));
```

## Error Injection

```ada
-- For any send connector, tester provides Expect_*_Dropped
T.Expect_Data_Product_T_Send_Dropped := True;
-- Component tries to send → tester captures drop instead of asserting failure
T.Expect_Data_Product_T_Send_Dropped := False;  -- Reset
```

## Coverage

See [references/coverage-guide.md](references/coverage-guide.md) for full guide.

```bash
rm -rf build && redo coverage            # MUST clean first
# Focus on component-*-implementation.adb (YOUR code)
# Ignore framework/generated files in coverage.txt
```

**Structural ceiling (~80-85%):** `Send_Dropped` null handlers, `Invalid_Command`, and `Recv_Async_Dropped` are structurally uncoverable because the tester always connects all connectors and always produces valid command arguments.

| Component Type | Realistic Target |
|---|---|
| Simple passive (no commands) | 95-100% |
| Passive with commands | 80-90% |
| Active (async recv) | 75-85% |
| Active with commands | 70-80% |

### Coverage Improvement Workflow

1. Run `rm -rf build && redo coverage`
2. Read `build/coverage/coverage.txt`, find `component-*-implementation.adb` section
3. Map missing line numbers to source: `cat -n component-*-implementation.adb`
4. Identify pattern: untested branch, unexercised connector, data dependency path
5. Add test to `tests.yaml` → `redo templates` → copy spec → implement → verify

### Common Uncovered Patterns

- **Untested connector:** Add test that sends via that connector
- **Untested branch:** Add test with input triggering the uncovered if/elsif/else
- **Active async path at 0%:** Must send AND `Dispatch_All` — just sending queues without processing
- **Data dependency path at 0%:** Override tester's `*_T_Service` to return success with test data

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
