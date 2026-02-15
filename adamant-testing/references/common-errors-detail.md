# Common Test Errors -- Detailed Reference

Summaries are in SKILL.md. This file has extended explanations and fixes for every recurring error.

---

## 1. Connector Errors

### 1a. `type:` instead of `return_type:` on get connectors (100% miss rate)
```yaml
# WRONG:
- type: Sys_Time.T
  kind: get
# RIGHT:
- return_type: Sys_Time.T
  kind: get
```
Get connectors have no input type -- they return a value. The YAML schema rejects `type:` on get connectors.

### 1b. Missing Send_Dropped overrides (~80% miss rate)
Every `send` connector generates a `{Name}_T_Send_Dropped` handler that MUST be overridden in the tester if you want to test drop paths. Without override, the default handler calls `Assert(False)`.
```ada
-- In tester .adb, override:
overriding procedure Event_T_Send_Dropped (Self : in out Instance; Arg : in Event.T) is
begin
   Self.Event_T_Send_Dropped_History.Push (Arg);
end Event_T_Send_Dropped;
```

### 1c. Named send connector histories
A send connector named `Primary_Packet_T_Send` becomes `Primary_Packet_T_Recv_Sync_History` in the tester. The naming follows the reciprocal pattern: sender's "send" becomes receiver's "recv_sync".

### 1d. Dual Command.T connectors (async+sync)
When a component has BOTH `recv_async` for Command.T AND `recv_sync` for Command.T, tester generates `Command_T_Send` (async) and `Command_T_Send_2` (sync). Use `_Send_2` for the component's own commands.

### 1e. Named Event.T send connectors crash on non-component events
Tester's `Dispatch_Event` calls `Local_Event_Id_Type'Val(Evnt.Header.Id)` -- crashes with CONSTRAINT_ERROR on external event IDs that fall outside the component's event enum range. Fix: test DPs/command responses instead of routing histories, or edit tester `.adb` to remove `Dispatch_Event` from named Event.T output handlers.

---

## 2. Test Setup Errors

### 2a. Missing `with` clauses in test body (~70% miss rate)
```ada
-- Sub-agents consistently forget these:
with Tick;           -- for Tick.T literals
with Command;        -- for Command.T construction
with Packet;         -- for Packet.T construction
with Interfaces; use Interfaces;  -- for Unsigned_32 etc.
```
The test spec (generated) doesn't include these. The test body (hand-written) must add them.

### 2b. Wrong Init call
```ada
-- WRONG: Init_Base takes no component params
Self.Tester.Init_Base (My_Param => 42);

-- RIGHT: Init_Base is parameterless (or queue size for active)
Self.Tester.Init_Base;
Self.Tester.Component_Instance.Init (My_Param => 42);
```

### 2c. Wrong setup order
```ada
-- CORRECT order:
Self.Tester.Init_Base;           -- 1. Base init (queue for active)
Self.Tester.Connect;             -- 2. Wire connectors
Self.Tester.Component_Instance.Init (Params);  -- 3. Component init (if YAML has init:)
Self.Tester.Component_Instance.Set_Up;         -- 4. Set_Up (if overridden)
```

### 2d. Calling Dispatch_All on passive component
Passive components have no queue. `Dispatch_All` only exists on active component testers.
```ada
-- WRONG for passive:
Natural_Assert.Eq (T.Dispatch_All, 1);

-- RIGHT for passive: just send, component processes synchronously
T.Tick_T_Send ((Time => (0, 0), Count => 1));
-- Results available immediately
```

---

## 3. Assertion Errors

### 3a. Typed history accumulation (#1 recurring error)
Typed histories (e.g., `T.Status_Updated_History`) accumulate across ALL calls in a test. Raw histories can be cleared but typed histories must be cleared separately.
```ada
-- After first tick:
Natural_Assert.Eq (T.Status_Updated_History.Get_Count, 1);
-- After second tick WITHOUT clearing:
Natural_Assert.Eq (T.Status_Updated_History.Get_Count, 2);  -- NOT 1!

-- To reset:
T.Status_Updated_History.Clear;
```

### 3b. History overflow
Default history size is small (often 10-20 entries). Tests that tick many times overflow it:
```
FAIL: History is full. You may need to enlarge it for this test.
```
Fix: reduce tick count or clear histories between phases.

### 3c. Dispatch_All returns Natural
```ada
-- WRONG: Ada cannot discard function return values
T.Dispatch_All;

-- RIGHT options:
Natural_Assert.Eq (T.Dispatch_All, 1);           -- Check count
Count := T.Dispatch_All;                           -- Capture
Ignore : Natural := T.Dispatch_All;               -- Discard
pragma Unreferenced (Ignore);
```

### 3d. Wrong assertion module
```ada
-- Framework provides nested instantiations:
with Command_Response.Assertion; use Command_Response.Assertion;
-- Then use: Command_Response_Assert.Eq (...)

-- NOT:
with Basic_Assertions;  -- Only for Natural_Assert, Integer_Assert
```

---

## 4. Command Testing Errors

### 4a. Command.T aggregate wrong
```ada
-- WRONG: Arg_Buffer_Length at top level
Cmd : Command.T := (Header => (Id => 1), Arg_Buffer_Length => 0);

-- RIGHT: Arg_Buffer_Length is inside Header
Cmd : Command.T := (Header => (Id => 1, Arg_Buffer_Length => 0), others => <>);
```

### 4b. Invalid_Command test pattern
```ada
-- Corrupt the arg buffer length to trigger invalid command path:
declare
   Cmd : Command.T := T.Commands.Enable (T.Command_T_Send_2_Id_With_Offset);
begin
   Cmd.Header.Arg_Buffer_Length := 22;  -- Wrong length
   T.Command_T_Send_2 (Cmd);
   -- For active: Natural_Assert.Eq (T.Dispatch_All, 1);
end;
```

### 4c. Raw command ID collisions
Component-local command IDs start from 0. When constructing commands manually, use high IDs (100+) to avoid collisions with real component commands.

---

## 5. Parameter Testing Errors

### 5a. Three-step parameter flow
```ada
-- ALL three steps required:
declare
   Status : Command_Execution_Status.E;
begin
   -- Stage
   T.Parameters.Stage (T.Command_T_Send_2_Id_With_Offset, Status);
   Command_Execution_Status_Assert.Eq (Status, Command_Execution_Status.Success);
   -- Validate (for active: dispatch between steps)
   T.Parameters.Validate (T.Command_T_Send_2_Id_With_Offset, Status);
   Command_Execution_Status_Assert.Eq (Status, Command_Execution_Status.Success);
   -- Update
   T.Parameters.Update (T.Command_T_Send_2_Id_With_Offset, Status);
   Command_Execution_Status_Assert.Eq (Status, Command_Execution_Status.Success);
   -- Tick to apply
   T.Tick_T_Send ((Time => (0, 0), Count => 1));
end;
```

### 5b. Validate_Parameters takes individual args
```ada
-- WRONG: combined record
function Validate_Parameters (Self : in out Instance; Params : My_Params.T) return ...

-- RIGHT: individual .U args per parameter
function Validate_Parameters (Self : in out Instance;
   Max_Value : in Packed_U16.U;
   Threshold : in Packed_U32.U) return Command_Execution_Status.E
```

---

## 6. Type and Value Errors

### 6a. Tick.T Count field is Unsigned_32
```ada
-- WRONG:
T.Tick_T_Send ((Time => (0, 0), Count => 1));
-- May work but ambiguous. Explicit:
T.Tick_T_Send ((Time => (0, 0), Count => Unsigned_32'(1)));
```

### 6b. Packed_F32.T.Value is Short_Float
```ada
-- WRONG:
Value : Interfaces.IEEE_Float_32 := My_Dp.Value;

-- RIGHT:
Value : Short_Float := My_Dp.Value;
```

### 6c. Record vs array aggregates
```ada
-- Records use ():
My_Record := (Field_1 => 0, Field_2 => 1);

-- Arrays use []:
My_Array := [1, 2, 3];

-- Nested: array of records
My_Array := [(Field => 0), (Field => 1)];
```

### 6d. Event param types must be static-sized
Variable-length types (Command.T, Packet.T) cannot be event parameters. Use packed types only.

### 6e. No dynamic allocation
Ravenscar profile: use fixed-size arrays, NOT `access` types or `new`.

---

## 7. Data Dependency Errors

### 7a. Request connector tester returns uninitialized data
Tester's `*_T_Service` handler returns default/uninitialized data. Override to set `Fetch_Status.Success`:
```ada
overriding function Sys_Time_T_Return (Self : in out Instance) return Sys_Time.T is
begin
   return (Time => (1, 0));  -- Non-zero time
end Sys_Time_T_Return;
```

### 7b. Change detection needs different values
If component uses change detection (shadow values), first tick may not emit DPs if initial shadow matches computation. Set dependency data to produce DIFFERENT values between ticks.

---

## 8. Build Errors

### 8a. Test dirs: NO `.all_path`
Test directories use `env.py` (importing from `environments.test`), NOT `.all_path`. Having both causes duplicate source conflicts.

### 8b. Stale ALI files hide tester changes
After modifying tester `.ads` files, run `redo clean` in the test dir before recompiling.

### 8c. Unused `with` removal
`use X;` makes operators directly visible. Removing `with X;` breaks those even if GNAT says the `with` is unused. Grep body for types/operators from the package before removing.
