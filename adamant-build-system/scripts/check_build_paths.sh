#!/bin/bash
# check_build_paths.sh -- Verify build path structure for a project.
# Checks that all component and type directories have .all_path files,
# and all test directories have env.py (but NOT .all_path).
#
# Usage:
#   bash check_build_paths.sh <project_root>
#
# Example:
#   bash check_build_paths.sh /home/user/adamant_demo

PROJECT_ROOT="$1"
if [ -z "$PROJECT_ROOT" ] || [ ! -d "$PROJECT_ROOT" ]; then
    echo "Usage: check_build_paths.sh <project_root>" >&2
    exit 1
fi

ERRORS=0
WARNINGS=0

echo "=== Build Path Verification ==="
echo "Project: $PROJECT_ROOT"
echo ""

# Check components
echo "--- Components ---"
for comp_dir in "$PROJECT_ROOT"/src/components/*/; do
    comp=$(basename "$comp_dir")
    
    # Check .all_path
    if [ ! -f "$comp_dir/.all_path" ]; then
        echo "  MISSING .all_path: $comp"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Check test dir if it exists
    test_dir="$comp_dir/test"
    if [ -d "$test_dir" ]; then
        if [ ! -f "$test_dir/env.py" ]; then
            echo "  MISSING test/env.py: $comp"
            ERRORS=$((ERRORS + 1))
        fi
        if [ -f "$test_dir/.all_path" ]; then
            echo "  BAD: test/.all_path exists (should not): $comp"
            ERRORS=$((ERRORS + 1))
        fi
        if ! ls "$test_dir"/*.tests.yaml >/dev/null 2>&1; then
            echo "  WARNING: no tests.yaml in test/: $comp"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
done

# Check types
echo ""
echo "--- Types ---"
for type_dir in "$PROJECT_ROOT"/src/types/*/; do
    type_name=$(basename "$type_dir")
    if [ ! -f "$type_dir/.all_path" ]; then
        echo "  MISSING .all_path: $type_name"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
echo "=== Summary ==="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "Fix missing .all_path with: touch <dir>/.all_path"
    echo "Fix missing env.py with: echo 'from environments import test' > <dir>/env.py"
    exit 1
fi
