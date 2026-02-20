#!/usr/bin/env python3
"""
adamant_scaffold.py - Generate Adamant component file scaffolding from a spec.

Creates all YAML models, implementation stubs, and test directory structure
for a new Adamant component. Does NOT generate code (that requires redo).

Usage:
    python3 adamant_scaffold.py <spec_file>

Spec file is a simple YAML description of the desired component. Example:

    name: voltage_monitor
    description: Monitors bus voltage and raises faults
    execution: passive
    init:
      - name: Low_Threshold
        type: Short_Float
        description: Lower voltage threshold
      - name: High_Threshold
        type: Short_Float
        description: Upper voltage threshold
    connectors:
      recv_sync:
        - type: Tick.T
          description: Periodic tick input
      send:
        - type: Event.T
          description: Event output
        - type: Data_Product.T
          description: Data product output
        - type: Fault.T
          description: Fault output
      request:
        - type: Data_Product_Fetch.T
          return_type: Data_Product_Return.T
          description: Data product fetch for data dependencies
      get:
        - type: Sys_Time.T
          description: System time
    events:
      - name: Voltage_Normal
        description: Voltage has returned to normal range
        param_type: Packed_F32.T
      - name: Data_Fetch_Failed
        description: Failed to fetch bus voltage
    data_products:
      - name: Last_Voltage
        type: Packed_F32.T
        description: Most recently read bus voltage
    faults:
      - name: Undervoltage_Fault
        description: Bus voltage below threshold
        param_type: Packed_F32.T
    data_dependencies:
      description: Data dependencies for voltage monitor
      items:
        - name: Bus_Voltage
          type: Packed_F32.T
          description: Current bus voltage reading
    commands:
      - name: Reset_Faults
        description: Clear all active faults
    parameters:
      description: Configurable voltage thresholds
      items:
        - name: Low_Threshold
          type: Packed_F32.T
          default: "3.0"
          description: Lower voltage threshold

Output: creates component directory with all files under current working directory.
"""

import sys
import os
import yaml


def snake_to_mixed(name):
    """Convert snake_case to Mixed_Case."""
    return "_".join(w.capitalize() for w in name.split("_"))


def generate_component_yaml(spec, output_dir):
    """Generate the main component YAML."""
    name = spec["name"]
    content = {
        "---": None,
        "description": spec.get("description", f"{snake_to_mixed(name)} component"),
        "execution": spec.get("execution", "passive"),
    }

    # Build as ordered text to preserve YAML style
    lines = ["---"]
    lines.append(f"description: {spec.get('description', snake_to_mixed(name) + ' component')}")
    lines.append(f"execution: {spec.get('execution', 'passive')}")

    if spec.get("init"):
        lines.append("init:")
        for param in spec["init"]:
            lines.append(f"  - name: {param['name']}")
            lines.append(f"    type: {param['type']}")
            if "default" in param:
                lines.append(f'    default: "{param["default"]}"')
            if "description" in param:
                lines.append(f"    description: {param['description']}")

    if spec.get("connectors"):
        lines.append("connectors:")
        conn = spec["connectors"]

        for direction in ["recv_sync", "recv_async"]:
            if direction in conn:
                lines.append(f"  - description: {conn[direction][0].get('description', direction + ' connector')}")
                lines.append(f"    type: {conn[direction][0]['type']}")
                lines.append(f"    kind: {direction}")
                if conn[direction][0].get("name"):
                    lines.append(f"    name: {conn[direction][0]['name']}")
                # Handle multiple of same direction
                for c in conn[direction][1:]:
                    lines.append(f"  - description: {c.get('description', direction + ' connector')}")
                    lines.append(f"    type: {c['type']}")
                    lines.append(f"    kind: {direction}")
                    if c.get("name"):
                        lines.append(f"    name: {c['name']}")

        for direction in ["send", "get", "request"]:
            if direction in conn:
                for c in conn[direction]:
                    lines.append(f"  - description: {c.get('description', direction + ' connector')}")
                    lines.append(f"    type: {c['type']}")
                    if direction == "request":
                        lines.append(f"    return_type: {c.get('return_type', 'Not_Specified')}")
                    lines.append(f"    kind: {direction}")
                    if c.get("name"):
                        lines.append(f"    name: {c['name']}")
                    if c.get("count"):
                        lines.append(f"    count: {c['count']}")

    path = os.path.join(output_dir, f"{name}.component.yaml")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def generate_events_yaml(spec, output_dir):
    """Generate events YAML."""
    if not spec.get("events"):
        return None
    name = spec["name"]
    lines = ["---"]
    lines.append(f"description: Events for {snake_to_mixed(name)}")
    lines.append("events:")
    for evt in spec["events"]:
        lines.append(f"  - name: {evt['name']}")
        lines.append(f"    description: {evt.get('description', evt['name'])}")
        if evt.get("param_type"):
            lines.append(f"    param_type: {evt['param_type']}")
    path = os.path.join(output_dir, f"{name}.events.yaml")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def generate_data_products_yaml(spec, output_dir):
    """Generate data products YAML."""
    if not spec.get("data_products"):
        return None
    name = spec["name"]
    lines = ["---"]
    lines.append(f"description: Data products for {snake_to_mixed(name)}")
    lines.append("data_products:")
    for dp in spec["data_products"]:
        lines.append(f"  - name: {dp['name']}")
        lines.append(f"    type: {dp['type']}")
        if "description" in dp:
            lines.append(f"    description: {dp['description']}")
    path = os.path.join(output_dir, f"{name}.data_products.yaml")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def generate_commands_yaml(spec, output_dir):
    """Generate commands YAML."""
    if not spec.get("commands"):
        return None
    name = spec["name"]
    lines = ["---"]
    lines.append(f"description: Commands for {snake_to_mixed(name)}")
    lines.append("commands:")
    for cmd in spec["commands"]:
        lines.append(f"  - name: {cmd['name']}")
        lines.append(f"    description: {cmd.get('description', cmd['name'])}")
        if cmd.get("arg_type"):
            lines.append(f"    arg_type: {cmd['arg_type']}")
    path = os.path.join(output_dir, f"{name}.commands.yaml")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def generate_parameters_yaml(spec, output_dir):
    """Generate parameters YAML."""
    if not spec.get("parameters"):
        return None
    name = spec["name"]
    params = spec["parameters"]
    lines = ["---"]
    lines.append(f"description: {params.get('description', 'Parameters for ' + snake_to_mixed(name))}")
    lines.append("parameters:")
    for p in params.get("items", []):
        lines.append(f"  - name: {p['name']}")
        lines.append(f"    type: {p['type']}")
        if "default" in p:
            lines.append(f'    default: "{p["default"]}"')
        if "description" in p:
            lines.append(f"    description: {p['description']}")
    path = os.path.join(output_dir, f"{name}.parameters.yaml")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def generate_faults_yaml(spec, output_dir):
    """Generate faults YAML."""
    if not spec.get("faults"):
        return None
    name = spec["name"]
    lines = ["---"]
    lines.append(f"description: Faults for {snake_to_mixed(name)}")
    lines.append("faults:")
    for fault in spec["faults"]:
        lines.append(f"  - name: {fault['name']}")
        lines.append(f"    description: {fault.get('description', fault['name'])}")
        if fault.get("param_type"):
            lines.append(f"    param_type: {fault['param_type']}")
    path = os.path.join(output_dir, f"{name}.faults.yaml")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def generate_data_dependencies_yaml(spec, output_dir):
    """Generate data dependencies YAML."""
    if not spec.get("data_dependencies"):
        return None
    name = spec["name"]
    dd = spec["data_dependencies"]
    lines = ["---"]
    lines.append(f"description: {dd.get('description', 'Data dependencies for ' + snake_to_mixed(name))}")
    lines.append("data_dependencies:")
    for dep in dd.get("items", []):
        lines.append(f"  - name: {dep['name']}")
        lines.append(f"    type: {dep['type']}")
        if "description" in dep:
            lines.append(f"    description: {dep['description']}")
    path = os.path.join(output_dir, f"{name}.data_dependencies.yaml")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def generate_implementation_spec(spec, output_dir):
    """Generate the implementation spec (.ads) stub."""
    name = spec["name"]
    mixed = snake_to_mixed(name)

    lines = []
    lines.append(f"-- {mixed} Implementation Spec")
    lines.append(f"--")
    lines.append(f"-- {spec.get('description', mixed + ' component')}")

    with_clauses = set()
    # Add with clauses based on features
    if spec.get("data_dependencies"):
        with_clauses.add("Data_Product_Enums")
    if spec.get("commands"):
        with_clauses.add("Command_Enums")

    for w in sorted(with_clauses):
        lines.append(f"with {w};")
    lines.append("")
    lines.append(f"package Component.{mixed}.Implementation is")
    lines.append("")
    lines.append(f"   type Instance is new Base_Instance with private;")
    lines.append("")
    lines.append("private")
    lines.append("")
    lines.append(f"   type Instance is new Base_Instance with record")
    lines.append(f"      -- TODO: Add component state fields here")
    lines.append(f"      null;")
    lines.append(f"   end record;")
    lines.append("")

    # Generate overriding stubs list as comments
    lines.append(f"   -- Required overrides (see generated base spec):")

    # Init
    if spec.get("init"):
        params = "; ".join(f"{p['name']} : in {p['type']}" for p in spec["init"])
        lines.append(f"   overriding procedure Init (Self : in out Instance; {params});")
    lines.append("")

    # Recv connectors
    if spec.get("connectors"):
        for direction in ["recv_sync", "recv_async"]:
            for c in spec["connectors"].get(direction, []):
                type_name = c["type"].replace(".", "_")
                proc_name = f"{type_name}_{direction.title().replace('_', '_')}"
                if c.get("name"):
                    proc_name = c["name"]
                lines.append(f"   overriding procedure {proc_name} (Self : in out Instance; Arg : in {c['type']});")
        lines.append("")

    # Commands
    if spec.get("commands"):
        lines.append("   -- Command handler:")
        lines.append("   overriding procedure Command_T_Recv_Sync (Self : in out Instance; Arg : in Command.T);")
        lines.append("")

    # Dropped handlers
    if spec.get("connectors"):
        for c in spec["connectors"].get("send", []):
            type_name = c["type"].replace(".", "_")
            lines.append(f"   overriding procedure {type_name}_Send_Dropped (Self : in out Instance; Arg : in {c['type']}) is null;")
        lines.append("")

    # Data dependency abstracts
    if spec.get("data_dependencies"):
        lines.append("   overriding function Get_Data_Dependency (Self : in out Instance; Id : in Data_Product_Types.Data_Product_Id) return Data_Product_Return.T;")
        lines.append("   overriding procedure Invalid_Data_Dependency (Self : in out Instance; Id : in Data_Product_Types.Data_Product_Id; Ret : in Data_Product_Return.T);")
        lines.append("")

    # Parameters
    if spec.get("parameters"):
        lines.append("   -- Parameter overrides:")
        params_list = spec["parameters"].get("items", [])
        validate_params = "; ".join(f"{p['name']} : in {p['type'].replace('.T', '.U')}" for p in params_list)
        lines.append(f"   overriding function Validate_Parameters (Self : in out Instance; {validate_params}) return Parameter_Validation_Status.E;")
        lines.append("   overriding procedure Update_Parameters_Action (Self : in out Instance);")
        lines.append("   overriding procedure Invalid_Parameter (Self : in out Instance; Par : in Parameter.T; Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type);")
        lines.append("")

    lines.append(f"end Component.{mixed}.Implementation;")

    path = os.path.join(output_dir, f"component-{name}-implementation.ads")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def generate_implementation_body(spec, output_dir):
    """Generate the implementation body (.adb) stub."""
    name = spec["name"]
    mixed = snake_to_mixed(name)

    lines = []
    lines.append(f"-- {mixed} Implementation Body")

    with_clauses = set()
    if spec.get("data_dependencies"):
        with_clauses.add("Data_Product_Enums")
        with_clauses.add("Data_Product_Return")
        with_clauses.add("Data_Product_Types")
    if spec.get("commands"):
        with_clauses.add("Command_Enums")
        with_clauses.add("Command")

    for w in sorted(with_clauses):
        lines.append(f"with {w};")
    lines.append("")
    lines.append(f"package body Component.{mixed}.Implementation is")
    lines.append("")

    # Init
    if spec.get("init"):
        params = "; ".join(f"{p['name']} : in {p['type']}" for p in spec["init"])
        lines.append(f"   overriding procedure Init (Self : in out Instance; {params}) is")
        lines.append(f"   begin")
        lines.append(f"      -- TODO: Store init parameters")
        for p in spec["init"]:
            lines.append(f"      -- Self.{p['name']} := {p['name']};")
        lines.append(f"   end Init;")
        lines.append("")

    # Recv handlers
    if spec.get("connectors"):
        for direction in ["recv_sync", "recv_async"]:
            for c in spec["connectors"].get(direction, []):
                type_name = c["type"].replace(".", "_")
                proc_name = f"{type_name}_{direction.title().replace('_', '_')}"
                if c.get("name"):
                    proc_name = c["name"]
                lines.append(f"   overriding procedure {proc_name} (Self : in out Instance; Arg : in {c['type']}) is")
                if spec.get("parameters"):
                    lines.append(f"   begin")
                    lines.append(f"      -- IMPORTANT: Call Update_Parameters first, then read parameter values")
                    lines.append(f"      Self.Update_Parameters;")
                else:
                    lines.append(f"   begin")
                lines.append(f"      -- TODO: Implement handler")
                lines.append(f"      null;")
                lines.append(f"   end {proc_name};")
                lines.append("")

    # Command handler
    if spec.get("commands"):
        lines.append("   overriding procedure Command_T_Recv_Sync (Self : in out Instance; Arg : in Command.T) is")
        lines.append("      use Command_Enums.Command_Execution_Status;")
        lines.append(f"      use {mixed}_Commands;")
        lines.append("   begin")
        lines.append("      case Self.Commands.Decode_Command (Arg).Id is")
        for cmd in spec["commands"]:
            lines.append(f"         when {cmd['name']}_Id =>")
            lines.append(f"            -- TODO: Implement {cmd['name']}")
            lines.append(f"            Self.Command_Response_T_Send (Self.Commands.Command_Response (Arg, Success));")
        lines.append("      end case;")
        lines.append("   end Command_T_Recv_Sync;")
        lines.append("")

    # Data dependency overrides
    if spec.get("data_dependencies"):
        lines.append("   overriding function Get_Data_Dependency (Self : in out Instance; Id : in Data_Product_Types.Data_Product_Id) return Data_Product_Return.T is")
        lines.append("   begin")
        lines.append("      return Self.Data_Product_Fetch_T_Request ((Id => Id));")
        lines.append("   end Get_Data_Dependency;")
        lines.append("")
        lines.append("   overriding procedure Invalid_Data_Dependency (Self : in out Instance; Id : in Data_Product_Types.Data_Product_Id; Ret : in Data_Product_Return.T) is")
        lines.append("   begin")
        lines.append("      -- TODO: Handle invalid data dependency")
        lines.append("      null;")
        lines.append("   end Invalid_Data_Dependency;")
        lines.append("")

    # Parameter overrides
    if spec.get("parameters"):
        params_list = spec["parameters"].get("items", [])
        validate_params = "; ".join(f"{p['name']} : in {p['type'].replace('.T', '.U')}" for p in params_list)
        lines.append(f"   overriding function Validate_Parameters (Self : in out Instance; {validate_params}) return Parameter_Validation_Status.E is")
        lines.append("      use Parameter_Enums.Parameter_Validation_Status;")
        lines.append("   begin")
        lines.append("      -- TODO: Validate parameter values")
        lines.append("      return Valid;")
        lines.append("   end Validate_Parameters;")
        lines.append("")
        lines.append("   overriding procedure Update_Parameters_Action (Self : in out Instance) is")
        lines.append("   begin")
        lines.append("      -- Called after parameters are updated. Access new values via Self.Param_Name.Value")
        lines.append("      null;")
        lines.append("   end Update_Parameters_Action;")
        lines.append("")
        lines.append("   overriding procedure Invalid_Parameter (Self : in out Instance; Par : in Parameter.T; Errant_Field_Number : in Unsigned_32; Errant_Field : in Basic_Types.Poly_Type) is")
        lines.append("   begin")
        lines.append("      null;")
        lines.append("   end Invalid_Parameter;")
        lines.append("")

    lines.append(f"end Component.{mixed}.Implementation;")

    path = os.path.join(output_dir, f"component-{name}-implementation.adb")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def generate_test_infrastructure(spec, output_dir):
    """Generate test directory with tests.yaml and env.py."""
    name = spec["name"]
    test_dir = os.path.join(output_dir, "test")
    os.makedirs(test_dir, exist_ok=True)

    # tests.yaml
    lines = ["---"]
    lines.append(f"description: {snake_to_mixed(name)} unit tests")
    lines.append(f"tests:")
    lines.append(f"  - name: {snake_to_mixed(name)}_Tests")
    lines.append(f"    component: {snake_to_mixed(name)}")
    path = os.path.join(test_dir, f"{name}.tests.yaml")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

    # env.py
    env_lines = [
        "from environments import test",
    ]
    path = os.path.join(test_dir, "env.py")
    with open(path, "w") as f:
        f.write("\n".join(env_lines) + "\n")

    return test_dir


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <spec_file.yaml>", file=sys.stderr)
        sys.exit(1)

    spec_file = sys.argv[1]
    with open(spec_file) as f:
        spec = yaml.safe_load(f)

    name = spec["name"]

    # Determine output directory
    output_dir = os.path.join("src", "components", name)
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    os.makedirs(output_dir, exist_ok=True)

    created = []

    # Generate all files
    created.append(generate_component_yaml(spec, output_dir))
    if spec.get("events"):
        created.append(generate_events_yaml(spec, output_dir))
    if spec.get("data_products"):
        created.append(generate_data_products_yaml(spec, output_dir))
    if spec.get("commands"):
        created.append(generate_commands_yaml(spec, output_dir))
    if spec.get("parameters"):
        created.append(generate_parameters_yaml(spec, output_dir))
    if spec.get("faults"):
        created.append(generate_faults_yaml(spec, output_dir))
    if spec.get("data_dependencies"):
        created.append(generate_data_dependencies_yaml(spec, output_dir))
    created.append(generate_implementation_spec(spec, output_dir))
    created.append(generate_implementation_body(spec, output_dir))
    test_dir = generate_test_infrastructure(spec, output_dir)
    created.append(os.path.join(test_dir, f"{name}.tests.yaml"))
    created.append(os.path.join(test_dir, "env.py"))

    print(f"Scaffolded {name} component:")
    for f in created:
        if f:
            print(f"  {f}")
    print()
    print("Next steps:")
    print(f"  1. Review and edit the generated files")
    print(f"  2. Run: redo {output_dir}/build/src/component-{name}.ads")
    print(f"  3. Run: redo {output_dir}/test/build/template/  (to generate test templates)")
    print(f"  4. Copy templates: cp {output_dir}/test/build/template/*.ads {output_dir}/test/")
    print(f"  5. Edit test body: {output_dir}/test/{name}_tests-implementation.adb")
    print(f"  6. Run tests: cd {output_dir}/test && redo test")


if __name__ == "__main__":
    main()
