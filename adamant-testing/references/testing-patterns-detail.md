## Component Type Testing Patterns

### Command Component Testing

```ada
-- Send commands via tester helpers
T.Command_T_Send (T.Commands.Set_Value ((Value => 42)));
T.Command_T_Send (T.Commands.No_Arg_Command);

-- Verify responses
Natural_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get_Count, 1);
Command_Response_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get (1), (
   Source_Id => 0,
   Registration_Id => expected_reg_id,
   Command_Id => T.Commands.Get_Set_Value_Id,  -- ID getter
   Status => Success
));

-- Test both success and failure paths
T.Command_T_Send (T.Commands.Set_Value ((Value => 999)));  -- Invalid
-- Verify Failure response...
```

### Event Component Testing

```ada
-- Send stimuli
T.Tick_T_Send ((Time => (0, 0), Count => 0));

-- Check total events and specific types
Natural_Assert.Eq (T.Event_T_Recv_Sync_History.Get_Count, 2);
Natural_Assert.Eq (T.First_Tick_Event_History.Get_Count, 1);
Natural_Assert.Eq (T.Regular_Tick_Event_History.Get_Count, 1);

-- Verify event parameters
Tick_Assert.Eq (T.Regular_Tick_Event_History.Get (1), expected_tick_param);
```

### Active Component Testing

```ada
-- Send to async connectors (queued)
T.Async_Data_Send (data1);
T.Async_Data_Send (data2);

-- Nothing in output histories yet
Natural_Assert.Eq (T.Output_History.Get_Count, 0);

-- Process queue (returns number processed)
Natural_Assert.Eq (T.Dispatch_All, 2);

-- Now check outputs
Natural_Assert.Eq (T.Output_History.Get_Count, 2);
-- Verify outputs...

-- Multiple dispatch cycles for incremental processing
T.Async_Data_Send (data3);
Natural_Assert.Eq (T.Dispatch_All, 1);  -- One more processed
```

## Error Injection and Edge Case Testing

### Queue Overflow Testing

```ada
-- Fill queue to capacity
T.Async_Data_Send (data1);
T.Async_Data_Send (data2);
T.Async_Data_Send (data3);  -- At capacity

-- Enable dropped message expectation
T.Expect_Async_Data_Send_Dropped := True;

-- This should overflow but not fail test
T.Async_Data_Send (data4);

-- Verify drop was recorded
Natural_Assert.Eq (T.Async_Data_Send_Dropped_Count, 1);
```

### Invalid Command Testing

```ada
-- Test wrong argument length
Invalid_Cmd : Command.T := T.Commands.Set_Value ((Value => 0));
Invalid_Cmd.Header.Arg_Buffer_Length := 0;  -- Wrong length
T.Command_T_Send (Invalid_Cmd);

-- Verify Length_Error response
Command_Response_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get (1), (
   Source_Id => 0,
   Registration_Id => expected_reg_id,
   Command_Id => T.Commands.Get_Set_Value_Id,
   Status => Length_Error
));
```

### Custom Error Injection

```ada
-- For any Send connector, tester provides Expect_*_Dropped
T.Expect_Data_Product_T_Send_Dropped := True;
-- Component tries to send, tester captures drop instead of asserting failure
-- Reset for next test:
T.Expect_Data_Product_T_Send_Dropped := False;
```

## Data Dependency Testing

For components with data dependencies (common in algorithm wrappers):

### Data Dependency Mock Setup

```ada
-- Tester provides override fields for mocking
type Instance is new Component.Algorithm_Component_Reciprocal.Base_Instance with record
   -- Mock data values
   Sensor_Reading : Sensor_Data.T;
   Reference_Data : Reference.T;
   
   -- Mock return conditions
   Data_Dependency_Return_Status_Override : Data_Product_Enums.Fetch_Status.E := Success;
   Data_Dependency_Return_Id_Override : Data_Product_Types.Data_Product_Id := 0;
   Data_Dependency_Return_Length_Override : Data_Product_Types.Data_Product_Buffer_Length_Type := 0;
   Data_Dependency_Timestamp_Override : Sys_Time.T := (0, 0);
end record;
```

### Data Dependency Mock Implementation

```ada
overriding function Data_Product_Fetch_T_Service (Self : in out Instance; Arg : in Data_Product_Fetch.T) return Data_Product_Return.T is
   Status : Data_Product_Enums.Fetch_Status.E := Self.Data_Dependency_Return_Status_Override;
   Buffer : Data_Product_Types.Data_Product_Buffer_Type;
begin
   -- Use overrides or defaults
   if Status = Success then
      case Arg.Id is
         when 0 => -- Sensor_Reading dependency
            Buffer (Buffer'First .. Buffer'First + Sensor_Data.Size_In_Bytes - 1) :=
               Sensor_Data.Serialization.To_Byte_Array (Self.Sensor_Reading);
         when 1 => -- Reference_Data dependency  
            Buffer (Buffer'First .. Buffer'First + Reference.Size_In_Bytes - 1) :=
               Reference.Serialization.To_Byte_Array (Self.Reference_Data);
         when others =>
            Status := Id_Out_Of_Range;
      end case;
   end if;
   
   return (
      The_Status => Status,
      The_Data_Product => (
         Header => (Time => Self.System_Time, Id => Arg.Id, Buffer_Length => expected_length),
         Buffer => Buffer
      )
   );
end Data_Product_Fetch_T_Service;
```

### Data Dependency Test Scenarios

```ada
-- Test with fresh data
T.Sensor_Reading := (Value => 1.0, Quality => Good);
T.System_Time := (100, 0);  -- Current time
T.Tick_T_Send ((Time => (100, 0), Count => 0));
-- Verify algorithm processes data...

-- Test with stale data
T.Data_Dependency_Timestamp_Override := (50, 0);  -- Old timestamp
T.Tick_T_Send ((Time => (100, 0), Count => 0));
-- Verify algorithm reports stale data...

-- Test with missing data
T.Data_Dependency_Return_Status_Override := Id_Out_Of_Range;
T.Tick_T_Send ((Time => (100, 0), Count => 0));
-- Verify algorithm handles missing dependency...
```

