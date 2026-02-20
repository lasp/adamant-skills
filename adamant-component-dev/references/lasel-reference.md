<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# LASEL (LASP Awesome Sequence Engine Language) Reference

Domain-specific language for automated command execution in Adamant's command_sequencer component. Compiled into binary bytecode by LASP SEQ tool.

## Basic Syntax

```lasel
seq sequence_name
  ; Comments start with semicolon
  declare counter u32              ; Variable types: u32, i16, f32, etc. (16 max)
  
  ; Commands (three-instruction pattern: Set + Update + Send Bit Pattern)
  cmd Component_A.Command_Name
  cmd Component_A.Command_2 Seconds 11 Subseconds 15
  cmd Component_A.Command_3 Value $counter   ; Variable substitution
  
  ; Variables and operators
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
  wait for 5                       ; Relative: N seconds
  wait until 120001                ; Absolute: VTC timestamp
  waitvalue Component_A.Temp.Value < 50 ? for 30     ; Telemetry + timeout
  
  ; Subsequence control
  call calibration_routine 5 10    ; Call with args, returns to caller
  start other_sequence             ; Overwrite current engine
  spawn parallel_sequence          ; Run on different engine
  return 0                         ; Return value to caller
  
  ; Engine control
  kill 3                           ; Kill engine 3
  kill engines 1 5                 ; Kill range
  
  ; Diagnostics and type casting
  print info "Starting calibration"
  print debug $counter             ; Levels: debug, info, critical, error
  cast_f_to_u                      ; Also: cast_u_to_f, cast_s_to_u, cast_u_to_s, cast_f_to_s, cast_s_to_f
endseq
```

## Opcode Reference (Implemented)

| Opcode | Name | Description |
|--------|------|-------------|
| 0 | Set Bit Pattern | Extract command from sequence into buffer |
| 1 | Send Bit Pattern | Send buffered command |
| 2 | Update Bit Pattern | Update buffer with variable values |
| 3/4/5 | Call/Spawn/Start | Subsequence control (same engine/other engine/replace) |
| 6 | Push | Copy variable to argument buffer |
| 7/27/30 | Eval/Eval FLT/Eval S | Unsigned/float/signed operations |
| 8-10 | Fetch A/Fetch B/Store | Variable load/store |
| 11-12 | Fetch TLM A/B | Telemetry fetch to registers |
| 14 | Wait | Absolute or relative time wait |
| 15-19 | Goto/Jump variants | Conditional/unconditional jumps |
| 20 | Return | Return value and finish |
| 21 | Wait If Zero | Conditional wait with timeout |
| 23 | Kill Engine | Kill specified engine(s) |
| 28-34 | Cast variants | Type conversion (F↔U, S↔U, F↔S) |
| 35-36 | Wait on B variants | Wait using variable B for time |
| 43-44 | Print/Print Var | Event message output |

Unimplemented: String ops (37-42,45), Kill Category/Name (22,24), Subscribe (25-26).

## Engine Architecture

- Configurable engines run in parallel; lower IDs = higher priority
- Each engine has configurable call stack depth (`Stack_Size`)
- Event-driven: pause at waits/commands, resume on tick
- States: UNINITIALIZED → INACTIVE → RESERVED → ACTIVE/WAITING/ENGINE_ERROR
- 16 local variables per sequence, 4 bytes each

## Safety Features

- **Instruction limit**: Prevents infinite loops (configurable)
- **Timeout limit**: Prevents indefinite waits (configurable)
- **Stack depth**: Bounded subsequence nesting
- **Error policy**: `Continue_On_Command_Failure` discriminant

## Assembly Integration

See [adamant-assembly-dev](../../adamant-assembly-dev/SKILL.md) for wiring Command_Sequencer. Key connections: tick input, command send/response, sequence loading, data product access.

## Monitoring

Commands: `Kill_All_Engines`, `Kill_Engine`, `Set_Summary_Packet_Period`, `Issue_Details_Packet`, `Set_Engine_Arguments`

Events: Starting/Finished_Sequence, Execution/Timeout errors, Command failures, Print output.

## Limitations

- No string operations, global variables, or sequence categories
- Sequences tracked by 16-bit ID only (no names)
- Floating point comparison tolerance hard-coded to zero
- Sequences run from provided memory address (not copied)
