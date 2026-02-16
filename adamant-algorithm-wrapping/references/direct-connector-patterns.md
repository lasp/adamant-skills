# Direct Connector Patterns (Alternative to Data Dependencies)

## When to Use Direct Get Connectors

Use `get` connectors instead of data dependencies when:
- The input type contains F64 (Long_Float/Packed_F64x3) fields -- data dependency serialization has endian issues with F64 packed types
- You want a simpler component with fewer connectors (no Data_Product_Fetch request connector)
- The upstream component can expose data via a direct connector

## Component YAML Pattern

```yaml
connectors:
  - description: Fetch primary input.
    name: Input_Name_T_Get
    return_type: Input_Type.T    # MUST use return_type, NOT type
    kind: get
```

**Critical: `get` connectors use `return_type`, NOT `type`.** The code generator rejects `type` on `get` kind.

## Tester Pattern for Get Connectors

The generated tester returns uninitialized data from get connectors by default. You MUST:

1. Add a storage field to the tester spec:
```ada
type Instance is new ... with record
   ...
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

**Name collision warning:** If the type package name matches a field name (e.g., `Att_Guid` package and `Att_Guid` field), use a different field name (e.g., `Att_Guid_Data`).

## F64 Packed Type Endian Workaround

On little-endian systems (x86), the generated `.C.Unpack(T)` and `.C.To_C(U)` functions produce CONSTRAINT_ERROR "invalid data" for Packed_F64x3 fields. The root cause: `Scalar_Storage_Order => High_Order_First` stores bytes big-endian, but the `.C` package's element copy doesn't handle the byte swap correctly for F64.

### Workaround: Manual Field-by-Field Conversion

Instead of:
```ada
-- BROKEN for F64 types:
Eph_C : Ephemeris.C.U_C := Ephemeris.C.To_C (Ephemeris.Unpack (Packed_Val));
```

Use:
```ada
-- CORRECT: go through native U type with manual field copy
function To_Ephemeris_C (Src : Ephemeris.U) return Ephemeris.C.U_C is
begin
   return (R_Bdy_Zero_N => [Src.R_Bdy_Zero_N (0), Src.R_Bdy_Zero_N (1), Src.R_Bdy_Zero_N (2)],
           V_Bdy_Zero_N => [Src.V_Bdy_Zero_N (0), Src.V_Bdy_Zero_N (1), Src.V_Bdy_Zero_N (2)],
           Sigma_Bn     => [Src.Sigma_Bn (0), Src.Sigma_Bn (1), Src.Sigma_Bn (2)],
           Omega_Bn_B   => [Src.Omega_Bn_B (0), Src.Omega_Bn_B (1), Src.Omega_Bn_B (2)],
           Time_Tag     => Src.Time_Tag);
end To_Ephemeris_C;

-- Call as:
Eph_C : Ephemeris.C.U_C := To_Ephemeris_C (Ephemeris.Unpack (Packed_Val));
```

The key insight: `Ephemeris.Unpack(T)` correctly handles endian conversion (Ada's Scalar_Storage_Order does the byte swap). The resulting `U` record has native-endian field values. Copying individual scalar fields to C types preserves correct values.

### T_Le Alternative (Framework Limitation)

Adamant provides `T_Le` (little-endian packed) types. These would avoid the endian issue, BUT:
- Records CANNOT mix `T` and `T_Le` fields (e.g., Ephemeris with both F64x3 and F32x3)
- `T_Le` records don't generate `Serialization` or `Representation` child packages
- Without Serialization, data products and data dependencies won't work

Conclusion: Use `T` types with the manual-copy workaround until framework support improves.

## Implementation Pattern with Direct Connectors

```ada
overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
   -- Fetch via direct connectors and convert:
   Input_C : aliased Input_Type.C.U_C := Input_Type.C.To_C (Input_Type.Unpack (Self.Input_T_Get));
   -- For F64 types, use manual conversion instead:
   -- Input_C : aliased Input_Type.C.U_C := To_Input_C (Input_Type.Unpack (Self.Input_T_Get));
   Output : constant Out_Type.C.U_C := Update (Self.Alg, Input_C'Unchecked_Access);
begin
   Self.Data_Product_T_Send (Self.Data_Products.Result (
      Arg.Time, Out_Type.Pack (Out_Type.C.To_Ada (Output))));
end Tick_T_Recv_Sync;
```
