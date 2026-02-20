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

**ccsds_downsampler** (passive)
- Purpose: Filter packets by APID with configurable rates
- Use: Reduce telemetry downlink rate for specific packet types

**ccsds_echo** (passive)
- Purpose: Echo CCSDS packets as Adamant packets
- Use: Loop back uplink as downlink

**ccsds_packetizer** (passive)
- Purpose: Adamant packets -> CCSDS packets with CRC/timestamp
- Use: Package internal packets for CCSDS downlink

**ccsds_product_extractor** (passive)
- Purpose: Extract data products from CCSDS packet data
- Use: Parse telemetry from CCSDS packets into typed data

**ccsds_router** (either)
- Purpose: Route CCSDS packets by APID lookup table
- Use: Distribute packets to appropriate processing components

**ccsds_serial_interface** (active)
- Purpose: CCSDS over serial via Ada.Text_IO
- Use: Backdoor serial interface for CCSDS communication

## Network Interfaces (2 components)

**ccsds_socket_interface** (active)
- Purpose: CCSDS over TCP/IP socket with listener task
- Use: Connect assembly to ground system via network

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
- Init: `Max_Number_Of_Commands` (required). Self-loopback: Command_Response_T_To_Forward_Send -> own Command_Response_T_Recv_Async

**command_sequencer** (active)
- Purpose: Execute LASEL sequences with multiple engines
- Use: Automated sequence execution with parallel engines

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

## Event Management (4 components)

**event_filter** (passive)
- Purpose: Filter events by ID range and configurable state
- Use: Suppress unwanted events, debug mode control

**event_limiter** (passive)
- Purpose: Rate-limit events to prevent flooding
- Use: Prevent event storms, maintain system stability

**event_packetizer** (passive)
- Purpose: Collect events into packets with timeout
- Use: Efficient event downlink batching
- Init: `Num_Internal_Packets`, `Partial_Packet_Timeout` (both required). NO init_base

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

**stack_monitor** (passive)
- Purpose: Monitor stack usage for all assembly tasks
- Use: System health monitoring for task stack utilization

**task_watchdog** (passive)
- Purpose: Monitor component health via pets
- Use: Software watchdog for component liveness monitoring

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

**parameter_store** (active)
- Purpose: Store parameter table in non-volatile memory
- Use: Persistent parameter storage and backup

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

**sequence_store** (active)
- Purpose: Manage memory slots storing sequences by ID
- Use: Non-volatile sequence storage and management

## Rate Group & Scheduling (5 components)

**rate_group** (active)
- Purpose: Execute components at periodic rate with timing
- Use: Fundamental scheduling providing tasks for passive components

**tick_divider** (passive)
- Purpose: Divide tick rate into multiple subrates
- Use: Multi-rate scheduling from single tick source

**ticker** (active)
- Purpose: Generate periodic ticks at microsecond intervals
- Use: Primary tick source for assembly scheduling

**tick_listener** (passive)
- Purpose: Count ticks since last invocation
- Use: Software interrupt simulation

**splitter** (passive)
- Purpose: Split single connector into arrayed outputs
- Use: Fan-out distribution for any data type

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
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md)