---
name: adamant-build-system
description: Understanding and using the Adamant redo-based build system and code generation framework. Use when building Adamant projects, debugging compilation issues, or understanding code generation.
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
- `.all_path` -- included for ALL targets
- `.Linux_path` -- included only when TARGET contains "Linux"
- `.Pico_path` -- included only for Pico targets
- `.bb_path` -- bare board targets only
- `.32bit_path` / `.64bit_path` -- architecture-specific

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
export PROJECT_DIR=/path/to/project    # Project root (set by project env/activate)
```

`PROJECT_DIR` is set by the project's `env/activate` script and used by target GPR files to locate project-local `.gpr` files. Without it, target builds fail.

Default BUILD_ROOTS: Adamant repo root + project root (both auto-detected via `.git`).

### Environment Activation
```bash
# Framework only:
source $ADAMANT_DIR/env/activate

# Project (passes project dir as extra build root):
source $ADAMANT_DIR/env/activate /path/to/project

# Multiple roots:
source $ADAMANT_DIR/env/activate "/path/to/project1:/path/to/project2"
```yaml

**In Docker containers, prefer `adamant_env.sh login`** over raw `docker exec` with inline `source`. The base image's `.bashrc` may have already activated the adamant environment, blocking the project's activate via the `ADAMANT_ENVIRONMENT_SET` guard. Login handles this correctly. See `adamant-project-setup` for details.

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
redo coverage         # Coverage analysis via gcov
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

Assembly-level generation includes: HTML command/telemetry docs, PDF documentation, SVG/EPS/PNG architecture diagrams, Python binding classes, COSMOS plugin configs, MATLAB interfaces. Use `redo what` in the assembly directory to list all available targets.

**⚠️ Subassembly constraint**: All assembly-level generation targets (docs, diagrams, COSMOS, Python) require a flat assembly with a top-level `components:` key. Assemblies using only `subassemblies:` will fail validation. Generate per-subassembly or create a flattened assembly for doc generation.

### Maintenance
```bash
redo clean            # Remove build/ in current directory
redo clean_all        # Recursive clean (all subdirectories)
redo clear_cache      # Clear model cache (SQLite in $ADAMANT_TMP_DIR)
redo run               # Build and execute main.elf (from main/ dir only)
redo yaml_sloc         # Count YAML source lines of code
```ada

`redo clean` is always safe on any directory (framework or project). It just removes build artifacts, causing longer rebuilds since redo will rebuild anything whose source changed.

**Assembly build order:** For assemblies, `redo all` in the assembly directory generates source in `build/src/`. The ELF binary is built from `main/` (a sibling directory). If building manually: run `redo all` in the assembly dir first, THEN `redo` in `main/`. Or just use `redo run` from `main/` which handles the dependency chain.

**`redo clean_all` is safe on ANY directory, including the adamant framework.** If redo state corrupts (symptom: `No rule to build 'src/core/connector/in_return_connector.adb'`), run `redo clean_all` on BOTH adamant and the project, then rebuild. The usual cause of corruption is concurrent redo processes (e.g. multiple sub-agents building simultaneously). If clean_all doesn't fix it, recover with `adamant_env.sh remove` + `start` (fresh Docker volumes).

**NEVER manually delete build directories or redo state.** This includes `rm -rf build`, `rm -rf .redo`, `rm -rf */build`, `rm -rf */test/build`, or any variant. Always use `redo clean` or `redo clean_all` -- they properly reset state. Do NOT re-clone the adamant repository (destructive, wipes local state).

### Inspect
```bash
redo what             # List all buildable targets in current directory
redo what_predefined  # List predefined (universal) targets
redo path             # Display build path info
redo print_path       # Print resolved build path
redo recursive        # Recursively build all subdirectories
```ada

### Style Check Details
`redo style` performs four checks:
1. **Ada style** -- Recompiles all `.o` files with `CHECK_STYLE=True`, enforcing GNAT style switches (`-gnaty3aABbdDefhiklL12nOprStux`)
2. **Python flake8** -- Checks `*.py` in current dir and `build/py/` (ignores E121,E123,E126,E226,E24,E704,W503,W504,E402,E501)
3. **YAML lint** -- Validates YAML files after resolving Jinja2 templates via configuration
4. **Codespell** -- Spell-checks all source files (uses `redo/codespell/ignore_list.txt`)

Results written to `build/style/style.log`.

## Code Generation Pipeline

```
YAML Model → Schema Validation (PyKwalify) → Python Model Object → Jinja2 Template → Generated Output
```ada

### Directory Structure
- `gen/schemas/` -- PyKwalify YAML validation schemas
- `gen/models/` -- Python model classes that ingest validated YAML
- `gen/generators/` -- Generator entry points (orchestrate model→template)
- `gen/templates/` -- Jinja2 templates organized by output type

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

### File Override Mechanism

GPR Source_Dirs includes both `build/src/` (generated) and the component's source directory. When GNAT finds two files with the same name, the **source directory wins** because it appears earlier in the Source_Dirs list. This is how you override generated base classes or type packages:

1. Run `redo all` to generate the file in `build/src/`
2. Copy it to your source directory: `cp build/src/my_file.ads ./my_file.ads`
3. Edit the copy -- your version now takes precedence
4. Subsequent `redo` regenerates `build/src/` but GNAT uses your copy

**Template stubs** (`build/template/`) work differently -- they are NOT in Source_Dirs. You explicitly copy them to your source directory to create implementation files. They are never auto-included.

### Test Template Workflow (Critical)

This is the #1 source of test build failures. Test directories need generated template files copied in:

```bash
# From the component directory (NOT the test/ dir):
cd src/components/my_component
redo templates                    # generates build/template/*.ads, *.adb
cp build/template/my_component_tests-implementation.ads test/
cp build/template/my_component_tests-implementation.adb test/
# Also copy tester files:
cp build/template/component-my_component-implementation-tester.ads test/
cp build/template/component-my_component-implementation-tester.adb test/
```

Only THEN can you edit the test body. Without these files, `redo test` fails with "Cannot find template files". The test directory has NO `.all_path` file -- it uses `env.py` only (`from environments import test`).

### Ada Elaboration / Binding Step

Assembly main executables require an elaboration step (adainit/adafinal). This is handled automatically by `redo` via `gnatbind` during the link phase. If you see "undefined reference to adainit", it means:
1. The main procedure is missing `pragma Ada_Main` or the GPR Main attribute is wrong
2. The bind step was skipped (corrupted redo state -- fix with `redo clean_all`)
3. For standalone encapsulated libraries (FFI), GNAT handles adainit/adafinal automatically when using relocatable (shared) mode

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

# Core type buffer sizes (bytes) -- size to fit largest instance in system
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
```ada

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
```yaml

## Compiler & Linker Flags

Key flags (from `a_adamant.gpr`): `-gnat2022 -gnatwa -gnatf` (Ada 2022, all warnings, full errors).
Style: `-gnaty3aABbdDefhiklL12nOprStux` (see adamant-style skill for full flag reference).
Linux_Test: no Ravenscar, links AUnit. Bareboard: Ravenscar enforced, dead code elimination.
Full flag details: [references/build-commands.md](references/build-commands.md)

## SPARK Prove

`redo prove` runs GNATprove. See `adamant-formal-verification` skill for full SPARK/prove workflow, `all.prove.yaml` configuration, and contract patterns.

## Cross-Compilation Targets

### Available Targets (from `redo/targets/`)

| Target Class | Path Files | Arch | Description |
|-------------|-----------|------|-------------|
| `Linux` (default) | `.all_path`, `.Linux_path`, `.64bit_path` | x86-64 | Alias for Linux_Debug |
| `Linux_Debug` | same | x86-64 | -O0, debug, Ravenscar, validity checks |
| `Linux_Test` | `.all_path`, `.Linux_path`, `.64bit_path` | x86-64 | Debug without Ravenscar, links AUnit |
| `Linux_Coverage` | same as Test | x86-64 | Test + gcov flags |
| `Linux_Prove` | same as Debug | x86-64 | For GNATprove SPARK analysis |
| `Linux_Analyze` | same as Debug | x86-64 | GNAT SAS deep mode |
| ARM bare board | `.all_path`, `.bb_path`, `.32bit_path` | ARM (arm-eabi) | For Cortex-M, etc. |
| RISC-V bare board | `.all_path`, `.bb_path`, `.32bit_path` | RISC-V (riscv32-elf) | For RISC-V MCUs |

**Note on bare-board targets:** `arm_bare_board` and `riscv_bare_board` are base classes in `redo/targets/`. Projects define concrete targets by subclassing them (e.g., `class Pico(riscv_bare_board)` or `class STM32(arm_bare_board)`). Set `TARGET` to the concrete class name, not the base. Check your project's `redo/targets/` for available concrete targets.

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
- **Full** (Jorvik) -- default, full tasking
- **SFP** (Small Footprint) -- reduced runtime
- **ZFP** (Zero Footprint) -- bare metal, no runtime

## Common Build Errors

| Error | Fix |
|-------|-----|
| `No target test.elf` | Missing `test.adb` in test directory |
| `duplicate file name` | Filenames must be globally unique across all `.path` dirs |
| Model cache stale | `redo clear_cache` then rebuild (see escalation below) |
| `redo coverage` shows 0% or stamp mismatch | Stale gcov data; `redo clean` in test dir, then re-run `redo coverage` |
| Ravenscar violations in tests | Use `env.py` (selects Linux_Test target, not Linux) |

### Model Cache Troubleshooting Escalation

If `redo clear_cache` + rebuild doesn't fix stale generated output:

1. **Check for file overrides**: A hand-written file in the source directory overrides generated output in `build/src/`. Run `find . -name "the_file.ads" -not -path "*/build/*"` -- if found outside `build/`, that's your stale copy.
2. **Clean + clear + rebuild**: `redo clean` then `redo clear_cache` then `redo all` (in that order -- clean removes old `.o` files that redo's dep tracking might skip).
3. **Check `$ADAMANT_TMP_DIR`**: Multiple environments may use different temp dirs. Verify: `echo $ADAMANT_TMP_DIR`.
4. **Full clean**: `redo clean_all` on both adamant and project directories.
5. **Fresh Docker volumes**: `adamant_env.sh remove` + `start` as last resort.

More errors and project structure: [references/build-commands.md](references/build-commands.md)

## References
- [references/build-commands.md](references/build-commands.md) -- All redo targets and build commands
- [references/build-system-audit.md](references/build-system-audit.md) -- Undocumented targets and audit findings
- [references/internals-and-generation.md](references/internals-and-generation.md) -- Code generation internals, template database, generator architecture
- **SPARK prove**: See `adamant-formal-verification` skill (supersedes spark-prove-guide.md)

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Type system**: [adamant-type-system](../adamant-type-system/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
