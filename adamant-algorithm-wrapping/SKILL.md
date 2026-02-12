---
name: adamant-algorithm-wrapping
description: Complete pipeline for wrapping C++ algorithms into Adamant passive components with C shims, Ada bindings, and unit tests
---

# Adamant Algorithm Wrapping Pipeline

Workflow for wrapping C++ algorithms (e.g., GNC) into Adamant components via C shims.

```
C++ Algorithm -> C Shim -> Ada Bindings -> Packed Records -> Component YAML -> Implementation -> Unit Tests
```

**Repository layout:**
- C++ algorithms: `fp32-fsw-xmera/algorithms/<name>/`
- Ada wrapper components: `adamant-xmera-components/src/components/<name>/`
- Shared packed types: `adamant-xmera-components/src/types/`

See [references/c-shim-bindings.md](references/c-shim-bindings.md) for Stages 1-3 (C shim creation, h2ads Ada binding generation, C struct to packed record conversion).

## Stage 4: Component YAML Model

Wrapper components are typically **passive** with a `recv_sync` tick connector and a `request` connector for data dependencies:

```yaml
---
description: Wraps FooAlgorithm to compute X from Y inputs.
execution: passive
init:
  description: Creates algorithm handle.
connectors:
  - description: Run algorithm on tick.
    type: Tick.T
    kind: recv_sync
  - description: Fetch data product from database.
    type: Data_Product_Fetch.T
    return_type: Data_Product_Return.T
    kind: request
  - description: Data product output.
    type: Data_Product.T
    kind: send
  - description: Events.
    type: Event.T
    kind: send
```

Add `Parameter_Update.T` modify connector if algorithm has tunable config.

### Data Dependencies

Data dependencies fetch inputs from the Product_Database. Must fit in `data_product_buffer_size` (typically 128 bytes).

```yaml
---
description: Data dependencies for FooComponent.
data_dependencies:
  - name: Nav_Attitude
    type: Nav_Att.T
    description: Navigation attitude state.
  - name: Ephemeris
    type: Ephemeris.T
    description: Ephemeris data.
```

## Stage 5: Implementation

### Spec Pattern
```ada
with Foo_Algorithm_C; use Foo_Algorithm_C;

package Component.Foo_Component.Implementation is
   type Instance is new Foo_Component.Base_Instance with private;
   overriding procedure Init (Self : in out Instance);
   not overriding procedure Destroy (Self : in out Instance);
private
   type Instance is new Foo_Component.Base_Instance with record
      Alg : Foo_Algorithm_Access := null;
   end record;
```

### Body Pattern
```ada
overriding procedure Init (Self : in out Instance) is
begin
   Self.Alg := Create;
end Init;

not overriding procedure Destroy (Self : in out Instance) is
begin
   Destroy (Self.Alg);
end Destroy;

overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
   use Algorithm_Wrapper_Util;
   use Data_Product_Enums.Data_Dependency_Status;
   Input_1 : Input_Type.T;
   Input_1_Status : constant Data_Dependency_Status.E :=
      Self.Get_Nav_Attitude (Value => Input_1, Stale_Reference => Arg.Time);
begin
   Self.Update_Parameters;  -- Only if parameters exist
   if Is_Dep_Status_Success (Input_1_Status) then
      declare
         Input_C : constant Input_Type.C.U_C :=
            Input_Type.C.To_C (Input_Type.Unpack (Input_1));
         Output_C : constant Output_Type.C.U_C :=
            Update (Self.Alg, Input_C'Unchecked_Access);
      begin
         Self.Data_Product_T_Send (Self.Data_Products.Result (
            Arg.Time, Output_Type.Pack (Output_Type.C.To_Ada (Output_C))));
      end;
   end if;
end Tick_T_Recv_Sync;
```

**Type conversion chain:** `Packed.T` (wire) -> `Unpack` -> `.U` (Ada record) -> `.C.To_C` -> `.C.U_C` (C-compatible) and reverse.

### Error Handlers (always include)
```ada
overriding procedure Invalid_Data_Dependency
  (Self : in out Instance; Id : in Data_Product_Types.Data_Product_Id;
   Ret : in Data_Product_Return.T) is
   pragma Annotate (GNATSAS, Intentional, "subp always fails", "intentional assertion");
begin
   pragma Assert (False);
end Invalid_Data_Dependency;
```

### Parameter Handling
```ada
overriding procedure Update_Parameters_Action (Self : in out Instance) is
begin
   Set_Control_Gain (Self.Alg, Self.Control_Gain.Value);
end Update_Parameters_Action;
```

## Stage 6: Unit Testing

### Setup
```python
# test/env.py
from environments import test
```

Ensure `.all_path` exists in the **component** directory (NOT the test directory).

### Test Pattern

Use **T rename**, work with **`.T` packed types** (not `.U`), and use **`T.System_Time`** for tick timestamps (never `(0, 0)` -- causes staleness issues):

```ada
overriding procedure Test (Self : in out Instance) is
   T : Component.Foo.Implementation.Tester.Instance_Access renames Self.Tester;
begin
   -- Set up input data products on the tester
   T.Nav_Attitude := (Sigma_Bn => [0.1, 0.2, 0.3], ...);

   T.Tick_T_Send ((Time => T.System_Time, Count => 0));

   Natural_Assert.Eq (T.Result_History.Get_Count, 1);
   declare
      Output : constant Output_Type.T := T.Result_History.Get (1);
   begin
      -- Compare against Python reference test values
      Float_Assert.Eq (Output.Field, Expected, Epsilon => 0.0001);
   end;
end Test;
```

**Array aggregate syntax:** Use `[x, y, z]` directly, NOT `(Value => [x, y, z])`.

## Stage 7: Build Validation

**Zero warnings required** (safety-critical):
```bash
cd component_directory/ && redo       # Compile clean
cd test/ && redo test                  # Tests pass
```

Verify C++ library linkage: `nm libgncAlgorithms.a | grep <algorithm>`

## Common Pitfalls

- **Type precision mismatch:** C `float` -> `Short_Float` (F32), C `double` -> `Long_Float` (F64). Never swap.
- **C struct duplication:** Always use Adamant packed records for C structs, never standalone Ada packages.
- **Missing constant validation:** `#define` constants must be validated at elaboration via `pragma Assert` against imported C getter functions.
- **Tick timestamp `(0, 0)`:** Causes data dependency staleness failures. Use `T.System_Time`.
- **Missing `.all_path`:** In component dir (not test dir). Causes template generation failures.
- **Library not in CMakeLists.txt:** Algorithm must be added to fp32-fsw-xmera build to link.

## Reference Implementations

- `adamant-xmera-components/src/components/attitude_tracking_error/` (Eigen vectors, data deps)
- `adamant-xmera-components/src/components/rate_control/` (parameters + algorithm)
- `adamant-xmera-components/src/components/sunline_ephem/` (basic wrapper pattern)
- `fp32-fsw-xmera/algorithms/sunSearch/` (shared types header DRY pattern)
- `fp32-fsw-xmera/algorithms/attTrackingError/` (Eigen conversion pattern)
