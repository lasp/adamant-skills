# Build System Internals & Code Generation Details

## Code Generation Pipeline

```
YAML Model -> Schema Validation -> Python Model Object -> Jinja2 Template -> Generated Ada/HTML/LaTeX/Python
```

- `gen/schemas/` — PyKwalify YAML validation schemas
- `gen/models/` — Python classes that ingest validated YAML
- `gen/generators/` — Generator classes pairing models with templates
- `gen/templates/` — Jinja2 templates organized by type

## Generated Output Counts (per YAML model type)

| Model Type | Templates | Key Outputs |
|-----------|-----------|-------------|
| Component | 22 | Ada source, LaTeX docs |
| Assembly | 37 | Ada, HTML, Python, MATLAB, XML, COSMOS |
| Record/Array/Enum | 36 | Ada (pack/unpack/validate/assert/C), Python, MATLAB, LaTeX |
| Commands/Events/etc | 23 | Ada suites, HTML, LaTeX |
| Memory/Register Map | 6 | Ada (SPARK-validated), HTML, LaTeX |
| Tests | 9 | AUnit runner, tester, reciprocal |

## Exact Generated Files

**component.yaml** → `build/src/component-{name}.ads/.adb` (base class), `build/template/component-{name}-implementation.ads/.adb` (impl stubs)

**events.yaml** → `build/src/{name}_events.ads/.adb`, `{name}_events-representation.ads/.adb`, `build/html/{name}_events.html`

**commands.yaml** → `build/src/{name}_commands.ads/.adb`, `build/html/{name}_commands.html`

**data_products.yaml** → `build/src/{name}_data_products.ads/.adb`, `{name}_data_products-representation.ads/.adb`, `build/html/{name}_data_products.html`

**record.yaml** (e.g. `quaternion.record.yaml`) → `build/src/`:
- `quaternion.ads/.adb` — packed type with T, U, Pack/Unpack, serialization
- `quaternion-representation.ads/.adb` — string representation
- `quaternion-validation.ads/.adb` — field range validation
- `quaternion-assertion.ads/.adb` — test assertions
- `quaternion-c.ads/.adb` — C bindings
- Also: `build/py/`, `build/m/`, `build/html/`, `build/tex/`, `build/pdf/`, `build/yaml/`

**enums.yaml** → `build/src/{name}.ads`, `{name}-representation.ads/.adb`, `{name}-assertion.ads/.adb`, `build/py/`, `build/html/`

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

`redo clear_cache` clears the model cache.

## Override Protection

Generated files in `build/src/` can be overridden by same-named files in the source directory. Generator checks for existing files before writing.

## Build Path Order

Later paths take precedence. Project paths override framework paths.

## Compilation Modes

| Mode | Optimization | Debug | Checks | Notes |
|------|-------------|-------|--------|-------|
| Production | Yes | No | Validity off | |
| Development | -O0 -g | Yes | -gnatVd | Default |
| Debug | -O0 -g -gnata | Yes | -gnatVa, Initialize_Scalars | |
| Test | Debug + coverage | Yes | All | |

Ada runtime modes: **Full** (Jorvik, default), **SFP** (small-footprint), **ZFP** (zero-footprint, bare metal).

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
