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
| `gen/models/base.py` | Base class for all model objects. Defines `__eq__`, `__new__`, caching, and `full_filename` |
| `gen/models/assembly.py` | Assembly model: loads components, wires connections, calls `set_assembly()` per instance |
| `gen/models/component.py` (`component`) | Component model: reads `*.component.yaml`, manages submodels via `set_component_instance_data`, handles per-instance mutation |
| `gen/models/component.py` (`component_submodel`) | Base class for all component submodels (packets, events, commands, etc.): `load_component()`, `set_component()`, `set_assembly()` base implementations |
| `gen/models/packets.py` | Generic packet suite model (base class for custom packet models) |
| `redo/database/model_cache_database.py` | SQLite pickle cache: `store_model` (pickle.dumps), `get_model` (pickle.loads), session ID tracking via `ADAMANT_SESSION_ID` |
| `redo/util/model_loader.py` | `try_load_model_by_name()`, `load_model()` -- path resolution and model instantiation |

### Component-Specific Model Overrides

When a component ships its own `gen/models/` directory, those Python files override the generic framework models for that component's YAML files. The build path uniqueness rule applies: the first match wins; project overrides framework.

**Critical example:** `src/components/parameters/gen/models/parameters_packets.py` overrides the generic `packets` model for the `Parameters` and `Parameter_Store` components. It runs `set_assembly()` to resolve per-instance packet types from the live assembly connection graph.

To find all custom model overrides in the codebase:
```bash
find $ADAMANT_DIR/src -name "*.py" -path "*/gen/models/*"
```

## Python Model Object Identity -- Critical Pitfall

The base model class (`gen/models/base.py`) defines a custom `__eq__` that compares by **filename**, not by Python object identity:

```python
def __eq__(self, other):
    return self and other and self.full_filename == other.full_filename
```

**Consequence:** All instances of the same component type (e.g., three `Parameter_Store` instances all loaded from `parameter_store.component.yaml`) compare as equal under `==`. This silently causes incorrect behavior in any Python model code that tries to distinguish between multiple instances of the same component type using `==`.

**Rule:** Always use `is` (Python identity operator) when comparing component model objects that should represent specific assembly instances:

```python
# WRONG -- True for ALL Parameter_Store instances, regardless of which one:
conn.to_component == self.component

# CORRECT -- True only for the exact Python object representing this instance:
conn.to_component is self.component
```

This applies to all comparisons in `set_assembly()`, `set_component()`, and any other model code that traverses `assembly.connections` or `assembly.components`.

### Why `is` Works: Model Caching Context

The SQLite model cache (`model_cache_database`) always returns fresh Python objects via `pickle.loads` — this applies to both cache paths:
- **This-session path:** `is_model_cached_this_session` checks `ADAMANT_SESSION_ID` in SQLite. If matched, calls `do_load_from_cache` → `pickle.loads` → fresh object.
- **Cross-session path:** `is_cached_model_up_to_date` checks file timestamps and dependencies, then also calls `do_load_from_cache` → `pickle.loads` → fresh object.

**There is no in-memory Python object cache.** Every call to `load_from_cache` returns a new deserialized object. The session check only avoids re-validating timestamps; it does not return a cached in-memory reference.

Object identity (`is`) is preserved **within a single pickle graph**: a component and all its submodels are pickled together. When unpickled, `pp.component` is the exact same Python object as the component model returned, because pickle's memo table preserves the circular reference. When `set_component_instance_data` mutates `component.instance_name` in-place, the submodel's `self.component` reflects the change immediately — they are the same object.

Connection `to_component`/`from_component` references and submodel `self.component` references are the same Python object when both originate from the same `load_component()` call in the assembly loader. This is why `is` correctly distinguishes instances even when `==` cannot.

## Assembly Load Sequence

Understanding when each callback fires is essential for debugging `set_assembly()` issues.

1. **`subassembly.load()`** -- loads component instances and raw connections for the current YAML file. Each component YAML is deserialized from the SQLite pickle cache.

2. **Named subassemblies loaded recursively** -- with `is_subassembly=True`, which suppresses the `set_assembly()` call. Subassembly components and connections are grafted into the parent `self.components` / `self.connections` dicts by direct reference.

3. **`connection.connect(self.components)` for unconnected connections only** -- resolves connection stubs with `if not connection.connected`: sets live `conn.from_component` / `conn.to_component` Python object references by looking up `self.components[instance_name]`.

   **Subassembly caveat:** Connections defined inside a subassembly are already `connected` when merged into the parent assembly, so the parent's connect pass skips them. Their `conn.to_component` references point to the subassembly-scope component models. Since subassembly components are merged into `assembly.components` by **direct reference** (not copied), `conn.to_component` and `assembly.components[name]` are the same Python object. The `is` operator therefore works correctly even for subassembly connections.

4. **`set_component_instance_data(instance_name, data)`** -- mutates each component model in-place: sets `instance_name`, applies parameter overrides, stamps instance name onto submodels. Each instance is a distinct Python object even though all share the same `full_filename`.

5. **`component.set_assembly(assembly)` per instance** -- iterates `assembly.components.values()`, calling `set_assembly` and propagating to all submodels (packets, events, commands, data products, parameters, faults). `assembly.connections` is fully populated at this point.

6. **`final()`** -- called after ID assignment; post-processing hooks for generators.

**Key insight:** By step 5, `assembly.connections` contains complete wiring information and object identity is stable. Any `set_assembly()` implementation that traces the connection graph using `is` will see correct per-instance results.

## Component Model Lifecycle Per Instance

```
model_loader.try_load_model_by_name(type)  # Returns fresh Python object via pickle.loads
    -> base.__new__() returns cache hit or builds fresh object
    -> base.__init__() skips load() if from_cache=True

set_component_instance_data(instance_name, data)  # Called once per assembly instance
    -> mutates in-place: instance_name, parameter_overrides
    -> stamps submodels with component reference (preserved by pickle memo)

set_assembly(assembly)              # Called after all connections are established
    -> submodels propagate via component.submodels[filename]
    -> custom set_assembly() implementations can query assembly.connections
```

**Pickle memo:** Submodels pickled with a component share the same Python object references after unpickling (pickle memo preserves the object graph). So `self.component` in a submodel's `set_assembly()` is the exact same Python object as the component in `assembly.components`. This is why `is` works: all references to a given instance within a single pickle graph are identical objects.

After `set_component_instance_data`, each component instance is a distinct Python object with its own `instance_name`. The `full_filename` (used by `__eq__`) is identical for all instances of the same type. Only `is` reliably identifies a specific instance.

## Custom `set_assembly()` Pattern

When a component needs assembly-scope information (e.g., resolving packet types from connected components), override `set_assembly()` in the component's `gen/models/` directory:

```python
# src/components/my_component/gen/models/my_component_packets.py
from models.packets import packets, packet
from models.exceptions import ModelException

class my_component_packets(packets):
    def submodel_name(self):
        return "packets"   # Treat as a plain packets submodel

    def set_assembly(self, assembly):
        self.assembly = assembly

        for key, pkt in self.entities.items():
            if pkt.name == "My_Target_Packet":
                # Trace connections using "is" to identify THIS instance
                peer = None
                for conn in self.assembly.connections:
                    if (
                        conn.to_component is self.component   # THIS instance
                        and conn.to_connector.name == "Expected_Connector_Name"
                    ):
                        peer = conn.from_component
                        break

                if peer is None:
                    raise ModelException("Could not find expected peer component.")

                # Use peer to resolve the correct type
                # ...

        super(my_component_packets, self).set_assembly(assembly)
```

**Rules for custom model overrides:**
- Place in `src/components/<name>/gen/models/<override>.py`
- The class name must match the file name (Python module name convention)
- Call `super().set_assembly(assembly)` at the end to invoke the base class chain
- Always use `is` for instance comparisons; never `==`
- Use `model_loader.get_model_file_path(model_name, model_types=[...])` to resolve YAML paths from model names
- Call `redo.redo_ifchange(model_path)` after resolving a model path to declare a build dependency

## Debugging Code Generation Bugs

### Symptom Taxonomy

| Symptom | Likely Root Cause |
|---------|-------------------|
| All instances of a component type produce the same generated output | `==` used instead of `is` in instance comparison |
| Wrong component's data used for one assembly instance | Connection trace finds first match, not correct match |
| `set_assembly` callback receives stale or incorrect assembly | Subassembly merge order; check `assembly.py` subassembly grafting |
| ModelException "could not find X in assembly" despite X existing | Wrong connector name in connection trace (check generated YAML) |
| Packet type resolves correctly in isolation but wrong in multi-instance case | `__eq__` filename comparison silently matching wrong instance |

### Investigation Workflow

1. **Identify the generator or model** responsible for the wrong output. Check `build/src/` for the generated file and trace back to the generator via `default.do` routing.

2. **Find the Python model class**. Look for `gen/models/` in the component's source tree. If absent, the generic framework model in `$ADAMANT_DIR/gen/models/` applies.

3. **Read `set_assembly()`** in the model class. This is where assembly-scope data is consumed.

4. **Check all `==` comparisons on component objects**. Any `conn.from_component == self.component` or `comp == self.component` is suspect -- replace with `is`.

5. **Trace the connection topology** in the assembly YAML to verify the expected wiring matches what the code searches for. Connector names must exactly match the component YAML's connector definitions.

6. **Add temporary debug prints** to `set_assembly()` if needed:
   ```python
   import sys
   print(f"[DEBUG] set_assembly: self.component.instance_name={self.component.instance_name}", file=sys.stderr)
   for conn in self.assembly.connections:
       if conn.to_component is self.component:
           print(f"[DEBUG]   conn: {conn.from_component.instance_name} -> {conn.to_connector.name}", file=sys.stderr)
   ```
   Run `redo clear_cache` and then `redo all` from the assembly directory to force regeneration with debug output visible.

7. **Verify with `redo clear_cache`** before testing any model fix. The SQLite cache stores pickled model objects; stale cache entries can mask code changes.

### Connection Name Discovery

To find the exact connector name used in a connection, check:
- The component's `*.component.yaml` (lists all connector definitions)
- The generated `build/src/component-<name>.ads` (Ada spec names connectors exactly)
- The assembly YAML connection entries (lists `from_connector` and `to_connector` names)

## Related Framework Internals References

- `internals-and-generation.md` in `adamant-build-system` skill -- generator dispatch, session database, build path resolution
- `gen/models/base.py` -- full `__eq__`, `__new__`, `__init__`, and caching implementation
- `gen/models/assembly.py` -- complete assembly loading and `set_assembly` call chain

## When NOT to Use This Skill

- Normal component development: use `adamant-component-dev`
- Assembly wiring: use `adamant-assembly-dev`
- Build commands and code gen pipeline overview: use `adamant-build-system`
- Type definitions: use `adamant-type-system`

This skill is specifically for debugging situations where the framework's Python model layer is producing incorrect output, or when extending the framework with new custom model overrides.
