# Post-Mortem Debugging: the Last Chance Handler Pipeline

What happens when an exception escapes on the flight target, every place the
evidence lands, and how to decode it. Component/type paths are Adamant
framework (open); project specifics are described as patterns.

## Anatomy: from raise to telemetry

1. An unhandled Ada exception reaches GNAT's hook
   `__gnat_last_chance_handler` (projects export their handler with this
   link name; C++ termination routes into the same last-chance path via a
   project-installed `std::terminate` handler).
2. The handler translates the occurrence into the framework type
   `Packed_Exception_Occurrence.T`
   (`src/types/.../packed_exception_occurrence.record.yaml`): fixed
   100-byte exception name, 300-byte message, U32 stack-trace depth, and a
   fixed-size array of U32 stack-trace addresses. Translation uses
   `Ada.Exceptions.Traceback` with truncation, absorbing secondary
   exceptions -- the capture path must not itself crash.
3. The handler typically writes a copy to a non-volatile region, then
   **spins broadcasting the LCH packet** until the hardware watchdog
   resets. The FSW stops servicing everything else -- including telemetry
   transmission -- which produces the hang signature below.
4. After reboot, the `last_chance_manager` component can dump the NV copy
   by command (`Dump_Last_Chance_Handler_Region`), and its data product
   (first stack-trace address, nonzero = fired) is the "did we LCH?" flag.

`zero_divider` exists to exercise this whole chain on demand: a
magic-number-protected command that divides by zero. Use it to validate the
capture/decode pipeline before you need it in anger.

## The hang-is-a-crash signature

The LCH kills telemetry, so in a ground-system test suite the crash
surfaces as an **infinite wait, not a failure**:

- Housekeeping packet sequence counts freeze; test scripts re-poll the same
  value on a tight cadence.
- On hardware devkits: all status LEDs flashing together is commonly the
  LCH loop, not a heartbeat.
- Emulator/container stdout shows only peripheral noise -- the LCH output
  goes to the FSW UART, which is usually a separate channel (socket
  terminal or file backend), not the emulator's stdout.
- **The LCH output may be a BINARY packet broadcast, not banner text.**
  Flight-class handlers often spin-transmit the packed occurrence as
  CCSDS frames with no human-readable banner (banner prints are commonly
  debug-gated and compiled out). The reliable detectors on a captured
  UART log: the exception NAME appears as ASCII inside the packet stream
  (grep for `CONSTRAINT_ERROR`/`PROGRAM_ERROR`/`STORAGE_ERROR` or run
  `strings` on the capture), and the log grows rapidly after telemetry
  goes silent (the spin loop rebroadcasts continuously -- a
  multi-megabyte UART file from a quiet system IS the crash).

Backstop pattern worth adding to suite utilities: fail a wait if the
housekeeping sequence count does not advance for N real seconds --
converting silent hangs into normal failures that archive their logs.

## Capture paths (in preference order)

1. **Telemetry**: the LCH packet itself, if the ground system was
   listening. The exception name + message often carry the raising
   source location directly (assertion failures include file:line) -- no
   symbolization needed.
2. **NV dump**: after reset, command `last_chance_manager` to dump the
   saved occurrence.
3. **UART log**: route the FSW UART to a file backend or socket terminal in
   the emulator script. For Renode file backends, enable flush-on-write
   (`sysbus.uart CreateFileBackend @<path> true` -- the trailing `true`)
   or output buffers until Renode exits, defeating both live watching and
   crash forensics. Caveat: very early exceptions can predate UART
   bring-up and be swallowed silently.
4. **GDB attach to the spinning target**: the LCH loop is a live, parked
   CPU -- Renode's GDB server still works. Batch-capture without touching
   the running state:

   ```bash
   <cross>-gdb <matching main.elf> -batch \
     -ex 'set pagination off' -ex 'set print pretty on' \
     -ex 'set print elements 1024' \
     -ex 'target remote localhost:3333' \
     -ex 'info registers' \
     -ex 'bt full' > /tmp/lch_capture.txt
   ```

   If the handler stores the occurrence in a known variable, `print` it in
   the same batch (project handlers commonly keep a global occurrence --
   check the project's LCH source for the name). **The Ada-qualified name
   often does not resolve in gdb** (`print pkg.the_global` -> "No
   definition ... in current context", especially for Export/Convention-C
   globals): fall back to the mangled or exported symbol from
   `<cross>-nm main.elf | grep -i <name>` -- print that name directly, or
   overlay the type on its address (`print {<type>} 0x<addr>`), or
   `x/<n>xb 0x<addr>` and decode per the packed layout. Data symbols work
   the same as code symbols here. Get the **matching ELF** from wherever
   the emulator loaded it (e.g. `docker cp` from the container) -- never
   a rebuilt one.

## Symbolization

The trace is raw addresses; two generic resolutions (both standard
binutils -- projects often wrap them in `gnd/bin` helpers, so look there
first):

- **file:line (best)**: `<cross>-addr2line -f -C -e main.elf <addr...>`
- **nearest symbol**: generate a sorted symbol table at build time,
  `<cross>-nm -C -n main.elf > main.nm`, then resolve each address to the
  greatest symbol address <= addr (bisect). This is what ground-side
  exception viewers do, because shipping an nm text dump is lighter than
  shipping the ELF.

**The same-build rule is absolute**: a symbol file from any other build
resolves to plausible-looking but wrong names. Regenerate `main.nm`
whenever the ELF changes, and archive both together for releases.

`scripts/symbolize_traceback.py` in this skill does both modes:

```bash
# nearest-symbol against an nm dump:
python3 symbolize_traceback.py --nm main.nm 0x800123a4 0x80009f10
# file:line via addr2line against the ELF:
python3 symbolize_traceback.py --elf main.elf --prefix riscv32-elf- 0x800123a4
# addresses also accepted on stdin, decimal or hex, one per line or pasted
# from an Ada "Call stack traceback locations:" line
```

### Extracting the trace from a RAW byte capture

When the occurrence arrives as a binary broadcast in a UART capture (or
a memory dump) rather than pasted text, get the addresses out first:

- **Layout is open**: the packed exception occurrence record's YAML
  model gives every field's size and order (name, message, trace depth,
  trace addresses); byte offsets derive directly from it. Packed
  Adamant types serialize **big-endian** unless the type says otherwise
  -- a raw `x/` dump or a little-endian `struct` read shows byte-swapped
  words (a trace word rendered as `0xc4200b80` for `0x800b20c4`, or an
  absurd depth like 117440512 = 0x07000000, is the byte-order tell, not
  corruption).
- **Fast localization**: find the exception-name/message ASCII in the
  capture, then read consecutive big-endian 32-bit words after it and
  keep those inside the code region -- e.g. in Python,
  `struct.unpack_from('>I', buf, off)` filtered to the text segment's
  address range. The trace sits at a fixed offset from the text fields
  per the layout, so one packet yields the full address list.
- Then symbolize as above (same-build rule applies unchanged).

## Interrupt-context traps: the one-frame trace

Traps taken on the interrupt stack (bus faults, alignment traps) yield a
stack trace with **one frame** -- the unwinder cannot cross the trap
handler frame without DWARF for it. The occurrence still names the trap
(e.g. "Unhandled trap: N"); recover the real call chain by re-running:

1. Start the emulator paused (add `pauseEmulation` to the machine script,
   or use the emulator's pause-at-start option).
2. Set a **hardware** breakpoint at the LCH entry symbol (`hbreak`), and
   optionally at the runtime trap handler.
3. Continue; when it fires, `bt full` on the trap frame gives the chain
   the stored trace could not.

## Trap-register decoding (RISC-V)

When attached at/after a trap on RISC-V targets:

| Register | Meaning |
|---|---|
| `mcause` | Trap cause: 0 = instruction address misaligned, 2 = illegal instruction, 4 = load address misaligned, 5 = load access fault, 6 = store/AMO address misaligned, 7 = store/AMO access fault |
| `mepc` | PC of the faulting instruction -- disassemble around it (`x/8i $mepc - 8`) |
| `mtval` | Faulting address; low bits reveal the misalignment (e.g. bit 1 set = 2-byte-aligned access where 4 needed) |

The runtime's trap handlers typically raise `PROGRAM_ERROR` with
"Unhandled trap: N" and no further context -- the registers ARE the
context; capture them before resuming or resetting.

Two verification caveats before decoding:

- **Not every target PROGRAM_ERROR is a trap.** With checks on
  (Debug/Test targets) GNAT raises many failures as software checks
  (`__gnat_rcheck_*` calls -- e.g. a misaligned Address overlay raises
  before any hardware access; see target-pitfalls Family 1). In that
  case mcause/mepc/mtval stay zero and the trap vector is never entered:
  zeroed trap CSRs plus a PROGRAM_ERROR means catch the raise, not the
  trap.
- **The emulator GDB stub may not expose CSRs** to `info registers`
  (they print empty). Read them through the monitor passthrough:
  `monitor sysbus.cpu MCAUSE` (likewise MEPC / MTVAL / MTVEC).

## Crash root-cause checklist (proven suspects, most frequent first)

1. **Unseeded/stale data dependency on first tick**: a component asserts
   `Status = Success` on a data product nothing published yet, or one
   published at Set_Up with timestamp (0,0) that a nonzero stale limit
   rejects. Fix at the source: publish defaults at Set_Up and make stale
   limits tolerate the Set_Up timestamp. Then sweep for the systemic
   pattern -- one grep for assert-on-dependency
   (`grep -rnE "pragma Assert ?\(.*Status" src/components/*/component-*-implementation.adb`)
   typically finds every sibling with the same defect; fixing one crash
   otherwise just reveals the next.
2. **NaN/Inf from wrapped C/C++ algorithms** packed into constrained
   packed types -> `CONSTRAINT_ERROR` on 'Valid checks.
3. **Early-return components** leaving only Set_Up defaults in the product
   database for downstream consumers.
4. **Execution-order violations** -- a consumer ticks before its producer
   in the same rate group.

Isolation technique when the suspect is unknown: binary-search the tick
connections -- disconnect components from the driving tick splitter, confirm
the LCH stops, re-add one per run. Deterministic and fast compared to
staring at 60 components.

**Never fix an LCH by disabling assertions** (`Assertion_Policy (Ignore)`,
dropping `-gnata`): the algorithm then runs on the bad input and emits
garbage telemetry instead of a diagnosable crash.

## Bench operations: headless emulator runs

Scripted crash-reproduction runs fail on operations, not on debugging
theory. The recurring traps, each observed repeatedly in practice:

- **Launch form**: `setsid nohup renode --disable-gui -P <port>
  <script.resc> > run.log 2>&1 < /dev/null &` -- the `< /dev/null` and
  `setsid` matter in container-exec contexts, where an emulator left
  attached to the exec's stdin dies (or hangs the exec) when the shell
  tears down; the `--console` flag exits the moment stdin closes under
  nohup, silently ending the run. Give each concurrent run its own `-P`
  monitor port.
- **Stale instances own the ports**: the default monitor (1234) and GDB
  (3333) ports outlive failed runs; the next launch aborts with
  `AddressAlreadyInUse`, or a gdb attach lands on the WRONG (old)
  machine. Clean up with this as its OWN command -- never in the same
  compound command as a launch line:

  ```bash
  pkill -f '[R]enode' ; sleep 1
  ```

  The bracketed pattern avoids the `pkill -f` self-match trap: if the
  kill pattern appears anywhere in your own compound command line (an
  unbracketed pattern matches itself; a bracketed one still matches a
  launch string elsewhere in the SAME command), pkill kills your own
  wrapper (exit 143). Both halves of the rule have burned careful
  operators -- use the one-liner verbatim, separately.
- **The emulator can outlive or die with its shell** depending on how
  the container exec tears down -- never assume; check the process and
  the ports, not your memory of launching it.
- **Interactive monitor over telnet eats leading bytes** while its line
  editor redraws -- a piped command arrives truncated ("No such command
  or device: etTimeSourceInfo"). Resend until the echo matches, drive it
  from a real socket client with delays, or prefer file backends and
  logs over interactive monitor queries entirely.
- **Batch gdb `continue` may be refused or asynchronous** against an
  emulator stub ("Cannot execute this command while the target is
  running"): treat batch attach as good for HALTED inspection --
  attach, read registers/memory/backtraces, detach. To observe live
  execution points headlessly, prefer emulator-native instrumentation:
  Renode's `sysbus.cpu AddHook <address> "<python>"` logs arbitrary
  state each time the PC passes an address (and watchpoint-style hooks
  exist for data addresses) with no gdb session at all -- resolve the
  addresses from `nm` on the same build.

## Suite automation: terminal sentinels

For scripted cross-target test runs, watch the UART log for terminal
markers instead of fixed timeouts:

- `Unexpected\s+Errors:\s+\d+` -- AUnit run completed (pass or fail)
- `In last chance handler` -- the embedded runtime's LCH banner: the test
  crashed; stop waiting. **Do not rely on this for flight builds**: a
  project LCH that broadcasts binary packets emits no banner -- sentinel
  on the exception-name ASCII inside the stream (`grep -a
  'CONSTRAINT_ERROR\|PROGRAM_ERROR\|STORAGE_ERROR'`), on `strings`
  output, or on unexpected log-size growth instead.
- Emulator-side fatal markers (e.g. `CPU abort` in the emulator log)

Sentinel-driven shutdown makes a 4-second test take 4 seconds instead of
the timeout floor, and converts crashes into immediate, attributable
failures.

## Post-mortem event history

Beyond the exception itself, the framework's `logger` component pattern
keeps a circular buffer of recent events that survives to be dumped and
decoded on the ground:

```bash
gnd/bin/decode_event_log.py <assembly>_events.py post_mortem_dump.bin
```

(framework `gnd/bin`, alongside `decode_event_packets.py` for live-packet
dumps and `socket_event_decoder.py` for a live UDP console decoder; all
take the autogenerated `<assembly>_events.py` as the event dictionary).
The last N events before the crash are frequently more diagnostic than the
stack trace itself.
