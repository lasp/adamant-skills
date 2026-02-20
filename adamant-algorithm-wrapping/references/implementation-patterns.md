# Implementation Patterns

## Spec (.ads) Template

```ada
with Tick;
with <Algorithm_Name>_C; use <Algorithm_Name>_C;

package Component.<Component_Name>.Implementation is

   type Instance is new <Component_Name>.Base_Instance with private;

private

   type Instance is new <Component_Name>.Base_Instance with record
      Alg : <Algorithm_Name>_Access := null;
   end record;

   overriding procedure Init (Self : in out Instance);
   not overriding procedure Destroy (Self : in out Instance);
   overriding procedure Set_Up (Self : in out Instance) is null;
   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T);

   -- Add if component has parameters:
   overriding procedure Parameter_Update_T_Modify (Self : in out Instance; Arg : in out Parameter_Update.T);
   overriding procedure Update_Parameters_Action (Self : in out Instance);

   -- Data dependency handlers:
   overriding procedure Invalid_Data_Dependency (Self : in out Instance;
      Id : in Data_Product_Types.Data_Product_Id; Ret : in Data_Product_Return.T);

end Component.<Component_Name>.Implementation;
```

## Body (.adb) Template -- Without Parameters

```ada
with <Type_1>.C;
with <Output_Type>.C;
with Algorithm_Wrapper_Util;

package body Component.<Component_Name>.Implementation is

   overriding procedure Init (Self : in out Instance) is
   begin
      Self.Alg := Create;
   end Init;

   not overriding procedure Destroy (Self : in out Instance) is
   begin
      Destroy (Self.Alg);
   end Destroy;

   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
      use Data_Product_Enums; use Data_Product_Enums.Data_Dependency_Status;
      use Algorithm_Wrapper_Util;

      Dep_1 : <Type_1>.T;
      Dep_1_Status : constant Data_Dependency_Status.E :=
         Self.Get_<Dep_1_Name> (Value => Dep_1, Stale_Reference => Arg.Time);
   begin
      if Is_Dep_Status_Success (Dep_1_Status) then
         declare
            Dep_1_C : aliased <Type_1>.C.U_C :=
               <Type_1>.C.To_C (<Type_1>.Unpack (Dep_1));
            Output : constant <Output_Type>.C.U_C :=
               <Algorithm>_C.Update_State (
                  Self.Alg, Input_1 => Dep_1_C'Unchecked_Access);
         begin
            Self.Data_Product_T_Send (Self.Data_Products.<Product_Name> (
               Arg.Time, <Output_Type>.Pack (<Output_Type>.C.To_Ada (Output))));
         end;
      end if;
   end Tick_T_Recv_Sync;

   overriding procedure Invalid_Data_Dependency (
      Self : in out Instance;
      Id : in Data_Product_Types.Data_Product_Id;
      Ret : in Data_Product_Return.T) is
   begin
      pragma Assert (False);
   end Invalid_Data_Dependency;

end Component.<Component_Name>.Implementation;
```

## Body (.adb) Additions -- With Parameters

Add `Self.Update_Parameters;` as the FIRST line of `Tick_T_Recv_Sync`:

```ada
overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
   ...
begin
   Self.Update_Parameters;  -- Apply any pending parameter changes
   if Is_Dep_Status_Success (...) then
      ...
```

Add parameter handlers:

```ada
overriding procedure Parameter_Update_T_Modify (
   Self : in out Instance; Arg : in out Parameter_Update.T) is
begin
   Self.Process_Parameter_Update (Arg);
end Parameter_Update_T_Modify;

overriding procedure Update_Parameters_Action (Self : in out Instance) is
begin
   -- Apply parameters to C algorithm via setters.
   Set_Gain (Self.Alg, Self.Derivative_Gain_P.Value);
end Update_Parameters_Action;
```

## Type Conversion Chain

### Input: Ada packed -> C
```
Ada .T  ->  Unpack  ->  Ada .U  ->  To_C  ->  C.U_C  ->  'Unchecked_Access
```

```ada
Dep : Type_Name.T;  -- From data dependency fetch
Dep_C : aliased Type_Name.C.U_C := Type_Name.C.To_C (Type_Name.Unpack (Dep));
-- Pass: Dep_C'Unchecked_Access
```

### Output: C -> Ada packed
```
C.U_C  ->  To_Ada  ->  Ada .U  ->  Pack  ->  Ada .T
```

```ada
Result_C : constant Type_Name.C.U_C := Algorithm_C.Update (...);
Result : constant Type_Name.T := Type_Name.Pack (Type_Name.C.To_Ada (Result_C));
```

## Data Flow Summary

1. **Tick arrives** -> Triggers `Tick_T_Recv_Sync`
2. **Update parameters** -> `Self.Update_Parameters` (if component has params)
3. **Fetch dependencies** -> `Self.Get_<Name>(Value => X, Stale_Reference => Arg.Time)`
4. **Check status** -> `Is_Dep_Status_Success` on all deps
5. **Convert to C** -> `Unpack` then `To_C`, take `'Unchecked_Access`
6. **Call algorithm** -> `Algorithm_C.Update(Self.Alg, ...)`
7. **Convert result** -> `To_Ada` then `Pack`
8. **Publish** -> `Self.Data_Product_T_Send(Self.Data_Products.Name(Arg.Time, Result))`