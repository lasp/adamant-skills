# adamant-cosmos-testing

Integration-level test scripts that verify Adamant assembly behavior through COSMOS ground interface.

## When to Use

Use when writing COSMOS test scripts (Ruby or Python) that exercise a running Adamant assembly via its CCSDS ground interface. Covers command acceptance, telemetry verification, mode transitions, fault injection, parameter updates, rate verification, and end-to-end data flow testing.

**Prerequisites:** Assembly running (hardware or Linux ELF), COSMOS plugin deployed with correct cmd/tlm definitions, CCSDS link established.

## MANDATORY First Step: Read the Interface Spec (cmd.txt / tlm.txt)

**Treat the FSW as a black box.** You test through the command and telemetry
interface, just like a real integration tester. You do NOT need to read
component source code or implementation details.

**Before writing ANY test code**, read the deployed plugin's cmd.txt and tlm.txt:

```
1. Read cmd.txt -> extract all COMMAND lines -> these are your available commands
   Format: COMMAND TARGET Instance_Name-Command_Name ...
   Parameters listed below each command with types and ranges

2. Read tlm.txt -> extract all TELEMETRY lines -> these are your packet names
   Format: TELEMETRY TARGET Packet_Name ...
   Items listed below each packet with names, sizes, types

3. Write tests using ONLY the names from these files
```

**If `redo agent-cmd-tlm` is available** (agent-oriented redo target), use it
instead -- it produces a compact summary optimized for agent consumption.

**Secondary sources (only when needed):**
- Assembly YAML: when test requires understanding component relationships or wiring
- `references/model-based-test-derivation.md`: when cmd.txt/tlm.txt are unavailable
  and you need to derive names from YAML models

**NEVER assume or shorten names.** Use the EXACT names from cmd.txt/tlm.txt.
`Safe_Mode_Thermal_Packet` is NOT `Safe_Thermal_Packet`.

## Real Assembly Conventions

Examples in this skill use generic short names for clarity. Real Adamant COSMOS plugins differ:

- **Target name:** Use the actual target from plugin.txt (e.g., `STATION_ASSEMBLY`), not `ASSEMBLY`
- **Command names:** Adamant COSMOS commands use `Component_Instance-Command_Name` format (hyphen-separated), e.g., `cmd("STATION_ASSEMBLY Heater_Controller_Instance-Force_Heater_On")`
- **Telemetry item names:** Use dotted paths: `Component_Instance.Data_Product_Name.Field.Value`, e.g., `tlm("STATION_ASSEMBLY System_Status_Packet Command_Router_Instance.Command_Success_Count.Value")`
- **Command_Response:** May not be a separate CCSDS packet. Some assemblies embed response status in the System_Status_Packet (e.g., `Last_Failed_Command.Status`). Check your tlm.txt.
- **Mode commands:** May be individual commands (`Enter_Safe_Mode`, `Enter_Science_Mode`) rather than a parameterized `SET_MODE`. Check cmd.txt for actual command names.
- **Parameter updates:** The 3-step Stage/Validate/Update is one pattern. Many assemblies use direct Set commands (e.g., `Set_Thresholds with Value <packed_u32>`). Check your assembly's command definitions.
- **Fault injection:** Most assemblies do NOT have `INJECT_FAULT` test commands. Alternative patterns: override data products to fault-triggering values, use force commands (Force_Heater_Off), or manipulate system state through normal commands.
- **Packed parameters:** Commands may pack multiple values into a single integer (e.g., two U16 thresholds packed into one U32 Value field). Check the command's arg_type in cmd.txt.

## Scripting API Quick Reference

### Commands

```python
cmd("TARGET CMD_NAME with PARAM1 val1, PARAM2 val2")  # Converted, range+hazardous checked
cmd_raw("TARGET CMD_NAME with PARAM1 val1")            # No conversions
cmd_no_range_check("TARGET CMD_NAME with PARAM1 val1") # Skip range validation
cmd_no_hazardous_check("TARGET CMD_NAME")              # Skip hazardous prompt
cmd_no_checks("TARGET CMD_NAME with PARAM1 val1")      # No range check, apply conversions
cmd_raw_no_checks("TARGET CMD_NAME with PARAM1 val1")  # No range check, no conversions
```

Positional syntax also works: `cmd("TARGET", "CMD_NAME", {"PARAM1": val1})`.

### Telemetry

```python
tlm("TARGET PACKET ITEM")                     # Converted value
tlm("TARGET PACKET ITEM", type="RAW")         # Raw value
set_tlm("TARGET PACKET ITEM = value")          # Set (volatile, next packet overwrites)
override_tlm("TARGET", "PACKET", "ITEM", val)  # Override (persistent, survives packets)
normalize_tlm("TARGET", "PACKET", "ITEM")      # Clear override
inject_tlm("TARGET", "PACKET", {"ITEM": val})  # Inject complete packet
```

### Check (immediate, raises CheckError on failure)

```python
check("TARGET PACKET ITEM > 100")
check_tolerance("TARGET PACKET ITEM", expected, tolerance)
check_expression("tlm('TARGET PACKET ITEM') > 0 and tlm('TARGET PACKET OTHER') < 100")
```

### Wait (returns True/False, does NOT raise)

```python
wait(5)                                              # Sleep 5 seconds
success = wait("TARGET PACKET ITEM > 0", timeout=10)
success = wait_tolerance("TARGET PACKET ITEM", expected, tolerance, timeout)
success = wait_expression("tlm('T P I') > 0", timeout=10, polling_rate=0.25)
success = wait_packet("TARGET", "PACKET", num_packets, timeout)
```

### Wait + Check (raises CheckError on timeout)

```python
elapsed = wait_check("TARGET PACKET ITEM > 0", 10)
elapsed = wait_check_tolerance("TARGET PACKET ITEM", expected, tolerance, timeout)
elapsed = wait_check_expression("some_expression", timeout, polling_rate=0.25)
elapsed = wait_check_packet("TARGET", "PACKET", num_packets, timeout)
```

**Pattern summary:**

| Pattern | On success | On timeout |
|---------|-----------|-----------|
| `check*` | Print success | Raise CheckError |
| `wait*` | Return True | Return False (warn) |
| `wait_check*` | Return elapsed time | Raise CheckError |

Default polling rate: 0.25s. All patterns accept optional `type="RAW"` for raw values.

### Limits

```python
enable_limits("TARGET", "PACKET", "ITEM")
disable_limits("TARGET", "PACKET", "ITEM")
set_limits("TARGET", "PACKET", "ITEM", red_low, yellow_low, yellow_high, red_high)
enable_limits_group("GROUP_NAME")
set_limits_set("SET_NAME")  # Switch between DEFAULT, TVAC, etc.
```

### Exceptions

```python
CheckError          # check/wait_check failure
StopScriptError     # Stop entire suite
SkipScriptError     # Mark test SKIP, continue suite
```

## Suite Organization

### Python (recommended for Adamant -- tooling is Python-based)

```python
from openc3.script import Suite, Group, cmd, tlm, wait, wait_check, wait_check_expression, \
    wait_check_packet, check, check_expression, check_tolerance, override_tlm, normalize_tlm, \
    set_limits, enable_limits, disable_limits, cmd_no_range_check, get_out_of_limits
from openc3.script import CheckError, SkipScriptError

class CommandTests(Group):
    def setup(self):
        """Runs before each group execution"""
        self.initial_cmd_count = tlm("ASSEMBLY HK CMD_RECV_COUNT")

    def teardown(self):
        """Runs after each group execution"""
        cmd("ASSEMBLY SET_MODE with MODE SAFE")
        wait(2)

    def test_noop_accepted(self):
        cmd("ASSEMBLY NOOP")
        wait_check("ASSEMBLY CMD_RESPONSE STATUS == 'SUCCESS'", 5)
        wait_check_expression(
            f"tlm('ASSEMBLY HK CMD_RECV_COUNT') == {self.initial_cmd_count + 1}", 5)

    def test_invalid_command_rejected(self):
        cmd("ASSEMBLY BAD_CMD")  # Unknown command
        wait_check("ASSEMBLY CMD_RESPONSE STATUS == 'EXECUTION_ERROR'", 5)

class IntegrationSuite(Suite):
    def __init__(self):
        super().__init__()
        self.add_group(CommandTests)
        self.add_group(TelemetryTests)
        self.add_group(ModeTests)
```

### Method naming conventions
- `test_*` -- test methods (auto-discovered, run alphabetically)
- `script_*` -- operational scripts (also auto-discovered)
- `op_*` -- operational procedures (also auto-discovered)
- `setup` / `teardown` -- run before/after group or suite

### Suite Runner settings
```python
SuiteRunner.settings = {
    "Loop": False,                # Repeat suite continuously
    "Break Loop On Error": False, # Stop looping on first failure
    "Abort After Error": False,   # Stop suite on first failure
}
```

### ScriptResult values
Each test produces: `PASS`, `FAIL`, `SKIP`, or `STOP`.

## Test Categories for Adamant Assemblies

### 1. Command Acceptance

Every Adamant assembly has a Command_Router that dispatches commands and returns Command_Response data products. Test pattern:

```python
def test_command_accepted(self):
    initial = tlm("ASSEMBLY HK CMD_SUCCESS_COUNT")
    cmd("ASSEMBLY SOME_COMMAND with PARAM1 value1")
    wait_check("ASSEMBLY CMD_RESPONSE STATUS == 'SUCCESS'", 5)
    wait_check_expression(
        f"tlm('ASSEMBLY HK CMD_SUCCESS_COUNT') == {initial + 1}", 5)

def test_command_failure_counted(self):
    initial_fail = tlm("ASSEMBLY HK CMD_FAILURE_COUNT")
    # Send command that will fail validation
    cmd_no_range_check("ASSEMBLY SET_THRESHOLD with VALUE 99999")
    wait_check("ASSEMBLY CMD_RESPONSE STATUS == 'EXECUTION_ERROR'", 5)
    wait_check_expression(
        f"tlm('ASSEMBLY HK CMD_FAILURE_COUNT') == {initial_fail + 1}", 5)
```

### 2. Telemetry Verification

Verify packets arrive, sequence counts advance, and values are within limits.

```python
PACKETS = [
    "ASSEMBLY HK",
    "ASSEMBLY ADCS_HK",
    "ASSEMBLY THERMAL_HK",
]

def test_all_packets_updating(self):
    for pkt in self.PACKETS:
        seq1 = tlm(f"{pkt} CCSDS_SEQ_COUNT")
        wait(2)
        seq2 = tlm(f"{pkt} CCSDS_SEQ_COUNT")
        if seq2 <= seq1:
            raise CheckError(f"{pkt} not updating (seq {seq1} -> {seq2})")

def test_values_within_limits(self):
    check("ASSEMBLY THERMAL_HK BOARD_TEMP", "GREEN")
    check("ASSEMBLY POWER_HK BUS_VOLTAGE", "GREEN")
```

### 3. Mode Transitions

```python
def test_safe_to_nominal(self):
    cmd("ASSEMBLY SET_MODE with MODE SAFE")
    wait_check("ASSEMBLY HK OPERATING_MODE == 'SAFE'", 10)
    cmd("ASSEMBLY SET_MODE with MODE NOMINAL")
    wait_check("ASSEMBLY CMD_RESPONSE STATUS == 'SUCCESS'", 5)
    wait_check("ASSEMBLY HK OPERATING_MODE == 'NOMINAL'", 10)
    # Verify dependent subsystems activate
    wait_check("ASSEMBLY ADCS_HK CONTROLLER_STATE == 'ACTIVE'", 10)

def test_invalid_transition_rejected(self):
    cmd("ASSEMBLY SET_MODE with MODE SAFE")
    wait_check("ASSEMBLY HK OPERATING_MODE == 'SAFE'", 10)
    # DEPLOY requires NOMINAL first
    cmd("ASSEMBLY SET_MODE with MODE DEPLOY")
    wait_check("ASSEMBLY CMD_RESPONSE STATUS == 'EXECUTION_ERROR'", 5)
    check_expression("tlm('ASSEMBLY HK OPERATING_MODE') == 'SAFE'")
```

### 4. Fault Injection and Recovery

```python
def test_overtemp_triggers_safe_mode(self):
    cmd("ASSEMBLY SET_MODE with MODE NOMINAL")
    wait_check("ASSEMBLY HK OPERATING_MODE == 'NOMINAL'", 10)
    initial_faults = tlm("ASSEMBLY HK FAULT_COUNT")
    # Inject fault (assembly-specific test command)
    cmd("ASSEMBLY INJECT_FAULT with FAULT_ID OVER_TEMP, VALUE 120.0")
    wait_check_expression(
        f"tlm('ASSEMBLY HK FAULT_COUNT') > {initial_faults}", 10)
    # Assembly should autonomously transition to SAFE
    wait_check("ASSEMBLY HK OPERATING_MODE == 'SAFE'", 15)

def test_fault_clear(self):
    cmd("ASSEMBLY CLEAR_FAULT with FAULT_ID OVER_TEMP")
    wait_check("ASSEMBLY CMD_RESPONSE STATUS == 'SUCCESS'", 5)
```

### 5. End-to-End Data Flow

Command an action, verify data propagates through the processing chain to telemetry output.

```python
def test_sensor_read_to_telemetry(self):
    seq_before = tlm("ASSEMBLY ADCS_HK CCSDS_SEQ_COUNT")
    cmd("ASSEMBLY REQUEST_MAG_SAMPLE")
    wait_check("ASSEMBLY CMD_RESPONSE STATUS == 'SUCCESS'", 5)
    # Wait for new ADCS packet with updated data
    wait_check_expression(
        f"tlm('ASSEMBLY ADCS_HK CCSDS_SEQ_COUNT') > {seq_before}", 10)
    # Verify magnetic field magnitude is Earth-like (20-65 uT)
    mag_x = tlm("ASSEMBLY ADCS_HK MAG_X")
    mag_y = tlm("ASSEMBLY ADCS_HK MAG_Y")
    mag_z = tlm("ASSEMBLY ADCS_HK MAG_Z")
    magnitude = (mag_x**2 + mag_y**2 + mag_z**2) ** 0.5
    if not 20.0 <= magnitude <= 65.0:
        raise CheckError(f"Mag magnitude {magnitude} outside expected range")
```

### 6. Parameter Update Lifecycle

Adamant uses a 3-step parameter update: Stage -> Validate -> Update.

```python
def test_parameter_update_cycle(self):
    original = tlm("ASSEMBLY HK OVER_TEMP_THRESHOLD")
    new_value = 95.0
    # Stage
    cmd(f"ASSEMBLY STAGE_PARAMETER with TABLE_ID FAULT_THRESHOLDS, "
        f"ENTRY_ID OVER_TEMP_THRESHOLD, VALUE {new_value}")
    wait_check("ASSEMBLY CMD_RESPONSE STATUS == 'SUCCESS'", 5)
    # Validate
    cmd("ASSEMBLY VALIDATE_PARAMETERS with TABLE_ID FAULT_THRESHOLDS")
    wait_check("ASSEMBLY PARAM_STATUS VALIDATION_STATE == 'VALID'", 5)
    # Update (commit)
    cmd("ASSEMBLY UPDATE_PARAMETERS with TABLE_ID FAULT_THRESHOLDS")
    wait_check("ASSEMBLY CMD_RESPONSE STATUS == 'SUCCESS'", 5)
    # Verify new value in telemetry
    wait_check_expression(
        f"tlm('ASSEMBLY HK OVER_TEMP_THRESHOLD') == {new_value}", 10)

def test_invalid_parameter_rejected(self):
    cmd("ASSEMBLY STAGE_PARAMETER with TABLE_ID FAULT_THRESHOLDS, "
        "ENTRY_ID OVER_TEMP_THRESHOLD, VALUE 999.0")
    cmd("ASSEMBLY VALIDATE_PARAMETERS with TABLE_ID FAULT_THRESHOLDS")
    wait_check("ASSEMBLY PARAM_STATUS VALIDATION_STATE == 'INVALID'", 5)
```

### 7. Rate Verification

```python
EXPECTED_RATES = {
    "ASSEMBLY HK": 1.0,           # Hz
    "ASSEMBLY ADCS_HK": 10.0,
    "ASSEMBLY THERMAL_HK": 0.1,
}
RATE_TOLERANCE = 0.15  # 15%

def test_packet_rates(self):
    for pkt, expected_hz in self.EXPECTED_RATES.items():
        measure_sec = max(5.0, 3.0 / expected_hz)
        seq_start = tlm(f"{pkt} CCSDS_SEQ_COUNT")
        t_start = time.time()
        wait(measure_sec)
        seq_end = tlm(f"{pkt} CCSDS_SEQ_COUNT")
        elapsed = time.time() - t_start
        measured_hz = (seq_end - seq_start) / elapsed
        deviation = abs(measured_hz - expected_hz) / expected_hz
        if deviation > self.RATE_TOLERANCE:
            raise CheckError(
                f"{pkt}: expected {expected_hz} Hz, measured {measured_hz:.2f} Hz "
                f"({deviation*100:.1f}% deviation)")
```

### 8. Stress and Edge Cases

```python
def test_rapid_commanding(self):
    initial = tlm("ASSEMBLY HK CMD_SUCCESS_COUNT")
    for _ in range(50):
        cmd("ASSEMBLY NOOP")
    # Allow time for command queue to drain
    wait_check_expression(
        f"tlm('ASSEMBLY HK CMD_SUCCESS_COUNT') >= {initial + 50}", 30)

def test_boundary_parameter(self):
    # Exact min boundary -- should be valid
    cmd("ASSEMBLY STAGE_PARAMETER with TABLE_ID THRESHOLDS, "
        "ENTRY_ID OVER_TEMP, VALUE -40.0")
    cmd("ASSEMBLY VALIDATE_PARAMETERS with TABLE_ID THRESHOLDS")
    wait_check("ASSEMBLY PARAM_STATUS VALIDATION_STATE == 'VALID'", 5)
    # Just outside boundary -- should be invalid
    cmd("ASSEMBLY STAGE_PARAMETER with TABLE_ID THRESHOLDS, "
        "ENTRY_ID OVER_TEMP, VALUE -40.1")
    cmd("ASSEMBLY VALIDATE_PARAMETERS with TABLE_ID THRESHOLDS")
    wait_check("ASSEMBLY PARAM_STATUS VALIDATION_STATE == 'INVALID'", 5)
```

## Using Adamant Python in Test Scripts (pydep)

Use `pydep` to build Adamant's generated Python (packed record types, CRC16, pack/unpack utilities) into the plugin. This enables test scripts to construct command payloads and decode telemetry using real Adamant types.

### Setup
1. Add Adamant Python dependencies to plugin's `pydep` configuration
2. Built packages go into plugin `lib/` directory
3. Import in test scripts via `sys.path` or COSMOS plugin path

### Usage in Python test scripts
```python
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from packed_records import My_Record

# Build a packed command payload
record = My_Record()
record.Field_1 = 42
record.Field_2 = 3.14
raw_bytes = record.pack()

# Verify telemetry matches expected packed structure
expected = My_Record()
expected.unpack(raw_bytes_from_tlm)
assert expected.Field_1 == 42
```

### Packed_F32 encoding for command parameters
```python
import struct

# Many Adamant commands take packed float32 values as U32 integers
def pack_f32(value: float) -> int:
    """Pack a float32 into a big-endian U32 for COSMOS command parameter."""
    return struct.unpack('>I', struct.pack('>f', value))[0]

# Usage: cmd(f"ASSEMBLY Pid_Controller_Instance-Set_Kp with VALUE {pack_f32(2.5)}")
```

### Event subpacket decoding via pydep
```python
# Event packets (APID 98) contain variable-length subpackets.
# Each subpacket has: Event_Header (id, timestamp) + serialized event record.
# Use pydep-built types to decode:
from event_header import Event_Header
from mode_changed_event import Mode_Changed_Event

raw = tlm("ASSEMBLY EVENT_PACKET SUBPACKET_DATA", type="RAW")
header = Event_Header()
header.unpack(raw[:Event_Header.size()])
event_id = header.Id
# Decode body based on event_id mapping
if event_id == MODE_CHANGED_ID:
    body = Mode_Changed_Event()
    body.unpack(raw[Event_Header.size():Event_Header.size() + Mode_Changed_Event.size()])
    assert body.New_Mode == expected_mode
```

**Note:** Direct event subpacket parsing requires knowing the event record layout from generated Python types. When pydep types aren't available, verify events indirectly via data product state changes (e.g., check that Mode data product changed after sending a mode command).

### CRC16 validation
```python
from crc16 import Crc16

# Single-shot
crc = Crc16()
crc.update(payload_bytes)
assert crc.value == expected_crc

# Incremental (same result as bulk)
crc2 = Crc16()
crc2.update(header_bytes)
crc2.update(body_bytes)
# crc2.value == Crc16().update(header_bytes + body_bytes).value

# Cross-validate against COSMOS
cosmos_crc = int(tlm("ASSEMBLY System_Status_Packet CCSDS_CRC", type="RAW"))
local_crc = Crc16()
local_crc.update(packet_bytes_without_crc)
assert local_crc.value == cosmos_crc
```

### Raw CCSDS packet construction
For protocol-level testing, build CCSDS packets manually:
```python
import struct
from crc16 import Crc16

def build_ccsds_cmd(apid, seq_count, payload_bytes):
    """Build a complete CCSDS command packet with CRC."""
    data_length = len(payload_bytes) + 2 - 1  # +2 for CRC, -1 per CCSDS convention
    # Primary header: version=0, type=1(cmd), sec_hdr=1, APID
    word0 = (0 << 13) | (1 << 12) | (1 << 11) | (apid & 0x7FF)
    word1 = (0x3 << 14) | (seq_count & 0x3FFF)  # seq_flags=3 (unsegmented)
    header = struct.pack('>HHH', word0, word1, data_length)
    # Secondary header (Adamant: 8-byte function code area)
    # Append payload + CRC
    packet = header + payload_bytes
    crc = Crc16()
    crc.update(packet)
    return packet + struct.pack('>H', crc.value)
```

## Disconnect Mode (Offline Testing)

Disconnect mode validates command structure without sending to hardware. Useful for script development and CI.

```python
# Activate programmatically
from openc3.script import disconnect_script
disconnect_script()

# Or via CLI
# openc3.sh cli script run test.py --disconnect
```

**`openc3.script.DISCONNECT`** — boolean flag, True when running in disconnect mode. Use to conditionally set up overrides.

**Behavior in disconnect mode:**
- Commands: parsed and validated against definitions, NOT sent
- Checks: print ERROR instead of raising CheckError
- Limits methods: silently ignored
- Telemetry reads: still need API_SERVER (use `override_tlm` to pre-set expected values)
- `tlm()` on an item with no prior `override_tlm` returns the default/zero value from the definition

### Simulating telemetry for offline tests
```python
def setup(self):
    if openc3.script.DISCONNECT:
        # Pre-set expected telemetry values for offline validation
        override_tlm("ASSEMBLY", "HK", "OPERATING_MODE", "SAFE")
        override_tlm("ASSEMBLY", "HK", "CMD_SUCCESS_COUNT", 0)
```

## Plugin File Organization

```
openc3-cosmos-assembly/
  targets/ASSEMBLY/
    cmd_tlm/
      cmd.txt
      tlm.txt
    procedures/
      test_command_acceptance.py
      test_telemetry_verification.py
      test_mode_transitions.py
      test_fault_injection.py
      test_end_to_end.py
      test_parameter_update.py
      test_rate_verification.py
      test_stress.py
      integration_suite.py        # Suite aggregating all groups
    lib/
      (pydep-built Adamant Python)
      cmd_checksum.rb             # Adamant XOR checksum protocol
      crc_sync_protocol.rb        # CRC + sync word protocol (serial)
      cmd_sync_checksum.rb        # Checksum + sync word (serial)
  plugin.txt
  plugin.gemspec
```

## Running Tests

### Via CLI
```bash
openc3.sh cli script run ASSEMBLY/procedures/test_command_acceptance.py
openc3.sh cli script run ASSEMBLY/procedures/integration_suite.py
openc3.sh cli script run ASSEMBLY/procedures/test_command_acceptance.py --disconnect
```

### Via Script Runner UI
Script Runner -> File -> Open -> select script -> Run (or Run Disconnect)

### Via REST API
```bash
TOKEN=$(curl -s http://localhost:2900/auth/token -d '{"scope":"DEFAULT"}' | jq -r .token)
curl http://localhost:2900/script-api/running-script \
  -H "Authorization: $TOKEN" \
  -d '{"name":"ASSEMBLY/procedures/integration_suite.py","scope":"DEFAULT"}'
```

## Array Data Products in Telemetry

COSMOS flattens array data products into individually-named items. For an array data product `Zone_Temperature` with 4 elements, the tlm.txt typically defines:

```
ITEM Zone_Temperature_0 ...   # First element
ITEM Zone_Temperature_1 ...   # Second element
```

Access in scripts:
```python
temp_0 = tlm("ASSEMBLY THERMAL_HK Zone_Temperature_0.Value")
temp_1 = tlm("ASSEMBLY THERMAL_HK Zone_Temperature_1.Value")
```

**Note:** The exact naming depends on how the product_packets.yaml and tlm.txt define the items. Always check your tlm.txt for the actual item names.

## Limits-Based Out-of-Range Detection

Use COSMOS limits + telemetry overrides to test out-of-range condition handling without real sensor data:

```python
def test_overvoltage_detection(self):
    # Set tight limits
    set_limits("ASSEMBLY", "POWER_HK", "BUS_VOLTAGE", 10.0, 12.0, 14.0, 16.0)
    enable_limits("ASSEMBLY", "POWER_HK", "BUS_VOLTAGE")
    # Override telemetry to trigger violation
    override_tlm("ASSEMBLY", "POWER_HK", "BUS_VOLTAGE", 17.0)
    wait(1)
    # Check limits state
    ool = get_out_of_limits()
    voltage_ool = [v for v in ool if v[2] == "BUS_VOLTAGE"]
    if not voltage_ool:
        raise CheckError("Expected BUS_VOLTAGE out of limits")
    # Cleanup
    normalize_tlm("ASSEMBLY", "POWER_HK", "BUS_VOLTAGE")
    disable_limits("ASSEMBLY", "POWER_HK", "BUS_VOLTAGE")
```

`get_out_of_limits()` returns a list of `[target, packet, item, state]` tuples where state is `"RED"`, `"RED_HIGH"`, `"RED_LOW"`, `"YELLOW"`, `"YELLOW_HIGH"`, or `"YELLOW_LOW"`.

## Large-Subscription Teardown and tlm() Connection Reset

Tests that use `subscribe_packets()` to collect many packets (e.g., streaming
memory dumps, long capture bursts, bulk data product retrieval) and then
immediately call `tlm()` against the cmd-tlm-api REST endpoint can hit a
deterministic HTTP keep-alive race:

1. `get_packets()` returns a large multi-KB response from cmd-tlm-api
2. Python-side processing of the returned packets takes some time
3. Puma's idle keep-alive timeout (~20s default) closes the pooled HTTP connection
4. The Python `requests` connection pool in `openc3.script` has no way to know
   the server already closed the connection
5. The next `tlm()` call reuses the stale connection and gets a TCP RST back
6. Script raises `JsonDRbError: ... ConnectionResetError(104, 'Connection reset by peer')`

The cmd-tlm-api server is healthy throughout -- the failing request never even
reaches the server. This is purely a client-side connection-pool race.

**Failure signature:**

```
openc3.io.json_drb_object.JsonDRbError: No response from server: Request:
{'url': 'http://openc3-cosmos-cmd-tlm-api:2901/openc3-api/api', ...}
::: Exception: ConnectionError(ProtocolError('Connection aborted.',
ConnectionResetError(104, 'Connection reset by peer')))
```

**When to expect this:**

- Tests that do `subscribe_packets()` -> `cmd()` (that generates many packets) ->
  `wait_check(RECEIVED_COUNT >= target)` -> `get_packets()` -> `tlm()`
- Particularly when the packets are large (hundreds of bytes each) and numerous
  (dozens)
- More likely in CI than interactive use (CI has less idle traffic keeping the
  connection warm)
- Highly reproducible on the same line once timing is established; does not
  appear random

**Mitigation:** Wrap the `tlm()` call that follows `get_packets()` with a
retry. One retry is sufficient because the second attempt opens a fresh
connection:

```python
# Retry tolerates stale HTTP keep-alive connection from the preceding
# get_packets() large response. One retry re-establishes the connection.
value = None
for attempt in range(3):
    try:
        value = tlm(f"{TARGET} {PACKET} {ITEM}")
        break
    except Exception as e:
        if attempt == 2:
            raise
        print(f"tlm() failed after get_packets() (attempt {attempt + 1}/3): {e}; retrying...")
        wait(1)
```

The pattern applies to **any** `tlm()` / `cmd()` / `wait_check()` call that
immediately follows a large subscription response. The race is not specific
to any particular packet or test -- it is an OpenC3 Python client library
limitation that can affect any test making this call sequence.

## Practical Notes

- **Timeouts:** Tune to assembly rate group config. Examples assume 1 Hz housekeeping.
- **CCSDS sequence wrap:** 14-bit counter wraps at 16383. Use a helper for delta calculation:
  ```python
  def seq_delta(before, after): return (after - before) % 16384
  ```
- **Command_Response:** Standard Adamant pattern -- every command produces a response data product. Always verify STATUS after commanding.
- **Fault injection:** Assembly-specific. Requires test commands built into the assembly (not all assemblies have these).
- **Packet names:** Must match COSMOS plugin cmd.txt/tlm.txt definitions exactly (TARGET PACKET ITEM).
- **`wait_check_expression` evaluates strings:** Only `tlm()`, `cmd()`, and built-in Python are available inside the expression string. User-defined functions (e.g., `seq_delta()`) are NOT visible. Use `wait_check_packet` or manual polling loops instead.
- **CCSDS standard items:** COSMOS auto-generates `CCSDS_VERSION`, `CCSDS_TYPE`, `CCSDS_SEC_HDR_FLG`, `CCSDS_APID`, `CCSDS_SEQ_FLAGS`, `CCSDS_SEQ_COUNT`, `CCSDS_LENGTH` for every packet with a CCSDS header. Read with `type="RAW"` to get integer values.
- **Python vs Ruby:** Both APIs have identical method names and behavior. Python recommended for Adamant since tooling is Python-based.
- **Performance:** Use `disable_instrumentation()` context manager for tight loops:
  ```python
  with disable_instrumentation():
      for _ in range(100):
          cmd("ASSEMBLY Component-Noop")
  ```
- **Thread safety:** COSMOS Python API is NOT guaranteed thread-safe. Avoid concurrent `cmd()`/`tlm()` calls from multiple threads. If testing concurrent command streams, serialize sends or accept race conditions in test results.
- **Watchdog testing:** Common pattern -- `Pet_Watchdog` keeps healthy, `Force_Timeout` triggers fault state. Verify via watchdog state data product, then recover with another pet command.

## Negative Assertion Patterns

Sometimes you need to verify something does NOT happen (e.g., downstream stops updating after disabling a component). COSMOS has no built-in "assert unchanged" -- use a polling stability check:

```python
def wait_for_stable(target, packet, item, duration_s=5, poll_s=0.5, tolerance=None):
    """Assert a telemetry value does NOT change over duration_s seconds.
    Use tolerance for float values (e.g., tolerance=0.01)."""
    baseline = tlm(f"{target} {packet} {item}")
    elapsed = 0
    while elapsed < duration_s:
        time.sleep(poll_s)
        elapsed += poll_s
        current = tlm(f"{target} {packet} {item}")
        if tolerance is not None:
            changed = abs(float(current) - float(baseline)) > tolerance
        else:
            changed = current != baseline
        if changed:
            raise RuntimeError(f"{item} changed from {baseline} to {current} after {elapsed}s")
```

Use for interruption tests (disable component, verify downstream freezes) and quiescent state checks.

**Always pair negative assertions with positive-control re-enable tests.** A system that was never active also passes `wait_for_stable`. Pattern: (1) verify thing IS changing, (2) disable, (3) verify thing STOPS changing, (4) re-enable, (5) verify thing RESUMES changing. Steps 1 and 4-5 prevent false passes.

**Duration guidance:** Set `duration_s` to at least 3x the component's control period. A 1 Hz controller needs >= 3s; a 10 Hz controller needs >= 0.3s (use 1s minimum for reliability).

## Boot Sequence Testing

Early boot phases need `wait_packet` (not `wait_check`) because telemetry may not have arrived yet:

```python
def test_01_assembly_alive(self):
    """First contact -- wait for ANY packet before checking values."""
    wait_packet("ASSEMBLY", "System_Status_Packet", 1, timeout=10)  # blocks until first packet
    # NOW safe to use wait_check/check
    check("ASSEMBLY System_Status_Packet CCSDS_SEQ_COUNT > 0")
```

Order boot tests numerically (`test_01` through `test_0N`) to enforce sequential verification: POST -> init -> rate groups -> command link -> telemetry flow -> nominal mode.

**No-faults health gate** (use after boot or before ops procedures):
```python
fault_count = int(tlm(f"{target} System_Status_Packet Fault_Count.Value"))
assert fault_count == 0, f"Assembly has {fault_count} active faults"
```

## Operational Procedure Patterns

For ops scripts (not test assertions), use `script_*` or `op_*` naming (COSMOS discovers but doesn't assert):

```python
# script_daily_pass.py -- not test_daily_pass.py
def pre_pass_check(target):
    """Gate on health before proceeding."""
    soc = float(tlm(f"{target} Power_HK Battery_SOC.Value"))
    if soc < 30.0:
        raise RuntimeError(f"SOC too low for pass: {soc}%")
    return {"soc": soc, "faults": int(tlm(f"{target} System_Status_Packet Fault_Count.Value"))}

def abort_pass(target, criteria):
    """Check abort criteria between steps."""
    soc = float(tlm(f"{target} Power_HK Battery_SOC.Value"))
    return soc < criteria.get("min_soc", 20.0)
```

Key differences from test scripts: no assertions (use explicit if/raise), operator-facing print output, abort/contingency checks between steps, structured pass reports at end.

## Multi-Target Testing

When testing assemblies that communicate (e.g., flight SW + ground simulator), use separate target names:

```python
# Configure simulator
cmd(f"GROUND_SIM Sensor_Sim-Set_Sun_Vector with X {pack_f32(0.5)}, Y {pack_f32(0.5)}, Z {pack_f32(0.707)}")
# Verify flight SW responds
wait_check("FLIGHT_FSW Attitude_HK Controller_State.Value == 'TRACKING'", 15)
# Cross-target consistency
sim_seq = tlm("GROUND_SIM Sim_Status CCSDS_SEQ_COUNT")
flight_seq = tlm("FLIGHT_FSW Flight_HK CCSDS_SEQ_COUNT")
```

For vector commands with multiple F32 fields, pack each independently:
```python
cmd(f"TARGET Component-Set_Vector with X {pack_f32(1.0)}, Y {pack_f32(2.0)}, Z {pack_f32(3.0)}")
```

## Related Skills

- **adamant-cosmos-integration** -- Plugin structure, CCSDS wiring, cmd/tlm definitions, CLI reference
- **adamant-component-dev** -- Component YAML, commands, events, data products, parameters
- **adamant-assembly-dev** -- Assembly wiring, rate groups, command routing
- **adamant-testing** -- Unit-level component testing (Ada, inside the assembly)
