# Adamant Generator Development

Patterns and workflows for developing custom generators for Adamant framework components. Generators produce Ada source, YAML types, HTML docs, and ground system artifacts from YAML model files.

## Architecture Overview

Adamant's code generation pipeline:
```
YAML Model File -> Schema Validation -> Python Model Object -> Jinja2 Template -> Generated Output
```

**Discovery chain:**
1. `env/set_python_path.sh` adds every directory containing `__init__.py` to PYTHONPATH
2. `redo/util/meta.py` scans PYTHONPATH for directories named `generators/` or `generator/`
3. All `.py` files in those directories are imported
4. `meta.get_all_subclasses_of(generator_base)` finds all generator classes
5. Each generator's `input_file_regex()` determines which YAML files it processes
6. The generator database maps (input_file, generator) -> output_file for redo

## Directory Structure

Component-local generators live inside the component directory:
```
src/components/<component_name>/
  gen/
    __init__.py              # REQUIRED: empty file, makes gen/ a Python package
    generators/
      <generator_name>.py    # Generator classes
    models/
      <model_name>.py        # Model classes (parse YAML into Python objects)
    schemas/
      <schema_name>.yaml     # Pykwalify schemas for YAML validation
    templates/
      <template_dir>/
        name.ads             # Jinja2 templates ("name" is replaced with model name)
    doc/                     # Optional: LaTeX documentation for the generator
      <generator_name>.tex
```

All 15 framework components with custom generators follow this exact structure.

## YAML File Naming Convention

**CRITICAL**: YAML model files follow a strict naming pattern that determines how they are discovered and processed:

```
[specific_name.]model_name.model_type.yaml
```

- `model_type` = the type string used for regex matching (e.g., `ccsds_router_table`, `parameter_table`)
- `model_name` = typically the assembly name (for assembly submodels) or component name
- `specific_name` = optional qualifier when multiple instances of the same model type exist

Examples:
```
linux_example.ccsds_router_table.yaml          # model_name=linux_example, model_type=ccsds_router_table
test_parameter_table.test_assembly.parameter_table.yaml  # specific_name=test_parameter_table, model_name=test_assembly
linux_example.product_packets.yaml             # model_name=linux_example, model_type=product_packets
```

The `model_type` in the filename MUST match `model_class.__name__` in the generator (which becomes `input_file_regex = r".*\.<model_type>\.yaml$"`).

## Generator Class Patterns

### Pattern 1: Basic Generator (most common)

For generators that produce a single output file from a single YAML input. Inherit from both `basic_generator` and `generator_base`:

```python
import os.path
from models import my_model
from base_classes.generator_base import generator_base
from generators.basic import basic_generator


class my_output_ads(basic_generator, generator_base):
    def __init__(self):
        this_file_dir = os.path.dirname(os.path.realpath(__file__))
        template_dir = os.path.join(this_file_dir, ".." + os.sep + "templates")
        basic_generator.__init__(
            self,
            model_class=my_model.my_model,
            template_filename="name.ads",
            template_dir=template_dir,
        )

    def output_filename(self, input_filename):
        dirname, specific_name, model_name, *ignore = self._split_input_filename(
            input_filename
        )
        if not specific_name:
            build_dir = self._get_default_build_dir()
            a = self.template_basename.rsplit("name", maxsplit=1)
            output_filename = (model_name + "_my_suffix").join(a)
            return dirname + os.sep + build_dir + os.sep + output_filename
        return basic_generator.output_filename(self, input_filename)

    def generate(self, input_filename):
        m = my_model.my_model(input_filename)
        m.load_assembly()  # if assembly submodel
        print(m.render(self.template, template_path=self.template_dir))
```

### Pattern 2: Assembly-Aware Generator (needs assembly context)

When the generator needs to resolve references against the assembly (component names, connector indices, IDs):

```python
def generate(self, input_filename):
    # Load the assembly model
    dirname, view_name, assembly_name, *ignore = self._split_input_filename(
        input_filename
    )
    assembly_model_name = model_loader.get_model_file_path(
        assembly_name, model_types="assembly"
    )
    if not assembly_model_name:
        error.error_print(
            "Could not find a model file for assembly '" + assembly_name + "'."
        )
        error.abort()
    a = assembly.assembly(assembly_model_name)

    # Load the submodel and resolve against assembly
    r = my_model.my_model(input_filename)
    r.resolve_against_assembly(a)
    print(r.render(self.template, template_path=self.template_dir))
```

### Pattern 3: Assembly Generator Extension (extending assembly templates)

For generators that produce assembly-level outputs with component-local templates (e.g., event_to_text):

```python
from generators.assembly import assembly_generator

class my_assembly_output_ads(assembly_generator, generator_base):
    def __init__(self):
        this_file_dir = os.path.dirname(os.path.realpath(__file__))
        template_dir = os.path.join(this_file_dir, ".." + os.sep + "templates")
        assembly_generator.__init__(
            self, "name_my_output.ads", template_dir=template_dir
        )
```

### Pattern 4: Ided Suite Override (custom commands/events/data_products/faults)

When a component needs to generate its own commands, events, data products, or faults that depend on the assembly-level configuration YAML:

```python
from generators.basic import add_basic_generators_to_module
from generators.ided_suite import fault_templates, command_templates, data_product_templates

# Override the standard ided_suite generators with custom model classes
add_basic_generators_to_module(
    my_custom_faults.my_custom_faults, fault_templates, module=globals()
)
add_basic_generators_to_module(
    my_custom_commands.my_custom_commands, command_templates, module=globals()
)
```

This reuses standard templates (events/name_events.ads, etc.) but with a custom model class that computes different content.

## Model Class Patterns

### Assembly Submodel (most component generators use this)

Assembly submodels are loaded by the assembly model during its load process. The assembly calls `set_assembly()` on each submodel, giving it access to the full assembly context.

```python
from models.assembly import assembly_submodel
from models.exceptions import ModelException

class my_model(assembly_submodel):
    def __init__(self, filename):
        this_file_dir = os.path.dirname(os.path.realpath(__file__))
        schema_dir = os.path.join(this_file_dir, ".." + os.sep + "schemas")
        super(my_model, self).__init__(
            filename, schema_dir + "/my_schema.yaml"
        )

    def load(self):
        """Called during __init__. Parse YAML data into Python objects."""
        super(my_model, self).load()  # sets self.assembly = None
        self.name = None
        self.description = None

        # Access raw YAML via self.data (dict from pykwalify-validated YAML)
        if self.specific_name:
            self.name = ada.formatType(self.specific_name)
        else:
            self.name = ada.formatType(self.model_name) + "_My_Suffix"

        if "description" in self.data:
            self.description = self.data["description"]

        # Parse YAML entries into model objects
        for entry_data in self.data["entries"]:
            # ... build Python objects from YAML data

    def set_assembly(self, assembly):
        """Called by assembly model during load. Resolve assembly references here."""
        super(my_model, self).set_assembly(assembly)
        # Now self.assembly is set -- resolve component names, connector indices, IDs
        self._resolve_references()
```

### Key Model Base Class Members

Available in all models inheriting from `base`:
- `self.data` -- parsed YAML content (dict)
- `self.model_name` -- extracted from filename (e.g., "linux_example")
- `self.model_type` -- extracted from filename (e.g., "parameter_table")
- `self.specific_name` -- optional prefix from filename (or None)
- `self.full_filename` -- absolute path to YAML file
- `self.dependencies` -- list of file paths this model depends on
- `self.render(template, template_path)` -- render Jinja2 template with self.__dict__

Available in assembly submodels:
- `self.assembly` -- the parent assembly model (set via `set_assembly()`)
- `self.load_assembly()` -- explicitly load the assembly (called by generators, not during normal assembly load)

### Assembly Model API (for resolving references)

```python
# Get a component by its instance name
comp = self.assembly.get_component_with_name("My_Component_Instance")
# comp.instance_name, comp.name (type name), comp.full_filename
# comp.connectors, comp.commands, comp.parameters, comp.events, comp.faults, comp.data_products

# Get a connector by name
connector = comp.connectors.of_name("Ccsds_Space_Packet_T_Send")

# Get connections on a connector
connections = connector.get_connections()
# Each connection: c.to_component, c.to_connector, or None/"ignore"
```

## Schema Patterns (Pykwalify)

Schemas validate YAML input before model loading:

```yaml
---
type: map
mapping:
  # Required string field
  instance_name:
    type: str
    required: True
  # Optional description
  description:
    type: str
    required: False
  # Required list with minimum 1 entry
  entries:
    seq:
      - type: map
        mapping:
          name:
            type: str
            required: True
          value:
            type: int
            required: True
          mode:
            type: str
            enum: ['option_a', 'option_b', 'option_c']
            required: False
    range:
      min: 1
    required: True
```

## Template Patterns (Jinja2)

Templates use Jinja2 with access to all model object members via `self.__dict__`:

```ada
-- Generated file. DO NOT EDIT.
{% if description %}
{{ printMultiLine(description, '-- ') }}
{% endif %}
package {{ name }} is

{% for entry in entries %}
   -- Entry for {{ entry.name }}
   {{ entry.name }}_Value : constant := {{ entry.value }};
{% endfor %}

end {{ name }};
```

**Template naming**: `name` in the template filename is replaced with the model name in the output filename. Example: template `name.ads` with model name `linux_example_my_table` produces `linux_example_my_table.ads`.

**Template location**: Templates go in `gen/templates/<template_subdir>/` where `<template_subdir>` matches the model type or a descriptive name.

**Output file placement rules** (from `basic_generator._get_default_build_dir()`):
- `.ads`, `.adb` files -> `build/src/` (unless name ends in `-implementation`, `-implementation-tester`, `main`, `test` -> `build/template/`)
- `.tex` files -> `doc/build/tex/`
- `.html` files -> `build/html/`
- `.yaml` files -> `build/yaml/`
- Other extensions -> `build/<extension>/`

## Utility Functions

```python
from util import ada
ada.formatVariable("my_component")  # -> "My_Component" (Ada variable naming)
ada.formatType("my_type")           # -> "My_Type" (Ada type naming)
ada.isTypePrimitive("Natural")      # -> True

from util import model_loader
model = model_loader.try_load_model_by_name("assembly_name", model_types="assembly")
path = model_loader.get_model_file_path("component_name", model_types="component")

from util import error
error.error_print("message")
error.error_abort("fatal message")
```

## Framework Components with Custom Generators (Reference Catalog)

15 of 59 framework components have custom generators:

| Component | Model Type | Assembly-Aware | Generates |
|-----------|-----------|----------------|-----------|
| ccsds_router | ccsds_router_table | Yes (resolves connector indices) | Ada routing table spec |
| parameters | parameter_table | Yes (resolves param IDs, connector indices) | Ada param table spec, YAML record type |
| fault_correction | fault_responses | Yes (resolves fault/command IDs) | Ada fault response table, YAML record/enum |
| task_watchdog | task_watchdog_list | Yes (resolves pet connector indices) | Ada watchdog list spec, YAML record types |
| product_packetizer | product_packets | Yes (resolves data product IDs) | Ada packet definitions, HTML |
| ccsds_downsampler | ccsds_downsampler_filters | Model-only | Ada filter config |
| ccsds_command_depacketizer | (assembly-level) | Yes | Ada command routing |
| ccsds_packetizer | (assembly-level) | Yes | Hydra XML config |
| ccsds_product_extractor | extracted_products | Yes | Ada extraction table |
| command_sequencer | (assembly-level) | Yes | Ada sequence config |
| cpu_monitor | (assembly-level) | Yes | Custom packets |
| queue_monitor | (assembly-level) | Yes | Custom packets |
| stack_monitor | (assembly-level) | Yes | Custom packets |
| event_text_logger | (assembly-level) | Yes | Ada event-to-text mapping |
| sequence_store | sequence_store | Yes | Ada sequence storage config |

## Creating a New Generator: Checklist

1. **Define the YAML schema** in `gen/schemas/<model_type>.yaml`
   - Use pykwalify format
   - Required fields, types, enums, ranges

2. **Create the model class** in `gen/models/<model_name>.py`
   - Inherit from `assembly_submodel` if assembly context is needed
   - Implement `load()` to parse `self.data`
   - Implement `set_assembly()` if resolving assembly references
   - Add resolved data to `self.dependencies` for redo tracking

3. **Create Jinja2 templates** in `gen/templates/<template_dir>/`
   - `name` in filename is replaced with model name
   - Access all model members directly in template

4. **Create the generator class** in `gen/generators/<generator_name>.py`
   - Inherit from `basic_generator` and `generator_base`
   - Point to model class and template
   - Override `output_filename()` for custom naming
   - Override `generate()` if assembly loading is needed

5. **Create empty `__init__.py`** in `gen/`
   - REQUIRED for PYTHONPATH discovery
   - After adding `__init__.py`, run `adamant_env.sh refresh` to rebuild the PYTHONPATH snapshot
   - Then run `redo clear_cache` to invalidate stale model/generator caches

6. **Create the YAML model file** in the assembly directory
   - Named: `[specific.]assembly_name.<model_type>.yaml`
   - Must be in a directory with `.all_path`

7. **Refresh the environment**: Run `adamant_env.sh refresh` to rebuild the cached PYTHONPATH snapshot (picks up the new `__init__.py`), then `redo clear_cache` to invalidate stale generator registry

8. **Test**: Run `redo` and verify the generated output appears in `build/src/`

## Common Patterns in Existing Generators

### Resolving Component Connector Indices
Many generators need to translate component names into connector output indices (1-based). Pattern from ccsds_router_table:

```python
# Get the component's output connector
connector = component_model.connectors.of_name("Output_T_Send")
connections = connector.get_connections()
connected_components = {}
for idx, c in enumerate(connections):
    if c is not None and c != "ignore":
        connected_components[c.to_component.instance_name] = idx + 1
```

### Generating YAML Type Definitions
Some generators produce YAML type definitions (records, enums) that feed back into the type system. These go to `build/yaml/` and are picked up by the standard type generators:

```python
class my_record_yaml(basic_generator, generator_base):
    def __init__(self):
        # ...
        basic_generator.__init__(
            self,
            model_class=my_model.my_model,
            template_filename="name_record.record.yaml",
            template_dir=template_dir,
        )
```

### Overriding Standard Ided Suite Generators
When a component needs assembly-aware commands/events/faults/data_products, create a custom model that inherits from the standard model but adds assembly resolution:

```python
# In gen/models/my_custom_commands.py
from models.commands import commands

class my_custom_commands(commands):
    def __init__(self, filename):
        # Custom loading that computes commands from assembly config
        ...
```

Then in the generator, use `add_basic_generators_to_module` to register the custom model with standard templates.

## Error Handling

Use `ModelException` for user-facing errors in models:
```python
from models.exceptions import ModelException, throw_exception_with_filename

@throw_exception_with_filename
def resolve(self):
    if not self.assembly.get_component_with_name(name):
        raise ModelException(
            'Component "' + name + '" does not exist in assembly "' + self.assembly.name + '".'
        )
```

The `@throw_exception_with_filename` decorator adds the YAML filename to error messages.

## Anti-Patterns

- **Do NOT use `rm -rf` on build directories** -- use `redo clean` or `redo clean_all`
- **Do NOT generate files outside `build/`** -- redo owns the build directory lifecycle
- **Do NOT hardcode paths** -- use `os.path` and the model's `full_file_dir`
- **Do NOT forget `__init__.py`** -- without it, generators won't be discovered
- **Do NOT forget `adamant_env.sh refresh`** -- after adding `__init__.py`, the PYTHONPATH snapshot is stale; refresh rebuilds it without restarting the container. Follow with `redo clear_cache`.
- **Do NOT use same `model_type` string as an existing model** -- causes regex collisions
- **Do NOT forget to add dependencies** -- redo needs `self.dependencies` for incremental builds
- **Do NOT use `print()` for debugging** -- generators capture stdout as output; use `sys.stderr.write()`
