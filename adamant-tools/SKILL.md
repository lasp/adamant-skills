# adamant-tools

Development tools for Adamant component workflows. Three standalone Python scripts that require no Docker or build environment (except `adamant_inspect` which reads generated files).

## Tools

### adamant_inspect.py -- Generated API Extractor

**Purpose:** After `redo` generates a component, extract a concise summary of the generated API: connectors, methods to override, helpers to call, events, data products, commands, parameters, faults, data dependencies, and tester histories.

**When to use:** After first successful `redo` build of a component, before writing the implementation body or test body. Eliminates guessing at generated method names, parameter types, and tester API.

```
python3 adamant_inspect.py <component_dir>

# Example:
python3 adamant_inspect.py src/components/voltage_monitor
```

**Output sections:**
- INIT PARAMETERS -- `Init` procedure signature
- SET_ID_BASES -- which ID bases the component requires
- RECV CONNECTORS -- abstract procedures to override (handler implementations)
- SEND/GET/REQUEST CONNECTORS -- helper procedures/functions to call
- DROPPED HANDLERS -- abstract null procedures for each send connector
- DATA DEPENDENCY HELPERS -- private `Get_*` functions for data deps
- DATA DEPENDENCY ABSTRACTS -- `Get_Data_Dependency` and `Invalid_Data_Dependency`
- INSTANCE FIELDS -- `Self.*` record fields (Events, Data_Products, Faults, etc.)
- EVENTS/DATA_PRODUCTS/COMMANDS/FAULTS -- creation function signatures
- PARAMETERS -- table fields and `Validate_Parameters` signature
- TESTER API -- typed history names, connector histories, override fields

**Key value:** The #1 cold-start error is guessing at generated API names. This tool provides the exact signatures.

### adamant_scaffold.py -- Component Scaffolder

**Purpose:** Generate all YAML models, implementation stubs (.ads/.adb), and test infrastructure (tests.yaml, env.py) from a spec file.

**When to use:** Starting a new component. Write a simple YAML spec describing what the component needs, then scaffold generates all files.

```
python3 adamant_scaffold.py <spec_file.yaml> [output_dir]

# Example:
python3 adamant_scaffold.py watchdog_timer_spec.yaml
# Creates src/components/watchdog_timer/ with all files
```

**Spec file format:**
```yaml
name: watchdog_timer
description: Monitors heartbeats and triggers timeout faults
execution: passive
init:
  - name: Timeout_Ms
    type: Unsigned_32
    description: Timeout period in milliseconds
connectors:
  recv_sync:
    - type: Tick.T
      description: Periodic check
  send:
    - type: Event.T
      description: Event output
    - type: Data_Product.T
      description: Data product output
  get:
    - type: Sys_Time.T
      description: System time
events:
  - name: Heartbeat_Received
    description: Valid heartbeat detected
  - name: Timeout_Triggered
    description: Heartbeat timeout detected
    param_type: Packed_U32.T
data_products:
  - name: Heartbeat_Count
    type: Packed_U32.T
    description: Total heartbeats received
commands:
  - name: Reset
    description: Reset the watchdog timer
faults:
  - name: Heartbeat_Timeout
    description: No heartbeat within timeout period
parameters:
  description: Configurable parameters
  items:
    - name: Timeout_Threshold
      type: Packed_U32.T
      default: "5000"
      description: Timeout in milliseconds
data_dependencies:
  description: External data dependencies
  items:
    - name: System_Health
      type: Packed_Boolean.T
      description: Overall system health status
```

**Generated files:**
- `<name>.component.yaml` -- main component model
- `<name>.events.yaml` -- event definitions (if events specified)
- `<name>.data_products.yaml` -- data product definitions (if DPs specified)
- `<name>.commands.yaml` -- command definitions (if commands specified)
- `<name>.parameters.yaml` -- parameter definitions (if parameters specified)
- `<name>.faults.yaml` -- fault definitions (if faults specified)
- `<name>.data_dependencies.yaml` -- data dependency definitions (if data deps specified)
- `component-<name>-implementation.ads` -- implementation spec stub
- `component-<name>-implementation.adb` -- implementation body stub with TODO markers
- `test/<name>.tests.yaml` -- test configuration
- `test/env.py` -- test environment

**After scaffolding:**
1. Review and edit generated files (fill in TODOs)
2. `redo <component_dir>/build/src/component-<name>.ads` (generate base class)
3. Run `adamant_inspect.py` to see the full generated API
4. `redo <component_dir>/test/build/template/` (generate test templates)
5. `cp <component_dir>/test/build/template/*.ads <component_dir>/test/`
6. Write test body, then `cd test && redo test`

### adamant_validate_yaml.py -- YAML Pre-flight Checker

**Purpose:** Fast structural validation of component YAML files without Docker. Catches the errors that most commonly cause `redo` failures.

**When to use:** After writing or editing YAML files, before running `redo`. Saves a Docker round-trip per error.

```
python3 adamant_validate_yaml.py <component_dir>

# Example:
python3 adamant_validate_yaml.py src/components/voltage_monitor
```

**What it checks:**
- Required fields in component YAML (description, execution, connector types/kinds)
- Framework component name collisions (58 known names)
- Init parameter structure and string defaults
- Feature YAML field names (`param_type` not `type` for events, `arg_type` not `type` for commands)
- Cross-file consistency (feature YAML exists but matching connector missing)
- File naming conventions (implementation spec/body, test directory structure)
- Test directory rules (env.py content, no .all_path in test dirs)

**What it does NOT check:**
- Full JSON Schema validation (requires Adamant Python environment)
- Ada compilation correctness
- Connector count or wiring validity

## Integration with Skills

These tools complement the existing skills:
- **adamant-component-dev**: Use `adamant_scaffold` to create files, `adamant_validate_yaml` before building
- **adamant-testing**: Use `adamant_inspect` after first build to see tester API before writing tests
- **adamant-build-system**: Tools run outside Docker; `redo` still handles all code generation

## Environment Caching: adamant_env.sh exec

The project's `docker/adamant_env.sh exec` command handles environment activation automatically via a cached snapshot (~0.25s vs 3-5 seconds for full activation). **Always use `adamant_env.sh exec` -- never use `source env/activate` directly.**

```bash
# Run any command inside the container:
bash docker/adamant_env.sh exec "cd /home/user/<project> && redo <target>"

# Discover what can be built:
bash docker/adamant_env.sh exec "cd /home/user/<project>/path/to/dir && redo what"
```

**Sub-agent workflow pattern:**
```bash
# Step 1: Copy tools into container (once per container start)
docker cp adamant-tools/*.py <project>_container:/tmp/

# Step 2: Validate YAML (e.g. src/components/thermal_controller)
bash docker/adamant_env.sh exec "python3 /tmp/adamant_validate_yaml.py src/components/thermal_controller"

# Step 3: Build component
bash docker/adamant_env.sh exec "cd /home/user/<project> && redo src/components/thermal_controller/build/src/component-thermal_controller.ads"

# Step 4: Inspect generated API
bash docker/adamant_env.sh exec "python3 /tmp/adamant_inspect.py src/components/thermal_controller"

# Step 5: Build and test
bash docker/adamant_env.sh exec "cd /home/user/<project>/src/components/thermal_controller/test && redo test"
```

## pykwalify Schema Validation

Inside Docker (with `source activate`), the validator automatically uses Adamant's real pykwalify schemas from `$SCHEMAPATH`. This catches all YAML structural errors authoritatively -- no heuristic guessing.

Outside Docker, the validator falls back to heuristic checks (field names, connector consistency, naming conventions). These catch the most common errors but are not exhaustive.

## Location

Tools are in the `adamant-tools/` directory of the skills repository. Copy into Docker containers or run from the host against mounted volumes.
