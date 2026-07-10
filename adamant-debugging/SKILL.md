---
name: adamant-debugging
description: Debug Adamant software at three levels -- interactive GDB on unit tests and assemblies (breakpoints, stepping, Ada catchpoints), post-mortem crash triage (Last Chance Handler packets, stack-trace symbolization, Renode attach), and target/compiler-level pitfalls (works-on-Linux-traps-on-target, codegen bugs, stale generated code). Use when a test fails and assertions/prints are not enough, when the FSW crashes or a test suite hangs, when decoding an exception traceback, or when behavior differs between Linux and the flight target.
---

# adamant-debugging

Three debugging layers, in escalation order: interactive GDB (a failing test
in front of you), post-mortem triage (a crash already happened -- decode what
the flight software left behind), and target/compiler-level (the bug only
exists on the cross target). The framework already builds debuggable
artifacts and ships crash-reporting components -- the skill is knowing which
level you are at and the Ada-specific moves at each.

## Quick Start (debug a failing unit test)

```bash
cd src/components/<component_name>/test
redo test                        # builds build/bin/Linux_Test/test.elf
gdb build/bin/Linux_Test/test.elf
```

```gdb
catch exception          # break wherever any Ada exception is raised
run                      # runs the whole AUnit suite
bt                       # on catch: raise point <- test proc <- AUnit caller
```

**Diagnosis standard: a root cause is demonstrated, not inferred.** Reading
source produces a hypothesis; the diagnosis is complete only when the
mechanism has been shown at runtime -- the actual values at the defect (a
catchpoint stop, a breakpoint print, a watchpoint transition). This is what
separates "the bug is probably X" from a report a reviewer can act on, and
it routinely falsifies convincing source-reading theories.

No flags, no rebuild-for-debug: Linux test binaries are always compiled
`-O0 -g -gnata -gnatVa` and never stripped, so source-level debugging works
on the artifact `redo test` already built.

## Build targets: which artifacts are debuggable

Debug readiness is decided by the build TARGET, not a flag:

| Target family | Switches | Steppable? |
|---|---|---|
| `Linux` (= `Linux_Debug`), `Linux_Test`, `Linux_Coverage` | `-O0 -g -fstack-check -gnato -gnata -gnatVa` | Yes -- honest line-by-line |
| Bareboard `<Platform>_Debug` / `_Test` variants | `-g3 -ggdb -O0 -gnata -gnatVa` | Yes |
| Bareboard `_Production` / `_Development` | `-g3 -ggdb` **plus `-O2`** | Loadable; stepping jumpy, locals may be optimized out |

- There is no production Linux mode -- `Linux` is a rename of `Linux_Debug`.
- Bareboard ELFs keep symbols in **every** mode, so a production ELF loads in
  gdb -- but for honest stepping build the `-O0` variant:
  `redo build/bin/<Platform>_Debug/main.elf`.
- `DEBUG=1 redo ...` is **build verbosity** (prints gprbuild/gcc command
  lines), not debug symbols -- the target already provides those.
- Executables land at `<src_dir>/build/bin/<TARGET>/<test|main>.elf`; test
  dirs force the `_Test` suffix automatically via `env.py`. `redo targets`
  lists every target.

## Ada-specific GDB moves

1. **Set breakpoints by `file:line`, not Ada name** -- the expression form
   (`break My_Package.My_Proc`) frequently fails to resolve:

   ```gdb
   break <unit_name>-implementation.adb:326
   ```

   For symbolic breakpoints use the linker name (Ada mangles with double
   underscores): `nm test.elf | grep -i <proc_name>` then break on
   `<unit>__implementation__<proc>`.

2. **`catch exception` is the failing-test power tool** -- `-gnata` means a
   failing `pragma Assert` raises `ADA.ASSERTIONS.ASSERTION_ERROR`; the
   catchpoint stops at the raise with the full stack:

   ```gdb
   catch exception                    # all Ada exceptions
   catch exception unhandled          # only ones that would kill the test
   catch assert                       # only failed assertions
   ```

3. **No single-test filter** -- the AUnit harness runs the whole suite;
   break in the specific `Test_*` procedure and `continue` past the rest.

4. **Validity checks change what you see** -- `-gnatVa` +
   Initialize_Scalars means uninitialized scalars hold recognizable invalid
   patterns; an extreme value in `info locals` usually means "never
   assigned", not "corrupted".

## Debugging environment

- gdb ships with the GNAT toolchain and is on PATH **only in the activated
  environment** (container login via the project's env tooling); a bare
  `docker exec` shell will not find it.
- DWARF records build-environment paths. Inside the container everything
  matches; a host gdb works on Linux-target binaries if launched from the
  source dir (cwd resolution) or with
  `set substitute-path <container_prefix> <host_checkout>`.
- **Rebuild before debugging** -- "Source file is more recent than
  executable" means line numbers are lying.
- Assembly binaries on Linux: same story without the `_Test` suffix --
  `redo build/bin/Linux/main.elf`, then `gdb` it (`redo run` = build + run).

## Cross targets: Renode and JTAG

Cross ELFs cannot execute on the host. Attach a **cross** gdb
(`riscv32-elf-gdb`, `arm-eabi-gdb`) to a GDB server:

- **Renode**: the project's `.resc` loads the ELF (`sysbus LoadELF`) and
  starts `machine StartGdbServer 3333`; attach with the ELF as **symbols
  only -- no `load`** (Renode already loaded it):

  ```bash
  <cross>-gdb build/bin/<Platform>/main.elf -ex 'target remote :3333'
  ```

  Ctrl-C halts the live target; `monitor <cmd>` passes to the Renode
  console. Projects wrap this in `redo renode` / `debug_renode.sh` scripts
  beside the assembly or `test_renode` dirs -- discover them before
  hand-rolling. Server in a different container: attach via
  `host.docker.internal:3333`.
- **JTAG hardware**: probe's GDB server runs on the host (USB) with its
  all-interfaces flag; gdb in the container attaches via
  `target extended-remote host.docker.internal:<port>` and owns the
  bring-up -- script it (`gdb -nx -x bringup.gdb`): reset, halt,
  `file <elf>`, `load` (needs a RAM-loader link), break, continue.

## Post-mortem: crashes and the Last Chance Handler

When an exception escapes on the flight target, GNAT's
`__gnat_last_chance_handler` hook fires and Adamant's LCH pattern captures a
`Packed_Exception_Occurrence` (exception name, message, and a stack-trace
address array) and broadcasts it as a telemetry packet until watchdog reset.
Framework components involved (all open, in `src/components/`):

| Component | Role in debugging |
|---|---|
| `zero_divider` | Commandable, magic-number-protected crash trigger -- **the LCH test fixture**; also supplies the LCH packet definition |
| `last_chance_manager` | Dumps/clears the non-volatile copy of the last exception by command; data product doubles as an "LCH fired" flag |
| `stack_monitor` | Per-task stack + secondary-stack usage percent, per tick |
| `cpu_monitor` / `queue_monitor` | Per-task CPU windows / queue high-water marks |
| `memory_dumper` | Command-driven dump of configured memory regions |
| `logger` + `gnd/bin/decode_event_log.py` | Post-mortem circular-buffer event dump -> decoded event list |

Triage rules (each learned from a real incident -- details and the full
runbook in `references/post-mortem-and-lch.md`):

- **A hung test suite IS a crash until proven otherwise.** The LCH stops
  telemetry; downstream waits spin forever, so the failure never reports.
  Check whether housekeeping sequence counts froze.
- **Symbolize against the same build.** Generate a symbol table at build
  time (`<cross>-nm -C -n main.elf > main.nm`); resolve trace addresses by
  nearest-symbol-below, or `<cross>-addr2line -f -C -e main.elf <addr>` for
  file:line. A symbol file from any other build resolves plausible garbage.
- **The crashed target is still attachable**: Renode's GDB server works
  while the CPU spins in the LCH -- capture the exception occurrence and
  registers via a batch gdb script, no reproduction needed.
- Interrupt-context traps record only ONE frame (the unwinder cannot cross
  the trap handler); recover the real chain by re-running paused with a
  hardware breakpoint at the LCH entry.

`scripts/symbolize_traceback.py` (in this skill) resolves pasted traceback
addresses against an nm dump or ELF -- see the reference for usage.

## Target/compiler-level debugging

"Works on Linux, traps on the flight target" is a class, not a fluke:
undefined behavior is target-dependent, so **cross-run the unit tests on the
flight target** (`redo test_renode` where the project provides it) rather
than trusting host green. The known pitfall families -- alignment-erroneous
overlays, scalar-storage-order codegen bugs, per-flag workarounds pinned in
gpr files, and the post-rebase stale-generated-code signatures -- are in
`references/target-pitfalls.md` with their proof techniques (bit-pattern
analysis, disassembly around the faulting PC, RISC-V trap-register
decoding).

## Project tooling discovery

Closed-source projects commonly ship debug helpers the framework does not:
symbolizers, per-task stack maps, UART/log capture scripts, scripted gdb
bring-ups. Before hand-rolling, look in the project's ground tooling and
assembly directories:

```bash
ls gnd/bin/ | grep -iE 'stack|trace|decode|symbol|log'
ls src/assembly/<name>/main/*.sh src/assembly/<name>/main/*.gdb
```

Prefer the project's own scripts -- they encode target-specific details
(ports, ELF paths, register sets) this skill keeps generic.

## Checklist

1. Pick the layer: failing test in hand -> interactive gdb; crash/hang
   already happened -> post-mortem; target-only misbehavior -> pitfalls ref
2. Rebuild so symbols match source; pick the `-O0` target if stepping
3. Interactive: `catch exception` before `run`; breakpoints by `file:line`;
   escalate to watchpoints / `info tasks` / memory views per the advanced
   reference when the mechanism is a mystery write, a hung task, or a
   packed-layout mismatch
4. Cross: server first (Renode/JTAG), then cross gdb; `load` only on JTAG
5. Post-mortem: capture the LCH output (telemetry, NV dump via
   `last_chance_manager`, UART log, or gdb attach to the spinning target)
6. Symbolize addresses against the SAME build's nm dump or ELF
7. Suite hang: check for frozen housekeeping counters before debugging the
   test script
8. Target-only bug: reproduce under Renode, decode the trap registers,
   check the pitfalls reference before suspecting your code

## Common Errors

1. **`break Package.Proc` "not defined"** -- use `file:line` or the mangled
   `pkg__proc` name from `nm`.
2. **Breakpoint never hits / lines mismatch** -- stale binary; gdb warned
   "Source file is more recent than executable"; rebuild.
3. **`gdb: command not found` in the container** -- bare shell; enter the
   activated environment (gdb lives in the toolchain, not `/usr/bin`).
4. **No source listing on host gdb** -- DWARF has container paths; `cd` to
   the source dir or `set substitute-path`.
5. **Stepping jumps around on a bareboard ELF** -- attached to an `-O2`
   image; build and load the `_Debug` variant.
6. **`load` fails/hangs against Renode** -- Renode already `LoadELF`ed;
   attach with symbols only (`load` belongs to the JTAG flow).
7. **Expected a debug build from `DEBUG=1`** -- that is build verbosity;
   the target selects switches, and tests/Linux are already debug.
8. **Cannot reach the GDB server from the container** -- server listening
   on another host/container's localhost; use
   `host.docker.internal:<port>` and all-interfaces server flags.
9. **Symbolized trace names look wrong / nonsensical** -- symbol file and
   ELF are from different builds; regenerate the nm dump from the exact ELF
   that was running.
10. **Suite "hangs" with no failure** -- likely an LCH crash upstream:
    telemetry died, waits spin. Triage as a crash (post-mortem reference),
    not as a slow test.
11. **Single-frame stack trace from an interrupt trap** -- expected; the
    unwinder stops at the trap boundary. Use the paused-emulation +
    hardware-breakpoint recovery in the post-mortem reference.
12. **Assertions "fixed" by disabling them** -- never ship
    `Assertion_Policy (Ignore)` to hide an LCH: the code then runs on the
    bad input and produces garbage instead of a diagnosable crash. Fix the
    dependency (fetch + early-return on non-Success).

## References

- `references/gdb-advanced-inspection.md` -- watchpoints (who mutates this?),
  Ada task/thread triage (`info tasks`, `thread apply all bt`, live attach),
  packed-record vs raw-memory views, conditional/scripted stops, signals vs
  cross-target traps, core-file handoff, Renode monitor passthrough. Read
  when breakpoints + catchpoints are not enough to demonstrate a mechanism.
- `references/post-mortem-and-lch.md` -- LCH anatomy and wire format,
  capture paths (telemetry / NV dump / UART / gdb attach), symbolization
  pipeline + script usage, interrupt-context trap recovery, RISC-V trap
  register decoding, crash root-cause checklist, suite-hang signatures.
  Read when a crash or hang already happened.
- `references/target-pitfalls.md` -- works-on-Linux-traps-on-target
  families with reproducers and proof techniques; compiler-bug workaround
  flag pinning; post-rebase stale-codegen signature table; runtime
  debug-variant builds; monitor components for resource debugging. Read
  when behavior differs between host and flight target, or after a rebase
  produces baffling compile errors.
- `scripts/symbolize_traceback.py` -- stdlib-only resolver: traceback
  addresses + (nm dump | ELF + binutils prefix) -> symbol+offset and
  optional file:line.
