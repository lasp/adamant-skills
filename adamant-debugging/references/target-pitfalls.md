# Target and Compiler-Level Debugging

For bugs that only exist on the cross target, and build-system states that
masquerade as code bugs. Every family here was diagnosed on a real program;
the proof techniques transfer even where the specific bug does not.

## The governing principle

**Undefined/erroneous execution is target-dependent.** Code that is
erroneous per the Ada RM can run correctly on x86_64 Linux for years and
hardware-fault on the flight target on the first tick, with no compiler
warning at either point. Consequences:

- Host-green is not target-green: run unit tests on the flight target
  (`redo test_renode` where the project provides the rule) as a first-class
  gate, not a spot check.
- "It works on Linux" is evidence about Linux, not about your code.

## Family 1: alignment-erroneous overlays

Overlaying a composite type onto a byte array (`for X'Address use ...`,
unchecked conversions to access types) is **erroneous** if the runtime
address violates the type's alignment (Ada RM 13.3(13/3)). x86_64 tolerates
misaligned loads; RISC-V emits `lw` and hardware-faults (mcause=4).

- Detection: trap with `mcause=4`; `mtval` low bits show the misalignment;
  disassembly around `mepc` shows the wide load and the offset arithmetic
  that produced the misaligned address.
- Mitigation: only overlay types with `'Alignment = 1` (packed byte-level
  types); assert `T'Alignment = 1` beside the overlay as executable
  documentation. Never overlay types whose fields the compiler may access
  with wide loads.

## Family 2: codegen bugs around representation clauses

Scalar_Storage_Order (byte-swapped types) interacts badly with newer
syntax forms on some cross ports -- observed: SSO **not honored** inside an
iterated component association (`[for J in Src'Range => Src (J)]`) on a
RISC-V port, producing byte-reversed scalars, while the array-type
conversion form (`T (Src)`) lowers through the SSO-aware path correctly.

- Detection technique -- **bit-pattern proof**: take the wrong value's raw
  bits, byte-reverse them by hand, and show the result is the expected
  value (or a telltale like a quiet NaN). This turns "flaky float bug"
  into "byte order, codegen, this construct" in one step.
- When a compiler bug is confirmed: report upstream with the minimal
  reproducer, and pin the workaround **where it is load-bearing** -- a
  comment at the workaround site naming the vendor ticket, plus the flag
  in the affected gpr files (e.g. a known case pins `-fno-tree-sra` to
  keep SSO honored for constant declarations). Unpinned workarounds
  evaporate in refactors.

## Proof techniques (transferable)

1. **Disassemble around the faulting PC**: `x/8i $mepc - 8` (or objdump the
   ELF at that address) -- the instruction plus the preceding address
   arithmetic usually names the construct that generated it.
2. **Bit-pattern analysis**: byte-reverse / bit-slice the observed wrong
   value against the expected one before theorizing.
3. **Minimal reproducer on both targets**: same source, Linux target and
   cross target; "passes host, traps target" plus the disassembly is a
   complete compiler-bug report.
4. **Read the generated code, not just yours**: for framework-generated
   packed types, the fault is often in `build/src` codegen -- the offset
   table in the generated validation/serialization functions shows exactly
   which field access misaligns.

## Post-rebase stale generated code

The build system does not always detect that generated `build/src` sources
are stale against rebased YAML models. The resulting compile errors look
like real defects but follow a recognizable signature table:

| Error string shape | Actual meaning |
|---|---|
| `"<Enum>" not declared in "<Pkg>"` | stale generated enum package |
| `no selector "Attach_..."/"..._Access" for private type "Instance"` | stale generated component base |
| `unmatched actual "..._Id_Base"` in instantiation | stale generated id-base packages |

Confirm before debugging: `git diff origin/<branch> HEAD -- <model>.yaml`
coming back empty means the source model is fine and the generated code is
stale. Fix by restarting the build environment and regenerating, never by
"fixing" the generated code.

Related environment forensic: if a build error cites file content you have
already changed, suspect a stale bind-mount cache -- compare
`stat -c 'inode=%i size=%s mtime=%Y' <file>` on host vs container; an
environment restart (not a build clean) resolves it.

## Custom runtime debug builds

Bare-metal targets run project-built GNAT runtimes (BSP layout:
`gnat/` RTL + device bindings, `gnarl/` tasking, `ld/` linker scripts, with
`*_user/` overlay hooks). Two debugging-relevant facts:

- Runtime build scripts typically accept a debug variant (building with
  the runtime's Debug flag and installing as `<name>-debug`) -- use it when
  stepping **into** runtime code (task dispatching, exception propagation,
  the last-chance path itself: `a-elchha.adb` is the runtime side of the
  LCH hook).
- Emulator-specific runtime overlays exist as tiny linker-script overlays
  (e.g. re-pointing RAM to the emulator's larger memory) -- if a binary
  runs on hardware but not the emulator or vice versa, check which runtime
  variant it was linked against before debugging the program.

Bare-board unit tests have no parameter-manager staging: unstaged
parameters are uninitialized memory, so a cross test that "flakes across
hosts" while its Linux twin is solid should be checked for unstaged
parameters before anything else.

## Resource-exhaustion debugging with monitor components

Before attaching a debugger to a "random" crash or slowdown, check whether
the assembly already telemeters the answer -- the framework monitors
(`src/components/`):

- `stack_monitor` -- per-task stack + secondary-stack usage %; a task near
  100% explains "random" memory corruption (stack overflow into adjacent
  data).
- `queue_monitor` -- per-component queue high-water marks; saturated queues
  explain dropped commands/telemetry long before a crash.
- `cpu_monitor` -- per-task CPU over configurable windows; a task pinned at
  its window explains missed deadlines and watchdog trips.
- Counters beat logs for rate problems: saturated drop counters (a U8
  pinned at 255) plus a pinned FIFO high-water mark diagnose overflow even
  when the visible symptom is downstream ("bad CRC", parse errors) --
  check occupancy/drop counters before debugging the parser.

Add the monitors to debug builds of an assembly even if the flight
configuration omits them; they are passive and cheap.
