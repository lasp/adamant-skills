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

Empty marker files control visibility:
- `.all_path` — all targets
- `.Linux_path` / `.Pico_path` — target-specific
- Test dirs use `env.py`, NOT `.all_path`

### Environment Variables
```bash
export TARGET=Linux                    # Default target
export ADAMANT_CONFIGURATION_YAML=/path/to/project.configuration.yaml
export EXTRA_BUILD_PATH="/extra"       # Add to computed path
export EXTRA_BUILD_ROOTS="/root"       # Add roots scanned for .path files
```

Default BUILD_ROOTS: Adamant repo root + project root (found via `.git`).
File names must be unique across entire build path. Later paths take precedence (project overrides framework).

Validation: `bash scripts/check_build_paths.sh <project_root>`

## Redo Commands

```bash
# Build
redo templates          # Generate stubs (copy from build/template/)
redo all                # Build everything in current directory
redo -j                 # Parallel build
redo run                # Build and run (from main/ dir)

# Test & Verify
redo test               # Unit tests (from test/ dir)
redo test_all           # Recursive tests (all subdirectories)
redo style              # Style check (Ada warnings, YAML lint, Python flake8, codespell)
redo style_all          # Recursive style check (all subdirectories)
redo prove              # SPARK proof (needs all.prove.yaml)
redo coverage           # Coverage (redo clean first!)

# Docs & Diagrams
redo build/svg/name.svg              # Architecture/type diagram
redo build/html/name.html            # HTML documentation

# Maintenance
redo clean              # Remove build/ in current directory
redo clean_all          # Recursive clean (all subdirectories)
redo clear_cache        # Clear model cache (SQLite in ~/.adamant/tmp/)
```

## Code Generation Pipeline

```
YAML Model → Schema Validation → Python Model Object → Jinja2 Template → Generated Output
```

- `gen/schemas/` — PyKwalify YAML validation schemas
- `gen/models/` — Python classes that ingest validated YAML
- `gen/templates/` — Jinja2 templates organized by type

Generated files live in `build/src/`. Source files with the same name override generated ones.

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

## SPARK Prove Configuration

Place `all.prove.yaml` in component directory:
```yaml
level: 2          # 0-4 (timeout/prover escalation)
mode: "gold"      # check|flow|prove|all|stone|bronze|silver|gold
```

Override: `PROVE_SWITCHES="--level=4" redo prove`

## Cross-Compilation

```bash
export TARGET=Pico
redo build/bin/Pico/main.elf
```

Target-specific bodies via build path:
```
hardware_action.ads              # Shared spec (.all_path)
linux/hardware_action.adb        # .Linux_path
pico/hardware_action.adb         # .Pico_path
```

## Project Configuration

`project.configuration.yaml`:
```yaml
data_product_buffer_size: 100
command_buffer_size: 100
event_buffer_size: 100
parameter_buffer_size: 100
packet_buffer_size: 500
```

Increase buffer sizes if you get `Storage_Error` at runtime.

## Compilation Modes

| Mode | Optimization | Debug | Checks |
|------|-------------|-------|--------|
| Production | Yes | No | Validity off |
| Development | -O0 -g | Yes | -gnatVd (default) |
| Debug | -O0 -g -gnata | Yes | -gnatVa, Initialize_Scalars |
| Test | Debug + coverage | Yes | All |

Ada runtime modes: **Full** (Jorvik, default), **SFP** (small-footprint), **ZFP** (zero-footprint, bare metal).

## Internals

Details: [references/internals-and-generation.md](references/internals-and-generation.md)

Session database uses SQLite in `~/.adamant/tmp/{session_id}/`. `redo clear_cache` clears the model cache.

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Type system**: [adamant-type-system](../adamant-type-system/SKILL.md)
- **Assembly**: [adamant-assembly-dev](../adamant-assembly-dev/SKILL.md)
