<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Adamant Style Patterns — Quick Reference

Before/after examples for each enforced rule. See SKILL.md for full rule descriptions.

## Whitespace

### Indentation (`-gnaty3`)
```ada
-- WRONG (2 spaces):       -- RIGHT (3 spaces):
procedure Foo is           procedure Foo is
  X : Integer;                X : Integer;
begin                      begin
  X := 1;                    X := 1;
end Foo;                   end Foo;
```

### Token Spacing (`-gnatyt`)
```ada
-- WRONG:                  -- RIGHT:
Unsigned_32(Value)         Unsigned_32 (Value)
A+B                        A + B
2**16                      2 ** 16
Foo ( X, Y )               Foo (X, Y)
```

### Unnecessary Parentheses (`-gnatyx`)
```ada
-- WRONG:                  -- RIGHT:
return (Self.Count);       return Self.Count;
if (X > 0) then            if X > 0 then
```

## Naming and Casing

### Mixed Case (`-gnatyD`) and Reference Casing (`-gnatyr`)
```ada
-- WRONG:                  -- RIGHT:
MY_COUNTER : Integer;      My_Counter : Integer;
X : Heartbeat_Ok;          X : Heartbeat_OK;  -- match declaration
```

### Keywords, Attributes, Standard Names
```ada
-- WRONG:                  -- RIGHT:
BEGIN                      begin
X := Buffer'length;        X := Buffer'Length;
Y : integer;               Y : Integer;
pragma unreferenced;       pragma Unreferenced;
```

## Control Flow

### Short-Circuit (`-gnatyB`)
```ada
-- WRONG:                  -- RIGHT:
if A > 0 or B > 0 then     if A > 0 or else B > 0 then
if Enabled and Ready then   if Enabled and then Ready then
```

### Multi-Line If (`-gnatyi`)
```ada
-- WRONG:                          -- RIGHT:
if Self.Enabled and then           if Self.Enabled and then
   Self.Count > Threshold then        Self.Count > Threshold
                                   then
```

### Statements on Then/Else (`-gnatyS`)
```ada
-- WRONG:                  -- RIGHT:
if X then return; end if;  if X then
                              return;
                           end if;
```

### End Labels (`-gnatye`)
```ada
-- WRONG:     -- RIGHT:
end;          end My_Proc;
end;          end Component.Foo.Implementation;
```

### Empty Blocks
```ada
-- WRONG:                        -- RIGHT:
if Error then                    if Error then
   -- TODO: handle later            null; -- TODO: handle later
end if;                          end if;
```

## Arrays and Aggregates

### Array Brackets (Ada 2022)
```ada
-- WRONG (obsolescent):    -- RIGHT:
(others => 0)              [others => 0]
(1, 2, 3)                 [1, 2, 3]

-- Records still use ():
(Field_A => 1)             -- correct for records
[others => (Field => 0)]   -- mixed: outer=array, inner=record
```

### Multi-Dimensional `'Length` (`-gnatyA`)
```ada
-- WRONG:                  -- RIGHT:
Buffer'Length              Buffer'Length (1)
```

## With-Clauses

### Unused/Redundant With
```ada
-- Remove unused:
with Tick;  -- not referenced → delete

-- Don't duplicate between spec and body:
-- .ads has: with Tick;
-- .adb has: with Tick;  -- redundant → delete from .adb
```

### `use type` for Operators
```ada
use type Interfaces.Unsigned_32;                    -- gives +, -, =, <
use type Command_Enums.Command_Response_Status.E;   -- gives = operator
```

## Variables

### Unused Variable
```ada
procedure Foo (Arg : in Tick.T) is
   pragma Unreferenced (Arg);
begin
   null;
end Foo;
```

### Assigned-But-Never-Read
```ada
-- pragma Unreferenced does NOT work here. Options:
Natural_Assert.Eq (T.Dispatch_All, 2);              -- use directly
Ignore : Natural; pragma Warnings (Off, Ignore);     -- suppress
Ignore_Count : Natural;                               -- naming convention
```

### Constants
```ada
-- WRONG:                                    -- RIGHT:
The_Time : Sys_Time.T := Self.Sys_Time_T_Get;   The_Time : constant Sys_Time.T := Self.Sys_Time_T_Get;
```

## Numeric Literals
```ada
-- WRONG:              -- RIGHT:
16#FFFFFFFF#           16#FFFF_FFFF#
1000000                1_000_000
```

## YAML

### Document Start and Quoting
```yaml
---                                          # required marker
default: "Sensor_Id.Sensor_Id_Type.Temp_1"  # quoted enum default
```

### Component `with:` (Only for Preamble)
```yaml
# WRONG:           # RIGHT:
with:              with:
  - Tick             - Interfaces
  - Command        preamble: |
                     use Interfaces;
```

### 2-Space Indentation
```yaml
# WRONG (4 spaces):     # RIGHT (2 spaces):
fields:                  fields:
    - name: value          - name: value
```

## Python
```python
from environments import test  # noqa: F401   # suppress unused import warning
```

## Dangerous Removals

### Operator Visibility
```ada
-- Looks unused but provides = operator:
with Command_Types; use Command_Types;
-- grep for types/operators BEFORE removing any with
```

### Ambiguous Returns
```ada
-- Removing `use Command_Execution_Status;` makes this ambiguous:
return Success;
-- Must qualify: return Command_Execution_Status.Success;
```
