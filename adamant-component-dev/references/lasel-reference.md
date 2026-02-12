# LASEL (LASP Awesome Sequence Engine Language) Reference

Domain-specific language for automated command execution in Adamant's command_sequencer.

## Syntax

```
seq sequence_name
  ; Comments start with semicolon
  declare counter u32              ; Variable types: u32, i16, f32, etc.
  
  ; Commands
  cmd Component_A.Command_Name
  cmd Component_A.Command_2 Seconds 11 Subseconds 15
  cmd Component_A.Command_3 Value $counter
  
  ; Variables
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
  cast_f_to_u                      ; Float->unsigned, also: cast_u_to_f, cast_s_to_u, etc.
endseq
```

## Engine Model

- Multiple engines run in parallel (configurable via `Num_Engines` discriminant)
- Each engine has a stack for subsequence calls (configurable `Stack_Size`)
- Lower engine IDs have higher priority
- Event-driven: sequences pause at waits/commands and resume on tick

## Engine States

```
UNINITIALIZED -> INACTIVE -> RESERVED (loading) -> ACTIVE (running)
                                                -> WAITING (blocked)
                                                -> ENGINE_ERROR
```

## Safety Features

- **Instruction limit**: max instructions per tick prevents infinite loops
- **Timeout limit**: max wait duration prevents indefinite blocks
- **Stack depth**: bounded subsequence nesting
- **Continue_On_Command_Failure**: configurable error policy

## Loading

Sequences are compiled by the LASP SEQ tool into binary bytecode with headers (ID, length, CRC). Loaded via `Sequence_Load_T_Recv_Async` connector. Sequences run from provided memory address (not copied).

## Sequencer Commands

- `Kill_All_Engines` -- halt all running sequences
- `Kill_Engine` -- halt specific engine by ID
- `Set_Engine_Arguments` -- provide arguments before loading
- `Set_Summary_Packet_Period` -- configure telemetry reporting
- `Issue_Details_Packet` -- get detailed engine status
