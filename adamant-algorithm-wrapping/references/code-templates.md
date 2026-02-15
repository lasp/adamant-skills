# Code Templates -- Algorithm Wrapping

Full code templates referenced from [SKILL.md](../SKILL.md). Each section corresponds to a SKILL.md section number.

---

## 1. C Shim Templates

### Opaque Handle Pattern (Header)
```c
// Header (.h)
#ifdef __cplusplus
extern "C" {
#endif

typedef struct FooAlgorithm FooAlgorithm;

// Lifecycle
FooAlgorithm* FooAlgorithm_create(void);
void FooAlgorithm_destroy(FooAlgorithm* self);

// Core update
OutputPayload FooAlgorithm_update(FooAlgorithm* self, const InputPayload* input);

// Setters/getters for tunable parameters
void FooAlgorithm_setGainP(FooAlgorithm* self, float p);
float FooAlgorithm_getGainP(FooAlgorithm* self);

// Reset (for stateful algorithms)
void FooAlgorithm_reset(FooAlgorithm* self, uint64_t callTime);

#ifdef __cplusplus
}
#endif
```

### C Shim Implementation
```cpp
// Implementation (.cpp)
#include "fooAlgorithm_c.h"
#include "fooAlgorithm.h"  // C++ class header
#include <Eigen/Core>

FooAlgorithm* FooAlgorithm_create(void) {
    return reinterpret_cast<FooAlgorithm*>(new ::FooAlgorithm());
}

void FooAlgorithm_destroy(FooAlgorithm* self) {
    delete reinterpret_cast<::FooAlgorithm*>(self);
}

OutputPayload FooAlgorithm_update(FooAlgorithm* self, const InputPayload* input) {
    return reinterpret_cast<::FooAlgorithm*>(self)->update(*input);
}
```

### POD Conversion for Eigen Types
```c
typedef struct { float data[3]; } Vector3f_c;

// In .cpp, convert at boundary:
void FooAlgorithm_setVector(FooAlgorithm* self, Vector3f_c vec) {
    Eigen::Vector3f v;
    v << vec.data[0], vec.data[1], vec.data[2];
    reinterpret_cast<::FooAlgorithm*>(self)->setVector(v);
}

Vector3f_c FooAlgorithm_getVector(FooAlgorithm* self) {
    Eigen::Vector3f v = reinterpret_cast<::FooAlgorithm*>(self)->getVector();
    Vector3f_c out;
    out.data[0] = v[0]; out.data[1] = v[1]; out.data[2] = v[2];
    return out;
}
```

### Shared Payload Struct Example
```c
// msgPayloadDef/AttGuidMsgF32Payload.h
typedef struct {
    float sigma_BR[3];
    float omega_BR_B[3];
    float omega_RN_B[3];
    float domega_RN_B[3];
} AttGuidMsgF32Payload;
```

---

## 2. Ada Binding Spec Templates

### Complete Ada Binding Spec
```ada
pragma Ada_2012;
pragma Style_Checks (Off);
pragma Warnings     (Off, "-gnatwu");

with Interfaces.C; use Interfaces; use Interfaces.C;
with Input_Type.C;
with Output_Type.C;

package Foo_Algorithm_C is

   type Foo_Algorithm is limited private;
   type Foo_Algorithm_Access is access all Foo_Algorithm;

   function Create return Foo_Algorithm_Access
     with Import => True, Convention => C,
          External_Name => "FooAlgorithm_create";

   procedure Destroy (Self : Foo_Algorithm_Access)
     with Import => True, Convention => C,
          External_Name => "FooAlgorithm_destroy";

   function Update
     (Self     : Foo_Algorithm_Access;
      Input_In : Input_Type.C.U_C_Access)
     return Output_Type.C.U_C
     with Import => True, Convention => C,
          External_Name => "FooAlgorithm_update";

   procedure Set_Gain_P (Self : Foo_Algorithm_Access; P : Short_Float)
     with Import => True, Convention => C,
          External_Name => "FooAlgorithm_setGainP";

private
   type Foo_Algorithm is null record;
end Foo_Algorithm_C;

pragma Style_Checks (On);
pragma Warnings     (On, "-gnatwu");
```

### Constant Validation
```ada
NUM_SLEWS : constant := 3;
function Get_Num_Slews return Unsigned_32
  with Import => True, Convention => C, External_Name => "FooAlgorithm_getNumSlews";
pragma Assert (Unsigned_32 (NUM_SLEWS) = Get_Num_Slews);
```

---

## 6. Implementation Templates

### Spec
```ada
with Foo_Algorithm_C; use Foo_Algorithm_C;

package Component.Foo.Implementation is
   type Instance is new Foo.Base_Instance with private;
   overriding procedure Init (Self : in out Instance);
   not overriding procedure Destroy (Self : in out Instance);
private
   type Instance is new Foo.Base_Instance with record
      Alg : Foo_Algorithm_Access := null;
   end record;
   overriding procedure Set_Up (Self : in out Instance) is null;
   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T);
   overriding procedure Data_Product_T_Send_Dropped (Self : in out Instance; Arg : in Data_Product.T) is null;
   overriding function Get_Data_Dependency (Self : in out Instance; Id : in Data_Product_Types.Data_Product_Id)
     return Data_Product_Return.T is (Self.Data_Product_Fetch_T_Request ((Id => Id)));
   overriding procedure Invalid_Data_Dependency
     (Self : in out Instance; Id : in Data_Product_Types.Data_Product_Id; Ret : in Data_Product_Return.T);
end Component.Foo.Implementation;
```

### Body -- Basic Wrapper
```ada
with Input_Type.C;
with Output_Type.C;
with Algorithm_Wrapper_Util;

package body Component.Foo.Implementation is

   overriding procedure Init (Self : in out Instance) is
   begin
      Self.Alg := Create;
   end Init;

   not overriding procedure Destroy (Self : in out Instance) is
   begin
      Destroy (Self.Alg);
   end Destroy;

   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
      use Data_Product_Enums.Data_Dependency_Status;
      use Algorithm_Wrapper_Util;
      Input_Dep : Input_Type.T;
      Status : constant Data_Dependency_Status.E :=
         Self.Get_My_Input (Value => Input_Dep, Stale_Reference => Arg.Time);
   begin
      if Is_Dep_Status_Success (Status) then
         declare
            Input_C : aliased Input_Type.C.U_C := Input_Type.C.To_C (Input_Type.Unpack (Input_Dep));
            Output_C : constant Output_Type.C.U_C := Update (Self.Alg, Input_C'Unchecked_Access);
         begin
            Self.Data_Product_T_Send (Self.Data_Products.Result (
               Arg.Time, Output_Type.Pack (Output_Type.C.To_Ada (Output_C))));
         end;
      end if;
   end Tick_T_Recv_Sync;

   overriding procedure Invalid_Data_Dependency (...) is
      pragma Annotate (GNATSAS, Intentional, "subp always fails", "intentional assertion");
   begin
      pragma Assert (False);
   end Invalid_Data_Dependency;

end Component.Foo.Implementation;
```

### Body -- With Parameters (Rate Control Pattern)
```ada
overriding procedure Parameter_Update_T_Modify (Self : in out Instance; Arg : in out Parameter_Update.T) is
begin
   Self.Process_Parameter_Update (Arg);
end Parameter_Update_T_Modify;

overriding procedure Update_Parameters_Action (Self : in out Instance) is
begin
   Set_Gain_P (Self.Alg, Self.Gain_P.Value);
   -- Push all parameter values to C++ algorithm state
end Update_Parameters_Action;
```

### Algorithm_Wrapper_Util
```ada
function Is_Dep_Status_Success (Status : Data_Product_Enums.Data_Dependency_Status.E) return Boolean;
-- Returns True for Success, False for Not_Available/Stale, asserts False for Error
```

---

## 10. Testing Templates

### Test Lifecycle
```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Init;  -- Creates C++ handle
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;

overriding procedure Tear_Down_Test (Self : in out Instance) is
begin
   Self.Tester.Component_Instance.Destroy;  -- Frees C++ handle
   Self.Tester.Final_Base;
end Tear_Down_Test;
```

### Writing Test Cases
```ada
overriding procedure Test (Self : in out Instance) is
   T : Component.Foo.Implementation.Tester.Instance_Access renames Self.Tester;
begin
   -- Set data dependencies (tester provides these):
   T.My_Input := (Sigma_Bn => [0.25, -0.45, 0.75], ...);

   -- Tick the component:
   T.Tick_T_Send ((Time => T.System_Time, Count => 0));

   -- Verify output data products:
   Natural_Assert.Eq (T.Data_Product_T_Recv_Sync_History.Get_Count, 1);
   Natural_Assert.Eq (T.Result_History.Get_Count, 1);
   Result_Assert.Eq (T.Result_History.Get (1), Expected_Value, Epsilon => 0.001);
end Test;
```

### Verifying Parameter Updates
```ada
-- Set parameter, then tick:
T.Parameters := (Gain_P => (Value => 1.5), Inertia => [...]);
T.Parameter_Update_T_Send ((Operation => Set, Status => Success));
T.Tick_T_Send ((Time => T.System_Time, Count => 0));
-- Verify output reflects new parameter values
```
