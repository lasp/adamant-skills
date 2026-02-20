<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Assertion Patterns

Extended testing patterns and with-clause sets. Basic assertion patterns are in SKILL.md.

---

## Common With-Clause Sets

### Minimal (passive, no commands, basic DPs)
```ada
with Basic_Assertions; use Basic_Assertions;
with Packed_U32.Assertion; use Packed_U32.Assertion;
```

### With commands and parameters
```ada
with Command_Enums;
with Parameter_Enums;
use type Command_Enums.Command_Response_Status.E;
use type Parameter_Enums.Parameter_Update_Status.E;
```

### With loop counters and custom types
```ada
with Interfaces; use Interfaces;
with Sys_Time;
with Packed_F32.Assertion; use Packed_F32.Assertion;
with Packed_Byte.Assertion; use Packed_Byte.Assertion;
```

### With custom project types (for Pack/Unpack)
```ada
with Thruster_Command;
with Monitor_State;
with Packed_Monitor_State.Assertion; use Packed_Monitor_State.Assertion;
```

---

## Extended Testing Patterns

### Custom Packed Type Construction
```ada
-- Pack unpacked record to packed type for sending
Cmd : constant Thruster_Command.U := (
   Thruster_Id => (Value => 1),
   Thrust_Magnitude => (Value => 10.0),
   Duration_Ms => (Value => 500));
T.Thruster_Command_T_Send (Thruster_Command.Pack (Cmd));
```

### History Overflow Management
```ada
-- Clear periodically in long loops (history depth = 100)
for I in 1 .. 90 loop
   T.Tick_T_Send ((Time => (0, 0), Count => Unsigned_32 (I)));
   if I mod 40 = 0 then
      T.Data_Product_T_Recv_Sync_History.Clear;
      T.Output_History.Clear;
   end if;
end loop;
```

### Multiple Connector Testing
```ada
-- Named command connectors generate _Send, _Send_2, etc.
T.Command_T_Send (cmd);     -- First command connector  
T.Command_T_Send_2 (cmd2);  -- Second command connector
```