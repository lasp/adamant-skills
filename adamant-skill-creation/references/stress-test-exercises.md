# Stress Test Exercises
<!-- validated: v1 2026-02-20 -->

Cold-start sub-agent exercises for each skill. Each exercise starts from NOTHING -- the agent must create all files from skill knowledge alone.

## Exercise: component

**Skills loaded:** adamant-skill-selector, adamant-component-dev, adamant-framework-components
**Task:** Create an active component called `heartbeat_monitor` that:
- Has an init parameter `timeout_ms` (Unsigned_32, default 5000)
- Receives `Tick.T` on a synchronous connector
- Sends `Sys_Time.T` request/response to get current time
- Has a command `Reset_Counter` (no args) and `Set_Timeout` (Unsigned_32 arg)
- Has a data product `Heartbeat_Count` (Packed_U32)
- Has a fault `Heartbeat_Timeout`
- Has events: `Heartbeat_Received`, `Heartbeat_Timeout_Detected`, `Counter_Reset`, `Timeout_Updated`
- Has a parameter `Warning_Threshold` (Packed_U16, default 3)
- Implementation: increment counter on tick, fault if counter exceeds timeout, reset on command
**Create in:** `/home/user/adamant_bot_station/src/components/heartbeat_monitor/`
**Validation:** `redo style && redo test` from component directory

## Exercise: test

**Skills loaded:** adamant-skill-selector, adamant-testing, adamant-component-dev
**Task:** Write tests for an existing component (e.g., `limit_checker` or similar).
Steps:
1. Read the component's YAML files to understand its interface
2. Create `test/` directory with `env.py` and `component_name.tests.yaml`
3. Run `redo templates` from test/ dir to generate tester scaffolding
4. Copy generated files from `build/template/` to `test/`
5. Write ONLY the `*_tests-implementation.adb` (test case bodies) from scratch
Tests must cover:
- Nominal behavior
- Command execution (all commands)
- Event verification via typed history
- Data product verification
- Parameter updates (stage/validate/update cycle)
- Error/fault paths
**Create in:** `/home/user/adamant_bot_station/src/components/<component>/test/`
**Validation:** `redo test` then `redo coverage` from component directory

## Exercise: assembly

**Skills loaded:** adamant-skill-selector, adamant-assembly-dev, adamant-framework-components
**Task:** Create a mini assembly called `heartbeat_assembly` that:
- Contains 1 custom component (heartbeat_monitor) + framework components
- Has a Tick_Divider driving a 1Hz rate group
- Has Command_Router for command dispatch
- Has Event_Packetizer for event collection
- Has a Stack_Monitor
- Linux target, 1 rate group
**Create in:** `/home/user/adamant_bot_station/src/assembly/heartbeat_assembly/`
**Validation:** `redo main/build/bin/Linux/main.elf`

## Exercise: subassembly

**Skills loaded:** adamant-skill-selector, adamant-subassemblies, adamant-assembly-dev, adamant-framework-components
**Task:** Create an assembly with 2 subassemblies:
- `monitoring_sub`: heartbeat_monitor + Tick_Divider + rate group
- `telemetry_sub`: Event_Packetizer + Data_Product_Database + Product_Packetizer
- Parent wires cross-subassembly connections (events, data products)
- Parent has Command_Router, Sys_Time_Master
**Create in:** `/home/user/adamant_bot_station/src/assembly/sub_test_assembly/`
**Validation:** ELF builds clean

## Exercise: types

**Skills loaded:** adamant-skill-selector, adamant-type-system
**Task:** Create a set of custom types:
1. Packed record `Sensor_Reading.T` with fields: sensor_id (U8), value (F32), timestamp (U32), status (enum: Valid/Invalid/Stale)
2. Enum `Sensor_Status.E` with 3 values above
3. Array `Sensor_Array.T` of 4 Sensor_Reading.T
4. Simple record `Sensor_Config` with threshold_high (Short_Float), threshold_low (Short_Float)
**Create in:** `/home/user/adamant_bot_station/src/types/sensor_reading/`, etc.
**Validation:** `redo style` on types directories

## Exercise: algorithm

**Skills loaded:** adamant-skill-selector, adamant-algorithm-wrapping, adamant-component-dev
**Task:** Wrap a simple C math function into an Adamant component:
- C function: `float low_pass_filter(float input, float prev_output, float alpha)` 
- Create C source file with the function
- Create C shim header
- Create Ada binding (manual, since no `-fdump-ada-spec` in exercise)
- Create passive Adamant component `low_pass_filter` that wraps it
- Data dependency input: `Packed_F32.T` (raw sensor value)
- Data dependency output: `Packed_F32.T` (filtered value)
- Init param: alpha (Short_Float, default 0.1)
**Create in:** `/home/user/adamant_bot_station/src/components/low_pass_filter/`
**Validation:** `redo style && redo test`

## Exercise: build

**Skills loaded:** adamant-skill-selector, adamant-build-system
**Task:** Given a new source directory with Ada files, set up the build infrastructure:
- Create `.all_path` file with correct contents
- Create `env.py` for test directory
- Verify build path resolution
- Create a `main/` directory with main.adb for an assembly
**Create in:** various directories under bot_station
**Validation:** `redo` resolves all paths correctly

## Exercise: style

**Skills loaded:** adamant-skill-selector, adamant-style
**Task:** Given intentionally messy Ada and YAML files, fix all style violations:
- Ada: wrong casing, missing spaces around operators, wrong indentation, lines >120 chars
- YAML: wrong indentation, missing descriptions, inconsistent quoting
**Provide:** Pre-created messy files
**Validation:** `redo style` passes with 0 warnings
