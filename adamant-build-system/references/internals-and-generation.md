<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Build System Internals & Code Generation Details

Core pipeline, generated output tables, and compilation modes are in SKILL.md. This file has internal details.

## Python Model Object Identity -- Critical Pitfall

**See `adamant-framework-internals` skill for full details.** Summary: `base.__eq__` compares by `full_filename`, not Python identity. All instances of the same component type compare equal under `==`. Always use `is` for instance comparisons in model code.

## Generator Database & Dispatch

Each generated output maps to one generator class. `default.do` routes:
- `build/` files -> `build_via_generator` (dynamic load by output path)
- Named targets (`all`, `test`, `prove`) -> specific rule classes
- `.type_ranges.yaml` -> `build_type_ranges_yaml`
- `_h.ads`, `_hpp.ads` -> `build_bindings` (C/C++ header -> Ada spec)

## Session Database

Build sessions use SQLite in `~/.adamant/tmp/{session_id}/`:
- **generator_database**: output -> generator class + input
- **source_database**: Ada package -> source files + model YAML
- **redo_target_database**: directory -> buildable targets

## C/C++ Algorithm Library Integration

GCC `-fdump-ada-spec` auto-generates `.ads` from C headers:
```cmake
add_custom_command(
  OUTPUT "${BINDINGS_DIR}/${name}Algorithm_c.ads"
  COMMAND ${CMAKE_CXX_COMPILER} -c -fdump-ada-spec -C "${SOURCE_DIR}/${name}Algorithm_c.h"
)
```

Link in GPR:
```ada
package Linker is
   for Switches ("Ada") use ... & "-L/path/to/lib" & "-lstdc++" & "-lgncAlgorithms";
end Linker;
```

## Build Path Resolution

The `.all_path` and `.all_path.Linux` etc. markers work via directory scanning:

1. Build system scans all directories in BUILD_ROOTS
2. Each directory with `.all_path` is included for ALL targets
3. Each directory with `.all_path.Linux` (or `.all_path.Pico`, etc.) is included only for that target
4. Test directories use `env.py` instead (sets `from environments import test`)
5. Assembly main directories use `env.py` with `from environments import main` or `from environments import linux` etc.

### Directory inclusion rules:
- Component source: `src/components/name/` -> `.all_path`
- Type definitions: `src/types/name/` -> `.all_path`
- Test directories: `src/components/name/test/` -> `env.py` ONLY, NO `.all_path`
- Assembly main: `main/` or `main/linux/` -> `env.py` with target environment
- Assembly wiring: `assembly/` -> `.all_path`

## Generated File Layout

For a component `my_component` with YAML model:

```
src/components/my_component/
  my_component.component.yaml     # Input model
  my_component.commands.yaml      # Optional
  my_component.events.yaml        # Optional
  my_component.data_products.yaml # Optional
  my_component.parameters.yaml    # Optional
  my_component.faults.yaml        # Optional
  component-my_component-implementation.ads  # Hand-written spec
  component-my_component-implementation.adb  # Hand-written body
  build/src/                      # GENERATED (never edit)
    component-my_component.ads    # Base class spec
    component-my_component.adb    # Base class body
    my_component_commands.ads     # Command IDs + types
    my_component_commands.adb     # Command package body
    my_component_events.ads       # Event constructors
    my_component_events.adb       # Event package body
    my_component_data_products.ads
    my_component_data_products.adb
    my_component_parameters.ads
    my_component_parameters.adb
    my_component_faults.ads
    my_component_faults.adb

  test/
    env.py                        # Test environment (from environments import test)
    my_component.tests.yaml       # Test list
    my_component_tests-implementation.ads   # Hand-written test spec
    my_component_tests-implementation.adb   # Hand-written test body
    component-my_component-implementation-tester.ads  # Hand-written tester spec
    component-my_component-implementation-tester.adb  # Hand-written tester body
    build/
      src/                        # GENERATED test infrastructure
        component-my_component_reciprocal.ads  # Generated tester reciprocal
        component-my_component_reciprocal.adb
        my_component_tests.ads    # Generated test suite
        my_component_tests-implementation-suite.adb
      template/                   # GENERATED templates (copy to test/ for initial setup)
        my_component_tests-implementation.ads
        my_component_tests-implementation.adb
        component-my_component-implementation-tester.ads
        component-my_component-implementation-tester.adb
```

## Configuration YAML Processing

The `configuration.yaml` in each project sets buffer sizes, stack margins, and other system-wide parameters:

```yaml
# Processed at code gen time. Changes require redo clean + rebuild.
data_products:
  max_data_product_size_bytes: 256
events:
  max_event_param_size_bytes: 64
commands:
  max_command_arg_size_bytes: 256
packets:
  max_packet_size_bytes: 1024
task_monitoring:
  max_active_components: 50
  stack_margin_bytes: 2048
```

These values size the framework's generic buffer types and affect the generated `Configuration` package.

## Build Targets Reference

| Target | From | Does |
|--------|------|------|
| `redo all` | Any dir with `.all_path` or `env.py` | Build all targets in this dir |
| `redo test` | test/ dir | Build + run tests |
| `redo coverage` | test/ dir | Build with gcov + run + gcovr report |
| `redo prove` | Any dir | Run GNATprove on SPARK-annotated files |
| `redo templates` | test/ dir | Regenerate tester template stubs |
| `redo style` | Any dir | Check Ada/YAML/Python style |
| `redo style_all` | project root | Style check entire project tree |
| `redo clean` | Any dir | Remove build artifacts in this dir |
| `redo clean_all` | project root | Clean entire project tree |
| `redo clear_cache` | project root | Clear model caching SQLite DB |
| `redo cosmos_config` | assembly/main/ | Generate COSMOS plugin config |
