# Skill Validation History

Tracking convergence of Adamant skills through cold-start validation exercises.

## Convergence Data (2026-02-10 through 2026-02-14)

### Component Development Skills
| Round | Date | Errors | Key Issues |
|-------|------|--------|------------|
| 1-13 | 02-10 to 02-11 | 20+ → 6 | Wrong signatures, missing overrides, name collisions |
| 14 | 02-12 | 6 | Validate_Parameters individual args, duplicate sends, framework name collisions |
| 15 | 02-12 | 1 | Update_Parameters_Action abstract |
| 16 | 02-12 | 2 | Packed_U8 nonexistent, Unsigned_32 naming |
| 17 | 02-12 | 3 | Connector confusion, missing Invalid_Command, wrong Execute_Command |
| 18 | 02-12 | 1 | Spurious Init on passive without init params |
| 19 | 02-12 | **0** | First clean compilation from cold-start agent |

### Assembly Development Skills
| Round | Date | Errors | Key Issues |
|-------|------|--------|------------|
| 1 (mini-assembly) | 02-12 | 6 | Sys_Time wiring, event routing, arrayed indices |
| 2 (test_assembly) | 02-14 | 0 | Clean build from cold-start agent |

### Type System Skills
| Round | Date | Errors | Key Issues |
|-------|------|--------|------------|
| 1 | 02-12 | 3 | Minor gaps |
| 2 (comm_status) | 02-14 | 0 | Clean build + 2/2 tests pass |

### Testing Skills
| Round | Date | Errors | Key Issues |
|-------|------|--------|------------|
| 1 | 02-12 | 0 | 5/5 tests, 100% coverage on first compile |

### COSMOS Integration Skills
| Round | Date | Errors | Key Issues |
|-------|------|--------|------------|
| 1 | 02-12 | 2 | Wrong DP names, wrong package name |

## Persistent Sub-Agent Error Patterns

These errors recur across multiple sub-agents despite skill documentation:

1. **`type:` instead of `return_type:` on get connectors** (100% miss rate)
2. **Missing Send_Dropped overrides** (~80% miss rate)
3. **Missing `with Tick;` / `with Command;` in test bodies** (~70% miss rate)
4. **Trailing whitespace in generated code** (~60% miss rate)
5. **Typed history accumulation** (clear raw but forget typed histories)

### Mitigation
- Bold/caps warnings in SKILL.md for #1 and #2
- Explicit checklist items for #3
- Style skill alignment for #4
- Dedicated section with example for #5

## Validation Task Templates

### Passive Component (basic)
"Create a passive component named `<name>` with: recv_sync for Tick.T,
send for Event.T and Data_Product.T, get for Sys_Time.T. Define 2 data
products and 2 events. Write 3 test cases. Target: 0 compile errors."

### Active Component (complex)
"Create an active component named `<name>` with: recv_async for Command.T
and Packet.T, send for Event.T/Data_Product.T/Command_Response.T/Fault.T,
get for Sys_Time.T. Add parameters, faults, and commands. Write 5 test
cases including parameter management and fault triggering."

### Assembly
"Create a minimal assembly with 3 components, a rate group at 5Hz, command
routing, and event forwarding. Include a main procedure that initializes
and starts the system."

### Custom Type + Component
"Define a packed record type with at least 5 fields including sub-byte
fields. Create a component that uses this type in data products and events.
Write tests that verify packing/unpacking round-trips."
