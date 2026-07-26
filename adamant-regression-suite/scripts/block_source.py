#!/usr/bin/env python3
# block_source.py -- PreToolUse hook that enforces the regression-suite black-box rule.
#
# Blocks any tool call that would read flight-software implementation source
# (.ads .adb .cpp .cc .cxx .c .h .hpp .hh) so a regression-test author works only
# from the interface contract (YAML models, generated COSMOS dictionary, generated
# ground-side Python). See ../references/enforcement.md for wiring.
#
# Wire into a project's .claude/settings.json (use ${CLAUDE_PROJECT_DIR} -- hooks run in the
# session cwd, and a relative path that fails to resolve exits 2, which BLOCKS every matched call):
#   "hooks": { "PreToolUse": [ { "matcher": "Read|Edit|Write|NotebookEdit|Grep|Bash",
#     "hooks": [ { "type": "command",
#       "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/hooks/block_source.py\"" } ] } ] }
#
# Contract: reads the tool-call JSON on stdin. Exit 0 = allow; exit 2 = block
# (stderr is shown to the agent). Exit 2 is the ONLY blocking code -- exit 1 is a
# non-blocking error and the call proceeds. Fails OPEN (exit 0) on unparseable
# input so a hook bug never wedges the session; the settings.json deny rules
# remain as a second layer. To harden to fail-closed, the except branch must
# sys.exit(2) with a reason on stderr (NOT exit 1).

import json
import re
import sys

# Longer alternatives first so e.g. ".hpp" matches "hpp", not "h".
FORBIDDEN = re.compile(r"\.(adb|ads|cpp|cxx|cc|hpp|hh|c|h)\b", re.IGNORECASE)

REASON = (
    "Blocked: this call names a flight-software source file, which regression tests must not "
    "read. Derive the fact from the YAML models, the generated COSMOS cmd/tlm dictionary, or the "
    "generated ground-side Python instead (see adamant-regression-suite). If the source-like "
    "token was incidental (prose, an unrelated path), rephrase the command to avoid it."
)


def glob_variants(glob_value):
    """Expand one level of {a,b} and [abc] glob alternatives into concrete globs, so
    brace/class forms (*.{adb,ads}, *.[ch], *.ad[bs]) can't slip past the dot-anchored regex."""
    if not glob_value:
        return []
    variants = [glob_value]
    m = re.search(r"\{([^}]*)\}", glob_value)
    if m:
        variants = [glob_value[:m.start()] + alt + glob_value[m.end():]
                    for alt in m.group(1).split(",")]
    expanded = []
    for v in variants:
        m = re.search(r"\[([^\]]*)\]", v)
        if m:
            expanded.extend(v[:m.start()] + ch + v[m.end():] for ch in m.group(1))
        else:
            expanded.append(v)
    return expanded


def candidates(tool_name, tool_input):
    """Strings that, if they name a forbidden source file, should block the call."""
    if tool_name in ("Read", "Edit", "Write", "NotebookEdit"):
        return [tool_input.get("file_path", ""), tool_input.get("notebook_path", "")]
    if tool_name == "Grep":
        # path/glob can target source. Known residual: a content search over a directory
        # containing source can still print source lines (see enforcement.md Notes and limits).
        glob_value = tool_input.get("glob", "") or ""
        return [tool_input.get("path", ""), glob_value, *glob_variants(glob_value)]
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
