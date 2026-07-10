# Advanced GDB Inspection for Adamant/Ada

Beyond breakpoints and catchpoints. Each pattern below is listed with its
Ada/GNAT/Adamant-specific wrinkle -- the part generic GDB knowledge gets
wrong. All work on Linux test binaries; cross-target notes inline.

## Watchpoints: who mutates this?

The tool for "the value is wrong and I do not know which write did it":

```gdb
break <file>:<line-where-scope-exists>   # get into a frame that sees the variable
run
watch self.the_count                     # stops on ANY write, with old/new values
continue
```

- Ada wrinkles: expressions are case-insensitive lowercase in gdb
  (`self.the_count`, not `Self.The_Count`); component state lives in fields
  of `self`, so you must first stop inside any component method for `self`
  to be in scope. For a record field, watch the field, not the record --
  watching a large record falls back to slow software watchpoints.
- `watch -l` (location) keeps watching the resolved address after the frame
  exits -- required when the mutation happens outside the scope where you
  set the watchpoint (a different procedure writing the same component
  state).
- Hardware watchpoint budget is ~4 addresses (x86 and most cross targets);
  on Renode targets prefer `hbreak`/hardware watchpoints -- software
  watchpoints single-step the emulated CPU and are unusably slow.
- `rwatch` (reads) answers the inverse: "who consumes this stale value?"

## Ada tasks (Ravenscar) and threads

Adamant active components each run an Ada task; on Linux these are pthreads,
and GNAT gdb layers task awareness on top:

```gdb
info tasks            # Ada view: task names, states (Runnable/Waiting/...)
task 3                # switch to task 3 (like `thread`, but Ada-aware)
thread apply all bt   # every thread's backtrace -- the deadlock/hang tool
```

- A hung assembly triages fast: attach (`gdb -p <pid>` on Linux, or the
  Renode GDB server), **`info tasks` first** (the Ada view names each task
  and its state -- a `Delay`/`Waiting` task is your hang), then `task <n>`
  + `bt` to see where it is parked. `thread apply all bt` is the fallback
  when `info tasks` is unavailable; read which task is parked
  in a queue wait vs spinning vs gone. Adamant task names come from the
  active component instance names -- `info tasks` maps the blocked task
  straight to the component.
- Attach does not need a restart: `gdb <elf> -p $(pgrep -f main.elf)` on a
  running Linux assembly is non-destructive (`detach` leaves it running).
- Under Renode, tasks appear via the same `info tasks` when the runtime's
  task structures are readable; if not, fall back to `thread apply all bt`
  on the CPU threads plus the runtime's ready-queue globals.

## Records, packed types, and memory

Adamant telemetry/commands are packed records; the pretty-printed view and
the wire view differ, and comparing them is a debugging technique:

```gdb
set print pretty on
print arg                    # structured Ada record view
print arg.header.id          # drill into fields
ptype arg                    # the full type layout as gdb sees it
x/16xb &arg                  # the raw bytes actually in memory
print/x self.the_count       # any value in hex
```

- Packed Adamant types (`Packed_*.T`) have bit-level layouts: `print` shows
  logical field values, `x/…xb` shows the packed bytes -- a mismatch between
  the two views localizes serialization/byte-order defects without any
  print statements.
- `print <type>'(<expr>)` casts; `print {Packed_U32.T} 0x<addr>` overlays a
  type on raw memory (reading a buffer as a packed record).
- Arrays: `print arr(3..5)` slices; `print arr@10` prints 10 elements from
  a pointer-ish start; `set print elements 0` unlimits long buffers.
- `find <start>, <end>, <value>` searches memory for a byte pattern --
  locating a magic number or a leaked buffer content.

## Conditional and scripted stops

```gdb
break <file>:<line> if arg.count mod 2 = 0    # Ada expressions allowed
ignore 1 999                                  # skip breakpoint 1 999 times
commands 1
  silent
  printf "count=%d\n", self.the_count
  continue
end
```

- Condition expressions are Ada (mod, and/or, attributes mostly work);
  when a condition is refused, fall back to `commands` + a scripted check.
- `ignore` + a counter beats stepping through loops; `info breakpoints`
  shows the hit count so far -- run once to count, re-run with `ignore N-1`.
- `display self.the_count` auto-prints on every stop; `finish` runs to the
  caller with the return value; `until <line>` exits loops forward.

## Signals, traps, and interrupts

- Linux: `catch signal SIGSEGV` (or `handle SIGSEGV stop nopass`) stops at
  the fault before the runtime converts it; `bt` then shows the true
  faulting frame. GNAT maps some signals into Ada exceptions -- catching
  the signal fires earlier than `catch exception`.
- Cross/Renode: traps do not raise signals -- the CPU vectors to the trap
  handler. Break there by symbol (`hbreak *__gnat_trap_handler` or the
  runtime's vector symbol), then read the trap registers
  (`info registers mcause mepc mtval` on RISC-V; see the post-mortem
  reference for decoding) and `x/8i $mepc - 8`.
- Interrupt-context frames do not unwind past the handler (one-frame
  traces); the paused-start + `hbreak` recovery in the post-mortem
  reference applies to interactive sessions too.

## Post-mortem handoff and cores

- `generate-core-file <name>` snapshots a live (or just-caught) Linux
  process; anyone can later `gdb <elf> <core>` with full state -- the
  Linux-side analogue of the LCH NV dump, and the right artifact to attach
  to a bug report.
- `gcore <pid>` does the same from outside gdb.

## Renode-specific inspection

- `monitor <renode command>` from an attached gdb passes through: e.g.
  `monitor sysbus ReadDoubleWord 0x<addr>`, `monitor machine
  GetTimeSourceInfo`, pause/start. The emulator can read memory the CPU
  cannot safely touch mid-trap.
- Emulated time stops while gdb has the CPU halted -- watchdogs and
  timeouts do not fire during inspection (unlike attaching to real
  hardware, where the watchdog keeps counting: on hardware, disable or pet
  the watchdog before long pauses, or the target resets mid-session).
- `hbreak`/hardware watchpoints over software ones: the GDB stub
  single-steps software watchpoints, which stalls the whole emulation.
