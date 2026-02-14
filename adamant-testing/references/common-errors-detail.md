# Common Test Errors — Detailed Reference

## 1. Wrong Stimulus API
Use `T.Tick_T_Send(...)` NOT `T.Tick_T_Recv_Sync(...)`. The tester SENDS to the component under test. `_Recv_Sync` is what the tester receives FROM the component (event/DP/fault capture).

## 2. History `.Value` accessor
`T.Pet_Count_History.Get(N)` returns `Packed_U32.T` directly. Compare with `Packed_U32_Assert.Eq(T.Pet_Count_History.Get(1), (Value => 42))`. Do NOT write `.Get(1).Value` then compare to a packed record -- type mismatch.

## 3. Tick.T.Count is Unsigned_32
When using loop variable casts, use `Interfaces.Unsigned_32(I)` not `Unsigned_16`. Add `with Interfaces;` to the test body if needed.

## 4. Missing imports in test body
Test bodies need explicit `with` for packages used: `with Interfaces;`, `with Basic_Assertions; use Basic_Assertions;`, typed assertion packages like `with Packed_U32.Assertion; use Packed_U32.Assertion;`.

## 5. Tester files MUST come from build/template/
Run `redo templates` from the test/ directory. This generates ALL tester files in `build/template/`: tester `.ads`, tester `.adb`, `test.adb`, and test implementation stubs. Copy ALL of them to `test/` at initial setup. Do NOT hand-write tester files -- they have complex history packages, overrides, and Init_Base/Final_Base that must match the generated reciprocal component exactly.

## 6. History name convention
Typed histories use the event/DP name + `_History`. NOT `_Event_History` or `_Data_Product_History`. Example: event `Telemetry_Enabled` -> `T.Telemetry_Enabled_History`.

## 7. Command response status type
In command response assertions, use `Command_Enums.Command_Response_Status.Success/Failure`, NOT `Command_Execution_Status`. The response record's Status field is `Command_Response_Status.E`.

## 8. Init params go to Component_Instance.Init, NOT Init_Base
`Self.Tester.Init_Base` takes NO component params (only Queue_Size for active). Component init params go to `Self.Tester.Component_Instance.Init(Param => Value)`. Order: Init_Base -> Connect -> Component_Instance.Init -> Set_Up.

## 9. Typed histories don't auto-clear (MOST COMMON)
Clearing `T.Data_Product_T_Recv_Sync_History` does NOT clear individual typed histories like `T.Counter_History`. Use CUMULATIVE counts or clear typed histories explicitly: `T.My_Event_History.Clear;`

## 10. Change detection initial state
Components using change detection fire a DP update on the FIRST tick because initial shadow value (typically 0) differs from computed value. Account for this extra DP in history counts.

## 11. `use type` for operator visibility
When using `pragma Assert` or direct `=` comparisons on enumeration types, you need `use type Command_Enums.Command_Response_Status.E;`. Without it, `=` is not directly visible.

## 12. History overflow ("History is full")
Default depth is 100. Each tick sending 2 DPs consumes 2 slots. 50+ ticks risks overflow. Solutions: clear histories mid-test, reduce stimulus, test milestones with fewer iterations.

## 13. Packet.T Header has NO Priority field
Fields: Time, Id, Sequence_Count, Buffer_Length. Do NOT access `.Header.Priority`.

## Async-Specific Errors

### Dispatch_All is a FUNCTION
Returns Natural. Must capture: `Count := T.Dispatch_All;` (use `pragma Unreferenced (Count);` if unused).

### Named send connector histories
A send connector named `Primary_Packet_T_Send` becomes `Primary_Packet_T_Recv_Sync_History` in the tester.

### Named Event.T send connectors crash on non-component events
Tester's `Dispatch_Event` calls `Local_Event_Id_Type'Val(Evnt.Header.Id)` — crashes on external event IDs. Use Packet.T for forwarding instead.

### Instance record field name conflicts
Names like `Queue` conflict with generated base class. Use prefixed names like `Cmd_Buffer`.

### No dynamic allocation
Ravenscar profile: use fixed-size arrays, NOT `access` types or `new`.

### Change detection initial values
If shadows default to same value as first computation, NO DP is sent on first tick.

### Event param types must be static-sized
Variable-length types (Command.T, Packet.T) cannot be event parameters. Use packed types.

### Dual Command.T connectors (async+sync)
Tester generates `Command_T_Send` (async) and `Command_T_Send_2` (sync). Use `_Send_2` for component's own commands.
