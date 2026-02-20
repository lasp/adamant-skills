---
name: adamant-style
description: Adamant code style rules enforced by redo style. Use when writing or reviewing Ada, YAML, or Python in any Adamant project, fixing style warnings, or aligning generated code with project conventions.
---

# Adamant Style Guide

`redo style` enforces Ada compiler warnings, YAML lint, Python flake8, and codespell. All code must pass.

```bash
redo style              # Current directory
redo style_all          # Recursive (all subdirectories)
```

Style logs written to `build/style/style.log` per directory.

## Ada Style Flags

Enforced: `-gnaty3aABbdDefhiklL12nOprStux`

| Flag | Rule |
|------|------|
| `3` | Indentation of 3 spaces |
| `a` | Attribute casing must match RM |
| `A` | Multi-dimensional `'Length` must specify index |
| `B` | Short-circuit operators required for booleans |
| `b` | No trailing blanks |
| `d` | No DOS line endings |
| `D` | Identifiers in mixed case |
| `e` | Labels required on `end` statements |
| `f` | No form feeds or vertical tabs |
| `h` | No horizontal tabs |
| `i` | If-then layout (multi-line `then` placement) |
| `k` | Keywords must be lower case |
| `l` | Layout per Ada RM |
| `L12` | Max nesting level of 12 |
| `n` | Standard casing must match RM |
| `O` | `overriding` keyword required |
| `p` | Pragma casing |
| `r` | Reference casing must match declaration |
| `S` | No statements on same line as `then`/`else` |
| `t` | Token spacing (space before parens, around operators) |
| `u` | No unnecessary blank lines |
| `x` | No unnecessary parentheses |

NOT enforced: `c` (comment formatting), `m`/`M` (max line length), `s` (separate specs).

## Ada Whitespace Rules

- **3-space indentation** (`-gnaty3`): Not 2, not 4
- **No trailing whitespace** (`-gnatyb`)
- **No multiple blank lines** in sequence (`-gnatyu`)
- **No tabs** (`-gnatyh`), no form feeds (`-gnatyf`), no DOS line endings (`-gnatyd`)
- **Space before `(`** in type conversions/calls: `Unsigned_32 (Value)` not `Unsigned_32(Value)`
- **Space around binary operators**: `A + B`, `2 ** 16`
- **No space after `(` or before `)`**: `Foo (X, Y)` not `Foo ( X, Y )`
- **No unnecessary parentheses** (`-gnatyx`): `return X;` not `return (X);`

## Ada Naming and Casing

- **Mixed case identifiers** (`-gnatyD`): `My_Variable`
- **Match declaration casing exactly** (`-gnatyr`): If declared `Heartbeat_OK`, always `Heartbeat_OK`
- **Keywords lower case** (`-gnatyk`): `begin`, `end`, `if`
- **Attribute/standard/pragma casing per RM** (`-gnatya`, `-gnatyn`, `-gnatyp`): `'Length`, `Integer`, `pragma Unreferenced`

## Short-Circuit Operators (`-gnatyB`) — CRITICAL

Always use `or else`/`and then` for boolean expressions. Bitwise `or`/`and` on integers is fine.
```ada
-- WRONG: if A > 0 or B > 0 then
-- RIGHT: if A > 0 or else B > 0 then
-- OK:    Mask := Mask or 16#FF#;  (bitwise, not boolean)
```

## Control Flow Layout

- **`then` on its own line** when condition spans multiple lines (`-gnatyi`):
  ```ada
  if Self.Enabled and then
     Self.Count > Threshold
  then
  ```
- **No statements on `then`/`else` line** (`-gnatyS`): Always use separate lines
- **Labels on `end`** (`-gnatye`): `end My_Proc;` not bare `end;`
- **Max nesting 12** (`-gnatyL12`): Refactor if exceeded
- **`null;` required** in empty blocks (comment-only bodies not allowed)

## Array Aggregates (Ada 2022)

Use `[]` for arrays, `()` for records. `-gnatwj` warns on obsolescent `()` array syntax.
```ada
Buffer := [others => 0];                       -- array
Rec := (Field_A => 1, Field_B => 2);           -- record
Arr := [others => (others => <>)];             -- outer [] array, inner () record
```

## Multi-Dimensional `'Length` (`-gnatyA`)

```ada
-- WRONG: Buffer'Length     RIGHT: Buffer'Length (1)
```

## With-Clauses and Visibility

- **Only `with` packages you reference** (`-gnatwu`)
- **No redundant `with`** in body if spec has it (`-gnatwr`)
- **Move `with` to body** if only body references it
- **`overriding` keyword required** (`-gnatyO`)

### `use Interfaces` Redundancy

Components with commands, init params, or data dependencies get `with Interfaces; use Interfaces;` in generated base class. Adding again triggers `-gnatwr`. Simple tick-only components need it explicitly.

## Variables and Constants

- **No unused variables** (`-gnatwu`): `pragma Unreferenced (Var);`
- **Assigned-but-never-read**: `pragma Unreferenced` does NOT work. Use `pragma Warnings (Off, Var);` or rename `Ignore_*`
- **Declare constants when possible** (`-gnatwk`)

## Subprogram and Aggregate Style

- **`is null`** for empty connector drop handlers
- **Named association** in aggregates when >1 field
- **Underscore grouping** for large literals: `16#FFFF_FFFF#`
- **Qualified aggregates**: `Packed_U16.T'(Value => N)` when type is ambiguous

## YAML Rules

1. **`---` document start marker** required
2. **No trailing whitespace**, no tabs
3. **2-space indentation** (Adamant convention)
4. **Quoted enum defaults**: `default: "Sensor_Id.Sensor_Id_Type.Temperature_1"`
5. **`with:` only for preamble/field types** — NOT for connector types

```yaml
# WRONG:          # RIGHT:
with:              with:
  - Tick             - Interfaces
  - Command        preamble: |
                     use Interfaces;
```

Assembly YAML `with:` is different — assemblies legitimately need packages for discriminants and init params.

## Python (flake8)

Ignored rules: E121, E123, E126, E226, E24, E704, W503, W504, E402, E501.

- `from environments import test  # noqa: F401` — suppress unused import
- Must have exactly one trailing newline

## Codespell

Runs on all files (excluding build dirs). Project ignore list at `$ADAMANT_DIR/redo/codespell/ignore_list.txt`.

## Framework Template Artifacts (Cannot Fix)

Expected warnings from generated template/type files:
- `unit "Component.X.Implementation.Tester" is not referenced in spec`
- `with clause might be moved to body`
- `unnecessary with of ancestor`
- `unit "Interfaces" is not referenced` in generated type specs

## AI/Sub-Agent Output Warnings

Common violations in AI-generated code:
1. Trailing whitespace — fix: `sed -i 's/[[:space:]]*$//' file.adb`
2. Multiple consecutive blank lines
3. Wrong indentation (2 or 4 instead of 3)
4. `(others => 0)` instead of `[others => 0]`
5. Boolean `or`/`and` instead of `or else`/`and then`
6. Missing space before `(` in type conversions

**Always run `redo style` on AI-touched files before committing.**

## Quick Decision Table

| Situation | Action |
|---|---|
| Unused variable | `pragma Unreferenced (Var);` |
| Assigned-but-never-read | `pragma Warnings (Off, Var);` or `Ignore_*` |
| Unused `with` in body (spec has it) | Remove from body |
| Unused `with` in spec (only body uses it) | Move to body |
| `with X; use X;` seems unused but operators used | Keep — grep first |
| `(others => 0)` on array | `[others => 0]` |
| `(others => <>)` on record | Keep `()` |
| Boolean `or`/`and` | `or else`/`and then` |
| Multi-line if | Put `then` on its own line |
| Empty block body | Add `null;` |
| Function result unused | `Ignore := Func (...); pragma Unreferenced (Ignore);` |
| Redundant `use Interfaces` | Remove if base class provides it |
| `Buffer'Length` on 2D array | `Buffer'Length (1)` |

## Dangerous Removals (Verify Before Removing)

- **`with X; use X;` providing operator visibility**: Removing breaks `=`, `<` operators
- **`use Command_Execution_Status;`**: Removing makes `return Success;` ambiguous
- **`AUnit.Assertions`**: Only remove if ALL assertions use qualified names (no bare `Assert`)
- **Rule**: Before removing ANY `with`, grep the body for types/operators from that package

## Related Skills

- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Testing**: [adamant-testing](../adamant-testing/SKILL.md)
- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md)

## References

- **[references/style-patterns.md](references/style-patterns.md)**: Before/after examples for every pattern
