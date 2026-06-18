#!/usr/bin/env python3
# block_source.py -- PreToolUse hook that enforces the regression-suite black-box rule.
#
# Blocks any tool call that would read flight-software implementation source
# (.ads .adb .cpp .cc .cxx .c .h .hpp .hh) so a regression-test author works only
# from the interface contract (YAML models, generated COSMOS dictionary, generated
# ground-side Python). See ../references/enforcement.md for wiring.
#
# Wire into a project's .claude/settings.json:
#   "hooks": { "PreToolUse": [ { "matcher": "Read|Edit|Write|Grep|Bash",
#     "hooks": [ { "type": "command", "command": "python3 .claude/hooks/block_source.py" } ] } ] }
#
# Contract: reads the tool-call JSON on stdin. Exit 0 = allow; exit 2 = block
# (stderr is shown to the agent). Fails OPEN (exit 0) on unparseable input so a
# hook bug never wedges the session; the settings.json deny rules remain as a
# second layer. Harden to fail-closed if your context requires it.

import json
import re
import sys

# Longer alternatives first so e.g. ".hpp" matches "hpp", not "h".
FORBIDDEN = re.compile(r"\.(adb|ads|cpp|cxx|cc|hpp|hh|c|h)\b", re.IGNORECASE)

REASON = (
    "Blocked: reading flight-software source is not allowed for regression tests. "
    "Derive this from the YAML models, the generated COSMOS cmd/tlm dictionary, or the "
    "generated ground-side Python instead (see adamant-regression-suite)."
)


def candidates(tool_name, tool_input):
    """Strings that, if they name a forbidden source file, should block the call."""
    if tool_name in ("Read", "Edit", "Write", "NotebookEdit"):
        return [tool_input.get("file_path", ""), tool_input.get("notebook_path", "")]
    if tool_name == "Grep":
        # path/glob can target source; the search itself can print source lines.
        return [tool_input.get("path", ""), tool_input.get("glob", "") or ""]
    if tool_name == "Bash":
        # Any command that even names a source file is rejected -- a regression-test
        # author has no reason to cat/sed/grep an .adb/.ads/etc.
        return [tool_input.get("command", "")]
    return []


def main():
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {}) or {}
    except Exception:
        sys.exit(0)  # fail open: do not wedge the session on bad input

    for value in candidates(tool_name, tool_input):
        if value and FORBIDDEN.search(value):
            print(REASON, file=sys.stderr)
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
