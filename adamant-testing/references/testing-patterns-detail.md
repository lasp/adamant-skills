# Testing Patterns -- Detailed Reference

Core patterns (lifecycle, commands, async dispatch, data dependencies) are in SKILL.md. This file has extended examples for every coverage-critical pattern.

---

## 1. Invalid Command Testing

### Pattern: Corrupt arg buffer length
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

### Pattern: Unknown command ID
```ada
declare
   Cmd : Command.T := (Header => (Id => 999,
      Arg_Buffer_Length => 0, others => <>), others => <>);
begin
   T.Command_T_Send_2 (Cmd);
   -- Dispatch and check for command failure response
end;
```

---

## 2. Send_Dropped Testing

### Pattern: Using Expect flag
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

### Pattern: Skip connector attach
```ada
-- Alternative: don't call Attach on the connector during setup
-- Then any send on that connector triggers the dropped handler
-- This requires modifying the tester's Connect procedure
```

---

## 3. Recv_Async_Dropped Testing

### Pattern: Queue overflow
```ada
-- For active components with small queue
-- Send more messages than queue can hold
for I in 1 .. Queue_Size + 1 loop
   T.Packet_T_Send ((Header => (others => <>), Buffer => [others => 0]));
end loop;
-- The overflow triggers Recv_Async_Dropped handler
-- Check event or counter
```

---

## 4. Data Dependency Mocking

### Full mock implementation
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

### Testing fetch failure
```ada
-- Override tester to return failure
T.Fetch_Status_Override := Data_Product_Enums.Fetch_Status.Id_Out_Of_Range;
T.Tick_T_Send ((Time => (0, 0), Count => 1));
-- Component should handle fetch failure gracefully
-- Check for error event or fallback behavior
T.Fetch_Status_Override := Data_Product_Enums.Fetch_Status.Success;  -- Reset
```

---

## 5. Parameter Testing

### Full three-step flow
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

### Parameter validation failure
```ada
-- Set an out-of-range value and verify validation rejects it
T.Parameters.Set_Max_Threshold ((Value => 0));  -- Invalid value
T.Parameters.Stage (T.Command_T_Send_2_Id_With_Offset, Status);
T.Parameters.Validate (T.Command_T_Send_2_Id_With_Offset, Status);
Command_Execution_Status_Assert.Eq (Status, Command_Execution_Status.Failure);
```

---

## 6. Fault Testing

### Triggering a fault
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

### Fault cleared after condition resolves
```ada
-- Trigger fault condition
-- ...
-- Clear fault condition
-- Tick again
T.Tick_T_Send ((Time => (0, 0), Count => 2));
-- Verify no additional fault sent
Natural_Assert.Eq (T.Fault_T_Recv_Sync_History.Get_Count, 1);  -- Still 1
```

---

## 7. Coverage-Specific Patterns

### Testing all branches of a case statement
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

### Testing boundary values
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

### Clearing histories between test phases
```ada
-- CRITICAL: clear BOTH raw AND typed histories
T.Event_T_Recv_Sync_History.Clear;
T.Data_Product_T_Recv_Sync_History.Clear;
T.Status_Updated_History.Clear;        -- Typed history
T.Mode_Changed_History.Clear;          -- Typed history
-- Now counts reset to 0 for next phase
```

---

## 8. Active Component Patterns

### Async dispatch with multiple messages
```ada
-- Send 3 packets
T.Packet_T_Send (Pkt_1);
T.Packet_T_Send (Pkt_2);
T.Packet_T_Send (Pkt_3);
-- Dispatch all 3
Natural_Assert.Eq (T.Dispatch_All, 3);
-- All 3 now processed, check results
```

### Mixed async connector dispatch
```ada
-- Send on two different async connectors
T.Command_T_Send (Cmd);
T.Packet_T_Send (Pkt);
-- Both queued, dispatch both
Natural_Assert.Eq (T.Dispatch_All, 2);
```
