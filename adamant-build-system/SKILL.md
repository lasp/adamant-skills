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
*.view.yaml
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
```

Default BUILD_ROOTS: Adamant repo root + current project root (found via `.git`).

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
redo test               # Unit tests (current directory)
redo test_all           # Recursive tests
redo prove              # SPARK proof
redo prove_all          # Recursive SPARK proof
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
level: 1          # Proof effort (0-4)
mode: "silver"    # bronze/silver/gold/platinum
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

## Test Environment Configuration

Test directories can include `env.py` to set environment:
```python
# test/env.py
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
