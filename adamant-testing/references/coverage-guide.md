# Adamant Test Coverage Guide

Systematic approach to measuring and improving component implementation coverage using `redo coverage` and gcovr.

## Running Coverage

```bash
# From component test/ directory:
cd src/components/component_name/test

# CRITICAL: Clean build artifacts first. Stale .gcda from non-coverage
# builds corrupt results (shows wrong coverage numbers).
rm -rf build
redo coverage

# Output:
# build/coverage/coverage.txt   (text report)
# build/coverage/test.html/     (HTML report)
```

Coverage compiles with `-fprofile-arcs -ftest-coverage`, runs the test binary, then generates gcovr report. Test failures still produce valid coverage data.

## Reading Coverage Reports

The coverage.txt file lists ALL source files compiled into the test binary. Most are framework code. Focus on:

```
component-component_name-implementation.adb    <-- YOUR code (this is what matters)
component-component_name-implementation.ads    <-- spec (usually 100%)
```

Ignore these (framework/generated, inflates denominator):
- `build/src/component-*_reciprocal.*` -- generated tester reciprocal
- `build/src/*_tests.*` -- generated test framework
- `build/obj/*/b__test.adb` -- binder generated
- `test/component-*-tester.*` -- tester template
- Framework type packages (quaternion.adb, packed_u32.adb, etc.)

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

## Structural Coverage Ceiling

Most components have 10-20% structurally uncoverable code. These patterns create a practical ceiling of ~80-85%:

### Send_Dropped Handlers (null bodies)
```ada
overriding procedure Event_T_Send_Dropped (Self : in out Instance; Arg : in Event.T) is
begin
   null;  -- Only called when send connector not attached
end Event_T_Send_Dropped;
```
These only execute if the send connector is disconnected, which the tester always connects. Cannot be covered without modifying tester wiring.

### Invalid_Command Handler
```ada
overriding procedure Invalid_Command (Self : in out Instance; Cmd : in Command.T;
   Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type) is
begin
   null;  -- Framework calls this for malformed commands
end Invalid_Command;
```
Framework's Execute_Command calls this when command argument deserialization fails. Difficult to trigger from tester because `T.Commands.*` always produces valid arguments.

### Recv_Async_Dropped Handler
```ada
overriding procedure Packet_T_Recv_Async_Dropped (Self : in out Instance; Arg : in Packet.T) is
begin
   null;  -- Queue overflow already handled by framework
end Packet_T_Recv_Async_Dropped;
```

### Coverage Target by Component Type

| Component Type | Realistic Target | Notes |
|---|---|---|
| Simple passive (no commands) | 95-100% | Only Send_Dropped uncovered |
| Passive with commands | 80-90% | + Invalid_Command |
| Active (async recv) | 75-85% | + Recv_Async_Dropped |
| Active with commands | 70-80% | All three structural gaps |

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
   rm -rf build && redo coverage
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
   redo templates
   cp build/template/*_tests-implementation.ads .
   ```

7. **Implement test in *_tests-implementation.adb**

8. **Verify:**
   ```bash
   rm -rf build && redo coverage
   ```

## gcovr Known Issues

- **gcovr 8.6 path bug:** Some components get `SanityCheckError: Output file ... doesn't exist`. The gcov output path is mangled. No workaround other than upgrading gcovr.
- **Active component 0% coverage:** Some active components show 0% on ALL files including test code. This means the coverage-instrumented binary didn't execute properly. Clean rebuild usually fixes it.
