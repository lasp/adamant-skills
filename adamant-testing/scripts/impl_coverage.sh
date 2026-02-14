#!/bin/bash
# impl_coverage.sh - Report coverage for component implementation files only
# Usage: impl_coverage.sh [component_name ...]
# If no args, scans all components with test directories.
#
# Place this in your project's tools/ directory.
# Run from the project root after building coverage for components.

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPONENTS_DIR="$PROJECT_DIR/src/components"

if [ $# -gt 0 ]; then
  TARGETS="$@"
else
  TARGETS=$(ls -d "$COMPONENTS_DIR"/*/test 2>/dev/null | sed 's|.*/components/||;s|/test||' | sort)
fi

printf "%-35s %6s %6s %6s  %s\n" "COMPONENT" "LINES" "EXEC" "COV%" "MISSING"
printf "%-35s %6s %6s %6s  %s\n" "---" "---" "---" "---" "---"

TOTAL_LINES=0
TOTAL_EXEC=0

for comp in $TARGETS; do
  COV_FILE="$COMPONENTS_DIR/$comp/test/build/coverage/coverage.txt"
  if [ ! -f "$COV_FILE" ]; then
    printf "%-35s %6s %6s %6s  %s\n" "$comp" "-" "-" "-" "(no coverage data)"
    continue
  fi

  # Extract component-*-implementation.adb coverage data.
  # gcovr may wrap long filenames: filename on line N, numbers on line N+1.
  LINE_NUM=$(grep -n "component-.*-implementation\.adb" "$COV_FILE" | grep -v "tester\|reciprocal\|test/" | head -1 | cut -d: -f1)
  if [ -z "$LINE_NUM" ]; then
    printf "%-35s %6s %6s %6s  %s\n" "$comp" "-" "-" "-" "(no impl line)"
    continue
  fi

  # Get this line and the next, join them
  IMPL_DATA=$(sed -n "${LINE_NUM}p;$((LINE_NUM+1))p" "$COV_FILE" | tr '\n' ' ')

  # Extract: LINES EXEC PCT% [MISSING...]
  NUMS=$(echo "$IMPL_DATA" | grep -oP '\d+\s+\d+\s+\d+%[^c]*' | head -1)
  if [ -z "$NUMS" ]; then
    printf "%-35s %6s %6s %6s  %s\n" "$comp" "-" "-" "-" "(no impl line)"
    continue
  fi

  LINES=$(echo "$NUMS" | awk '{print $1}')
  EXEC=$(echo "$NUMS" | awk '{print $2}')
  PCT=$(echo "$NUMS" | awk '{print $3}')
  MISSING=$(echo "$NUMS" | awk '{for(i=4;i<=NF;i++) printf "%s ", $i; print ""}' | xargs)

  TOTAL_LINES=$((TOTAL_LINES + LINES))
  TOTAL_EXEC=$((TOTAL_EXEC + EXEC))

  printf "%-35s %6d %6d %6s  %s\n" "$comp" "$LINES" "$EXEC" "$PCT" "$MISSING"
done

if [ $TOTAL_LINES -gt 0 ]; then
  TOTAL_PCT=$((TOTAL_EXEC * 100 / TOTAL_LINES))
  printf "%-35s %6s %6s %6s\n" "---" "---" "---" "---"
  printf "%-35s %6d %6d %5d%%\n" "TOTAL (impl .adb only)" "$TOTAL_LINES" "$TOTAL_EXEC" "$TOTAL_PCT"
fi
