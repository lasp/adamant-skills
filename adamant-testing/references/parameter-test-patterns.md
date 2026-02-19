<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Parameter and Data Dependency Test Patterns

Stage/validate/update flow, data dependency mocking, and stale data simulation.

---

## 5. Parameter Testing Patterns

### 5a. Full stage-validate-update cycle

```ada
Status := T.Stage_Parameter (T.Parameters.Output_Limit ((Value => 5.0)));
pragma Assert (Status = Parameter_Enums.Parameter_Update_Status.Success);
Status := T.Validate_Parameters;
pragma Assert (Status = Parameter_Enums.Parameter_Update_Status.Success);
Status := T.Update_Parameters;
pragma Assert (Status = Parameter_Enums.Parameter_Update_Status.Success);
```

Source: pid_controller. All three steps required. Declare Status as
`Parameter_Enums.Parameter_Update_Status.E`. Requires:
```ada
with Parameter_Enums; use type Parameter_Enums.Parameter_Update_Status.E;
```

### 5b. Validation rejection

```ada
Status := T.Stage_Parameter (T.Parameters.Warning_Threshold ((Value => 95.0)));
pragma Assert (Status = Parameter_Enums.Parameter_Update_Status.Success);
Status := T.Validate_Parameters;
pragma Assert (Status = Parameter_Enums.Parameter_Update_Status.Validation_Error);
```

Source: threshold_monitor. Stage succeeds (just buffers), but Validate
rejects because the component's Validate_Parameters override checks
cross-parameter constraints (warning >= critical is invalid).

### 5c. Parameter takes effect on tick

After Update_Parameters succeeds, the component reads new values in its
next tick handler. You must send a tick after updating:

```ada
Status := T.Update_Parameters;
T.Tick_T_Send (The_Tick);
-- Now assert the new behavior (output clamped to 5.0)
Packed_F32_Assert.Eq (T.Output_History.Get (1), (Value => 5.0));
```

Source: pid_controller.

---

## 6. Data Dependency Testing Patterns

### 6a. Setting mock values and ticking

```ada
Test_Time : constant Sys_Time.T := (100, 0);
The_Tick : constant Tick.T := (Time => Test_Time, Count => 0);

-- In Set_Up_Test:
T.System_Time := Test_Time;
T.Data_Dependency_Timestamp_Override := Test_Time;

-- In test body, set the mock value then tick:
T.Sensor_Value := (Value => 50.0);
T.Tick_T_Send (The_Tick);
```

Source: threshold_monitor. Field names (Sensor_Value, Setpoint, etc.)
match the names in `data_dependencies.yaml`. The tester auto-generates
these fields.

### 6b. Multiple data dependencies

```ada
T.Setpoint := (Value => 10.0);
T.Process_Value := (Value => 7.0);
T.Tick_T_Send (The_Tick);
-- error = 10.0 - 7.0 = 3.0, output = Kp * 3.0 = 3.0
Packed_F32_Assert.Eq (T.Output_History.Get (1), (Value => 3.0));
```

Source: pid_controller. Set all dependency fields before ticking.

### 6c. Simulating fetch failure

```ada
T.Data_Dependency_Return_Status_Override := Data_Product_Enums.Fetch_Status.Id_Out_Of_Range;
T.Tick_T_Send (The_Tick);
-- Component's error path fires a fault, no DPs sent
Natural_Assert.Eq (T.Sensor_Failure_History.Get_Count, 1);
Natural_Assert.Eq (T.Data_Product_T_Recv_Sync_History.Get_Count, 0);
```

Source: threshold_monitor. Override the return status to test the
component's error handling for missing/failed data dependencies.

### 6d. Simulating stale data

```ada
T.Data_Dependency_Timestamp_Override := (50, 0);  -- Old timestamp
T.Tick_T_Send ((Time => (100, 0), Count => 0));   -- Current time is newer
```

The framework detects that the data product timestamp is older than
expected and reports staleness to the component.

---

