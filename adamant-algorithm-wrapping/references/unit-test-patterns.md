# Unit Test Patterns for Algorithm Wrapper Components

## Prerequisites

### Component in build path
```bash
cd src/components/<component_name>
touch .all_path
```

### Algorithm in fp32-fsw-xmera library
```bash
# Check if algorithm is in build
grep -r "<algorithm_name>" /home/user/fp32-fsw-xmera/CMakeLists.txt

# If not found, add to algorithms list in CMakeLists.txt:
# set(algorithms "attTrackingError" "<algorithm_name>")

# Rebuild library
cd /home/user/fp32-fsw-xmera
./clean.sh
./build.sh linux-gcc-debug

# Verify symbols exist
nm /home/user/fp32-fsw-xmera/build/linux-gcc-debug/lib/libgncAlgorithms.a | grep -i <algorithm_name>
```

## Setup Files

### tests.yaml
```yaml
---
description: Unit test suite for the <Component Name> component
tests:
  - name: Test
    description: Run algorithm to ensure integration is sound.
```

### env.py
```python
from environments import test  # noqa: F401
```

### Generate and copy templates
```bash
cd src/components/<component_name>/test
redo templates
cp build/template/*.ad[sb] .
```

## Test Body Template (Loop-Based)

```ada
with Basic_Assertions; use Basic_Assertions;
with <Output_Type>.Assertion; use <Output_Type>.Assertion;
with Packed_F32x3.Assertion; use Packed_F32x3.Assertion;

package body <Component_Name>_Tests.Implementation is

   overriding procedure Set_Up_Test (Self : in out Instance) is
   begin
      Self.Tester.Init_Base;
      Self.Tester.Connect;
      Self.Tester.Component_Instance.Init;
      Self.Tester.Component_Instance.Set_Up;
   end Set_Up_Test;

   overriding procedure Tear_Down_Test (Self : in out Instance) is
   begin
      Self.Tester.Component_Instance.Destroy;
      Self.Tester.Final_Base;
   end Tear_Down_Test;

   overriding procedure Test (Self : in out Instance) is
      T : Component.<Name>.Implementation.Tester.Instance_Access renames Self.Tester;

      type Test_Vector is record
         Input_1 : <Type_1>.T;
         Expected : <Out_Type>.T;
      end record;

      Cases : constant array (1 .. N) of Test_Vector := [
         (Input_1 => (...), Expected => (...)),
         -- more cases from Python test
      ];
   begin
      for I in Cases'Range loop
         T.<Dep_1_Name> := Cases (I).Input_1;

         T.Tick_T_Send ((Time => T.System_Time, Count => 0));

         Natural_Assert.Eq (T.<Output>_History.Get_Count, I);

         declare
            Output : constant <Out_Type>.T := T.<Output>_History.Get (I);
         begin
            Packed_F32x3_Assert.Eq (
               Output.<Field>,
               Cases (I).Expected.<Field>,
               Epsilon => 0.0001);
         end;
      end loop;
   end Test;

end <Component_Name>_Tests.Implementation;
```

## Test Body Template (Multiple Configurations)

When testing different Init parameters, skip Init/Set_Up in Set_Up_Test:

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   -- Skip Init/Set_Up here -- called manually per configuration
end Set_Up_Test;

overriding procedure Test (Self : in out Instance) is
   T : Component.<Name>.Implementation.Tester.Instance_Access renames Self.Tester;
begin
   -- Configuration A
   T.Component_Instance.Init (Param => value_a);
   T.Component_Instance.Set_Up;
   T.<Dep> := test_value;
   T.Tick_T_Send ((Time => T.System_Time, Count => 0));
   Natural_Assert.Eq (T.<Output>_History.Get_Count, 1);
   T.Component_Instance.Destroy;

   -- Configuration B
   T.Component_Instance.Init (Param => value_b);
   T.Component_Instance.Set_Up;
   T.<Dep> := test_value;
   T.Tick_T_Send ((Time => T.System_Time, Count => 0));
   Natural_Assert.Eq (T.<Output>_History.Get_Count, 2);  -- Accumulated!
   T.Component_Instance.Destroy;
end Test;
```

## Critical Rules

### ALWAYS use T.System_Time for Tick
```ada
-- CORRECT:
T.Tick_T_Send ((Time => T.System_Time, Count => 0));

-- WRONG (causes staleness issues):
T.Tick_T_Send ((Time => (0, 0), Count => 0));
```

### Work with .T (packed) types, NOT .U (unpacked)
```ada
-- CORRECT:
Att : constant Nav_Att.T := (
   Sigma_Bn => [0.1, 0.01, -0.1],
   Omega_Bn_B => [1.0, 1.0, -1.0],
   ...);

-- WRONG (unnecessary Pack/Unpack):
Att : constant Nav_Att.T := Nav_Att.Pack ((
   Sigma_Bn => [0.1, 0.01, -0.1], ...));
```

### Array aggregates: direct, not record wrapper
```ada
-- CORRECT (Packed_F32x3.T is an array type):
Sigma_Bn => [0.1, 0.01, -0.1]

-- WRONG (this is for Packed_F32x3_Record.U):
Sigma_Bn => (Value => [0.1, 0.01, -0.1])
```

### T rename pattern
```ada
T : Component.<Name>.Implementation.Tester.Instance_Access renames Self.Tester;
```

### History counts accumulate
When running multiple test cases in one procedure, history Get_Count keeps incrementing:
```ada
-- After case 1: Get_Count = 1
-- After case 2: Get_Count = 2
Natural_Assert.Eq (T.<Output>_History.Get_Count, I);
```

### Destroy before re-init
When testing multiple configurations:
```ada
T.Component_Instance.Destroy;
T.Component_Instance.Init (new_params);
T.Component_Instance.Set_Up;
```

## Setting Data Dependencies

Dependencies are set directly on the tester:
```ada
T.<Dependency_Name> := <value>;
```

The tester's reciprocal returns this value when the component fetches the dependency.

## Assertion Types

| For type | Use assertion |
|----------|-------------|
| `Natural` | `Natural_Assert.Eq` |
| `Packed_F32x3.T` fields | `Packed_F32x3_Assert.Eq (..., Epsilon => 0.0001)` |
| Full record comparison | `<Type>_Assert.Eq (..., Epsilon => 0.0001)` |

## How Many Test Cases?

- If Python test is simple: replicate it
- If Python test is complex (16+ parametrized cases): select 3-5 representative cases
- Goal: verify Ada-to-C++ binding works, not exhaustive algorithm testing
- C++ algorithm already has comprehensive unit tests

## Common Pitfalls

1. **Using .U types** -- Always use .T in tests
2. **Wrong array syntax** -- `[x, y, z]` not `(Value => [x, y, z])`
3. **Using (0,0) for Tick time** -- Use `T.System_Time`
4. **Not using T rename** -- Convention and readability
5. **Forgetting Destroy between configs** -- Causes resource leak
6. **Not calling Set_Up after Init** -- Both required
7. **Wrong epsilon** -- Typically 0.0001 for F32, 0.000001 for F64

## Troubleshooting

- **"no selector 'Tester'"**: Component not in build path (missing `.all_path`)
- **Undefined reference to algorithm functions**: Algorithm not in libgncAlgorithms.a
- **Wrong output values**: Check C struct field order matches Ada record
- **AUnit not found**: Missing `env.py` in test directory
- **Test crashes**: Component not properly initialized/destroyed

## Reference Examples

- `adamant-xmera-components/src/components/sunline_ephem/test/` -- Simple loop-based
- `adamant-xmera-components/src/components/attitude_tracking_error/test/` -- Single case with T rename
- `adamant-xmera-components/src/components/nav_aggregate/test/` -- Multiple configurations
