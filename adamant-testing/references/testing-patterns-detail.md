## Component Type Testing Patterns

Core patterns (lifecycle, commands, async dispatch, data dependencies) are in SKILL.md. This file has extended examples.

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
T.Expect_Data_Product_T_Send_Dropped := False;  -- Reset for next test
```

### Data Dependency Mock Implementation (Full Example)

```ada
overriding function Data_Product_Fetch_T_Service (Self : in out Instance;
   Arg : in Data_Product_Fetch.T) return Data_Product_Return.T is
   Status : Data_Product_Enums.Fetch_Status.E := Self.Data_Dependency_Return_Status_Override;
   Buffer : Data_Product_Types.Data_Product_Buffer_Type;
begin
   if Status = Success then
      case Arg.Id is
         when 0 =>
            Buffer (Buffer'First .. Buffer'First + Sensor_Data.Size_In_Bytes - 1) :=
               Sensor_Data.Serialization.To_Byte_Array (Self.Sensor_Reading);
         when others =>
            Status := Id_Out_Of_Range;
      end case;
   end if;
   return (
      The_Status => Status,
      The_Data_Product => (
         Header => (Time => Self.System_Time, Id => Arg.Id, Buffer_Length => expected_length),
         Buffer => Buffer));
end Data_Product_Fetch_T_Service;
```
