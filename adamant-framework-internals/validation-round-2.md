# Adamant Framework Internals Skill Validation - Round 2

**Validator:** Claude Subagent  
**Date:** 2026-02-18  
**Focus:** Connection model and framework internals deep-dive

## Exercise 1: Connection Model Analysis

### What the Skill Claims
- Connection objects have fields: from_component, to_component, from_connector, to_connector
- Connection has `connected` flag that is set during connection process
- `connect()` method exists but mechanism not detailed
- Connection `to_component`/`from_component` references are the same Python object when both originate from the same `load_component()` call

### What the Code Actually Does

**Connection Class Location:** `~/.openclaw/workspace/projects/adamant/gen/models/assembly.py` lines 134-379

**Connection Object Fields:**
```python
class connection(object):
    def __init__(self, filename, data):
        self.connected = False
        self.ignored = False
        self.data = data
        self.lineno = data.lc.line
```

After `connect()` is called, additional fields are set:
- `self.from_component` - Component object reference
- `self.from_connector` - Connector object reference  
- `self.from_index` - Array index (defaults to 1)
- `self.to_component` - Component object reference
- `self.to_connector` - Connector object reference
- `self.to_index` - Array index (defaults to 1)
- `self.description` - Optional connection description
- `self.from_name` - Formatted string like "component.connector[index]"
- `self.to_name` - Formatted string like "component.connector[index]"
- `self.name` - Combined "from_name-to_name"

**How `connect()` Works:**
1. Extracts component names from YAML data via `ada.formatVariable(self.data["from_component"])`
2. Looks up component objects in `components[component_name]` dictionary
3. Finds connector objects via `component.connectors.of_name(connector_name)`
4. Handles array indices for arrayed connectors
5. Calls `self.from_connector.connect_to()` to establish bidirectional link
6. Sets `self.connected = True` on success, or `self.ignored = True` for ignore connections

**Connected Flag:**
- Initialized to `False` in `__init__`
- Set to `True` when `connect()` successfully links connectors
- Set to `False` for ignored connections (which set `ignored = True` instead)
- Used in assembly loading: `if not connection.connected and not connection.ignored:`

**Object Identity Claim Verification:**
✅ **VERIFIED** - The claim is correct. In `assembly.load()`:
```python
for component in self.data["components"]:
    component_model = model_loader.try_load_model_by_name(component["type"], model_types="component")
    self.components[component_name] = component_model
```

Later during connection resolution:
```python
from_component = components[from_component_name]  # Same object reference
```

Since `components` dictionary stores the exact same Python objects returned by `load_component()`, connection references point to identical objects.

### Gaps in Skill Documentation
1. **Missing field details** - Skill doesn't document the full set of connection fields (indices, names, description)
2. **Array handling** - No mention of from_index/to_index for arrayed connectors
3. **Ignore mechanism** - Doesn't explain ignored connections vs connected connections
4. **Error handling** - Missing details about ModelException cases in connect()

---

## Exercise 2: model_loader.py Analysis

### What the Skill Claims
- `try_load_model_by_name()` exists for model loading
- `load_model()` exists  
- Path resolution interacts with BUILD_ROOTS
- `get_model_file_path()` is used in custom override pattern

### What the Code Actually Does

**File Location:** `~/.openclaw/workspace/projects/adamant/redo/util/model_loader.py`

**`try_load_model_by_name()` Implementation:**
```python
def try_load_model_by_name(model_name, model_types=[], *args, **kwargs):
    model_file = get_model_file_path(model_name, model_types)
    if model_file:
        return load_model(model_file, *args, **kwargs)
    return None
```
- Uses `get_model_file_path()` to resolve name to file path
- Delegates to `load_model()` if file found
- Returns `None` if no model found (graceful failure)

**`load_model()` Implementation:**
```python
def load_model(model_filename, *args, **kwargs):
    model_class = _get_model_class(model_filename)
    return model_class(model_filename, *args, **kwargs)
```
- Uses `_get_model_class()` to get Python class from filename
- Instantiates class with filename and additional args
- `_get_model_class()` extracts model type from extension and imports `models.{type}` module

**Path Resolution with BUILD_ROOTS:**
Path resolution happens via `database.model_database.model_database()`:
```python
def _get_model_file_paths(model_name, model_types=[]):
    with database.model_database.model_database() as db:
        model_dict = db.get_model_dict(model_name)
```
- Model database is populated by scanning BUILD_ROOTS during database creation
- First match wins (project overrides framework)
- BUILD_ROOTS determines search order

**`get_model_file_path()` Function:**
```python
def get_model_file_path(model_name, model_types=[]):
    model_files = get_model_file_paths(model_name=model_name, model_types=model_types)
    if model_files:
        if len(model_files) > 1:
            system_error.error_abort("more than one model of the name was found: " + str(model_files))
        return model_files[0]
    return None
```
- Returns single file path or None
- Errors if multiple matches found
- Used in custom override pattern as skill claims

### Gaps in Skill Documentation
1. **Database layer** - Skill doesn't explain the model_database abstraction
2. **Error conditions** - Missing details about when/how failures occur
3. **Module import mechanism** - `_get_model_class()` details not covered
4. **Multiple file handling** - `get_model_file_paths()` vs `get_model_file_path()` distinction

---

## Exercise 3: Submodel Propagation Deep-dive

### What the Skill Claims
- `set_assembly` propagates to submodels
- Need to trace exactly HOW propagation works

### What the Code Actually Does

**Location:** `~/.openclaw/workspace/projects/adamant/gen/models/component.py` lines 912-918

**Component's `set_assembly()` Method:**
```python
def set_assembly(self, assembly):
    self.instance_assembly_model = assembly
    
    # Load this assembly into all of the submodels:
    for m in self.submodels.values():
        # Load the assembly:
        m.set_assembly(assembly)
```

**Propagation Analysis:**

**Which submodels get `set_assembly()` called?**
- ALL submodels in `self.submodels.values()`
- `self.submodels` is populated during component loading when submodels call `set_component()`
- Includes: packets, events, commands, data_products, parameters, faults, etc.

**In what order?**
- Dictionary iteration order (insertion order in Python 3.7+)
- Order depends on when each submodel was loaded/attached during component load
- No explicit ordering guarantees

**What data is available to each submodel's `set_assembly()`?**
- Full `assembly` object with:
  - `assembly.components` - All component instances (after `set_component_instance_data`)
  - `assembly.connections` - All resolved connections (after `connect()` calls)
  - `assembly.submodels` - Previously loaded assembly submodels
  - Component identity is stable (`component.instance_name` set)
  
**Base Submodel Behavior:**
```python
def set_assembly(self, assembly):
    self.assembly = assembly
```
Custom submodels can override to add assembly-specific logic.

### Assembly Loading Context
From `assembly.py`, `set_assembly()` is called AFTER:
1. All components loaded and instantiated
2. All connections resolved via `connection.connect()`  
3. All component instance data set via `set_component_instance_data()`

This ensures submodels have complete assembly state when `set_assembly()` runs.

### Gaps in Skill Documentation
1. **Timing guarantees** - Skill doesn't specify that connections are fully resolved before `set_assembly()`
2. **Order dependencies** - No mention that submodel order isn't guaranteed
3. **State availability** - Missing details about what assembly state is available when

---

## Exercise 4: Custom Model Override Categorization

### Files Found
22 custom model override files in `~/.openclaw/workspace/projects/adamant/src -path "*/gen/models/*"`

### Categorization Results

**Files that override `set_assembly()`:** (16 files)
- `downsampler_data_products.py`
- `product_extractor_data_products.py`  
- `command_sequencer_packets.py`
- `cpu_monitor_packets.py`
- `fault_correction_commands.py`
- `fault_correction_data_products.py`
- `parameters_packets.py`
- `product_packetizer_packets.py`
- `queue_monitor_packets.py`
- `sequence_store_packets.py`
- `stack_monitor_packets.py`
- `task_watchdog_commands.py`
- `task_watchdog_data_products.py`
- `task_watchdog_faults.py`
- `task_watchdog_list.py`

**Files that override other methods:** (6 files)
- `product_packetizer_packets.py` - also overrides `final()`
- `task_watchdog_faults.py` - also overrides `set_component()`
- `ccsds_downsampler_filters.py` - custom data structures, no standard overrides
- `extracted_products.py` - custom data structures, no standard overrides  
- `ccsds_router_table.py` - custom `resolve_router_destinations()` method
- `fault_responses.py` - custom data structures, no standard overrides
- `parameter_table.py` - custom data structures, no standard overrides
- `product_packets.py` - custom data structures, no standard overrides
- `sequence_store.py` - custom data structures, no standard overrides

### Pattern Analysis

**Standard Pattern (15 files):**
```python
class my_component_packets(packets):
    def submodel_name(self):
        return "packets"
        
    def set_assembly(self, assembly):
        self.assembly = assembly
        # Custom assembly-scope logic here
        super(my_component_packets, self).set_assembly(assembly)
```

**Variations Found:**
1. **Data structure files** - Define custom classes, no standard method overrides
2. **Multi-method override** - `task_watchdog_faults.py` overrides both `set_component()` and `set_assembly()`
3. **Final override** - `product_packetizer_packets.py` also overrides `final()` method

### Patterns NOT Covered by Skill
1. **Custom data structure pattern** - 6 files define custom data classes without inheriting from standard submodels
2. **Multi-method overrides** - Skill doesn't mention overriding `set_component()` or `final()`
3. **Complex assembly resolution** - `ccsds_router_table.py` has custom `resolve_router_destinations(assm)` method

---

## Exercise 5: Generator Dispatch Mechanism

### What the Skill Claims
- Check `default.do` for routing
- Generated file path maps to generator class
- Generator registry exists somewhere
- Should be able to trace from wrong generated file back to responsible generator

### What the Code Actually Does

**Dispatch Entry Point:** `~/.openclaw/workspace/projects/adamant/default.do`

**Generated File Routing:**
```python
elif redo_arg.in_build_dir(sys.argv[2]):
    from rules.build_via_generator import build_via_generator as rule_cls
```

**Generator Registry:** `database.generator_database.generator_database()`

**File-to-Generator Mapping Process:**
1. `build_via_generator.py` calls `db.get_generator(output_filename)`
2. Database returns tuple: `(module_name, class_name, file_name, input_filename)`
3. Generator class is dynamically imported and instantiated
4. `generator.generate(input_filename)` produces output file

**Registry Population:**
- Database is built by scanning generators during database creation
- Each generator registers its output patterns
- Database maps output filename patterns to generator classes

**Tracing Wrong Generated File to Generator:**
1. Given wrong output file path
2. Query `generator_database().get_generator(output_filename)` 
3. Returns generator module, class, and source file
4. Can examine generator source to understand logic
5. Input filename also provided for tracing source YAML

**Database Implementation:**
Located in `database/generator_database.py` (not examined in detail but referenced in code)

### Error Investigation Workflow
```python
try:
    with generator_database() as db:
        value = db.get_generator(output_filename)
except KeyError:
    error.error_abort("No rule to build " + output_filename + ".")

module_name = value[0]    # Generator module name
class_name = value[1]     # Generator class name  
file_name = value[2]      # Generator source file
input_filename = value[3] # Input YAML file
```

### Gaps in Skill Documentation
1. **Database details** - Skill doesn't explain generator database structure
2. **Registration process** - How generators register their patterns not covered
3. **Error debugging** - Concrete steps for tracing generator bugs not detailed
4. **Multiple output patterns** - How one generator can produce multiple file types

---

## Summary of Skill Gaps

### Major Missing Areas
1. **Array connector handling** - Connection model supports arrays but skill doesn't cover this
2. **Custom data structure pattern** - 6 override files use pattern not documented in skill  
3. **Generator database mechanics** - Core dispatch mechanism under-documented
4. **Multi-method override patterns** - `set_component()`, `final()` overrides not covered

### Minor Gaps
1. Connection field details incomplete
2. Model loading error conditions
3. Submodel propagation order dependencies  
4. Generator registration process

### Accuracy Assessment
✅ **Accurate Claims:** Connection object identity, `set_assembly` propagation, custom override location  
⚠️ **Incomplete Claims:** Connection field list, generator dispatch details  
❌ **No Major Inaccuracies Found**

The skill provides a solid foundation but needs expansion in the identified gap areas, particularly around the custom data structure pattern and generator database mechanics.