---
name: adamant-debugging
description: Debug Adamant binaries with GDB -- unit tests, Linux assembly binaries, and cross-compiled bareboard targets under Renode or JTAG hardware. Use when a test fails and assertions/prints are not enough, when stepping through component or assembly code, when catching Ada exceptions at the raise point, or when choosing which build target gives honest (-O0) stepping.
---

# adamant-debugging

GDB workflows for Adamant executables. The framework's build targets already
produce debuggable artifacts -- the skill is knowing which target carries which
switches, where the binary lands, and the Ada-specific GDB moves that differ
from C/C++ debugging.

## Quick Start (debug a failing unit test)

```bash
cd src/components/<component_name>/test
redo test                        # or: redo all -- builds build/bin/Linux_Test/test.elf
gdb build/bin/Linux_Test/test.elf
```

```gdb
catch exception          # break wherever any Ada exception is raised
run                      # runs the whole AUnit suite
bt                       # on catch: raise point <- test proc <- AUnit caller
```

No flags, no rebuild-for-debug: Linux test binaries are always compiled
`-O0 -g -gnata -gnatVa` and are never stripped (no strip step exists in the
build rules), so full source-level debugging works on the artifact
`redo test` already built.

## Why builds are already debuggable (and when they are not)

Debug readiness is decided by the build TARGET, not a flag:

| Target family | Switches | Steppable? |
|---|---|---|
| `Linux` (= `Linux_Debug`), `Linux_Test`, `Linux_Coverage` | `-O0 -g -fstack-check -gnato -gnata -gnatVa` | Yes -- honest line-by-line |
| Bareboard `<Platform>_Debug` / `_Test` variants | `-g3 -ggdb -O0 -gnata -gnatVa` | Yes |
| Bareboard `_Production` / `_Development` | `-g3 -ggdb` **plus `-O2`** | Loadable, but stepping is jumpy and locals may be optimized out |

Rules that follow from the table:

- There is no production Linux mode -- `Linux` is a rename of `Linux_Debug`,
  so anything built for host execution is already a debug build.
- Bareboard ELFs keep symbols in **every** mode (the base gpr sets
  `-g3 -ggdb` unconditionally), so a production ELF loads in gdb -- but for
  honest stepping build the `-O0` variant explicitly:
  `redo build/bin/<Platform>_Debug/main.elf` and point gdb's `file` at it.
- `DEBUG=1 redo ...` is **build verbosity** (prints gprbuild/gcc command
  lines), not debug symbols. The name collides with what you might expect;
  symbols come from the target, which already provides them.

Artifact locations: executables land at
`<src_dir>/build/bin/<TARGET>/<test|main>.elf`; test dirs force the `_Test`
target automatically via their `env.py`, so you do not set TARGET by hand.
`redo targets` lists every available target with its gpr file.

## Ada-specific GDB moves

These differ from C/C++ debugging and are where cold-start time goes:

1. **Set breakpoints by `file:line`, not Ada name.** The Ada expression form
   (`break My_Package.My_Proc`) frequently fails to resolve; `file:line`
   always works:

   ```gdb
   break <unit_name>-implementation.adb:326
   ```

   If you need a symbolic breakpoint, use the linker name -- Ada mangles
   with double underscores. Find it first:

   ```bash
   nm build/bin/Linux_Test/test.elf | grep -i <proc_name>
   # e.g. <unit>__implementation__test_set_up
   ```

2. **`catch exception` is the failing-test power tool.** Debug/test targets
   compile with `-gnata`, so a failing `pragma Assert` raises
   `ADA.ASSERTIONS.ASSERTION_ERROR`. Catch it and gdb stops at the raise
   with the full call stack -- almost always faster than locating the
   failing assertion by reading test output:

   ```gdb
   catch exception                    # all Ada exceptions
   catch exception unhandled          # only ones that would kill the test
   catch assert                       # only failed assertions
   ```

3. **There is no single-test filter.** The AUnit harness runs the whole
   suite; to debug one test, break in that `Test_*` procedure (file:line)
   and `continue` past everything before it.

4. **Validity checks change what you see.** `-gnatVa` + Initialize_Scalars
   means uninitialized scalars hold recognizable invalid patterns rather
   than garbage -- a variable showing an extreme/invalid value in
   `info locals` usually means "never assigned", not "corrupted".

## Debugging environment

- gdb ships with the GNAT toolchain and is on PATH **only in the activated
  environment** (container login shell via the project's env tooling). A
  bare `docker exec` shell will not find it -- it lives under the toolchain
  installation, not `/usr/bin`.
- DWARF records build-environment paths. Debugging inside the container
  matches exactly. A host gdb also works on Linux-target binaries (they are
  native executables): run gdb from the source directory so sources resolve
  via cwd, or map the prefix:

  ```gdb
  set substitute-path <container_build_prefix> <host_checkout_path>
  ```

- **Rebuild before debugging.** gdb's "Source file is more recent than
  executable" warning means line numbers are lying; `redo test` first.
- Use `gdb -nx` if a host `~/.gdbinit` interferes with batch scripts.

## Assembly binaries on Linux

Same story as tests, without the `_Test` suffix -- from the directory
containing `main.adb`:

```bash
redo build/bin/Linux/main.elf     # Linux = Linux_Debug, -O0 -g
gdb build/bin/Linux/main.elf      # or: redo run  (build + execute)
```

## Cross targets: Renode emulation

Cross-compiled ELFs cannot execute on the host (`redo test` on a cross
target builds `test.elf`, then stops with a hint to run it under Renode).
The debug pattern -- project-provided, but consistent wherever it appears:

1. A Renode script (`.resc`) creates the machine from a platform
   description, loads the same ELF the build produced
   (`sysbus LoadELF @build/bin/<Platform>/main.elf`), starts a GDB server
   (`machine StartGdbServer 3333`), and starts emulation -- the target runs
   immediately; gdb attaches to a live system.
2. Attach with the **cross** gdb from the target's toolchain (e.g.
   `riscv32-elf-gdb`, `arm-eabi-gdb`), giving the ELF for symbols only --
   no `load`, Renode already loaded it:

   ```bash
   <cross>-gdb build/bin/<Platform>/main.elf -ex 'target remote :3333'
   ```

3. Ctrl-C halts the live target; then breakpoints/stepping work normally.
   `monitor <command>` passes through to the Renode console.
4. Projects typically wrap steps 1-2 in `redo renode` / `debug_renode.sh`
   scripts beside the assembly or `test_renode` directory -- look for them
   before hand-rolling; each `test_renode` dir follows the same
   resc-plus-attach-script shape.

If the Renode server runs in a different container than gdb, attach via the
host gateway (`target remote host.docker.internal:3333`) instead of
localhost.

## Cross targets: JTAG hardware

Same attach model with a hardware GDB server (e.g. a SEGGER J-Link) instead
of Renode, with two differences:

- The probe's server runs on the **host** (USB access); gdb runs in the
  container and reaches it via `target extended-remote
  host.docker.internal:<port>` -- start the server with its
  listen-on-all-interfaces option or the container cannot connect.
- gdb must put the target in a known state and load the image itself.
  Script it (`gdb -nx -x <file>.gdb`) so every session is reproducible:

  ```gdb
  target extended-remote host.docker.internal:2331
  monitor reset
  monitor halt
  file build/bin/<Platform>/main.elf
  load                       # works when the image links with a RAM loader
  break main.adb:11
  continue
  ```

## IDE route

`redo build/gpr/test.gpr` (or `main.gpr`) in the executable's directory
generates a standalone GPRbuild project with the computed source paths --
open it in GNAT Studio and use its integrated gdb instead of the CLI.

## Checklist

1. Rebuild the executable (`redo test` / `redo all`) so symbols match source
2. Pick the honest target: Linux/`_Test` are already `-O0 -g`; for bareboard
   build the `_Debug` variant if stepping matters
3. Launch gdb on `build/bin/<TARGET>/<test|main>.elf` from the source dir
   (in the activated environment, or fix `substitute-path` on host)
4. `catch exception` before `run` when hunting a failure
5. Breakpoints by `file:line`; symbolic only via `nm`-discovered `__` names
6. Cross target: start Renode (or the JTAG server) first, then attach the
   cross gdb with the ELF as the symbol file
7. On attach to a live Renode target: no `load`; on JTAG: scripted
   reset/halt/`load`

## Common Errors

1. **`break Package.Proc` reports "not defined"** -- Ada name resolution in
   gdb is unreliable; use `file:line`, or the mangled `pkg__proc` name from
   `nm`.
2. **Breakpoint never hits / lines do not match source** -- stale binary.
   gdb warned "Source file is more recent than executable" at load; rebuild.
3. **`gdb: command not found` in the container** -- bare shell without the
   activated environment; enter via the project's env login (gdb lives in
   the toolchain directory, not `/usr/bin`).
4. **No source listing, only addresses (host gdb)** -- DWARF paths are
   container paths; `cd` to the source dir before launching or
   `set substitute-path`.
5. **Stepping jumps around / locals `<optimized out>` on a bareboard ELF** --
   you attached to a `_Production`/`_Development` (-O2) image; build and
   load the `_Debug` variant.
6. **`load` fails or hangs on a Renode-attached session** -- Renode already
   loaded the ELF via `LoadELF`; give gdb the ELF as symbols only and skip
   `load` (that command belongs to the JTAG flow with a RAM loader).
7. **Expected a debug build from `DEBUG=1`** -- that variable controls build
   verbosity, not compilation switches; the target selects switches, and
   debug-capable ones are already the default for tests and Linux.
8. **Cannot connect to the GDB server from the container** -- the server is
   listening on localhost of a different host/container; use
   `host.docker.internal:<port>`, and start hardware servers with their
   all-interfaces flag.

## References

None yet -- workflows above are self-contained. Renode `.resc`/platform
authoring belongs to project repos; JTAG server specifics belong to the
probe vendor's documentation.
