<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Template Analysis: Adamant Component Code Generation Patterns

This document analyzes the Jinja2 templates that generate Adamant component code to identify patterns and edge cases not documented in the main skills. Templates examined from `~/.openclaw/workspace/projects/adamant/gen/templates/component/` and `~/.openclaw/workspace/projects/adamant/gen/templates/tests/`.

## Template Overview

The key templates that generate component code:

- `component-name.ads` - Base class specification  
- `component-name.adb` - Base class body
- `component-name-implementation.ads` - Implementation spec template
- `component-name_reciprocal.ads` - Tester reciprocal spec (in tests/)
- `component-name_reciprocal.adb` - Tester reciprocal body (in tests/)
- `name_commands.ads` - Commands package (in commands/)

## `with` Clauses Generation Patterns

### Base Class Spec (`component-name.ads`)

**Generated `with` clauses:**
```jinja2
{% if base_ads_includes %}
-- Includes:
{% for include in base_ads_includes %}
with {{ include }};
{% if include in ["Interfaces", "Connector_Types"] %}
use {{ include }};
{% endif %}
{% endfor %}
{% endif %}
```

**Key finding**: Only `Interfaces` and `Connector_Types` get automatic `use` clauses. The `base_ads_includes` variable is populated by the generator based on:
- Connector types used
- Feature models present (commands, events, data products, etc.)  
- Custom types referenced in preamble or connectors
- Generic parameters

### Base Class Body (`component-name.adb`)

**Generated `with` clauses:**
```jinja2
-- Includes:
{% if connectors.n_arrayed().invoker() %}
with Safe_Deallocator;
{% endif %}
{% for include in base_adb_includes %}
with {{ include }};
{% endfor %}
```

**Edge case patterns:**
1. `Safe_Deallocator` only included for components with arrayed invoker connectors (count=0 or count>1)
2. No automatic `use` clauses in the body - more conservative approach

### Implementation Template (`component-name-implementation.ads`)

**Generated `with` clauses:**
```jinja2
{% if template_ads_includes %}
-- Includes:
{% for include in template_ads_includes %}
with {{ include }};
{% endfor %}
{% endif %}
```

**Key finding**: Implementation templates only include minimal required packages. The skill documentation requirement to NOT `with` framework packages is enforced here - the template doesn't auto-include them.

### Tester Reciprocal (`component-name_reciprocal.ads`)

**Generated `with` clauses:**
```jinja2
-- Includes:
with File_Logger;
{% if tester_base_ads_includes %}
{% for include in tester_base_ads_includes %}
{% if include in includes %}
pragma Warnings (Off, "unit ""{{ include }}"" is not referenced");
pragma Warnings (Off, "no entities of ""{{ include }}"" are referenced in spec");
{% endif %}
with {{ include }};
{% if include in includes %}
pragma Warnings (On, "no entities of ""{{ include }}"" are referenced in spec");
pragma Warnings (On, "unit ""{{ include }}"" is not referenced");
{% endif %}
{% if include in ["Connector_Types"] %}
use {{ include }};
{% endif %}
{% endfor %}
{% endif %}
```

**Critical pattern**: Tester reciprocals use `pragma Warnings` to suppress unused package warnings when includes are in a certain set. Only `Connector_Types` gets a `use` clause.

### Commands Package (`name_commands.ads`)

**Generated `with` clauses:**
```jinja2
-- Standard Includes
with Command;
with Command_Types;
{% if variable_length_types %}
with Serializer_Types; use Serializer_Types;
{% endif %}
{% if includes %}

-- Argument Includes
{% for include in includes %}
{% if include not in ["Command", "Command_Types"] %}
with {{ include }};
{% endif %}
{% endfor %}
{% endif %}
```

**Pattern**: Commands always include `Command` and `Command_Types`. Variable length types trigger `Serializer_Types` with automatic `use` clause. Argument type packages are included but duplicates are filtered out.

## Abstract vs Concrete Procedures

### Base Class Abstract Procedures (Users Must Override)

From `component-name.ads`:

**Init procedure:**
```jinja2
{% if init %}
not overriding procedure Init (Self : in out Base_Instance{% if init.parameters %}; {{ init.parameter_declaration_string() }}{% endif %}) is abstract;
{% endif %}
```
- Only generated if YAML has `init:` section
- Parameters come from `init.parameters` in component YAML

**Connector handlers:**
```jinja2
{% for connector in connectors.invokee() %}
{% if connector.kind == "return" %}
not overriding function {{ connector.name }} (Self : in out Base_Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}) return {{ connector.return_type }} is abstract;
{% elif connector.kind == "service" %}
not overriding function {{ connector.name }} (Self : in out Base_Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}; Arg : {{ connector.mode }} {{ connector.type }}) return {{ connector.return_type }} is abstract;
{% else %}
not overriding procedure {{ connector.name }} (Self : in out Base_Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}; Arg : {{ connector.mode }} {{ connector.type }}) is abstract;
{% endif %}
{% endfor %}
```

**Key patterns:**
1. Index parameter only for arrayed connectors (`count == 0` or `count > 1`)
2. `return` and `service` connectors generate functions, others generate procedures
3. All invokee connectors require user implementation

**Dropped handlers (abstract):**
```jinja2
{% for connector in connectors.of_kind("send") %}
not overriding procedure {{ connector.name }}_Dropped (Self : in out Base_Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}; Arg : in {{ connector.type }}) is abstract;
{% endfor %}
```
- Every `send` connector requires a dropped handler
- Can be implemented as `is null` in implementation

**Command handlers (when commands.yaml exists):**
```jinja2
{% for command in commands %}
not overriding function {{ command.name }} (Self : in out Base_Instance{% if command.type %}; Arg : in {{ command.type }}{% endif %}) return Command_Execution_Status.E is abstract;
{% endfor %}

not overriding procedure Invalid_Command (Self : in out Base_Instance; Cmd : in Command.T; Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type) is abstract;
```

### Concrete Procedures (Framework Provides)

**Connector send methods:**
```jinja2
{% for connector in connectors.invoker() %}
{% if connector.kind == "send" %}
not overriding procedure {{ connector.name }}_Send_If_Connected (Self : in out Base_Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}; Arg : in {{ connector.type }});
not overriding procedure {{ connector.name }}_Send (Self : in out Base_Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}; Arg : in {{ connector.type }});
not overriding function Is_{{ connector.name }}_Connected (Self : in Base_Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}) return Boolean;
{% elif connector.kind == "get" %}
not overriding function {{ connector.name }} (Self : in Base_Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}) return {{ connector.return_type }};
{% endif %}
{% endfor %}
```

**Built-in lifecycle methods:**
- `Set_Id_Bases` (when component has commands/events/data products)
- `Map_Data_Dependencies` (when data_dependencies.yaml exists)
- `Init_Base` (when init_base section in YAML)

## Connector Count Edge Cases

### Zero Connectors (`count: 0`)
- Generates array access with dynamic index type
- Assembly determines array size at generation time
- Index type: `subtype Name_Index is Connector_Index_Type`
- Storage: `Name_Array_Access` (pointer to array)

### Single Connector (`count: 1` or omitted)
- No index parameter in connector methods
- Direct instance storage: `Connector_Name : Name_Connector.Instance`
- Most common case

### Multiple Fixed Count (`count: N` where N > 1)
- Fixed-size array with specific range
- Index type: `subtype Name_Index is Connector_Index_Type range First .. First + N - 1`
- Storage: `Name_Array` (fixed array, not access)

### Implementation Template Patterns

From `component-name-implementation.ads`:

**Invokee connector overrides:**
```jinja2
{% for connector in connectors.invokee() %}
{% if connector.kind == "return" %}
overriding function {{ connector.name }} (Self : in out Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}) return {{ connector.return_type }};
{% elif connector.kind == "service" %}
overriding function {{ connector.name }} (Self : in out Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}; Arg : {{ connector.mode }} {{ connector.type }}) return {{ connector.return_type }};
{% else %}
overriding procedure {{ connector.name }} (Self : in out Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}; Arg : {{ connector.mode }} {{ connector.type }});
{% endif %}
{% if connector.kind == "recv_async" %}
-- This procedure is called when a {{ connector.name }} message is dropped due to a full queue.
overriding procedure {{ connector.name }}_Dropped (Self : in out Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}; Arg : {{ connector.mode }} {{ connector.type }});
{% endif %}
{% endfor %}
```

**Key finding**: `recv_async` connectors get both regular handler AND dropped handler in implementation template.

**Dropped handler defaults:**
```jinja2
{% for connector in connectors.of_kind("send") %}
-- This procedure is called when a {{ connector.name }} message is dropped due to a full queue.
overriding procedure {{ connector.name }}_Dropped (Self : in out Instance{% if connector.count == 0 or connector.count > 1 %}; Index : in {{ connector.name }}_Index{% endif %}; Arg : in {{ connector.type }}) is null;
{% endfor %}
```

**Pattern**: Implementation templates provide `is null` defaults for send connector dropped handlers.

## Tester Reciprocal Patterns

### Connector Package Generation

**For invokee connectors (component's inputs become tester's outputs):**
```jinja2
{% for connector in connectors.invokee() %}
{% if connector.common and not generic %}
package {{ connector.tester_name }}_Connector renames Common_Connectors.{{ connector.common_connector_package }};
{% elif connector.kind == "return" %}
package {{ connector.tester_name }}_Connector is new {{ connector.connector_package }} ({{ connector.return_type }});
{% elif connector.kind == "service" %}
package {{ connector.tester_name }}_Connector is new {{ connector.connector_package }} ({{ connector.type }}, {{ connector.return_type }});
{% else %}
package {{ connector.tester_name }}_Connector is new {{ connector.connector_package }} ({{ connector.type }});
{% endif %}
```

**Critical pattern**: `common` connectors use `renames` for efficiency, others use generic instantiation.

**Array connector handling in tester:**
```jinja2
{% if connector.count == 0   %}
subtype {{ connector.tester_name }}_Index is Connector_Index_Type;
type {{ connector.tester_name }}_Array is array ({{ connector.tester_name }}_Index range <>) of {{ connector.tester_name }}_Connector.Instance;
type {{ connector.tester_name }}_Array_Access is access {{ connector.tester_name }}_Array;
{% elif connector.count > 1 %}
subtype {{ connector.tester_name }}_Index is Connector_Index_Type range Connector_Index_Type'First .. Connector_Index_Type'First + {{ connector.count }} - 1;
type {{ connector.tester_name }}_Array is array ({{ connector.tester_name }}_Index) of {{ connector.tester_name }}_Connector.Instance;
{% endif %}
```

### Suite Object Generation

**Feature suite instances:**
```jinja2
{% if commands %}
-- Command suite object instance:
Commands : {{ commands.name }}.Instance;
{% endif %}
{% if parameters %}
-- Parameter suite object instance:  
Parameters : {{ parameters.name }}.Instance;
{% endif %}
<!-- similar for events, data_products, faults, packets, data_dependencies -->
```

**System time handling:**
```jinja2
{% if data_dependencies %}
-- System time for test. Make this non-zero to data dependencies don't report as stale.
System_Time : Sys_Time.T := (10000, 0);
{% else %}
-- System time for test:
System_Time : Sys_Time.T := (0, 0);
{% endif %}
```

**Key insight**: Components with data dependencies get non-zero default system time to avoid staleness errors in tests.

## Critical Edge Cases Not Documented in Skills

### 1. Array Connector Index Calculation
- `count: 0` uses dynamic sizing determined by assembly
- `count: N` uses fixed range `First .. First + N - 1`  
- Testers always use `First .. First` (single index) for invokee connectors

### 2. Generic Component Handling  
- `pragma Warnings` used extensively in tester reciprocals for generic components
- `common` connectors handled differently in generic vs non-generic components

### 3. Parameter Protected Object Generation
When `parameters.yaml` exists, extensive protected object code is generated in base body:
- Staged vs active parameter distinction
- Protected staging/fetching functions per parameter
- Table ID tracking for parameter updates
- Ready-to-update flag management

### 4. Variable Length Type Handling
Commands with variable-length argument types get different function signatures:
```jinja2
{% if command.type and command.type_model and command.type_model.variable_length %}
not overriding function {{ command.name }} (Self : in Instance{% if command.type %}; Arg : in {{ command.type }}{% endif %}; Cmd : out Command.T) return Serialization_Status;
{% else %}
not overriding function {{ command.name }} (Self : in Instance{% if command.type %}; Arg : in {{ command.type }}{% endif %}) return Command.T;
{% endif %}
```

### 5. Logging Verbosity in Tester Reciprocals
Tester reciprocals have sophisticated logging that changes based on message type:
- Framework types (Event, Data_Product, etc.) can log header-only or full representation
- Custom types always log full representation
- Different log prefixes for different connector directions (`->`, `--`)

### 6. Compile-Time Size Checking
Commands package generates compile-time errors if argument types exceed buffer size:
```jinja2
pragma Compile_Time_Error (
   {{ command.type_package }}.Size_In_Bytes > Command_Types.Command_Arg_Buffer_Type'Length,
   "Command '{{ command.name }}' has argument of type '{{ command.type }}' which has a maximum serialized length larger than the buffer size of Command.T."
);
```

## Summary

The templates reveal significant conditional logic based on:
- Connector counts and kinds
- Presence of feature YAML files
- Generic vs non-generic components  
- Variable-length types
- Common vs custom connector types

The edge cases around array connectors, parameter handling, and tester generation are more complex than documented in the skills. Understanding these patterns explains why certain component patterns work and helps predict what will be generated for edge cases.