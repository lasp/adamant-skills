#!/usr/bin/env python3
"""
adamant_validate_yaml.py - Validate Adamant YAML models against common errors.

Checks component, events, data_products, commands, parameters, faults, and
data_dependencies YAML files for structural issues that would cause redo to
fail. Does NOT require Docker or the Adamant build environment.

This is a fast pre-flight check, not a schema validator. It catches the
errors that cold-start agents most commonly make.

Usage:
    python3 adamant_validate_yaml.py <component_dir>

Example:
    python3 adamant_validate_yaml.py src/components/voltage_monitor
"""

import sys
import os
import glob
import yaml

# Try to use pykwalify for authoritative schema validation (available inside Docker)
try:
    from pykwalify.core import Core as PykwalifyCore
    HAS_PYKWALIFY = True
except ImportError:
    HAS_PYKWALIFY = False


# Framework component names that will collide
FRAMEWORK_COMPONENTS = {
    "command_router", "command_sequencer", "event_filter", "event_limiter",
    "event_packetizer", "event_forward", "fault_correction", "ccsds_command_depacketizer",
    "ccsds_packetizer", "ccsds_serial_interface", "ccsds_subpacket_extractor",
    "ccsds_downsampler", "command_protector", "command_response_enforcer",
    "counter_reporter", "cpu_monitor", "data_product_database",
    "data_product_dumper", "data_product_extractor", "data_product_packetizer",
    "event_text_logger", "fault_reporter", "interrupt_listener",
    "interrupt_servicer", "last_chance_handler", "memory_copier", "memory_dumper",
    "memory_manager", "memory_stuffer", "osa_shell", "packet_depacketizer",
    "parameter_manager", "parameter_store", "pid_controller", "product_database",
    "product_packetizer", "queue_monitor", "rate_group", "sequence_store",
    "stack_monitor", "task_watchdog", "ticker", "zero_divider",
    "adc_data_collector", "analog_filter", "ata_interface",
    "bytestreamproducer", "compression_engine",
}


class ValidationError:
    def __init__(self, file, message, severity="ERROR"):
        self.file = file
        self.message = message
        self.severity = severity

    def __str__(self):
        return f"  [{self.severity}] {self.file}: {self.message}"


def validate_component_yaml(path, comp_name):
    """Validate main component YAML."""
    errors = []
    with open(path) as f:
        data = yaml.safe_load(f)

    if not data:
        errors.append(ValidationError(path, "Empty YAML file"))
        return errors

    # Check required fields
    if "description" not in data:
        errors.append(ValidationError(path, "Missing 'description' field"))

    if "execution" not in data:
        errors.append(ValidationError(path, "Missing 'execution' field"))
    elif data["execution"] not in ("active", "passive"):
        errors.append(ValidationError(path, f"Invalid execution: '{data['execution']}' (must be 'active' or 'passive')"))

    # Check name collision
    if comp_name in FRAMEWORK_COMPONENTS:
        errors.append(ValidationError(path, f"Name '{comp_name}' collides with framework component"))

    # Check connectors
    if "connectors" in data:
        if not isinstance(data["connectors"], list):
            errors.append(ValidationError(path, "connectors must be a list"))
        else:
            has_command_recv = False
            has_command_response_send = False
            has_param_modify = False
            has_event_send = False
            has_dp_send = False
            has_fault_send = False

            for i, conn in enumerate(data["connectors"]):
                if "type" not in conn and "return_type" not in conn:
                    errors.append(ValidationError(path, f"Connector {i}: missing 'type' (or 'return_type' for get connectors)"))
                elif "type" not in conn and conn.get("kind") == "get":
                    pass  # get connectors can use return_type only
                if "kind" not in conn:
                    errors.append(ValidationError(path, f"Connector {i}: missing 'kind'"))
                elif conn["kind"] not in ("recv_sync", "recv_async", "send", "get", "request", "modify", "provide"):
                    errors.append(ValidationError(path, f"Connector {i}: invalid kind '{conn['kind']}'"))

                conn_type = conn.get("type", "")
                conn_kind = conn.get("kind", "")

                if conn_type == "Command.T" and conn_kind in ("recv_sync", "recv_async"):
                    has_command_recv = True
                if conn_type == "Command_Response.T" and conn_kind == "send":
                    has_command_response_send = True
                if conn_type == "Parameter_Update.T" and conn_kind == "modify":
                    has_param_modify = True
                if conn_type == "Event.T" and conn_kind == "send":
                    has_event_send = True
                if conn_type == "Data_Product.T" and conn_kind == "send":
                    has_dp_send = True
                if conn_type == "Fault.T" and conn_kind == "send":
                    has_fault_send = True

            # Check that command handler components have response send
            # Only flag if this component defines commands (has commands.yaml) --
            # components that recv Command.T for logging/forwarding don't need responses
            comp_dir_check = os.path.dirname(path)
            comp_base = os.path.splitext(os.path.basename(path))[0].replace(".component", "")
            has_commands_yaml = os.path.isfile(os.path.join(comp_dir_check, f"{comp_base}.commands.yaml"))
            if has_command_recv and not has_command_response_send and has_commands_yaml:
                errors.append(ValidationError(path, "Has Command.T recv and commands.yaml but missing Command_Response.T send connector"))

    # Check init params (can be a list or dict with 'parameters' key)
    if "init" in data:
        init_data = data["init"]
        init_params = []
        if isinstance(init_data, list):
            init_params = init_data
        elif isinstance(init_data, dict) and "parameters" in init_data:
            init_params = init_data["parameters"]
        elif isinstance(init_data, dict):
            # Could be other init formats
            pass
        else:
            errors.append(ValidationError(path, "init must be a list or dict with 'parameters' key"))

        for i, param in enumerate(init_params):
            if "name" not in param:
                errors.append(ValidationError(path, f"Init param {i}: missing 'name'"))
            if "type" not in param:
                errors.append(ValidationError(path, f"Init param {i}: missing 'type'"))
            # Check defaults are strings
            if "default" in param and not isinstance(param["default"], str):
                errors.append(ValidationError(path, f"Init param '{param.get('name', i)}': default must be a string (got {type(param['default']).__name__})", "WARNING"))

    return errors


def validate_feature_yaml(path, kind):
    """Validate events/data_products/commands/faults/parameters YAML."""
    errors = []
    with open(path) as f:
        data = yaml.safe_load(f)

    if not data:
        errors.append(ValidationError(path, "Empty YAML file"))
        return errors

    key_map = {
        "events": "events",
        "data_products": "data_products",
        "commands": "commands",
        "faults": "faults",
        "parameters": "parameters",
        "data_dependencies": "data_dependencies",
    }
    list_key = key_map.get(kind)

    if list_key and list_key not in data:
        errors.append(ValidationError(path, f"Missing '{list_key}' key"))
        return errors

    items = data.get(list_key, [])
    if not isinstance(items, list):
        errors.append(ValidationError(path, f"'{list_key}' must be a list"))
        return errors

    for i, item in enumerate(items):
        if "name" not in item:
            errors.append(ValidationError(path, f"Item {i}: missing 'name'"))
            continue

        name = item["name"]

        # Common checks
        if kind == "events":
            # param_type is optional
            if "type" in item:
                errors.append(ValidationError(path, f"Event '{name}': use 'param_type' not 'type'"))
        elif kind == "data_products":
            if "type" not in item:
                errors.append(ValidationError(path, f"Data product '{name}': missing 'type'"))
        elif kind == "commands":
            if "type" in item:
                errors.append(ValidationError(path, f"Command '{name}': use 'arg_type' not 'type'"))
        elif kind == "faults":
            if "type" in item:
                errors.append(ValidationError(path, f"Fault '{name}': use 'param_type' not 'type'"))
        elif kind == "parameters":
            if "type" not in item:
                errors.append(ValidationError(path, f"Parameter '{name}': missing 'type'"))
            if "default" in item and not isinstance(item["default"], str):
                errors.append(ValidationError(path, f"Parameter '{name}': default must be a string (got {type(item['default']).__name__})"))
        elif kind == "data_dependencies":
            if "type" not in item:
                errors.append(ValidationError(path, f"Data dependency '{name}': missing 'type'"))

    return errors


def validate_cross_consistency(comp_dir, comp_name):
    """Check cross-file consistency."""
    errors = []

    comp_path = os.path.join(comp_dir, f"{comp_name}.component.yaml")
    if not os.path.isfile(comp_path):
        return errors

    with open(comp_path) as f:
        comp_data = yaml.safe_load(f)

    if not comp_data or "connectors" not in comp_data:
        return errors

    connectors = comp_data["connectors"]
    conn_types = set()
    for c in connectors:
        if isinstance(c, dict):
            t = c.get("type", "")
            k = c.get("kind", "")
            conn_types.add((t, k))

    # Check feature files have matching connectors
    feature_files = {
        "events": ("Event.T", "send"),
        "data_products": ("Data_Product.T", "send"),
        "faults": ("Fault.T", "send"),
        "commands": ("Command.T", "recv_sync"),
        "parameters": ("Parameter_Update.T", "modify"),
    }

    for feature, (req_type, req_kind) in feature_files.items():
        feat_path = os.path.join(comp_dir, f"{comp_name}.{feature}.yaml")
        if os.path.isfile(feat_path):
            # Check connector exists
            has_conn = False
            for t, k in conn_types:
                if t == req_type:
                    has_conn = True
                    break
            if not has_conn:
                errors.append(ValidationError(
                    feat_path,
                    f"Feature file exists but component.yaml has no {req_type} {req_kind} connector"
                ))

    return errors


def validate_file_naming(comp_dir, comp_name):
    """Check file naming conventions."""
    errors = []

    # Implementation files
    spec = os.path.join(comp_dir, f"component-{comp_name}-implementation.ads")
    body = os.path.join(comp_dir, f"component-{comp_name}-implementation.adb")

    if not os.path.isfile(spec):
        errors.append(ValidationError(comp_dir, f"Missing implementation spec: component-{comp_name}-implementation.ads"))
    if not os.path.isfile(body):
        errors.append(ValidationError(comp_dir, f"Missing implementation body: component-{comp_name}-implementation.adb"))

    # Test directory
    test_dir = os.path.join(comp_dir, "test")
    if os.path.isdir(test_dir):
        tests_yaml = os.path.join(test_dir, f"{comp_name}.tests.yaml")
        env_py = os.path.join(test_dir, "env.py")
        if not os.path.isfile(tests_yaml):
            errors.append(ValidationError(test_dir, f"Missing tests YAML: {comp_name}.tests.yaml"))
        if not os.path.isfile(env_py):
            errors.append(ValidationError(test_dir, "Missing env.py"))

        # Check env.py content
        if os.path.isfile(env_py):
            with open(env_py) as f:
                content = f.read()
            if "from environments import test" not in content:
                errors.append(ValidationError(env_py, "env.py should contain 'from environments import test'"))
            # Check for .all_path (should NOT exist in test dirs)
            all_path = os.path.join(test_dir, ".all_path")
            if os.path.isfile(all_path):
                errors.append(ValidationError(test_dir, ".all_path should NOT exist in test directories (use env.py only)"))

    return errors


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <component_dir>", file=sys.stderr)
        sys.exit(1)

    comp_dir = sys.argv[1]
    if not os.path.isdir(comp_dir):
        print(f"Error: {comp_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    comp_name = os.path.basename(os.path.normpath(comp_dir))
    all_errors = []

    # Detect assembly directories -- skip component validation
    assembly_yamls = glob.glob(os.path.join(comp_dir, "*.assembly.yaml"))
    if assembly_yamls:
        print(f"Assembly directory detected ({comp_name}). Component validation not applicable.")
        print(f"  Found: {', '.join(os.path.basename(f) for f in assembly_yamls)}")
        sys.exit(0)

    # Validate component YAML
    comp_yaml = os.path.join(comp_dir, f"{comp_name}.component.yaml")
    if os.path.isfile(comp_yaml):
        all_errors.extend(validate_component_yaml(comp_yaml, comp_name))
    else:
        all_errors.append(ValidationError(comp_dir, f"Missing {comp_name}.component.yaml"))

    # Validate feature YAMLs
    for kind in ("events", "data_products", "commands", "faults", "parameters", "data_dependencies"):
        feat_path = os.path.join(comp_dir, f"{comp_name}.{kind}.yaml")
        if os.path.isfile(feat_path):
            all_errors.extend(validate_feature_yaml(feat_path, kind))

    # Cross-consistency checks
    all_errors.extend(validate_cross_consistency(comp_dir, comp_name))

    # File naming
    all_errors.extend(validate_file_naming(comp_dir, comp_name))

    # pykwalify schema validation (if available and SCHEMAPATH set)
    schema_dir = os.environ.get("SCHEMAPATH")
    if HAS_PYKWALIFY and schema_dir and os.path.isdir(schema_dir):
        schema_map = {
            "component": "component.yaml",
            "events": "events.yaml",
            "data_products": "data_products.yaml",
            "commands": "commands.yaml",
            "parameters": "parameters.yaml",
            "faults": "faults.yaml",
            "data_dependencies": "data_dependencies.yaml",
        }
        for kind, schema_file in schema_map.items():
            yaml_file = os.path.join(comp_dir, f"{comp_name}.{kind}.yaml")
            schema_path = os.path.join(schema_dir, schema_file)
            if os.path.isfile(yaml_file) and os.path.isfile(schema_path):
                try:
                    c = PykwalifyCore(source_file=yaml_file, schema_files=[schema_path])
                    c.validate(raise_exception=True)
                except Exception as e:
                    # Extract just the validation error message
                    msg = str(e).split("\n")[0] if "\n" in str(e) else str(e)
                    all_errors.append(ValidationError(yaml_file, f"Schema validation: {msg}"))
        if not all_errors:
            print(f"Validation: PASS ({comp_name}) [pykwalify schema-validated]")
        else:
            pass  # Fall through to error output below
    elif HAS_PYKWALIFY and not schema_dir:
        pass  # pykwalify available but no SCHEMAPATH -- use heuristic checks only

    # Output
    error_count = sum(1 for e in all_errors if e.severity == "ERROR")
    warn_count = sum(1 for e in all_errors if e.severity == "WARNING")

    if all_errors:
        print(f"Validation: {error_count} error(s), {warn_count} warning(s)")
        for e in all_errors:
            print(str(e))
        if error_count > 0:
            sys.exit(1)
    elif not (HAS_PYKWALIFY and schema_dir):
        print(f"Validation: PASS ({comp_name}) [heuristic only -- install pykwalify + set SCHEMAPATH for full validation]")


if __name__ == "__main__":
    main()
