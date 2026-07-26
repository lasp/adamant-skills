# Enforcing the black-box rule

The black-box rule (no reading `.ads/.adb/.cpp/.c/.h`) protects the regression suite from being
written against the implementation. An instruction alone is not enough -- an author skims, or an
agent reaches for a header by reflex. Enforce it in layers, strongest last. All layers use standard
Claude Code configuration in the *adopting project's* `.claude/`; the skill only documents them and
ships the hook asset.

**Threat model:** these layers stop *reflexive/oblivious* source access -- the skimming author, the
agent that habitually opens a header. They are not a hard boundary against a determined agent (a
subprocess that globs and reads files itself passes every layer). If you need OS-level enforcement,
use Claude Code sandboxing; these layers are guardrails, not walls.

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
      "Read(**/*.ads)", "Read(**/*.adb)",
      "Read(**/*.cpp)", "Read(**/*.cc)", "Read(**/*.cxx)",
      "Read(**/*.c)",   "Read(**/*.h)",  "Read(**/*.hpp)", "Read(**/*.hh)",
      "Edit(**/*.ads)", "Edit(**/*.adb)", "Edit(**/*.cpp)", "Edit(**/*.cc)", "Edit(**/*.cxx)",
      "Edit(**/*.c)",   "Edit(**/*.h)",  "Edit(**/*.hpp)", "Edit(**/*.hh)",
      "Write(**/*.ads)", "Write(**/*.adb)", "Write(**/*.cpp)", "Write(**/*.cc)", "Write(**/*.cxx)",
      "Write(**/*.c)",   "Write(**/*.h)",  "Write(**/*.hpp)", "Write(**/*.hh)"
    ]
  }
}
```

**Rule scoping:** `**/*.ads` (and `/`-anchored) patterns are **project-root-relative** -- they cover
the repo containing the settings file, not the whole filesystem. Source mounted from *other*
directories (`additionalDirectories` -- a mounted framework tree, sibling component repos) needs its
own rules: absolute `Read(//abs/path/**/*.ads)` or home-relative `Read(~/path/**/*.ads)`.

**The gap this leaves:** deny rules are applied to Read/Edit/Write, and (best-effort) to the Grep and
Glob tools and to recognized Bash file commands (`cat`, `head`, `tail`, `sed`) for rule-matched
paths. The residual is arbitrary subprocesses that open files themselves (`python`/`node` one-liners,
`awk`, `xxd`) and command shapes the parser does not recognize. Layer 2 catches the ones that
literally name a source file -- and gives the agent a self-correcting message instead of a silent
permission denial.

## Layer 2 -- pre-tool hook (closes the literal-name shell reflex)
A `PreToolUse` hook inspects Read, Edit, Write, NotebookEdit, Grep, *and* Bash calls and rejects any
that literally names a forbidden extension. Ship [../scripts/block_source.py](../scripts/block_source.py)
and reference it from the project's settings:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Edit|Write|NotebookEdit|Grep|Bash",
        "hooks": [
          { "type": "command", "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/hooks/block_source.py\"" }
        ]
      }
    ]
  }
}
```

Copy `block_source.py` to the project's `.claude/hooks/`. Use `${CLAUDE_PROJECT_DIR}` in the command,
not a bare relative path -- hooks run in the session's current directory, and a relative path that
fails to resolve makes `python3` exit 2, which is the *blocking* exit code: every matched tool call
would be blocked with a confusing "can't open file" error.

On a forbidden access the hook exits **2** with a short reason on stderr, which Claude Code surfaces
to the agent so it self-corrects ("source read blocked -- derive this from the YAML / generated
dictionary instead"). Exit 2 is the only blocking exit code -- exit 1 is a non-blocking error and the
tool call proceeds.

### How to verify the hook works
With the hook wired, all of these must be blocked, and the `.yaml` read must succeed:

```bash
# blocked (Read tool):           open any *.adb / *.ads / *.c / *.h
# blocked (Bash bypass):         cat src/.../something.adb
# blocked (Grep into source):    grep -n "foo" src/.../something.ads
# allowed:                       read any *.yaml model / generated *.py / *.txt dictionary

# passes through BY DESIGN (know the residual gaps -- see Notes and limits):
#   grep -rn "foo" src/          (content search never names an extension)
#   cat src/components/foo/*     (shell glob expands after the hook runs)
#   git log -p -- src/           (history output can contain source)
```

### Notes and limits
- **Residual Bash gaps.** The hook blocks commands that *literally name* a source extension. A
  recursive grep over a directory, a shell glob (`cat src/*`, `cat foo.ad?`), `find | xargs cat`, or
  `git log -p`/`git show` can still print source without naming one. These are within the reflexive
  threat model but uncaught -- the instruction layer and review are the backstop.
- **Grep content-mode leak.** The hook checks Grep's `path`/`glob` inputs; a content search over a
  directory that *contains* source can still print matching source lines even though no argument
  names a forbidden extension.
- **Intentionally over-broad on Bash.** Any command that merely *mentions* a source-like token is
  blocked (a commit message quoting `foo.h`, a `~/.adb/` path, inner extensions like `packet.c.yaml`).
  Acceptable for this domain; if a legitimate command is blocked, rephrase it to avoid the token.
- **Glob is not blocked.** Glob returns paths, not contents, so it is low risk and useful for
  navigation. Block it too only if listing source filenames is itself sensitive for your project.
- **Fail-open on malformed input.** The reference hook allows the call if it cannot parse the
  tool-call JSON, so a hook bug never wedges the session. Layer 1 deny rules still apply in that case.
  To harden to fail-closed, the `except` branch must use `sys.exit(2)` with a reason on stderr --
  exit 1 does NOT block.
- **Scope.** Keep the hook and deny rules in the project that is under test, not in the generic skill.
