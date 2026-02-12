---
name: adamant-testing
description: Comprehensive testing patterns and infrastructure for Adamant embedded software framework components
---

# Adamant Testing Framework

Complete guide to testing Adamant components using auto-generated testers, history capture, and data dependency mocking.

## Test Structure Overview

```
component_name/test/
├── component_name.tests.yaml                # Test model (required)
├── test.adb                                # Standard AUnit runner (generated)
├── env.py                                  # Build path (required, NOT auto-generated)
├── component-component_name-implementation-tester.ads/adb  # Generated tester
├── component_name_tests-implementation.ads/adb            # Handwritten tests
├── test.do                                 # Build and run
└── output.txt.do                           # Capture output
```

**CRITICAL:** Test directories must NOT contain `.all_path`. Use `env.py` only. Having `.all_path` in test directories causes duplicate `test.adb` conflicts across components.

## Test Model (.tests.yaml)

```yaml
description: Unit test suite description (optional)
tests:
  - name: Test_Nominal_Operation            # Becomes Ada procedure name
    description: Test description (optional)
  - name: Test_Error_Conditions
    description: Test all error paths
  - name: Test_Queue_Overflow              # For active components
    description: Test async queue overflow
```

## Test Environment Setup

**Minimum env.py** (required for AUnit and test build paths):
```python
from environments import test  # noqa: F401
```

**Extended env.py** (for extra build paths, e.g., mock dependencies):
```python
from environments import test, modify_build_path  # noqa: F401
import os
this_dir = os.path.dirname(os.path.realpath(__file__))
modify_build_path.add_to_build_path([this_dir, this_dir + os.sep + ".."])
```

**test.adb structure:**
```ada
with AUnit.Reporter.Text;
with AUnit.Run;
with Component_Name_Tests.Implementation.Suite;

procedure Test is
   procedure Runner is new AUnit.Run.Test_Runner (Component_Name_Tests.Implementation.Suite.Get);
   Reporter : AUnit.Reporter.Text.Text_Reporter;
begin
   AUnit.Reporter.Text.Set_Use_ANSI_Colors (Reporter, True);
   Runner (Reporter);
end Test;
```

## Tester Generation and Architecture

### Reciprocal Component Pattern

Testers are **reciprocal components** with inverted connectors:
- Component's outgoing connectors become tester's incoming (capture outputs)
- Component's incoming connectors become tester's outgoing (provide inputs)  
- Tester contains component instance and connector histories

### Generated Tester Structure

```ada
package Component.Example_Component.Implementation.Tester is
   use Component.Example_Component_Reciprocal;
   
   -- History packages for each connector type
   package Event_T_Recv_Sync_History_Package is new Printable_History (...);
   package Data_Product_T_Recv_Sync_History_Package is new Printable_History (...);
   
   type Instance is new Component.Example_Component_Reciprocal.Base_Instance with record
      Component_Instance : aliased Component.Example_Component.Implementation.Instance;
      -- Connector histories
      Event_T_Recv_Sync_History : Event_T_Recv_Sync_History_Package.Instance;
      -- Individual typed histories (events, data products, faults)
      Specific_Event_History : Specific_Event_History_Package.Instance;
   end record;
   
   -- Lifecycle
   procedure Init_Base (Self : in out Instance; [Queue_Size : in Natural]);
   procedure Final_Base (Self : in out Instance);
   procedure Connect (Self : in out Instance);
   
   -- Connector primitives (capture component outputs)
   overriding procedure Event_T_Recv_Sync (Self : in out Instance; Arg : in Event.T);
end Component.Example_Component.Implementation.Tester;
```

### Tester Implementation Pattern

```ada
procedure Init_Base (Self : in out Instance; Queue_Size : in Natural) is
begin
   -- Initialize component heap (for active components)
   Self.Component_Instance.Init_Base (Queue_Size => Queue_Size);
   
   -- Initialize tester histories
   Self.Event_T_Recv_Sync_History.Init (Depth => 20);
   Self.Specific_Event_History.Init (Depth => 20);
end Init_Base;

procedure Connect (Self : in out Instance) is
begin
   -- Wire component outputs to tester inputs
   Self.Component_Instance.Attach_Event_T_Send (Self'Unchecked_Access, Self.Event_T_Recv_Sync_Access);
   -- Wire tester outputs to component inputs
   Self.Attach_Tick_T_Send (Self.Component_Instance'Unchecked_Access, Self.Component_Instance.Tick_T_Recv_Sync_Access);
end Connect;

overriding procedure Event_T_Recv_Sync (Self : in out Instance; Arg : in Event.T) is
begin
   Self.Event_T_Recv_Sync_History.Push (Arg);  -- Raw event capture
   Self.Dispatch_Event (Arg);                  -- Route to specific handlers
end Event_T_Recv_Sync;
```

## Test Implementation Patterns

### Standard Test Setup

```ada
package Component_Name_Tests.Implementation is
   type Instance is new Component_Name_Tests.Base_Instance with private;
private
   overriding procedure Set_Up_Test (Self : in out Instance);
   overriding procedure Tear_Down_Test (Self : in out Instance);
   -- Test procedures match .tests.yaml names
   overriding procedure Test_Nominal_Operation (Self : in out Instance);
   
   type Instance is new Component_Name_Tests.Base_Instance with record
      null; -- Add test-specific state if needed
   end record;
end Component_Name_Tests.Implementation;
```

### Test Lifecycle Implementation

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   -- For passive components:
   Self.Tester.Init_Base;
   
   -- For active components (provide queue size):
   Self.Tester.Init_Base (Queue_Size => Self.Tester.Component_Instance.Get_Max_Queue_Element_Size * 3);
   
   -- Wire and initialize
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;

overriding procedure Tear_Down_Test (Self : in out Instance) is
begin
   Self.Tester.Final_Base;
end Tear_Down_Test;
```

### Tester Alias Convention

```ada
overriding procedure Test_Name (Self : in out Instance) is
   T : Component.Name.Implementation.Tester.Instance_Access renames Self.Tester;
begin
   -- Test implementation using T shorthand
end Test_Name;
```

## History API and Verification Patterns

### History Core Operations

```ada
-- Check counts first (prevents constraint errors)
Natural_Assert.Eq (T.Event_T_Recv_Sync_History.Get_Count, 3);

-- Access entries (1-indexed, 1 = oldest)
Event_Assert.Eq (T.Event_T_Recv_Sync_History.Get (1), expected_event);
Event_Assert.Eq (T.Event_T_Recv_Sync_History.Get (2), expected_event_2);

-- Check for empty/unexpected results
Boolean_Assert.Eq (T.Error_Event_History.Is_Empty, True);

-- Clear between test phases
T.Event_T_Recv_Sync_History.Clear;

-- Meta operations
Natural_Assert.Eq (T.History.Get_Depth, 20);  -- Configured depth
Boolean_Assert.Eq (T.History.Is_Full, False);
```

### Visibility in Test Bodies

Command return type: `Command_Enums.Command_Execution_Status.E` (not standalone `Command_Execution_Status`).
```ada
with Command_Enums;
use type Command_Enums.Command_Execution_Status.E;
-- Then: Assert (Status = Command_Enums.Command_Execution_Status.Success, "...");
```

### Sending Stimuli

```ada
-- Tick (requires both Time and Count):
T.Tick_T_Send ((Time => (0, 0), Count => 1));

-- Command (with arg_type):
T.Command_T_Send (T.Commands.My_Command ((Arg_Field => Value)));

-- Command (no args):
T.Command_T_Send (T.Commands.My_Noop_Command);

-- Arrayed connector (index, then value):
T.Packed_Sensor_Reading_T_Send (Channel_Index, Reading);

-- Parameter update (3-step: stage, validate, update, then tick):
Status := T.Stage_Parameter (T.Parameters.Param_Name ((Field => Value)));
Status := T.Validate_Parameters;  -- Calls component's Validate_Parameters
Status := T.Update_Parameters;    -- Marks ready_to_update
T.Tick_T_Send (The_Tick);          -- Component calls Self.Update_Parameters in tick
-- Parameter_Update_Status type: Parameter_Enums.Parameter_Update_Status.E

-- Commands and parameters: ALWAYS use T.Commands and T.Parameters (tester accessors)
-- NEVER create local Command/Parameter instances -- they lack proper ID bases
T.Command_T_Send (T.Commands.Set_Value ((Value => 42)));  -- correct
-- Local_Cmds : Commands.Instance; ... Local_Cmds.Set_Value(...)  -- WRONG, crashes

-- Command ID access (getter function, not field):
Cmd_Id := T.Commands.Get_Reset_Counter_Id;  -- NOT T.Commands.Reset_Counter_Id

-- Assertion imports: use Basic_Assertions and typed assertion child packages:
-- with Basic_Assertions; use Basic_Assertions;  -- for Natural_Assert
-- with Packed_U32.Assertion; use Packed_U32.Assertion;  -- for typed packed assertions

-- DANGER: `cp build/template/* .` OVERWRITES hand-written files if names match.
-- Only copy templates ONCE at initial setup, or copy selectively.

-- Request connector: override tester's *_T_Service to return test data:
-- Default returns uninitialized Data_Product_Return.T (fetch will fail).
-- In tester .adb, set To_Return.The_Status := Data_Product_Enums.Fetch_Status.Success;
```

## Dual-Level Capture Pattern

### Events, Data Products, and Faults

All typed outputs use **dual-level capture**:

**1. Raw connector-level capture:**
```ada
T.Event_T_Recv_Sync_History.Get_Count        -- All events
T.Data_Product_T_Recv_Sync_History.Get_Count -- All data products
T.Fault_T_Recv_Sync_History.Get_Count        -- All faults
```

**2. Individual typed capture:**
```ada
T.Specific_Event_History.Get_Count            -- Just this event type
T.Counter_Data_Product_History.Get_Count      -- Just this data product
T.Timeout_Fault_History.Get_Count             -- Just this fault type
```

**Implementation pattern:**
```ada
-- Raw capture + dispatch
overriding procedure Event_T_Recv_Sync (Self : in out Instance; Arg : in Event.T) is
begin
   Self.Event_T_Recv_Sync_History.Push (Arg);
   Self.Dispatch_Event (Arg);  -- Routes to individual handlers
end Event_T_Recv_Sync;

-- Individual handler captures typed parameters
overriding procedure Specific_Event (Self : in out Instance; Arg : in Typed_Param.T) is
begin
   Self.Specific_Event_History.Push (Arg);
end Specific_Event;
```

## Component Type Testing Patterns

See [references/testing-patterns-detail.md](references/testing-patterns-detail.md) for detailed patterns:
- Command testing (send, verify response, invalid command handling)
- Event testing (param extraction, typed assertion)
- Data product testing (value extraction, typed assertion)
- Parameter testing (3-step: Stage -> Validate -> Update + tick)
- Fault testing (trigger, verify, clear)
- Data dependency testing (mock via tester, staleness, error injection)

## Build and Test Execution

### Test Build Commands

```bash
redo test                    # Build and run tests
redo templates              # Generate test stubs if needed  
redo clean                  # Clean test artifacts
```

### Build File Patterns

**test.do:**
```bash
bin=build/bin/Linux_Test/test.elf
redo-ifchange $bin
$bin 1>&2 | true
```

**output.txt.do:**
```bash
redo-ifchange build/bin/Linux_Test/test.elf
build/bin/Linux_Test/test.elf 2>&1 | sed 's,\x1B\[[0-9;]*[a-zA-Z],,g' > $3 | true
```

## Assertion Preference Order

Use this hierarchy (most preferred first):

1. **Packed type assertions** (preferred): `Packed_U32_Assert.Eq(...)`, `Packed_F32_Assert.Eq(...)`, `Event_Assert.Eq(...)` -- type-safe, clear error messages, match framework conventions
2. **Smart_Assert pattern**: `Smart_Assert.Eq(actual, expected)` -- generic, works with any type that has Image
3. **Basic_Assertions**: `Natural_Assert.Eq(...)`, `Boolean_Assert.Eq(...)` -- for counts, flags
4. **AUnit Assert** (fallback): `Assert(condition, "message")` -- only when no typed assertion fits

```ada
-- PREFERRED: packed type assertion for data product comparison
Packed_U32_Assert.Eq (T.Counter_History.Get (1), (Value => 42));

-- GOOD: smart assert for custom types
Smart_Assert.Eq (T.Custom_History.Get (1).Field, Expected_Value);

-- OK: basic assertion for counts
Natural_Assert.Eq (T.Event_T_Recv_Sync_History.Get_Count, 3);

-- FALLBACK: AUnit assert when nothing else fits
Assert (Status = Success, "Expected success status");
```

Import the assertion packages you need:
```ada
with Basic_Assertions; use Basic_Assertions;           -- Natural_Assert, Boolean_Assert
with Packed_U32.Assertion; use Packed_U32.Assertion;   -- Packed_U32_Assert
with Smart_Assert;                                      -- Smart_Assert.Eq
with AUnit.Assertions; use AUnit.Assertions;           -- Assert (fallback)
```

## Common Test Errors (Do NOT Make These)

1. **Wrong stimulus API**: Use `T.Tick_T_Send(...)` NOT `T.Tick_T_Recv_Sync(...)`. The tester SENDS to the component under test. `_Recv_Sync` is what the tester receives FROM the component (event/DP/fault capture).

2. **History `.Value` accessor in comparisons**: `T.Pet_Count_History.Get(N)` returns `Packed_U32.T` directly. Compare with `Packed_U32_Assert.Eq(T.Pet_Count_History.Get(1), (Value => 42))`. Do NOT write `.Get(1).Value` then compare to a packed record -- type mismatch.

3. **Tick.T.Count is Unsigned_32**: When using loop variable casts, use `Interfaces.Unsigned_32(I)` not `Unsigned_16`. Add `with Interfaces;` to the test body if needed.

4. **Missing imports in test body**: Test bodies need explicit `with` for packages used: `with Interfaces;`, `with Basic_Assertions; use Basic_Assertions;`, typed assertion packages like `with Packed_U32.Assertion; use Packed_U32.Assertion;`.

5. **Tester file confusion**: The tester `.ads` is generated (in `build/template/`). The tester `.adb` is hand-written. Copy templates to `test/` ONCE at initial setup. Files in `test/` override generated templates.

## Testing Best Practices

### Test Organization

1. **Always check counts before content** - prevents constraint errors
2. **Clear histories between test phases** - prevents test pollution  
3. **Test both success and failure paths** - comprehensive coverage
4. **Use tester alias `T`** - improves readability
5. **Verify exact expected outputs** - not just counts

### Async Component Testing

1. **Always Dispatch_All before checking results**
2. **Calculate queue sizes appropriately** - `component.Get_Max_Queue_Element_Size * N`
3. **Test queue overflow scenarios** - use Expect_*_Dropped
4. **Batch operations where logical** - send multiple, dispatch once

### Data Dependency Testing

1. **Test fresh, stale, and missing data scenarios**
2. **Verify algorithm behavior under each condition**
3. **Use realistic mock data** - avoid all-zeros
4. **Test data validation logic** - invalid ranges, corrupt data

### Error Testing Strategy

- **Invalid command arguments** - wrong length, out of range values
- **Queue overflow conditions** - full async queues
- **Dropped message scenarios** - downstream component failures  
- **Resource exhaustion** - memory, table space
- **Timing edge cases** - stale data, timeout conditions

The Adamant testing framework provides comprehensive white-box testing through reciprocal components, history capture, and sophisticated mocking capabilities. Master these patterns for robust component verification.