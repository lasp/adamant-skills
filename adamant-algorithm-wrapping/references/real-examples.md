# Real Examples from xmera-components

Annotated code from actual wrapped algorithms in `adamant-xmera-components`.

## Attitude Tracking Error -- Basic Wrapper (No Parameters)

### C Shim Header (fp32-fsw-xmera)
```c
typedef struct AttTrackingErrorAlgorithm AttTrackingErrorAlgorithm;
AttTrackingErrorAlgorithm* AttTrackingErrorAlgorithm_create(void);
void AttTrackingErrorAlgorithm_destroy(AttTrackingErrorAlgorithm* self);
void AttTrackingErrorAlgorithm_reset(AttTrackingErrorAlgorithm* self, uint64_t callTime);
AttGuidMsgF32Payload AttTrackingErrorAlgorithm_update(
    AttTrackingErrorAlgorithm* self,
    AttRefMsgF32Payload* attRefInMsg,
    NavAttMsgF32Payload* attNavInMsg);
void AttTrackingErrorAlgorithm_setSigma_R0R(AttTrackingErrorAlgorithm* self, Vector3f_c sigma_R0R);
Vector3f_c AttTrackingErrorAlgorithm_getSigma_R0R(AttTrackingErrorAlgorithm* self);
```

### Ada Binding Spec
Key transformations from h2ads output:
- `AttGuidMsgF32Payload` → `Att_Guid.C.U_C` (Adamant packed type)
- `AttRefMsgF32Payload*` → `Att_Ref.C.U_C_Access`
- `Vector3f_c` → `Packed_F32x3_Record.C.U_C`
- Opaque handle → `limited private` / `null record`

```ada
package Att_Tracking_Error_Algorithm_C is
   type Att_Tracking_Error_Algorithm is limited private;
   type Att_Tracking_Error_Algorithm_Access is access all Att_Tracking_Error_Algorithm;

   function Create return Att_Tracking_Error_Algorithm_Access
     with Import => True, Convention => C,
          External_Name => "AttTrackingErrorAlgorithm_create";

   procedure Destroy (Self : Att_Tracking_Error_Algorithm_Access)
     with Import => True, Convention => C,
          External_Name => "AttTrackingErrorAlgorithm_destroy";

   function Update
     (Self              : Att_Tracking_Error_Algorithm_Access;
      Current_Sim_Nanos : Unsigned_64;
      Att_Ref_In        : Att_Ref.C.U_C_Access;
      Att_Nav_In        : Nav_Att.C.U_C_Access)
     return Att_Guid.C.U_C
     with Import => True, Convention => C,
          External_Name => "AttTrackingErrorAlgorithm_update";

   procedure Set_Sigma_R0R (Self : ...; Sigma_R0R : Packed_F32x3_Record.C.U_C)
     with Import => True, Convention => C,
          External_Name => "AttTrackingErrorAlgorithm_setSigma_R0R";
private
   type Att_Tracking_Error_Algorithm is null record;
end;
```

### Component YAML
```yaml
description: Attitude tracking error algorithm.
execution: passive
init:
  description: Initializes static configuration for algorithm.
connectors:
  - { description: Run algorithm, type: Tick.T, kind: recv_sync }
  - { description: Fetch data product, type: Data_Product_Fetch.T,
      return_type: Data_Product_Return.T, kind: request }
  - { description: Data product output, type: Data_Product.T, kind: send }
```

### Implementation Body -- Key Patterns
```ada
-- Init: create handle + set initial config
overriding procedure Init (Self : in out Instance) is
begin
   Self.Alg := Create;
   declare
      Sigma_Set : constant Packed_F32x3_Record.C.U_C := (Value => [0.01, 0.05, -0.55]);
   begin
      Set_Sigma_R0R (Self.Alg, Sigma_Set);
   end;
end Init;

-- Tick: fetch dependencies → convert → call C → convert back → send
overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
   use Algorithm_Wrapper_Util;
   Ref : Att_Ref.T;
   Ref_Status : constant Data_Dependency_Status.E :=
      Self.Get_Attitude_Reference (Value => Ref, Stale_Reference => Arg.Time);
   Nav : Nav_Att.T;
   Nav_Status : constant Data_Dependency_Status.E :=
      Self.Get_Navigation_Attitude (Value => Nav, Stale_Reference => Arg.Time);
begin
   if Is_Dep_Status_Success (Ref_Status) and then Is_Dep_Status_Success (Nav_Status) then
      declare
         Ref_C : aliased Att_Ref.C.U_C := Att_Ref.C.To_C (Att_Ref.Unpack (Ref));
         Nav_C : aliased Nav_Att.C.U_C := Nav_Att.C.To_C (Nav_Att.Unpack (Nav));
         Guid  : constant Att_Guid.C.U_C := Update (
            Self.Alg, Current_Sim_Nanos => 0,
            Att_Ref_In => Ref_C'Unchecked_Access,
            Att_Nav_In => Nav_C'Unchecked_Access);
      begin
         Self.Data_Product_T_Send (Self.Data_Products.Attitude_Guidance (
            Arg.Time, Att_Guid.Pack (Att_Guid.C.To_Ada (Guid))));
      end;
   end if;
end Tick_T_Recv_Sync;
```

### Test Case
```ada
overriding procedure Test (Self : in out Instance) is
   T : ... renames Self.Tester;
begin
   T.Attitude_Reference := (
      Sigma_Rn => [0.35, -0.25, 0.15],
      Omega_Rn_N => [0.018, -0.032, 0.015],
      Domega_Rn_N => [0.048, -0.022, 0.025]);
   T.Navigation_Attitude := (
      Time_Tag => 0.0,
      Sigma_Bn => [0.25, -0.45, 0.75],
      Omega_Bn_B => [-0.015, -0.012, 0.005],
      Veh_Sun_Pnt_Bdy => [0.0, 0.0, 0.0]);

   T.Tick_T_Send ((Time => T.System_Time, Count => 0));

   Natural_Assert.Eq (T.Attitude_Guidance_History.Get_Count, 1);
   Att_Guid_Assert.Eq (T.Attitude_Guidance_History.Get (1), (
      Sigma_Br => [0.18368415, -0.09744478, -0.0989607],
      Omega_Br_B => [-0.01181208, -0.00891603, -0.03441226],
      Omega_Rn_B => [-0.00318792, -0.00308397, 0.03941226],
      Domega_Rn_B => [-0.02388623, -0.028356, 0.04514848]),
      Epsilon => 0.001);
end Test;
```

---

## Rate Control -- Wrapper with Parameters

### Additional Patterns
This component adds `Parameter_Update.T` modify connector for runtime-tunable gains.

### Ada Binding -- Setter Functions
```ada
procedure Set_Spacecraft_Inertia
  (Self : Rate_Control_Algorithm_Access;
   Vehicle_Config_In : Vehicle_Config.C.U_C_Access)
  with Import => True, Convention => C, ...;

procedure Set_Derivative_Gain_P
  (Self : Rate_Control_Algorithm_Access;
   P    : Short_Float)
  with Import => True, Convention => C, ...;
```

### Update_Parameters_Action
Called automatically when parameters are staged+committed. Pushes Ada parameter values to C++ algorithm:

```ada
overriding procedure Update_Parameters_Action (Self : in out Instance) is
   Vehicle_Config_C : aliased Vehicle_Config.C.U_C := (
      Iscpnt_B_B => Packed_F32x9.C.To_C (Self.Spacecraft_Inertia),
      Co_M_B => [0.0, 0.0, 0.0],
      Mass_Sc => 0.0,
      Current_Adcsstate => 0);
begin
   Set_Spacecraft_Inertia (Self.Alg, Vehicle_Config_C'Unchecked_Access);
   Set_Derivative_Gain_P (Self.Alg, Self.Derivative_Gain_P.Value);
end Update_Parameters_Action;
```

### Tick with Parameter Update
```ada
overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
begin
   Self.Update_Parameters;  -- Apply any staged parameter changes FIRST
   -- Then fetch dependencies and call algorithm...
end;
```

---

## Ephem Nav Converter -- Simple Single-Input Wrapper

Simplest pattern: one input dependency, one output, no parameters.

```c
// C shim: single input pointer, returns output by value
NavTransMsgF32Payload EphemNavConverterAlgorithm_update(
    EphemNavConverterAlgorithm* self,
    uint64_t callTime,
    const EphemerisMsgF32Payload* ephemerisInMsg);
```

---

## Algorithm_Wrapper_Util -- Shared Utility

Used by ALL wrapper components for consistent data dependency error handling:

```ada
package Algorithm_Wrapper_Util is
   function Is_Dep_Status_Success (Status : Data_Dependency_Status.E) return Boolean;
   -- Success → True, Not_Available/Stale → False, Error → Assert False
end;
```
