# Existing Component Generator Catalog

Detailed breakdown of all 15 framework components with custom generators.

## Generator Complexity Tiers

### Tier 1: Assembly Template Extensions (simplest)
These just add component-local templates to the assembly generator. No custom model, no custom schema.

**event_text_logger** (21 lines)
- Produces: `name_event_to_text.ads`, `name_event_to_text.adb`
- Model: uses `assembly.assembly` directly (via `assembly_generator`)
- Templates iterate over all events in the assembly to build a text lookup function
- No custom YAML input -- triggered by assembly model

**ccsds_packetizer** (57 lines)
- Produces: Hydra XML configuration
- Model: uses `assembly.assembly` directly
- Generates ground system config from assembly packet definitions

**ccsds_command_depacketizer** (43 lines)
- Produces: Ada command routing source
- Model: uses `assembly.assembly` directly
- Generates command depacketization tables from assembly

### Tier 2: Assembly-Aware Monitors (custom packets from assembly)
These generate custom packets/data products that summarize assembly-level information.

**cpu_monitor** (42 lines)
- Custom model: `cpu_monitor_packets` (overrides standard packets model)
- Produces: packets with CPU usage fields computed from assembly task list
- Uses `add_basic_generators_to_module` with standard packet templates

**queue_monitor** (44 lines)
- Custom model: `queue_monitor_packets`
- Produces: packets with queue depth fields computed from assembly queued components
- Same pattern as cpu_monitor

**stack_monitor** (44 lines)
- Custom model: inherits from packets
- Produces: packets with stack usage fields

### Tier 3: Custom YAML + Assembly Resolution (most common)
These have their own YAML schema, model, and assembly resolution logic.

**ccsds_router** (generator: 50 lines, model: 180 lines)
- YAML type: `ccsds_router_table`
- Schema: APID -> destination component list mapping
- Resolution: translates component names to connector output indices
- Key: `resolve_router_destinations(assembly)` -- maps destination names to 1-based connector indices
- Validates: component exists, is Ccsds_Router type, destinations are connected
- Supports: multi-destination routing, `ignore` keyword, `Component.Connector` syntax for disambiguation

**parameters** (generator: 105 lines, model: ~450 lines)
- YAML type: `parameter_table`
- Schema: parameter instance name + ordered parameter list
- Resolution: resolves parameter IDs, component IDs, connector indices, byte offsets
- Key: `_resolve_parameter_table()` -- computes start/end indices, validates sizes fit in Packet.T
- Supports: `Component.Parameter` or just `Component` (all params), grouped parameters (union entries)
- Cross-table duplicate detection
- Generates: Ada table spec, YAML record type definition
- Multiple output classes: `parameter_table_ads`, `parameter_table_yaml`, `parameter_table_xml`

**fault_correction** (generator: 135 lines, model: separate)
- YAML type: `fault_responses`
- Schema: fault -> command response mapping with latching/enable config
- Resolution: resolves fault IDs and command IDs from assembly
- Generates: Ada response table, YAML record type, YAML enum type
- Multiple generators: `fault_responses_ads`, `fault_responses_status_record_yaml`, `fault_responses_status_enum_yaml`, `fault_responses_packed_id_type_record_yaml`
- Also overrides standard faults, commands, data_products generators with assembly-aware models

**task_watchdog** (generator: 157 lines, model: separate)
- YAML type: `task_watchdog_list`
- Schema: petter list with connector names, limits, actions, fault IDs
- Resolution: resolves pet connector indices from assembly
- Generates: Ada watchdog list spec, YAML state record, YAML limit/action command records
- Multiple generators for different output types

**product_packetizer** (generator: 102 lines, model: separate)
- YAML type: `product_packets`
- Schema: packet definitions with data product references and periods
- Resolution: resolves data product IDs from assembly component models
- Generates: Ada packet definitions, HTML documentation
- Also overrides standard packets generators

**ccsds_downsampler** (generator: 45 lines, model: separate)
- YAML type: `ccsds_downsampler_filters`
- Schema: filter configuration per APID
- Model + overrides for data products

**ccsds_product_extractor** (generator: 79 lines, model: separate)
- YAML type: `extracted_products`
- Schema: product extraction configuration
- Assembly-aware resolution

**command_sequencer** (generator: 103 lines, model: separate)
- Assembly-level sequence configuration
- Custom packets model

**sequence_store** (generator: 78 lines, model: separate)
- YAML type: `sequence_store`
- Schema: sequence storage configuration
- Assembly-aware resolution

## Common Code Patterns Across All Generators

### output_filename() Pattern
Every custom generator follows the same output_filename pattern:
```python
def output_filename(self, input_filename):
    dirname, specific_name, model_name, *ignore = self._split_input_filename(input_filename)
    if not specific_name:
        build_dir = self._get_default_build_dir()
        a = self.template_basename.rsplit("name", maxsplit=1)
        output_filename = (model_name + "_<suffix>").join(a)
        return dirname + os.sep + build_dir + os.sep + output_filename
    return basic_generator.output_filename(self, input_filename)
```

### template_dir Pattern
Every generator locates its templates relative to its own file:
```python
this_file_dir = os.path.dirname(os.path.realpath(__file__))
template_dir = os.path.join(this_file_dir, ".." + os.sep + "templates")
```

### Assembly Loading Pattern
Two approaches for assembly-aware generators:

**Approach A** (explicit in generator): Load assembly in `generate()`:
```python
assembly_model_name = model_loader.get_model_file_path(assembly_name, model_types="assembly")
a = assembly.assembly(assembly_model_name)
r = my_model(input_filename)
r.resolve(a)
```

**Approach B** (via submodel): Call `load_assembly()` in `generate()`:
```python
m = my_model(input_filename)
m.load_assembly()  # triggers set_assembly() callback
```

Approach B is preferred when the model inherits from `assembly_submodel` because it handles caching and dependency updates automatically.
