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

```bash
redo templates                              # Generate tester stubs
cp build/template/component-*-tester.ads build/template/component-*-tester.adb .
cp build/template/*_tests-implementation.ads .   # ONLY spec, NOT .adb (overwrites tests!)
cp build/template/test.adb .
redo test                                   # Build and run
redo coverage                                # Coverage analysis via gcov
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

**Order:** `Init_Base` → `Connect` → `Component_Instance.Init` → `Set_Up`. Init params go to `Component_Instance.Init`, NOT `Init_Base`. Both Init and Set_Up are optional -- only call them if YAML declares `init:` or component overrides Set_Up. For per-test init params, defer Init/Set_Up to each test body (see [test-corpus.md](references/test-corpus.md) pattern 1h).

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
4. **Typed histories don't auto-clear** when raw history is cleared -- most common mistake
5. **History depth is 100** -- clear mid-test to avoid overflow (each tick sending 2 DPs = 2 slots)
6. **`Dispatch_All` is a FUNCTION** returning Natural -- must capture: `Count := T.Dispatch_All;`
7. **Copy tester files from `build/template/`**, never hand-write them
8. **`*_tests-implementation.ads` MUST come from template** (has correct base class)
9. **History naming:** `{entity_name}_History` (not `_Event_History` or `_Data_Product_History`)
10. **No `Packed_U8`** -- use `Packed_Byte.T`
11. **Tick.T.Count is Unsigned_32** -- use `Interfaces.Unsigned_32(I)` for loop casts
12. **Change detection initial state:** First tick fires extra DP because shadow differs from computed value
13. **Packet.T structure**: `(Header => (Time => ..., Id => ..., Sequence_Count => ..., Buffer_Length => N), Buffer => [others => 0])`. The payload field is `Buffer`, NOT `Data`. Header has NO Priority field
14. **Named Event.T send connectors crash** on non-component event IDs. When a component has multiple Event.T send connectors (e.g., `Filtered_Event_T_Send` for forwarding), the generated tester calls `Self.Dispatch_Event(Arg)` on ALL Event.T receive handlers. Forwarded events with arbitrary IDs cause `CONSTRAINT_ERROR: range check failed` in `Dispatch_Event` because the ID doesn't map to a local event enum. **Fix:** Edit the tester .adb to remove the `Dispatch_Event` call from the non-component Event.T handler, keeping only the history push.
15. **Instance record names like `Queue` conflict** with generated base class -- use prefixed names
16. **Unused `Status` variable** in parameter tests -- use `pragma Unreferenced (Status);` or check it
17. **Test spec `with Tester`** and **`unnecessary with of ancestor`** warnings -- these ARE fixable. Move `with Component.X.Implementation.Tester;` from test spec to body. Remove ancestor `with` in child packages (child auto-sees parent). These files are hand-written (copied from `build/template/`), NOT regenerated by `redo templates` after initial creation.
18. **Use `[]` for array aggregates** -- `[others => 0]` not `(others => 0)`. Record aggregates stay `()`
19. **`use Command_Execution_Status.E;`** is useless -- the `use type` in generated code already provides operator visibility
20. **`Dispatch_All` result must be captured or discarded** -- if you don't check the count, call bare `T.Dispatch_All;` without `Count :=`
21. **`then` on its own line** for multi-line if/elsif conditions (Ada style `-gnatyi`)

22. **`AUnit.Assertions` removal caution:** GNAT reports "no entities referenced" even when bare `Assert(...)` is called via `use` clause. Only remove if ALL assertions use qualified names (`Natural_Assert.Eq`, `Packed_U32_Assert.Eq`). Grep for bare `Assert (` before removing.
23. **`Dispatch_All` only exists on active component testers** -- passive components process synchronously, no queue, no `Dispatch_All`. Calling it on a passive tester is a compile error.
24. **Removing `with` clauses:** `use X;` makes operators and subprograms directly visible -- removing `with X;` breaks those even if GNAT says the `with` is unused. Grep body for types/operators from the package before removing.
25. **Declare-but-never-assign pattern:** `Count : Natural;` then `Natural_Assert.Eq (Count, N)` is a real bug -- `Count` is uninitialized. Use history/DP queries: `T.Event_T_Recv_Sync_History.Get_Count`
26. **Missing test bodies:** If test spec declares `overriding procedure Test_Foo` but body is empty, GNAT emits "missing body" error. Every declared test procedure needs a body, even if minimal.
27. **Stale ALI files hide tester changes:** If you update a tester .ads file (e.g., add Dispatch_All) and get "no selector" errors even when the source looks correct, run `redo clean` in the test dir before recompiling. Do NOT manually `rm -rf build` -- use redo's own clean commands (`redo clean` or `redo clean_all`).
28. **Tester connector names:** To send TO the component, use `T.Packet_T_Send(...)` (tester sends), NOT `T.Packet_T_Recv_Sync(...)` (that's the component's receive handler name).
29. **Command names come from YAML:** Always check `*.commands.yaml` for exact names. `Reset_Counts` vs `Reset_Count` matters. Use `T.Commands.<Exact_Name>`.
30. **Redundant `with Parent;` before child spec:** `with Foo_Tests;` before `package Foo_Tests.Implementation is` triggers "unnecessary with of ancestor" -- the child already sees the parent.
31. **Dispatch_All returns Natural:** `Dispatch_All` is a function, not a procedure. Ada does not allow discarding function return values. Use `Natural_Assert.Eq(T.Dispatch_All, N)` (framework pattern) or `Ignore := T.Dispatch_All; pragma Unreferenced (Ignore);` with `Ignore : Natural;` declared locally.

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

When tests need different init params, defer Init/Set_Up to each test body:
```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   -- NO Init or Set_Up here
end Set_Up_Test;

overriding procedure Test_With_4_Channels (Self : in out Instance) is
   T : ... renames Self.Tester;
begin
   T.Component_Instance.Init (Max_Channels => 4);
   T.Component_Instance.Set_Up;
   -- test body
end Test_With_4_Channels;
```

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

## Send_Dropped Handlers and Coverage

Every send connector generates a `*_Send_Dropped` handler that the component must override. These fire when `Send` returns `Message_Dropped` status -- NOT when a connector is unattached.

### How Send_Dropped Actually Works

The generated base class has this pattern:
```ada
procedure Sample_T_Send (Self : in out Base_Instance; Arg : in Packed_F32.T; ...) is
   Ret : Connector_Status;
begin
   Ret := Sample_T_Send_Connector.Call (Self.Connector_Sample_T_Send, Arg, ...);
   case Ret is
      when Success => null;
      when Message_Dropped => Sample_T_Send_Dropped (Base_Instance'Class (Self), Arg);
   end case;
end Sample_T_Send;

procedure Sample_T_Send_If_Connected (...) is
begin
   if Self.Is_Sample_T_Send_Connected then
      Self.Sample_T_Send (Arg, ...);    -- Only calls Send if connected
   end if;
end Sample_T_Send_If_Connected;
```

Key points:
- `Send_If_Connected` skips entirely when not connected -- does NOT call `Send_Dropped`
- `Send_Dropped` only fires when the connector IS attached but the receiver rejects (queue full)
- **Sync connectors always return `Success`** -- `Message_Dropped` never fires for sync sends
- Only **async connectors** can return `Message_Dropped` (queue overflow)

### Coverage Implications

- **`is null;` in spec:** Zero coverage impact. gcov doesn't count these.
- **`begin null; end` in body:** gcov counts these as uncovered lines, but they are **uncoverable for sync connectors**. Add a TODO comment acknowledging the gap:
  ```ada
  -- TODO: Send_Dropped handlers (impl lines N-M) are uncoverable.
  -- Sync connectors always return Success, so Message_Dropped never fires.
  ```
- **Active components with async recv:** Can overflow the tester's queue to trigger Recv_Async_Dropped, but that's a different handler (on the tester, not the component).

### Testing Send_Dropped on Async Send Connectors

For components that SEND to async connectors (rare -- most send to sync), use the tester's `Expect_*_Dropped` mechanism. This requires hand-editing the tester spec/body to add a boolean flag. See `command_router` tests in the framework for the pattern:

```ada
-- In tester .ads (hand-written):
Expect_Command_T_Send_Dropped : Boolean := False;
Command_T_Send_Dropped_Count : Natural := 0;

-- In test body:
T.Expect_Command_T_Send_Dropped := True;
-- ... trigger component to send ...
Natural_Assert.Eq (T.Command_T_Send_Dropped_Count, 1);
```

## Coverage

See [references/coverage-guide.md](references/coverage-guide.md) for full guide.

```bash
# From the component's test/ directory:
redo coverage
```

### Reading coverage.txt

Coverage output is at `build/coverage/coverage.txt`. It lists ALL compiled files with line counts and missing line numbers. Example:

```
File                                       Lines     Exec  Cover   Missing
------------------------------------------------------------------------------
component-heater_controller-implementation.adb
                                              73       71    97%   119-120
component-heater_controller-implementation.ads
                                               6        3    50%   60-62
build/src/component-heater_controller.adb
                                             162      116    71%   32,34-35,...
```

**Focus on these two files only** (YOUR handwritten code):
- `component-*-implementation.adb` -- the implementation body (main coverage target)
- `component-*-implementation.ads` -- the implementation spec

**Ignore everything else** in the report:
- `build/src/component-*.adb` -- generated base class (framework code)
- `build/src/*_commands.adb`, `*_events.adb`, `*_data_products.adb` -- generated suites
- `test/build/src/*_reciprocal.*` -- generated tester
- `test/build/obj/*/b__test.adb` -- binder generated
- `test/component-*-tester.*` -- tester template
- `test/*_tests-implementation.*` -- your test code (100% expected)

### Using Missing Lines to Guide Tests

The `Missing` column shows exact line numbers. Map them to source:

```bash
cat -n component-*-implementation.adb    # From the component directory (NOT test/)
```

Cross-reference missing lines with the source to identify the uncovered pattern:
- **Untested case branch** (e.g., lines 119-120 = `when Forced_On =>`) -- add test exercising that mode
- **Untested if/elsif/else** -- add test with input triggering the uncovered branch
- **`is null` Send_Dropped in .ads** (e.g., lines 60-62) -- these are `is null;` declarations that gcov counts as lines but have no executable code. **Ignore these** -- they cannot be "covered" and do not affect implementation coverage

### Project-Level Coverage Script

`tools/impl_coverage.sh` filters coverage.txt to show only implementation .adb files. Run from project root:

```bash
bash tools/impl_coverage.sh                    # All components
bash tools/impl_coverage.sh component_name     # Specific component
```

**No structural ceiling.** All executable paths are coverable with proper testing:
- **Invalid_Command:** Corrupt `Cmd.Header.Arg_Buffer_Length := 22;` on a valid command
- **Send_Dropped (async sends):** Use `Expect_*_Dropped` tester flag (see Send_Dropped section above)
- **Recv_Async_Dropped:** Overflow queue (small `Init_Base Queue_Size`, send N+1)

| Component Type | Target |
|---|---|
| Simple passive (no commands) | 95-100% |
| Passive with commands | 90-100% |
| Active (async recv) | 90-100% |
| Active with commands | 85-100% |

### Coverage Improvement Workflow

1. Run `redo coverage` (from test/ dir)
2. Read `build/coverage/coverage.txt`
3. Find `component-*-implementation.adb` entry, note missing lines
4. Map missing lines to source: `cat -n component-*-implementation.adb` (from component dir)
5. Identify pattern: untested branch, unexercised connector, data dependency path
6. Add test to `tests.yaml` -> `redo templates` -> copy ONLY the `*_tests-implementation.ads` -> implement in `.adb` -> `redo coverage`

### Common Uncovered Patterns

- **Untested case/if branch:** Add test with input triggering the uncovered branch
- **Untested connector handler:** Add test that sends via that connector
- **Active async path at 0%:** Must send AND `Dispatch_All` -- just sending queues without processing
- **Data dependency path at 0%:** Override tester's `*_T_Service` to return success with test data
- **`is null` in .ads at <100%:** Ignore -- gcov artifacts, not executable code

## References

- [references/test-corpus.md](references/test-corpus.md) -- All test patterns with real code examples
- [references/adamant-example-patterns.md](references/adamant-example-patterns.md) -- Advanced patterns from adamant_example project
- [references/common-errors-detail.md](references/common-errors-detail.md) -- Extended error documentation with solutions
- [references/testing-patterns-detail.md](references/testing-patterns-detail.md) -- Detailed testing pattern analysis
- [references/coverage-guide.md](references/coverage-guide.md) -- Coverage analysis setup and interpretation

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
