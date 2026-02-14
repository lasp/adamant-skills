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

Validation: `bash scripts/check_build_paths.sh <project_root>`

### Environment Variables
```bash
export TARGET=Linux                    # Default target
export ADAMANT_CONFIGURATION_YAML=/path/to/project.configuration.yaml
export EXTRA_BUILD_PATH="/extra"       # Add to computed path
export EXTRA_BUILD_ROOTS="/root"       # Add roots scanned for .path files
```

Default BUILD_ROOTS: Adamant repo root + project root (found via `.git`).
File names must be unique across entire build path.

## Redo Commands

```bash
# Build
redo templates          # Generate stubs
redo all                # Build everything
redo -j                 # Parallel build
redo run                # Build and run

# Test & Verify
redo test               # Unit tests (from test/ dir)
redo test_all           # Recursive tests
redo prove              # SPARK proof (needs all.prove.yaml)
redo coverage           # Coverage (rm -rf build first!)

# Docs & Diagrams
redo build/svg/name.svg              # Diagram
redo build/html/name.html            # HTML docs

# Maintenance
redo clean              # Remove build/
redo clear_cache        # Clear model cache
```

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

`adamant.configuration.yaml`:
```yaml
data_product_buffer_size: 100
command_buffer_size: 100
event_buffer_size: 100
parameter_buffer_size: 100
packet_buffer_size: 500
```

## Internals

Details: [references/internals-and-generation.md](references/internals-and-generation.md)

Pipeline: YAML → schema validation → Python model → Jinja2 template → generated output.
Generated files in `build/src/` can be overridden by same-named source files.
Later build paths take precedence (project overrides framework).
