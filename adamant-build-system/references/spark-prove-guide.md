<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# SPARK Formal Verification in Adamant

## Overview

Adamant provides integrated support for SPARK formal verification through GNATprove. SPARK is a subset of Ada with contracts (preconditions, postconditions, data dependencies) that enables mathematical proof of program correctness.

## How to Add SPARK Verification to a Component

### 1. Enable SPARK Mode in Source Files

Add `SPARK_Mode => On` to both package specification and body:

```ada
-- my_component.ads
package My_Component with
   SPARK_Mode => On
is
   procedure Do_Something (X : in out Integer)
      with Global => null,           -- No global variables accessed
           Depends => (X => X),       -- X depends only on X
           Pre => X < Integer'Last,   -- Precondition
           Post => X = X'Old + 1;     -- Postcondition

end My_Component;
```

```ada
-- my_component.adb
package body My_Component with
   SPARK_Mode => On
is
   procedure Do_Something (X : in out Integer) is
   begin
      X := X + 1;
   end Do_Something;
end My_Component;
```

### 2. Create Prove Configuration

Create `all.prove.yaml` in the component directory:

```yaml
---
description: GNATprove configuration for My_Component
level: 2        # Proof difficulty level (0-4)
mode: "silver"  # Analysis mode
```

### 3. Run SPARK Verification

From the component directory:

```bash
redo prove
```

The prove target will:
1. Use the `Linux_Prove` build target
2. Set `SAFE_COMPILE=True` to analyze all dependencies
3. Run GNATprove with the configured switches
4. Output results to `build/prove/prove.txt`

## all.prove.yaml Configuration Reference

### Available Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `description` | string | No | - | Human-readable description of the configuration |
| `level` | integer | No | 2 | Proof effort level (0-4) |
| `mode` | string | No | "gold" | Analysis mode |

### Level Options (0-4)

| Level | Equivalent Switches | Description |
|-------|-------------------|-------------|
| 0 | `--prover=cvc4 --timeout=1 --memlimit=1000 --steps=0 --counterexamples=off` | Minimal effort |
| 1 | `--prover=cvc4,z3,altergo --timeout=1 --memlimit=1000 --steps=0 --counterexamples=off` | Multiple provers, short timeout |
| 2 | `--prover=cvc4,z3,altergo --timeout=5 --memlimit=1000 --steps=0 --counterexamples=on` | **Default**, balanced effort |
| 3 | `--prover=cvc4,z3,altergo --timeout=20 --memlimit=2000 --steps=0 --counterexamples=on` | Increased timeout and memory |
| 4 | `--prover=cvc4,z3,altergo --timeout=60 --memlimit=2000 --steps=0 --counterexamples=on` | Maximum effort |

### Mode Options

| Mode | Purpose |
|------|---------|
| `check` | Basic syntax and type checking only |
| `check_all` | Extended checking including unused variables |
| `flow` | Flow analysis (data and control flow) |
| `prove` | Proof of contracts and absence of runtime errors |
| `all` | Both flow analysis and proof |
| `stone` | Minimal analysis (equivalent to `check`) |
| `bronze` | Basic flow analysis |
| `silver` | **Recommended**, flow + proof of easy conditions |
| `gold` | **Default**, comprehensive analysis |

## Build System Integration

### How Prove Works

1. **Target Selection**: Always uses `Linux_Prove` target (inherits from `Linux_Debug`)
2. **Source Discovery**: Finds all `.o` files that can be built in current directory
3. **Source Resolution**: Maps object files back to Ada source files
4. **Dependency Building**: Builds all Ada dependencies recursively with `SAFE_COMPILE=True`
5. **GNATprove Execution**: Runs GNATprove with configured switches

### Generated Command

The build system generates a GNATprove command like:

```bash
gnatprove -j0 --checks-as-errors=on --level=2 --mode=silver \
  -aP $ADAMANT_DIR/redo/targets/gpr \
  -P linux_debug.gpr \
  -XADAMANT_DIR=$ADAMANT_DIR \
  -XOBJECT_DIR=build/prove \
  -XSOURCE_DIRS=dir1,dir2,... \
  source1.ads source2.adb ...
```

### Environment Overrides

You can override prove switches:

```bash
PROVE_SWITCHES="--level=4 --mode=gold" redo prove
```

### Output Location

- Prove results: `build/prove/prove.txt`
- All output goes to stderr and the log file

## SPARK Contract Examples

### Data Dependencies

```ada
procedure Process (Input : Integer; Output : out Integer; Counter : in out Integer)
   with Global => (Input => Some_Global_Const,          -- Reads Some_Global_Const
                   In_Out => Some_Global_Var),          -- Reads and writes Some_Global_Var
        Depends => (Output => Input,                     -- Output depends on Input
                    Counter => Counter,                  -- Counter depends on previous Counter
                    Some_Global_Var => (Some_Global_Var, Input));  -- Global depends on both
```

### Preconditions and Postconditions

```ada
procedure Increment (X : in out Integer)
   with Pre => X < Integer'Last,       -- Must not overflow
        Post => X = X'Old + 1;         -- Increments by exactly 1

procedure Divide (Dividend : Integer; Divisor : Integer; Result : out Integer)
   with Pre => Divisor /= 0,           -- Division by zero check
        Post => abs (Result * Divisor - Dividend) < abs (Divisor);  -- Remainder property
```

### Ghost Code for Verification

```ada
with Ghost_Data with Ghost;  -- Ghost package import

procedure Complex_Algorithm (Data : in out Array_Type)
   with Post => (for all I in Data'Range => Data(I) >= Data'Old(I))  -- Never decreases values
is
   -- Ghost variables for proof assistance
   Original_Sum : Integer with Ghost := Sum_Array(Data);
begin
   -- Algorithm implementation
   for I in Data'Range loop
      if Data(I) < 0 then
         Data(I) := abs(Data(I));
      end if;
   end loop;
   
   pragma Assert (Sum_Array(Data) >= Original_Sum);  -- Ghost assertion for proof
end Complex_Algorithm;
```

## SPARK Mode Gotchas and Limitations

### 1. Access Types Not Allowed

SPARK doesn't support general access types (pointers). Adamant's generated memory map and register map packages handle this by providing access types in a nested package with `SPARK_Mode => Off`:

```ada
package Memory_Map with SPARK_Mode => On is
   -- Memory mapped variables here
   
   package Accesses with SPARK_Mode => Off is
      -- Access types here since they're not allowed in SPARK
      Data_Access : constant Data_Type_Access := Data'Access;
   end Accesses;
end Memory_Map;
```

### 2. Command Handlers May Need SPARK_Mode(Off)

Command handlers often need to:
- Access global state in complex ways
- Use access types for data structures
- Perform operations not easily provable

If a command handler can't be made SPARK-compliant, disable SPARK for that specific subprogram:

```ada
procedure Handle_Command (Self : in out Instance; Cmd : in Command.T)
   with SPARK_Mode => Off  -- Disable SPARK for this procedure only
is
begin
   -- Complex command handling that's difficult to prove
end Handle_Command;
```

### 3. Tasking Restrictions

SPARK has restrictions on Ada tasking. Most Adamant components work within these restrictions, but complex tasking patterns may need `SPARK_Mode => Off`.

### 4. Exception Handling

SPARK doesn't support exception handling. Use preconditions and runtime checks instead:

```ada
-- Instead of:
-- begin
--    risky_operation;
-- exception
--    when Constraint_Error => handle_error;
-- end;

-- Use preconditions:
procedure Safe_Operation (Index : Natural)
   with Pre => Index in Valid_Range
is
begin
   -- Safe operation that won't raise exceptions
end Safe_Operation;
```

### 5. File I/O and External Interfaces

File I/O and external system calls are generally not provable and should be in `SPARK_Mode => Off` regions.

## Best Practices

### 1. Start Simple

Begin with `mode: "silver"` and `level: 1` or `2`. Increase difficulty as your contracts improve.

### 2. Incremental Adoption

You don't need to make everything SPARK-compliant at once:
- Start with pure computational procedures
- Add contracts gradually
- Use `SPARK_Mode => Off` for complex parts initially

### 3. Use Ghost Code

Ghost variables, functions, and assertions help provers understand your intent:

```ada
function Is_Sorted (Arr : Array_Type) return Boolean with Ghost;

procedure Sort (Data : in out Array_Type)
   with Post => Is_Sorted(Data)
is
   -- Implementation with ghost assertions to help proof
   pragma Assert (Is_Sorted(Data(1..N)));  -- Loop invariant
end Sort;
```

### 4. Understand Proof Failures

Common proof failures and solutions:

- **"precondition might fail"** → Add stronger precondition or runtime check
- **"postcondition might fail"** → Strengthen implementation or weaken postcondition
- **"overflow check might fail"** → Add range constraints or preconditions
- **"divide by zero might fail"** → Add `Divisor /= 0` precondition

### 5. Testing Still Required

SPARK proves absence of runtime errors and contract compliance, but doesn't prove functional correctness. You still need comprehensive testing.

## Example: Complete SPARK Component

```yaml
# all.prove.yaml
---
description: SPARK verification for Safe_Counter component
level: 2
mode: "silver"
```

```ada
-- safe_counter.ads
package Safe_Counter with SPARK_Mode => On is
   
   type Counter_Type is range 0 .. 1000;
   
   type Instance is tagged private;
   
   procedure Initialize (Self : out Instance)
      with Post => Get_Value(Self) = 0;
   
   procedure Increment (Self : in out Instance)
      with Pre => Get_Value(Self) < Counter_Type'Last,
           Post => Get_Value(Self) = Get_Value(Self'Old) + 1;
   
   procedure Reset (Self : in out Instance)
      with Post => Get_Value(Self) = 0;
   
   function Get_Value (Self : Instance) return Counter_Type;

private
   type Instance is tagged record
      Value : Counter_Type := 0;
   end record;
   
end Safe_Counter;
```

```ada
-- safe_counter.adb
package body Safe_Counter with SPARK_Mode => On is

   procedure Initialize (Self : out Instance) is
   begin
      Self.Value := 0;
   end Initialize;

   procedure Increment (Self : in out Instance) is
   begin
      Self.Value := Self.Value + 1;
   end Increment;

   procedure Reset (Self : in out Instance) is
   begin
      Self.Value := 0;
   end Reset;

   function Get_Value (Self : Instance) return Counter_Type is
   begin
      return Self.Value;
   end Get_Value;

end Safe_Counter;
```

Run verification:

```bash
cd path/to/safe_counter
redo prove
```

This example would successfully prove:
- No integer overflow (Counter_Type range prevents it)
- Contracts are satisfied
- No runtime errors possible

## Integration with Other Build Targets

SPARK verification integrates with other Adamant build targets:

```bash
redo style          # Style check (includes Ada warnings)
redo prove          # SPARK formal verification  
redo test           # Unit testing with AUnit
redo coverage       # Code coverage analysis
redo analyze        # GNAT SAS static analysis
```

Use all these together for comprehensive code quality assurance.