# Build System Internals & Code Generation Details

Core pipeline, generated output tables, and compilation modes are in SKILL.md. This file has internal details.

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
