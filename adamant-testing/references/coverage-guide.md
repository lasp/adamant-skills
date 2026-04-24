<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Adamant Test Coverage Guide

Systematic approach to measuring and improving component implementation coverage using `admt coverage` and gcovr.

## Running Coverage

```bash
# From component test/ directory:
cd src/components/component_name/test
admt coverage

# Output:
# build/coverage/coverage.txt   (text report)
# build/coverage/test.html/     (HTML report)
```

Coverage compiles with `-fprofile-arcs -ftest-coverage`, runs the test binary, then generates gcovr report. Test failures still produce valid coverage data.

## Reading Coverage Reports

The `build/coverage/coverage.txt` file lists ALL source files compiled into the test binary with line counts and missing line numbers. Example:

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

**Focus on these two files** (your handwritten code):
- `component-*-implementation.adb` -- the implementation body (primary coverage target)
- `component-*-implementation.ads` -- the implementation spec

**The `Missing` column is the key output.** It tells you exactly which lines are uncovered. Map them to source with `cat -n component-*-implementation.adb` (from the component dir, not test/).

**`is null` handlers in .ads inflate the miss count.** Lines like `overriding procedure Event_T_Send_Dropped (...) is null;` get counted by gcov but have no executable code. A spec showing 50% due to `is null` declarations is actually fine -- there is nothing to test.

**Ignore everything else** in the report (framework/generated code):
- `build/src/component-*.adb` -- generated base class
- `build/src/*_commands.adb`, `*_events.adb`, `*_data_products.adb` -- generated suites
- `test/build/src/*_reciprocal.*` -- generated tester
- `test/build/obj/*/b__test.adb` -- binder generated
- `test/component-*-tester.*` -- tester template

### gcovr Line Wrapping

gcovr wraps long filenames to two lines:
```
component-component_name-implementation.adb
                                              23       23   100%
```
The numbers (lines, exec, coverage%) are on the NEXT line. Any coverage parsing scripts must handle this.

## Filtering to Implementation Coverage

Use `impl_coverage.sh` (at `tools/impl_coverage.sh` in the project) to extract only the implementation .adb coverage:

```bash
bash tools/impl_coverage.sh                    # All components
bash tools/impl_coverage.sh component_name     # Specific component
```

Output format:
```
COMPONENT                            LINES   EXEC   COV%  MISSING
attitude_controller                     23     23   100%
event_dispatcher                        57     36    63%  42,49-50,...
```

## Coverage Patterns for Full Path Coverage

These patterns require tester modifications but are fully coverable (no structural ceiling):

### Send_Dropped Handlers

Send_Dropped fires when `Send` returns `Message_Dropped` -- NOT when a connector is unattached. `Send_If_Connected` skips entirely when not connected (does not call `Send_Dropped`).

**Testing Send_Dropped on sync connectors:** The generated reciprocal tester has `Connector_*_Recv_Sync_Status` fields (default `Success`). Set to `Connector_Types.Message_Dropped` before triggering sends to cover Send_Dropped handlers:
```ada
T.Connector_Event_T_Recv_Sync_Status := Connector_Types.Message_Dropped;
T.Tick_T_Send ((Time => (0, 0), Count => 1));  -- Triggers Send_Dropped
T.Connector_Event_T_Recv_Sync_Status := Connector_Types.Success;  -- Restore
```

**Testing Send_Dropped on async connectors:** Use `Expect_*_Dropped` flags on the hand-written tester (see `command_router` tests in framework).

**`is null;` vs `begin null; end`:** Handlers declared `is null;` in the spec have zero gcov lines. Handlers with `begin null; end` in the body show as uncovered but ARE coverable using the `Connector_*_Status` pattern above.

### Invalid_Command Handler
```ada
overriding procedure Invalid_Command (Self : in out Instance; Cmd : in Command.T;
   Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type) is
begin
   null;  -- Framework calls this for malformed commands
end Invalid_Command;
```
Triggered when `Execute_Command` detects argument deserialization failure. To cover:

```ada
-- Create valid command then corrupt it:
Cmd : Command.T := T.Commands.My_Command ((Value => 42));
Cmd.Header.Arg_Buffer_Length := 22;  -- Wrong length triggers Invalid_Command
T.Command_T_Send (Cmd);
-- Framework calls Invalid_Command, then sends Length_Error response
Natural_Assert.Eq (T.Invalid_Command_Received_History.Get_Count, 1);
```

For commands with custom record/enum arg types, use `(others => <>)` as a safe default aggregate -- the arg value doesn't matter since we're corrupting the length:
```ada
Cmd : Command.T := T.Commands.Set_Route ((others => <>));
Cmd.Header.Arg_Buffer_Length := 22;
```

The framework's `parameter_manager` tests demonstrate this pattern.

### Recv_Async_Dropped Handler
```ada
overriding procedure Packet_T_Recv_Async_Dropped (Self : in out Instance; Arg : in Packet.T) is
begin
   null;  -- Queue overflow already handled by framework
end Packet_T_Recv_Async_Dropped;
```
To cover, overflow the async queue. From `parameter_manager` Test_Full_Queue:
```ada
-- Init with small queue (3 commands fit):
T.Init_Base (Queue_Size => T.Component_Instance.Get_Max_Queue_Element_Size * 3);
-- Fill queue:
T.Command_T_Send (Cmd);
T.Command_T_Send (Cmd);
T.Command_T_Send (Cmd);
-- Overflow triggers Recv_Async_Dropped:
T.Expect_Command_T_Send_Dropped := True;
T.Command_T_Send (Cmd);
Natural_Assert.Eq (T.Command_Dropped_History.Get_Count, 1);
```

### Coverage Target by Component Type

All paths are coverable with proper testing techniques:

| Component Type | Target | Technique for Full Coverage |
|---|---|---|
| Simple passive (no commands) | 95-100% | Set Connector_*_Recv_Sync_Status for Send_Dropped |
| Passive with commands | 90-100% | + Corrupt command for Invalid_Command |
| Active (async recv) | 90-100% | + Recv_Async_Dropped (structurally hard -- tester raises on queue full) |
| Active with commands | 85-100% | All techniques combined |

**Send_Dropped testing:** Use `T.Connector_*_Recv_Sync_Status := Connector_Types.Message_Dropped` (NOT re-init without Connect -- `Send_If_Connected` returns early when disconnected, so Send_Dropped never fires).

**Recv_Async_Dropped:** Structurally difficult -- the tester raises an exception when the component's async queue is full, before the Dropped handler fires. No framework tests cover this pattern. Accept these lines as uncoverable or document with TODO comments.

## Common Uncovered Patterns and Fixes

### 1. Untested Connector Handlers
**Symptom:** Entire procedure at 0% (e.g., `Command_T_Recv_Sync` never called).
**Fix:** Add test that sends via that connector:
```ada
T.Command_T_Send (T.Commands.My_Command ((Value => 42)));
```

### 2. Untested Branches (if/elsif/else)
**Symptom:** Lines inside one branch at 0%, others covered.
**Fix:** Add test with input that triggers the uncovered branch:
```ada
-- Cover the "else" branch (threshold not exceeded)
T.Sensor_Reading_T_Send (Reading_Below_Threshold);
T.Tick_T_Send ((Time => (0, 0), Count => 1));
```

### 3. Active Component Async Path Not Covered
**Symptom:** `*_Recv_Async` procedure body at 0% even though tests exist.
**Fix:** Must send to async queue AND dispatch:
```ada
T.Packet_T_Send (My_Packet);   -- Puts in async queue
Count := T.Dispatch_All;        -- Processes queue
Natural_Assert.Eq (Count, 1);   -- Verify dispatched
```

### 4. Data Dependency Path Not Covered
**Symptom:** Code after `Self.Get_*` call at 0%.
**Fix:** Override tester's `*_T_Service` to return success with test data:
```ada
-- In tester .adb, override the service function:
overriding function Sensor_Data_T_Service (Self : in out Instance) return Sensor_Data_Return.T is
   To_Return : Sensor_Data_Return.T;
begin
   To_Return.The_Status := Data_Product_Enums.Fetch_Status.Success;
   To_Return.The_Value := Sensor_Data.Pack ((X => 1.0, Y => 2.0, Z => 3.0));
   return To_Return;
end Sensor_Data_T_Service;
```

### 5. Named Event.T Send Connector Crash
**Symptom:** Test crashes with CONSTRAINT_ERROR in Dispatch_Event when component forwards events through named Event.T send connectors.
**Fix:** Edit the tester .adb to remove `Dispatch_Event` from named Event.T output handlers:
```ada
-- In test/component-*-implementation-tester.adb:
-- REMOVE this line from Critical_Event_T_Recv_Sync and similar:
--   Self.Dispatch_Event (Arg);
-- Keep only the history push:
overriding procedure Critical_Event_T_Recv_Sync (Self : in out Instance; Arg : in Event.T) is
begin
   Self.Critical_Event_T_Recv_Sync_History.Push (Arg);
   -- Do NOT call Dispatch_Event -- forwarded events have arbitrary IDs
end Critical_Event_T_Recv_Sync;
```

## Coverage Improvement Workflow

1. **Run coverage with clean build:**
   ```bash
   admt coverage
   ```

2. **Read coverage.txt, find implementation .adb section**

3. **Map missing lines to source code:**
   ```bash
   cat -n component-name-implementation.adb
   ```
   Cross-reference missing line numbers with the source.

4. **Identify pattern** (branch, connector, data dependency, structural)

5. **Add tests to .tests.yaml:**
   ```yaml
   - name: Test_New_Path
     description: Cover the uncovered branch
   ```

6. **Regenerate and copy spec:**
   ```bash
   admt templates               # prompts to copy; answer `n` to cherry-pick below
   cp build/template/*_tests-implementation.ads .
   ```

7. **Implement test in *_tests-implementation.adb**

8. **Verify:**
   ```bash
   admt coverage
   ```

## Tester Helpers for Private State Coverage

When branches depend on private component fields not reachable via commands, parameters, or connectors, add setter procedures to the hand-written tester. The tester IS a child of `Component.X.Implementation`, giving it full visibility into private record fields:

```ada
-- In tester .ads (before end):
procedure Set_Battery_Voltage (Self : in out Instance; Value : in Interfaces.Unsigned_16);

-- In tester .adb (before end):
procedure Set_Battery_Voltage (Self : in out Instance; Value : in Interfaces.Unsigned_16) is
begin
   Self.Component_Instance.Last_Battery_Voltage := Value;
end Set_Battery_Voltage;
```

Then in tests:
```ada
T.Set_Battery_Voltage (1500);  -- Force undervoltage condition
T.Tick_T_Send ((Time => T.System_Time, Count => 1));
Natural_Assert.Ge (T.Undervoltage_Fault_History.Get_Count, 1);
```

**When simulation overwrites state:** If `Tick_T_Recv_Sync` calls a simulation procedure that overwrites the field you set, you must work around the simulation:
- Set the sum/count fields so the simulation's average computation produces the desired value
- Adjust thresholds (e.g., Init with lower thresholds) so simulation values trigger the branch
- Set the field AND the threshold simultaneously

**Common uses:** voltage/current sensors, SOC levels, fault states, power states, temperature averages, mode flags, counters that need specific values for branch coverage.

## Advanced Coverage Techniques

### Queue Overflow Testing (Active Components)

#### Queue sizing for testability

```ada
Self.Tester.Init_Base (Queue_Size => Self.Tester.Component_Instance.Get_Max_Queue_Element_Size * 50);
```

Source: command_queue. Size the queue to hold exactly N messages. For
overflow tests, use a smaller multiplier.

#### Internal queue full detection

```ada
-- Fill queue (component has internal queue of 20)
for I in 1 .. 20 loop
   T.Command_T_Send (Cmd);
end loop;
Ignore := T.Dispatch_All;
Natural_Assert.Eq (T.Command_Queued_History.Get_Count, 20);
Natural_Assert.Eq (T.Queue_Full_History.Get_Count, 0);

-- One more triggers Queue_Full event
T.Command_T_Send (Cmd);
Ignore := T.Dispatch_All;
Natural_Assert.Eq (T.Queue_Full_History.Get_Count, 1);
```

Source: command_queue. Tests the component's own internal queue limit,
not the framework async queue.

### State Machine Testing Pattern

#### Valid and invalid transitions

```ada
-- Valid: Safe -> Standby
T.Command_T_Send (T.Commands.Enter_Standby_Mode);
Natural_Assert.Ge (T.Mode_Transition_Success_History.Get_Count, 1);

-- Valid: Standby -> Science
T.Command_T_Send (T.Commands.Enter_Science_Mode);
Natural_Assert.Ge (T.Mode_Transition_Success_History.Get_Count, 2);

-- Invalid: Safe -> Science (direct, should reject)
-- (test in separate procedure starting from Safe)
T.Command_T_Send (T.Commands.Enter_Science_Mode);
Natural_Assert.Ge (T.Mode_Transition_Rejected_History.Get_Count, 1);
```

Source: mode_manager. Test all valid transitions AND all invalid
ones to cover the state machine completely.

### Change Detection and Initial State

#### First tick fires extra DPs

```ada
-- Count=1 -> SOC=99 (component's Last_Soc defaults to 100)
-- The shadow value (100) differs from computed (99), so change detected
T.Tick_T_Send ((Time => (0, 0), Count => 1));
Natural_Assert.Ge (T.Data_Product_T_Recv_Sync_History.Get_Count, 1);
```

Source: battery_monitor. Components with change detection may fire DPs
on the first tick because shadow defaults differ from computed values.

#### Hysteresis in threshold transitions

```ada
-- Enter warning
T.Sensor_Value := (Value => 80.0);
T.Tick_T_Send (The_Tick);
Natural_Assert.Eq (T.Warning_Entered_History.Get_Count, 1);

-- Drop below warning but above hysteresis band (75 - 2 = 73)
T.Sensor_Value := (Value => 74.0);
T.Tick_T_Send (The_Tick);
Natural_Assert.Eq (T.Warning_Cleared_History.Get_Count, 0);  -- Still in Warning

-- Drop below hysteresis band
T.Sensor_Value := (Value => 72.0);
T.Tick_T_Send (The_Tick);
Natural_Assert.Eq (T.Warning_Cleared_History.Get_Count, 1);  -- Now cleared
```

Source: threshold_monitor. Test both the entry and exit transitions,
including hysteresis bands.

### Coverage-Specific Test Patterns

#### Trigger Invalid_Command (covers Invalid_Command handler)
```ada
-- Create valid command then corrupt the arg length:
Cmd : Command.T := T.Commands.Reset_Stats;
Cmd.Header.Arg_Buffer_Length := 22;
T.Command_T_Send (Cmd);
-- For active components, dispatch:
-- Natural_Assert.Eq (T.Dispatch_All, 1);
Natural_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get_Count, 1);
```
Framework's `Execute_Command` detects length mismatch, calls `Invalid_Command`, sends error response. Works for ANY command -- just corrupt `Arg_Buffer_Length` to any non-matching value.

#### Trigger Send_Dropped (covers Send_Dropped handlers)
Skip the connector attachment in the tester's `Connect` procedure:
```ada
-- In tester .adb, comment out one Attach:
-- Self.Component_Instance.Attach_Event_T_Send (To_Component => Self'Unchecked_Access, Hook => Self.Event_T_Recv_Sync_Access);
-- Then trigger the component to send on that connector.
-- The Send_If_Connected check sees no connection and calls Send_Dropped.
```
Alternative: add `Expect_Event_T_Send_Dropped : Boolean := False;` to tester spec and use the framework's connector status mechanism.

#### Trigger Recv_Async_Dropped (covers async dropped handler)
Overflow the async queue by sending more messages than `Queue_Size` allows:
```ada
-- Init with tiny queue:
T.Init_Base (Queue_Size => T.Component_Instance.Get_Max_Queue_Element_Size * 2);
-- Send 3 messages to overflow:
T.Packet_T_Send (Pkt);
T.Packet_T_Send (Pkt);
T.Packet_T_Send (Pkt);  -- This one triggers Recv_Async_Dropped
```

## Coverage Anti-Patterns (What NOT to Do)

1. Do NOT create commands manually -- always use `T.Commands.<Name>` for the component's own commands
2. Do NOT call `T.Dispatch_All` on passive component testers (compile error)
3. Do NOT use `(others => 0)` for arrays -- use `[others => 0]` (Ada 2022)
4. Do NOT assume raw history clear also clears typed histories
5. Do NOT use `Time => (0, 0)` with data dependencies (staleness failure)
6. Do NOT forget `pragma Unreferenced` on unused Status or Ignore variables
7. Do NOT hand-write tester specs -- always copy from `build/template/`
8. Do NOT use `with Smart_Assert;` directly -- use `Basic_Assertions` or typed `*_Assert`
9. Do NOT skip Set_Up when YAML has init params
10. Do NOT forget to Dispatch_All for active components (sends queue but don't process)
11. Do NOT use .Value field access when typed assertion exists (less informative errors)
12. Do NOT mix `Self.Tester.*` and undeclared `T.*` -- either use full path or declare the rename
13. Do NOT use low command IDs (0, 1, 2...) for raw Command.T in tests -- they collide with registered local command IDs (Reset_Counts_Id => 0, etc.). Use high IDs (100+) to avoid accidentally triggering command handlers.
14. Do NOT use `(Value => 1)` for command args with custom record/enum types -- use `(others => <>)` or the correct field names. For Invalid_Command tests the arg doesn't matter (length is corrupted), but it must compile.
15. Do NOT leave `Dispatch_Event` calls in tester overrides for Event.T connectors that carry forwarded/external events. When a component has a non-component Event.T send connector (e.g., `Filtered_Event_T_Send`), the generated tester calls `Self.Dispatch_Event(Arg)` on it. Forwarded events have arbitrary IDs outside the local enum range, causing `CONSTRAINT_ERROR`. Fix: edit tester .adb to remove the `Dispatch_Event` call, keep only `Self.Filtered_Event_T_Recv_Sync_History.Push(Arg);`.

## gcovr Known Issues

- **gcovr 8.6 path bug:** Some components get `SanityCheckError: Output file ... doesn't exist`. The gcov output path is mangled. No workaround other than upgrading gcovr.
- **Active component 0% coverage:** Some active components (telemetry_collector, watchdog_kicker) show 0% on ALL files including test code despite all tests passing. This is a GNAT/gcov limitation: Ada tasks in active components may prevent clean process exit, so gcov data (.gcda files) is never flushed to disk. The .gcno (notes) files exist but no .gcda (data) files are produced. Running the binary manually (not via `admt coverage`) sometimes produces .gcda files, but with stamp mismatches. No workaround exists for the redo pipeline -- this is a structural limitation.
