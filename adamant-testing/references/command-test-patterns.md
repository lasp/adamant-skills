<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Command Test Patterns

Core command dispatch and argument construction patterns.

---

## Dispatch_All (Active Components)

```ada
Natural_Assert.Eq (T.Dispatch_All, 5);  -- Function returning Natural
```

Dispatch_All processes queued async messages. Must capture or use return value. Passive components don't have Dispatch_All.

## Command Argument Construction

```ada
-- No arguments
T.Command_T_Send (T.Commands.Reset_Monitor);

-- Record arguments
T.Command_T_Send (T.Commands.Set_Gains ((Kp => 2.0, Ki => 0.0, Kd => 0.0)));

-- Packed type arguments
T.Command_T_Send (T.Commands.Set_Priority ((Value => 10)));
```

Always use `T.Commands.<Name>` -- the tester has correct ID base. Response verification patterns are in SKILL.md.