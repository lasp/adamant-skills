# Adamant Test Pattern Corpus

Comprehensive reference of test patterns extracted from bot_station components.
Each pattern shows correct code from real components with explanations of why.

---

## 1. Set_Up_Test Patterns

### 1a. Simplest passive component (no init, no Set_Up)

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
end Set_Up_Test;
```

Source: edge_detector. Some components have no init params AND no Set_Up
logic. Both Init and Set_Up are optional -- only call them if the component
YAML declares `init:` parameters or the component has a `Set_Up` override.

### 1b. Passive component with Set_Up but no init params

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;
```

Source: uptime_counter, station_mode_manager, heartbeat_monitor. Most
components have Set_Up even without init params (registers commands, etc.).

### 1c. Passive component with init params

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Init (Low_Threshold => 20, Critical_Threshold => 10);
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;
```

Source: battery_monitor. Order is critical: Init_Base -> Connect -> Init -> Set_Up.
Init params come from the component's `init` section in YAML. They go to
`Component_Instance.Init`, never to `Init_Base`.

### 1d. Passive component with packed type init param

```ada
Self.Tester.Component_Instance.Init (Default_State => (Value => 1));
```

Source: power_switch. When init param is a packed type (Packed_U32.T, etc.),
wrap in aggregate: `(Value => N)`.

### 1e. Active component (needs Queue_Size)

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base (Queue_Size => Self.Tester.Component_Instance.Get_Max_Queue_Element_Size * 50);
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;
```

Source: command_queue. The `Queue_Size` argument is ONLY for active
components. It sizes the internal async message queue in bytes.
Use `Get_Max_Queue_Element_Size * N` to hold N messages.

### 1f. Active component with init params

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base (Queue_Size => Self.Tester.Component_Instance.Get_Max_Queue_Element_Size * 60);
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Init (Rate_Threshold => (Value => 10));
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;
```

Source: event_aggregator. Active + init params = both Queue_Size in
Init_Base AND params in Component_Instance.Init.

### 1g. Passive component with data dependencies

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Set_Up;
   -- Set tester time to match tick time (prevents staleness failures)
   Self.Tester.System_Time := Test_Time;
   Self.Tester.Data_Dependency_Timestamp_Override := Test_Time;
end Set_Up_Test;
```

Source: threshold_monitor. Data dependency timestamps MUST be non-zero and
must match the tick time, or the framework flags the data as stale.
Also set initial data dependency values:
```ada
Self.Tester.Setpoint := (Value => 0.0);
Self.Tester.Process_Value := (Value => 0.0);
```
Source: station_pid_controller.

### 1h. Deferred init (per-test initialization)

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   -- Component init is done in individual tests with specific values
end Set_Up_Test;

-- Then in each test:
overriding procedure Test_Nominal_Check (Self : in out Instance) is
   T : ... renames Self.Tester;
begin
   T.Component_Instance.Init (Check_Period => 1);
   T.Component_Instance.Set_Up;
   -- ... test logic ...
end Test_Nominal_Check;
```

Source: health_checker. When tests need different init params, defer Init
and Set_Up to each test body. This is common for components where init
params fundamentally change behavior.

### 1i. T. shorthand in Set_Up/Tear_Down

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
   T : Component.Telemetry_Filter.Implementation.Tester.Instance_Access renames Self.Tester;
begin
   T.Init_Base;
   T.Connect;
end Set_Up_Test;
```

Source: telemetry_filter. Some components use the T rename in fixtures too.
Both styles (Self.Tester.* vs T.*) are valid.

---

## 2. Tear_Down_Test

Always the same pattern across all components:

```ada
overriding procedure Tear_Down_Test (Self : in out Instance) is
begin
   Self.Tester.Final_Base;
end Tear_Down_Test;
```

No exceptions. No cleanup needed beyond Final_Base.

---

## 3. Dispatch_All Patterns (Active Components Only)

### 3a. Capture and assert return value

```ada
Count := T.Dispatch_All;
Natural_Assert.Eq (Count, 5);
```

Source: event_aggregator. Dispatch_All is a FUNCTION returning Natural
(number of messages processed). Must capture or use in expression.

### 3b. Inline assertion (preferred framework pattern)

```ada
Natural_Assert.Eq (T.Dispatch_All, 5);
```

Combines dispatch and assertion. Clean and idiomatic.

### 3c. Discard return value (don't care about count)

```ada
Ignore := T.Dispatch_All;
pragma Unreferenced (Ignore);
```

With declaration: `Ignore : Natural;`

Source: command_queue. Use when you only care about side effects, not count.
Ada does not allow discarding function return values without assignment.

### 3d. Send-then-dispatch workflow

```ada
-- Nothing processed yet (async queue holds messages)
for I in 1 .. 5 loop
   T.Event_T_Send (Dummy_Evt);
end loop;
Count := T.Dispatch_All;
Natural_Assert.Eq (Count, 5);

-- NOW the component has processed them
T.Tick_T_Send ((Time => (0, 0), Count => 1));
Natural_Assert.Ge (T.Window_Report_History.Get_Count, 1);
```

Source: event_aggregator. The key insight: sending to async connectors
queues messages. Nothing happens until Dispatch_All processes them.

### 3e. Dispatch_All does NOT exist on passive testers

Passive components process synchronously in the Send call itself. Calling
Dispatch_All on a passive tester is a compile error. If you see "no selector
Dispatch_All", the component is passive.

---

## 4. Command Testing Patterns

### 4a. Simple no-arg command

```ada
T.Command_T_Send (T.Commands.Reset_Monitor);
Natural_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get_Count, 1);
```

Source: heartbeat_monitor. Always use `T.Commands.<Name>` for command
construction. The tester's Commands object has the correct ID base.

### 4b. Command with record arguments

```ada
T.Command_T_Send (T.Commands.Set_Gains ((Kp => 2.0, Ki => 0.0, Kd => 0.0)));
Natural_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get_Count, 1);
Natural_Assert.Eq (T.Gains_Updated_History.Get_Count, 1);
```

Source: station_pid_controller. Argument is a record aggregate matching
the command's argument type from the commands YAML.

### 4c. Command with packed type argument

```ada
T.Command_T_Send (T.Commands.Set_Priority ((Value => 10)));
```

Source: telemetry_filter. Packed types use `(Value => N)`.

### 4d. Command with bitfield-packed argument

```ada
T.Command_T_Send (T.Commands.Set_Thresholds (
   (Value => Unsigned_32 (30) * 2 ** 16 + Unsigned_32 (15))));
```

Source: battery_monitor. When a command packs multiple fields into a single
word, use bit shifting to construct the value.

### 4e. Lightweight response check (just status)

```ada
pragma Assert (T.Command_Response_T_Recv_Sync_History.Get (1).Status =
   Command_Enums.Command_Response_Status.Success);
```

Source: threshold_monitor, telemetry_filter. Simpler when you only care
about success/failure. Requires `use type Command_Enums.Command_Response_Status.E;`.

### 4f. Multiple commands in sequence (cumulative history)

```ada
T.Command_T_Send (T.Commands.Enter_Standby_Mode);
Natural_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get_Count, 1);
Natural_Assert.Ge (T.Mode_Transition_Success_History.Get_Count, 1);

T.Command_T_Send (T.Commands.Enter_Science_Mode);
Natural_Assert.Ge (T.Mode_Transition_Success_History.Get_Count, 2);
```

Source: station_mode_manager. History accumulates -- use cumulative indices.

### 4g. Dual command connectors (async + sync)

```ada
-- Sync command connector (component's own commands)
T.Command_T_Send_2 (T.Commands.Clear_Queue);
Natural_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get_Count, 1);
```

Source: command_queue. When a component has both async and sync command
receive connectors, the tester generates `_Send` (async) and `_Send_2` (sync).

### 4h. Testing rejected commands (state machine)

```ada
-- Try Science from Safe (should reject)
T.Command_T_Send (T.Commands.Enter_Science_Mode);
Natural_Assert.Ge (T.Mode_Transition_Rejected_History.Get_Count, 1);

-- Try Maneuver from Safe (should reject)
T.Command_T_Send (T.Commands.Enter_Maneuver_Mode);
Natural_Assert.Ge (T.Mode_Transition_Rejected_History.Get_Count, 2);
```

Source: station_mode_manager. Test both valid and invalid transitions to
cover the state machine's rejection paths.

### 4i. Invalid command (wrong arg length)

```ada
Invalid_Cmd : Command.T := T.Commands.Set_Value ((Value => 0));
Invalid_Cmd.Header.Arg_Buffer_Length := 0;  -- Corrupt the length
T.Command_T_Send (Invalid_Cmd);
-- Expect Length_Error response
```

Modify a valid command's header to trigger the framework's length check.
The component never sees the command; the framework rejects it.

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

Source: station_pid_controller. All three steps required. Declare Status as
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

Source: station_pid_controller.

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

Source: station_pid_controller. Set all dependency fields before ticking.

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

## 7. Data Product Assertion Patterns

### 7a. Count check on raw connector history

```ada
Natural_Assert.Eq (T.Data_Product_T_Recv_Sync_History.Get_Count, 10);
```

Source: uptime_counter. Raw history captures ALL data products sent.

### 7b. Typed history check (specific DP)

```ada
Natural_Assert.Eq (T.Output_History.Get_Count, 1);
Packed_F32_Assert.Eq (T.Output_History.Get (1), (Value => 3.0));
```

Source: station_pid_controller. Typed histories are named `{dp_name}_History`.
Values are 1-indexed. Use the matching assertion package for the DP type.

### 7c. Multiple DPs per tick

```ada
T.Tick_T_Send (The_Tick);
-- 3 DPs per tick: Current_State, Warning_Count, Critical_Count
Natural_Assert.Eq (T.Data_Product_T_Recv_Sync_History.Get_Count, 3);
Packed_Monitor_State_Assert.Eq (T.Current_State_History.Get (1),
   (State => Monitor_State.Monitor_State_Type.Nominal));
Packed_U32_Assert.Eq (T.Warning_Count_History.Get (1), (Value => 0));
Packed_U32_Assert.Eq (T.Critical_Count_History.Get (1), (Value => 0));
```

Source: threshold_monitor. Components often emit multiple DPs per tick.

### 7d. DP history accumulates across ticks (use cumulative indices)

```ada
T.Tick_T_Send ((Time => (0, 0), Count => 1));   -- DPs at indices 1..N
T.Tick_T_Send ((Time => (0, 0), Count => 2));   -- DPs at indices N+1..2N
-- Access second tick's value:
Packed_U32_Assert.Eq (T.Ticks_Since_Heartbeat_History.Get (2), (Value => 2));
```

Source: heartbeat_monitor. Typed histories accumulate. Index grows with
each emission. Clear if you need to reset indices.

### 7e. Using .Get_Count for latest index

```ada
Packed_U32_Assert.Eq (
   T.Window_Report_History.Get (T.Window_Report_History.Get_Count),
   (Value => 0));
```

Source: event_aggregator. When you want the most recently emitted value
regardless of how many have been emitted, use `.Get_Count` as the index.

### 7f. Direct field access on history values

```ada
Assert (T.Switch_State_History.Get (1).Value = Unsigned_8'(1), "Should be ON");
```

Source: power_switch. You can access fields directly on `.Get(N)` results
without using typed assertions. Useful with AUnit Assert.

### 7g. Natural_Assert.Ge for framework-dependent counts

```ada
Natural_Assert.Ge (T.Data_Product_T_Recv_Sync_History.Get_Count, 1);
```

Source: health_aggregator, station_mode_manager. When exact count depends
on framework internals (initial DPs, registration events), use Ge instead
of Eq.

---

## 8. Event History Assertion Patterns

### 8a. Raw event count

```ada
Natural_Assert.Eq (T.Event_T_Recv_Sync_History.Get_Count, 1);
```

Source: heartbeat_monitor. Counts all events regardless of type.

### 8b. Typed event history (count-only)

```ada
Natural_Assert.Eq (T.Monitor_Reset_History.Get_Count, 1);
Natural_Assert.Eq (T.Heartbeat_Ok_History.Get_Count, 1);
```

Source: heartbeat_monitor. Named `{event_name}_History`. Count-only check
is common when the event has no interesting parameters.

### 8c. Event with parameter value

```ada
Natural_Assert.Eq (T.Heartbeat_Missing_History.Get_Count, 1);
Packed_U32_Assert.Eq (T.Heartbeat_Missing_History.Get (1), (Value => 11));
```

Source: heartbeat_monitor. Event parameters are captured in the typed
history. Access with `.Get(index)` and assert with matching typed assertion.

### 8d. Event with F32 parameter

```ada
Natural_Assert.Eq (T.Warning_Entered_History.Get_Count, 1);
Packed_F32_Assert.Eq (T.Warning_Entered_History.Get (1), (Value => 75.0));
```

Source: threshold_monitor. Same pattern, different packed type.

### 8e. Absence check (no event fired)

```ada
Natural_Assert.Eq (T.Output_Saturated_History.Get_Count, 0);
Natural_Assert.Eq (T.Event_T_Recv_Sync_History.Get_Count, 0);
```

Source: station_pid_controller, heartbeat_monitor. Explicitly verify that
error/warning events did NOT fire in nominal paths.

---

## 9. Fault Testing Patterns

### 9a. Component-emitted faults (fault send connector)

```ada
-- Trigger condition that makes component emit a fault
T.Data_Dependency_Return_Status_Override := Data_Product_Enums.Fetch_Status.Id_Out_Of_Range;
T.Tick_T_Send (The_Tick);
Natural_Assert.Eq (T.Sensor_Failure_History.Get_Count, 1);
```

Source: threshold_monitor. Fault histories work like event histories.

### 9b. Fault with idempotent trigger (fires once)

```ada
-- Tick 11 times to trigger fault
for I in 1 .. 11 loop
   T.Tick_T_Send ((Time => (0, 0), Count => Interfaces.Unsigned_32 (I)));
end loop;
Natural_Assert.Eq (T.Fault_T_Recv_Sync_History.Get_Count, 1);
Natural_Assert.Eq (T.Heartbeat_Lost_History.Get_Count, 1);

-- Additional ticks don't trigger more faults
T.Tick_T_Send ((Time => (0, 0), Count => 12));
T.Tick_T_Send ((Time => (0, 0), Count => 13));
Natural_Assert.Eq (T.Fault_T_Recv_Sync_History.Get_Count, 1);  -- Still 1
```

Source: heartbeat_monitor. Many components fire faults only once per
condition (latch behavior). Test that additional triggers don't duplicate.

### 9c. Fault triggered by accumulation

```ada
-- Send 10 packets (no fault yet):
for I in 1 .. 10 loop
   T.Packet_T_Send (Pkt);
end loop;
pragma Assert (T.Fault_T_Recv_Sync_History.Get_Count = 0);

-- 11th crosses threshold:
T.Packet_T_Send (Pkt);
pragma Assert (T.Fault_T_Recv_Sync_History.Get_Count >= 1);
```

Source: telemetry_filter. Faults can trigger after N occurrences.

---

## 10. History Management Patterns

### 10a. Clear before next phase

```ada
T.Event_T_Recv_Sync_History.Clear;
T.Data_Product_T_Recv_Sync_History.Clear;
T.Output_History.Clear;
T.Integral_History.Clear;
T.Error_History.Clear;
```

Source: station_pid_controller. Clear both raw AND typed histories when
starting a new test phase. Raw clear does NOT clear typed.

### 10b. Periodic clear to avoid depth overflow (100 max)

```ada
for I in 1 .. 90 loop
   T.Tick_T_Send ((Time => (0, 0), Count => Unsigned_32 (I)));
   if I mod 40 = 0 then
      T.Data_Product_T_Recv_Sync_History.Clear;
      T.Tick_Count_History.Clear;
      T.Uptime_Seconds_History.Clear;
   end if;
end loop;
```

Source: uptime_counter. History depth is 100 entries. If a component emits
2 DPs per tick, overflow at tick 50. Clear periodically in long loops.

### 10c. Clear before final assertion window

```ada
-- Clear before final stretch
T.Data_Product_T_Recv_Sync_History.Clear;
T.Tick_Count_History.Clear;
T.Uptime_Seconds_History.Clear;

-- Ticks 91-100
for I in 91 .. 100 loop
   T.Tick_T_Send ((Time => (0, 0), Count => Unsigned_32 (I)));
end loop;

-- Now assert on known-clean history
Natural_Assert.Eq (T.Uptime_Milestone_History.Get_Count, 1);
```

Source: uptime_counter. Clear just before the interesting window so
indices are predictable.

---

## 11. Queue Overflow Testing (Active Components)

### 11a. Queue sizing for testability

```ada
Self.Tester.Init_Base (Queue_Size => Self.Tester.Component_Instance.Get_Max_Queue_Element_Size * 50);
```

Source: command_queue. Size the queue to hold exactly N messages. For
overflow tests, use a smaller multiplier.

### 11b. Internal queue full detection

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

---

## 12. Custom Packed Type Patterns

### 12a. Pack unpacked record to packed type for sending

```ada
with Thruster_Command;

Cmd : constant Thruster_Command.U := (
   Thruster_Id => (Value => 1),
   Thrust_Magnitude => (Value => 10.0),
   Duration_Ms => (Value => 500));

T.Thruster_Command_T_Send (Thruster_Command.Pack (Cmd));
```

Source: thruster_controller. When a connector expects a packed type (.T),
construct the unpacked version (.U) and call `.Pack(...)`. Each subfield
of the unpacked type is itself a packed type with `(Value => N)`.

### 12b. Custom enum assertion

```ada
with Monitor_State;
with Packed_Monitor_State.Assertion; use Packed_Monitor_State.Assertion;

Packed_Monitor_State_Assert.Eq (T.Current_State_History.Get (1),
   (State => Monitor_State.Monitor_State_Type.Nominal));
```

Source: threshold_monitor. For custom packed enum types, the assertion
package and the enum type come from different packages. The packed type
wraps the enum.

---

## 13. Tick Construction Patterns

### 13a. Inline tick (most common)

```ada
T.Tick_T_Send ((Time => (0, 0), Count => 1));
```

Fine for simple tests where data dependencies are not involved.

### 13b. Named constant tick

```ada
The_Tick : constant Tick.T := (Time => (0, 0), Count => 1);
-- or positional:
The_Tick : constant Tick.T := ((0, 0), 1);
```

Source: station_pid_controller, command_queue. Better when reused.
Requires `with Tick;`.

### 13c. Tick with matching data dependency time

```ada
Test_Time : constant Sys_Time.T := (100, 0);
The_Tick : constant Tick.T := (Time => Test_Time, Count => 0);
```

Source: threshold_monitor. MUST use non-zero time and match
`Data_Dependency_Timestamp_Override` to avoid staleness errors.

### 13d. Loop ticks with cast

```ada
for I in 1 .. 5 loop
   T.Tick_T_Send ((Time => (0, 0), Count => Unsigned_32 (I)));
end loop;
```

Source: uptime_counter. `Count` is `Interfaces.Unsigned_32`, loop variable
is Integer. Cast required. Requires `with Interfaces; use Interfaces;`.

### 13e. Tick count as component input

```ada
-- Count=81 -> SOC = 100 - 81 = 19 (below Low_Threshold=20)
T.Tick_T_Send ((Time => (0, 0), Count => 81));
Natural_Assert.Ge (T.Soc_Low_Warning_History.Get_Count, 1);
```

Source: battery_monitor. Some components use `Count` as input data
(not just a sequence number). The tick count drives behavior.

---

## 14. Helper Function Patterns

### 14a. Package-level constants for test stimuli

```ada
Dummy_Evt : constant Event.T := (
   Header => (Time => (0, 0), Id => Event_Types.Event_Id'First,
              Param_Buffer_Length => 0),
   Param_Buffer => [others => 0]);
```

Source: event_aggregator. Declare constants at package body level when
shared across multiple test procedures.

### 14b. Local constants for command construction

```ada
Cmd_1 : constant Command.T := (
   (Source_Id => 1, Id => 10, Arg_Buffer_Length => 0),
   [others => 0]);
```

Source: command_queue. When testing raw command routing (not component's
own commands), construct Command.T directly. Note: use `T.Commands.<Name>`
for the component's own commands; raw construction only for forwarded/routed
commands.

### 14c. Packet.T construction

```ada
Pkt : Packet.T;
Pkt.Header := (
   Time => (0, 0),
   Id => 5,
   Sequence_Count => 0,
   Buffer_Length => 0);
```

Source: telemetry_filter. Packet.T Header has Time, Id, Sequence_Count,
and Buffer_Length. No Priority field.

---

## 15. State Machine Testing Pattern

### 15a. Valid and invalid transitions

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

Source: station_mode_manager. Test all valid transitions AND all invalid
ones to cover the state machine completely.

---

## 16. Change Detection and Initial State

### 16a. First tick fires extra DPs

```ada
-- Count=1 -> SOC=99 (component's Last_Soc defaults to 100)
-- The shadow value (100) differs from computed (99), so change detected
T.Tick_T_Send ((Time => (0, 0), Count => 1));
Natural_Assert.Ge (T.Data_Product_T_Recv_Sync_History.Get_Count, 1);
```

Source: battery_monitor. Components with change detection may fire DPs
on the first tick because shadow defaults differ from computed values.

### 16b. Hysteresis in threshold transitions

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

---

## 17. Assertion Style Patterns

### 17a. Typed assertions (preferred)

```ada
Packed_U32_Assert.Eq (T.Tick_Count_History.Get (5), (Value => 5));
Packed_F32_Assert.Eq (T.Output_History.Get (1), (Value => 3.0));
Packed_Byte_Assert.Eq (T.Heartbeat_State_History.Get (1), (Value => 0));
```

Source: uptime_counter, station_pid_controller, heartbeat_monitor.
Type-safe, clear error messages.

### 17b. AUnit Assert (acceptable alternative)

```ada
Assert (T.Switch_State_History.Get (1).Value = Unsigned_8'(1), "Should be ON");
```

Source: power_switch. Works but less precise error messages. Requires
`with AUnit.Assertions; use AUnit.Assertions;`.

### 17c. pragma Assert (simple checks)

```ada
pragma Assert (T.Packet_T_Recv_Sync_History.Get_Count = 1, "Expected 1 forwarded packet");
pragma Assert (T.Command_Response_T_Recv_Sync_History.Get (1).Status =
   Command_Enums.Command_Response_Status.Success);
```

Source: telemetry_filter. Simple boolean checks. No import needed.
Note: bare `pragma Assert` gives poor error messages on failure.

---

## 18. Common With-Clause Sets

### Minimal (passive, no commands, basic DPs)
```ada
with Basic_Assertions; use Basic_Assertions;
with Packed_U32.Assertion; use Packed_U32.Assertion;
```

### With loop counters
```ada
with Interfaces; use Interfaces;
```

### With commands
```ada
with Command_Enums;
use type Command_Enums.Command_Response_Status.E;
```

### With parameters
```ada
with Parameter_Enums; use type Parameter_Enums.Parameter_Update_Status.E;
```

### With data dependencies
```ada
with Sys_Time;
with Data_Product_Enums;
```

### With faults
```ada
with Fault;
```

### With custom packed types (match your component)
```ada
with Packed_F32.Assertion; use Packed_F32.Assertion;
with Packed_Byte.Assertion; use Packed_Byte.Assertion;
with Packed_U16.Assertion; use Packed_U16.Assertion;
with Packed_Monitor_State.Assertion; use Packed_Monitor_State.Assertion;
```

### With custom project types (for Pack/Unpack)
```ada
with Thruster_Command;
with Monitor_State;
```

### With Event construction
```ada
with Event;
with Event_Types;
```

### With Packet construction
```ada
with Packet;
```

### With Command construction (raw, not via T.Commands)
```ada
with Command;
with Command.Assertion; use Command.Assertion;
```

### With Tick (for named constants)
```ada
with Tick;
```

---

## 19. Anti-Patterns (What NOT to Do)

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
