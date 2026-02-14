---
name: adamant-algorithm-wrapping
description: Complete pipeline for wrapping C++ algorithms into Adamant passive components with C shims, Ada bindings, and unit tests
---

# Adamant Algorithm Wrapping Pipeline

```
C++ Algorithm → C Shim → Ada Bindings → Packed Records → Component YAML → Implementation → Tests
```

See [references/c-shim-bindings.md](references/c-shim-bindings.md) for C shim and binding generation.
See [references/implementation-details.md](references/implementation-details.md) for type strategy and patterns.

## Component YAML (Typical Wrapper)

```yaml
description: Wraps FooAlgorithm
execution: passive
init:
  description: Creates algorithm handle.
connectors:
  - description: Run algorithm on tick.
    type: Tick.T
    kind: recv_sync
  - description: Fetch data product.
    type: Data_Product_Fetch.T
    return_type: Data_Product_Return.T
    kind: request
  - description: Data product output.
    type: Data_Product.T
    kind: send
  - description: Events.
    type: Event.T
    kind: send
  - description: System time.
    return_type: Sys_Time.T
    kind: get
```

Add `Parameter_Update.T` modify only if runtime-tunable config needed.

## Implementation Pattern

```ada
-- Spec
with Foo_Algorithm_C; use Foo_Algorithm_C;
package Component.Foo.Implementation is
   type Instance is new Foo.Base_Instance with private;
   overriding procedure Init (Self : in out Instance);
private
   type Instance is new Foo.Base_Instance with record
      Alg : Foo_Algorithm_Access := null;
   end record;
end;

-- Body
overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
   use Data_Product_Enums.Data_Dependency_Status;
   Input : Input_Type.T;
   Status : constant Data_Dependency_Status.E :=
      Self.Get_Nav_Attitude (Value => Input, Stale_Reference => Arg.Time);
begin
   if Status = Success then
      declare
         Input_C : constant Input_Type.C.U_C :=
            Input_Type.C.To_C (Input_Type.Unpack (Input));
         Output_C : constant Output_Type.C.U_C :=
            Update (Self.Alg, Input_C'Unchecked_Access);
      begin
         Self.Data_Product_T_Send_If_Connected (Self.Data_Products.Result (
            Arg.Time, Output_Type.Pack (Output_Type.C.To_Ada (Output_C))));
      end;
   end if;
end;
```

**Type chain:** `.T` → `Unpack` → `.U` → `.C.To_C` → `.C.U_C` (and reverse).
`.C.U_C` only exists for types with `-c.ads` child package. For custom types, use `access constant Type.T` directly.

## Testing Pattern

```ada
overriding procedure Test (Self : in out Instance) is
   T : Component.Foo.Implementation.Tester.Instance_Access renames Self.Tester;
begin
   T.Tick_T_Send ((Time => T.System_Time, Count => 0));  -- NOT (0,0)!
   Natural_Assert.Eq (T.Result_History.Get_Count, 1);
end;
```

Use `T.System_Time` for ticks (avoids staleness). Array aggregates: `[x, y, z]` directly.

## Common Pitfalls

- C `float` → `Short_Float` (F32), C `double` → `Long_Float` (F64). Never swap.
- Tick timestamp `(0, 0)` causes data dependency staleness failures
- `get` connector uses `return_type:` only, NOT `type:`
- Every send connector needs `*_Send_Dropped` override
- Check existing framework packed types before creating new ones
- Zero warnings required for safety-critical code
- Verify C++ library linkage: `nm libAlgorithms.a | grep <name>`

## Build

```bash
redo all          # Compile component
cd test/ && redo test   # Run tests
```
