#!/bin/bash
# count_connections.sh -- Count connections per component in an assembly YAML.
# Helps verify connector count allocations match actual wiring.
#
# Usage:
#   bash count_connections.sh <assembly.yaml>
#
# Outputs a table of component names and their connection counts,
# useful for verifying init_base count parameters.

YAML="$1"
if [ -z "$YAML" ] || [ ! -f "$YAML" ]; then
    echo "Usage: count_connections.sh <assembly.yaml>" >&2
    exit 1
fi

echo "=== Connection Counts ==="
echo ""
printf "%-40s %s\n" "Component" "Connections"
printf "%-40s %s\n" "----------------------------------------" "-----------"

# Extract component names and count their connections
# Connections are lines with "from_component" or "to_component" references
# A simpler approach: count how many times each component name appears in connections

# Get all component instance names
COMPONENTS=$(grep "^  - name:" "$YAML" | sed 's/.*name: //' | tr -d '"' | tr -d "'" | sort -u)

for comp in $COMPONENTS; do
    # Count occurrences in connection sections (from_component/to_component)
    count=$(grep -c "component: $comp\b\|component: ${comp}$" "$YAML" 2>/dev/null || echo 0)
    if [ "$count" -gt 0 ]; then
        printf "%-40s %s\n" "$comp" "$count"
    fi
done

echo ""
echo "Total unique components: $(echo "$COMPONENTS" | wc -w)"
