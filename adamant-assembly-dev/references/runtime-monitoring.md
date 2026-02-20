<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Assembly Runtime Monitoring Reference

## Assembly Lifecycle (MUST follow this order)

```ada
Init_Base;           -- Allocate queues, base memory
Set_Id_Bases;        -- Establish ID ranges (commands, events, DPs, packets)
Connect;             -- Wire all component connectors
Init_Components;     -- Component-specific initialization with params
delay 0.1;           -- Let tasks stabilize
Start_Components;    -- Launch active component tasks (BEFORE Set_Up)
Set_Up_Components;   -- Final config after all tasks running
-- Enter main loop (infinite delay or periodic heartbeat)
```

WARNING: Start BEFORE Set_Up. Reversing causes silent failures.

## Multi-Rate Scheduling

### Rate Hierarchy Pattern
```
Ticker (base rate, e.g. 5Hz/200ms)
    |
Tick_Divider [D1, D2, D3]
    ├── Rate_Group_1 (base/D1 Hz)  -- index 0 = highest priority
    ├── Rate_Group_2 (base/D2 Hz)  -- index 1
    └── Rate_Group_3 (base/D3 Hz)  -- index 2
```

- Tick_Divider divisors: `[5, 10, 1]` from 5Hz base = 1Hz, 0.5Hz, 5Hz
- Lower array index = higher execution priority
- Max_Count = product of all divisors (e.g. 50 for [5,10,1])
- Assembly preamble defines divisor array: `Dividers : aliased Component.Tick_Divider.Divider_Array_Type := [1 => 1, 2 => 10];`
- Init: `"Dividers => Dividers'Access"`
- Assembly build cache: must `redo clean` in BOTH assembly dir AND main dir to regenerate (do NOT use `rm -rf build`)
- Behavioral change: faster tick rates cause faster counter accumulation, may trigger timeouts sooner
- Single Ticker -> single Tick_Divider is standard pattern

### Typical Rate Assignment
| Rate | Usage |
|------|-------|
| 1Hz | Task watchdog, housekeeping |
| 0.5Hz | Event packetizer, monitors (CPU, queue, stack) |
| 5Hz | Data product packetizer, application logic |

### Priority Strategy
```
Priority 11: Fault_Correction (immediate fault response)
Priority 10: Ticker, Watchdog_Rate_Group
Priority 9:  Application rate groups
Priority 8:  Command_Router
Priority 6:  Socket_Interface (I/O)
Priority 3:  Parameter system
Priority 1:  Event_Text_Logger, background tasks
```

## Event Flow Architecture

### Dual-Path Pattern (standard)
```
All Components --> Event_Splitter
                    ├── [unfiltered] Event_Post_Mortem_Logger (ALL events)
                    └── [filtered]  Event_Filter --> Event_Limiter --> Event_Splitter_2
                                                                        ├── Event_Packetizer (CCSDS downlink)
                                                                        └── Event_Text_Logger (stderr)
```

- Post-mortem path preserves ALL events for crash analysis
- Filtered path prevents downlink saturation
- Event_Limiter: rate-limits per event ID (5-event persistence window)
- Event_Text_Logger: writes to Standard_Error (Ada.Text_IO)

### Event_Text_Logger
- Active component (async queue)
- Discriminant: `Event_To_Text => Assembly_Event_To_Text.Event_To_Text'Access`
- Output format: `SSSSSSSSSSS.NNNNNNNNN - Component.Event_Name (0xHHHH) : (params)`
- Auto-generated `Event_To_Text` function maps event IDs to human-readable strings

## CCSDS Pipeline

### Downlink (assembly -> ground)
```
Product_Database --fetch--> Product_Packetizer --Packet.T--> CCSDS_Packetizer --CCSDS--> Socket
Event_Packetizer --Packet.T-------->|
Other packet sources -------------->|
```

### Uplink (ground -> assembly)
```
Socket --CCSDS--> [optional: CCSDS_Router] --> Command_Depacketizer --> Command_Router --> Components
```

- linux_example bypasses CCSDS_Router (direct socket -> depacketizer)
- Command_Depacketizer validates: size, XOR-8 checksum, packet type, secondary header

### CCSDS Packet Structure
```
| Primary Header (6B) | Secondary Header/Timestamp (8B) | Data (var) | CRC-16 (2B) |
```
- CRC-16: CCITT polynomial, seed 0xFFFF
- APID from original Adamant Packet ID

### Socket Interface
- Active component with Listener subtask
- Default: TCP to 127.0.0.1:2003 (configurable)
- Auto-reconnect on connection loss
- Events: Socket_Connected, Socket_Not_Connected

## Data Product Pipeline

### Product_Packetizer
- Tick-driven (typically on fast rate group)
- Fetches DPs from Product_Database via get connector
- Packet definitions auto-generated from product_packets.yaml
- Each packet: independent period, offset, enable state
- Supports on-change mode (only send when DP values change)
- Commands: enable/disable packets, change periods, force send

## Ground Tools (Python)

### Socket Event Decoder (real-time monitoring)
```bash
cd adamant/gnd/bin
python socket_event_decoder.py <IP> <PORT> <APP_ID> <assembly_events.py> <log_file>
# Example:
python socket_event_decoder.py 127.0.0.1 2003 1 \
    /path/to/build/src/assembly_events.py events.log
```
- Connects via TCP (default) or UDP (`--udp`)
- Decodes CCSDS packets, validates CRC, extracts events
- Uses auto-generated `assembly_events.py` for event ID -> name mapping
- `-P` flag for production (skip auto-build)

### Decode Event Packets (post-mortem)
```bash
python decode_event_packets.py <assembly_events.py> <binary_dump.bin>
```

### Fast CCSDS Checker (packet analysis)
```bash
python fast_ccsds_checker.py <binary_file> [--apids 1 2 3]
```
- Memory-mapped I/O for large files
- Sequence count gap detection
- CRC validation statistics
- APID breakdown table

### Generated Ground Artifacts
- `assembly_events.py` -- event ID -> class mapping (auto-generated)
- Python packed type classes -- serialization/deserialization
- Event class generator -- creates component-specific event classes

## Runtime Health Monitoring

### Task Watchdog
- Passive, runs on watchdog rate group (1Hz)
- Pet-based: components send periodic pet messages
- Per-component config: limit (missed pets), action (warn/fault), critical flag
- Critical components: if they fail, hardware watchdog stops being petted
- Commands: enable/disable monitoring, change limits

### Stack Monitor
- Pattern-based: stacks filled with 0xCC at startup
- Searches for last 0xCC boundary to determine usage
- Reports percentage per task (primary + secondary stack)
- Caches search index for efficiency

### Queue Monitor
- Reports current and high-water-mark queue percentages per component
- 2 bytes per monitored component
- Runs on slow rate group

### Cycle Slip Detection
- Rate_Group checks queue depth after execution
- If > 0 pending ticks: rate group running too slow
- Generates event with tick count for diagnosis

## Connector Type Strategy for Runtime
- **Async**: Rate groups, most data producers (can't block)
- **Sync**: Time-critical paths, command responses
- **Critical bypass**: Fault_Correction uses sync to bypass Command_Router queue
- **Get**: Time service (Sys_Time), data product fetch

## CCSDS Socket: Assembly is TCP CLIENT

CRITICAL: The Ccsds_Socket_Interface is a TCP CLIENT -- it connects TO a ground system server.
Without a server (COSMOS, socat relay, or custom TCP server), the ground Python tools cannot
receive CCSDS telemetry. The `socket_event_decoder.py` is ALSO a TCP client.

For development without COSMOS:
- Primary monitoring: Event_Text_Logger stderr output (always works)
- Use `tools/event_monitor.sh` and `tools/event_stats.py` to parse stderr
- For CCSDS ground tools: start COSMOS first, or use `socat` as a TCP relay

## Development Monitoring Tools

### event_monitor.sh
```bash
# Run assembly, capture events for N seconds
docker exec adamant bash -c "timeout 10 ./main.elf 2>&1"

# Filter for errors/faults only
docker exec adamant bash -c "timeout 10 ./main.elf 2>&1 | grep 'Error\|Fault'"
```

### event_stats.py
```bash
# Parse stderr output, print event statistics
docker exec adamant bash -c "timeout 10 ./main.elf 2>&1 | python3 tools/event_stats.py"
```
Output: total events, rate, unique types, per-component breakdown.

## Practical: Running the Demo Assembly

```bash
# In Docker:
source /home/user/adamant/env/activate /home/user/<project_dir>
cd /home/user/<project_dir>/src/assembly/<assembly_name>/main

# Build
redo build/bin/Linux/main.elf

# Run (events to stderr)
./build/bin/Linux/main.elf 2>&1

# Separate stderr for event capture
./build/bin/Linux/main.elf 2>events.log &
tail -f events.log

# Ground tool monitoring (if CCSDS socket configured)
cd /home/user/adamant/gnd/bin
python socket_event_decoder.py 127.0.0.1 2003 1 \
    /home/user/<project_dir>/src/assembly/<assembly_name>/main/build/src/<assembly_name>_events.py \
    events.log
```
