<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Generated Code API Reference

From component YAML, the generator produces these packages (all in `build/src/`):

## Base Class (`Component.{Name}`)

```ada
type Base_Instance is abstract new Component.Core_Instance with private;

-- Init: abstract IFF YAML has init section
not overriding procedure Init (Self : in out Base_Instance; ...) is abstract;

-- Invokee connectors: abstract, override in implementation
not overriding procedure {Name} (Self : in out Base_Instance; Arg : in {Type}.T) is abstract;

-- Invoker connector methods (private, usable by child):
not overriding procedure {Name}_Send_If_Connected (Self : in out Base_Instance; Arg : in {Type}.T);
not overriding procedure {Name}_Send (Self : in out Base_Instance; Arg : in {Type}.T);  -- asserts connected
not overriding function Is_{Name}_Connected (Self : in Base_Instance) return Boolean;
not overriding function Sys_Time_T_Get (Self : in Base_Instance) return Sys_Time.T;  -- for get connectors

-- Dropped: abstract for every send connector
not overriding procedure {Name}_Send_Dropped (Self : in out Base_Instance; Arg : in {Type}.T) is abstract;
```

## Events Package (`{Name}_Events`)

```ada
type Local_Event_Id_Type is (Value_Changed_Id, Error_Detected_Id, ...);
-- Creation via Self.Events:
function Value_Changed (Self : Instance; Timestamp : Sys_Time.T; Param : in Packed_U32.T) return Event.T;
function Error_Detected (Self : Instance; Timestamp : Sys_Time.T) return Event.T;  -- no param
function Get_Value_Changed_Id (Self : Instance) return Event_Types.Event_Id;
```

## Data Products Package (`{Name}_Data_Products`)

```ada
function Current_Value (Self : Instance; Timestamp : Sys_Time.T; Item : in Packed_U32.T) return Data_Product.T;
function Get_Current_Value_Id (Self : Instance) return Data_Product_Types.Data_Product_Id;
```

## Commands Package (`{Name}_Commands`)

```ada
type Local_Command_Id_Type is (Set_Value_Id, Reset_Id, ...);
function Set_Value (Self : Instance; Arg : in Packed_U32.T) return Command.T;  -- for tests
function Get_Set_Value_Id (Self : Instance) return Command_Types.Command_Id;
```

`Execute_Command` (generated in base) dispatches to your per-command handler functions. Command handler names match YAML `name:` exactly (no `_Execute` suffix).

## Timestamp Pattern

Always get time from Sys_Time connector, reuse for consistency:
```ada
The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
```

Exception: Tick handlers may use `Arg.Time` from the tick itself.

## Assembly Lifecycle

`Init_Base` → `Set_Id_Bases` → `Map_Data_Dependencies` → `Connect_Components` → `Init_Components` → `Set_Up_Components` → `Start_Components`

See [adamant-assembly-dev](../../adamant-assembly-dev/SKILL.md) for assembly details.

## Type Generation

See [adamant-type-system](../../adamant-type-system/SKILL.md) for `.U`/`.T`/`.T_Le` types, `Pack`/`Unpack`, validation.

## Variable Length Commands

Commands with variable-length argument types get different signatures:
```ada
-- Normal: returns Command.T directly
function My_Cmd (Self : Instance; Arg : in My_Arg.T) return Command.T;
-- Variable-length: returns Serialization_Status, Command.T via out param
function My_Cmd (Self : Instance; Arg : in My_Arg.T; Cmd : out Command.T) return Serialization_Status;
```

Compile-time error if argument type exceeds `Command_Types.Command_Arg_Buffer_Type'Length`.
