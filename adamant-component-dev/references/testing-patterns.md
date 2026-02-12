# Adamant Testing Patterns

Patterns from real component test implementations. Use these to write correct Adamant tests the first time.

## Test Setup (Every Component Test)

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base (Queue_Size => 10 * Self.Tester.Component_Instance.Get_Max_Queue_Element_Size);
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Init (param1 => value1);
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;

overriding procedure Tear_Down_Test (Self : in out Instance) is
begin
   Self.Tester.Final_Base;
end Tear_Down_Test;
```

## Tester Alias Convention

```ada
T : Component.{Name}.Implementation.Tester.Instance_Access renames Self.Tester;
```

## History API (Core Testing Mechanism)

All tester outputs are captured in history objects. Always check count first, then content:

```ada
-- Check event count
Natural_Assert.Eq (T.Event_T_Recv_Sync_History.Get_Count, 1);
-- Check event content (1-indexed)
Command_Header_Assert.Eq (T.Command_Received_History.Get (1), expected_header);
-- Verify nothing unexpected
Boolean_Assert.Eq (T.Error_Event_History.Is_Empty, True);
-- Clear between test phases
T.Event_T_Recv_Sync_History.Clear;
```

## Async vs Sync Testing

**Sync connectors**: results available immediately after send.
**Async connectors**: must dispatch the queue first:

```ada
T.Command_T_Send (some_command);                    -- Send async
Natural_Assert.Eq (Self.Tester.Dispatch_All, 1);    -- Process queue (returns msg count)
Natural_Assert.Eq (T.Command_Response_History.Get_Count, 1);  -- Now check results
```

## Command Testing

```ada
-- Send command
T.Command_T_Send (T.Commands.Set_Value ((Value => 42)));
-- Verify response
Command_Response_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get (1),
   (Source_Id => 0, Registration_Id => 1, Command_Id => T.Commands.Get_Set_Value_Id, Status => Success));
```

## Data Product Testing

```ada
T.Control_Input_U_Send (input_data);
Natural_Assert.Eq (T.P_Output_History.Get_Count, 1);
Packed_F32_Assert.Eq (T.P_Output_History.Get (1), (Value => expected));
```

## Parameter Testing

```ada
-- Stage
Status := Self.Tester.Stage_Parameter (Self.Tester.Parameters.P_Gain ((Value => 1.0)));
Parameter_Update_Status_Assert.Eq (Status, Success);
-- Apply all staged
Parameter_Update_Status_Assert.Eq (Self.Tester.Update_Parameters, Success);
-- Fetch to verify
Status := Self.Tester.Fetch_Parameter (Self.Tester.Parameters.Get_P_Gain_Id, Param);
```

## Error Injection

```ada
-- Test dropped messages
T.Expect_Command_T_Send_Dropped := True;
T.Command_T_Send (some_command);
Natural_Assert.Eq (T.Command_T_Send_Dropped_Count, 1);

-- Test invalid inputs
Cmd.Header.Arg_Buffer_Length := 0;
T.Command_T_Send (Cmd);
-- Verify Length_Error response
```

## Floating Point Assertions

```ada
Short_Float_Assert.Eq (T.Mean_History.Get (1).Value, 1.0, Epsilon => 0.001);
```

## Custom Enum Assertions

```ada
package State_Assert is new Smart_Assert.Discrete (My_State.E, My_State.E'Image);
State_Assert.Eq (T.State_History.Get (1).State, My_State.Enabled);
```

## Key Rules

1. Always `Dispatch_All` for async connectors before checking results
2. Check history count before accessing entries (avoids constraint errors)
3. Clear histories between test phases to prevent pollution
4. Test both success AND failure paths for every command
5. Test queue overflow, invalid IDs, wrong argument lengths
6. Use `T` alias convention for readability
