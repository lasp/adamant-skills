<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Adamant Ada Implementation Patterns

Patterns extracted from 10 diverse component implementations.

## Instance Record Organization

```ada
type Instance is new Base_Instance with record
   -- Configuration (from Init)
   Max_Count : Natural := 0;
   -- Core state
   Table : Router_Table.Instance;
   -- Protected state (thread-safe)
   Counter : Protected_U16_Counter.Counter;
   -- Shadow variables (change detection)
   Last_Count : Natural := 0;
end record;
```

## Init / Set_Up / Final Lifecycle

- **Init**: Configuration, allocation, validation. Store config in Instance.
- **Set_Up**: Called after all components wired and started. Send initial data products, command registration.
- **Final**: Destroy structures, deallocate, null access types.

## Command Handler: Validate-Then-Act

```ada
overriding function My_Command (Self : in out Instance; Arg : in My_Arg.T)
   return Command_Execution_Status.E is
   use Command_Execution_Status;
   The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
begin
   if not Is_Valid (Arg) then
      Self.Event_T_Send_If_Connected (Self.Events.Invalid_Argument (The_Time, Arg));
      return Failure;
   end if;
   -- Perform operation, send success event
   return Success;
end My_Command;
```

## Thread Safety: Protected Object Wrapper

```ada
protected type Protected_Database is
   procedure Init (Min_Id : Data_Product_Id; Max_Id : Data_Product_Id);
   function Fetch (Id : Data_Product_Id) return Fetch_Result;
   procedure Update (Dp : Data_Product.T);
private
   Db : Data_Product_Database.Instance;
end Protected_Database;
```

## Change Detection for Data Products

Only send when values change (reduce bus traffic):
```ada
if Num_Filtered /= Self.Last_Filtered_Count then
   Self.Last_Filtered_Count := Num_Filtered;
   Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Total_Filtered (The_Time, (Value => Num_Filtered)));
end if;
```

## Status Enum Pattern

Return detailed status enums that drive event/response behavior:
```ada
type Check_Status is (Disable, Petting, Warn_Failure, Fault_Failure, Repeat_Failure);
case Status is
   when Disable | Petting => null;
   when Warn_Failure => Self.Event_T_Send_If_Connected (...);
   when Fault_Failure => Self.Send_Fault (Idx, Time);
   when Repeat_Failure => null;
end case;
```

## Memory Region Overlay (Zero-Copy)

```ada
subtype Safe_Byte_Array is Byte_Array (0 .. Self.Table_Length - 1);
Overlay : Safe_Byte_Array with Import, Convention => Ada, Address => Region.Address;
```

## Dynamic Allocation with Safe Cleanup

```ada
Self.Engines := new Engine_Array (Id'First .. Id'First + Num - 1);  -- In Init
-- In Final:
procedure Free is new Safe_Deallocator.Deallocate_If_Testing (Engine_Array, Engine_Array_Access);
Free (Self.Engines); Self.Engines := null;
```

## Binary Tree for O(log n) Lookups

```ada
package Lookup_Tree is new Binary_Tree (Lookup_Entry, Less_Than, Greater_Than);
Found : constant Boolean := Self.Tree.Search (Query, Result, Ignore_Index);
```

## Target Hardware Abstraction

Same interface, target-specific body via build path:
```
component/
├── hardware_action.ads            # Shared spec
├── linux/hardware_action.adb      # Dev no-op (.Linux_path)
└── pico/hardware_action.adb       # Real hardware (.Pico_path)
```
