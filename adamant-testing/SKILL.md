---
name: adamant-testing
description: Comprehensive testing patterns and infrastructure for Adamant embedded software framework components. Use when writing unit tests, creating test harnesses, using the History API, testing commands/parameters/faults/data products, or debugging test failures.
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

**⚠️ CRITICAL -- NEVER write tester .ads/.adb or test.adb from scratch.** These files are ~500 lines of generated code with complex reciprocal connector wiring, History API instantiation, and AUnit scaffolding. ALWAYS generate them:

```bash
# From the test/ directory:
cd test/
redo templates                              # Generate ALL tester stubs
cp build/template/component-*-tester.ads .  # Tester spec (generated)
cp build/template/component-*-tester.adb .  # Tester body (generated)
cp build/template/*_tests-implementation.ads .   # Test spec (generated)
cp build/template/test.adb .               # AUnit runner (generated)
# Then write ONLY: *_tests-implementation.adb (test case bodies)
redo test                                   # Build and run
redo coverage                                # Coverage analysis via gcov
```

**The ONLY file you write from scratch is `*_tests-implementation.adb`** (the test case bodies). Everything else is generated. You also need `env.py` and `*.tests.yaml`.

**⚠️ Test body package name is `<Component_Name>_Tests.Implementation`** (e.g., `Signal_Processor_Tests.Implementation`), NOT `Component.<Name>.Implementation.Tester.Tests.Implementation`. The file name is `<component_name>_tests-implementation.adb`. Match what `redo templates` generates in `*_tests-implementation.ads`.

**Adding tests:** Add to tests.yaml -> `redo templates` -> copy ONLY the `*_tests-implementation.ads` -> add implementation in `.adb` -> `redo test`.

## Test Body `with` Clauses

The test body (`*_tests-implementation.adb`) does NOT inherit visibility from the generated tester. You must explicitly `with` every package you use. Common pattern:

```ada
-- Required for most test bodies:
with Interfaces; use Interfaces;          -- Unsigned_16, Unsigned_32, etc.
with Basic_Assertions; use Basic_Assertions;  -- Natural_Assert, Boolean_Assert

-- For typed assertion packages (match your data product/event param types):
with Packed_U32.Assertion; use Packed_U32.Assertion;  -- Packed_U32_Assert
with Packed_U16.Assertion; use Packed_U16.Assertion;

-- For command response checking:
with Command_Enums; use Command_Enums;

-- For framework types used directly in test logic:
with Tick;                                -- qualify as Tick.T in sends
with Command;                             -- for invalid command construction
with Sys_Time;                            -- for timestamps
with Data_Product;                        -- if inspecting raw DPs

-- For command response/status assertions:
with Command_Enums.Assertion; use Command_Enums.Assertion;
-- Gives: Command_Response_Status_Assert, Command_Execution_Status_Assert

-- NEVER with these (they don't exist as standalone packages):
-- Command_Response_Status  (use Command_Enums.Command_Response_Status)
-- Command_Execution_Status (use Command_Enums.Command_Execution_Status)
```ada

**Name collisions**: `Tick` can collide with `Ada.Real_Time.Tick`. Always qualify: `Tick.T`, not just `T` when ambiguous. Add `use Tick;` if you reference `Tick.T` frequently.

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
```ada

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
```ada

**Order:** `Init_Base` → `Connect` → `Component_Instance.Init` → `Set_Up`. Init params go to `Component_Instance.Init`, NOT `Init_Base`. Both Init and Set_Up are optional -- only call them if YAML declares `init:` or component overrides Set_Up. For per-test init params, defer Init/Set_Up to each test body (see [test-corpus.md](references/test-corpus.md) pattern 1h).

**⚠️ History Depth**: Generated `Init_Base` initializes all histories with `Depth => 100`. If a test sends more than 100 events/data products/commands, the history overflows and the test fails with "History is full." Solutions:
- Increase depth in Init_Base: `Self.Event_T_Recv_Sync_History.Init (Depth => 500);`
- Clear histories mid-test: `Self.Tester.Event_T_Recv_Sync_History.Clear;`
- Design tests to use fewer iterations (preferred -- keep tests small and focused)

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
```ada

**ALWAYS use `T.Commands` / `T.Parameters`** -- never create local instances (wrong ID bases).
For custom packed types on connectors: construct unpacked (.U) then `Pack`: `T.Cmd_T_Send (My_Type.Pack (unpacked_val));`

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
```ada

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
```ada

Use `Command_Enums.Command_Response_Status.E` for response status (NOT `Command_Execution_Status`).
Need `use type Command_Enums.Command_Response_Status.E;` for `=` operator visibility.

## Assertion Hierarchy (Most → Least Preferred)

1. **Packed type assertions:** `Packed_U32_Assert.Eq(...)` -- type-safe, clear errors
2. **Basic_Assertions:** `Natural_Assert.Eq(...)`, `Boolean_Assert.Eq(...)` -- counts, flags
3. **pragma Assert:** `pragma Assert (condition);` -- simple checks
4. **AUnit Assert:** `Assert(condition, "message")` -- fallback

Do NOT call `Smart_Assert.Eq(...)` directly -- requires generic instantiation first.

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
```ada

**Implementation needs:** `with Data_Product_Enums; use Data_Product_Enums; use Data_Product_Enums.Data_Dependency_Status;` in the component body for status checks.

## Test Body With-Clauses

Add `with` for every type referenced in tests: `Basic_Assertions`, `Packed_F32.Assertion`, `Command_Enums`, `Interfaces`, custom types from `src/types/`. Only `with` what you use -- `redo style` flags unused imports.

## Common Errors

Top errors that waste time (full list with explanations: [common-errors-detail.md](references/common-errors-detail.md)):

1. **Wrong stimulus API:** `T.*_T_Send` to stimulate, NOT `T.*_T_Recv_Sync`
2. **Init params → `Component_Instance.Init`**, NOT `Init_Base`
3. **Typed histories don't auto-clear** when raw history cleared
4. **`Dispatch_All` is a FUNCTION** returning Natural (active components only)
5. **History depth is 100** -- clear mid-test for heavy DP producers
6. **No `Packed_U8`** -- use `Packed_Byte.T`
7. **Tick.T.Count is Unsigned_32** -- cast loop vars
8. **Named Event.T send connectors crash** on non-component event IDs
9. **Array aggregates use `[]`**, record aggregates use `()`
10. **Copy tester files from `build/template/`**, never hand-write

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

## Deferred Init (Per-Test Initialization)

When tests need different init params, skip Init/Set_Up in `Set_Up_Test` (keep only `Init_Base` + `Connect`), call `Component_Instance.Init` + `Set_Up` in each test body.

## Multiple Command Connectors

Named command connectors generate `_Send`, `_Send_2`, etc.:
```ada
T.Command_T_Send (cmd);     -- First command connector
T.Command_T_Send_2 (cmd2);  -- Second command connector (named in YAML)
```

## Error Injection

```ada
-- For any send connector, tester provides Expect_*_Dropped
T.Expect_Data_Product_T_Send_Dropped := True;
-- Component tries to send → tester captures drop instead of asserting failure
T.Expect_Data_Product_T_Send_Dropped := False;  -- Reset
```

## Send_Dropped Testing

Send_Dropped fires when connector IS attached but receiver returns `Message_Dropped` -- NOT when unattached (`Send_If_Connected` skips entirely).

### Sync sends (most common)

```ada
-- Set tester connector status to trigger Send_Dropped:
T.Connector_Event_T_Recv_Sync_Status := Connector_Types.Message_Dropped;
T.Connector_Data_Product_T_Recv_Sync_Status := Connector_Types.Message_Dropped;
T.Tick_T_Send ((Time => (0, 0), Count => 1));  -- Triggers sends
-- Restore:
T.Connector_Event_T_Recv_Sync_Status := Connector_Types.Success;
T.Connector_Data_Product_T_Recv_Sync_Status := Connector_Types.Success;
```ada

Field names: `Connector_<Type>_Recv_Sync_Status` in generated reciprocal `.ads`.

### Async sends

Use `Expect_*_Dropped` tester flag (hand-edit tester). See framework `command_router` tests.

## Parameter Testing (Update_Parameters_Action Coverage)

The tester's 3-step Stage/Validate/Update protocol does NOT call `Update_Parameters_Action`. The tester's `Update_Parameters` sends a `Parameter_Update.T` with `Operation => Update` via the modify connector, which calls `Process_Parameter_Update`. This sets `Ready_To_Update` but does NOT call `Update_Parameters_Action`.

To trigger `Update_Parameters_Action`, you must separately call `Update_Parameters` on the component instance. Since this is a non-overriding procedure on `Base_Instance` (not visible through the private type), add a tester helper:

```ada
-- In tester .ads (before end):
procedure Call_Update_Parameters (Self : in out Instance);

-- In tester .adb (before end):
procedure Call_Update_Parameters (Self : in out Instance) is
begin
   Self.Component_Instance.Update_Parameters;
end Call_Update_Parameters;
```

Then in the test body, after the 3-step protocol:
```ada
Stat := T.Stage_Parameter (T.Parameters.Threshold ((Value => 50)));
Stat := T.Validate_Parameters;
Stat := T.Update_Parameters;
T.Call_Update_Parameters;  -- Actually applies staged values
```ada

This pattern applies to ALL components with `parameters.yaml` and custom `Update_Parameters_Action`.

## Tester Helpers for Private State

When component fields are not reachable via commands or parameters, add setter procedures to the hand-written tester. The tester IS a child of `Component.X.Implementation`, so it can access private record fields:

```ada
-- In tester .ads (before end):
procedure Set_Pressure (Self : in out Instance; Value : in Short_Float);

-- In tester .adb (before end):
procedure Set_Pressure (Self : in out Instance; Value : in Short_Float) is
begin
   Self.Component_Instance.Pressure := Value;
end Set_Pressure;
```ada

Test file calls: `T.Set_Pressure (501.0);`

Use for: simulated sensor values, internal state flags, cooldown counters -- anything the component stores privately that must be set to exercise specific branches.

## Coverage

```bash
redo coverage    # From the component's test/ directory
```

Focus on `component-*-implementation.adb` in `build/coverage/coverage.txt`. Ignore generated files (`build/src/`, `test/build/`).

**Key coverage patterns:**
- **Invalid_Command** (requires `with Command;` in test body):
```ada
declare
   Cmd : Command.T := T.Commands.My_Command ((Field => 0));
begin
   Cmd.Header.Arg_Buffer_Length := 22;  -- corrupt length
   T.Command_T_Send (Cmd);
   -- Check command response shows Length_Error:
   Natural_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get_Count, 1);
   Command_Response_Status_Assert.Eq (
      T.Command_Response_T_Recv_Sync_History.Get (1).Status,
      Command_Enums.Command_Response_Status.Length_Error);
end;
```ada
- **Send_Dropped (sync):** `T.Connector_*_Recv_Sync_Status := Connector_Types.Message_Dropped;`
- **Untested branches:** Map `Missing` line numbers to source with `cat -n`

Full coverage workflow, reading reports, and common uncovered patterns: [coverage-guide.md](references/coverage-guide.md)

## References

- [references/setup-variants.md](references/setup-variants.md) -- Init/Set_Up patterns, Tear_Down, Tick construction
- [references/assertion-patterns.md](references/assertion-patterns.md) -- History API, packed type assertions, with-clause sets
- [references/command-test-patterns.md](references/command-test-patterns.md) -- Command dispatch, argument construction, helpers
- [references/parameter-test-patterns.md](references/parameter-test-patterns.md) -- Stage/validate/update flow, data dependency mocking
- [references/coverage-techniques.md](references/coverage-techniques.md) -- Full path coverage, error injection, anti-patterns
- [references/adamant-example-patterns.md](references/adamant-example-patterns.md) -- Advanced patterns from example project
- [references/common-errors-detail.md](references/common-errors-detail.md) -- Extended error documentation with solutions
- [references/testing-patterns-detail.md](references/testing-patterns-detail.md) -- Detailed testing pattern analysis
- [references/coverage-guide.md](references/coverage-guide.md) -- Coverage analysis setup and interpretation

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
- **Style**: [adamant-style](../adamant-style/SKILL.md) -- test code must pass `redo style`
- **Type system**: [adamant-type-system](../adamant-type-system/SKILL.md) -- packed type assertions and comparisons
