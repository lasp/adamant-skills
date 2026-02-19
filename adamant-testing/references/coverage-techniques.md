<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Coverage Techniques

Full path coverage, error injection, queue overflow, state machine testing, and anti-patterns.

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

Source: mode_manager. Test all valid transitions AND all invalid
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


## 19. Coverage-Specific Test Patterns

### 19a. Trigger Invalid_Command (covers Invalid_Command handler)
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

### 19b. Trigger Send_Dropped (covers Send_Dropped handlers)
Skip the connector attachment in the tester's `Connect` procedure:
```ada
-- In tester .adb, comment out one Attach:
-- Self.Component_Instance.Attach_Event_T_Send (To_Component => Self'Unchecked_Access, Hook => Self.Event_T_Recv_Sync_Access);
-- Then trigger the component to send on that connector.
-- The Send_If_Connected check sees no connection and calls Send_Dropped.
```
Alternative: add `Expect_Event_T_Send_Dropped : Boolean := False;` to tester spec and use the framework's connector status mechanism.

### 19c. Trigger Recv_Async_Dropped (covers async dropped handler)
Overflow the async queue by sending more messages than `Queue_Size` allows:
```ada
-- Init with tiny queue:
T.Init_Base (Queue_Size => T.Component_Instance.Get_Max_Queue_Element_Size * 2);
-- Send 3 messages to overflow:
T.Packet_T_Send (Pkt);
T.Packet_T_Send (Pkt);
T.Packet_T_Send (Pkt);  -- This one triggers Recv_Async_Dropped
```

## 20. Anti-Patterns (What NOT to Do)

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
15. Do NOT use `(Value => 1)` for command args with custom record/enum types -- use `(others => <>)` or the correct field names. For Invalid_Command tests the arg doesn't matter (length is corrupted), but it must compile.
14. Do NOT leave `Dispatch_Event` calls in tester overrides for Event.T connectors that carry forwarded/external events. When a component has a non-component Event.T send connector (e.g., `Filtered_Event_T_Send`), the generated tester calls `Self.Dispatch_Event(Arg)` on it. Forwarded events have arbitrary IDs outside the local enum range, causing `CONSTRAINT_ERROR`. Fix: edit tester .adb to remove the `Dispatch_Event` call, keep only `Self.Filtered_Event_T_Recv_Sync_History.Push(Arg);`.
