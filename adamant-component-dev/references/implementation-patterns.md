<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
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

The instance record MUST be in the private section of the spec. Public part declares `type Instance is new Base_Instance with private;`.

```ada
-- In private section:
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

### Validate_Parameters with Range Checks

When parameters have valid ranges, override `Validate_Parameters` to enforce them.
The function receives each parameter as an individual `.U` (unpacked) argument.
Return `Invalid` to reject the entire staged set; the framework will NOT apply any
of the staged parameters.

```ada
overriding function Validate_Parameters (Self : in out Instance;
   Gain : in Packed_F32.U;
   Offset : in Packed_F32.U;
   Sample_Rate : in Packed_U16.U) return Parameter_Validation_Status.E
is
   use Parameter_Validation_Status;
begin
   -- .U types are records with .Value field -- use .Value for comparisons
   if Gain.Value < 0.1 or else Gain.Value > 10.0 then
      Self.Event_T_Send_If_Connected (Self.Events.Parameter_Rejected (
         Self.Sys_Time_T_Get, (Id => 0)));  -- Gain out of range
      return Invalid;
   end if;
   if Offset.Value < -100.0 or else Offset.Value > 100.0 then
      Self.Event_T_Send_If_Connected (Self.Events.Parameter_Rejected (
         Self.Sys_Time_T_Get, (Id => 1)));  -- Offset out of range
      return Invalid;
   end if;
   if Sample_Rate.Value < 1 or else Sample_Rate.Value > 1000 then
      Self.Event_T_Send_If_Connected (Self.Events.Parameter_Rejected (
         Self.Sys_Time_T_Get, (Id => 2)));  -- Sample_Rate out of range
      return Invalid;
   end if;
   return Valid;
end Validate_Parameters;
```

Key points:
- Parameter arguments are `.U` (unpacked) types, NOT packed. Use arithmetic directly.
- Return `Invalid` on first failed check (short-circuit). Framework blocks the update.
- Emit rejection events with enough context to identify which parameter failed.
- Cross-parameter constraints (e.g., min < max) also go here.
- The framework comment says "range checking is performed during staging" -- this is
  true only for types with Ada-level range constraints (e.g., a subtype of Integer
  range 1..100). Generic packed types like `Packed_F32.U` (Short_Float) and
  `Packed_U16.U` (Unsigned_16) have no application-level subrange, so staging
  accepts ANY valid value. Use `Validate_Parameters` for application-specific
  bounds on these unconstrained types.

### Update_Parameters_Action with Side Effects

Use `Update_Parameters_Action` to apply new parameter values to internal state
and report current values as data products:

```ada
overriding procedure Update_Parameters_Action (Self : in out Instance) is
   Timestamp : constant Sys_Time.T := Self.Sys_Time_T_Get;
begin
   -- Access parameters via Self.<Param_Name> (returns .U record)
   -- Update internal algorithm state from new parameters
   Self.Current_Gain := Self.Gain.Value;
   Self.Current_Offset := Self.Offset.Value;
   -- Report current parameter values as data products
   Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Current_Gain (
      Timestamp, (Value => Self.Gain.Value)));
   Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Current_Offset (
      Timestamp, (Value => Self.Offset.Value)));
   -- Emit event
   Self.Event_T_Send_If_Connected (Self.Events.Parameters_Applied (Timestamp));
end Update_Parameters_Action;
```

## Memory Region Overlay (Zero-Copy)

Access byte arrays without copying using address overlays:
```ada
subtype Safe_Byte_Array is Byte_Array (0 .. Self.Table_Length - 1);
Overlay : Safe_Byte_Array with Import, Convention => Ada, Address => Region.Address;
```

## Dynamic Allocation with Safe Cleanup

**⚠️ CRITICAL**: Never use `Ada.Unchecked_Deallocation` directly — it violates the Ravenscar `No_Unchecked_Deallocation` restriction. Always use `Safe_Deallocator.Deallocate_If_Testing`, which frees memory in test builds and is a null operation on bareboard targets.

```ada
-- Allocate in Init
Self.Engines := new Engine_Array (Id'First .. Id'First + Num - 1);

-- Cleanup in Final (Safe_Deallocator only frees in test builds)
procedure Free is new Safe_Deallocator.Deallocate_If_Testing (Engine_Array, Engine_Array_Access);
Free (Self.Engines);
Self.Engines := null;
```

## Deserializing Packed Types from Byte Arrays

Use the generated `Serialization.From_Byte_Array` instead of manual byte extraction with `Shift_Left`/`or`:

```ada
-- CORRECT: Use framework serialization
declare
   Id_Packed : constant Packed_U16.T := Packed_U16.Serialization.From_Byte_Array (
      Data (Data'First .. Data'First + 1)
   );
begin
   Table_Id := Parameter_Types.Parameter_Table_Id (Id_Packed.Value);
end;

-- WRONG: Manual byte extraction
Table_Id := Parameter_Types.Parameter_Table_Id (
   Shift_Left (Unsigned_16 (Data (Data'First)), 8) or Unsigned_16 (Data (Data'First + 1))
);
```

Every packed type (`Packed_U16`, `Packed_U32`, custom records, etc.) has a generated `Serialization` child package with `From_Byte_Array` and `To_Byte_Array`. Use these for all serialization/deserialization — they handle endianness correctly and are validated by the framework.

## Standalone Helper Packages

When creating a standalone Ada package with an `Instance` type (e.g., a buffer, state machine, or utility object that lives alongside a component), make the type `tagged limited private` to enable dot-notation method calls:

```ada
-- In spec:
type Instance is tagged limited private;
procedure Create (Self : in out Instance; Size : in Positive);
function Get_Value (Self : in Instance) return Natural;

-- Caller can use dot notation:
Self.Buffer.Create (1024);
Value := Self.Buffer.Get_Value;
```

Without `tagged`, callers must use package-qualified calls: `My_Package.Create (Self.Buffer, 1024)`.

## Assertion Style

Use `pragma Assert` without string messages — place a comment above the assertion instead. String messages consume space in the final binary on embedded targets:

```ada
-- CORRECT: Comment explains, no string in assertion
-- Destinations must not be null:
pragma Assert (Table_Entry.Destinations /= null);

-- WRONG: String message wastes binary space
pragma Assert (Table_Entry.Destinations /= null, "Destinations must not be null.");
```

## Data Product Counter Type

Use `Interfaces.Unsigned_32` for data product counters, not `Natural`. This matches `Packed_U32.T` directly (no type conversion needed) and allows natural wraparound:

```ada
type Instance is new Base_Instance with record
   Packet_Count : Interfaces.Unsigned_32 := 0;  -- CORRECT
   -- Bad_Count : Natural := 0;                  -- WRONG: needs type conversion for DPs
end record;

-- No conversion needed when sending data product:
Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Count (Time, (Value => Self.Packet_Count)));
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

## Data Dependency Pattern

When a component needs data from another component's data products at runtime:

### YAML Setup
```yaml
# component.data_dependencies.yaml
data_dependencies:
  - name: Gyro_Rate
    description: Gyroscope angular rate
    type: My_Angular_Rate.T    # Must match the ACTUAL type, not a similarly-named framework type
```

Requires in component.yaml:
```yaml
connectors:
  - kind: request
    type: Data_Product_Fetch.T
    return_type: Data_Product_Return.T
  - kind: get
    return_type: Sys_Time.T
```

### Generated API (two overloads)
```ada
-- Full form (with timestamp output):
function Get_Gyro_Rate (Self : in out Base_Instance;
   Stale_Reference : in Sys_Time.T;       -- IN: you provide reference time
   Timestamp : out Sys_Time.T;            -- OUT: when data was produced
   Value : out My_Angular_Rate.T)         -- OUT: the fetched value
   return Data_Product_Enums.Data_Dependency_Status.E;

-- Short form (no timestamp):
function Get_Gyro_Rate (Self : in out Base_Instance;
   Stale_Reference : in Sys_Time.T;       -- IN: you provide reference time
   Value : out My_Angular_Rate.T)         -- OUT: the fetched value
   return Data_Product_Enums.Data_Dependency_Status.E;
```

### Usage in Body
```ada
The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
Data : My_Angular_Rate.T;
Status : Data_Product_Enums.Data_Dependency_Status.E;
...
Status := Self.Get_Gyro_Rate (Stale_Reference => The_Time, Value => Data);
if Status = Data_Product_Enums.Data_Dependency_Status.Success then
   -- Use Data
end if;
```

### Required Overrides
```ada
-- Delegation to fetch connector (usually in impl spec):
overriding function Get_Data_Dependency (Self : in out Instance;
   Id : in Data_Product_Types.Data_Product_Id) return Data_Product_Return.T
   is (Self.Data_Product_Fetch_T_Request ((Id => Id)));

-- Error handler (in impl body):
overriding procedure Invalid_Data_Dependency (Self : in out Instance;
   Id : in Data_Product_Types.Data_Product_Id;
   Ret : in Data_Product_Return.T) is
begin
   null;  -- Or log/handle the error
end Invalid_Data_Dependency;
```

### Common Mistakes
- Using a framework type name instead of your project's local type
- Treating Stale_Reference as OUT (it's IN -- you provide the reference time)
- Missing Get_Data_Dependency override in the impl spec
- Missing Invalid_Data_Dependency override in the impl body

## Component Design Archetypes

Common component patterns for mission software. Not framework components -- these are patterns to implement as project-specific components.

### Mode Manager
Command-driven state machine with transition validation. Private enum for modes, command per transition, guard conditions for valid transitions.
```ada
type Mode_Enum is (Safe, Standby, Science, Calibration);
-- Private record field: Current_Mode : Mode_Enum := Safe;
-- Helper: Do_Transition sets mode, increments counter, sends event + DP
-- Each command handler checks Current_Mode guard before calling Do_Transition
-- Safe mode always allowed from any mode (no guard)
```

### Threshold Monitor
Parameterized sensor monitoring with warning/critical levels and hysteresis. Uses parameters for thresholds, data dependencies for sensor input, faults for limit violations.
- Init params or parameters.yaml: warning_high, warning_low, critical_high, critical_low, hysteresis_band
- Data dependency: sensor value from another component's DP
- Faults: over_limit, under_limit
- Events: threshold_crossed, returned_to_nominal

### Signal Filter (Deadband / Moving Average / Hysteresis)
Lightweight passive components with `Input_T_Recv_Sync` + `Tick_T_Recv_Sync` + typed `Output_T_Send`. Init params configure filter behavior (deadband width, window size, on/off thresholds). Process on tick, not on input receipt -- store input, compute on tick, send filtered output.

### Edge Detector
Digital input monitoring. Store previous sample, compare on tick, emit rising/falling edge events. No commands needed -- purely reactive.
