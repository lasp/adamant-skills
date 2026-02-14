# Algorithm Wrapping — Implementation Details

## Input Strategy: Parameters vs Data Dependencies

**Parameters** (modify connector): fixed spacecraft properties, tunable gains, configuration. Changed infrequently.
- Spacecraft inertia, control gains, slew properties, damping coefficients

**Data Dependencies** (request connector): dynamic telemetry from other components. Fetched each tick, staleness-checked.
- Attitude state, ephemeris, sensor readings, navigation solutions

**Stateful algorithms**: may need reset/init call. Track config state (e.g., `Slews_Configured : Boolean`), call algorithm reset in `Update_Parameters_Action`.

## Existing Types (Check Before Creating)

- `adamant/src/types/packed_arrays/` — `Packed_F32x3`, `Packed_F32x9`, etc.
- `adamant/src/types/` — `Packed_F32`, `Packed_U32`, etc.
- Project-specific types directory for domain-specific records

## Type Conversion Chain

```
Packed.T (wire) → Unpack → .U (Ada record) → .C.To_C → .C.U_C (C-compatible)
```
Reverse: `.C.To_Ada → Pack → .T`

`.C.U_C` only exists for types with explicit C bindings (`-c.ads` child package). For custom YAML records, use `access constant Type_Name.T` in binding specs instead.

## Error Handlers (Safety-Critical)

```ada
overriding procedure Invalid_Data_Dependency
  (Self : in out Instance; Id : in Data_Product_Types.Data_Product_Id;
   Ret : in Data_Product_Return.T) is
   pragma Annotate (GNATSAS, Intentional, "subp always fails", "intentional assertion");
begin
   pragma Assert (False);
end Invalid_Data_Dependency;
```

## Parameter Handling

```ada
overriding procedure Update_Parameters_Action (Self : in out Instance) is
begin
   Set_Control_Gain (Self.Alg, Self.Control_Gain.Value);
end Update_Parameters_Action;
```

## Ada Binding Conventions

- Opaque handles: `null record` (not `System.Address`)
- Pointer types: `type Foo_Access is access all Foo;` with `limited private` in public
- Suppress style warnings: `pragma Style_Checks (Off);`
- C float → `Short_Float` (F32), C double → `Long_Float` (F64)

## Reference Implementations

Check your project's existing algorithm wrappers for patterns:
- Basic wrapper: tick + request + data_product connectors
- With parameters: + modify connector + Update_Parameters_Action
- Eigen vectors: .C.U_C conversion with To_C/To_Ada
