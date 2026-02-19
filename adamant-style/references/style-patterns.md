<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Adamant Style Patterns -- Detailed Reference

Every pattern documented in SKILL.md with before/after examples, the exact GNAT flag, and explanation.

## Ada Style Flag Reference

Actual enforced flags: `-gnaty3aABbdDefhiklL12nOprStux`

Source: `adamant/redo/targets/gpr/a_adamant.gpr`

Notably NOT enforced:
- `-gnatyc` (comment formatting) -- Adamant is more accepting
- `-gnatym`/`-gnatyM` (max line length) -- no limit enforced
- `-gnatys` (separate specs required) -- not enforced

---

## Whitespace Patterns

### 3-Space Indentation (`-gnaty3`)

```ada
-- WRONG (2 spaces):
procedure Foo is
  X : Integer;
begin
  X := 1;
end Foo;

-- WRONG (4 spaces):
procedure Foo is
    X : Integer;
begin
    X := 1;
end Foo;

-- RIGHT (3 spaces):
procedure Foo is
   X : Integer;
begin
   X := 1;
end Foo;
```

### No Trailing Blanks (`-gnatyb`)

Invisible but caught. Configure editor to strip trailing whitespace on save.

### No Unnecessary Blank Lines (`-gnatyu`)

```ada
-- WRONG:
   Self.Count := 0;


   Self.Enabled := True;

-- RIGHT:
   Self.Count := 0;

   Self.Enabled := True;
```

### No Tabs (`-gnatyh`)

Tabs produce: `horizontal tab not allowed`. Use spaces only.

### No DOS Line Endings (`-gnatyd`)

Files must use Unix LF (`\n`), not Windows CR+LF (`\r\n`).

### Token Spacing (`-gnatyt`)

```ada
-- WRONG:
X := Unsigned_32(Value);
Y := A+B;
Z := 2**16;

-- RIGHT:
X := Unsigned_32 (Value);
Y := A + B;
Z := 2 ** 16;
```

Space required before `(` in calls and conversions. Space around binary operators.

No space after `(` or before `)`:
```ada
-- WRONG: Foo ( X, Y )
-- RIGHT: Foo (X, Y)
```

### No Unnecessary Parentheses (`-gnatyx`)

```ada
-- WRONG:
return (Self.Count);

-- RIGHT:
return Self.Count;

-- WRONG:
if (X > 0) then

-- RIGHT:
if X > 0 then
```

---

## Naming and Casing Patterns

### Mixed Case Identifiers (`-gnatyD`)

```ada
-- WRONG:
MY_COUNTER : Integer;
mycounter : Integer;

-- RIGHT:
My_Counter : Integer;
```

### Reference Casing Must Match Declaration (`-gnatyr`)

```ada
-- If declared as:
type Heartbeat_OK is ...;

-- WRONG:
X : Heartbeat_Ok;

-- RIGHT:
X : Heartbeat_OK;
```

This applies to all identifiers: types, variables, subprograms, enum literals.

### Keyword Lower Case (`-gnatyk`)

```ada
-- WRONG:
BEGIN
   IF X > 0 THEN
      RETURN;
   END IF;
END;

-- RIGHT:
begin
   if X > 0 then
      return;
   end if;
end;
```

### Attribute Casing (`-gnatya`)

```ada
-- WRONG:
X := Buffer'length;
Y := Buffer'RANGE;

-- RIGHT:
X := Buffer'Length;
Y := Buffer'Range;
```

### Standard Casing (`-gnatyn`)

```ada
-- WRONG:
X : integer;
Y : boolean;

-- RIGHT:
X : Integer;
Y : Boolean;
```

### Pragma Casing (`-gnatyp`)

```ada
-- WRONG:
pragma unreferenced (Arg);
pragma INLINE (Func);

-- RIGHT:
pragma Unreferenced (Arg);
pragma Inline (Func);
```

---

## Control Flow Patterns

### Short-Circuit Operators (`-gnatyB`)

```ada
-- WRONG (boolean or/and):
if A > 0 or B > 0 then
if Enabled and Ready then

-- RIGHT:
if A > 0 or else B > 0 then
if Enabled and then Ready then

-- OK (bitwise on integer types):
Mask := Mask or 16#FF#;
Flags := Flags and 16#0F#;
```

GNAT error: `non-short-circuit form used`

### Multi-Line If-Then Layout (`-gnatyi`)

```ada
-- WRONG:
if Self.Enabled and then
   Self.Count > Threshold then
   Do_Something;
end if;

-- RIGHT:
if Self.Enabled and then
   Self.Count > Threshold
then
   Do_Something;
end if;

-- Also applies to elsif:
elsif Self.Mode = Active and then
   Self.Ready
then
   Process;
end if;
```

### No Statements on Then/Else Line (`-gnatyS`)

```ada
-- WRONG:
if X then return; end if;
if X then Y := 1;
else Y := 2;
end if;

-- RIGHT:
if X then
   return;
end if;

if X then
   Y := 1;
else
   Y := 2;
end if;
```

### End Labels Required (`-gnatye`)

```ada
-- WRONG:
package body Component.Foo.Implementation is
   procedure Bar is
   begin
      null;
   end;
end;

-- RIGHT:
package body Component.Foo.Implementation is
   procedure Bar is
   begin
      null;
   end Bar;
end Component.Foo.Implementation;
```

### Max Nesting Level 12 (`-gnatyL12`)

If you hit this, refactor into helper subprograms.

### Empty Blocks Need `null;`

```ada
-- WRONG:
if Error then
   -- TODO: handle later
end if;

-- RIGHT:
if Error then
   null; -- TODO: handle later
end if;
```

---

## Array and Aggregate Patterns

### Array Aggregates Use `[]` (Ada 2022)

```ada
-- WRONG (obsolescent):
Buffer : Byte_Array := (others => 0);
Buffer := (1, 2, 3, 4);

-- RIGHT:
Buffer : Byte_Array := [others => 0];
Buffer := [1, 2, 3, 4];

-- Record aggregates still use ():
Rec := (Field_A => 1, Field_B => 2);

-- Mixed (array of records):
Arr := [others => (Field => 0)];
```

GNAT warning: `obsolescent: should use square brackets`

### Multi-Dimensional `'Length` (`-gnatyA`)

```ada
-- WRONG:
for I in 1 .. Buffer'Length loop

-- RIGHT (for 2D+ arrays, must specify dimension):
for I in 1 .. Buffer'Length (1) loop
```

---

## With-Clause Patterns

### Unused With (`-gnatwu`)

```ada
-- WRONG (Tick not used anywhere in body):
with Tick;
package body Component.Foo.Implementation is ...

-- RIGHT: remove the with clause
package body Component.Foo.Implementation is ...
```

### Redundant With in Body (`-gnatwr`)

```ada
-- WRONG (spec already has `with Tick;`):
-- In .ads: with Tick;
-- In .adb: with Tick;   -- redundant

-- RIGHT: only in .ads (or move to .adb if only body uses it)
```

### Redundant `use Interfaces` in Components

Components with commands, init params, or data dependencies automatically get
`with Interfaces; use Interfaces;` in their generated base class spec.

```ada
-- WRONG (for components with commands/init/deps):
with Interfaces; use Interfaces;
package Component.Foo.Implementation is ...

-- RIGHT (Interfaces already visible from base):
package Component.Foo.Implementation is ...

-- EXCEPTION (simple tick-only components need explicit):
with Interfaces; use Interfaces;
package Component.Simple.Implementation is ...
```

### `use type` for Operator Visibility

```ada
-- When you need operators but not full visibility:
use type Interfaces.Unsigned_32;    -- gives +, -, *, =, <, etc.
use type Command_Enums.Command_Response_Status.E;  -- gives = operator
```

### Overriding Keyword Required (`-gnatyO`)

```ada
-- WRONG:
procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T);

-- RIGHT:
overriding procedure Tick_T_Recv_Sync (Self : in out Instance; Arg : in Tick.T);
```

---

## Variable and Constant Patterns

### Unused Variable

```ada
-- WRONG:
procedure Foo (Arg : in Tick.T) is
begin
   -- Arg not used
   null;
end Foo;

-- RIGHT:
procedure Foo (Arg : in Tick.T) is
   pragma Unreferenced (Arg);
begin
   null;
end Foo;
```

### Assigned-But-Never-Read

`pragma Unreferenced` does NOT work for this case.

```ada
-- WRONG:
Count : Natural;
Count := T.Dispatch_All;
-- Count never read after this

-- RIGHT (option 1 -- use directly):
Natural_Assert.Eq (T.Dispatch_All, 2);

-- RIGHT (option 2 -- suppress warning):
Ignore : Natural;
pragma Warnings (Off, Ignore);
...
Ignore := T.Dispatch_All;

-- RIGHT (option 3 -- naming convention):
Ignore_Count : Natural;
...
Ignore_Count := T.Dispatch_All;
```

### Declare Constants When Possible

```ada
-- WRONG (never modified):
The_Time : Sys_Time.T := Self.Sys_Time_T_Get;

-- RIGHT:
The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
```

---

## Numeric Literal Patterns

### Underscore Grouping

```ada
-- WRONG:
X := 16#FFFFFFFF#;
Y := 1000000;

-- RIGHT:
X := 16#FFFF_FFFF#;
Y := 1_000_000;
```

### Based Literals

```ada
-- Hex:
Mask : constant := 16#FF00#;

-- Binary:
Pattern : constant := 2#1010_0101#;
```

---

## YAML Patterns

### Document Start Marker

```yaml
# WRONG (no marker):
description: My component

# RIGHT:
---
description: My component
```

### Quoted Enum Defaults

```yaml
# WRONG:
default: Sensor_Id.Sensor_Id_Type.Temperature_1

# RIGHT:
default: "Sensor_Id.Sensor_Id_Type.Temperature_1"
```

### Component YAML `with:` Misuse

```yaml
# WRONG -- connector types do not go in with:
with:
  - Tick
  - Command
  - Interfaces

# RIGHT -- only packages referenced in preamble or field types:
with:
  - Interfaces
preamble: |
  use Interfaces;
  subtype My_Range is Unsigned_8 range 0 .. 100;
```

### Record Type YAML `with:`

```yaml
# with: is needed when field types reference external packages:
---
description: A sensor reading
with:
  - Interfaces
  - Sensor_Id
fields:
  - name: id
    type: Sensor_Id.Sensor_Id_Type.E    # needs Sensor_Id in with:
  - name: value
    type: Interfaces.Unsigned_16         # needs Interfaces in with:
```

### 2-Space Indentation in YAML

```yaml
# WRONG (4 spaces):
fields:
    - name: value
      type: Interfaces.Unsigned_16

# RIGHT (2 spaces):
fields:
  - name: value
    type: Interfaces.Unsigned_16
```

---

## Python Patterns

### env.py

```python
# WRONG (missing noqa):
from environments import test

# RIGHT:
from environments import test  # noqa: F401
```

### Trailing Newline

Files must end with exactly one newline. No blank lines at end.

### Flake8 Ignored Rules

E121, E123, E126, E226, E24, E704, W503, W504, E402, E501 are not enforced.

---

## Codespell Patterns

Codespell catches common misspellings in all file types.

```
# Flagged:
paramter -> parameter
recieve -> receive
occured -> occurred
```

If a legitimate identifier triggers codespell (e.g., `metrix`), it should be in the project ignore list at `$ADAMANT_DIR/redo/codespell/ignore_list.txt`.

---

## Template Artifact Warnings (Expected)

These appear in `style.log` for test directories and are NOT fixable:

```
*_tests-implementation.ads:1:NN: warning: unit "Component.X.Implementation.Tester" is not referenced in spec [-gnatwu]
*_tests-implementation.ads:1:NN: warning: with clause might be moved to body [-gnatwu]
*_tests-implementation.ads:2:06: warning: unnecessary with of ancestor [-gnatwr]
```

These come from `redo templates` generated files. Modifying them would be overwritten on next template generation.

---

## Dangerous Removal Patterns

### Operator Visibility Through `use`

```ada
-- This looks unused to GNAT:
with Command_Types; use Command_Types;
-- But removing it breaks:
if Status = Success then  -- = operator from Command_Types

-- RULE: grep for types/operators from the package before removing
```

### AUnit.Assertions False Positive

```ada
-- GNAT says "no entities referenced" but:
with AUnit.Assertions; use AUnit.Assertions;
-- Removing breaks bare Assert(...) calls

-- SAFE to remove ONLY if all assertions are:
Natural_Assert.Eq (...);
Packed_U32_Assert.Eq (...);
-- (no bare Assert calls)
```

### `use Command_Execution_Status`

```ada
-- If you remove this:
use Command_Execution_Status;
-- Then this becomes ambiguous:
return Success;
-- Must qualify: return Command_Execution_Status.Success;
```

---

## Complete Style Check Workflow

```bash
# 1. Run style check
cd src/components/my_component
redo style

# 2. Review output
cat build/style/style.log

# 3. ALL warnings are fixable -- fix them all
# "not referenced in spec" -> move to body
# "might be moved to body" -> move declaration to body
# "unnecessary with of ancestor" -> remove the with clause

# 4. Fix all warnings
# 5. Re-run until clean (zero warnings)
redo style

# 6. Recursive check from project root
cd /path/to/project
redo style_all
```
