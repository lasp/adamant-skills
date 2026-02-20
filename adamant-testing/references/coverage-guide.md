<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Adamant Test Coverage Guide

Coverage analysis using `redo coverage` and gcovr.

## Running Coverage

```bash
cd src/components/component_name/test
redo coverage
```

Output files:
- `build/coverage/coverage.txt` (text report)
- `build/coverage/test.html/` (HTML report)

## Reading Coverage Reports

Focus on these files in `coverage.txt`:
- `component-*-implementation.adb` -- your implementation (primary target)
- `component-*-implementation.ads` -- interface (`is null` handlers inflate miss count but aren't testable)

The `Missing` column shows uncovered line numbers. Map to source with:
```bash
cat -n component-*-implementation.adb  # From component dir, not test/
```

Ignore generated framework code (`build/src/`, `test/build/`).

## Core Coverage Patterns

### Send_Dropped Handlers
Set tester status to trigger Send_Dropped:
```ada
T.Connector_Event_T_Recv_Sync_Status := Connector_Types.Message_Dropped;
T.Tick_T_Send ((Time => (0, 0), Count => 1));
T.Connector_Event_T_Recv_Sync_Status := Connector_Types.Success;  -- Restore
```

### Invalid_Command Handler
```ada
Cmd : Command.T := T.Commands.My_Command ((Value => 0));
Cmd.Header.Arg_Buffer_Length := 22;  -- Corrupt length
T.Command_T_Send (Cmd);
Natural_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get_Count, 1);
```

### Data Dependency Error Paths
```ada
T.Data_Dependency_Return_Status_Override := Data_Product_Enums.Fetch_Status.Id_Out_Of_Range;
T.Tick_T_Send (The_Tick);
-- Test component's error handling
```

## Common Missing Coverage

- **Connector handlers not called:** Add test that sends via that connector
- **Untested branches:** Add input that triggers the uncovered condition  
- **Active async paths:** Must dispatch after sending: `T.Dispatch_All`
- **Data dependency paths:** Override tester service functions to return test data

Coverage target: 95%+ for passive components, 85-95% for active components.