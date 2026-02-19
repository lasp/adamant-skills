<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Setup and Initialization Patterns

Init/Set_Up variants, Tear_Down, and Tick construction patterns from the Adamant test corpus.

---

## 1. Set_Up_Test Patterns

### 1a. Simplest passive component (no init, no Set_Up)

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
end Set_Up_Test;
```

Source: edge_detector. Some components have no init params AND no Set_Up
logic. Both Init and Set_Up are optional -- only call them if the component
YAML declares `init:` parameters or the component has a `Set_Up` override.

### 1b. Passive component with Set_Up but no init params

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;
```

Source: uptime_counter, mode_manager, heartbeat_monitor. Most
components have Set_Up even without init params (registers commands, etc.).

### 1c. Passive component with init params

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Init (Low_Threshold => 20, Critical_Threshold => 10);
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;
```

Source: battery_monitor. Order is critical: Init_Base -> Connect -> Init -> Set_Up.
Init params come from the component's `init` section in YAML. They go to
`Component_Instance.Init`, never to `Init_Base`.

### 1d. Passive component with packed type init param

```ada
Self.Tester.Component_Instance.Init (Default_State => (Value => 1));
```

Source: power_switch. When init param is a packed type (Packed_U32.T, etc.),
wrap in aggregate: `(Value => N)`.

### 1e. Active component (needs Queue_Size)

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base (Queue_Size => Self.Tester.Component_Instance.Get_Max_Queue_Element_Size * 50);
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;
```

Source: command_queue. The `Queue_Size` argument is ONLY for active
components. It sizes the internal async message queue in bytes.
Use `Get_Max_Queue_Element_Size * N` to hold N messages.

### 1f. Active component with init params

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base (Queue_Size => Self.Tester.Component_Instance.Get_Max_Queue_Element_Size * 60);
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Init (Rate_Threshold => (Value => 10));
   Self.Tester.Component_Instance.Set_Up;
end Set_Up_Test;
```

Source: event_aggregator. Active + init params = both Queue_Size in
Init_Base AND params in Component_Instance.Init.

### 1g. Passive component with data dependencies

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   Self.Tester.Component_Instance.Set_Up;
   -- Set tester time to match tick time (prevents staleness failures)
   Self.Tester.System_Time := Test_Time;
   Self.Tester.Data_Dependency_Timestamp_Override := Test_Time;
end Set_Up_Test;
```

Source: threshold_monitor. Data dependency timestamps MUST be non-zero and
must match the tick time, or the framework flags the data as stale.
Also set initial data dependency values:
```ada
Self.Tester.Setpoint := (Value => 0.0);
Self.Tester.Process_Value := (Value => 0.0);
```
Source: pid_controller.

### 1h. Deferred init (per-test initialization)

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
begin
   Self.Tester.Init_Base;
   Self.Tester.Connect;
   -- Component init is done in individual tests with specific values
end Set_Up_Test;

-- Then in each test:
overriding procedure Test_Nominal_Check (Self : in out Instance) is
   T : ... renames Self.Tester;
begin
   T.Component_Instance.Init (Check_Period => 1);
   T.Component_Instance.Set_Up;
   -- ... test logic ...
end Test_Nominal_Check;
```

Source: health_checker. When tests need different init params, defer Init
and Set_Up to each test body. This is common for components where init
params fundamentally change behavior.

### 1i. T. shorthand in Set_Up/Tear_Down

```ada
overriding procedure Set_Up_Test (Self : in out Instance) is
   T : Component.Telemetry_Filter.Implementation.Tester.Instance_Access renames Self.Tester;
begin
   T.Init_Base;
   T.Connect;
end Set_Up_Test;
```

Source: telemetry_filter. Some components use the T rename in fixtures too.
Both styles (Self.Tester.* vs T.*) are valid.

---


## 2. Tear_Down_Test

Always the same pattern across all components:

```ada
overriding procedure Tear_Down_Test (Self : in out Instance) is
begin
   Self.Tester.Final_Base;
end Tear_Down_Test;
```

No exceptions. No cleanup needed beyond Final_Base.

---


## 13. Tick Construction Patterns

### 13a. Inline tick (most common)

```ada
T.Tick_T_Send ((Time => (0, 0), Count => 1));
```

Fine for simple tests where data dependencies are not involved.

### 13b. Named constant tick

```ada
The_Tick : constant Tick.T := (Time => (0, 0), Count => 1);
-- or positional:
The_Tick : constant Tick.T := ((0, 0), 1);
```

Source: pid_controller, command_queue. Better when reused.
Requires `with Tick;`.

### 13c. Tick with matching data dependency time

```ada
Test_Time : constant Sys_Time.T := (100, 0);
The_Tick : constant Tick.T := (Time => Test_Time, Count => 0);
```

Source: threshold_monitor. MUST use non-zero time and match
`Data_Dependency_Timestamp_Override` to avoid staleness errors.

### 13d. Loop ticks with cast

```ada
for I in 1 .. 5 loop
   T.Tick_T_Send ((Time => (0, 0), Count => Unsigned_32 (I)));
end loop;
```

Source: uptime_counter. `Count` is `Interfaces.Unsigned_32`, loop variable
is Integer. Cast required. Requires `with Interfaces; use Interfaces;`.

### 13e. Tick count as component input

```ada
-- Count=81 -> SOC = 100 - 81 = 19 (below Low_Threshold=20)
T.Tick_T_Send ((Time => (0, 0), Count => 81));
Natural_Assert.Ge (T.Soc_Low_Warning_History.Get_Count, 1);
```

Source: battery_monitor. Some components use `Count` as input data
(not just a sequence number). The tick count drives behavior.

---

