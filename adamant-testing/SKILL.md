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

-- Command:
T.Command_T_Send (T.Commands.My_Command ((Arg_Field => Value)));

-- Data product:
T.Data_Product_T_Send ((Header => ..., Buffer => ...));
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

### Command Component Testing

```ada
-- Send commands via tester helpers
T.Command_T_Send (T.Commands.Set_Value ((Value => 42)));
T.Command_T_Send (T.Commands.No_Arg_Command);

-- Verify responses
Natural_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get_Count, 1);
Command_Response_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get (1), (
   Source_Id => 0,
   Registration_Id => expected_reg_id,
   Command_Id => T.Commands.Get_Set_Value_Id,  -- ID getter
   Status => Success
));

-- Test both success and failure paths
T.Command_T_Send (T.Commands.Set_Value ((Value => 999)));  -- Invalid
-- Verify Failure response...
```

### Event Component Testing

```ada
-- Send stimuli
T.Tick_T_Send ((Time => (0, 0), Count => 0));

-- Check total events and specific types
Natural_Assert.Eq (T.Event_T_Recv_Sync_History.Get_Count, 2);
Natural_Assert.Eq (T.First_Tick_Event_History.Get_Count, 1);
Natural_Assert.Eq (T.Regular_Tick_Event_History.Get_Count, 1);

-- Verify event parameters
Tick_Assert.Eq (T.Regular_Tick_Event_History.Get (1), expected_tick_param);
```

### Active Component Testing

```ada
-- Send to async connectors (queued)
T.Async_Data_Send (data1);
T.Async_Data_Send (data2);

-- Nothing in output histories yet
Natural_Assert.Eq (T.Output_History.Get_Count, 0);

-- Process queue (returns number processed)
Natural_Assert.Eq (T.Dispatch_All, 2);

-- Now check outputs
Natural_Assert.Eq (T.Output_History.Get_Count, 2);
-- Verify outputs...

-- Multiple dispatch cycles for incremental processing
T.Async_Data_Send (data3);
Natural_Assert.Eq (T.Dispatch_All, 1);  -- One more processed
```

## Error Injection and Edge Case Testing

### Queue Overflow Testing

```ada
-- Fill queue to capacity
T.Async_Data_Send (data1);
T.Async_Data_Send (data2);
T.Async_Data_Send (data3);  -- At capacity

-- Enable dropped message expectation
T.Expect_Async_Data_Send_Dropped := True;

-- This should overflow but not fail test
T.Async_Data_Send (data4);

-- Verify drop was recorded
Natural_Assert.Eq (T.Async_Data_Send_Dropped_Count, 1);
```

### Invalid Command Testing

```ada
-- Test wrong argument length
Invalid_Cmd : Command.T := T.Commands.Set_Value ((Value => 0));
Invalid_Cmd.Header.Arg_Buffer_Length := 0;  -- Wrong length
T.Command_T_Send (Invalid_Cmd);

-- Verify Length_Error response
Command_Response_Assert.Eq (T.Command_Response_T_Recv_Sync_History.Get (1), (
   Source_Id => 0,
   Registration_Id => expected_reg_id,
   Command_Id => T.Commands.Get_Set_Value_Id,
   Status => Length_Error
));
```

### Custom Error Injection

```ada
-- For any Send connector, tester provides Expect_*_Dropped
T.Expect_Data_Product_T_Send_Dropped := True;
-- Component tries to send, tester captures drop instead of asserting failure
-- Reset for next test:
T.Expect_Data_Product_T_Send_Dropped := False;
```

## Data Dependency Testing

For components with data dependencies (common in algorithm wrappers):

### Data Dependency Mock Setup

```ada
-- Tester provides override fields for mocking
type Instance is new Component.Algorithm_Component_Reciprocal.Base_Instance with record
   -- Mock data values
   Sensor_Reading : Sensor_Data.T;
   Reference_Data : Reference.T;
   
   -- Mock return conditions
   Data_Dependency_Return_Status_Override : Data_Product_Enums.Fetch_Status.E := Success;
   Data_Dependency_Return_Id_Override : Data_Product_Types.Data_Product_Id := 0;
   Data_Dependency_Return_Length_Override : Data_Product_Types.Data_Product_Buffer_Length_Type := 0;
   Data_Dependency_Timestamp_Override : Sys_Time.T := (0, 0);
end record;
```

### Data Dependency Mock Implementation

```ada
overriding function Data_Product_Fetch_T_Service (Self : in out Instance; Arg : in Data_Product_Fetch.T) return Data_Product_Return.T is
   Status : Data_Product_Enums.Fetch_Status.E := Self.Data_Dependency_Return_Status_Override;
   Buffer : Data_Product_Types.Data_Product_Buffer_Type;
begin
   -- Use overrides or defaults
   if Status = Success then
      case Arg.Id is
         when 0 => -- Sensor_Reading dependency
            Buffer (Buffer'First .. Buffer'First + Sensor_Data.Size_In_Bytes - 1) :=
               Sensor_Data.Serialization.To_Byte_Array (Self.Sensor_Reading);
         when 1 => -- Reference_Data dependency  
            Buffer (Buffer'First .. Buffer'First + Reference.Size_In_Bytes - 1) :=
               Reference.Serialization.To_Byte_Array (Self.Reference_Data);
         when others =>
            Status := Id_Out_Of_Range;
      end case;
   end if;
   
   return (
      The_Status => Status,
      The_Data_Product => (
         Header => (Time => Self.System_Time, Id => Arg.Id, Buffer_Length => expected_length),
         Buffer => Buffer
      )
   );
end Data_Product_Fetch_T_Service;
```

### Data Dependency Test Scenarios

```ada
-- Test with fresh data
T.Sensor_Reading := (Value => 1.0, Quality => Good);
T.System_Time := (100, 0);  -- Current time
T.Tick_T_Send ((Time => (100, 0), Count => 0));
-- Verify algorithm processes data...

-- Test with stale data
T.Data_Dependency_Timestamp_Override := (50, 0);  -- Old timestamp
T.Tick_T_Send ((Time => (100, 0), Count => 0));
-- Verify algorithm reports stale data...

-- Test with missing data
T.Data_Dependency_Return_Status_Override := Id_Out_Of_Range;
T.Tick_T_Send ((Time => (100, 0), Count => 0));
-- Verify algorithm handles missing dependency...
```

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