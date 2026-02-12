---
name: adamant-build-system
description: Understanding and using the Adamant redo-based build system and code generation framework
---

# Adamant Build System and Code Generation

Redo-based build system: YAML models -> Python/Jinja2 code generation -> Ada compilation, with incremental dependency tracking and multi-target cross-compilation.

## Code Generation Pipeline

```
YAML Model -> Schema Validation -> Python Model Object -> Jinja2 Template -> Generated Ada/HTML/LaTeX/Python
```

- `gen/schemas/` -- PyKwalify YAML validation schemas
- `gen/models/` -- Python classes that ingest validated YAML (component.py, assembly.py, record.py)
- `gen/generators/` -- Generator classes pairing models with templates
- `gen/templates/` -- Jinja2 templates organized by type (component/, record/, assembly/)

One YAML model generates many outputs (Ada specs, HTML docs, LaTeX, Python ground classes, SVG diagrams, COSMOS config).

## YAML Model File Extensions

```
*.component.yaml       *.assembly.yaml        *.record.yaml          *.array.yaml
*.commands.yaml        *.events.yaml          *.data_products.yaml   *.data_dependencies.yaml
*.parameters.yaml      *.faults.yaml          *.packets.yaml         *.tests.yaml
*.view.yaml            *.register_map.yaml    *.memory_map.yaml      *.requirements.yaml
```

## Build Path System

Empty marker files control what is visible to compilation:
- `.all_path` -- include for all targets
- `.Linux_path` / `.Pico_path` / `.<target>_path` -- target-specific

```
project/
├── .all_path
├── src/components/
│   ├── counter/.all_path              # All targets
│   └── adc_collector/.Pico_path       # Pico only
└── src/assembly/
    ├── linux/.Linux_path
    └── pico/.Pico_path
```

### Environment Variables
```bash
export TARGET=Linux                    # Select target (default)
export BUILD_PATH="/path1:/path2"      # Override computed path
export EXTRA_BUILD_PATH="/extra"       # Add to computed path
export EXTRA_BUILD_ROOTS="/root"       # Add roots scanned for .path files
export REMOVE_BUILD_PATH="/path"       # Exclude from path
export ADAMANT_CONFIGURATION_YAML=/path/to/project.configuration.yaml
```

Default BUILD_ROOTS: Adamant repo root + current project root (found via `.git`).
File names must be unique across entire build path -- duplicates cause ambiguous linking.

### Compilation Modes
Set via TARGET: `Linux` (Development), `Linux_Test` (Test + coverage-ready), `Pico` (Production).
- **Production**: optimized, no debug, validity checking off
- **Development**: `-O0 -g`, RM validity checks (`-gnatVd`)
- **Debug**: `-O0 -g -gnata`, all validity checks (`-gnatVa`), Initialize_Scalars
- **Test**: Debug + coverage instrumentation
- **Coverage**: Test mode with gcovr reporting

Ada runtime modes: **Full** (Jorvik profile, default), **SFP** (small-footprint), **ZFP** (zero-footprint, bare metal).

## Redo Commands

### Discovery
```bash
redo what               # Available targets in current directory
redo what_predefined    # All predefined commands
redo path               # Current build path (machine-readable)
redo print_path         # Human-readable build path
redo targets            # Available build targets
```

### Build
```bash
redo templates          # Generate implementation template stubs
redo all                # Build everything in current directory
redo -j                 # Parallel build (all cores)
redo run                # Build and run (requires main.adb)
```

### Test and Verify
```bash
redo test               # Unit tests -- run from test/ subdirectory, NOT component root
redo test_all           # Recursive tests (run from any directory, descends into all test/ dirs)
redo prove              # SPARK proof (requires all.prove.yaml in component dir)
redo prove_all          # Recursive SPARK proof (only processes dirs with all.prove.yaml)
redo analyze            # Static analysis (CodePeer/GNATSAS)
redo analyze_all        # Recursive analysis
redo coverage           # Coverage (sets coverage target automatically)
redo coverage_all       # Recursive coverage
redo style              # Code style (gnatpp)
redo style_all          # Recursive style
```

### Documentation and Diagrams
```bash
redo build/svg/name.svg              # Component/assembly diagram
redo build/html/name.html            # HTML documentation
redo publish                         # Build all docs
```

### Ground Interface Generation
```bash
redo build/cosmos/assembly_commands.txt   # COSMOS command definitions
redo build/cosmos/assembly_telemetry.txt  # COSMOS telemetry definitions
redo build/py/component_name.py           # Python ground class
redo build/py/assembly_name.py            # Python assembly interface
redo build/m/component_name.m             # MATLAB interface
redo build/xml/assembly_name.xml          # System interface document
```

### SPARK Prove Configuration

`all.prove.yaml` in a component/package directory configures `redo prove`:
```yaml
description: GNATprove configuration
level: 2          # 0-4, default 2. Levels set prover/timeout/memlimit:
                  #   0: cvc4 only, 1s timeout
                  #   1: cvc4+z3+altergo, 1s
                  #   2: cvc4+z3+altergo, 5s, counterexamples on
                  #   3: same, 20s, 2GB memlimit
                  #   4: same, 60s, 2GB memlimit
mode: "gold"      # check|check_all|flow|prove|all|stone|bronze|silver|gold (default: gold)
```

Override via environment: `PROVE_SWITCHES="--level=4 --timeout=30" redo prove`

### Maintenance
```bash
redo clean              # Remove build/ directories
redo clean_all          # Recursive clean
redo clear_cache        # Clear build system cache
```

## Target Cross-Compilation

```bash
export TARGET=Linux     # Native (default)
export TARGET=Pico      # Raspberry Pi Pico
redo build/bin/$TARGET/main.elf
```

Target-specific body selection via build path:
```
hardware_action.ads              # Shared spec (.all_path)
linux/hardware_action.adb        # Dev no-op (.Linux_path)
pico/hardware_action.adb         # Real hardware (.Pico_path)
```

## Adamant Configuration

`adamant.configuration.yaml` (or project-specific via `ADAMANT_CONFIGURATION_YAML` env var) sets system-wide buffer sizes:
```yaml
description: Project configuration
data_product_buffer_size: 100         # All buffer sizes are REQUIRED
command_buffer_size: 100
event_buffer_size: 100
parameter_buffer_size: 100
packet_buffer_size: 500
ccsds_packet_buffer_size: 500
stack_margin: 100                     # Stack margin bytes (bareboard only; Linux uses 12KB fixed)
```

Values are accessible in both source code and YAML models. Schema allows additional key-value pairs.

## Build System Internals

### Override Protection
Generated files in `build/src/` can be overridden by hand-written files in the source directory. The generator checks for existing files before writing -- place a file with the same name in the component directory to override any generated output.

### Generated Output Counts (per YAML model type)

| Model Type | Templates | Key Outputs |
|-----------|-----------|-------------|
| Component | 22 | Ada source, LaTeX docs |
| Assembly | 37 | Ada, HTML, Python, MATLAB, XML, COSMOS |
| Record/Array/Enum | 36 | Ada (pack/unpack/validate/assert/C), Python, MATLAB, LaTeX |
| Commands/Events/etc | 23 | Ada suites, HTML, LaTeX |
| Memory/Register Map | 6 | Ada (SPARK-validated), HTML, LaTeX |
| Tests | 9 | AUnit runner, tester, reciprocal |
| Configuration | 1 | Ada configuration.ads |

Output directories: `.ads/.adb` -> `build/src/`, `*-implementation*` -> `build/template/`, `.tex` -> `doc/build/tex/`, other -> `build/<ext>/`.

### Exact Generated Files (per YAML model type)

**component.yaml** -> `build/src/component-{name}.ads/.adb` (base class), `build/template/component-{name}-implementation.ads/.adb` (impl stubs)

**events.yaml** -> `build/src/{name}_events.ads/.adb`, `{name}_events-representation.ads/.adb`, `build/html/{name}_events.html`

**commands.yaml** -> `build/src/{name}_commands.ads/.adb`, `build/html/{name}_commands.html`

**data_products.yaml** -> `build/src/{name}_data_products.ads/.adb`, `{name}_data_products-representation.ads/.adb`, `build/html/{name}_data_products.html`

**data_dependencies.yaml** -> `build/src/{name}_data_dependencies.ads/.adb`, `build/html/{name}_data_dependencies.html`

**record.yaml** (e.g. `quaternion.record.yaml`) -> `build/src/`:
- `quaternion.ads/.adb` -- packed type with T, U, Pack/Unpack, serialization
- `quaternion-representation.ads/.adb` -- string representation
- `quaternion-validation.ads/.adb` -- field range validation
- `quaternion-assertion.ads/.adb` -- test assertions
- `quaternion-c.ads/.adb` -- C bindings (U_C type, To_C/To_Ada)
- `quaternion_type_ranges.adb` -- type range extraction binary
- Also: `build/py/quaternion.py`, `build/m/Quaternion.m`, `build/html/quaternion.html`, `build/tex/quaternion.tex`, `build/pdf/quaternion.pdf`, `build/yaml/quaternion.type_ranges.yaml`

**enums.yaml** -> `build/src/{name}.ads`, `{name}-representation.ads/.adb`, `{name}-assertion.ads/.adb`, `build/py/{name}.py`, `build/html/{name}.html`

**Component-level non-src outputs**: `build/dot/{name}.dot`, `build/svg/{name}.svg`, `build/png/{name}.png`, `build/eps/{name}.eps`

Memory/register map generators uniquely run GNATprove on generated Ada code to validate SPARK compliance before outputting.

### Generator Database
Each generated output maps to exactly one generator class. The dispatch in `default.do` routes:
- Files in `build/` -> `build_via_generator` (dynamically loads generator by output path)
- Named targets (`all`, `test`, `prove`, etc.) -> specific rule classes
- `.type_ranges.yaml` -> `build_type_ranges_yaml`
- `_h.ads`, `_hpp.ads` -> `build_bindings` (C/C++ header to Ada spec)

### Build Path Order
Later paths take precedence for same-named files. Project paths override framework paths. This enables project-specific customization of framework components.

### Session Database
Build sessions use SQLite databases in `~/.adamant/tmp/{session_id}/`:
- **generator_database**: output file -> generator class + input file
- **source_database**: Ada package name -> source files + model YAML
- **redo_target_database**: directory -> buildable targets

`redo clear_cache` clears the model cache (SQLite-based, prevents redundant YAML processing).

## Test Environment Configuration

### Test Directory Setup

Test directories REQUIRE:
1. `env.py` with `from environments import test` (provides AUnit paths)
2. `component_name.tests.yaml` (test definitions)
3. **NO `.all_path` file** -- test directories must NOT have `.all_path` (causes duplicate test.adb conflicts across components)

```python
# test/env.py -- MINIMUM required content:
from environments import test  # noqa: F401
```

Additional environment setup:
```python
import os
os.environ['EXTRA_BUILD_PATH'] = '/path/to/test/dependencies'
```

## C/C++ Algorithm Library Integration

For external algorithm libraries (e.g., fp32-fsw-xmera GNC algorithms with Eigen):

### Ada Binding Generation

GCC `-fdump-ada-spec` auto-generates `.ads` from C headers. The CMake `generate_ada_spec` macro:
```cmake
add_custom_command(
  OUTPUT "${BINDINGS_DIR}/${name}Algorithm_c.ads"
  COMMAND ${CMAKE_CXX_COMPILER} -c -fdump-ada-spec -C
          "${SOURCE_DIR}/algorithms/${name}/${name}Algorithm_c.h"
          -I${SOURCE_DIR} -DEIGEN_FREESTANDING=1
)
```

Build and copy bindings:
```bash
cmake -DGENERATE_ADA_BINDINGS=ON -DCMAKE_BUILD_TYPE=Release ..
make
cp build/bindings/*.ads ../adamant_project/src/components/wrapper/
```

### Linking in GPR

```ada
package Linker is
   for Switches ("Ada") use ... &
      "-L/path/to/lib" & "-lstdc++" & "-lgncAlgorithms";
end Linker;
```

For Eigen-based algorithms, build the external library with `-DEIGEN_FREESTANDING=1` using the LASP Eigen fork (`feature/freestanding-gcc15` branch). RISC-V target: `rv32imaf_zicsr` / `ilp32f` ABI / freestanding C++23.
