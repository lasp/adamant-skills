---
name: adamant-framework-components
description: Reference catalog of all 58 built-in Adamant components organized by subsystem. Quick lookup for component selection, execution models, and usage patterns.
---

# Adamant Framework Components Reference

Quick-lookup catalog of all 58 built-in Adamant components organized by subsystem. Each entry shows purpose, execution model, key connectors, and typical use case.

## CCSDS Communication (7 components)

**ccsds_command_depacketizer** (passive)
- Purpose: CCSDS packets -> Adamant commands with validation
- Use: Convert uplinked command packets to internal format
- No init parameters
- Connectors: `Ccsds_Space_Packet_T_Recv_Sync` (CCSDS packets in), `Command_T_Send` (commands out), `Data_Product_T_Send`, `Event_T_Send`, `Packet_T_Send` (error packets), `Sys_Time_T_Get`, `Command_Response_T_Send`, `Command_T_Recv_Sync` (self-commands)

**ccsds_downsampler** (passive)
- Purpose: Filter packets by APID with configurable rates
- Use: Reduce telemetry downlink rate for specific packet types
- Init: `Downsample_List` (Ccsds_Downsampler_Types.Ccsds_Downsample_Packet_List_Access, not_null) -- list of APIDs with filter factors for downsampling
- Connectors: `Ccsds_Space_Packet_T_Recv_Sync` (packets in), `Command_T_Recv_Sync`, `Ccsds_Space_Packet_T_Send` (filtered packets out), `Command_Response_T_Send`, `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`

**ccsds_echo** (passive)
- Purpose: Echo CCSDS packets as Adamant packets
- Use: Loop back uplink as downlink
- Connectors: `Ccsds_Space_Packet_T_Recv_Sync` (CCSDS in), `Packet_T_Send` (Adamant packets out), `Sys_Time_T_Get`

**ccsds_packetizer** (passive)
- Purpose: Adamant packets -> CCSDS packets with CRC/timestamp
- Use: Package internal packets for CCSDS downlink
- Connectors: `Packet_T_Recv_Sync` (in, receives Adamant packets), `Ccsds_Space_Packet_T_Send` (out, sends CCSDS packets)
- No init, no commands -- pure passthrough conversion with CRC16 + 8-byte secondary header timestamp

**ccsds_product_extractor** (passive)
- Purpose: Extract data products from CCSDS packet data
- Use: Parse telemetry from CCSDS packets into typed data
- Init: `Data_Product_Extraction_List` (Product_Extractor_Types.Extracted_Product_List_Access, not_null) -- list of data products to extract from packets with APID/offset mapping
- Connectors: `Ccsds_Space_Packet_T_Recv_Sync` (CCSDS in), `Data_Product_T_Send` (extracted products), `Event_T_Send`, `Sys_Time_T_Get`

**ccsds_router** (either)
- Purpose: Route CCSDS packets by APID lookup table with sequence count checking
- Use: Distribute packets to appropriate processing components by APID; autocoder exists in gen/ subdirectory for table generation
- With: `Ccsds_Router_Types`
- Init:
  - `Table` (Ccsds_Router_Types.Router_Table_Entry_Array, not_null) -- routing table mapping APIDs to output connectors with sequence count modes
  - `Report_Unrecognized_APIDs` (Boolean, default True) -- send error packet/event for unrecognized APIDs
- Connectors: `Ccsds_Space_Packet_T_Recv_Sync` (sync input), `Ccsds_Space_Packet_T_Recv_Async` (async input), `Ccsds_Space_Packet_T_Send` (arrayed output, count=0), `Unrecognized_Ccsds_Space_Packet_T_Send` (unmatched APIDs), `Event_T_Send`, `Packet_T_Send` (errors), `Sys_Time_T_Get`

**ccsds_serial_interface** (active)
- Purpose: CCSDS over serial via Ada.Text_IO
- Use: Backdoor serial interface for CCSDS communication
- Init: `Interpacket_Gap_Ms` (Natural, default 0) -- time in milliseconds to wait between CCSDS packet transmissions for UART protocols requiring gaps
- Subtasks: `Listener` (listens on serial port for incoming packets)
- Connectors: `Ccsds_Space_Packet_T_Recv_Async` (data in), `Ccsds_Space_Packet_T_Send` (data out), `Event_T_Send`, `Sys_Time_T_Get`

## Network Interfaces (2 components)

**ccsds_socket_interface** (active)
- Purpose: CCSDS over TCP/IP socket with listener task
- Use: Connect assembly to ground system via network
- init_base: `Queue_Size`
- init: `Addr` (String access), `Port` (Natural)
- subtasks: `Listener` (with priority/stack for recv task)
- Connectors: `Ccsds_Space_Packet_T_Send`, `Ccsds_Space_Packet_T_Recv_Async`, `Event_T_Send`, `Sys_Time_T_Get`

**ccsds_subpacket_extractor** (either)
- Purpose: Extract CCSDS subpackets from larger packets with offset control
- Use: Unpack multiplexed CCSDS packets, skip headers/trailers
- Init:
  - `start_Offset` (Natural, default 0) -- bytes past CCSDS header to start extraction from
  - `stop_Offset` (Natural, default 0) -- bytes at end of packet to ignore during extraction
  - `max_Subpackets_To_Extract` (Integer, default -1) -- max subpackets per packet; negative=unlimited, 0=disabled
- Connectors: `Ccsds_Space_Packet_T_Recv_Sync` (sync input), `Ccsds_Space_Packet_T_Recv_Async` (async input), `Ccsds_Space_Packet_T_Send` (subpackets out), `Event_T_Send`, `Packet_T_Send` (error packets), `Sys_Time_T_Get`

## Command Processing (6 components)

**command_protector** (passive)
- Purpose: Protect hazardous commands with arm/disarm + timeout
- Use: Prevent accidental execution of dangerous commands
- Preamble: Defines `Command_Id_List` (array of Command_Types.Command_Id)
- Init: `protected_Command_Id_List` (Command_Id_List) -- list of command IDs to protect
- Connectors: `Tick_T_Recv_Sync` (arm timeout), `Command_T_To_Forward_Recv_Sync` (commands to check), `Command_T_Recv_Sync`, `Command_T_Send` (forwarded commands), `Command_Response_T_Send`, `Data_Product_T_Send`, `Event_T_Send`, `Packet_T_Send` (rejected commands), `Sys_Time_T_Get`

**command_rejector** (passive)
- Purpose: Block commands based on ID blacklist
- Use: Prevent unwanted commands from specific sources
- Preamble: Defines `Command_Id_List` (array of Command_Types.Command_Id)
- Init: `command_Id_Reject_List` (Command_Id_List) -- list of command IDs to reject
- Connectors: `Command_T_To_Forward_Recv_Sync` (commands to check), `Command_T_Send` (forwarded commands), `Data_Product_T_Send`, `Event_T_Send`, `Packet_T_Send` (error packets), `Sys_Time_T_Get`

**command_router** (active)
- Purpose: Route commands by ID to destination components with registration table
- Use: Central command distribution hub for assembly; includes NOOP self-test commands and response forwarding
- Init:
  - `max_Number_Of_Commands` (Natural) -- maximum unique commands that can be registered (sizes internal heap table)
- Connectors: `Command_T_To_Route_Recv_Async` (main command input), `Command_T_To_Route_Recv_Sync` (high-priority bypass), `Command_T_Send` (arrayed output, count=0), `Command_Response_T_Recv_Async` (registration + responses), `Command_Response_T_To_Forward_Send` (response forwarding, count=0), `Command_T_Recv_Async` (self-commands), `Command_Response_T_Send` (self-responses), `Event_T_Send`, `Data_Product_T_Send`, `Sys_Time_T_Get`

**command_sequencer** (active)
- Purpose: Execute LASEL sequences with multiple engines
- Use: Automated sequence execution with parallel engines
- Preamble: Defines `Create_Sequence_Load_Command_Access` -- function access type that formulates sequence load commands (mission-specific)
- Init:
  - `Num_Engines` (Seq_Types.Num_Engines_Type) -- number of parallel sequence engines
  - `Stack_Size` (Seq_Types.Stack_Depth_Type) -- stack depth per engine for subsequence calls
  - `Create_Sequence_Load_Command_Function` (Create_Sequence_Load_Command_Access, not_null) -- mission-specific sequence load command builder
  - `Packet_Period` (Unsigned_16) -- summary packet rate in ticks (0=disabled)
  - `Continue_On_Command_Failure` (Boolean) -- if True, engines continue on failed commands
  - `Timeout_Limit` (Natural) -- ticks before timeout on command response/subsequence load (0=disabled)
  - `Instruction_Limit` (Positive) -- max instructions before forced pause (prevents infinite loops)
- Connectors: `Tick_T_Recv_Async`, `Command_Response_T_Recv_Async` (register source per engine), `Command_T_Recv_Async` (self-commands), `Sequence_Load_T_Recv_Async` (load sequences via memory region), `Sequence_Load_Return_T_Send`, `Command_T_Send` (sequence commands out), `Data_Product_Fetch_T_Request` (telemetry conditionals), `Command_Response_T_Send`, `Packet_T_Send`, `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get` (12 total)

**connector_counter_8/16** (passive)
- Purpose: Count connector invocations (1/2 byte counters)
- Use: Monitor/debug connector activity rates

## Generic Connector Utilities (4 components)

**connector_delayer** (active)
- Purpose: Delay transmission by configurable microseconds
- Use: Space out data transmission or create alarms
- Generic: `T` (any data type), `Serialized_Length` (serialization function for variable-length types)
- Init: `Delay_Us` (Natural) -- microseconds to delay before transmission
- Connectors: `T_Recv_Async` (queued input), `T_Send` (delayed output), `Sys_Time_T_Get`, `Event_T_Send`

**connector_protector** (passive)
- Purpose: Thread-safe protected object for connectors
- Use: Add thread safety to non-thread-safe components
- Generic: `T` -- generic data type for protected pass-through (atomic T_Send call within protected object)
- Connectors: `T_Recv_Sync` (input), `T_Send` (atomic protected output)

**connector_queuer** (active)
- Purpose: Add FIFO queue to synchronous connectors
- Use: Convert sync connectors to async with ordering
- Generic:
  - `T` -- generic data type passed through the queue
  - `Serialized_Length` -- function to get serialized length of T (for variable-length types)
- Connectors: `T_Recv_Async` (queued input), `T_Send` (FIFO output), `Sys_Time_T_Get`, `Event_T_Send`

**forwarder** (passive)
- Purpose: Enable/disable control switch for data streams
- Use: Stream on/off switch for any data type
- Generic: `T` -- any connector type (instantiated at compile time)
- Init:
  - `Startup_Forwarding_State` (Basic_Enums.Enable_Disable_Type.E) -- Enable or Disable forwarding at startup
- Connectors: `T_Recv_Sync` (data in), `Command_T_Recv_Sync`, `T_Send` (forwarded data), `Command_Response_T_Send`, `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get` (7 total)

## Event Management (4 components)

**event_filter** (passive)
- Purpose: Filter events by ID range and configurable state
- Use: Suppress unwanted events, debug mode control
- Init:
  - `Event_Id_Start_Range` (Event_Types.Event_Id) -- start of filterable event ID range
  - `Event_Id_End_Range` (Event_Types.Event_Id) -- end of filterable event ID range
  - `Event_Filter_List` (Event_Filter_Entry.Event_Id_List, default empty) -- IDs filtered by default
- Connectors: `Tick_T_Recv_Sync`, `Event_T_Recv_Sync` (events in), `Command_T_Recv_Sync`, `Event_Forward_T_Send` (passed events), `Event_T_Send` (component events), `Sys_Time_T_Get`, `Command_Response_T_Send`, `Data_Product_T_Send`, `Packet_T_Send` (9 total)

**event_limiter** (passive)
- Purpose: Rate-limit events to prevent flooding
- Use: Prevent event storms, maintain system stability
- Init: `Event_Id_Start` (Event_Types.Event_Id) -- start of ID range for limiting, `Event_Id_Stop` (Event_Types.Event_Id) -- end of ID range, `Event_Disable_List` (Two_Counter_Entry.Event_Id_List, default empty) -- IDs disabled by default, `Event_Limit_Persistence` (Two_Counter_Entry.Persistence_Type) -- max events per tick before limiting (1-7)
- Connectors: `Tick_T_Recv_Sync` (decrement counters), `Event_T_Recv_Sync` (events in), `Command_T_Recv_Sync`, `Event_Forward_T_Send` (passed events), `Event_T_Send` (component events), `Sys_Time_T_Get`, `Command_Response_T_Send`, `Data_Product_T_Send`, `Packet_T_Send` (state dump)

**event_packetizer** (passive)
- Purpose: Collect events into packets with timeout
- Use: Efficient event downlink batching
- Preamble: Defines `Two_Or_More` subtype (Positive range 2 .. Positive'Last)
- Init (NO init_base):
  - `Num_Internal_Packets` (Two_Or_More) -- number of internal double-buffered packets; minimum 2. When all exhausted, events are dropped
  - `Partial_Packet_Timeout` (Natural) -- ticks before sending a partial packet (must have ≥1 event); 0 disables (only full packets sent)
- Connectors: `Tick_T_Recv_Sync` (triggers send of full/timeout packets), `Event_T_Recv_Sync` (events IN -- NOT Event_T_Send), `Command_T_Recv_Sync`, `Packet_T_Send` (event packets out as Packet.T), `Sys_Time_T_Get`, `Data_Product_T_Send`, `Command_Response_T_Send` (7 total)

**event_text_logger** (active)
- Purpose: Print events as text using assembly-specific conversion
- Use: Human-readable event logging for debugging
- Discriminant: `Event_To_Text` (required, assembly-generated access type)
- Connectors: `Event_T_Recv_Async` only (NO Sys_Time_T_Get connector)

## System Monitoring (5 components)

**cpu_monitor** (passive)
- Purpose: Monitor CPU execution time for tasks/interrupts over 3 configurable time periods
- Use: System performance monitoring and diagnostics. Uses Ada.Execution_Time.Clock (nonstandard interface -- reads task IDs from autocoded globals, not connectors)
- Preamble: Defines `Num_Measurement_Periods` (range 0..2), `Execution_Periods_Type` (array of Positive indexed by Num_Measurement_Periods)
- Init:
  - `Task_List` (Task_Types.Task_Info_List_Access, not_null) -- autocoded list of tasks to monitor
  - `Interrupt_List` (Interrupt_Types.Interrupt_Id_List_Access, not_null) -- autocoded list of interrupts to monitor
  - `Execution_Periods` (Execution_Periods_Type, default [1, 6, 30]) -- tick multiples for each of 3 measurement windows (e.g. at 10s tick: 10s, 1min, 5min)
  - `Packet_Period` (Unsigned_16, default 1) -- ticks between packet sends; 0 disables
- Connectors: `Tick_T_Recv_Sync`, `Packet_T_Send`, `Sys_Time_T_Get`, `Command_T_Recv_Sync`, `Command_Response_T_Send`, `Data_Product_T_Send`, `Event_T_Send` (7 total)

**queue_monitor** (passive)
- Purpose: Monitor queue usage for all queued components
- Use: System health monitoring for queue utilization
- Init: `Queued_Component_List` (Component.Component_List_Access, not_null), `Packet_Period` (Unsigned_16, default "1")
- Connectors: Tick.T recv_sync, Packet.T send, Sys_Time.T get, Command.T recv_sync, Command_Response.T send, Data_Product.T send, Event.T send (7 total)

**stack_monitor** (passive)
- Purpose: Monitor stack and secondary stack usage (percent) for all assembly tasks
- Use: System health monitoring for task stack utilization; recalculates on every tick
- Init:
  - `Task_List` (Task_Types.Task_Info_List_Access, not_null) -- autocoded list of tasks to monitor
  - `Packet_Period` (Unsigned_16, default 1) -- ticks between packet sends; 0 disables
- Connectors: `Tick_T_Recv_Sync`, `Packet_T_Send`, `Sys_Time_T_Get`, `Command_T_Recv_Sync`, `Command_Response_T_Send`, `Data_Product_T_Send`, `Event_T_Send` (7 total)

**task_watchdog** (passive)
- Purpose: Monitor component health via pets
- Use: Software watchdog for component liveness monitoring
- Init:
  - `Task_Watchdog_Entry_Init_List` (Task_Watchdog_Types.Task_Watchdog_Init_List) -- autocoded list of monitored components with limits, criticality, and actions
- Connectors: `Tick_T_Recv_Sync`, `Pet_T_Recv_Sync` (arrayed, count=0, one per monitored component), `Pet_T_Send` (downstream hw watchdog), `Command_T_Recv_Sync`, `Command_Response_T_Send`, `Fault_T_Send`, `Event_T_Send`, `Data_Product_T_Send`, `Sys_Time_T_Get` (9 total)

**last_chance_manager** (passive)
- Purpose: Manage non-volatile exception data from LCH
- Use: Exception debugging and system recovery
- Init: `Exception_Data` (Packed_Exception_Occurrence.T_Access, not_null) -- nonvolatile memory region for LCH data, `Dump_Exception_Data_At_Startup` (Boolean) -- auto-dump exception data at startup
- Connectors: `Command_T_Recv_Sync`, `Command_Response_T_Send`, `Packet_T_Send` (exception dumps), `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`

## Interrupt Handling (3 components)

**interrupt_listener** (passive)
- Purpose: Poll-based access to interrupt data
- Use: Check if interrupt occurred and get associated data
- Generic: `Interrupt_Data_Type` -- user-defined datatype set in custom interrupt handler and returned to downstream components; consider using `Tick.T` (timestamp + count) if no specific data needed
- With: `Interrupt_Handlers`
- Discriminant: `custom_Interrupt_Procedure` (Custom_Interrupt_Handler_Package.Interrupt_Procedure_Type) -- custom procedure called within interrupt handler; use null procedure if no specific behavior desired
- Interrupts: `interrupt` -- interrupt source that triggers data collection
- Connectors: `Interrupt_Data_Type_Return` (interrupt data generated by custom procedure returned via this connector)

**interrupt_pender** (passive)
- Purpose: Block execution until interrupt, then release with user-defined interrupt data
- Use: Synchronous interrupt-driven component coordination -- only one component can attach to return connector
- Generic: `Interrupt_Data_Type` (user-defined data collected during interrupt; consider `Tick.T` if no specific data needed), `Set_Interrupt_Data_Time` (optional procedure to set timestamp in interrupt data)
- With: `Interrupt_Handlers`
- Discriminant: `custom_Interrupt_Procedure` (Custom_Interrupt_Handler_Package.Interrupt_Procedure_Type) -- custom procedure called in interrupt handler; use null procedure if no specific behavior
- Interrupts: `interrupt` -- interrupt source that triggers data release
- Connectors: `Wait_On_Interrupt_Data_Type_Return` (blocks caller until interrupt), `Sys_Time_T_Get` (optional, for timestamping)

**interrupt_servicer** (active)
- Purpose: Execute attached component on internal task when interrupt received with user-defined data
- Use: Asynchronous interrupt-to-task context switching for downstream component execution
- Generic: `Interrupt_Data_Type` (user-defined data collected during interrupt; consider `Tick.T` if no specific data needed), `Set_Interrupt_Data_Time` (optional procedure to set timestamp in interrupt data)
- With: `Interrupt_Handlers`
- Discriminant: `custom_Interrupt_Procedure` (Custom_Interrupt_Handler_Package.Interrupt_Procedure_Type) -- custom procedure called in interrupt handler; use null procedure if no specific behavior
- Interrupts: `interrupt` -- interrupt source that triggers task execution
- Connectors: `Interrupt_Data_Type_Send` (sends interrupt data to downstream component), `Sys_Time_T_Get` (optional, for timestamping)

## Memory Management (8 components)

**memory_copier** (active)
- Purpose: Service memory copy commands with timeout
- Use: Safe memory region copying between addresses
- Init: `ticks_Until_Timeout` (Natural) -- timeout ticks before failing copy command
- Connectors: `Timeout_Tick_Recv_Sync` (timeout tick), `Command_T_Recv_Async`, `Command_Response_T_Send`, `Memory_Region_Copy_T_Send` (copy request), `Memory_Region_Release_T_Recv_Sync` (copy response), `Memory_Region_Request_T_Get` (scratch memory), `Ided_Memory_Region_T_Send` (release scratch), `Event_T_Send`, `Sys_Time_T_Get`

**memory_dumper** (active)
- Purpose: Dump memory regions or compute CRC by command
- Use: Memory inspection and verification
- Init: `memory_Regions` (Memory_Manager_Types.Memory_Region_Array_Access, not_null) -- list of allowed memory regions for dumping/CRC
- Connectors: `Command_T_Recv_Async`, `Command_Response_T_Send`, `Memory_Dump_Send` (to Memory_Packetizer), `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`

**memory_manager** (active)
- Purpose: Manage single memory location with loan/return IDs
- Use: Thread-safe memory region access control
- Init: 
  - `bytes` (Basic_Types.Byte_Array_Access, default null) -- pointer to preallocated memory region; if null, heap allocation used
  - `size` (Integer, default -1) -- bytes to allocate on heap if bytes=null; must be negative if bytes not null
- Connectors: `Memory_Region_Request_T_Return` (memory requests), `Ided_Memory_Region_T_Release` (memory returns), `Command_T_Recv_Async`, `Command_Response_T_Send`, `Memory_Dump_Send`, `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`

**memory_packetizer** (active)
- Purpose: Packetize memory regions with sequence tracking
- Use: Background memory downlink with multiple packet IDs
- Init:
  - `Max_Packets_Per_Time_Period` (Natural) -- max packets per time period to throttle output
  - `Time_Period_In_Seconds` (Positive, default 1) -- time period for throttling
  - `Max_Packet_Ids` (Positive, default 10) -- max unique packet IDs for sequence count tracking
- Connectors: `Packet_T_Send`, `Memory_Dump_Recv_Async` (memory regions to packetize), `Command_T_Recv_Async`, `Command_Response_T_Send`, `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`

**memory_packetizer_fixed_id** (active)
- Purpose: Packetize memory regions with single fixed packet ID and rate throttling
- Use: Background memory downlink with consistent packet ID -- ignores ID field from Memory_Dump input
- Init:
  - `Max_Packets_Per_Time_Period` (Natural) -- max packets per time period to throttle output
  - `Time_Period_In_Seconds` (Positive, default 1) -- time period for throttling measurement
- Connectors: `Packet_T_Send`, `Memory_Dump_Recv_Async` (memory regions to packetize), `Command_T_Recv_Async`, `Command_Response_T_Send`, `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`

**memory_stuffer** (active)
- Purpose: Write to memory regions with optional protection
- Use: Safe memory writing with arming mechanism
- Init:
  - `memory_Regions` (Memory_Manager_Types.Memory_Region_Array_Access, not_null) -- list of memory regions available for writing
  - `memory_Region_Protection_List` (Memory_Manager_Types.Memory_Protection_Array_Access, default null) -- protection state per memory region (protected/unprotected); if null, all regions are unprotected
- Connectors: `Tick_T_Recv_Async` (arm timeout tracking), `Command_T_Recv_Async`, `Memory_Region_Copy_T_Recv_Async` (memory copy requests), `Memory_Region_Release_T_Send` (release copied memory), `Command_Response_T_Send`, `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`

**logger** (passive)
- Purpose: Log generic data to circular buffer with configurable memory allocation
- Use: Data logging and playback for any data type with heap or static memory options
- Generic: `T` (any data type to log), `Serialized_Length` (function for variable-length packed types)
- With: `Circular_Buffer_Meta`, `Serializer_Types`, `Logger_Enums`
- Init:
  - `bytes` (Basic_Types.Byte_Array_Access, default null) -- preallocated memory for log data; if null, heap allocation used
  - `meta_Data` (Circular_Buffer_Meta.T_Access, default null) -- preallocated meta data storage; must be null if size positive
  - `size` (Integer, default -1) -- bytes to allocate on heap if bytes=null; must be negative if bytes not null
  - `initial_Mode` (Logger_Enums.Logger_Mode.E, default Disabled) -- initial logging state (enabled/disabled)
- Connectors: `T_Recv_Sync` (generic data in), `Memory_Dump_Send` (to memory packetizer), `Command_T_Recv_Sync`, `Command_Response_T_Send`, `Event_T_Send`, `Data_Product_T_Send`, `Sys_Time_T_Get`

**limiter** (passive)
- Purpose: Rate-limit generic data output by tick rate with configurable threshold
- Use: Queue and meter output of any data type at commandable rates; packet rate in units of periodic tick
- Generic: `T` (any data type), `Serialized_Length` (function for variable-length packed types)
- With: `Serializer_Types`
- Init: `Max_Sends_Per_Tick` (Interfaces.Unsigned_16) -- maximum sends per tick; stops at threshold or empty queue
- Connectors: `Tick_T_Recv_Sync` (rate control), `T_Recv_Async` (queued input), `T_Send` (metered output), `Command_T_Recv_Sync` (optional), `Command_Response_T_Send` (optional), `Parameter_Update_T_Modify` (optional), `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`

## Parameter Management (2 components)

**parameters** (active)
- Purpose: Stage, update, report active system parameters
- Use: Central parameter management and distribution
- Init:
  - `Parameter_Table_Entries` (Parameters_Component_Types.Parameter_Table_Entry_List_Access, not_null) -- autocoded parameter table layout
  - `Table_Id` (Parameter_Types.Parameter_Table_Id) -- unique ID for this parameter table (autocoded)
  - `Dump_Parameters_On_Change` (Boolean, default False) -- auto-dump on any parameter change
- Connectors: `Parameter_Update_T_Provide` (arrayed, count=0), `Command_T_Recv_Async`, `Command_Response_T_Send`, `Parameters_Memory_Region_T_Recv_Async` (table upload or store), `Parameters_Memory_Region_Release_T_Send`, `Packet_T_Send`, `Event_T_Send`, `Data_Product_T_Send`, `Sys_Time_T_Get` (9 total)

**parameter_store** (active)
- Purpose: Store parameter table in non-volatile memory
- Use: Persistent parameter storage and backup
- Init: `bytes` (Basic_Types.Byte_Array_Access, not_null -- must match parameter table size exactly), `dump_Parameters_On_Change` (Boolean, default "False")
- Connectors: Command.T recv_async, Command_Response.T send, Parameters_Memory_Region.T recv_async, Parameters_Memory_Region_Release.T send, Packet.T send, Event.T send, Sys_Time.T get (7 total)

## Control Systems (1 component)

**pid_controller** (passive)
- Purpose: PID control with P/I/D gains, integral wind-up limiting, and optional statistical diagnostics
- Use: Closed-loop control systems with feed-forward, error statistics (mean/variance/max), and diagnostic packets
- Init:
  - `control_Frequency` (Short_Float) -- control frequency in Hz for PID time step calculation
  - `database_Update_Period` (Unsigned_16) -- period in ticks for data product updates
  - `moving_Average_Max_Samples` (Natural) -- max diagnostic samples for statistics; 0 disables statistics
  - `moving_Average_Init_Samples` (Integer, default -1) -- initial samples for statistics; -1 uses max
- Connectors: `Control_Input_U_Recv_Sync` (measured/commanded positions + feed-forward), `Control_Output_U_Send` (PID output), `Parameter_Update_T_Modify` (PID gains), `Packet_T_Send` (diagnostics), `Command_T_Recv_Sync`, `Command_Response_T_Send`, `Event_T_Send`, `Data_Product_T_Send`, `Sys_Time_T_Get`

## Data Product Management (4 components)

**product_copier** (passive)
- Purpose: Copy data products between databases at intervals
- Use: Data product snapshotting and synchronization
- With: `Product_Mapping`
- Init:
  - `Products_To_Copy` (Product_Mapping_Array_Access, not_null) -- list of source/destination ID mappings to copy each tick; raises error if null or duplicate destinations exist
  - `Send_Event_On_Source_Id_Out_Of_Range` (Boolean, default True) -- send error event when fetch status is Id_Out_Of_Range (may indicate misconfiguration)
  - `Send_Event_On_Source_Not_Available` (Boolean, default False) -- send error event when fetch status is Not_Available (may be expected if product not ready)
- Connectors: `Tick_T_Recv_Sync` (trigger copy), `Data_Product_T_Send` (destination), `Data_Product_Fetch_T_Request` (source), `Event_T_Send`, `Sys_Time_T_Get`

**product_database** (passive)
- Purpose: Fast ID-indexed database for latest data products using direct ID-to-index lookup
- Use: Central telemetry database with direct indexing. Works best with compact (non-sparse) ID spaces
- Init:
  - `Minimum_Data_Product_Id` (Data_Product_Types.Data_Product_Id) -- minimum accepted ID
  - `Maximum_Data_Product_Id` (Data_Product_Types.Data_Product_Id) -- maximum accepted ID; heap allocates max-sized entry for every ID in range
  - `Send_Event_On_Missing` (Boolean, default True) -- send event when fetching a missing product; disable if expected
- Connectors: `Data_Product_T_Recv_Sync` (store), `Data_Product_Fetch_T_Service` (fetch by ID), `Event_T_Send`, `Command_T_Recv_Sync`, `Command_Response_T_Send`, `Data_Product_T_Send` (component DPs), `Packet_T_Send` (database dumps), `Sys_Time_T_Get` (8 total)
- **NOT the same as Ccsds_Packetizer**: Product_Database produces `Packet.T`; Ccsds_Packetizer receives `Packet.T` and produces CCSDS-framed packets

**product_packetizer** (passive)
- Purpose: Request data products and packetize at rates
- Use: Telemetry packet generation from data products
- Discriminant: `Packet_List` (Product_Packet_Types.Packet_Description_List_Access_Type, autocoded from product_packets.yaml)
- Init: `Commands_Dispatched_Per_Tick` (Positive, default 3)
- Connectors: `Tick_T_Recv_Sync`, `Data_Product_Fetch_T_Request` (request to Product_Database), `Packet_T_Send` (packets out), `Command_T_Recv_Async`, `Event_T_Send`, `Sys_Time_T_Get`, `Command_Response_T_Send`

**sequence_store** (active)
- Purpose: Manage memory slots storing sequences by ID with unique activation control
- Use: Non-volatile sequence storage and management; enforces unique sequence IDs for activated sequences, prevents conflicts
- With: `Sequence_Store_Types`, `Memory_Region`
- Preamble: Defines `Sequence_Slot_Array` (array of Memory_Region.T) and `Sequence_Slot_Array_Access`
- Init:
  - `sequence_Slots` (Sequence_Slot_Array_Access, not_null) -- array of memory regions (slots) to manage; each slot holds one sequence plus header/metadata; slots must not overlap and be large enough for sequence header
  - `check_Slots_At_Startup` (Boolean) -- if True, validate sequences in all slots via CRC at startup
  - `dump_Slot_Summary_At_Startup` (Boolean) -- if True, dump slot summaries at startup
- Connectors: `Command_T_Recv_Async`, `Command_Response_T_Send`, `Sequence_Store_Memory_Region_Store_T_Recv_Async` (load sequences), `Sequence_Store_Memory_Region_Fetch_T_Service` (fetch by Packed_Sequence_Id.T, returns Sequence_Store_Memory_Region_Fetch.T), `Sequence_Store_Memory_Region_Release_T_Send`, `Packet_T_Send` (slot summaries), `Event_T_Send`, `Sys_Time_T_Get`

## Rate Group & Scheduling (5 components)

**rate_group** (active)
- Purpose: Execute components at periodic rate with cycle slip detection and timing reports
- Use: Fundamental scheduling providing tasks for passive components; executes connected components in order
- Init:
  - `Ticks_Per_Timing_Report` (Interfaces.Unsigned_16, default 1) -- period in ticks for timing report data product (0=disabled)
  - `Timing_Report_Delay_Ticks` (Interfaces.Unsigned_16, default 3) -- ticks to wait before calculating timing report (ignores startup transients)
  - `Issue_Time_Exceeded_Events` (Boolean, default False) -- issue events when execution time exceeds maximum
- Connectors: `Tick_T_Recv_Async` (periodic trigger), `Tick_T_Send` (arrayed output, count=0), `Pet_T_Send` (watchdog service), `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`

**tick_divider** (passive)
- Purpose: Divide tick rate into multiple subrates with priority ordering
- Use: Multi-rate scheduling from single tick source; first connector has highest priority
- With: `Connector_Types`, `Interfaces`
- Preamble:
  - `Divider_Array_Type` (array of Interfaces.Unsigned_32 indexed by Connector_Types.Connector_Index_Type)
  - `Divider_Array_Type_Access` (access to Divider_Array_Type)
  - `Tick_Source_Type` (Internal, Tick_Counter) -- counting mode
- Init:
  - `Dividers` (Divider_Array_Type_Access, not_null) -- divisor values per output connector (0=disabled)
  - `Tick_Source` (Tick_Source_Type, default Internal) -- use internal counter or incoming tick's Count field
- Connectors: `Tick_T_Recv_Sync` (input), `Tick_T_Send` (arrayed output, count=0), `Event_T_Send`, `Sys_Time_T_Get`

**ticker** (active)
- Purpose: Generate periodic ticks at microsecond intervals
- Use: Primary tick source for assembly scheduling
- Discriminant: `Period_Us` (Positive) -- the tick period in microseconds
- Connectors: `Tick_T_Send` (periodic output), `Sys_Time_T_Get`

**tick_listener** (passive)
- Purpose: Count ticks since last invocation and return count on demand
- Use: Software interrupt simulation; useful substitute for interrupt_listener when simulating interrupts with software ticks
- No init parameters
- Connectors: `Get_Tick_Count` (returns Packed_Natural.T with tick count since last call), `Tick_T_Recv_Sync` (tick input)

**splitter** (passive)
- Purpose: Split single connector into arrayed outputs for simultaneous distribution
- Use: Fan-out distribution when single send connector needs to go to multiple destinations
- Generic: `T` (any connector type for compile-time instantiation)
- No init parameters
- Connectors: `T_Recv_Sync` (single input), `T_Send` (arrayed output, count=0, size determined by assembly)

## Time Synchronization (4 components)

**gps_time** (passive)
- Purpose: Provide GPS-format system time service
- Use: Central time service for assembly
- No init parameters
- Connectors: `Sys_Time_T_Return` (provides GPS time service)

**precision_time_protocol_master** (active)
- Purpose: PTP master implementing precision time protocol for slave synchronization with follow-up message support
- Use: High-precision distributed time synchronization -- slaves measure/sync to this master's clock
- Init:
  - `Sync_Period` (Positive, default 1) -- ticks between PTP message sends; 0 disables syncing
  - `Enabled_State` (Ptp_State.Ptp_State_Type, default Enabled) -- startup enabled/disabled state
- Connectors: `Tick_T_Recv_Async` (sync frequency control), `Command_T_Recv_Async`, `Ptp_Time_Message_Receive_T_Recv_Async` (Delay_Request from slaves), `Follow_Up_Sys_Time_T_Recv_Async` (accurate Sync timestamp), `Ptp_Time_Message_T_Send` (Sync messages out), `Sys_Time_T_Get`, `Command_Response_T_Send`, `Event_T_Send`, `Data_Product_T_Send`

**time_at_tone_master** (passive)
- Purpose: TaT protocol master (time message, then tone)
- Use: Clock synchronization using time-at-tone

**time_of_tone_master** (passive)
- Purpose: TaT master variant (tone first, then accurate time)
- Use: Higher-accuracy clock synchronization

## Fault Management (2 components)

**fault_correction** (active)
- Purpose: Automated fault response via command correction
- Use: Fault response and recovery
- Init: `Fault_Response_Configurations` (Fault_Correction_Types.Fault_Response_Config_List)
- Connectors: Command.T recv_async, Command_Response.T send, Fault.T recv_async, Command.T send (correction output), Data_Product.T send, Event.T send, Sys_Time.T get (7 total)

**zero_divider** (passive)
- Purpose: Safe divide-by-zero to trigger Last Chance Handler
- Use: System testing and exception handler verification

## Hardware Interface (1 component)

**register_stuffer** (passive)
- Purpose: Atomic 32-bit register read/write with protection
- Use: Hardware register access with optional arming
- Init: `Protect_Registers` (Boolean) -- if True, arm command required before each register write; if False, no arm required (does not affect reads); assumes all registers are little endian and rejects non-4-byte-aligned addresses
- Connectors: `Tick_T_Recv_Sync` (arm timeout tracking), `Command_T_Recv_Sync`, `Command_Response_T_Send`, `Data_Product_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`, `Packet_T_Send`

## Component Selection Guide

**Need CCSDS communication?** Use ccsds_router + ccsds_packetizer/command_depacketizer
**Need rate groups?** Use ticker -> tick_divider -> rate_group pattern
**Need telemetry?** Use product_database + product_packetizer
**Need parameters?** Use parameters + parameter_store
**Need event management?** Use event_filter + event_packetizer
**Need fault protection?** Use task_watchdog + fault_correction
**Need memory operations?** Use memory_manager + memory_packetizer
**Need command routing?** Use command_router + command_protector
**Need monitoring?** Use cpu_monitor + stack_monitor + queue_monitor (all passive; cpu_monitor and stack_monitor require autocoded `Task_Info_List_Access`; cpu_monitor also needs `Interrupt_Id_List_Access`)
**Need sequences?** Use command_sequencer + sequence_store

Components marked (either) can be active or passive - choose based on assembly needs.
Generic components require type instantiation at compile time.

## Name Collision Risk

Component names must be unique across the entire build path (framework + project). These framework names are commonly reused by accident:

`attitude_estimator`, `command_sequencer`, `event_filter`, `fault_correction`, `limiter`, `logger`, `mode_manager`, `orbit_propagator`, `parameters`, `pid_controller`, `power_manager`, `splitter`, `telemetry_formatter`, `telemetry_manager`

**Prevention**: Prefix project components with a project-specific name (e.g., `myproject_attitude_estimator`, `myproject_pid_controller`).

## References
- [references/component-audit.md](references/component-audit.md) -- Framework component accuracy audit (100% verified)

## Related Skills
- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
- **Subassemblies**: [adamant-subassemblies](../adamant-subassemblies/SKILL.md)
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md)
- **COSMOS**: [adamant-cosmos-integration](../adamant-cosmos-integration/SKILL.md) -- CCSDS components for ground system