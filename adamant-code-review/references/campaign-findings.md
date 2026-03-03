# Campaign Review Findings

Concrete issues found during cold-start skill validation campaigns.
Each entry includes the iteration where it was first observed and the resolution.

## Component Issues

### recv_sync tick on active component (T13-S2-i5)
- **Severity:** warning
- **Pattern:** Active component declares `recv_sync Tick.T` instead of `recv_async`
- **Impact:** Tick handler runs in the rate group's task context, not the component's own task. Functional, but defeats the purpose of the active execution model for tick-driven work.
- **Resolution:** Use `recv_async Tick.T` for active components that do non-trivial work on tick.

### data_product.ads buffer size mismatch (T13-S1-i1)
- **Severity:** error (build failure)
- **Pattern:** Framework's generated `data_product.ads` uses default 36-byte buffer, but project configures 192 bytes in `config/demo.configuration.yaml`.
- **Impact:** Components with data products larger than 36 bytes fail to compile.
- **Resolution:** Run `redo clean_all` to regenerate framework types with project config. Sub-agent patched the generated file directly -- fragile workaround.

### Ada reserved word in command names (T13-S2, multiple iterations)
- **Severity:** error (compilation failure)
- **Pattern:** Using `Abort` as a command name. Ada reserved word.
- **Impact:** GNAT rejects the generated Ada code.
- **Resolution:** Rename to `Abort_Sequence`, `Cancel_Sequence`, `Seq_Abort`, etc. Skills document this but agents still trip on it occasionally.

## Test Issues

### Typed history accumulation across tests (T12, recurring)
- **Severity:** error (assertion failure)
- **Pattern:** Agent writes `T.Event_T_Recv_Sync_History.Count = 1` in test 3, but events from tests 1 and 2 are still in the typed history.
- **Impact:** Assertion fails with unexpected count.
- **Resolution:** Use cumulative counts, or clear histories between tests. Skills document this pattern.

### Shallow assertions (T12, early rounds)
- **Severity:** warning
- **Pattern:** Tests only check `History.Count` without verifying the actual values in history entries.
- **Impact:** Tests pass even when output values are wrong.
- **Resolution:** Compare packed type fields directly: `T.Event_T_Recv_Sync_History.Get(N).Header.Id = Self.Tester.Events.Get_Some_Event_Id`

## Assembly Issues

### Flattened assembly when subassembly required (T13-S2-i4)
- **Severity:** warning (scope deviation)
- **Pattern:** Agent attempted subassembly, hit event_to_text code gen bug, abandoned subassembly and flattened.
- **Impact:** Task said "use a subassembly" -- agent deviated from requirement.
- **Resolution:** The event_to_text bug is cosmetic (affects style check on subassembly dir, not the ELF). Prior iterations used subassemblies successfully. Agent should push through the style warning.

### Queue_Size vs Priority_Queue_Depth confusion (T13-S2, multiple iterations)
- **Severity:** error (build failure)
- **Pattern:** Using `Queue_Size` init param when component has multiple `recv_async` with different priorities. Should be `Priority_Queue_Depth`.
- **Impact:** Wrong init parameter causes compilation error.
- **Resolution:** Check component YAML -- if multiple recv_async with different `priority` values, use `Priority_Queue_Depth`. Single recv_async or same priority uses `Queue_Size`.

### Fault response name mismatch (T13-S1-i2, T13-S2-i3)
- **Severity:** error (build failure)
- **Pattern:** Fault_responses.yaml references `Source_Persistent_Loss` but component declares `Source_Lost`. Or references `Empty_Sequence_Fault` but component declares `Empty_Sequence`.
- **Impact:** Assembly validation rejects unknown fault name.
- **Resolution:** Read the component's faults.yaml to get exact names. Don't guess suffixes.

### Tick connector kind mismatch (T13-S2, multiple iterations)
- **Severity:** error (build failure)
- **Pattern:** Assembly wires `Tick_T_Recv_Sync` but component declares `recv_async` (or vice versa).
- **Impact:** Connector kind mismatch causes assembly validation failure.
- **Resolution:** Read the component YAML `connectors:` section to determine the exact kind.

## Type Issues

### Packed type exceeds data product buffer (T13-S1-i1)
- **Severity:** error (build failure)
- **Pattern:** Data product type larger than project's configured `data_product_buffer_size`.
- **Impact:** Compilation error in generated data product package.
- **Resolution:** Check `config/*.configuration.yaml` for buffer size limit. Keep DP types within bounds.

## Efficiency Observations

### Build output noise (all iterations)
- **Pattern:** Sub-agents paste 40-80 lines of redo target announcements and recompilation warnings into their output.
- **Impact:** Wasted output tokens, no diagnostic value.
- **Resolution:** AGENTS.md build output filtering (added 2026-03-02). Use `sed + grep` filter to strip noise.

### Subassembly event_to_text (known framework limitation)
- **Pattern:** Every subassembly with events produces a broken `_event_to_text.adb`.
- **Impact:** Style check on subassembly dir shows errors. Parent assembly's event_to_text compiles fine. ELF unaffected.
- **Resolution:** Documented in adamant-subassemblies skill. Not a code defect -- framework limitation. Style exit code is still 0.
