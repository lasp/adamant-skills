---
name: adamant-build-system
description: Understanding and using the Adamant redo-based build system and code generation framework
---

# Adamant Build System

Redo-based: YAML models → Python/Jinja2 code generation → Ada compilation, with incremental deps and multi-target cross-compilation.

## YAML Model Extensions

```
*.component.yaml    *.assembly.yaml     *.record.yaml       *.array.yaml
*.commands.yaml     *.events.yaml       *.data_products.yaml *.tests.yaml
*.parameters.yaml   *.faults.yaml       *.packets.yaml      *.enums.yaml
```

## Build Path System

Empty marker files control directory inclusion in the build path:
- `.all_path` — included for ALL targets
- `.Linux_path` — included only when TARGET contains "Linux"
- `.Pico_path` — included only for Pico targets
- `.bb_path` — bare board targets only
- `.32bit_path` / `.64bit_path` — architecture-specific

The build system recursively searches each BUILD_ROOT for these marker files. A directory is included if it contains `.all_path` OR `.<TARGET>_path` matching the current target. Test directories use `env.py` instead of `.all_path`.

### Path Resolution Order
1. Every directory containing `.all_path`
2. Every directory containing `.$TARGET_path` (target-specific)
3. Directories in `$EXTRA_BUILD_PATH`
4. Current source directory of the redo build target

**File uniqueness rule:** File names must be unique across the entire build path. When duplicates exist, later paths take precedence (project overrides framework).

### Environment Variables
```bash
export TARGET=Linux                    # Build target (default: Linux)
export ADAMANT_DIR=/path/to/adamant    # Framework root (auto-detected)
export ADAMANT_CONFIGURATION_YAML=/path/to/project.configuration.yaml
export EXTRA_BUILD_PATH="/extra/dirs"  # Additional build path directories
export BUILD_ROOTS="/root1:/root2"     # Roots scanned for .path files
export BUILD_PATH="/explicit/path"     # Override: skip scanning, use this directly
export SCHEMAPATH=$ADAMANT_DIR/gen/schemas
export TEMPLATEPATH=$ADAMANT_DIR/gen/templates
export ADAMANT_TMP_DIR=<auto>          # Session temp dir for SQLite caches
```

Default BUILD_ROOTS: Adamant repo root + project root (both auto-detected via `.git`).

### Environment Activation
```bash
# Framework only:
source $ADAMANT_DIR/env/activate

# Project (passes project dir as extra build root):
source $ADAMANT_DIR/env/activate /path/to/project

# Multiple roots:
source $ADAMANT_DIR/env/activate "/path/to/project1:/path/to/project2"
```

Activation does: set BUILD_ROOTS, create Python venv, install requirements, set GPR_PROJECT_PATH, configure Alire dependencies, set PYTHONPATH for code generators.

Validation: `bash scripts/check_build_paths.sh <project_root>`

## Redo Command Reference

All predefined targets (available in any directory):

### Build Targets
```bash
redo all              # Build everything in current directory
redo -j               # Parallel build (uses -j0 internally for gprbuild)
redo templates        # Generate implementation stubs → build/template/
redo publish          # Publish build artifacts
redo targets          # Show available build targets and their descriptions
```

### Test & Verification
```bash
redo test             # Run unit test (from test/ dir, needs test.adb → test.elf)
redo test_all         # Recursive: run all tests in subdirectories
redo coverage         # Coverage analysis via gcov (redo clean first!)
redo coverage_all     # Recursive coverage for all subdirectories
redo style            # Style check: Ada warnings + flake8 + yamllint + codespell
redo style_all        # Recursive style check
redo prove            # SPARK proof (needs all.prove.yaml in component dir)
redo analyze          # GNAT SAS static analysis
redo analyze_all      # Recursive static analysis
redo pretty           # Auto-format Ada source code
```

### Diagrams & Documentation
```bash
redo build/svg/name.svg     # Architecture/type diagram (SVG)
redo build/eps/name.eps     # EPS diagram
redo build/png/name.png     # PNG diagram
redo build/pdf/name.pdf     # PDF document
redo build/html/name.html   # HTML documentation
```

### Maintenance
```bash
redo clean            # Remove build/ in current directory
redo clean_all        # Recursive clean (all subdirectories)
redo clear_cache      # Clear model cache (SQLite in $ADAMANT_TMP_DIR)
```

### Inspect
```bash
redo what             # List all buildable targets in current directory
redo what_predefined  # List predefined (universal) targets
```

### Style Check Details
`redo style` performs four checks:
1. **Ada style** — Recompiles all `.o` files with `CHECK_STYLE=True`, enforcing GNAT style switches (`-gnaty3aABbdDefhiklL12nOprStux`)
2. **Python flake8** — Checks `*.py` in current dir and `build/py/` (ignores E121,E123,E126,E226,E24,E704,W503,W504,E402,E501)
3. **YAML lint** — Validates YAML files after resolving Jinja2 templates via configuration
4. **Codespell** — Spell-checks all source files (uses `redo/codespell/ignore_list.txt`)

Results written to `build/style/style.log`.

## Code Generation Pipeline

```
YAML Model → Schema Validation (PyKwalify) → Python Model Object → Jinja2 Template → Generated Output
```

### Directory Structure
- `gen/schemas/` — PyKwalify YAML validation schemas
- `gen/models/` — Python model classes that ingest validated YAML
- `gen/generators/` — Generator entry points (orchestrate model→template)
- `gen/templates/` — Jinja2 templates organized by output type

### Generators
| Generator | Purpose |
|-----------|---------|
| `assembly.py` | Assembly-level code generation (Ada, HTML, Python, MATLAB, XML) |
| `component.py` | Component base classes and stubs |
| `packed_types.py` | Record/array/enum types (pack/unpack/validate) |
| `basic.py` | Simple single-file generation |
| `configuration.py` | Project configuration (Ada package from YAML) |
| `ided_suite.py` | ID'd suites (commands, events, data products, etc.) |
| `tests.py` | Test harness (AUnit runner, tester component) |
| `memory_map.py` | Memory map generation |

### Model Classes (`gen/models/`)
| Model | Source YAML |
|-------|------------|
| `component.py` | `*.component.yaml` |
| `assembly.py` | `*.assembly.yaml` |
| `record.py` | `*.record.yaml` |
| `array.py` | `*.array.yaml` |
| `enums.py` | `*.enums.yaml` |
| `commands.py` | `*.commands.yaml` |
| `events.py` | `*.events.yaml` |
| `data_products.py` | `*.data_products.yaml` |
| `packets.py` | `*.packets.yaml` |
| `parameters.py` | `*.parameters.yaml` |
| `faults.py` | `*.faults.yaml` |
| `tests.py` | `*.tests.yaml` |
| `configuration.py` | `*.configuration.yaml` |
| `prove.py` | `*.prove.yaml` |

### Template Directories (`gen/templates/`)
Templates organized by output type: `array/`, `assembly/`, `base/`, `commands/`, `component/`, `configuration/`, `data_dependencies/`, `data_products/`, `enums/`, `events/`, `faults/`, `gpr/`, `memory_map/`, `packets/`, `parameters/`, `record/`, `register_map/`, `requirements/`, `tests/`, `tex/`.

### Generated Output per Model Type

| Model Type | Key Outputs |
|-----------|-------------|
| Component | Base class `.ads/.adb`, implementation stubs in `build/template/` |
| Assembly | Ada source, HTML, Python, MATLAB, XML, COSMOS config |
| Record/Array/Enum | Ada (pack/unpack/validate/assert/C), Python, MATLAB, LaTeX |
| Commands/Events/etc | Ada suites, HTML, LaTeX |
| Tests | AUnit runner, tester, reciprocal component |

### Key Generated Files
- **component.yaml** → `build/src/component-{name}.ads/.adb` (base class), `build/template/component-{name}-implementation.ads/.adb` (stubs)
- **events.yaml** → `build/src/{name}_events.ads/.adb` + `-representation`
- **commands.yaml** → `build/src/{name}_commands.ads/.adb`
- **record.yaml** → `build/src/{name}.ads/.adb` + `-representation`, `-validation`, `-assertion`, `-c`

Generated files live in `build/src/`. Source files with the same name override generated ones.

### Jinja2 Template Variables
YAML files can use Jinja2 syntax to reference configuration values:
```yaml
buffer_size: {{ data_product_buffer_size }}
```
Templates are resolved against the project configuration YAML before validation.

## Configuration YAML Schema

The `*.configuration.yaml` file provides project-wide constants. Referenced via `$ADAMANT_CONFIGURATION_YAML`.

### Required Fields
```yaml
---
description: "Project description string"

# Core type buffer sizes (bytes) — size to fit largest instance in system
data_product_buffer_size: 32      # Data product serialization buffer
command_buffer_size: 255          # Command argument buffer
event_buffer_size: 32             # Event parameter buffer
parameter_buffer_size: 32         # Parameter type buffer
packet_buffer_size: 1246          # Packet buffer
fault_buffer_size: 8              # Fault parameter buffer
ccsds_packet_buffer_size: 1274    # CCSDS space packet buffer (if using CCSDS)

# Task/stack configuration
stack_margin: 1000                # Stack margin bytes (bareboard only; Linux uses 12KB fixed)
command_registration_delay: 250   # Microseconds between command registrations
```

### Custom Variables
Add project-specific key-value pairs below the required fields. Reference them in YAML via `{{ variable_name }}` or in Ada via the `Configuration` package.

### Example Project Configuration
```yaml
---
description: Configuration for the Adamant Bot Station demo.
data_product_buffer_size: 32
command_buffer_size: 128
event_buffer_size: 32
parameter_buffer_size: 32
fault_buffer_size: 8
ccsds_packet_buffer_size: 512
packet_buffer_size: 480
stack_margin: 1000
command_registration_delay: 250
```

## Compiler & Linker Flags

### Base Ada Flags (all targets, from `a_adamant.gpr`)
```
-gnatf        Full errors
-gnatwa       Enable all warnings
-gnatwl       Elaboration pragma warnings
-gnatw.o      Modified but unreferenced out parameters
-gnatwt       Deleted conditional code
-gnatw.X      Disable No_Exception_Propagation warnings
-gnat2022     Enable Ada 2022 features
```

### Style Flags (enabled by `redo style` / `CHECK_STYLE=True`)
```
-gnaty3aABbdDefhiklL12nOprStux
  3   = 3-space indentation          a = attribute casing
  A   = array 'Length must use index  B = and/or only for bitwise
  b   = no trailing blanks            d = no DOS line endings
  D   = mixed case identifiers        e = labels on end statements
  f   = no form feeds                 h = no horizontal tabs
  i   = if-then layout                k = lowercase keywords
  l   = RM layout                     L12 = max nesting 12
  n   = Standard casing per RM        O = overriding markers required
  p   = pragma casing                 r = reference casing matches decl
  S   = no statements on then/else    t = token spacing
  u   = unnecessary blank lines       x = no unnecessary parens
```

### Linux Debug Flags (`a_linux_debug_base.gpr`)
```
-O0           No optimization
-g            Debug info
-fstack-check Dynamic stack checking
-gnato        Numeric overflow checking
-gnata        Assertions enabled
-gnatVa       ALL validity checking
-gnatec=...initialize_scalars.adc   Detect uninitialized variables
```

### Linux Debug (with Ravenscar, `linux_debug.gpr`)
Adds: `-gnatec=...ravenscar.adc` (Ravenscar profile enforcement)

### Linux Test (`linux_test.gpr`)
Same as Linux Debug base but WITHOUT Ravenscar, links with AUnit.

### Bareboard Base Flags (`a_bareboard_base.gpr`)
```
-fno-delete-null-pointer-checks   Allow access to address 0x0
-g3 -ggdb                         Full debug info
-ffunction-sections -fdata-sections  Dead code elimination prep
-gnatec=...ravenscar.adc          Ravenscar always enforced
-gnatec=...sequential_elaboration.adc
```
Linker: `-Wl,--gc-sections -Wl,--print-memory-usage -Wl,--defsym=__stack_size=5000`
Binder: `-D10k` (10KB default secondary stack)

### Bareboard Production (`a_bareboard_production.gpr`)
Adds: `-O2 -gnatn` (optimization + back-end inlining)

### Bareboard Debug (`a_bareboard_debug.gpr`)
Adds: `-O0 -gnato -gnata -gnatVa` (no optimization, full checking)

### C/C++ Flags
```
C:   -Wall -Wextra -pedantic -std=gnu99
C++: -Wall -Wextra -pedantic -std=c++0x
```

## SPARK Prove Configuration

Place `all.prove.yaml` in component directory:
```yaml
level: 2          # 0-4 (timeout/prover escalation)
mode: "gold"      # check|flow|prove|all|stone|bronze|silver|gold
```

Override: `PROVE_SWITCHES="--level=4" redo prove`

Prove always uses the `Linux_Prove` target internally. Sets `SAFE_COMPILE=True` to ensure all source dependencies are analyzed.

## Cross-Compilation Targets

### Available Targets (from `redo/targets/`)

| Target Class | Path Files | Arch | Description |
|-------------|-----------|------|-------------|
| `Linux` (default) | `.all_path`, `.Linux_path`, `.64bit_path` | x86-64 | Alias for Linux_Debug |
| `Linux_Debug` | same | x86-64 | -O0, debug, Ravenscar, validity checks |
| `Linux_Test` | `.all_path`, `.Linux_path`, `.Linux_Test_path`, `.64bit_path` | x86-64 | Debug without Ravenscar, links AUnit |
| `Linux_Coverage` | same as Test | x86-64 | Test + gcov flags |
| `Linux_Prove` | same as Debug | x86-64 | For GNATprove SPARK analysis |
| `Linux_Analyze` | same as Debug | x86-64 | GNAT SAS deep mode |
| ARM bare board | `.all_path`, `.bb_path`, `.32bit_path` | ARM (arm-eabi) | For Cortex-M, etc. |
| RISC-V bare board | `.all_path`, `.bb_path`, `.32bit_path` | RISC-V (riscv32-elf) | For RISC-V MCUs |

### Target-Specific Source Bodies
```
hardware_action.ads              # Shared spec (.all_path)
linux/hardware_action.adb        # .Linux_path
pico/hardware_action.adb         # .Pico_path
```

### Setting the Target
```bash
export TARGET=Pico
redo build/bin/Pico/main.elf
```

### Ada Runtime Modes
- **Full** (Jorvik) — default, full tasking
- **SFP** (Small Footprint) — reduced runtime
- **ZFP** (Zero Footprint) — bare metal, no runtime

## Project Structure

```
project/
├── config/
│   └── project.configuration.yaml   # Project configuration
├── env/
│   ├── activate                     # Sources adamant/env/activate with project root
│   └── requirements.txt             # Extra Python dependencies
├── docker/
│   └── adamant_env.sh               # Container management (start/login/stop)
├── src/
│   └── components/                  # Component source directories
│       └── my_component/
│           ├── .all_path            # Include in all builds
│           ├── my_component.component.yaml
│           ├── component-my_component-implementation.ads
│           ├── component-my_component-implementation.adb
│           └── test/                # Unit tests (uses env.py, NOT .all_path)
│               ├── env.py
│               └── test.adb
└── assembly/
    └── main.assembly.yaml
```

## Common Build Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Storage_Error` at runtime | Buffer too small | Increase buffer size in configuration YAML |
| `No target test.elf can be built` | Missing `test.adb` in test directory | Create `test.adb` with AUnit runner |
| `duplicate file name` | Same filename in multiple `.path` directories | Rename one; filenames must be globally unique |
| `No valid git repository found` | BUILD_ROOTS can't be auto-detected | Set `BUILD_ROOTS` or `BUILD_PATH` explicitly |
| Model cache stale / weird gen errors | SQLite cache out of date | `redo clear_cache` then rebuild |
| `redo coverage` shows 0% | Built with wrong target | `redo clean` first, then `redo coverage` (needs fresh build with gcov flags) |
| Style warnings as errors | `CHECK_STYLE=True` active | Fix style issues per GNAT style guide; see `build/style/style.log` |
| Ravenscar violations | Linux_Test needed, not Linux | Use test/ directory with `env.py` (auto-selects Linux_Test target) |
| `command_registration` queue overflow | Registration delay too short | Increase `command_registration_delay` in config YAML |
| Alire dependency errors | First container login | Run `alr build --release` or re-source `env/activate` |

## Internals

Details: [references/internals-and-generation.md](references/internals-and-generation.md)
Build commands: [references/build-commands.md](references/build-commands.md)

Session database uses SQLite in `$ADAMANT_TMP_DIR` (created per-session via `mktemp`). `redo clear_cache` clears the model cache.

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Type system**: [adamant-type-system](../adamant-type-system/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
