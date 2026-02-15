# LASEL (LASP Awesome Sequence Engine Language) Reference

Domain-specific language for automated command execution in Adamant's command_sequencer component.

## Language Overview

LASEL is compiled by the LASP SEQ tool into binary bytecode that executes on Adamant's command sequencer engines. Sequences run from provided memory addresses (not copied) and are event-driven, pausing at waits/commands and resuming on ticks.

## Basic Syntax

```lasel
seq sequence_name
  ; Comments start with semicolon
  declare counter u32              ; Variable types: u32, i16, f32, etc.
  
  ; Three-instruction command pattern:
  cmd Component_A.Command_Name     ; Compiles to: Set + Send Bit Pattern
  cmd Component_A.Command_2 Seconds 11 Subseconds 15
  cmd Component_A.Command_3 Value $counter   ; Variable substitution
  
  ; Variables (16 local variables max)
  set $counter = 0
  set $counter = $counter + 1
  set $counter = Component_A.Data_Product.Value   ; Telemetry fetch
  
  ; Operators: + - * / % == != < > <= >= && || & | ^
  
  ; Conditionals
  if $counter > 100
    cmd Component_A.Enable
  else
    cmd Component_A.Disable
  endif
  
  ; Waits
  wait for 5                       ; Relative: wait N seconds
  wait until 120001                ; Absolute: wait until VTC timestamp
  waitvalue Component_A.Temp.Value < 50 ? for 30     ; Telemetry condition + timeout
  waitvalue Component_B.Sensor.Value == 8.76 ? until 120001  ; Telemetry + absolute timeout
  
  ; Subsequence control
  call calibration_routine 5 10    ; Call with args, returns to caller
  start other_sequence             ; Overwrite current engine
  spawn parallel_sequence          ; Run on different engine
  return 0                         ; Return value to caller
  
  ; Engine control
  kill 3                           ; Kill engine 3
  kill engines 1 5                 ; Kill engines 1-5
  
  ; Diagnostics
  print info "Starting calibration"
  print error "Failed!"
  print debug $counter             ; Print levels: debug, info, critical, error
  
  ; Type casting
  cast_f_to_u                      ; Float->unsigned, also: cast_u_to_f, cast_s_to_u, 
  cast_s_to_f                      ; cast_u_to_s, cast_f_to_s, cast_s_to_f
endseq
```

## Complete Opcode Reference

| Opcode | Name                   | Status        | Description |
|--------|------------------------|---------------|-------------|
| 0      | Set Bit Pattern        | Implemented   | Extract command from sequence and store in internal buffer |
| 1      | Send Bit Pattern       | Implemented   | Send command stored in internal buffer |
| 2      | Update Bit Pattern     | Implemented   | Update internal command buffer with variable values |
| 3      | Call                   | Implemented   | Load and run a subsequence in this engine |
| 4      | Spawn                  | Implemented   | Load and run a sequence in another engine |
| 5      | Start                  | Implemented   | Load and run a sequence in this engine, replacing current |
| 6      | Push                   | Implemented   | Copy variable to argument buffer for new sequence |
| 7      | Eval                   | Implemented   | Perform unsigned integer operation on variables A and B |
| 8      | Fetch Var A            | Implemented   | Fetch variable/constant and store in internal variable A |
| 9      | Fetch Var B            | Implemented   | Fetch variable/constant and store in internal variable B |
| 10     | Store Var              | Implemented   | Store internal A into a sequence variable |
| 11     | Fetch TLM A            | Implemented   | Fetch telemetry value and store in internal variable A |
| 12     | Fetch TLM B            | Implemented   | Fetch telemetry value and store in internal variable B |
| 13     | Invalid                | N/A           | Not a valid opcode |
| 14     | Wait                   | Implemented   | Wait for absolute time or relative time from current |
| 15     | Goto                   | Implemented   | Jump to specific instruction |
| 16     | Jump If Zero           | Implemented   | Jump if internal variable A equals zero |
| 17     | Jump Not Zero          | Implemented   | Jump if internal variable A not equal to zero |
| 18     | Jump If Equal          | Implemented   | Jump if internal variable A equals specific value |
| 19     | Jump Not Equal         | Implemented   | Jump if internal variable A not equal to specific value |
| 20     | Return                 | Implemented   | Copy internal A to return variable and finish |
| 21     | Wait If Zero           | Implemented   | Continue waiting if internal A equals zero, check timeout |
| 22     | Kill Category          | Unimplemented | Sequence categories not supported |
| 23     | Kill Engine            | Implemented   | Kill sequence running in specified engine(s) |
| 24     | Kill Name              | Unimplemented | Not implemented |
| 25     | Subscribe              | Unimplemented | Not applicable to Adamant systems |
| 26     | Unsubscribe            | Unimplemented | Not applicable to Adamant systems |
| 27     | Eval FLT               | Implemented   | Perform floating point operation on variables A and B |
| 28     | Cast F to U            | Implemented   | Convert floating point to unsigned integer |
| 29     | Cast U to F            | Implemented   | Convert unsigned integer to floating point |
| 30     | Eval S                 | Implemented   | Perform signed integer operation on variables A and B |
| 31     | Cast S to U            | Implemented   | Convert signed integer to unsigned integer |
| 32     | Cast U to S            | Implemented   | Convert unsigned integer to signed integer |
| 33     | Cast F to S            | Implemented   | Convert floating point to signed integer |
| 34     | Cast S to F            | Implemented   | Convert signed integer to floating point |
| 35     | Wait on B              | Implemented   | Wait for time stored in variable B |
| 36     | Wait If Zero On B      | Implemented   | Wait if A is zero, timeout from variable B |
| 37     | Str Alloc              | Unimplemented | String pool not supported |
| 38     | Str Dealloc            | Unimplemented | String pool not supported |
| 39     | Str Set                | Unimplemented | String pool not supported |
| 40     | Str Update Bit Pattern | Unimplemented | String pool not supported |
| 41     | Str Copy               | Unimplemented | String pool not supported |
| 42     | Str Move               | Unimplemented | String pool not supported |
| 43     | Print                  | Implemented   | Print string as FSW event message |
| 44     | Print Var              | Implemented   | Print sequence variable as FSW event message |
| 45     | Print Str              | Unimplemented | String pool not supported |

## Engine Architecture

### Engine Model
- Configurable number of engines run in parallel (`Num_Engines` discriminant)
- Each engine has a configurable stack for subsequence calls (`Stack_Size` discriminant)
- Lower engine IDs have higher priority
- Event-driven: sequences pause at waits/commands and resume on tick

### Engine States
```
UNINITIALIZED -> INACTIVE -> RESERVED (loading) -> ACTIVE (running)
                                                -> WAITING (blocked)
                                                -> ENGINE_ERROR
```

### Runtime States
- **UNLOADED**: No sequence loaded
- **READY**: Sequence ready to execute
- **DONE**: Sequence finished successfully
- **WAIT_RELATIVE/ABSOLUTE**: Waiting on time
- **WAIT_COMMAND**: Waiting for command response
- **WAIT_TELEMETRY_SET/VALUE/RELATIVE**: Waiting for telemetry
- **WAIT_LOAD_NEW_SEQ_***: Waiting for sequence load
- **PRINT**: Requesting print output
- **ERROR**: Sequence in error state

## Command Pattern

LASEL commands are implemented using a three-instruction pattern:

1. **Set Bit Pattern** (opcode 0): Extract command from sequence into internal buffer
2. **Update Bit Pattern** (opcode 2): Update command arguments with variable values  
3. **Send Bit Pattern** (opcode 1): Send the prepared command

This allows dynamic argument substitution at runtime.

## Variables and Data Types

### Local Variables
- 16 local variables per sequence (indexed 0-15)
- 4-byte storage per variable (except strings: 64 bytes max)
- Types determined at runtime based on operations

### Internal Variables
- **A, B**: Primary working registers
- **Seq_Return**: Return value from subsequences
- **Timeout**: Timeout flag

### Data Types
- **Unsigned** (U): Unsigned integers
- **Signed** (I/S): Signed integers  
- **Float** (F): Floating point
- **Discrete** (D): Discrete/enumerated values

### Supported Operations
- Arithmetic: `+ - * / %`
- Bitwise: `& | ^ `
- Logical: `&& ||`
- Comparison: `== != < > <= >=`

## Integration Patterns

### Assembly Integration

Add to your assembly YAML:

```yaml
components:
  - type: Command_Sequencer
    name: Seq
    discriminant:
      - Num_Engines: 4        # Number of parallel engines
      - Stack_Size: 5         # Subsequence call depth
      - data_product_instance_config:
          - name: Summary_Packet_Period

init:
  Seq:
    Num_Engines: 4
    Stack_Size: 5
    Create_Sequence_Load_Command_Function: Load_Sequence'Access
    Packet_Period: 10        # Summary packet every 10 ticks
    Continue_On_Command_Failure: False
    Timeout_Limit: 600       # 10 minutes at 1Hz tick
    Instruction_Limit: 1000  # Max instructions per tick

connections:
  # Timing
  - from_component: Tick_Divider
    from_connector: Tick_T_Send
    to_component: Seq
    to_connector: Tick_T_Recv_Async
    
  # Command routing
  - from_component: Seq
    from_connector: Command_T_Send
    to_component: Command_Router
    to_connector: Command_T_Recv_Async
    
  # Command responses (one per engine)
  - from_component: Command_Router
    from_connector: Command_Response_T_Send[0]
    to_component: Seq
    to_connector: Command_Response_T_Recv_Async
    
  # Sequence loading
  - from_component: Sequence_Store
    from_connector: Sequence_Load_T_Send
    to_component: Seq
    to_connector: Sequence_Load_T_Recv_Async
    
  # Data product access
  - from_component: Product_Database
    from_connector: Data_Product_Return_T_Send
    to_component: Seq
    to_connector: Data_Product_Fetch_T_Service_Request
```

### Required Initialization Function

Create a sequence load command function:

```ada
function Load_Sequence (
   Id : in Sequence_Types.Sequence_Id; 
   Engine_Number : in Seq_Types.Sequence_Engine_Id;
   Engine_Request : in Command_Sequencer_Enums.Sequence_Load_Engine_Request_Type.E
) return Command.T is
   -- Implementation specific to your sequence storage
end Load_Sequence;
```

## Error Handling

### Safety Features
- **Instruction limit**: Prevents infinite loops (configurable `Instruction_Limit`)
- **Timeout limit**: Prevents indefinite waits (configurable `Timeout_Limit`)
- **Stack depth**: Bounded subsequence nesting (configurable `Stack_Size`)
- **Error policy**: `Continue_On_Command_Failure` discriminant

### Error Types
- **PARSE**: Invalid instruction fields
- **OPCODE**: Invalid/unrecognized opcode
- **COMMAND_PARSE/LENGTH/FAIL**: Command-related errors
- **TELEMETRY_FAIL**: Telemetry access errors
- **VARIABLE**: Invalid variable access
- **JUMP**: Invalid position jump
- **CAST**: Type conversion errors
- **LIMIT**: Instruction limit exceeded
- **TIMEOUT**: Command/load/telemetry timeout

## Monitoring and Control

### Commands
- `Kill_All_Engines`: Halt all running sequences
- `Kill_Engine`: Halt specific engine
- `Set_Summary_Packet_Period`: Configure telemetry reporting
- `Issue_Details_Packet`: Get detailed engine status
- `Set_Engine_Arguments`: Provide arguments before loading sequence

### Telemetry Packets
- **Summary Packet**: Brief overview of all engine states (configurable period)
- **Details Packet**: Complete state information for single engine (on demand)

### Events
- Sequence lifecycle: Starting_Sequence, Finished_Sequence
- Error reporting: Sequence_Execution_Error, Sequence_Timeout_Error
- Command failures: Sequence_Command_Failure
- Load operations: Load_To_Invalid_Engine_Id, Engine_In_Use
- Print statements: Print (from sequence print commands)

## Test Patterns

### Basic Sequence Testing
```ada
-- Load sequence into engine 0
Load_Result := Load_Sequence(Id => 42, Engine => 0);

-- Check engine state
Assert(Engine_State = ACTIVE);

-- Advance time for relative waits
Tick_Component(Seq);

-- Verify commands sent
Assert(Command_Router.Get_Command_Count = Expected_Count);

-- Check for completion
Assert(Engine_State = INACTIVE);
```

### Error Testing
```ada
-- Test instruction limit
Load_Infinite_Loop_Sequence;
for I in 1 .. Instruction_Limit + 1 loop
   Execute_Engine;
end loop;
Assert(Engine_State = ENGINE_ERROR);
Assert(Last_Error = LIMIT);

-- Test timeout
Load_Long_Wait_Sequence;
Advance_Time(Timeout_Limit + 1);
Assert(Engine_State = ENGINE_ERROR);
Assert(Last_Error = Command_Timeout);
```

### Integration Testing
```ada
-- Test telemetry conditionals
Set_Data_Product_Value(Temp_Sensor, 45.0);
Load_Temperature_Check_Sequence;
Execute_Until_Complete;
Assert(Commands_Include("Heater_On"));

-- Test subsequence calls
Load_Main_Sequence;
Execute_Until_State(WAIT_LOAD_NEW_SUB_SEQ);
Provide_Subsequence(Cal_Sequence);
Execute_Until_Complete;
Assert(Return_Value = Expected_Cal_Result);
```

## Limitations in Adamant Implementation

### Not Supported
- **String operations**: All Str_* opcodes are unimplemented
- **Global variables**: Only local variables supported
- **Sequence categories**: Kill_Category not implemented
- **Subscriptions**: Subscribe/Unsubscribe not applicable
- **Sequence names**: Sequences tracked by 16-bit ID only
- **Floating point tolerance**: Hard-coded to zero

### Mission Configuration Parameters
```ada
-- Defined in Seq_Types:
Max_Seq_Size : constant := 65536;        -- Max sequence size
Num_Seq_Variables : constant := 16;      -- Local variables per sequence
Max_Seq_String_Size : constant := 64;    -- Max string length

-- Defined at component initialization:
-- Num_Engines, Stack_Size, Timeout_Limit, Instruction_Limit
```

## Compilation and Loading

Sequences are compiled by the LASP SEQ tool into binary bytecode with headers:
- **Header**: Version info, category (unused), length
- **CRC**: Integrity checking
- **Bytecode**: Executable instructions

The command sequencer runs sequences directly from the provided memory address without copying, requiring the sequence storage component to maintain the sequence in memory for the duration of execution.