---
name: adamant-framework-internals
description: Deep-dive into Adamant framework internals for debugging code generation bugs, model lifecycle issues, and assembly load problems
---

# Adamant Framework Internals

Use this skill when debugging code generation misbehavior, fixing bugs in framework Python models, or understanding the assembly loading lifecycle. Not needed for normal component or assembly development.

## Key Framework Files

All paths relative to `$ADAMANT_DIR` (the `adamant/` repo root).

### Core Model Infrastructure

| File | Role |
|------|------|
| `gen/models/base.py` | Base class for all model objects. Defines `__eq__`, `__hash__`, `__new__`, caching, `full_filename`, `get_dependencies()` |
| `gen/models/assembly.py` | Assembly model: loads components, wires connections, calls `set_assembly()` per instance, generates IDs |
| `gen/models/component.py` (`component`) | Component model: reads `*.component.yaml`, manages submodels via `set_component_instance_data`, handles per-instance mutation |
| `gen/models/component.py` (`component_submodel`) | Base class for all component submodels (packets, events, commands, etc.): `load_component()`, `set_component()`, `set_assembly()`, `final()` |
| `gen/models/packets.py` | Generic packet suite model (base class for custom packet models) |
| `redo/database/model_cache_database.py` | SQLite pickle cache: `store_model` (pickle.dumps), `get_model` (pickle.loads), session ID tracking via `ADAMANT_SESSION_ID` |
| `redo/util/model_loader.py` | `try_load_model_by_name()`, `load_model()`, `get_model_file_path()` -- path resolution via model_database scanning BUILD_ROOTS |

### Component-Specific Model Overrides

When a component ships its own `gen/models/` directory, those Python files override the generic framework models for that component's YAML files. The build path uniqueness rule applies: the first match wins; project overrides framework.

To find all custom model overrides in the codebase:
```bash
find $ADAMANT_DIR/src -name "*.py" -path "*/gen/models/*"
```

**Three override patterns exist:**

1. **Submodel override** (~15 files): Inherits from `packets`, `commands`, `data_products`, or `faults`. Overrides `set_assembly()` to resolve per-instance types from assembly state. May also override `set_component()` or `final()`.

2. **Custom data structure** (~6 files): Defines standalone classes (e.g., routing tables, parameter tables, product packets) without inheriting standard submodels. Loaded by other overrides, not directly by the framework.

3. **Multi-method override**: Some overrides need both `set_component()` (for component-scope data) and `set_assembly()` (for assembly-scope data). Example: `task_watchdog_faults.py`.

## Python Model Object Identity -- Critical Pitfall

The base model class (`gen/models/base.py`) defines a custom `__eq__` that compares by **filename**, not by Python object identity:

```python
def __eq__(self, other):
    return self and other and self.full_filename == other.full_filename
```

`__hash__` also uses `full_filename`. All instances of the same component type compare as equal under `==` and hash identically.

**Rule:** Always use `is` (Python identity operator) when comparing component model objects that should represent specific assembly instances:

```python
# WRONG -- True for ALL Parameter_Store instances:
conn.to_component == self.component

# CORRECT -- True only for this specific instance:
conn.to_component is self.component
```

### Why `is` Works: Pickle Memo Preservation

The SQLite cache always returns fresh Python objects via `pickle.loads`. There is no in-memory object cache -- the session ID check only skips timestamp validation, not deserialization.

Object identity (`is`) is preserved **within a single pickle graph**: a component and all its submodels are pickled together. After unpickling, `submodel.component` is the exact same Python object as the component returned by `load_component()`, because pickle's memo table preserves circular references.

Connection `to_component`/`from_component` references are set by looking up `assembly.components[instance_name]` -- the same dictionary that holds the component objects. So `conn.to_component is assembly.components[name]` is always true for resolved connections.

### Additional base.py Methods for Debugging

- `get_dependencies()` -- returns model dependency list; useful for understanding cache invalidation
- `save_to_cache()` -- shows when models get stored
- `__repr__()` / `__str__()` -- shows basename in debug output
- `warning()` / `warn()` -- model-specific error reporting

## Connection Model

Connections are defined in `assembly.py` as `connection` objects:

```python
class connection(object):
    def __init__(self, filename, data):
        self.connected = False   # Set True after successful connect()
        self.ignored = False     # Set True for "ignore" connections
```

After `connect(components)` resolves the connection:
- `from_component` / `to_component` -- Python object references into `assembly.components`
- `from_connector` / `to_connector` -- Connector objects from the component
- `from_index` / `to_index` -- Array index (default 1) for arrayed connectors
- `from_name` / `to_name` -- Formatted `"component.connector[index]"` strings
- `name` -- Combined `"from_name-to_name"`
- `description` -- Optional connection description from YAML

**Connection resolution**: `connect()` extracts component/connector names from YAML data, looks up objects in the `components` dict, calls `from_connector.connect_to()` for bidirectional linking, then sets `connected = True`.

**Subassembly connections**: Already `connected` when merged into parent assembly. Their `to_component` references point to the same Python objects as `assembly.components[name]` because subassembly components are grafted by direct reference (not copied).

## Assembly Load Sequence

1. **`super().load()`** -- deserializes component instances and raw connections from YAML/cache.

2. **Subassemblies loaded recursively** -- with `is_subassembly=True` (suppresses `set_assembly()`). Components and connections grafted into parent by direct reference. Duplicate instance names across subassemblies are validated.

3. **`connection.connect(self.components)`** -- for unconnected, non-ignored connections only. Resolves YAML stubs into live Python object references.

4. **`set_component_instance_data(instance_name, data)`** -- mutates each component in-place: sets `instance_name`, applies parameter overrides, resolves generic types for connectors, calculates queue sizes, handles task instance data.

5. **`component.set_assembly(assembly)`** -- iterates `assembly.components.values()`, calling `set_assembly` which propagates to all submodels. Assembly submodels also get `set_assembly()`. Connections are fully resolved at this point.

6. **Component categorization** -- populates `component_kind_dict` (active/passive/queued/init/commands/etc.), assigns task priorities and ranks, gathers generic type includes.

7. **`_generate_component_ids()`** -- assigns unique IDs to all events, commands, data products, parameters, and faults across all components. Only runs when `not shallow_load`.

8. **`_load_complex_types()`** -- builds dependency-ordered type dictionaries from component `complex_types`.

9. **`final()`** -- post-processing hooks. Called on assembly, then per-component, then per-submodel. Use for logic that needs IDs (prefer `set_assembly()` when IDs aren't needed).

**Key insight:** By step 5, `assembly.connections` is fully populated and object identity is stable. Custom `set_assembly()` implementations can safely trace the connection graph using `is`. IDs are NOT available until step 7.

## Model Loader

`try_load_model_by_name(name, model_types)` resolves a model name to a file path via `model_database` (built by scanning BUILD_ROOTS), then calls `load_model()` which imports the Python class from the file extension and instantiates it.

`get_model_file_path(name, model_types)` returns a single path or None; errors if multiple matches found. Used in custom overrides to resolve dependent model paths. Always call `redo.redo_ifchange(path)` after resolving to declare a build dependency.

## Custom `set_assembly()` Pattern

Two common patterns in custom overrides:

### Pattern 1: Connection Tracing (per-instance resolution)

When a component needs to resolve types from connected peers:

```python
class my_component_packets(packets):
    def submodel_name(self):
        return "packets"

    def set_assembly(self, assembly):
        self.assembly = assembly
        for conn in self.assembly.connections:
            if (
                conn.to_component is self.component   # THIS instance (use 'is')
                and conn.to_connector.name == "Expected_Connector"
            ):
                peer = conn.from_component
                # Use peer to resolve types...
                break
        super(my_component_packets, self).set_assembly(assembly)
```

### Pattern 2: Init Parameter Resolution (type lookup)

When a component resolves types from its own init parameters (e.g., `parameters_packets.py`):

```python
class my_component_packets(packets):
    def submodel_name(self):
        return "packets"

    def set_assembly(self, assembly):
        self.assembly = assembly
        for key, pkt in self.entities.items():
            if pkt.name == "Target_Packet":
                # Resolve type from init parameters
                table_ref = self.component.init.get_parameter_value("Table_Config")
                model_path = model_loader.get_model_file_path(table_ref, model_types=[...])
                redo.redo_ifchange(model_path)
                resolved_model = model_loader.load_model(model_path)
                # Replace packet entity with resolved type...
        super(my_component_packets, self).set_assembly(assembly)
```

**Rules for all custom overrides:**
- Place in `src/components/<name>/gen/models/<override>.py`
- Class name must match file name (Python module convention)
- Call `super().set_assembly(assembly)` at the end
- Always use `is` for instance comparisons; never `==`
- Call `redo.redo_ifchange(path)` after resolving model paths (avoids stale cache; beware circular dependencies)

## Debugging Code Generation Bugs

### Symptom Taxonomy

| Symptom | Likely Root Cause |
|---------|-------------------|
| All instances of a type produce same generated output | `==` used instead of `is` in instance comparison |
| Wrong component's data for one assembly instance | Connection trace finds first match, not correct match |
| Wrong type resolved for packet/data product | Init parameter resolution logic error; check `set_assembly()` type lookup |
| `set_assembly` receives stale/incorrect assembly | Subassembly merge order; check `assembly.py` grafting |
| ModelException "could not find X" despite X existing | Wrong connector name, wrong model_types filter, or circular `redo_ifchange` |
| Correct in isolation but wrong in multi-instance case | `__eq__` filename comparison silently matching wrong instance |

### Investigation Workflow

1. **Identify the generator or model** responsible for wrong output. Check `build/src/` for the generated file. Query `generator_database().get_generator(output_filename)` to find the generator module, class, source file, and input YAML.

2. **Find the Python model class**. Look for `gen/models/` in the component's source tree. If absent, the generic framework model applies.

3. **Read `set_assembly()`** in the model class. Two patterns: connection tracing (uses `assembly.connections`) or init parameter resolution (uses `self.component.init`).

4. **For connection-tracing bugs**: Check all `==` comparisons on component objects -- replace with `is`. Verify connector names match component YAML definitions exactly.

5. **For type resolution bugs**: Verify the model name/path being looked up, check `model_types` filter, ensure `redo_ifchange` doesn't create circular dependencies.

6. **Add temporary debug prints** if needed:
   ```python
   import sys
   print(f"[DEBUG] instance={self.component.instance_name}", file=sys.stderr)
   for conn in self.assembly.connections:
       if conn.to_component is self.component:
           print(f"[DEBUG]   {conn.from_component.instance_name} -> {conn.to_connector.name}", file=sys.stderr)
   ```

7. **Always `redo clear_cache`** before testing any model fix. Stale pickled objects mask code changes.

## When NOT to Use This Skill

- Normal component development: use `adamant-component-dev`
- Assembly wiring: use `adamant-assembly-dev`
- Build commands and code gen pipeline overview: use `adamant-build-system`
- Type definitions: use `adamant-type-system`
