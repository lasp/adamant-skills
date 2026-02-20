#!/usr/bin/env python3
"""
adamant_inspect.py - Extract and summarize the generated API for an Adamant component.

Parses generated Ada spec files from build/src/ and build/template/ to produce
a concise summary of the component's API: connectors, methods to override,
available helpers, events, data products, commands, parameters, faults, and
data dependencies.

Usage:
    python3 adamant_inspect.py <component_dir>

Example:
    python3 adamant_inspect.py src/components/voltage_monitor

Output is plain text, suitable for pasting into a prompt or reading in a terminal.
"""

import sys
import os
import re
import glob


def find_files(component_dir):
    """Locate generated spec files."""
    build_src = os.path.join(component_dir, "build", "src")
    build_template = os.path.join(component_dir, "build", "template")
    test_build_src = os.path.join(component_dir, "test", "build", "src")
    test_build_template = os.path.join(component_dir, "test", "build", "template")

    result = {
        "base_spec": None,
        "events": None,
        "data_products": None,
        "commands": None,
        "parameters": None,
        "faults": None,
        "data_dependencies": None,
        "tester_spec": None,
        "impl_template": None,
    }

    if not os.path.isdir(build_src):
        return result

    # Component name from directory
    comp_name = os.path.basename(os.path.normpath(component_dir))

    for f in glob.glob(os.path.join(build_src, "*.ads")):
        base = os.path.basename(f)
        if base == f"component-{comp_name}.ads":
            result["base_spec"] = f
        elif base == f"{comp_name}_events.ads":
            result["events"] = f
        elif base == f"{comp_name}_data_products.ads":
            result["data_products"] = f
        elif base == f"{comp_name}_commands.ads":
            result["commands"] = f
        elif base == f"{comp_name}_parameters.ads":
            result["parameters"] = f
        elif base == f"{comp_name}_faults.ads":
            result["faults"] = f
        elif base == f"{comp_name}_data_dependencies.ads":
            result["data_dependencies"] = f

    # Template files
    template = os.path.join(build_template, f"component-{comp_name}-implementation.ads")
    if os.path.isfile(template):
        result["impl_template"] = template

    tester = os.path.join(test_build_template, f"component-{comp_name}-implementation-tester.ads")
    if os.path.isfile(tester):
        result["tester_spec"] = tester

    return result


def extract_sections(text):
    """Split Ada spec into logical sections based on comment headers."""
    sections = []
    current_header = "Header"
    current_lines = []
    for line in text.splitlines():
        # Match section headers like "-- Invokee connector primitives:"
        m = re.match(r"^\s*-+\s*$", line)
        if m:
            # Check if previous line was a comment header
            if current_lines and re.match(r"^\s*--\s+\S", current_lines[-1]):
                header_line = current_lines.pop()
                if current_lines:
                    sections.append((current_header, "\n".join(current_lines)))
                current_header = header_line.strip().lstrip("- ").rstrip(":")
                current_lines = []
                continue
        current_lines.append(line)
    if current_lines:
        sections.append((current_header, "\n".join(current_lines)))
    return sections


def extract_abstract_procedures(text):
    """Extract abstract procedure/function declarations."""
    results = []
    # Multi-line aware: join continuation lines
    joined = re.sub(r"\n\s+", " ", text)
    for m in re.finditer(
        r"(not overriding\s+(?:procedure|function)\s+\w+\s*(?:\([^)]*\))?[^;]*)\s+is\s+abstract",
        joined,
    ):
        sig = m.group(1).strip()
        # Clean up whitespace
        sig = re.sub(r"\s+", " ", sig)
        results.append(sig)
    return results


def extract_concrete_procedures(text, section_name=""):
    """Extract concrete (non-abstract) procedure/function declarations in private section."""
    results = []
    joined = re.sub(r"\n\s+", " ", text)
    for m in re.finditer(
        r"(not overriding\s+(?:procedure|function)\s+(\w+)\s*(?:\([^)]*\))?(?:\s*return\s+[^;]+)?)",
        joined,
    ):
        full = m.group(1).strip()
        name = m.group(2)
        # Skip abstract ones
        after = joined[m.end():m.end() + 30]
        if "is abstract" in after:
            continue
        full = re.sub(r"\s+", " ", full)
        results.append((name, full))
    return results


def extract_init_params(text):
    """Extract Init procedure parameters."""
    joined = re.sub(r"\n\s+", " ", text)
    m = re.search(
        r"procedure Init\s*\(Self\s*:\s*in out Base_Instance;\s*([^)]+)\)\s*is\s+abstract",
        joined,
    )
    if m:
        params_str = m.group(1)
        params = []
        for p in params_str.split(";"):
            p = p.strip()
            if p:
                params.append(p)
        return params
    return []


def extract_set_id_bases(text):
    """Extract Set_Id_Bases parameters."""
    joined = re.sub(r"\n\s+", " ", text)
    m = re.search(
        r"procedure Set_Id_Bases\s*\(Self\s*:\s*in out Base_Instance;\s*([^)]+)\)",
        joined,
    )
    if m:
        params_str = m.group(1)
        params = []
        for p in params_str.split(";"):
            p = p.strip()
            if p:
                # Just the parameter name and type
                params.append(p)
        return params
    return []


def extract_connector_info(text):
    """Extract connector names, types, and directions from base spec."""
    invokee = []  # recv connectors (to override)
    invoker = []  # send/get/request connectors (to call)

    joined = re.sub(r"\n\s+", " ", text)
    lines = text.splitlines()

    # Find invokee (recv) connectors - look for abstract procedures
    for m in re.finditer(
        r"not overriding procedure (\w+_Recv_(?:Sync|Async))\s*\(Self\s*:\s*in out Base_Instance;\s*Arg\s*:\s*in\s+(\S+)\)\s*is\s+abstract",
        joined,
    ):
        invokee.append({"name": m.group(1), "type": m.group(2), "direction": "recv"})

    # Modify connectors (in out)
    for m in re.finditer(
        r"not overriding procedure (\w+_Modify)\s*\(Self\s*:\s*in out Base_Instance;\s*Arg\s*:\s*in out\s+(\S+)\)\s*is\s+abstract",
        joined,
    ):
        invokee.append({"name": m.group(1), "type": m.group(2), "direction": "modify"})

    # Find invoker (send) connectors - look for Attach_ procedures
    for m in re.finditer(
        r"procedure Attach_(\w+)\s*\(Self\s*:\s*in out Base_Instance",
        joined,
    ):
        name = m.group(1)
        invoker.append({"name": name})

    # Classify invoker connectors
    for inv in invoker:
        name = inv["name"]
        if "_Send" in name:
            inv["direction"] = "send"
        elif "_Get" in name:
            inv["direction"] = "get"
        elif "_Request" in name:
            inv["direction"] = "request"
        else:
            inv["direction"] = "invoke"

    return invokee, invoker


def extract_dropped_handlers(text):
    """Extract *_Dropped abstract procedures."""
    results = []
    joined = re.sub(r"\n\s+", " ", text)
    for m in re.finditer(
        r"not overriding procedure (\w+_Dropped)\s*\(Self\s*:\s*in out Base_Instance;\s*Arg\s*:\s*in\s+(\S+)\)\s*is\s+abstract",
        joined,
    ):
        results.append({"name": m.group(1), "type": m.group(2)})
    return results


def extract_data_dep_helpers(text):
    """Extract private data dependency helper functions (Get_*)."""
    results = []
    joined = re.sub(r"\n\s+", " ", text)
    for m in re.finditer(
        r"not overriding function (Get_\w+)\s*\(Self\s*:\s*in out Base_Instance;\s*([^)]+)\)\s*return\s+(\S+)",
        joined,
    ):
        # Skip abstract ones (Get_Data_Dependency)
        after = joined[m.end():m.end() + 30]
        if "is abstract" in after:
            continue
        results.append({"name": m.group(1), "params": m.group(2).strip(), "returns": m.group(3)})
    return results


def extract_send_helpers(text):
    """Extract private send/get/request helper procedures/functions."""
    results = []
    joined = re.sub(r"\n\s+", " ", text)

    # Send procedures
    for m in re.finditer(
        r"not overriding procedure (\w+_Send(?:_If_Connected)?)\s*\(Self\s*:\s*in out Base_Instance;\s*Arg\s*:\s*in\s+(\S+)",
        joined,
    ):
        results.append({"name": m.group(1), "kind": "procedure", "type": m.group(2)})

    # Get functions (no arg)
    for m in re.finditer(
        r"not overriding function (\w+_Get)\s*\(Self\s*:\s*in Base_Instance\)\s*return\s+(\S+)",
        joined,
    ):
        results.append({"name": m.group(1), "kind": "function", "type": m.group(2)})

    # Request functions (with arg)
    for m in re.finditer(
        r"not overriding function (\w+_Request)\s*\(Self\s*:\s*in Base_Instance;\s*Arg\s*:\s*in\s+(\S+)\)\s*return\s+(\S+)",
        joined,
    ):
        results.append({"name": m.group(1), "kind": "function", "arg_type": m.group(2), "type": m.group(3)})

    # Is_Connected checks
    for m in re.finditer(
        r"not overriding function (Is_\w+_Connected)\s*\(Self\s*:\s*in Base_Instance\)\s*return\s+Boolean",
        joined,
    ):
        results.append({"name": m.group(1), "kind": "function", "type": "Boolean"})

    return results


def extract_feature_items(text, kind):
    """Extract event/data_product/fault/command creation functions from feature spec."""
    results = []
    joined = re.sub(r"\n\s+", " ", text)

    if kind in ("events", "faults"):
        # Functions that create Event.T or Fault.T
        for m in re.finditer(
            r"not overriding function (\w+)\s*\(Self\s*:\s*in Instance;\s*Timestamp\s*:\s*Sys_Time\.T(?:;\s*Param\s*:\s*in\s+(\S+))?\)\s*return\s+(?:Event|Fault)\.T",
            joined,
        ):
            item = {"name": m.group(1)}
            if m.group(2):
                item["param_type"] = m.group(2)
            results.append(item)
    elif kind == "data_products":
        for m in re.finditer(
            r"not overriding function (\w+)\s*\(Self\s*:\s*in Instance;\s*Timestamp\s*:\s*Sys_Time\.T;\s*Item\s*:\s*in\s+(\S+)\)\s*return\s+Data_Product\.T",
            joined,
        ):
            results.append({"name": m.group(1), "type": m.group(2)})
    elif kind == "commands":
        for m in re.finditer(
            r"not overriding function (\w+)\s*\(Self\s*:\s*in Instance(?:;\s*([^)]+))?\)\s*return\s+Command\.T",
            joined,
        ):
            item = {"name": m.group(1)}
            if m.group(2):
                item["params"] = m.group(2).strip()
            results.append(item)

    return results


def extract_local_ids(text):
    """Extract local ID enum values."""
    results = []
    m = re.search(r"type Local_\w+_Id_Type is\s*\(([\s\S]*?)\);", text)
    if m:
        for name in re.findall(r"(\w+_Id)", m.group(1)):
            results.append(name)
    return results


def extract_parameter_info(text):
    """Extract parameter table info from parameters spec."""
    results = []
    joined = re.sub(r"\n\s+", " ", text)

    # Look for Validate_Parameters signature
    validate_sig = None
    m = re.search(
        r"not overriding function Validate_Parameters\s*\(Self\s*:\s*in Instance;\s*([^)]+)\)",
        joined,
    )
    if m:
        validate_sig = m.group(1).strip()

    # Look for parameter record fields
    m = re.search(r"type Parameter_Table_Type is record([\s\S]*?)end record", text)
    if m:
        for fm in re.finditer(r"(\w+)\s*:\s*([^;]+)", m.group(1)):
            results.append({"name": fm.group(1).strip(), "type": fm.group(2).strip()})

    return results, validate_sig


def extract_tester_histories(text):
    """Extract typed history fields from tester spec using section comments."""
    histories = {"connector": [], "event": [], "data_product": [], "fault": [], "command": []}

    section = None
    for line in text.splitlines():
        if "-- Connector histories:" in line:
            section = "connector"
            continue
        elif "-- Event histories:" in line:
            section = "event"
            continue
        elif "-- Data product histories:" in line:
            section = "data_product"
            continue
        elif "-- Fault histories:" in line:
            section = "fault"
            continue
        elif "-- Command histories:" in line:
            section = "command"
            continue
        elif re.match(r"\s+--\s", line) and section:
            # Another comment section header resets
            if "histor" not in line.lower():
                section = None
                continue
        elif "end record" in line:
            section = None
            continue

        if section:
            m = re.match(r"\s+(\w+)\s*:\s*\w+\.Instance", line)
            if m:
                histories[section].append(m.group(1))

    return histories


def extract_tester_overrides(text):
    """Extract override fields from tester (data dep values, return status, etc.)."""
    results = []
    for line in text.splitlines():
        # Look for fields with override-like names
        m = re.match(r"\s+(\w+)\s*:\s*([^;]+?)\s*:=\s*([^;]+);", line)
        if m:
            name = m.group(1).strip()
            typ = m.group(2).strip()
            default = m.group(3).strip()
            # Skip histories and the component instance
            if "History" in name or name == "Component_Instance":
                continue
            results.append({"name": name, "type": typ, "default": default})
    return results


def format_output(component_dir, files):
    """Format the extracted information into readable output."""
    comp_name = os.path.basename(os.path.normpath(component_dir))
    lines = []
    lines.append(f"{'=' * 70}")
    lines.append(f"  GENERATED API: {comp_name}")
    lines.append(f"{'=' * 70}")

    # --- Base spec ---
    if files["base_spec"]:
        with open(files["base_spec"]) as f:
            base_text = f.read()

        # Init params
        init_params = extract_init_params(base_text)
        if init_params:
            lines.append("")
            lines.append("INIT PARAMETERS:")
            for p in init_params:
                lines.append(f"  {p}")

        # Set_Id_Bases
        id_bases = extract_set_id_bases(base_text)
        if id_bases:
            lines.append("")
            lines.append("SET_ID_BASES:")
            for p in id_bases:
                lines.append(f"  {p}")

        # Connectors
        invokee, invoker = extract_connector_info(base_text)
        if invokee:
            lines.append("")
            lines.append("RECV CONNECTORS (override these):")
            for c in invokee:
                lines.append(f"  procedure {c['name']} (Self : in out; Arg : in {c['type']})")

        if invoker:
            lines.append("")
            lines.append("SEND/GET/REQUEST CONNECTORS (call these):")
            send_helpers = extract_send_helpers(base_text)
            for h in send_helpers:
                if h["kind"] == "procedure":
                    lines.append(f"  Self.{h['name']} (Arg)")
                elif "arg_type" in h:
                    lines.append(f"  Result := Self.{h['name']} (Arg)  -- returns {h['type']}")
                elif h["name"].startswith("Is_"):
                    lines.append(f"  Self.{h['name']}  -- returns Boolean")
                else:
                    lines.append(f"  Result := Self.{h['name']}  -- returns {h['type']}")

        # Dropped handlers
        dropped = extract_dropped_handlers(base_text)
        if dropped:
            lines.append("")
            lines.append("DROPPED HANDLERS (must override, usually null):")
            for d in dropped:
                lines.append(f"  procedure {d['name']} (Self : in out; Arg : in {d['type']})")

        # Data dependency helpers
        dep_helpers = extract_data_dep_helpers(base_text)
        if dep_helpers:
            lines.append("")
            lines.append("DATA DEPENDENCY HELPERS (private, call in implementation):")
            for h in dep_helpers:
                lines.append(f"  Status := Self.{h['name']} (...; Value : out ...)  -- returns {h['returns']}")

        # Abstract overrides
        abstracts = extract_abstract_procedures(base_text)
        other_abstracts = [
            a for a in abstracts
            if not any(kw in a for kw in ("Recv_Sync", "Recv_Async", "_Modify", "_Dropped", "Init ", "Get_Data_Dependency", "Invalid_Data_Dependency"))
        ]
        if other_abstracts:
            lines.append("")
            lines.append("OTHER ABSTRACT (must override):")
            for a in other_abstracts:
                sig = a.replace("not overriding ", "")
                lines.append(f"  {sig}")

        # Data dependency abstracts
        dd_abstracts = [a for a in abstracts if "Data_Dependency" in a]
        if dd_abstracts:
            lines.append("")
            lines.append("DATA DEPENDENCY ABSTRACTS (must override):")
            for a in dd_abstracts:
                sig = a.replace("not overriding ", "")
                lines.append(f"  {sig}")

        # Record fields (accessible via Self.*)
        m = re.search(r"type Base_Instance is abstract new.*?with record([\s\S]*?)end record", base_text)
        if m:
            fields = []
            record_body = m.group(1)
            # Parse only actual field declarations (skip comments)
            for line in record_body.splitlines():
                line = line.strip()
                if line.startswith("--") or not line:
                    continue
                fm = re.match(r"(\w+)\s*:\s*([^;]+);", line)
                if fm:
                    fname = fm.group(1).strip()
                    ftype = fm.group(2).strip()
                    if not fname.startswith("Connector_"):
                        fields.append((fname, ftype))
            if fields:
                lines.append("")
                lines.append("INSTANCE FIELDS (access via Self.*):")
                for fname, ftype in fields:
                    lines.append(f"  Self.{fname} : {ftype}")

    # --- Events ---
    if files["events"]:
        with open(files["events"]) as f:
            events_text = f.read()
        items = extract_feature_items(events_text, "events")
        if items:
            lines.append("")
            lines.append("EVENTS (create via Self.Events.*):")
            for item in items:
                param = f", Param => {item['param_type']}" if "param_type" in item else ""
                lines.append(f"  Self.Events.{item['name']} (Timestamp{param})")

    # --- Data Products ---
    if files["data_products"]:
        with open(files["data_products"]) as f:
            dp_text = f.read()
        items = extract_feature_items(dp_text, "data_products")
        if items:
            lines.append("")
            lines.append("DATA PRODUCTS (create via Self.Data_Products.*):")
            for item in items:
                lines.append(f"  Self.Data_Products.{item['name']} (Timestamp, Item => {item['type']})")

    # --- Commands ---
    if files["commands"]:
        with open(files["commands"]) as f:
            cmd_text = f.read()
        items = extract_feature_items(cmd_text, "commands")
        ids = extract_local_ids(cmd_text)
        if items:
            lines.append("")
            lines.append("COMMANDS:")
            lines.append(f"  IDs: {', '.join(ids)}")
            for item in items:
                params = f" ({item['params']})" if "params" in item else ""
                lines.append(f"  Self.Commands.{item['name']}{params}  -- returns Command.T")

    # --- Parameters ---
    if files["parameters"]:
        with open(files["parameters"]) as f:
            param_text = f.read()
        params, validate_sig = extract_parameter_info(param_text)
        if params:
            lines.append("")
            lines.append("PARAMETERS:")
            lines.append("  Table fields (access via Self.Parameters.*):")
            for p in params:
                lines.append(f"    .{p['name']} : {p['type']}")
            if validate_sig:
                lines.append(f"  Validate signature: ({validate_sig})")

    # --- Faults ---
    if files["faults"]:
        with open(files["faults"]) as f:
            faults_text = f.read()
        items = extract_feature_items(faults_text, "faults")
        if items:
            lines.append("")
            lines.append("FAULTS (create via Self.Faults.*):")
            for item in items:
                param = f", Param => {item['param_type']}" if "param_type" in item else ""
                lines.append(f"  Self.Faults.{item['name']} (Timestamp{param})")

    # --- Data Dependencies ---
    if files["data_dependencies"]:
        with open(files["data_dependencies"]) as f:
            dd_text = f.read()
        lines.append("")
        lines.append("DATA DEPENDENCIES:")
        for m in re.finditer(
            r"not overriding function Extract_(\w+)\s*\(Self\s*:\s*in Instance;[^)]*Item\s*:\s*out\s+(\S+?)(?:\)|\s)",
            re.sub(r"\n\s+", " ", dd_text),
        ):
            lines.append(f"  {m.group(1)} -> {m.group(2)}")

    # --- Tester ---
    if files["tester_spec"]:
        with open(files["tester_spec"]) as f:
            tester_text = f.read()

        histories = extract_tester_histories(tester_text)
        overrides = extract_tester_overrides(tester_text)

        lines.append("")
        lines.append("TESTER API:")

        for section, items in histories.items():
            if items:
                lines.append(f"  {section.upper()} HISTORIES:")
                for h in items:
                    lines.append(f"    T.{h}")

        if overrides:
            lines.append("  OVERRIDE FIELDS (set in test to control behavior):")
            for o in overrides:
                lines.append(f"    T.{o['name']} : {o['type']} := {o['default']}")

    lines.append("")
    lines.append(f"{'=' * 70}")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <component_dir>", file=sys.stderr)
        print(f"Example: {sys.argv[0]} src/components/voltage_monitor", file=sys.stderr)
        sys.exit(1)

    component_dir = sys.argv[1]
    if not os.path.isdir(component_dir):
        print(f"Error: {component_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    files = find_files(component_dir)

    if not files["base_spec"]:
        print(f"Error: No generated base spec found in {component_dir}/build/src/", file=sys.stderr)
        print("Run 'redo' first to generate the component.", file=sys.stderr)
        sys.exit(1)

    print(format_output(component_dir, files))


if __name__ == "__main__":
    main()
