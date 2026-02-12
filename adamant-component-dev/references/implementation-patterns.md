# Adamant Ada Implementation Patterns

Patterns extracted from reading 10 diverse component implementations. This is the "Adamant way" of writing component Ada code.

## Generated Infrastructure API

All connector sends use `_If_Connected` -- never assume a connector is wired:
```ada
Self.Event_T_Send_If_Connected (Self.Events.Something_Happened (The_Time, Arg));
Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Current_Value (The_Time, (Value => X)));
Self.Command_Response_T_Send_If_Connected (Self.Command_Response_T_Send (Cmd_Header, Status));
```

Get time once per operation, reuse for consistency:
```ada
The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
```

Every async connector has a `*_Dropped` handler (default `is null`).

## Instance Record Organization

```ada
type Instance is new Base_Instance with record
   -- Configuration (from Init)
   Max_Count : Natural := 0;
   Send_Event_On_Missing : Boolean := True;
   -- Core state
   Table : Router_Table.Instance;
   -- Protected state (thread-safe counters/flags)
   Counter : Protected_U16_Counter.Counter;
   Entries : Protected_Event_Filter_Entries;
   -- Shadow variables (change detection for data products)
   Last_Count : Natural := 0;
   -- Computed constants
   Table_Length : Natural := 0;
end record;
```

## Init / Set_Up / Final Lifecycle

- **Init**: Takes configuration, allocates structures, validates constraints, stores config in Instance
- **Set_Up**: Called after all components initialized and tasks started. Sends initial data products, performs connector communications (e.g., command registration)
- **Final**: Destroys internal structures, deallocates memory, nulls access types

```ada
-- Set_Up example: command_router registers with all connected components
for Index in Self.Connector_Command_T_Send'Range loop
   if Self.Is_Command_T_Send_Connected (Index) then
      Self.Command_T_Send_If_Connected (Command_T_Send_Index (Index), Reg_Cmd);
   end if;
end loop;
```

## Command Handler Pattern

Validate first, send specific error events per failure mode, return status:
```ada
overriding function My_Command_Execute (Self : in out Instance; Arg : in My_Arg.T) return Command_Execution_Status.E is
   use Command_Execution_Status;
   The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
begin
   if not Is_Valid (Arg) then
      Self.Event_T_Send_If_Connected (Self.Events.Invalid_Argument (The_Time, Arg));
      return Failure;
   end if;
   -- Perform operation
   Self.Event_T_Send_If_Connected (Self.Events.Command_Succeeded (The_Time));
   return Success;
end My_Command_Execute;
```

## Thread Safety: Protected Object Wrapper

Wrap unprotected data structures in thin protected objects:
```ada
protected type Protected_Database is
   procedure Init (Min_Id : Data_Product_Id; Max_Id : Data_Product_Id);
   function Fetch (Id : Data_Product_Id) return Fetch_Result;
   procedure Update (Dp : Data_Product.T);
private
   Db : Data_Product_Database.Instance;  -- Unprotected inner package
end Protected_Database;
```

## Change Detection for Data Products

Only send data products when values actually change (reduce bus traffic):
```ada
Num_Filtered : constant Natural := Self.Entries.Get_Filtered_Count;
if Num_Filtered /= Self.Last_Filtered_Count then
   Self.Last_Filtered_Count := Num_Filtered;
   Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Total_Filtered (The_Time, (Value => Num_Filtered)));
end if;
```

## Active Component: Cycle Override

For periodic behavior with precise timing (instead of async queue processing):
```ada
overriding procedure Cycle (Self : in out Instance) is
begin
   delay until Self.Next_Period;
   Self.Tick_T_Send ((Time => Self.Sys_Time_T_Get, Count => Self.Count));
   Self.Count := @ + 1;
   Self.Next_Period := @ + Self.Period;
end Cycle;
```

## Parameter Management Hooks

Three-stage parameter lifecycle (generated signatures, developer fills in):
```ada
-- 1. Validate parameter combination (return Valid or Invalid)
overriding function Validate_Parameters (Self : in out Instance;
   P_Gain : Packed_F32.U; I_Gain : Packed_F32.U; ...) return Parameter_Validation_Status.E
is (Parameter_Validation_Status.Valid);  -- Default: accept all

-- 2. Post-update action (apply new parameters to algorithm state)
overriding procedure Update_Parameters_Action (Self : in out Instance) is null;  -- Default: no-op
```

## Memory Region Overlay (Zero-Copy)

Access byte arrays without copying using address overlays:
```ada
subtype Safe_Byte_Array is Byte_Array (0 .. Self.Table_Length - 1);
Overlay : Safe_Byte_Array with Import, Convention => Ada, Address => Region.Address;
```

## Dynamic Allocation with Safe Cleanup

```ada
-- Allocate in Init
Self.Engines := new Engine_Array (Id'First .. Id'First + Num - 1);

-- Cleanup in Final (Safe_Deallocator only frees in test builds)
procedure Free is new Safe_Deallocator.Deallocate_If_Testing (Engine_Array, Engine_Array_Access);
Free (Self.Engines);
Self.Engines := null;
```

## Status Enum Pattern

Internal operations return detailed status enums that drive event/response behavior:
```ada
type Fetch_Status is (Success, Data_Not_Available, Id_Out_Of_Range);
type Check_Status is (Disable, Petting, Warn_Failure, Fault_Failure, Repeat_Failure);

case Status is
   when Disable | Petting => null;
   when Warn_Failure =>
      Self.Event_T_Send_If_Connected (Self.Events.Pet_Limit_Exceeded (Time, (Index => Idx)));
   when Fault_Failure =>
      Self.Send_Fault (Idx, Time);
   when Repeat_Failure => null;
end case;
```

## Binary Tree for O(log n) Lookups

Complex components instantiate generic binary trees instead of linear search:
```ada
package Lookup_Tree is new Binary_Tree (Lookup_Entry, Less_Than, Greater_Than);
-- Search returns found entry and index
Found : constant Boolean := Self.Tree.Search (Query, Result, Ignore_Index);
```

## Service Connector (Synchronous Request-Response)

```ada
overriding function Data_Product_Fetch_T_Service (Self : in out Instance;
   Arg : in Data_Product_Fetch.T) return Data_Product_Return.T
```

Returns value immediately rather than sending response via separate connector.
