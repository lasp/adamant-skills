<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Assertion Patterns

History API verification, packed type assertions, Smart_Assert usage, and with-clause sets.

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

Source: pid_controller. Typed histories are named `{dp_name}_History`.
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

Source: health_aggregator, mode_manager. When exact count depends
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

Source: pid_controller, heartbeat_monitor. Explicitly verify that
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
Natural_Assert.Eq (T.Fault_T_Recv_Sync_History.Get_Count, 0);

-- 11th crosses threshold:
T.Packet_T_Send (Pkt);
Natural_Assert.Ge (T.Fault_T_Recv_Sync_History.Get_Count, 1);
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

Source: pid_controller. Clear both raw AND typed histories when
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


## 17. Assertion Style Patterns

### 17a. Typed assertions (preferred)

```ada
Packed_U32_Assert.Eq (T.Tick_Count_History.Get (5), (Value => 5));
Packed_F32_Assert.Eq (T.Output_History.Get (1), (Value => 3.0));
Packed_Byte_Assert.Eq (T.Heartbeat_State_History.Get (1), (Value => 0));
```

Source: uptime_counter, pid_controller, heartbeat_monitor.
Type-safe, clear error messages.

### 17b. AUnit Assert (acceptable alternative)

```ada
Assert (T.Switch_State_History.Get (1).Value = Unsigned_8'(1), "Should be ON");
```

Source: power_switch. Works but less precise error messages. Requires
`with AUnit.Assertions; use AUnit.Assertions;`.

### 17c. Smart_Assert for simple checks

```ada
Natural_Assert.Eq (T.Packet_T_Recv_Sync_History.Get_Count, 1);
Command_Response_Status_Assert.Eq (
   T.Command_Response_T_Recv_Sync_History.Get (1).Status,
   Command_Enums.Command_Response_Status.Success);
```

Source: telemetry_filter. Use typed Smart_Assert calls even for simple checks --
they print both expected and actual values on failure. Requires:
`with Command_Enums.Assertion; use Command_Enums.Assertion;`

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

## Extended Testing Patterns

### Invalid Command Testing

#### Pattern: Corrupt arg buffer length
```ada
declare
   Cmd : Command.T := T.Commands.Set_Value
      (T.Command_T_Send_2_Id_With_Offset, (Value => 0));
begin
   Cmd.Header.Arg_Buffer_Length := 22;  -- Wrong length
   T.Command_T_Send_2 (Cmd);
   -- For active components, dispatch:
   Natural_Assert.Eq (T.Dispatch_All, 1);
   -- Verify Invalid_Command_Received event
   Natural_Assert.Eq (T.Invalid_Command_Received_History.Get_Count, 1);
end;
```

#### Pattern: Unknown command ID
```ada
declare
   Cmd : Command.T := (Header => (Id => 999,
      Arg_Buffer_Length => 0, others => <>), others => <>);
begin
   T.Command_T_Send_2 (Cmd);
   -- Dispatch and check for command failure response
end;
```

### Send_Dropped Testing

#### Pattern: Using Expect flag
```ada
-- Tell tester to expect drops instead of asserting failure
T.Expect_Data_Product_T_Send_Dropped := True;
-- Trigger action that sends a data product
T.Tick_T_Send ((Time => (0, 0), Count => 1));
-- Verify drop was captured
Natural_Assert.Eq (T.Data_Product_T_Send_Dropped_History.Get_Count, 1);
-- Reset for subsequent tests
T.Expect_Data_Product_T_Send_Dropped := False;
```

#### Pattern: Skip connector attach
```ada
-- Alternative: don't call Attach on the connector during setup
-- Then any send on that connector triggers the dropped handler
-- This requires modifying the tester's Connect procedure
```

### Recv_Async_Dropped Testing

#### Pattern: Queue overflow
```ada
-- For active components with small queue
-- Send more messages than queue can hold
for I in 1 .. Queue_Size + 1 loop
   T.Packet_T_Send ((Header => (others => <>), Buffer => [others => 0]));
end loop;
-- The overflow triggers Recv_Async_Dropped handler
-- Check event or counter
```

### Data Dependency Mocking

#### Full mock implementation
```ada
overriding function Data_Product_Fetch_T_Service (Self : in out Instance;
   Arg : in Data_Product_Fetch.T) return Data_Product_Return.T is
   Status : Data_Product_Enums.Fetch_Status.E := Self.Fetch_Status_Override;
   Buffer : Data_Product_Types.Data_Product_Buffer_Type := [others => 0];
begin
   if Status = Data_Product_Enums.Fetch_Status.Success then
      case Arg.Id is
         when 0 =>
            Buffer (Buffer'First .. Buffer'First +
               Sensor_Data.Size_In_Bytes - 1) :=
               Sensor_Data.Serialization.To_Byte_Array (Self.Sensor_Value);
         when others =>
            Status := Data_Product_Enums.Fetch_Status.Id_Out_Of_Range;
      end case;
   end if;
   return (The_Status => Status,
           The_Data_Product => (Header => (
              Time => Self.System_Time,
              Id => Arg.Id,
              Buffer_Length => Sensor_Data.Size_In_Bytes),
              Buffer => Buffer));
end Data_Product_Fetch_T_Service;
```

#### Testing fetch failure
```ada
-- Override tester to return failure
T.Fetch_Status_Override := Data_Product_Enums.Fetch_Status.Id_Out_Of_Range;
T.Tick_T_Send ((Time => (0, 0), Count => 1));
-- Component should handle fetch failure gracefully
-- Check for error event or fallback behavior
T.Fetch_Status_Override := Data_Product_Enums.Fetch_Status.Success;  -- Reset
```

### Parameter Testing

#### Full three-step flow
```ada
declare
   Status : Command_Execution_Status.E;
   use Command_Execution_Status;
begin
   -- 1. Stage new parameter value
   T.Parameters.Set_Max_Threshold ((Value => 100));
   T.Parameters.Stage (T.Command_T_Send_2_Id_With_Offset, Status);
   Command_Execution_Status_Assert.Eq (Status, Success);
   -- For active: dispatch stage command
   Natural_Assert.Eq (T.Dispatch_All, 1);

   -- 2. Validate
   T.Parameters.Validate (T.Command_T_Send_2_Id_With_Offset, Status);
   Command_Execution_Status_Assert.Eq (Status, Success);
   Natural_Assert.Eq (T.Dispatch_All, 1);

   -- 3. Update (applies the parameter)
   T.Parameters.Update (T.Command_T_Send_2_Id_With_Offset, Status);
   Command_Execution_Status_Assert.Eq (Status, Success);
   Natural_Assert.Eq (T.Dispatch_All, 1);

   -- 4. Tick to use new parameter
   T.Tick_T_Send ((Time => (0, 0), Count => 1));
   Natural_Assert.Eq (T.Dispatch_All, 1);
   -- Verify component behavior changed with new parameter
end;
```

#### Parameter validation failure
```ada
-- Set an out-of-range value and verify validation rejects it
T.Parameters.Set_Max_Threshold ((Value => 0));  -- Invalid value
T.Parameters.Stage (T.Command_T_Send_2_Id_With_Offset, Status);
T.Parameters.Validate (T.Command_T_Send_2_Id_With_Offset, Status);
Command_Execution_Status_Assert.Eq (Status, Command_Execution_Status.Failure);
```

### Fault Testing

#### Triggering a fault
```ada
-- Set conditions that trigger the fault
T.Tick_T_Send ((Time => (0, 0), Count => 1));
-- Check fault was sent
Natural_Assert.Eq (T.Fault_T_Recv_Sync_History.Get_Count, 1);
-- Verify fault ID
declare
   F : constant Fault.T := T.Fault_T_Recv_Sync_History.Get (1);
begin
   -- Check fault header fields
   Natural_Assert.Eq (Natural (F.Header.Id), Expected_Fault_Id);
end;
```

#### Fault cleared after condition resolves
```ada
-- Trigger fault condition
-- ...
-- Clear fault condition
-- Tick again
T.Tick_T_Send ((Time => (0, 0), Count => 2));
-- Verify no additional fault sent
Natural_Assert.Eq (T.Fault_T_Recv_Sync_History.Get_Count, 1);  -- Still 1
```

### Coverage-Specific Patterns

#### Testing all branches of a case statement
```ada
-- If component has: case Mode is when A => ... when B => ... when C => ...
-- Test each mode:
T.Command_T_Send_2 (T.Commands.Set_Mode
   (T.Command_T_Send_2_Id_With_Offset, (Mode => Mode_Type.A)));
-- Tick and verify A behavior

T.Command_T_Send_2 (T.Commands.Set_Mode
   (T.Command_T_Send_2_Id_With_Offset, (Mode => Mode_Type.B)));
-- Tick and verify B behavior
-- etc.
```

#### Testing boundary values
```ada
-- For range checks: test at boundaries
-- If threshold is 100:
T.Set_Input_Value (99);   -- Just below
T.Tick_T_Send (...);
-- Verify below-threshold behavior

T.Set_Input_Value (100);  -- At threshold
T.Tick_T_Send (...);
-- Verify at-threshold behavior

T.Set_Input_Value (101);  -- Just above
T.Tick_T_Send (...);
-- Verify above-threshold behavior
```

#### Clearing histories between test phases
```ada
-- CRITICAL: clear BOTH raw AND typed histories
T.Event_T_Recv_Sync_History.Clear;
T.Data_Product_T_Recv_Sync_History.Clear;
T.Status_Updated_History.Clear;        -- Typed history
T.Mode_Changed_History.Clear;          -- Typed history
-- Now counts reset to 0 for next phase
```

### Active Component Patterns

#### Async dispatch with multiple messages
```ada
-- Send 3 packets
T.Packet_T_Send (Pkt_1);
T.Packet_T_Send (Pkt_2);
T.Packet_T_Send (Pkt_3);
-- Dispatch all 3
Natural_Assert.Eq (T.Dispatch_All, 3);
-- All 3 now processed, check results
```

#### Mixed async connector dispatch
```ada
-- Send on two different async connectors
T.Command_T_Send (Cmd);
T.Packet_T_Send (Pkt);
-- Both queued, dispatch both
Natural_Assert.Eq (T.Dispatch_All, 2);
```

---

