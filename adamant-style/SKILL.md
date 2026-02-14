---
name: adamant-style
description: Adamant code style rules enforced by redo style. Use when writing or reviewing Ada, YAML, or Python in any Adamant project.
---

# Adamant Style Guide

`redo style` enforces Ada compiler warnings, YAML lint, Python flake8, and codespell. All code must pass.

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
- **Record aggregates MUST use `()`** -- only arrays use `[]`
  ```ada
  -- Array aggregate:
  Buffer := [others => 0];          -- RIGHT (array)
  Buffer := (others => 0);          -- WRONG (obsolescent)

  -- Record aggregate:
  Rec := (Field_A => 1, Field_B => 2);  -- RIGHT (record)

  -- Nested array-of-records:
  Arr := [others => (others => <>)];    -- RIGHT: outer [] (array), inner () (record)
  Arr := [others => [others => <>]];    -- WRONG: inner is a record, must use ()
  ```

### With-Clauses
- **Only `with` packages you actually reference** (`-gnatwu`)
- **No redundant `with`** in body if spec already has it (`-gnatwr`)
- **No redundant `use`** if already visible through base class (`-gnatwr`)
- Move `with` to body if only the body references it

### Variables
- **No unused variables** (`-gnatwu`): Use `pragma Unreferenced (Var);` if needed
- **No useless assignments** (`-gnatwm`): Don't assign if value is never read
- **Assigned-but-never-read**: `pragma Unreferenced` does NOT suppress this. Use `pragma Warnings (Off, Var);` or rename variable to `Ignore_*`
- **Declare constants when possible** (`-gnatwk`): If variable is never modified, use `constant`
- **Redundant with in body** (`-gnatwr`): The body inherits the spec's context clauses. Don't repeat `with Foo;` in the body if the spec already has it

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

These warnings come from generated template/type files and are expected:

- **`with Tester` not referenced in spec** -- test spec withs tester but only body uses it
- **`unnecessary with of ancestor`** -- child package spec withs parent redundantly
- **`with clause might be moved to body`** -- same as above
- **`unit "Interfaces" is not referenced`** in generated type specs -- code generator includes `with Interfaces` for all packed types even when not needed

These are produced by `redo templates` and would be overwritten if you modify them.

## Generated Spec Warnings

When a component's YAML has `with:`, the generated spec includes that `with` even if only the body references it. Fix: remove from YAML `with:` and add to handwritten body instead.

### `use Interfaces` Redundancy Rule

The generated base class includes `with Interfaces; use Interfaces;` when the component model has commands, init params, data dependencies, or other features using Interfaces types. For these components, do NOT add `with Interfaces; use Interfaces;` in the implementation spec -- it's already visible through the base class.

Simple components (no commands, no init params, no data dependencies) do NOT get `use Interfaces` in their base class. If they use Unsigned types in the implementation spec, they DO need `with Interfaces; use Interfaces;`.

**Rule of thumb:** Components with commands, init, or data dependencies get `use Interfaces` from the base class (redundant in impl spec). Simple tick-driven components do not (need it in impl spec). When in doubt, run `redo style` -- it warns about redundancy.

## Common Patterns by Frequency

Actual frequency data from 100-component style campaign:

### Most Common (fix first)
1. **Unused `with` in test bodies** (40+ instances): `Tick`, `Interfaces`, `Command`, `Packed_U16/U32` left over from templates or copy-paste
   - **`AUnit.Assertions`**: GNAT reports "no entities referenced" even when `Assert` is called via `use` clause. Do NOT remove if bare `Assert(...)` appears in the body. But DO remove if ALL assertion calls are qualified (`Natural_Assert.Eq`, `Packed_U32_Assert.Eq`, `AUnit.Assertions.Assert`, etc.) -- the `use` is truly unused in that case.
2. **Redundant `use Interfaces`** (20+ instances): Already visible through generated base class for components with commands/init/data deps
3. **Unused `with` in component bodies** (15+ instances): Redundant with already in spec (`Packed_U32`, `Packed_Byte`, `Command_Types`, `Packet_Types`)
4. **`(others => ...)` array syntax** (64 instances): Needs `[others => ...]` (Ada 2022)
5. **Unused `with` in component specs** (10+ instances): `Packed_U32`, `Packed_U16` declared but not referenced

### Frequent
6. **Unused `Count` variable** in test bodies: `Count := T.Dispatch_All` where Count is never read -- either remove Count or call bare `T.Dispatch_All;`
7. **Missing space before `(`** in type conversions: `Unsigned_32(X)` -> `Unsigned_32 (X)`
8. **`or` / `and` instead of `or else` / `and then`** for boolean expressions
9. **`then` not on its own line** in multi-line conditions
10. **Redundant conversions**: `Natural (I)` where `I` is already Natural, or `Unsigned_16 (X.Value)` where `.Value` is already Unsigned_16

### Dangerous Removals (verify before removing)
- **`with X; use X;` where `use` provides operator visibility**: Removing `with Command_Types;` breaks `=` and `<` on `Command_Id`. Removing `with Packed_U32.Assertion;` breaks `Eq` calls. GNAT may report the `with` as unused but operators/procedures are used via `use`.
- **`use Command_Execution_Status;`**: If removed, `return Success;` becomes ambiguous with `Connector_Status.Success`. Must qualify or keep the `use`.
- **Rule**: Before removing ANY `with`, grep the body for types/operators/procedures from that package.

### Occasional
11. **Bad casing** (not matching declaration): e.g., `Heartbeat_Ok` vs declared `Heartbeat_OK`
12. **Type mismatches in assertions**: Wrong `Packed_U16_Assert` vs `Packed_U32_Assert`
13. **Multiple blank lines** in sequence
14. **Duplicate with-clauses** in test bodies (same package withed twice)
15. **`use Command_Execution_Status.E;`** in test bodies -- has no effect (generated code already provides visibility)
16. **`Dispatch_All` on passive components**: Passive components have no queue, no `Dispatch_All` -- remove the calls
17. **Record aggregate with `[]`**: Only arrays use `[]`; record aggregates (including `(others => <>)` for record defaults) must use `()`
18. **Empty `if` block**: Must have `null;` statement -- cannot leave only a comment
19. **`Short_Float` vs `IEEE_Float_32`**: `Packed_F32.T.Value` is `Short_Float`, not `Interfaces.IEEE_Float_32`
16. **Missing space around `**` operator**: `2**16` -> `2 ** 16`
17. **Assigned-but-never-read variables**: `Status` in parameter tests -- use `pragma Warnings (Off, Var);`

## Style Checklist

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

Everything else must be fixed.

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Testing**: [adamant-testing](../adamant-testing/SKILL.md)
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md)
