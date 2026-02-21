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
- Connectors: `Ccsds_Space_Packet_T_Recv_Sync` (in), `Command_T_Send` (out), `Event_T_Send`, `Data_Product_T_Send`, `Packet_T_Send` (errors), `Sys_Time_T_Get`, `Command_Response_T_Send`, `Command_T_Recv_Sync` (self-commands)

**ccsds_downsampler** (passive)
- Purpose: Filter packets by APID with configurable rates
- Use: Reduce telemetry downlink rate for specific packet types

**ccsds_echo** (passive)
- Purpose: Echo CCSDS packets as Adamant packets
- Use: Loop back uplink as downlink

**ccsds_packetizer** (passive)
- Purpose: Adamant packets -> CCSDS packets with CRC/timestamp
- Use: Package internal packets for CCSDS downlink
- Connectors: `Packet_T_Recv_Sync` (in, receives Adamant packets), `Ccsds_Space_Packet_T_Send` (out, sends CCSDS packets)
- No init, no commands -- pure passthrough conversion with CRC16 + 8-byte secondary header timestamp

**ccsds_product_extractor** (passive)
- Purpose: Extract data products from CCSDS packet data
- Use: Parse telemetry from CCSDS packets into typed data

**ccsds_router** (either)
- Purpose: Route CCSDS packets by APID lookup table
- Use: Distribute packets to appropriate processing components
- Init: `Table` (Router_Table_Entry_Array), `Report_Unrecognized_APIDs` (Boolean, default True)
- Table entry type: `Router_Table_Entry` has fields: `Apid` (Ccsds_Apid_Type), `Destinations` (Destination_Table_Access -- array of connector indices), `Sequence_Count_Mode` (No_Check/Warn/Drop_Dupes). An autocoder exists to generate the table from YAML (`gen/` subdir).
- Connectors: `Ccsds_Space_Packet_T_Recv_Sync` (in sync), `Ccsds_Space_Packet_T_Recv_Async` (in async), `Ccsds_Space_Packet_T_Send` (arrayed, count=0 variable), `Unrecognized_Ccsds_Space_Packet_T_Send` (unmatched APIDs), `Event_T_Send`, `Packet_T_Send` (errors), `Sys_Time_T_Get`

**ccsds_serial_interface** (active)
- Purpose: CCSDS over serial via Ada.Text_IO
- Use: Backdoor serial interface for CCSDS communication

## Network Interfaces (2 components)

**ccsds_socket_interface** (active)
- Purpose: CCSDS over TCP/IP socket with listener task
- Use: Connect assembly to ground system via network
- init_base: `Queue_Size`
- init: `Addr` (String access), `Port` (Natural)
- subtasks: `Listener` (with priority/stack for recv task)
- Connectors: `Ccsds_Space_Packet_T_Send`, `Ccsds_Space_Packet_T_Recv_Async`, `Event_T_Send`, `Sys_Time_T_Get`

**ccsds_subpacket_extractor** (either)
- Purpose: Extract CCSDS subpackets from larger packets
- Use: Unpack multiplexed CCSDS packets

## Command Processing (6 components)

**command_protector** (passive)
- Purpose: Protect hazardous commands with arm/disarm + timeout
- Use: Prevent accidental execution of dangerous commands

**command_rejector** (passive)
- Purpose: Block commands based on ID blacklist
- Use: Prevent unwanted commands from specific sources

**command_router** (active)
- Purpose: Route commands by ID to destination components
- Use: Central command distribution hub for assembly
- init_base: `Queue_Size`, `Command_T_Send_Count`, `Command_Response_T_To_Forward_Send_Count`
- init: `Max_Number_Of_Commands`
- Connectors: `Command_T_To_Route_Recv_Async` (input), `Command_T_Send` (arrayed), `Command_Response_T_Recv_Async` (self-loopback from Forward), `Command_Response_T_To_Forward_Send`, `Event_T_Send`, `Data_Product_T_Send`, `Sys_Time_T_Get`

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

**connector_protector** (passive)
- Purpose: Thread-safe protected object for connectors
- Use: Add thread safety to non-thread-safe components

**connector_queuer** (active)
- Purpose: Add FIFO queue to synchronous connectors
- Use: Convert sync connectors to async with ordering

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

**event_packetizer** (passive)
- Purpose: Collect events into packets with timeout
- Use: Efficient event downlink batching
- Init: `Num_Internal_Packets` (Two_Or_More, min 2), `Partial_Packet_Timeout` (Natural, 0=disabled). NO init_base
- Connectors: `Tick_T_Recv_Sync`, `Event_T_Recv_Sync` (events in), `Command_T_Recv_Sync`, `Packet_T_Send` (event packets out), `Sys_Time_T_Get`, `Data_Product_T_Send`, `Command_Response_T_Send`

**event_text_logger** (active)
- Purpose: Print events as text using assembly-specific conversion
- Use: Human-readable event logging for debugging
- Discriminant: `Event_To_Text` (required, assembly-generated access type)
- Connectors: `Event_T_Recv_Async` only (NO Sys_Time_T_Get connector)

## System Monitoring (5 components)

**cpu_monitor** (passive)
- Purpose: Monitor CPU execution time for tasks/interrupts
- Use: System performance monitoring and diagnostics

**queue_monitor** (passive)
- Purpose: Monitor queue usage for all queued components
- Use: System health monitoring for queue utilization
- Init: `Queued_Component_List` (Component.Component_List_Access, not_null), `Packet_Period` (Unsigned_16, default "1")
- Connectors: Tick.T recv_sync, Packet.T send, Sys_Time.T get, Command.T recv_sync, Command_Response.T send, Data_Product.T send, Event.T send (7 total)

**stack_monitor** (passive)
- Purpose: Monitor stack usage for all assembly tasks
- Use: System health monitoring for task stack utilization

**task_watchdog** (passive)
- Purpose: Monitor component health via pets
- Use: Software watchdog for component liveness monitoring
- Init:
  - `Task_Watchdog_Entry_Init_List` (Task_Watchdog_Types.Task_Watchdog_Init_List) -- autocoded list of monitored components with limits, criticality, and actions
- Connectors: `Tick_T_Recv_Sync`, `Pet_T_Recv_Sync` (arrayed, count=0, one per monitored component), `Pet_T_Send` (downstream hw watchdog), `Command_T_Recv_Sync`, `Command_Response_T_Send`, `Fault_T_Send`, `Event_T_Send`, `Data_Product_T_Send`, `Sys_Time_T_Get` (9 total)

**last_chance_manager** (passive)
- Purpose: Manage non-volatile exception data from LCH
- Use: Exception debugging and system recovery

## Interrupt Handling (3 components)

**interrupt_listener** (passive)
- Purpose: Poll-based access to interrupt data
- Use: Check if interrupt occurred and get associated data

**interrupt_pender** (passive)
- Purpose: Block until interrupt, then release with data
- Use: Interrupt-driven component synchronization

**interrupt_servicer** (active)
- Purpose: Execute on task when interrupt received
- Use: Interrupt-to-task context switching

## Memory Management (8 components)

**memory_copier** (active)
- Purpose: Service memory copy commands with timeout
- Use: Safe memory region copying between addresses

**memory_dumper** (active)
- Purpose: Dump memory regions or compute CRC by command
- Use: Memory inspection and verification

**memory_manager** (active)
- Purpose: Manage single memory location with loan/return IDs
- Use: Thread-safe memory region access control

**memory_packetizer** (active)
- Purpose: Packetize memory regions with sequence tracking
- Use: Background memory downlink with multiple packet IDs

**memory_packetizer_fixed_id** (active)
- Purpose: Packetize memory regions with single packet ID
- Use: Background memory downlink with fixed packet ID

**memory_stuffer** (active)
- Purpose: Write to memory regions with optional protection
- Use: Safe memory writing with arming mechanism

**logger** (passive)
- Purpose: Log generic data to circular buffer
- Use: Data logging and playback for any data type

**limiter** (passive)
- Purpose: Rate-limit generic data output by tick rate
- Use: Rate control for any data type

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
- Purpose: PID control with P/I/D gains and diagnostics
- Use: Closed-loop control systems

## Data Product Management (4 components)

**product_copier** (passive)
- Purpose: Copy data products between databases at intervals
- Use: Data product snapshotting and synchronization

**product_database** (passive)
- Purpose: Fast ID-indexed database for latest data products
- Use: Central telemetry database with direct indexing
- Init: `Minimum_Data_Product_Id`, `Maximum_Data_Product_Id` (both required)
- Connectors: `Data_Product_T_Recv_Sync` (input), `Packet_T_Send` (output)
- **NOT the same as Ccsds_Packetizer**: Product_Database produces `Packet.T`; Ccsds_Packetizer receives `Packet.T` (via `T_Recv_Async`) and produces CCSDS-framed packets

**product_packetizer** (passive)
- Purpose: Request data products and packetize at rates
- Use: Telemetry packet generation from data products
- Discriminant: `Packet_List` (Product_Packet_Types.Packet_Description_List_Access_Type, autocoded from product_packets.yaml)
- Init: `Commands_Dispatched_Per_Tick` (Positive, default 3)
- Connectors: `Tick_T_Recv_Sync`, `Data_Product_Fetch_T_Request` (request to Product_Database), `Packet_T_Send` (packets out), `Command_T_Recv_Async`, `Event_T_Send`, `Sys_Time_T_Get`, `Command_Response_T_Send`

**sequence_store** (active)
- Purpose: Manage memory slots storing sequences by ID
- Use: Non-volatile sequence storage and management

## Rate Group & Scheduling (5 components)

**rate_group** (active)
- Purpose: Execute components at periodic rate with timing
- Use: Fundamental scheduling providing tasks for passive components
- init_base: `Queue_Size`, `Tick_T_Send_Count`
- init: `Ticks_Per_Timing_Report`
- Connectors: `Tick_T_Recv_Async`, `Tick_T_Send` (arrayed), `Pet_T_Send`, `Event_T_Send`, `Sys_Time_T_Get`

**tick_divider** (passive)
- Purpose: Divide tick rate into multiple subrates
- Use: Multi-rate scheduling from single tick source
- init_base: `Tick_T_Send_Count`
- init: `Dividers` (access to preamble-defined `Divider_Array_Type`)
- preamble: Define `Divider_Array_Type` as array of Natural
- Connectors: `Tick_T_Recv_Sync`, `Tick_T_Send` (arrayed), `Event_T_Send`, `Sys_Time_T_Get`

**ticker** (active)
- Purpose: Generate periodic ticks at microsecond intervals
- Use: Primary tick source for assembly scheduling
- discriminant: `Period_Us` (microseconds between ticks)
- Connectors: `Tick_T_Send`, `Sys_Time_T_Get`

**tick_listener** (passive)
- Purpose: Count ticks since last invocation
- Use: Software interrupt simulation

**splitter** (passive)
- Purpose: Split single connector into arrayed outputs
- Use: Fan-out distribution for any data type
- generic_types: `T => Event.T` (or any connector type)
- init_base: `T_Send_Count`
- Connectors: `T_Recv_Sync`, `T_Send` (arrayed)

## Time Synchronization (4 components)

**gps_time** (passive)
- Purpose: Provide GPS-format system time service
- Use: Central time service for assembly

**precision_time_protocol_master** (active)
- Purpose: PTP master for slave clock synchronization
- Use: High-precision time sync across system

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

## Component Selection Guide

**Need CCSDS communication?** Use ccsds_router + ccsds_packetizer/command_depacketizer
**Need rate groups?** Use ticker -> tick_divider -> rate_group pattern
**Need telemetry?** Use product_database + product_packetizer
**Need parameters?** Use parameters + parameter_store
**Need event management?** Use event_filter + event_packetizer
**Need fault protection?** Use task_watchdog + fault_correction
**Need memory operations?** Use memory_manager + memory_packetizer
**Need command routing?** Use command_router + command_protector
**Need monitoring?** Use cpu_monitor + stack_monitor + queue_monitor (note: stack_monitor and cpu_monitor require `Task_Types.Task_Info_List_Access` init params -- check component YAML for exact init signatures before using)
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