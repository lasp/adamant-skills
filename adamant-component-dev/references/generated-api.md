# Generated Code API Reference


From component YAML, the generator produces these packages (all in `build/src/`):

### Base Class (`Component.{Name}`)

```ada
type Base_Instance is abstract new Component.Core_Instance with private;

-- Init: abstract, signature from init.parameters in YAML
not overriding procedure Init (Self : in out Base_Instance; ...) is abstract;

-- Set_Id_Bases: called by assembly to assign global ID ranges
not overriding procedure Set_Id_Bases (Self : in out Base_Instance;
   Command_Id_Base : Command_Types.Command_Id_Base;
   Data_Product_Id_Base : Data_Product_Types.Data_Product_Id_Base;
   Event_Id_Base : Event_Types.Event_Id_Base;
   Packet_Id_Base : Packet_Types.Packet_Id_Base);

-- Invokee connector primitives: abstract, override in implementation
not overriding procedure {Connector_Name} (Self : in out Base_Instance; Arg : in {Type}.T) is abstract;
-- Hook accessor for wiring:
not overriding function {Connector_Name}_Access (Self : in Base_Instance; ...) return not null {Connector}_Connector.Invokee_Hook;

-- Invoker connector methods (private section, usable by child):
not overriding procedure {Connector}_Send_If_Connected (Self : in out Base_Instance; Arg : in {Type}.T; ...);
not overriding procedure {Connector}_Send (Self : in out Base_Instance; Arg : in {Type}.T; ...);  -- asserts connected
not overriding function Is_{Connector}_Connected (Self : in Base_Instance) return Boolean;
-- For get connectors:
not overriding function Sys_Time_T_Get (Self : in Base_Instance) return Sys_Time.T;

-- Dropped handler: abstract, override in implementation (can be "is null")
not overriding procedure {Connector}_Send_Dropped (Self : in out Base_Instance; Arg : in {Type}.T) is abstract;

-- Base record (private) contains:
--   Connector_{Name} : {Connector}.Instance;  -- one per invoker connector
--   Events : {Name}_Events.Instance;
--   Data_Products : {Name}_Data_Products.Instance;
--   Packets : {Name}_Packets.Instance;
--   Command_Id_Base : Command_Types.Command_Id := 1;
```

### Events Package (`{Name}_Events`)

```ada
-- Local IDs (enumeration with rep clause):
type Local_Event_Id_Type is (Value_Changed_Id, Error_Detected_Id, ...);
for Local_Event_Id_Type use (Value_Changed_Id => 0, Error_Detected_Id => 1, ...);

-- Creation functions -- call via Self.Events:
function Value_Changed (Self : Instance; Timestamp : Sys_Time.T; Param : in Packed_U32.T) return Event.T;
function Error_Detected (Self : Instance; Timestamp : Sys_Time.T) return Event.T;  -- no param

-- ID getters:
function Get_Value_Changed_Id (Self : Instance) return Event_Types.Event_Id;
```

**Usage in implementation:**
```ada
The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
Self.Event_T_Send_If_Connected (Self.Events.Value_Changed (The_Time, (Value => 42)));
Self.Event_T_Send_If_Connected (Self.Events.Error_Detected (The_Time));  -- no param
```

### Data Products Package (`{Name}_Data_Products`)

```ada
-- Creation functions:
function Current_Value (Self : Instance; Timestamp : Sys_Time.T; Item : in Packed_U32.T) return Data_Product.T;

-- ID getters:
function Get_Current_Value_Id (Self : Instance) return Data_Product_Types.Data_Product_Id;
```

**Usage:** `Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Current_Value (The_Time, (Value => N)));`

### Commands Package (`{Name}_Commands`)

```ada
-- Local IDs:
type Local_Command_Id_Type is (Set_Value_Id, Reset_Id, ...);

-- Creation functions (for tests, not usually needed in implementation):
function Set_Value (Self : Instance; Arg : in Packed_U32.T) return Command.T;

-- ID getters:
function Get_Set_Value_Id (Self : Instance) return Command_Types.Command_Id;
```

**Command handler pattern in implementation:**
```ada
-- Base class auto-generates Execute_Command which dispatches to your handlers.
-- You implement one function per command:
overriding function Set_Value (Self : in out Instance; Arg : in Packed_U32.T) return Command_Execution_Status.E is
   use Command_Execution_Status;
begin
   Self.Value := Arg.Value;
   -- Send event/data product...
   return Success;  -- or Failure
end Set_Value;

-- Also implement Invalid_Command for bad argument handling:
overriding procedure Invalid_Command (Self : in out Instance; Cmd : in Command.T;
   Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);

-- Command_T_Recv_Sync connector dispatches automatically:
overriding procedure Command_T_Recv_Sync (Self : in out Instance; Arg : in Command.T) is
   Stat : constant Command_Response_Status.E := Self.Execute_Command (Arg);
begin
   Self.Command_Response_T_Send_If_Connected ((
      Source_Id => Arg.Header.Source_Id,
      Registration_Id => Self.Command_Reg_Id,
      Command_Id => Arg.Header.Id,
      Status => Stat));
end Command_T_Recv_Sync;
```

### Implementation Spec Pattern

```ada
package Component.{Name}.Implementation is
   type Instance is new {Name}.Base_Instance with private;

   -- Override Init from base:
   overriding procedure Init (Self : in out Instance; ...);

   -- Optional: Set_Up runs once after all components wired and started
   -- Use for: initial data product sends, command registration
   overriding procedure Set_Up (Self : in out Instance);

private
   type Instance is new {Name}.Base_Instance with record
      -- Your component state here:
      Counter : Natural := 0;
      Algorithm_Handle : Algorithm_Access := null;
   end record;

   -- Override connector handlers:
   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T);
   overriding procedure Command_T_Recv_Sync (Self : in out Instance; Arg : in Command.T);

   -- Dropped handlers (can be "is null" for non-critical):
   overriding procedure Event_T_Send_Dropped (Self : in out Instance; Arg : in Event.T) is null;

   -- Command handlers:
   overriding function Set_Value (Self : in out Instance; Arg : in Packed_U32.T) return Command_Execution_Status.E;
   overriding procedure Invalid_Command (Self : in out Instance; Cmd : in Command.T;
      Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);
end Component.{Name}.Implementation;
```

### Timestamp Pattern

Always get time from the Sys_Time connector, never from Arg:
```ada
The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
-- Use The_Time for all events and data products in this handler
Self.Event_T_Send_If_Connected (Self.Events.Something (The_Time));
Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Something (The_Time, Value));
```

Exception: Tick handlers may use `Arg.Time` from the tick itself if appropriate.

### Assembly Lifecycle (generated)

`Init_Base` -> `Set_Id_Bases` -> `Map_Data_Dependencies` -> `Connect_Components` -> `Init_Components` -> `Set_Up_Components` -> `Start_Components`

Component instances declared in `{Assembly}_Components` package. Task objects for active components with synchronization.

### Type Generation (from record/array/enum YAML)

- **U** (unpacked), **T** (packed big-endian), **T_Le** (packed little-endian) types
- `Pack(U) return T` / `Unpack(T) return U` conversion
- `To_Byte_Array` / `From_Byte_Array` serialization
- `Valid(U) return Boolean` field validation
- `-Representation`, `-Validation`, `-Assertion`, `-C` child packages
- Python and MATLAB ground classes

See [references/implementation-patterns.md](references/implementation-patterns.md) for Ada implementation idioms (connector usage, thread safety, command handlers, lifecycle hooks, change detection).

See [references/lasel-reference.md](references/lasel-reference.md) for the LASEL command sequence language (used with command_sequencer component).

See [adamant-testing](../adamant-testing/SKILL.md) skill for test setup, History API, async dispatch, assertions, error injection, and data dependency testing patterns.

