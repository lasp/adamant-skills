# Enforcing the black-box rule

The black-box rule (no reading `.ads/.adb/.cpp/.c/.h`) protects the regression suite from being
written against the implementation. An instruction alone is not enough -- an author skims, or an
agent reaches for a header by reflex. Enforce it in layers, strongest last. All layers use standard
Claude Code configuration in the *adopting project's* `.claude/`; the skill only documents them and
ships the hook asset.

## Layer 0 -- instruction
The skill's opening rule, the reason, and the contract read order. First line of defense; insufficient alone.

## Layer 1 -- permission deny rules
Deny the Read/Edit/Write tools for the source extensions. A `deny` rule takes precedence over any
`allow` rule. `.yaml/.yml/.py/.txt/.json/.md` need no rule -- they are allowed by default.

Add to the project's `.claude/settings.json` (or `settings.local.json`):

```json
{
  "permissions": {
    "deny": [
      "Read(/**/*.ads)", "Read(/**/*.adb)",
      "Read(/**/*.cpp)", "Read(/**/*.cc)", "Read(/**/*.cxx)",
      "Read(/**/*.c)",   "Read(/**/*.h)",  "Read(/**/*.hpp)", "Read(/**/*.hh)",
      "Edit(/**/*.ads)", "Edit(/**/*.adb)", "Edit(/**/*.cpp)", "Edit(/**/*.c)", "Edit(/**/*.h)",
      "Write(/**/*.ads)", "Write(/**/*.adb)", "Write(/**/*.cpp)", "Write(/**/*.c)", "Write(/**/*.h)"
    ]
  }
}
```

To block source only in the flight-software repo (leaving other repos readable), scope the glob:
`Read(~/path/to/<project>/**/*.ads)`, etc.

**The gap this leaves:** a Read-deny rule governs only the Read/Edit/Write tools. It does NOT stop a
shell command (`cat`, `sed`, `head`, `awk`, `grep`, `less`, `xxd`, ...) or the Grep tool from
printing the same source. Layer 1 alone is therefore advisory against a determined or oblivious agent.

## Layer 2 -- pre-tool hook (robust)
A `PreToolUse` hook inspects Read, Edit, Write, Grep, *and* Bash calls and rejects any that touch a
forbidden extension -- closing the shell bypass. Ship [../scripts/block_source.py](../scripts/block_source.py)
and reference it from the project's settings:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Edit|Write|Grep|Bash",
        "hooks": [
          { "type": "command", "command": "python3 .claude/hooks/block_source.py" }
        ]
      }
    ]
  }
}
```

Copy `block_source.py` to the project's `.claude/hooks/` (or reference it in place). On a forbidden
access the hook exits non-zero with a short reason, which Claude Code surfaces to the agent so it
self-corrects ("source read blocked -- derive this from the YAML / generated dictionary instead").

### How to verify the hook works
With the hook wired, all of these must be blocked, and the `.yaml` read must succeed:

```bash
# blocked (Read tool):           open any *.adb / *.ads / *.c / *.h
# blocked (Bash bypass):         cat src/.../something.adb
# blocked (Grep into source):    grep -n "foo" src/.../something.ads
# allowed:                       read any *.yaml model / generated *.py / *.txt dictionary
```

### Notes and limits
- **Glob is not blocked.** Glob returns paths, not contents, so it is low risk and useful for
  navigation. Block it too only if listing source filenames is itself sensitive for your project.
- **Fail-open on malformed input.** The reference hook allows the call if it cannot parse the
  tool-call JSON, so a hook bug never wedges the session. Layer 1 deny rules still apply in that case.
  Harden to fail-closed if your context demands it.
- **Scope.** Keep the hook and deny rules in the project that is under test, not in the generic skill.
