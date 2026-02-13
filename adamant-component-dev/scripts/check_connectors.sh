#!/bin/bash
# check_connectors.sh -- Validate that component.yaml has all required
# connectors for its feature YAML files.
#
# Feature YAMLs do NOT auto-generate send/recv connectors in the base class.
# Every feature YAML requires matching connectors explicitly listed in
# the component.yaml. This script checks for missing ones.
#
# Run from the component directory (where component.yaml lives).
#
# Usage:
#   bash check_connectors.sh

set -e

COMP_YAML=$(ls *.component.yaml 2>/dev/null | head -1)
if [ -z "$COMP_YAML" ]; then
    echo "ERROR: No .component.yaml found." >&2
    exit 1
fi

COMP_NAME="${COMP_YAML%.component.yaml}"
ERRORS=0

check_connector() {
    local feature="$1"
    local connector_type="$2"
    local connector_kind="$3"

    if ! grep -q "$connector_type" "$COMP_YAML" 2>/dev/null; then
        echo "  MISSING: $connector_kind $connector_type (required by $feature)"
        ERRORS=$((ERRORS + 1))
    fi
}

echo "Checking $COMP_NAME connectors..."

# commands.yaml requires Command.T recv_sync + Command_Response.T send
if [ -f "${COMP_NAME}.commands.yaml" ]; then
    check_connector "commands.yaml" "Command.T" "recv_sync"
    check_connector "commands.yaml" "Command_Response.T" "send"
fi

# events.yaml requires Event.T send
if [ -f "${COMP_NAME}.events.yaml" ]; then
    check_connector "events.yaml" "Event.T" "send"
fi

# data_products.yaml requires Data_Product.T send
if [ -f "${COMP_NAME}.data_products.yaml" ]; then
    check_connector "data_products.yaml" "Data_Product.T" "send"
fi

# faults.yaml requires Fault.T send
if [ -f "${COMP_NAME}.faults.yaml" ]; then
    check_connector "faults.yaml" "Fault.T" "send"
fi

# parameters.yaml requires Parameter_Update.T modify
if [ -f "${COMP_NAME}.parameters.yaml" ]; then
    check_connector "parameters.yaml" "Parameter_Update.T" "modify"
fi

# data_dependencies.yaml requires Data_Product_Fetch.T request
if [ -f "${COMP_NAME}.data_dependencies.yaml" ]; then
    if ! grep -q "Data_Product_Fetch.T\|Data_Product_Return.T" "$COMP_YAML" 2>/dev/null; then
        echo "  MISSING: request Data_Product_Fetch.T/Data_Product_Return.T (required by data_dependencies.yaml)"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check for Sys_Time.T get (common requirement)
if grep -q "Sys_Time" "$COMP_YAML" 2>/dev/null; then
    if ! grep -q "return_type.*Sys_Time.T\|return_type: Sys_Time.T" "$COMP_YAML" 2>/dev/null; then
        echo "  WARNING: Sys_Time referenced but no 'get' connector with return_type found"
    fi
fi

if [ $ERRORS -eq 0 ]; then
    echo "  All required connectors present."
else
    echo ""
    echo "  $ERRORS missing connector(s). Add them to $COMP_YAML."
    exit 1
fi
