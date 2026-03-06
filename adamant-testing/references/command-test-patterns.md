<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Command Test Patterns

Command dispatch, argument construction, async dispatch, and helper function patterns.

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

Source: pid_controller. Argument is a record aggregate matching
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
Command_Response_Status_Assert.Eq (
   T.Command_Response_T_Recv_Sync_History.Get (1).Status,
   Command_Enums.Command_Response_Status.Success);
```

Source: threshold_monitor, telemetry_filter. Simpler when you only care
about success/failure. Requires `with Command_Enums.Assertion; use Command_Enums.Assertion;`.

### 4f. Multiple commands in sequence (cumulative history)

```ada
T.Command_T_Send (T.Commands.Enter_Standby_Mode);
Natural_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get_Count, 1);
Natural_Assert.Ge (T.Mode_Transition_Success_History.Get_Count, 1);

T.Command_T_Send (T.Commands.Enter_Science_Mode);
Natural_Assert.Ge (T.Mode_Transition_Success_History.Get_Count, 2);
```

Source: mode_manager. History accumulates -- use cumulative indices.

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

Source: mode_manager. Test both valid and invalid transitions to
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

