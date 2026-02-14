---
name: adamant-style
description: Adamant code style rules enforced by redo style. Use when writing or reviewing Ada, YAML, or Python in any Adamant project.
---

# Adamant Style Guide

`redo style` enforces Ada compiler warnings, YAML lint, Python flake8, and codespell. All code must pass before committing.

## Running Style Checks

```bash
redo style              # Current directory
redo style_all          # Recursive (all subdirectories)
```

Style logs written to `build/style/style.log` per directory.

## YAML Rules

1. **Document start marker required**: Every `.yaml` file must begin with `---` on its own line
2. **No trailing whitespace**: Strip all trailing spaces
3. **Consistent indentation**: 2 or 4 spaces, no tabs
4. **No trailing spaces on any line**

## Ada Style Rules (gnatmake -gnatyaBbcdefhiklnOprsStux)

### Whitespace
- **No trailing whitespace** on any line (`-gnatyb`)
- **No multiple blank lines** in sequence (`-gnatyu`)
- **Space required before `(`** in type conversions and function calls (`-gnatyt`)
  ```ada
  -- WRONG: Unsigned_32(Value)
  -- RIGHT: Unsigned_32 (Value)
  ```

### Short-Circuit Operators (CRITICAL)
- **Always use `or else`** instead of `or` for boolean expressions (`-gnatyB`)
- **Always use `and then`** instead of `and` for boolean expressions
- Bitwise `or` / `and` on integer types are fine (they're not boolean)
  ```ada
  -- WRONG: if A > 0 or B > 0 then
  -- RIGHT: if A > 0 or else B > 0 then
  -- OK:    Mask := Mask or 16#FF#;  (bitwise, not boolean)
  ```

### Multi-Line If Statements
- **`then` on its own line** when condition spans multiple lines (`-gnatyi`)
  ```ada
  -- WRONG:
  if Self.Enabled and then
     Self.Count > Threshold then

  -- RIGHT:
  if Self.Enabled and then
     Self.Count > Threshold
  then
  ```

### Casing
- **Match declaration casing exactly** (`-gnatyr`): If a type or entity is declared as `Heartbeat_OK`, never write `Heartbeat_Ok`
- Ada identifiers are case-insensitive but style checking enforces consistent casing

### Array Aggregates (Ada 2022)
- **Use `[]` not `()`** for array aggregates (`-gnatwj`)
  ```ada
  -- WRONG: Buffer := (others => 0);
  -- RIGHT: Buffer := [others => 0];
  -- NOTE:  Record aggregates still use ()
  ```

### With-Clauses
- **Only `with` packages you actually reference** (`-gnatwu`)
- **No redundant `with`** in body if spec already has it (`-gnatwr`)
- **No redundant `use`** if already visible through base class (`-gnatwr`)
- Move `with` to body if only the body references it

### Variables
- **No unused variables** (`-gnatwu`): Use `pragma Unreferenced (Var);` if needed
- **No useless assignments** (`-gnatwm`): Don't assign if value is never read
- **Declare constants when possible** (`-gnatwk`): If variable is never modified, use `constant`

## Component YAML `with:` Section

**`with:` is ONLY for preamble code visibility.** Do not put connector types, framework types, or general imports here. Normal imports go in the handwritten `.ads` / `.adb` files.

```yaml
# WRONG -- these are NOT needed in YAML:
with:
  - Tick
  - Command
  - Interfaces
  - My_Custom_Type    # Unless used in preamble

# RIGHT -- only if preamble references it:
with:
  - Interfaces
preamble: |
  use Interfaces;
  subtype My_Range is Unsigned_8 range 0 .. 100;
```

**Assembly YAML `with:` is different** -- assemblies legitimately need packages for preamble, discriminants, and init params.

## Python (env.py)

```python
from environments import test  # noqa: F401
```

- Must have `# noqa: F401` to suppress unused import warning
- Must have exactly one trailing newline (no blank lines at end)

## Framework Template Artifacts (Cannot Fix)

These warnings come from generated template files and are expected:

- **`with Tester` not referenced in spec** -- test spec withs tester but only body uses it
- **`unnecessary with of ancestor`** -- child package spec withs parent redundantly
- **`with clause might be moved to body`** -- same as above

These are produced by `redo templates` and would be overwritten if you modify them.

## Generated Spec Warnings

When a component's YAML has `with:`, the generated spec includes that `with` even if only the body references it. Fix: remove from YAML `with:` and add to handwritten body instead.

### `use Interfaces` Redundancy Rule

The generated base class includes `with Interfaces; use Interfaces;` when the component model has commands, init params, data dependencies, or other features using Interfaces types. For these components, do NOT add `with Interfaces; use Interfaces;` in the implementation spec -- it's already visible through the base class.

Simple components (no commands, no init params, no data dependencies) do NOT get `use Interfaces` in their base class. If they use Unsigned types in the implementation spec, they DO need `with Interfaces; use Interfaces;`.

**Rule of thumb:** Components with commands, init, or data dependencies get `use Interfaces` from the base class (redundant in impl spec). Simple tick-driven components do not (need it in impl spec). When in doubt, run `redo style` -- it warns about redundancy.

## Common Patterns by Frequency

### Most Common (fix first)
1. Missing `---` in YAML files
2. Trailing whitespace in Ada/YAML
3. Unused `with` in test bodies (leftover from copy-paste)
4. Redundant `use Interfaces` (already visible through generated base class)
5. `(others => ...)` array syntax needs `[others => ...]`

### Frequent
6. Missing space before `(` in type conversions
7. `or` / `and` instead of `or else` / `and then`
8. Unused variables (especially `Status` in parameter test patterns)
9. `then` not on its own line in multi-line conditions

### Occasional
10. Bad casing (not matching declaration)
11. Redundant `with` in body (already in spec)
12. Type mismatches in assertions (wrong Packed_U16 vs Packed_U32)
13. Multiple blank lines

## Pre-Commit Checklist

```bash
# From component directory:
redo style

# Check output -- fix everything except template artifacts:
cat build/style/style.log
```

Acceptable warnings (template artifacts only):
- `unit "Component.X.Implementation.Tester" is not referenced in spec`
- `with clause might be moved to body` (on test spec)
- `unnecessary with of ancestor` (on test spec)

Everything else must be fixed before committing.

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Testing**: [adamant-testing](../adamant-testing/SKILL.md)
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md)
