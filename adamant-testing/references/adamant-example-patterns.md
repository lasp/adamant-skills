# Adamant Example Advanced Test Patterns

Advanced test patterns extracted from the complete adamant and adamant_example test corpus that are NOT documented in the existing test-corpus.md. These patterns demonstrate sophisticated testing techniques for complex components.

---

## 1. Task-Based Testing with Ada Tasks (parameter_manager)

### 1a. Task-controlled async response simulation

```ada
-- Globals to control task behavior
Task_Send_Response : Boolean := False;
Task_Send_Response_Twice : Boolean := False;
Task_Send_Timeout : Boolean := False;
Task_Response : Parameter_Enums.Parameter_Table_Update_Status.E := Success;

-- Task type for simulating downstream components
type Boolean_Access is access all Boolean;
task type Simulator_Task (
   Class_Self : Class_Access;
   Task_Exit : Boolean_Access
);

task body Simulator_Task is
   Count : Natural := 0;
begin
   while not Task_Exit.all and then Count < 2000 loop
      Count := @ + 1;
      
      if Task_Send_Response then
         Sleep (4);  -- Simulate processing delay
         Class_Self.all.Tester.Parameters_Memory_Region_Release_T_Send ((
            Region => (Address => Sim_Bytes'Address, Length => Sim_Bytes'Length),
            Status => Task_Response
         ));
         Task_Send_Response := False;
      elsif Task_Send_Response_Twice then
         -- Send two responses in sequence with different regions
         Sleep (4);
         Class_Self.all.Tester.Parameters_Memory_Region_Release_T_Send ((
            Region => (Address => Sim_Bytes_2'Address, Length => Sim_Bytes_2'Length),
            Status => Task_Response2
         ));
         Task_Send_Response_Twice := False;
         Task_Send_Response := True;  -- Chain to single response
      else
         Sleep (2);  -- Default sleep
      end if;
   end loop;
end Simulator_Task;

-- In test body:
overriding procedure Test_Nominal_Copy (Self : in out Instance) is
   Task_Exit : aliased Boolean := False;
   Sim_Task : Simulator_Task (Self'Unchecked_Access, Task_Exit'Unchecked_Access);
begin
   -- Send command that requires async response
   T.Command_T_Send (T.Commands.Copy_Parameter_Table ((Copy_Type => Default_To_Working)));
   
   -- Tell task to respond and dispatch
   Task_Send_Response_Twice := True;
   Natural_Assert.Eq (T.Dispatch_All, 1);
   
   -- Verify results...
   
   -- Kill helper task
   Task_Exit := True;
end Test_Nominal_Copy;
```

Source: parameter_manager. This pattern tests components that coordinate with asynchronous external services using Ada tasks to simulate realistic timing and response patterns.

### 1b. Sleep utility for task timing

```ada
procedure Sleep (Ms : in Natural := 5) is
   use Ada.Real_Time;
   Sleep_Time : constant Ada.Real_Time.Time_Span := Ada.Real_Time.Milliseconds (Ms);
   Wake_Time : constant Ada.Real_Time.Time := Ada.Real_Time.Clock + Sleep_Time;
begin
   delay until Wake_Time;
end Sleep;
```

Source: parameter_manager. Real-time sleep for controlling task timing in tests. Critical for testing race conditions and async behavior.

---

## 2. Advanced Error Injection Patterns

### 2a. Expect_*_Dropped for Send_Dropped handler coverage

```ada
-- Set expectation BEFORE each send that should drop
T.Expect_Command_T_Send_Dropped := True;
T.Command_T_Send (Cmd);

-- Verify the drop was detected
Natural_Assert.Eq (T.Command_Dropped_History.Get_Count, 1);
Command_Header_Assert.Eq (T.Command_Dropped_History.Get (1), Cmd.Header);
```

Source: parameter_manager Test_Full_Queue. The `Expect_*_Dropped` flag tells the tester framework to capture dropped sends instead of asserting failure. Must be set before EVERY send that should drop (auto-resets to False).

### 2b. Multiple error response simulation with task control

```ada
-- Set different error responses for sequential operations
Task_Response := Parameter_Enums.Parameter_Table_Update_Status.Parameter_Error;
Task_Response2 := Parameter_Enums.Parameter_Table_Update_Status.Crc_Error;

-- Test sequence with first operation failing
Task_Send_Response := True;
Natural_Assert.Eq (T.Dispatch_All, 1);

-- Verify partial failure - first step failed, no second step
Natural_Assert.Eq (T.Working_Parameters_Memory_Region_Recv_Sync_History.Get_Count, 1);
Natural_Assert.Eq (T.Default_Parameters_Memory_Region_Recv_Sync_History.Get_Count, 0);
Natural_Assert.Eq (T.Parameter_Table_Copy_Failure_History.Get_Count, 1);
Parameters_Memory_Region_Release_Assert.Eq (T.Parameter_Table_Copy_Failure_History.Get (1), (
   Region => (Address => Sim_Bytes'Address, Length => Sim_Bytes'Length),
   Status => Parameter_Enums.Parameter_Table_Update_Status.Parameter_Error
));
```

Source: parameter_manager Test_Copy_Failure. Tests partial failure scenarios where multi-step operations can fail at different stages with different error codes.

---

## 3. Memory Region Testing Patterns

### 3a. Memory region validation with Import pragma

```ada
-- Check region data by importing memory at the region address
declare
   Region : constant Memory_Region.T := T.Get_Parameter_Bytes_Region;
   subtype Safe_Byte_Array_Type is Basic_Types.Byte_Array (0 .. Region.Length - 1);
   Safe_Byte_Array : Safe_Byte_Array_Type with Import, Convention => Ada, Address => Region.Address;
begin
   Byte_Array_Assert.Eq (Safe_Byte_Array, T.Default);
end;
```

Source: parameter_manager. Uses Ada's Import pragma to safely access memory at a specific address for validation. The subtype ensures bounds checking.

### 3b. Aliased byte array setup for memory regions

```ada
-- Global aliased arrays for memory region addresses
Sim_Bytes : aliased Basic_Types.Byte_Array := [0 .. 99 => 12];
Sim_Bytes_2 : aliased Basic_Types.Byte_Array := [0 .. 99 => 11];

-- Usage in memory region construction
Region => (Address => Sim_Bytes'Address, Length => Sim_Bytes'Length)
```

Source: parameter_manager. Aliased arrays provide stable addresses for memory regions. Different arrays allow testing multiple memory areas.

---

## 4. Complex State Machine Testing (command_sequencer)

### 4a. Custom state assertion packages

```ada
-- Define smart assertion for enum types
package Seq_Engine_State_Assert is new Smart_Assert.Discrete (
   Seq_Enums.Seq_Engine_State.E, 
   Seq_Enums.Seq_Engine_State.E'Image
);

-- Usage in tests
Seq_Engine_State_Assert.Eq (T.Get_Engine_State (0), Engine_Error);
```

Source: command_sequencer. Creates typed assertions for custom state enums with readable error messages. Essential for complex state machine validation.

### 4b. Engine state tracking with detailed error context

```ada
-- Verify detailed engine error state
Engine_Error_Type_Assert.Eq (T.Sequence_Timeout_Error_History.Get (1), (
   Engine_Id => 0,
   Sequence_Id => 1,
   Engine_State => Engine_Error,
   Sequence_State => Error,
   Stack_Level => 0,
   Program_Counter => 25,  -- Set by guess and check from coverage
   Error_Type => Command_Timeout,
   Errant_Field_Number => 0
));
```

Source: command_sequencer Test_Sequence_Timeouts. Comprehensive state validation including program counter, error type, and context. The Program_Counter value must be determined empirically from test runs.

### 4c. Timeout simulation with tick sequences

```ada
-- Send command but don't respond, let it timeout
T.Command_T_Send (Component_A_Commands.Command_1);

-- Instead of sending response, advance time to trigger timeout
T.Tick_T_Send (((0, 0), 0));
Natural_Assert.Eq (T.Dispatch_All, 1);
T.Tick_T_Send (((0, 0), 0));
Natural_Assert.Eq (T.Dispatch_All, 1);
T.Tick_T_Send (((0, 0), 0));
Natural_Assert.Eq (T.Dispatch_All, 1);

-- Timeout should occur after N ticks
Natural_Assert.Eq (T.Sequence_Timeout_Error_History.Get_Count, 1);

-- Late response should be rejected
T.Command_Response_T_Send ((
   Source_Id => 0, Registration_Id => 0, 
   Command_Id => Component_A_Commands.Get_Command_1_Id, 
   Status => Success
));
Natural_Assert.Eq (T.Dispatch_All, 1);
Natural_Assert.Eq (T.Unexpected_Command_Response_History.Get_Count, 1);
```

Source: command_sequencer Test_Sequence_Timeouts. Tests timeout behavior by advancing time without sending expected responses, then verifies late responses are rejected.

---

## 5. Packet Construction and Validation (ccsds_command_depacketizer)

### 5a. Custom packet construction helpers

```ada
-- Generic packet constructor
function Construct_Packet (
   Data : Byte_Array; 
   Packet_Type : Ccsds_Packet_Type.E := Ccsds_Packet_Type.Telecommand;
   Secondary_Header : Ccsds_Secondary_Header_Indicator.E := Secondary_Header_Present;
   Apid : Ccsds_Apid_Type := 0; 
   Sequence_Count : Ccsds_Sequence_Count_Type := 0
) return Ccsds_Space_Packet.T is
   Packet : Ccsds_Space_Packet.T := (
      Header => (
         Version => 0, 
         Packet_Type => Packet_Type, 
         Secondary_Header => Secondary_Header, 
         Apid => Apid,
         Sequence_Flag => Ccsds_Sequence_Flag.Unsegmented, 
         Sequence_Count => Sequence_Count, 
         Packet_Length => Data'Length - 1
      ), 
      Data => [others => 0]
   );
begin
   Packet.Data (Packet.Data'First .. Packet.Data'First + Data'Length - 1) := Data;
   return Packet;
end Construct_Packet;
```

Source: ccsds_command_depacketizer. Flexible packet builder that allows testing different packet configurations. Note: Packet_Length is Data'Length - 1 per CCSDS standard.

### 5b. Command packet with checksum construction

```ada
function Construct_Command_Packet (
   Cmd_Id : Command_Types.Command_Id; 
   Data : Byte_Array := [1 .. 0 => 0];
   Checksum_Seed : Xor_8.Xor_8_Type := 255;
   Function_Code : Ccsds_Command_Secondary_Header.Function_Code_Type := 0;
   Packet_Length_Adjustment : Integer := 0
) return Ccsds_Space_Packet.T is
   The_Secondary_Header : Ccsds_Command_Secondary_Header.T := (
      Reserved => 0, Function_Code => Function_Code, Checksum => 0
   );
   Packet : Ccsds_Space_Packet.T := Construct_Packet (
      Ccsds_Command_Secondary_Header.Serialization.To_Byte_Array (The_Secondary_Header) &
      Command_Id.Serialization.To_Byte_Array ((Id => Cmd_Id)) & 
      Data & 
      (1 .. Natural (Function_Code) => 0)
   );
begin
   -- Adjust packet length if requested
   Packet.Header.Packet_Length := Unsigned_16 (Natural (@) + Packet_Length_Adjustment);
   
   declare
      Header_Bytes : constant Byte_Array := Ccsds_Primary_Header.Serialization.To_Byte_Array (Packet.Header);
      Checksum : constant Xor_8.Xor_8_Type := Xor_8.Compute_Xor_8 (Header_Bytes & Packet.Data, Checksum_Seed);
   begin
      The_Secondary_Header.Checksum := Checksum;
      Packet.Data (Packet.Data'First .. Packet.Data'First + Ccsds_Command_Secondary_Header.Serialization.Serialized_Length - 1) := 
         Ccsds_Command_Secondary_Header.Serialization.To_Byte_Array (The_Secondary_Header);
   end;
   
   return Packet;
end Construct_Command_Packet;
```

Source: ccsds_command_depacketizer. Constructs valid CCSDS command packets with correct checksums. The checksum is computed over the entire packet including headers.

### 5c. Invalid checksum testing

```ada
overriding procedure Test_Invalid_Packet_Checksum (Self : in out Instance) is
   T : Component.Ccsds_Command_Depacketizer.Implementation.Tester.Instance_Access renames Self.Tester;
   -- Create packet with wrong checksum seed
   Packet : constant Ccsds_Space_Packet.T := Construct_Command_Packet (17, [0 => 16], Checksum_Seed => 0);
   Invalid_Checksum_Info : constant Invalid_Packet_Xor8_Info.T := (
      Ccsds_Header => (Packet.Header, (0, 0, 221)), 
      Computed_Checksum => 255, 
      Expected_Checksum => 221
   );
begin
   -- Send packet with bad checksum multiple times
   T.Ccsds_Space_Packet_T_Send (Packet);
   T.Ccsds_Space_Packet_T_Send (Packet);
   T.Ccsds_Space_Packet_T_Send (Packet);

   -- Expect no valid commands
   Natural_Assert.Eq (T.Command_T_Recv_Sync_History.Get_Count, 0);
   
   -- Expect checksum error events
   Natural_Assert.Eq (T.Invalid_Packet_Checksum_History.Get_Count, 3);
   Invalid_Packet_Xor8_Info_Assert.Eq (T.Invalid_Packet_Checksum_History.Get (3), Invalid_Checksum_Info);
   
   -- Expect error packets forwarded
   Natural_Assert.Eq (T.Error_Packet_History.Get_Count, 3);
   Ccsds_Space_Packet_Assert.Eq (T.Error_Packet_History.Get (1), Packet);
end Test_Invalid_Packet_Checksum;
```

Source: ccsds_command_depacketizer. Tests packet validation by constructing packets with incorrect checksums using wrong checksum seeds. Verifies both rejection events and error packet forwarding.

---

## 6. Data Product Database Testing (product_database)

### 6a. Database range testing with ID loops

```ada
Min_Id : constant Data_Product_Types.Data_Product_Id := 17;
Max_Id : constant Data_Product_Types.Data_Product_Id := 26;

-- Store data products across ID range
for Id in Min_Id .. Max_Id loop
   D_Prod.Header.Id := Id;
   D_Prod.Buffer := [others => Basic_Types.Byte (Id)];
   T.Data_Product_T_Send (D_Prod);
end loop;

-- Fetch and verify data products
for Id in Min_Id .. Max_Id loop
   D_Prod.Header.Id := Id;
   D_Prod.Buffer := [others => Basic_Types.Byte (Id)];
   D_Prod_Return := T.Data_Product_Fetch_T_Request ((Id => Id));
   
   The_Status_Assert.Eq (D_Prod_Return.The_Status, Fetch_Status.Success);
   Data_Product_Assert.Eq (D_Prod_Return.The_Data_Product, D_Prod);
end loop;
```

Source: product_database Test_Nominal_Scenario. Tests database storage and retrieval across the full ID range. Each data product is uniquely identifiable by its ID and buffer content.

### 6b. Database override testing with poly types

```ada
-- Enable override mode
T.Command_T_Send (T.Commands.Set_Data_Product_Extraction ((Enable_State => Enabled)));

-- Attempt fetch (should be overridden)
D_Prod_Return := T.Data_Product_Fetch_T_Request ((Id => 18));
The_Status_Assert.Eq (D_Prod_Return.The_Status, Fetch_Status.Success);

-- Check override event  
Natural_Assert.Eq (T.Data_Product_Extraction_Enabled_History.Get_Count, 1);
Data_Product_Poly_Extract_Assert.Eq (T.Data_Product_Extraction_Enabled_History.Get (1), (
   Extract_Data_Product => (Header => (Time => (1, 17), Id => 18), The_Poly_Type => (Buffer => [others => 18])),
   Id => 18
));
```

Source: product_database Test_Nominal_Override. Tests database override functionality where fetch requests can be intercepted and modified. Uses poly types for flexible data product representation.

---

## 7. Component Reinitialization Testing

### 7a. Mid-test component reinitialization

```ada
-- Test with initial configuration
T.Component_Instance.Init (/* initial params */);

-- ... run some tests ...

-- Reinitialize component with different configuration
T.Component_Instance.Final;
T.Component_Instance.Init (
   Num_Engines => 3,
   Stack_Size => 3,
   Continue_On_Command_Failure => True,  -- Different config
   Timeout_Limit => 3,
   Instruction_Limit => 10000
);

-- Re-register and continue testing
T.Command_Response_T_Send ((
   Source_Id => 0, Registration_Id => 0, 
   Command_Id => 0, Status => Register_Source
));
Natural_Assert.Eq (T.Dispatch_All, 1);
```

Source: command_sequencer Test_Sequence_Timeouts. Demonstrates testing different component configurations within a single test by finalizing and reinitializing with different parameters.

---

## 8. Comprehensive Component Coverage Summary

Based on the complete test corpus analysis, here are the components and their test status:

### Adamant Example Components (adamant_example/src/components/)
- ✅ **c_demo**: HAS TESTS
- ✅ **counter**: HAS TESTS  
- ✅ **cpp_demo**: HAS TESTS
- ✅ **oscillator**: HAS TESTS
- ✅ **parameter_manager**: HAS TESTS (advanced patterns: Send_Dropped, Invalid_Command, task-based testing)
- ❌ **adc_data_collector**: NO TESTS
- ❌ **fault_producer**: NO TESTS
- ❌ **interrupt_responder**: NO TESTS
- ❌ **nav_aggregate_practice**: NO TESTS

### Adamant Core Components (adamant/src/components/) - Sample of 30
- ✅ **ccsds_command_depacketizer**: HAS TESTS (advanced packet testing patterns)
- ✅ **command_sequencer**: HAS TESTS (complex state machine testing)
- ✅ **product_database**: HAS TESTS (parameter store testing)
- ✅ **ccsds_downsampler**: HAS TESTS
- ✅ **ccsds_packetizer**: HAS TESTS
- ✅ **command_protector**: HAS TESTS
- ✅ **command_rejector**: HAS TESTS
- ✅ **command_router**: HAS TESTS
- ✅ **cpu_monitor**: HAS TESTS
- ✅ **event_filter**: HAS TESTS
- ❌ **ccsds_echo**: NO TESTS
- ❌ **ccsds_serial_interface**: NO TESTS
- ❌ **ccsds_socket_interface**: NO TESTS
- ❌ **connector_counter_16**: NO TESTS
- ❌ **connector_counter_8**: NO TESTS
- ❌ **gps_time**: NO TESTS

**Test coverage in adamant is approximately 80%** - the majority of components have comprehensive test suites.

---

## 9. Key Testing Insights from Corpus Analysis

### 9a. Advanced error injection requires tester modifications
Unlike basic testing, advanced coverage patterns (Send_Dropped, Invalid_Command, Recv_Async_Dropped) require either:
- Tester spec/body modifications to add `Expect_*_Dropped` flags
- Commenting out connector attachments in tester's `Connect` procedure  
- Custom queue sizing for overflow scenarios

### 9b. State machine testing uses custom assertions
Complex components like command_sequencer use `Smart_Assert.Discrete` to create typed state assertions with readable error messages. This is superior to pragma Assert for state validation.

### 9c. Memory region testing uses Ada Import pragma
Direct memory validation uses Import pragma with address-based subtyping for safe memory access. This pattern is essential for components that manage memory regions.

### 9d. Task-based testing enables realistic async simulation
Components that coordinate with external services benefit from Ada task-based test harnesses that simulate realistic timing, delays, and response sequences.

### 9e. Packet testing requires construction helpers
Protocol-level components benefit from custom packet construction functions that handle serialization, checksums, and header formatting. These helpers enable comprehensive packet validation testing.

These patterns represent the most sophisticated testing techniques in the Adamant framework, going well beyond the basic patterns documented in the existing test corpus.