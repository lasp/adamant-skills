# Common Test Errors — Detailed Reference

Summaries are in SKILL.md. This file has extended explanations for tricky cases.

## Async-Specific Patterns

### Named send connector histories
A send connector named `Primary_Packet_T_Send` becomes `Primary_Packet_T_Recv_Sync_History` in the tester.

### Named Event.T send connectors crash on non-component events
Tester's `Dispatch_Event` calls `Local_Event_Id_Type'Val(Evnt.Header.Id)` — crashes on external event IDs. Fix: edit tester `.adb` to remove `Dispatch_Event` from named Event.T output handlers, keep only the history push.

### Dual Command.T connectors (async+sync)
Tester generates `Command_T_Send` (async) and `Command_T_Send_2` (sync). Use `_Send_2` for component's own commands.

### Event param types must be static-sized
Variable-length types (Command.T, Packet.T) cannot be event parameters. Use packed types.

### Change detection initial values
If shadows default to same value as first computation, NO DP is sent on first tick.

### No dynamic allocation
Ravenscar profile: use fixed-size arrays, NOT `access` types or `new`.
