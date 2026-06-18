---
name: adamant-regression-suite
description: Build black-box Python regression test suites for a running Adamant assembly through its COSMOS command/telemetry interface, without reading flight-software source. Use when creating or extending a regression suite, deriving a test surface from the command/telemetry contract, enforcing source-blind testing, or wiring a suite into a simulation run harness.
---

# Adamant Regression Suite

Build Python regression suites that exercise a running Adamant assembly through its COSMOS
command/telemetry interface and verify the telemetry it returns. A regression suite is a
**black-box oracle**: it knows the interface contract, never the implementation.

## The black-box rule (non-negotiable)

**Do not read flight-software implementation source: `.ads`, `.adb`, `.cpp`, `.c`, `.h`.**
Author every test from the *interface contract* only:
- all `.yaml`/`.yml` model files (commands, events, data products, packets, parameters, faults,
  assembly, configuration) -- ALLOWED and expected;
- the generated COSMOS command/telemetry dictionary;
- the generated ground-side Python (numeric IDs and packed-type classes).

**Why:** a test written by reading the implementation encodes what the code *does*, not what the
interface *promises* -- it passes for the wrong reasons and stops catching regressions the moment
the implementation drifts. Working from the contract keeps the oracle independent of the code it checks.

**Enforce it; do not just trust it.** A skimming author reads source by reflex. Wire the deny rules
and the pre-tool hook from [references/enforcement.md](references/enforcement.md) +
[scripts/block_source.py](scripts/block_source.py) into the project before authoring. A Read-deny
rule alone is leaky -- a shell `cat` bypasses it -- and the hook closes that gap.

## Quick start (the loop)

1. **Read the contract** (order below) -- never the source.
2. **Survey the existing suite** -- match its groups, naming, helpers, and coverage; extend it, do
   not reinvent it (see "Survey the existing suite first").
3. **Author** a procedure in the project's ground/COSMOS tree (`gnd/cosmos/<TARGET>/procedures/`),
   reusing the project's helper library (`gnd/cosmos/<TARGET>/lib/`).
4. **Rebuild** so the generated IDs/dictionary are current (the project's standard Adamant build).
5. **Run** through the project's simulation harness and gate on exit code:
   ```bash
   <harness> test                                          # whole suite
   <harness> test <TARGET>/procedures/<new_suite>.py       # one script (fast inner loop)
   <harness> test <TARGET>/procedures/<new_suite>.py <SuiteClass>
   ```

## The interface contract (what you read instead of source)

Everything is generated from the flight-software build and is plain `.yaml`/`.py`:

```
Adamant YAML models (per component: *.commands.yaml / *.events.yaml / *.data_products.yaml /
  *.packets.yaml / *.parameters.yaml / *.faults.yaml; plus *.assembly.yaml + *.configuration.yaml)
   |  build
   +--> generated ground-side Python: <assembly>_commands.py, _events.py, _data_products.py,
   |       _packets.py, _parameters.py, _faults.py (numeric IDs + name<->id lookups), and
   |       <type>.py packed-type classes for (de)serialization
   +--> generated COSMOS cmd/tlm dictionary (the cmd/tlm names tests reference)
```

**Read order for one procedure:**
1. the generated COSMOS cmd/tlm dictionary -- exact command/telemetry names and parameters;
2. the component's `.yaml` models -- descriptions, ranges, enum states;
3. the generated `<assembly>_*.py` -- numeric IDs and the packed-type classes you need;
4. the project's helper library (`lib/`) -- timing and command-and-verify primitives;
5. the `*.configuration.yaml` -- buffer sizes and similar constants (never hardcode these).

Naming transform, CCSDS framing, and the command-response contract in depth:
[references/contract-derivation.md](references/contract-derivation.md).

### Names
- Command: `<Component_Instance>-<Command_Name>` under a COSMOS `<TARGET>`.
- Telemetry item: a dotted/dashed path under a packet, e.g. `<Component_Instance>-<Data_Product>-<Field>`.
- Use the **exact** names from the generated dictionary. Never abbreviate, guess, or **invent** a
  name, ID, range, or enum value -- every one traces to a contract artifact above. If you cannot
  point to where a value comes from, do not write it. `Safe_Mode_Thermal_Packet` is not `Safe_Thermal_Packet`.

### Standing Adamant contracts (true for every project)
- **Command response:** every command yields exactly one command response, and the command router
  keeps success/failure counts. Verify acceptance by a success-count delta (or last-command id);
  verify rejection by a failure-count delta. `Command_Response_Status`: `Success=0, Failure=1,
  Id_Error=2, Validation_Error=3, Length_Error=4, Dropped=5`.
- **CCSDS framing:** packets carry a CCSDS primary header, a secondary header (command function
  code/checksum; telemetry time code), and a CRC trailer -- all defined in YAML, never in source.

## Where the suite lives

- **Author** in the flight-software project's ground/COSMOS tree: procedures in
  `gnd/cosmos/<TARGET>/procedures/`, hand-maintained helpers in `gnd/cosmos/<TARGET>/lib/`. These are
  version-controlled source.
- **Generated dependencies** (`<assembly>_*.py`, packed-type classes) are build output, merged into
  the packaged plugin at build time. **Read them; never edit them** -- edits are lost on rebuild.
- **Rebuild** after any model change so IDs and the dictionary are current. Confirm with the
  project's VCS which files are tracked before deciding where a new file goes -- the packaged/built
  plugin is not the suite's home.

## Survey the existing suite first

Before adding tests, read the project's existing procedures and helpers under
`gnd/cosmos/<TARGET>/{procedures,lib}/` and conform to them -- faster, and it keeps the suite coherent:
- **Style and structure** -- how Groups are organized, how `setup`/`teardown` and helpers are used, naming conventions.
- **Helper API** -- the timing and command-and-verify helpers already provided; reuse them, never duplicate them.
- **Coverage** -- which commands, telemetry, modes, parameters, and faults are already exercised, so you
  extend coverage into the gaps instead of repeating what exists or leaving holes.

Match the existing conventions and extend the suite. A new procedure that diverges in style or
re-implements existing helpers is slower to review and harder to maintain. Applies to any project
that already has a suite.

## Suite structure (OpenC3)

```python
from openc3.script import *
from openc3.script.suite import Group, Suite

class <Feature>Tests(Group):
    def setup(self):     ...   # before each test in the group
    def teardown(self):  ...   # after the group (restore any global state you disturbed)
    def _helper(self):   ...   # underscore = helper, NOT discovered as a test
    def test_<behavior>(self): ...   # test_* auto-discovered, run ALPHABETICALLY

class TestSuite(Suite):
    def __init__(self):
        super().__init__()
        self.add_group(<Feature>Tests)   # add_group order = run order
    def setup(self):    ...   # once before all groups
    def teardown(self): ...   # once after all groups
```
- `test_*` methods run **alphabetically** within a group -- number them (`test_01_*`) when sequence matters.
- Route assertions through the check/wait-check API (below), never a bare Python `assert`, so
  failures land in the suite report.

## Standard regression patterns

Copy-ready snippets in [references/suite-patterns.md](references/suite-patterns.md). The essentials:

**Command-and-verify (baseline, command, check delta):**
```python
before = tlm("<TARGET> <Status_Packet> <Command_Router_Instance>-Command_Success_Count-Value")
cmd("<TARGET>", "<Component_Instance>-<Command_Name>", {"<PARAM>": value})
wait_check_expression(
    f"tlm('<TARGET> <Status_Packet> <Command_Router_Instance>-Command_Success_Count-Value') == {before}+1", 10)
```
Always baseline a free-running counter and check the delta -- never an absolute value.

**Simulation time vs wall-clock:** if the FSW runs in simulation time, use the project's sim-time
wait helpers (derived from a housekeeping packet's sequence count), not wall-clock `wait`. Reserve
real time for true wall-clock bounds. Find the helpers in the project's `lib/`.

**Telemetry / events / parameter tables:** wait for a value or a packet; capture event packets with
`subscribe_packets` -> `get_packets` and decode with the generated typed event classes; round-trip a
parameter table (send, then dump-and-compare with the generated packed-type class).

**State hygiene:** restore any global FSW state in `teardown()`; make setup helpers idempotent so a
group works on a cold start and a warm re-run.

## Running the suite

The project provides a simulation/run harness (softsim-style) that brings up the FSW, the simulator,
and COSMOS, runs the suite via the COSMOS script runner, and **exits non-zero on any failure** (the
regression gate):
```bash
<harness> start
<harness> test [<TARGET>/procedures/<script>.py] [<SuiteClass>]
```
The optional script/suite arguments run a single target -- the fast loop while developing one
procedure. Underneath, this is `openc3cli script run <script> --suite <Suite> --method start`.
For programmatic launch + log retrieval, see `adamant-cosmos-minio`; for the full script API, see
`adamant-cosmos-testing`.

## Checklist

1. Wire enforcement (deny rules + hook) into the project -- see enforcement.md.
2. Read the contract in order; identify the exact command/telemetry names for the feature.
3. Survey the existing suite; reuse its helpers and conventions; target behavior not already covered.
4. Create/extend a Group in `gnd/cosmos/<TARGET>/procedures/`; add it to the Suite in run order.
5. Write `test_*` methods: baseline -> command -> check delta; verify via the command-response
   contract; assert through the check API.
6. Reuse the project's `lib/` helpers (sim-time waits, command-and-verify); do not reinvent them.
7. Rebuild to refresh generated deps.
8. Run the single target via the harness; iterate until green; then run the full suite.

## Common errors

- **Reading source.** Any `.ads/.adb/.cpp/.c/.h` read is a process violation (and is blocked when
  the hook is wired). Re-derive the fact from YAML / the generated dictionary / generated Python.
- **Guessed or abbreviated names.** Use exact names from the generated dictionary.
- **Hardcoded constants.** Buffer sizes etc. come from `*.configuration.yaml`; derive, don't hardcode.
- **Wall-clock where sim-time is needed.** Use the project's sim-time helpers for FSW-rate checks.
- **Stale generated deps.** Rebuild after model changes; an old `<assembly>_*.py` has wrong IDs.
- **Editing build artifacts.** Author in the version-controlled `gnd/cosmos/...` source, not the gem.
- **Bare `assert`.** Route through `check`/`wait_check*` so failures are reported.
- **Absolute counter checks.** Counters free-run; always baseline and check the delta.

## References
| File | Read when |
|------|-----------|
| [references/contract-derivation.md](references/contract-derivation.md) | Deriving names/IDs/CCSDS/command-response from the contract; the naming transform in depth. |
| [references/enforcement.md](references/enforcement.md) | Wiring the black-box deny rules + pre-tool hook into a project. |
| [references/suite-patterns.md](references/suite-patterns.md) | Copy-ready Group/Suite, command-and-verify, event-capture, parameter-table, and state-hygiene snippets. |
| [scripts/block_source.py](scripts/block_source.py) | The reference pre-tool hook that blocks source reads via Read/Edit/Write/Grep/Bash. |

## Related skills
- `adamant-cosmos-testing` -- the COSMOS script API (cmd/tlm/wait-check) and suite/group mechanics.
- `adamant-cosmos-minio` -- launching a suite programmatically and parsing its result log.
- `adamant-component-dev` -- the YAML models (commands/events/data products/parameters) you read as the contract.
