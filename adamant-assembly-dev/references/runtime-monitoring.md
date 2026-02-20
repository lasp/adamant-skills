<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Assembly Runtime Monitoring Reference

## Assembly Lifecycle (MUST follow this order)

```ada
Init_Base;           -- Allocate queues, base memory
Set_Id_Bases;        -- Establish ID ranges
Connect;             -- Wire all component connectors
Init_Components;     -- Component-specific initialization
delay 0.1;           -- Let tasks stabilize
Start_Components;    -- Launch active tasks (BEFORE Set_Up)
Set_Up_Components;   -- Final config after all tasks running
```

WARNING: Start BEFORE Set_Up. Reversing causes silent failures.

## Event Flow Architecture

### Dual-Path Pattern (standard)
```
All Components --> Event_Splitter
                    ├── [unfiltered] Event_Post_Mortem_Logger (ALL events)
                    └── [filtered]  Event_Filter --> Event_Limiter --> Event_Splitter_2
                                                                        ├── Event_Packetizer
                                                                        └── Event_Text_Logger
```

- Post-mortem preserves ALL events for crash analysis
- Event_Limiter: rate-limits per event ID
- Event_Text_Logger output: `SSSSSSSSSSS.NNNNNNNNN - Component.Event_Name (0xHHHH) : (params)`

## CCSDS Pipeline

### Downlink
```
Product_Database --fetch--> Product_Packetizer --Packet.T--> CCSDS_Packetizer --CCSDS--> Socket
Event_Packetizer --Packet.T-------->|
```

### Uplink
```
Socket --CCSDS--> Command_Depacketizer --> Command_Router --> Components
```

For full COSMOS/ground setup, see [adamant-cosmos-integration](../../adamant-cosmos-integration/SKILL.md).

## Runtime Health Monitoring

| Component | What it does | Key detail |
|-----------|-------------|------------|
| Task_Watchdog | Pet-based liveness checking | Per-component limit/action/critical config |
| Stack_Monitor | Pattern-based (0xCC fill) stack usage | Reports % per task |
| Queue_Monitor | Current + high-water-mark queue % | 2 bytes per component |
| Cycle Slip | Rate_Group checks pending ticks after execution | > 0 = running too slow |

## Ground Tools (Python)

```bash
# Real-time event monitoring via CCSDS socket
python socket_event_decoder.py <IP> <PORT> <APP_ID> <assembly_events.py> <log_file>

# Post-mortem event decode
python decode_event_packets.py <assembly_events.py> <binary_dump.bin>

# CCSDS packet analysis
python fast_ccsds_checker.py <binary_file> [--apids 1 2 3]
```

## Development Monitoring (no COSMOS needed)

```bash
# Run assembly, capture events
docker exec adamant bash -c "timeout 10 ./main.elf 2>&1"

# Separate stderr for event capture
./main.elf 2>events.log &
tail -f events.log
```

**CRITICAL**: Ccsds_Socket_Interface is a TCP CLIENT. Without a server (COSMOS/socat), ground Python tools can't receive CCSDS telemetry. Event_Text_Logger stderr output always works.
