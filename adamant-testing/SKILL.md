---
name: adamant-testing
description: Comprehensive testing patterns and infrastructure for Adamant embedded software framework components. Use when writing unit tests, creating test harnesses, using the History API, testing commands/parameters/faults/data products, or debugging test failures.
---

# Adamant Testing Framework

Auto-generated reciprocal testers with history capture and white-box component access.

## ⚠️ Common Pitfalls (Read First)

1. **Send_Dropped histories are ALWAYS populated.** When `Connector_*_Recv_Sync_Status` is set to `Message_Dropped`, the tester's invokee handlers still push to history. Do NOT assert `History.Get_Count = 0` under Message_Dropped. The status only affects the invoker's return value.
2. **Tester Validate_Parameters returns `Parameter_Update_Status.E`** (values: `Success`, `Id_Error`, `Validation_Error`), NOT `Parameter_Validation_Status.E` (values: `Valid`, `Invalid`). The framework translates: your component's `Invalid` -> tester's `Validation_Error`.
3. **Unused Self in Validate_Parameters:** Use `pragma Unreferenced (Self);` -- do NOT copy Self (`Ignore : constant Instance := Self;`) as Instance is a limited type and copying violates Ravenscar.
4. **NEVER write tester files from scratch.** Run `redo templates` in both component/ and test/ dirs, then `cp build/template/*.ads build/template/*.adb .` in the test dir.

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

**⚠️ ALL redo commands for tests MUST run from inside the test/ directory.** Running from the project root uses the `Linux` target (no AUnit). The test `env.py` sets `TARGET=Linux_Test` which includes AUnit, but this only takes effect when redo is invoked from within test/.

```bash
# From the test/ directory (MANDATORY -- do NOT run from project root):
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

**⚠️ NEVER `cp build/template/*.adb .`** -- this overwrites your handwritten implementation body. Only copy specific files: tester `.ads/.adb`, test spec `.ads`, `test.adb`. Never glob-copy `.adb` files from templates after writing implementation.

## Test Body `with` Clauses

The test body (`*_tests-implementation.adb`) does NOT inherit visibility from the generated tester. You must explicitly `with` every package you use. Common pattern:

```ada
-- Required for most test bodies:
with Basic_Assertions; use Basic_Assertions;  -- Natural_Assert, Boolean_Assert
-- Only add `with Interfaces; use Interfaces;` if your test code directly uses
-- Unsigned_16, Unsigned_32, etc. Do NOT add it speculatively -- it causes
-- `-gnatwu` style warnings if unused. The generated tester and base class
-- already have Interfaces visibility for their own code.

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

-- NEVER with these directly (they are child instantiations, not standalone):
-- Natural_Assert              -> with Basic_Assertions; use Basic_Assertions;
-- Boolean_Assert              -> with Basic_Assertions; use Basic_Assertions;
-- Packed_U16_Assert           -> with Packed_U16.Assertion; use Packed_U16.Assertion;
-- Packed_U32_Assert           -> with Packed_U32.Assertion; use Packed_U32.Assertion;
-- Command_Response_Status_Assert -> with Command_Enums.Assertion; use Command_Enums.Assertion;
-- Command_Response_Status     -> use Command_Enums.Command_Response_Status
-- Command_Execution_Status    -> use Command_Enums.Command_Execution_Status
```ada

**Assertion methods**: `Eq`, `Neq`, `Lt`, `Le`, `Gt`, `Ge` -- all available on `Natural_Assert`, `Packed_U16_Assert`, etc. Use `Ge` for "at least N" checks (common for accumulated counts).

**Discarding status**: When a function returns a status you don't need, use `pragma Warnings (Off, "unused"); Ignore := Some_Function; pragma Warnings (On, "unused");` or the `Ignore renames` pattern.

**Package-level `use type`**: Can be placed at package body level (not just inside procedures) for operators needed across multiple test methods. Applies to ALL types whose operators you need -- framework types (e.g. `Command_Enums.Command_Response_Status.E`) AND custom preamble types from your own records (e.g. `My_Header.Version_Type`, `My_Header.Packet_Kind_Type`). Sub-byte enum/mod fields generate their own types in the record package.

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
- Component sends -> tester receives (captures in histories)
- Component receives -> tester sends (provides stimuli)
- White-box access via `T.Component_Instance`

**⚠️ History naming follows the TESTER's perspective (inverted from component):**
- Component has `Event_T_Send` -> tester history is `T.Event_T_Recv_Sync_History`
- Component has `Data_Product_T_Send` -> tester history is `T.Data_Product_T_Recv_Sync_History`
- Component has `Command_Response_T_Send` -> tester history is `T.Command_Response_T_Recv_Sync_History`
- Component has `Fault_T_Send` -> tester history is `T.Fault_T_Recv_Sync_History`
- Typed histories use event/DP/fault names: `T.My_Event_History`, `T.My_Data_Product_History`

**Sending stimuli to component (tester sends what component receives):**
- `T.Tick_T_Send(...)` -- sends tick TO component
- `T.Command_T_Send(...)` -- sends command TO component
- `T.Commands.My_Command(...)` -- constructs command with correct ID (ALWAYS use this)
- `T.Parameters.My_Param(...)` -- constructs parameter with correct ID
- **Named recv_async connectors**: For `name: Foo_T_Recv_Async` in component YAML, the tester send method is `T.Foo_T_Send()` (strips `_Recv_Async`, adds `_Send`). NOT `T.Foo_T_Recv_Async_Send()`.
- **Named recv_sync connectors**: Same pattern. For `name: Foo_T_Recv_Sync` in component YAML, the tester send method is `T.Foo_T_Send(Arg)` (strips `_Recv_Sync`, adds `_Send`). For unnamed typed connectors (e.g., `type: Interfaces.Unsigned_16`), the tester method is `T.Interfaces_Unsigned_16_Send(Arg)` -- NO `_T_` infix for raw Ada types. The `_T_` infix only appears for framework `.T` types (e.g., `Tick.T` -> `Tick_T_Send`).

**NEVER use `T.Command_T_Send_History`** -- that doesn't exist. The tester SENDS commands (no history for sends). It RECEIVES responses (history for receives).

**Set_Up DP history pollution**: If component overrides `Set_Up` and sends initial data products (e.g., zeroed counters), typed DP histories will have entries BEFORE any test stimuli. Clear typed histories before your assertion window, or account for the offset in `Get` indices.

**History buffer limits**: Default tester history buffers hold ~100 entries. Tests that send many ticks (e.g., 50+ in a loop) can overflow them, causing lost entries and wrong assertion indices. Keep tick counts per test under 50, or clear histories between test phases with `T.Event_T_Recv_Sync_History.Clear` etc.

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

**Order:** `Init_Base` → `Connect` → `Component_Instance.Init` → `Set_Up`. Init params go to `Component_Instance.Init`, NOT `Init_Base`. Both Init and Set_Up are optional -- only call them if YAML declares `init:` or component overrides Set_Up. **If the component YAML has NO `init:` section, do NOT call `Component_Instance.Init` or `Set_Up` -- they won't exist and won't compile.** For components without init, Set_Up_Test is just `Init_Base` + `Connect`. For per-test init params, defer Init/Set_Up to each test body (see [setup-variants.md](references/setup-variants.md) for deferred init patterns).

**Re-init mid-test (full):** To fully reset, call `Final_Base` then repeat: `Final_Base` → `Init_Base` → `Connect` → `Component_Instance.Init(new_params)` → `Set_Up`. This resets all histories and reconnects.

**Re-init mid-test (simple):** For passive components, you can often just call `T.Component_Instance.Init(new_params)` directly without the full teardown cycle. This changes init config without resetting histories. Used in real code (e.g., bot_station PID controller tests).

**⚠️ History Depth**: Generated `Init_Base` initializes all histories with `Depth => 100`. If a test sends more than 100 events/data products/commands, the history overflows and the test fails with "History is full." Solutions:
- **Increase depth in tester .adb Init_Base**: After copying templates from `build/template/`, edit the tester `.adb` file and change any `Depth => 100` to whatever you need (500, 1000, even 10000 -- there is no practical upper limit). The Init calls are in `Init_Base` in the `.adb`. Canonical example: `adamant_example/src/components/oscillator/test/component-oscillator-implementation-tester.adb` -- shows both raw connector histories and typed event histories with Depth parameters.
- Clear histories mid-test: `Self.Tester.Event_T_Recv_Sync_History.Clear;`
- Design tests to use fewer iterations (preferred -- keep tests small and focused)

## Sending Stimuli

```ada
T.Tick_T_Send ((Time => (0, 0), Count => 1));
T.Command_T_Send (T.Commands.My_Command ((Field => Value)));   -- with args
T.Command_T_Send (T.Commands.My_Noop_Command);                 -- no args

-- Parameters (3-step + processing trigger):
Status := T.Stage_Parameter (T.Parameters.Param_Name ((Value => 42.0)));
Parameter_Update_Status_Assert.Eq (Status, Parameter_Enums.Parameter_Update_Status.Success);
Status := T.Validate_Parameters;
Parameter_Update_Status_Assert.Eq (Status, Parameter_Enums.Parameter_Update_Status.Success);
Status := T.Update_Parameters;
Parameter_Update_Status_Assert.Eq (Status, Parameter_Enums.Parameter_Update_Status.Success);
-- Active: T.Tick_T_Send (The_Tick);  -- triggers Self.Update_Parameters in tick handler
-- Passive: T.My_Input_T_Send (Data);  -- triggers Self.Update_Parameters in recv handler
```

**ALWAYS use `T.Commands` / `T.Parameters`** -- never create local instances (wrong ID bases).
**ALWAYS read the generated tester .ads** (`build/template/component-*-tester.ads`) to discover
available helper functions. Do NOT guess the API -- `T.Stage_Parameter`, `T.Validate_Parameters`,
`T.Update_Parameters`, `T.Parameters.*`, typed history accessors, etc. are all defined there.
For custom packed types on connectors: construct unpacked (.U) then `Pack`: `T.Cmd_T_Send (My_Type.Pack (unpacked_val));`

## History Verification

**Dual-level capture:** raw connector history + individual typed histories.

```ada
-- Raw (all events/DPs/faults)
Natural_Assert.Eq (T.Event_T_Recv_Sync_History.Get_Count, 3);
-- Typed (specific event/DP/fault)
Natural_Assert.Eq (T.My_Event_History.Get_Count, 1);
-- Access (1-indexed) -- typed histories store PACKED type (.T), not unpacked (.U)
Packed_U32_Assert.Eq (T.Counter_History.Get (1), (Value => 42));
-- For custom packed record types, use the typed assert with a named aggregate:
-- My_Status_Assert.Eq (T.My_Status_History.Get (1), ((Field_1 => X, Field_2 => Y)));
-- No Pack/Unpack needed -- Ada resolves the .T type from context.
-- Clear between phases
T.Event_T_Recv_Sync_History.Clear;
```ada

**Named connectors:** `name: Spi_Data` on send → `Spi_Data_Reciprocal_History` in tester (NOT `_T_Recv_Sync_History`).

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

**⚠️ CRITICAL -- Variable-Length Types Must Be Initialized Before Queue Push**: Types with `variable_length:` fields (Packet.T, Command.T, etc.) MUST have their length field explicitly set before sending to an async queue. Ada does NOT zero-initialize record fields. An uninitialized `Buffer_Length` causes `Serialization_Failure` or `Too_Full` from the queue push, triggering `*_Send_Dropped`.
```ada
-- WRONG: Buffer_Length is uninitialized garbage
Pkt : Packet.T;
Pkt.Header.Sequence_Count := 42;
T.Packet_T_Send (Pkt);  -- FAILS: queue push error

-- CORRECT: Always set Buffer_Length (and other header fields)
Pkt : Packet.T;
Pkt.Header.Time := (0, 0);
Pkt.Header.Id := 0;
Pkt.Header.Sequence_Count := 42;
Pkt.Header.Buffer_Length := 0;  -- REQUIRED for queue serialization
T.Packet_T_Send (Pkt);  -- Works
```

## Arrayed Connector Testing

When a component has arrayed connectors (`count: N` in YAML):
- **Tester send (arrayed recv_async)**: `T.Packed_F32_T_Send (Index, Arg)` -- pass index as first arg
- **Tester send (arrayed recv_sync)**: Same pattern -- `T.Packed_F32_T_Send (Index, Arg)` (tester sends to component's recv_sync)
- **Index type visibility**: Import `Component.<Name>_Reciprocal` in test body for the tester's index type: `with Component.<Name>_Reciprocal; use Component.<Name>_Reciprocal;`
- **Connector_Count_Type arithmetic**: If using arithmetic on indices, add `with Connector_Types; use type Connector_Types.Connector_Count_Type;`
- **Dispatch_All does NOT invoke Cycle**: For active components, `Dispatch_All` only dispatches queued async messages. If periodic logic is in `Cycle`, it is not exercised by `Dispatch_All`. Prefer adding a `Tick.T recv_sync` connector for testable periodic computation.

## Command Response Verification

**⚠️ Dispatch_All is ONLY for recv_async connectors.** Commands on `recv_sync` connectors execute immediately when `T.Command_T_Send` is called -- do NOT call `Dispatch_All` for them (it will return 0). Only call `Dispatch_All` after sending to `recv_async` connectors (e.g., `Packet_T_Send` for async packet input). Check the component YAML to determine which connectors are sync vs async.

```ada
-- Command test pattern (commands are recv_sync -- execute immediately):
T.Command_T_Send (cmd);
-- Response is available immediately -- no Dispatch_All needed:
```

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

1. **Packed type assertions:** `Packed_U32_Assert.Eq(...)`, `My_Record_Assert.Eq(...)`, `My_Array_Assert.Eq(...)` -- type-safe, clear errors, works for framework and custom packed types
2. **Basic_Assertions:** `Natural_Assert.Eq(...)`, `Boolean_Assert.Eq(...)`, `Integer_Assert.Eq(...)` -- counts, flags, indices (see `adamant/src/util/basic_assertions/basic_assertions.ads` for full list)
3. **Enum assertion packages:** `Parameter_Update_Status_Assert.Eq(...)`, `Command_Response_Status_Assert.Eq(...)` -- from `*.Assertion` child packages

**NEVER use `pragma Assert` or AUnit `Assert(condition, "message")` in tests.** Smart_Assert-based assertions (items 1-3) print both expected and actual values on failure. `pragma Assert` and `Assert()` only say "failed" with no context, making debugging painful. Every assertion can be replaced with a typed Smart_Assert call -- use packed type assertions for record/array comparisons, `Basic_Assertions` for scalar values, and enum assertion packages for enum comparisons.

**NEVER use `E'Pos` or `T'Pos` to compare enum values.** The `Natural_Assert.Eq(E'Pos(Status), E'Pos(Expected))` pattern loses type safety and produces confusing failure output (positional integers instead of enum names). Always use the typed enum assertion package directly: `Parameter_Update_Status_Assert.Eq(Status, Parameter_Enums.Parameter_Update_Status.Success)`. For any enum type `Foo.E`, the assertion package is `with Foo.Assertion; use Foo.Assertion;` which provides `Foo_Assert.Eq`.

Do NOT call `Smart_Assert.Eq(...)` directly -- requires generic instantiation first. Use the pre-instantiated packages from `Basic_Assertions`, `*.Assertion` child packages, or instantiate your own for project-specific types.

```ada
with Basic_Assertions; use Basic_Assertions;
with Packed_U32.Assertion; use Packed_U32.Assertion;
with Command_Enums; use type Command_Enums.Command_Response_Status.E;
with Command_Enums.Assertion; use Command_Enums.Assertion;  -- Command_Response_Status_Assert
with Parameter_Enums;
with Parameter_Enums.Assertion; use Parameter_Enums.Assertion;  -- Parameter_Update_Status_Assert, Parameter_Validation_Status_Assert
with Data_Product_Enums; use Data_Product_Enums.Data_Dependency_Status;  -- for data dep tests
```

**Parameter status assertions:** Use `Parameter_Update_Status_Assert.Eq(Status, Parameter_Enums.Parameter_Update_Status.Success)` instead of `pragma Assert`. The `.Assertion` child package provides Smart_Assert instantiations for all enum types in that package.

**Custom enum data product assertions:** For enum types defined in project `types/`, auto-generated assertion packages follow the same pattern: `with My_Enum.Assertion; use My_Enum.Assertion;` gives `My_Enum_Assert.Eq(...)`. Use for DP history checks on enum-typed data products (e.g. mode state, operational status).

**Packed record and array data product assertions:** For custom packed types (`*.record.yaml` or `*.array.yaml`), use the auto-generated assertion package to compare the full value from the typed DP history. Construct the expected value as an aggregate -- no `Pack` or `Unpack` needed, Ada resolves the `.T` type from context:
```ada
with My_Status.Assertion; use My_Status.Assertion;
-- Packed record: compare with named aggregate
My_Status_Assert.Eq (T.My_Status_Product_History.Get (1), ((
   Field_1 => Value_1,
   Field_2 => Enum_Literal,
   Field_3 => Other_Value
)));
-- Packed array: compare with positional aggregate
My_Array_Assert.Eq (T.My_Array_Product_History.Get (1), [Val_0, Val_1, Val_2]);
-- WRONG: Do not unpack and check individual fields/elements with naked Assert:
-- Status := My_Status.Unpack (T.My_Status_Product_History.Get (1));
-- Assert (Status.Field_1 = Value_1, "msg");  -- loses typed error output
```

**Array type assertions:** Array types generate assertion packages with `_U_Assert` / `_Assert` / `_Le_Assert` suffixes (NOT `_Assert_Eq`). Usage: `with My_Array.Assertion; use My_Array.Assertion;` gives `My_Array_U_Assert.Eq(...)` for unpacked, `My_Array_Assert.Eq(...)` for packed `.T`.

## Data Dependency Testing

### Setting Mock Values and Ticking

The tester generates named fields for each data dependency. Set them directly:
```ada
-- Use non-zero timestamps when testing data dependency STALENESS.
-- (0,0) is fine for non-staleness tests (commands, events, basic DPs).
Test_Time : constant Sys_Time.T := (100, 0);
The_Tick : constant Tick.T := (Time => Test_Time, Count => 0);

-- In Set_Up_Test:
T.System_Time := Test_Time;
T.Data_Dependency_Timestamp_Override := Test_Time;

-- Set mock values (field names match data_dependencies.yaml names)
T.Sensor_Value := (Value => 50.0);
T.Tick_T_Send (The_Tick);
-- Component calls Self.Get_Sensor_Value(...) which reads T.Sensor_Value
```

Source: threshold_monitor. Field names (Sensor_Value, Setpoint, etc.) match the names in `data_dependencies.yaml`. The tester auto-generates these fields.

### Multiple Data Dependencies

```ada
T.Setpoint := (Value => 10.0);          -- Packed_F32.T
T.Process_Value := (Value => 7.0);      -- Packed_F32.T
T.Tick_T_Send (The_Tick);
-- error = 10.0 - 7.0 = 3.0, output = Kp * 3.0 = 3.0
Packed_F32_Assert.Eq (T.Output_History.Get (1), (Value => 3.0));
```

Source: pid_controller. Set all dependency fields before ticking.

### Simulating Fetch Failure

```ada
T.Data_Dependency_Return_Status_Override := Data_Product_Enums.Fetch_Status.Id_Out_Of_Range;
T.Tick_T_Send (The_Tick);
-- Component's error path fires a fault, no DPs sent
Natural_Assert.Eq (T.Sensor_Failure_History.Get_Count, 1);
Natural_Assert.Eq (T.Data_Product_T_Recv_Sync_History.Get_Count, 0);
```

Source: threshold_monitor. Override the return status to test the component's error handling for missing/failed data dependencies.

### Simulating Stale Data

```ada
T.Data_Dependency_Timestamp_Override := (50, 0);  -- Old timestamp
T.Tick_T_Send ((Time => (100, 0), Count => 0));   -- Current time is newer
```

The framework detects that the data product timestamp is older than expected and reports staleness to the component.

**`Data_Dependency_Timestamp_Override` is GLOBAL** -- it applies the same timestamp to ALL data dependency fetches. You cannot selectively make one dep stale while keeping another fresh via this field alone. To test per-dependency staleness, set individual mock values with different staleness characteristics and rely on the component's internal logic to differentiate, or test each dependency in isolation.

**Implementation needs:** `with Data_Product_Enums; use Data_Product_Enums; use Data_Product_Enums.Data_Dependency_Status;` in the component body for status checks.

**Side-effect events from Invalid_Data_Dependency:** When a `Get_*` call returns a non-Success status, the framework automatically calls the component's `Invalid_Data_Dependency` override DURING the Get call (before control returns to the caller). If that override sends events, those events appear in the history BEFORE any events the caller sends afterward. Account for these extra events in assertion counts -- e.g., if testing staleness and the override sends a Sensor_Stale event, that event fires inside Get, not after it.

## Test Body With-Clauses

Add `with` for every type referenced in tests: `Basic_Assertions`, `Packed_F32.Assertion`, `Command_Enums`, `Interfaces`, custom types from `src/types/`. Only `with` what you use -- `redo style` flags unused imports.

## Common Errors

Top errors that waste time:

0. **Speculative assertions:** Only assert on behavior you can verify from the YAML model + implementation. If you don't know whether a tick sends an event, don't assert on event counts. Write minimal, correct tests first -- you can always add assertions after observing actual behavior.
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

**⚠️ CRITICAL -- Tester histories are ALWAYS populated:** When `Message_Dropped` status is set, the tester's invokee handlers (`Event_T_Recv_Sync`, `Data_Product_T_Recv_Sync`, etc.) are still called and push to history. The `Message_Dropped` status only affects what the **invoker** (component under test) sees as a return value, which triggers the `*_Send_Dropped` handler. Do NOT assert `History.Get_Count = 0` -- the tester receives the data regardless of the status value.

### Sync sends (most common)

```ada
-- Set tester connector status to trigger Send_Dropped:
T.Connector_Event_T_Recv_Sync_Status := Connector_Types.Message_Dropped;
T.Connector_Data_Product_T_Recv_Sync_Status := Connector_Types.Message_Dropped;
T.Packed_F32_T_Send ((Value => 80.0));  -- Triggers component sends
-- Tester histories ARE populated (invokee always receives):
Natural_Assert.Eq (T.Event_T_Recv_Sync_History.Get_Count, 1);  -- NOT 0
-- The test verifies the *_Send_Dropped handler (null) doesn't crash.
-- Restore:
T.Connector_Event_T_Recv_Sync_Status := Connector_Types.Success;
T.Connector_Data_Product_T_Recv_Sync_Status := Connector_Types.Success;
```

Field names: `Connector_<Type>_Recv_Sync_Status` in generated reciprocal `.ads`.

### Async sends

Use `Expect_*_Dropped` tester flag (hand-edit tester). See framework `command_router` tests.

### Array Event.T connector tester crash

⚠️ When a component forwards Event.T through an array send connector (e.g., `count: 4`) AND has a separate Event.T send for component-generated events, the generated tester's `Event_T_Recv_Sync` handler calls `Dispatch_Event` on ALL received events. Forwarded events have IDs that don't match local event IDs, causing CONSTRAINT_ERROR (range check failure). **Fix:** After copying tester template, remove `Self.Dispatch_Event(Arg)` from the `Event_T_Recv_Sync` handler that receives forwarded (non-local) events.

## Parameter Testing

### Full Stage-Validate-Update Cycle

The complete parameter update flow requires three steps plus a tick:

```ada
Status := T.Stage_Parameter (T.Parameters.Output_Limit ((Value => 5.0)));
Parameter_Update_Status_Assert.Eq (Status, Parameter_Enums.Parameter_Update_Status.Success);
Status := T.Validate_Parameters;
Parameter_Update_Status_Assert.Eq (Status, Parameter_Enums.Parameter_Update_Status.Success);
Status := T.Update_Parameters;
Parameter_Update_Status_Assert.Eq (Status, Parameter_Enums.Parameter_Update_Status.Success);
T.Tick_T_Send (The_Tick);  -- New parameter values take effect
```

Declare Status as `Parameter_Enums.Parameter_Update_Status.E`. Requires:
```ada
with Parameter_Enums;
with Parameter_Enums.Assertion; use Parameter_Enums.Assertion;
```

### Validation Rejection Testing

```ada
Status := T.Stage_Parameter (T.Parameters.Warning_Threshold ((Value => 95.0)));
Parameter_Update_Status_Assert.Eq (Status, Parameter_Enums.Parameter_Update_Status.Success);
Status := T.Validate_Parameters;
Parameter_Update_Status_Assert.Eq (Status, Parameter_Enums.Parameter_Update_Status.Validation_Error);
```

Source: threshold_monitor. Stage succeeds (just buffers), but Validate rejects because the component's Validate_Parameters override checks cross-parameter constraints (warning >= critical is invalid).

### Parameter Takes Effect on Next Processing Call

After Update_Parameters succeeds, the component reads new values in its next processing
handler. For **active/ticked** components, send a tick. For **passive** components (no tick --
only recv_sync handlers), send the next data input instead:

```ada
-- Active component: tick applies parameters
Status := T.Update_Parameters;
T.Tick_T_Send (The_Tick);
Packed_F32_Assert.Eq (T.Output_History.Get (1), (Value => 5.0));

-- Passive component: next recv_sync input applies parameters
Status := T.Update_Parameters;
T.My_Input_T_Send (Next_Input);  -- component calls Self.Update_Parameters internally
-- Now assert new behavior with updated parameters
```

### Update_Parameters_Action Coverage

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
```

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

**Load selectively.** The main SKILL.md covers most testing patterns. Only load references when you need them.

| Reference | When to load |
|-----------|-------------|
| [references/setup-variants.md](references/setup-variants.md) | Components with init parameters, custom Set_Up, or Tear_Down. **Skip for simple components** with no init. |
| [references/assertion-patterns.md](references/assertion-patterns.md) | Complex assertion chains, packed type field comparisons, or when tests need extended History API patterns. **Skip for basic tests** (count + simple value checks). |
| [references/command-test-patterns.md](references/command-test-patterns.md) | Only when testing components with commands. **Skip for passive components without commands.** |
| [references/adamant-example-patterns.md](references/adamant-example-patterns.md) | Only for task-based testing, memory regions, or advanced packet construction. Rarely needed. |
| [references/coverage-guide.md](references/coverage-guide.md) | Only when measuring or improving test coverage (`redo coverage`). |

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
- **Style**: [adamant-style](../adamant-style/SKILL.md) -- test code must pass `redo style`
- **Type system**: [adamant-type-system](../adamant-type-system/SKILL.md) -- packed type assertions and comparisons
