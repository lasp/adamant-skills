# Direct Connector Patterns (Alternative to Data Dependencies)

## When to Use Direct Get Connectors

Use `get` connectors instead of data dependencies when:
- The input type contains F64 (Long_Float/Packed_F64x3) fields -- data dependency serialization has endian issues with F64 packed types
- You want a simpler component with fewer connectors

## Component YAML Pattern

```yaml
connectors:
  - description: Fetch primary input.
    name: Input_Name_T_Get
    return_type: Input_Type.T    # MUST use return_type, NOT type
    kind: get
```

**Critical: `get` connectors use `return_type`, NOT `type`.**

## Tester Pattern for Get Connectors

The generated tester returns uninitialized data from get connectors by default. You MUST:

1. Add a storage field to the tester spec:
```ada
type Instance is new ... with record
   Input_Data : Input_Type.T;  -- Added manually
end record;
```

2. Override the return function in tester body:
```ada
overriding function Input_Name_T_Return (Self : in out Instance) return Input_Type.T is
begin
   Self.Input_Name_T_Return_History.Push (Self.Input_Data);
   return Self.Input_Data;
end Input_Name_T_Return;
```

3. Set the value in the test before ticking:
```ada
T.Input_Data := My_Test_Value;
T.Tick_T_Send ((Time => (0, 0), Count => 0));
```

## F64 Packed Type Endian Workaround

On little-endian systems (x86), the generated `.C.Unpack(T)` and `.C.To_C(U)` functions produce CONSTRAINT_ERROR for Packed_F64x3 fields.

### Workaround: Manual Field-by-Field Conversion

Instead of:
```ada
-- BROKEN for F64 types:
Eph_C : Ephemeris.C.U_C := Ephemeris.C.To_C (Ephemeris.Unpack (Packed_Val));
```

Use:
```ada
-- CORRECT: manual field copy
function To_Ephemeris_C (Src : Ephemeris.U) return Ephemeris.C.U_C is
begin
   return (R_Bdy_Zero_N => [Src.R_Bdy_Zero_N (0), Src.R_Bdy_Zero_N (1), Src.R_Bdy_Zero_N (2)],
           V_Bdy_Zero_N => [Src.V_Bdy_Zero_N (0), Src.V_Bdy_Zero_N (1), Src.V_Bdy_Zero_N (2)],
           Time_Tag     => Src.Time_Tag);
end To_Ephemeris_C;

-- Call as:
Eph_C : Ephemeris.C.U_C := To_Ephemeris_C (Ephemeris.Unpack (Packed_Val));
```

## Implementation Pattern

```ada
overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
   Input_C : aliased Input_Type.C.U_C := Input_Type.C.To_C (Input_Type.Unpack (Self.Input_T_Get));
   -- For F64 types, use manual conversion instead
   Output : constant Out_Type.C.U_C := Update (Self.Alg, Input_C'Unchecked_Access);
begin
   Self.Data_Product_T_Send (Self.Data_Products.Result (
      Arg.Time, Out_Type.Pack (Out_Type.C.To_Ada (Output))));
end Tick_T_Recv_Sync;
```