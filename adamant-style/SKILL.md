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

## Ada Style Flags (Actual)

The enforced flags are `-gnaty3aABbdDefhiklL12nOprStux`:

| Flag | Rule |
|------|------|
| `3` | Indentation of 3 spaces |
| `a` | Attribute casing must match RM |
| `A` | Multi-dimensional `'Length` must specify index |
| `B` | Short-circuit operators required for booleans |
| `b` | No trailing blanks |
| `d` | No DOS line endings (CR+LF) |
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
- **No trailing whitespace** on any line (`-gnatyb`)
- **No multiple blank lines** in sequence (`-gnatyu`)
- **No tabs** (`-gnatyh`): Spaces only
- **No DOS line endings** (`-gnatyd`): Unix LF only
- **No form feeds or vertical tabs** (`-gnatyf`)
- **Space required before `(`** in type conversions and function calls (`-gnatyt`)
  ```ada
  -- WRONG: Unsigned_32(Value)
  -- RIGHT: Unsigned_32 (Value)
  ```
- **Space around binary operators**: `A + B`, `2 ** 16`, not `A+B`, `2**16`
- **No space after `(` or before `)`**: `Foo (X, Y)` not `Foo ( X, Y )`
- **No unnecessary parentheses** (`-gnatyx`): `return X;` not `return (X);`

## Ada Naming and Casing

- **Identifiers in mixed case** (`-gnatyD`): `My_Variable` not `MY_VARIABLE` or `myvariable`
- **Match declaration casing exactly** (`-gnatyr`): If declared `Heartbeat_OK`, never `Heartbeat_Ok`
- **Keywords lower case** (`-gnatyk`): `begin`, `end`, `if`, never `BEGIN`, `If`
- **Attribute casing** (`-gnatya`): `'Length`, `'Range`, `'First` (RM standard)
- **Standard casing** (`-gnatyn`): `Integer`, `Boolean`, `Natural` per RM
- **Pragma casing** (`-gnatyp`): `pragma Unreferenced`, not `pragma UNREFERENCED`

## Short-Circuit Operators (CRITICAL)

- **Always use `or else`** instead of `or` for boolean expressions (`-gnatyB`)
- **Always use `and then`** instead of `and` for boolean expressions
- Bitwise `or` / `and` on integer types are fine (they're not boolean)
  ```ada
  -- WRONG: if A > 0 or B > 0 then
  -- RIGHT: if A > 0 or else B > 0 then
  -- OK:    Mask := Mask or 16#FF#;  (bitwise, not boolean)
  ```

## Control Flow Layout

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
- **No statements on same line as `then`/`else`** (`-gnatyS`)
  ```ada
  -- WRONG: if X then return; end if;
  -- RIGHT:
  if X then
     return;
  end if;
  ```
- **Labels on `end` statements** (`-gnatye`): `end My_Proc;` not bare `end;` for named blocks
- **Max nesting depth 12** (`-gnatyL12`): Refactor deeply nested code
- **`null;` required** in empty blocks: Cannot leave only a comment in an if/else/loop body

## Array Aggregates (Ada 2022)

- **Use `[]` not `()`** for array aggregates (`-gnatwj`)
- **Record aggregates MUST use `()`** -- only arrays use `[]`
  ```ada
  Buffer := [others => 0];                       -- RIGHT (array)
  Buffer := (others => 0);                       -- WRONG (obsolescent)
  Rec := (Field_A => 1, Field_B => 2);           -- RIGHT (record)
  Arr := [others => (others => <>)];             -- RIGHT: outer [] (array), inner () (record)
  ```

## Multi-Dimensional Array `'Length` (`-gnatyA`)

```ada
-- WRONG: Buffer'Length
-- RIGHT: Buffer'Length (1)     -- must specify dimension index
```

## With-Clauses and Visibility

- **Only `with` packages you actually reference** (`-gnatwu`)
- **No redundant `with`** in body if spec already has it (`-gnatwr`)
- **No redundant `use`** if already visible through base class (`-gnatwr`)
- Move `with` to body if only the body references it
- **`overriding` keyword required** on overriding declarations (`-gnatyO`)

### `use Interfaces` Redundancy Rule

Components with commands, init params, or data dependencies get `with Interfaces; use Interfaces;` in their generated base class. Adding it again in the implementation spec triggers `-gnatwr`. Simple tick-only components do NOT get it automatically and need it explicitly.

## Variables and Constants

- **No unused variables** (`-gnatwu`): Use `pragma Unreferenced (Var);` if needed
- **No useless assignments** (`-gnatwm`): Don't assign if value is never read
- **Assigned-but-never-read**: `pragma Unreferenced` does NOT suppress this. Use `pragma Warnings (Off, Var);` or rename to `Ignore_*`
- **Declare constants when possible** (`-gnatwk`): If never modified, use `constant`

## Subprogram and Aggregate Style

- **`is null`** for empty connector drop handlers: `overriding procedure X_Send_Dropped (...) is null;`
- **Named association** in aggregates when >1 field: `(Value => 42)` not `(42)`
- **Underscore grouping** for large literals: `16#FFFF_FFFF#` not `16#FFFFFFFF#`
- **Based literals**: Use `16#...#` for hex
- **Qualified aggregates**: `Packed_U16.T'(Value => N)` when type is ambiguous

## YAML Rules

1. **Document start marker required**: Every `.yaml` file must begin with `---`
2. **No trailing whitespace**
3. **Consistent indentation**: 2 spaces for YAML (Adamant convention)
4. **No tabs**: Spaces only
5. **Quoted string defaults**: Enum defaults and string values: `default: "Sensor_Id.Sensor_Id_Type.Temperature_1"`
6. **`with:` only for preamble/field types**: Include a package in `with:` only if preamble code or field types reference it

### Type YAML Preamble Style

```yaml
preamble: |
  type Stale_Count_Type is mod 2**4;
  type Bit_Type is mod 2**1;
```

YAML is linted by yamllint with a project-specific config. Jinja2 templates are resolved before linting.

### Component YAML `with:`

**`with:` is ONLY for preamble code visibility.** Do not put connector types or framework types here.

```yaml
# WRONG:
with:
  - Tick
  - Command

# RIGHT -- only if preamble references it:
with:
  - Interfaces
preamble: |
  use Interfaces;
  subtype My_Range is Unsigned_8 range 0 .. 100;
```

**Assembly YAML `with:` is different** -- assemblies legitimately need packages for discriminants and init params.

## Python (flake8)

Ignored flake8 rules: E121, E123, E126, E226, E24, E704, W503, W504, E402, E501.

```python
from environments import test  # noqa: F401
```

- Must have `# noqa: F401` to suppress unused import warning
- Must have exactly one trailing newline
- E501 (line length) is NOT enforced

## Codespell

Codespell runs on all files in the directory (excluding build dirs). It checks for common misspellings. The project has an ignore list at `$ADAMANT_DIR/redo/codespell/ignore_list.txt`. If codespell flags a legitimate word, add it to the ignore list or restructure the text.

## Framework Template Artifacts (Cannot Fix)

These warnings come from generated template/type files and are expected:

- `unit "Component.X.Implementation.Tester" is not referenced in spec`
- `with clause might be moved to body` (on test spec)
- `unnecessary with of ancestor` (on test spec)
- `unit "Interfaces" is not referenced` in generated type specs

These are produced by `redo templates` and would be overwritten if modified.

## Implementation Spec Patterns

```ada
-- Component with commands/init/data deps: Interfaces visible via base class
-- Do NOT add: with Interfaces; use Interfaces;  (redundant)
with Tick;
with Command;

package Component.Limit_Checker.Implementation is
   type Instance is new Limit_Checker.Base_Instance with private;
private
   type Instance is new Limit_Checker.Base_Instance with record
      Current_Value : Unsigned_16 := 0;
   end record;
   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T);
   overriding procedure Event_T_Send_Dropped (Self : in out Instance; Arg : in Event.T) is null;
end Component.Limit_Checker.Implementation;
```

## Implementation Body Patterns

```ada
package body Component.Sensor_Reader.Implementation is
   use type Interfaces.Unsigned_32;

   overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T) is
      pragma Unreferenced (Arg);
      The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
   begin
      Self.Data_Product_T_Send_If_Connected (
         Self.Data_Products.Reading_Count (The_Time, (Value => Self.Reading_Count)));
   end Tick_T_Recv_Sync;
end Component.Sensor_Reader.Implementation;
```

Key patterns:
- `pragma Unreferenced (Arg);` when tick argument unused
- `use type` for operator visibility without full `use`
- `Self.*_Send_If_Connected` for optional connectors
- Qualified aggregates: `Packed_U16.T'(Value => N)` when type ambiguous

## Common Patterns by Frequency

### Most Common (fix first)
1. **Unused `with` in test bodies** (40+): Left over from templates or copy-paste
2. **Redundant `use Interfaces`** (20+): Already visible through generated base class
3. **Unused `with` in component bodies** (15+): Redundant with already in spec
4. **`(others => ...)` array syntax** (64): Needs `[others => ...]` (Ada 2022)
5. **Unused `with` in component specs** (10+): Declared but not referenced

### Frequent
6. **Unused `Count` from `Dispatch_All`**: Use `Natural_Assert.Eq (T.Dispatch_All, N)` directly, or suppress with `pragma Warnings (Off, "variable ""Count"" is assigned but never read");` before the package body. Ada forbids bare function calls (`T.Dispatch_All;` illegal).
7. **Missing space before `(`** in type conversions
8. **`or` / `and` instead of `or else` / `and then`**
9. **`then` not on its own line** in multi-line conditions
10. **Redundant conversions**: `Natural (I)` where `I` is already Natural

### Dangerous Removals (verify before removing)
- **`with X; use X;` where `use` provides operator visibility**: Removing `with Command_Types;` breaks `=` and `<`
- **`use Command_Execution_Status;`**: If removed, `return Success;` becomes ambiguous
- **`AUnit.Assertions`**: GNAT reports "no entities referenced" even when `Assert` is called via `use`. Only remove if ALL assertions use qualified names
- **Rule**: Before removing ANY `with`, grep the body for types/operators/procedures from that package

### Occasional
11. **Bad casing** (not matching declaration)
12. **Type mismatches in assertions**: Wrong `Packed_U16_Assert` vs `Packed_U32_Assert`
13. **Multiple blank lines** in sequence
14. **Duplicate with-clauses** (same package withed twice)
15. **`use Command_Execution_Status.E;`** in test bodies -- has no effect
16. **Record aggregate with `[]`**: Only arrays use `[]`
17. **`Short_Float` vs `IEEE_Float_32`**: `Packed_F32.T.Value` is `Short_Float`
18. **Missing space around `**` operator**: `2**16` -> `2 ** 16`
19. **Assigned-but-never-read variables**: Use `pragma Warnings (Off, Var);`
20. **Unnecessary parentheses**: `return (X);` -> `return X;` (`-gnatyx`)
21. **Wrong indentation**: Must be exactly 3 spaces per level
22. **Statements on `then`/`else` line**: Must be on separate line (`-gnatyS`)

## Quick Decision Table

| Situation | Action |
|---|---|
| Unused variable | `pragma Unreferenced (Var);` |
| Assigned-but-never-read | `pragma Warnings (Off, Var);` or rename `Ignore_*` |
| Unused `with` in body (spec has it) | Remove from body |
| Unused `with` in spec (only body uses it) | Move to body |
| `with X; use X;` seems unused but operators used | Keep it -- grep first |
| `(others => 0)` on array | Change to `[others => 0]` |
| `(others => <>)` on record | Keep `()` -- records use parens |
| Boolean `or`/`and` | Change to `or else`/`and then` |
| Multi-line if | Put `then` on its own line |
| Empty block body | Add `null;` |
| Function result unused | `Ignore := Func (...); pragma Unreferenced (Ignore);` |
| Redundant `use Interfaces` | Remove if base class provides it |
| Unnecessary parens | `return X;` not `return (X);` |
| Wrong indentation | Use 3 spaces per level |
| Statement on then/else line | Move to next line |
| `Buffer'Length` on 2D array | Use `Buffer'Length (1)` |

## Style Checklist

```bash
redo style
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

## References

- **[references/style-patterns.md](references/style-patterns.md)**: Detailed examples for every pattern with before/after code
