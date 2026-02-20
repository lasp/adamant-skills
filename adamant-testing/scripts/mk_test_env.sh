#!/bin/bash
# mk_test_env.sh -- Create test directory structure for an Adamant component.
# Run from the component directory (where component.yaml lives).
#
# Creates:
#   test/env.py              -- Test environment (imports test target)
#   test/<name>.tests.yaml   -- Test model (if not exists, creates stub)
#
# Usage:
#   bash mk_test_env.sh [test_name_1 test_name_2 ...]
#
# If test names are provided, they are added to the tests.yaml.
# If no test names are provided, a single "Nominal_Test" is created.

set -e

# Find component name from YAML
COMP_YAML=$(ls *.component.yaml 2>/dev/null | head -1)
if [ -z "$COMP_YAML" ]; then
    echo "ERROR: No .component.yaml found in current directory." >&2
    echo "Run this script from the component directory." >&2
    exit 1
fi

COMP_NAME="${COMP_YAML%.component.yaml}"
echo "Component: $COMP_NAME"

# Create test directory
mkdir -p test

# Create env.py (always overwrite -- it's one line)
cat > test/env.py << 'EOF'
from environments import test
EOF
echo "  Created test/env.py"

# Create tests.yaml if it doesn't exist
TESTS_YAML="test/${COMP_NAME}.tests.yaml"
if [ ! -f "$TESTS_YAML" ]; then
    echo "description: ${COMP_NAME} unit tests" > "$TESTS_YAML"
    echo "tests:" >> "$TESTS_YAML"

    if [ $# -gt 0 ]; then
        for name in "$@"; do
            echo "  - name: $name" >> "$TESTS_YAML"
            echo "    description: $name test case" >> "$TESTS_YAML"
        done
    else
        echo "  - name: Nominal_Test" >> "$TESTS_YAML"
        echo "    description: Nominal behavior test" >> "$TESTS_YAML"
    fi
    echo "  Created $TESTS_YAML"
else
    echo "  $TESTS_YAML already exists (skipped)"
fi

echo ""
echo "Done. Next steps (run in Docker from test/ dir):"
echo "  1. Edit $TESTS_YAML to define test cases"
echo "  2. cd test && redo templates"
echo "  3. cp build/template/component-*-tester.ads build/template/component-*-tester.adb ."
echo "  4. cp build/template/*_tests-implementation.ads build/template/test.adb ."
echo "  5. Write ONLY ${COMP_NAME}_tests-implementation.adb (test case bodies)"
echo "  6. redo test"
