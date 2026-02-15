# Algorithm Wrapping -- Implementation Details

Core implementation pattern and input strategy are in SKILL.md. This file has additional patterns.

## Existing Types (Check Before Creating)

- `adamant/src/types/packed_arrays/` -- `Packed_F32x3`, `Packed_F32x9`, etc.
- `adamant/src/types/` -- `Packed_F32`, `Packed_U32`, etc.
- Project-specific types directory for domain-specific records

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

## Ada Binding Conventions

- Opaque handles: `null record` (not `System.Address`)
- Pointer types: `type Foo_Access is access all Foo;` with `limited private` in public
- Suppress style warnings: `pragma Style_Checks (Off);`

## Reference Implementations

Check your project's existing algorithm wrappers for patterns:
- Basic wrapper: tick + request + data_product connectors
- With parameters: + modify connector + Update_Parameters_Action
- Eigen vectors: .C.U_C conversion with To_C/To_Ada
