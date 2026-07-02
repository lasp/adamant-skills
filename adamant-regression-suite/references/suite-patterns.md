# Regression suite patterns (copy-ready)

Generic, placeholder-named snippets for the recurring shapes in an Adamant COSMOS regression suite.
Replace `<TARGET>`, `<Component_Instance>`, `<Packet>`, `<Status_Packet>`, `<Command_Name>`,
`<assembly>`, `<Seq_Count_Item>` (the packet's sequence-count item -- the name comes from the
generated dictionary and is naming-layer-dependent), and helper names with the project's actual
values (read from the generated dictionary and the project `lib/`). For the full COSMOS script API
see `adamant-cosmos-testing`.

## Helper library + imports

Procedures import the project's shared helpers and the generated modules. Projects resolve the
installed plugin's `lib/` onto `sys.path` with a small boilerplate; reuse the project's existing
form rather than inventing one:

```python
import sys, os, glob
# resolve the newest installed plugin lib dir (project-specific glob)
_libs = glob.glob("/gems/gems/<plugin-prefix>-*")
if _libs:
    sys.path.append(os.path.join(max(_libs, key=os.path.getmtime), "targets/<TARGET>/lib"))

from openc3.script import *
from openc3.script.suite import Group, Suite
from <assembly>_events import <Component_Instance>_<Event_Name>          # numeric event id
from <project_lib> import wait_check_sim_time, send_and_verify_command   # project helpers -- use the
                                                                          # project's actual names from lib/
```

## Suite + Group skeleton

```python
class <Feature>Tests(Group):
    def setup(self):
        self._initial = tlm("<TARGET> <Status_Packet> <Command_Router_Instance>-Command_Success_Count-Value")

    def teardown(self):
        # restore any global FSW state this group changed
        cmd("<TARGET>", "<Component_Instance>-Set_Safe_Defaults")

    def _ensure_ready(self):
        # idempotent: works on a cold start AND a warm re-run
        ...

    def test_<behavior>(self):   # discovered + run alphabetically
        ...

class TestSuite(Suite):
    def __init__(self):
        super().__init__()
        self.add_group(<Feature>Tests)   # add order = run order

    def setup(self):     ...   # once before all groups
    def teardown(self):  ...   # once after all groups
```

## Command-and-verify (baseline -> command -> delta)

```python
def test_command_accepted(self):
    before = tlm("<TARGET> <Status_Packet> <Command_Router_Instance>-Command_Success_Count-Value")
    cmd("<TARGET>", "<Component_Instance>-<Command_Name>", {"<PARAM>": value})
    wait_check_expression(
        f"tlm('<TARGET> <Status_Packet> <Command_Router_Instance>-Command_Success_Count-Value') == {before}+1", 10)

def test_command_rejected(self):
    before = tlm("<TARGET> <Status_Packet> <Command_Router_Instance>-Command_Failure_Count-Value")
    cmd_no_range_check("<TARGET>", "<Component_Instance>-<Command_Name>", {"<PARAM>": out_of_range})
    wait_check_expression(
        f"tlm('<TARGET> <Status_Packet> <Command_Router_Instance>-Command_Failure_Count-Value') == {before}+1", 10)
```
Baseline every free-running counter and check the delta -- never an absolute value (counters do not
start at zero on a warm re-run).

## Simulation time vs wall-clock

If the FSW advances in simulation time, use the project's sim-time helpers (built from a housekeeping
packet's sequence count) instead of wall-clock `wait`:

```python
# project helper, e.g. wait_check_sim_time(check_str, timeout_sim_seconds)
wait_check_sim_time("<TARGET> <Packet> <Component_Instance>-<Data_Product>-<Field> == 'EXPECTED'", 20)
```
Reserve real `time.time()` / `wait(seconds)` for genuine wall-clock bounds (e.g. liveness timeouts).

## Telemetry, rates, and first contact

```python
def test_01_alive(self):
    wait_packet("<TARGET>", "<Status_Packet>", 1, 10)        # block for first packet before checking
    check("<TARGET> <Status_Packet> RECEIVED_COUNT > 0")     # RECEIVED_COUNT is COSMOS-derived (every packet)

def test_packet_updating(self):
    # <Seq_Count_Item> comes from the generated dictionary (framework default: Sequence_Count;
    # naming layers may differ, e.g. Primary_Header_sequence_count)
    s1 = tlm("<TARGET> <Packet> <Seq_Count_Item>", type="RAW")
    wait(2)
    s2 = tlm("<TARGET> <Packet> <Seq_Count_Item>", type="RAW")
    if (s2 - s1) % 16384 <= 0:                                # wrap-safe 14-bit delta
        raise CheckError("<Packet> not advancing")
```

## Event capture and decode

```python
def test_event_emitted(self):
    sub = subscribe_packets([["<TARGET>", "<Event_Packetizer_Instance>-Events_Packet"]])
    cmd("<TARGET>", "<Component_Instance>-<Command_Name>")
    wait(2)
    sub, packets = get_packets(sub)
    # decode with project/event helper that maps buffers -> event ids (generated typed classes)
    ids = decode_event_ids([p["BUFFER"] for p in packets])
    expected_id = <Component_Instance>_<Event_Name>   # bind the module-level import to a local --
    check_expression("expected_id in ids", locals())  # locals() cannot see module-level names
```

## Telemetry buffer dump + deserialize

```python
def test_dump_roundtrip(self):
    send_and_verify_command("<Component_Instance>-Dump_<Thing>")
    buf = get_tlm_buffer("<TARGET> <Packet>")["buffer"]
    obj = <Type>()                       # generated packed-type class
    obj._from_byte_array(bitstring.ConstBitStream(buf[HEADER_LENGTH:]))
    check_expression("obj.<Field> == expected", locals())
```

## Parameter-table round-trip

```python
def test_parameter_table(self):
    record = <Table_Record>( ... )                    # generated packed-type class
    send_param_table("<Parameters_Instance>", record)            # project helper (serialize+CRC+send+verify)
    verify_dumped_table("<Parameters_Instance>", <Table_Record>(), record)
```

## Negative / stability assertion

COSMOS has no built-in "assert unchanged". Poll for stability, and always pair it with a positive
control so a never-active value cannot pass by accident:

```python
def _assert_stable(self, item, duration_s=3, poll_s=0.5):
    base = tlm(item); t = 0
    while t < duration_s:
        wait(poll_s); t += poll_s
        if tlm(item) != base:
            raise CheckError(f"{item} changed from {base}")

# pattern: verify it IS changing -> disable -> assert stable -> re-enable -> verify it resumes
```

## Assertion discipline + state hygiene

- Every assertion goes through `check`, `check_expression`, `wait_check`, or `wait_check_expression`
  -- never a bare `assert`. Check failures report with formatted context (expected vs. actual
  telemetry) and behave correctly in disconnect mode; a bare assert fails uninformatively.
- `check*` raises on failure (immediate); `wait_check*` polls then raises on timeout; `wait*` never
  raises (the expression/tolerance/packet forms return a success bool; the plain time form returns
  elapsed time). Pick the one matching the test's intent.
- Restore disturbed global state in `teardown()`; keep setup helpers idempotent.
- Order tests numerically (`test_01_*`) when later tests depend on earlier state, since discovery is
  alphabetical.
