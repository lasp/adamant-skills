<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Build System Internals & Code Generation Details

Core pipeline, generated output tables, and compilation modes are in SKILL.md.

## Python Model Object Identity -- Critical Pitfall

**See `adamant-framework-internals` skill for full details.** `base.__eq__` compares by `full_filename`, not Python identity. All instances of the same component type compare equal under `==`. Always use `is` for instance comparisons.

## Generator Database & Dispatch

Each generated output maps to one generator class. `default.do` routes:
- `build/` files → `build_via_generator` (dynamic load by output path)
- Named targets (`all`, `test`, `prove`) → specific rule classes
- `.type_ranges.yaml` → `build_type_ranges_yaml`
- `_h.ads`, `_hpp.ads` → `build_bindings` (C/C++ header → Ada spec)

## Session Database

Build sessions use SQLite in `~/.adamant/tmp/{session_id}/`:
- **generator_database**: output → generator class + input
- **source_database**: Ada package → source files + model YAML
- **redo_target_database**: directory → buildable targets

## C/C++ Algorithm Library Integration

GCC `-fdump-ada-spec` auto-generates `.ads` from C headers. Link via GPR `Linker` package with `-L/path/to/lib -lstdc++ -l<lib>`. See `adamant-algorithm-wrapping` skill for full pipeline.

## Build Path Resolution Details

Marker files and directory inclusion rules:
- Component/type source dirs: `.all_path`
- Test directories: `env.py` only (`from environments import test`), NO `.all_path`
- Assembly main dirs: `env.py` with target environment (`from environments import main`/`linux`)
- Assembly wiring dirs: `.all_path`

## Generated File Layout

For component `my_component`:
```
src/components/my_component/
  *.component.yaml, *.commands.yaml, etc.   # Input models
  component-my_component-implementation.ads/.adb  # Hand-written
  build/src/                                # GENERATED (never edit)
    component-my_component.ads/.adb         # Base class
    my_component_commands.ads/.adb           # Per-feature packages
    my_component_events.ads/.adb
    my_component_data_products.ads/.adb
    my_component_parameters.ads/.adb
    my_component_faults.ads/.adb
  test/
    env.py                                  # Test environment
    *.tests.yaml                            # Test list
    *-implementation.ads/.adb               # Hand-written test + tester
    build/src/                              # Generated test infra
    build/template/                         # Generated stubs (copy to test/)
```
