#!/bin/bash
# check_name_collision.sh -- Check if a component name collides with
# Adamant framework built-in components (~55 components).
#
# Usage:
#   bash check_name_collision.sh <component_name> [adamant_dir]
#
# The adamant_dir defaults to the ADAMANT_DIR environment variable,
# or /home/user/adamant (Docker default).
#
# Exit code 0 = no collision, 1 = collision found.

COMP_NAME="$1"
ADAMANT_DIR="${2:-${ADAMANT_DIR:-/home/user/adamant}}"

if [ -z "$COMP_NAME" ]; then
    echo "Usage: check_name_collision.sh <component_name> [adamant_dir]" >&2
    exit 2
fi

FW_COMP_DIR="$ADAMANT_DIR/src/components"

if [ ! -d "$FW_COMP_DIR" ]; then
    echo "WARNING: Framework components dir not found: $FW_COMP_DIR" >&2
    echo "Cannot check for name collisions. Proceeding." >&2
    exit 0
fi

if [ -d "$FW_COMP_DIR/$COMP_NAME" ]; then
    echo "COLLISION: '$COMP_NAME' exists in framework at $FW_COMP_DIR/$COMP_NAME"
    echo "Rename your component (e.g., station_${COMP_NAME}) to avoid build conflicts."
    exit 1
else
    echo "OK: '$COMP_NAME' does not collide with framework components."
    exit 0
fi
