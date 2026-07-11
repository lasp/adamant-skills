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
address violates the type's alignment (Ada RM 13.3(13/3)). x86_64 is not
a strict-alignment target, so the overlay runs fine there; on a
strict-alignment target (RISC-V and most flight CPUs) the same code
fails -- in two distinct ways, and the first one is NOT a trap:

- **Checks on (Debug/Test targets): a software check fires first.** GNAT
  emits a misaligned-address check at the overlay's elaboration -- a call
  to `__gnat_rcheck_PE_Misaligned_Address_Value` -- raising PROGRAM_ERROR
  before any hardware access happens. No machine trap occurs: mcause /
  mepc / mtval never populate and a breakpoint on the trap vector never
  fires. A test harness catches the raise, so the symptom is an
  unexplained PROGRAM_ERROR against the test with no message. Detection:
  `catch exception` (or break on the rcheck symbol) on the cross target;
  statically, `objdump -dr` the cross object and look for a relocation
  to the rcheck symbol next to the wide load -- a constant load plus a
  call immediately before the `lw` is the recognition signature. The
  same source compiled for the host shows no such call: diffing host vs
  cross disassembly of one subprogram localizes the construct fast.
- **Checks suppressed (production `-gnatp`): the hardware path.** The
  wide load executes and a strict-alignment CPU traps (RISC-V mcause=4;
  `mtval` low bits show the misalignment; disassembly around `mepc`
  shows the load and the offset arithmetic). Caveat under emulation:
  emulator cores may silently EMULATE misaligned loads instead of
  trapping -- absence of a trap in an emulator does not prove alignment.
- Mitigation: only overlay types with `'Alignment = 1` (packed byte-level
  types); assert `T'Alignment = 1` beside the overlay as executable
  documentation. Never overlay types whose fields the compiler may access
  with wide loads. Check the WHOLE address derivation, not just your
  index math: a byte-array field of a packed record inherits the record's
  internal byte offset (a buffer behind a 16-bit length field starts at
  offset 2), so an overlay can be misaligned even when the index
  arithmetic looks word-aligned -- byte-wise folds or an aligned local
  copy are the safe rewrites.

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

## Stale objects fake runtime results (no compile error)

The stale-state failure mode that costs the most is silent: objects from
a previous source state survive an incremental build and the binary you
run (or the object you inspect) is not the source you read. Nothing
errors -- a fault "disappears", appears on one run and not the next, or a
disassembly/nm signature contradicts the source. Rules:

- **A runtime reproduction that contradicts expectations is a stale-state
  suspect first, a mystery second.** A shallow `redo clean` in the test
  directory is NOT sufficient to rule this out -- reciprocal component
  build dirs keep their objects. Run `redo clean_all` (or `admt clean
  --all`) at the component, rebuild, and reproduce again before drawing
  any conclusion from a surprising pass or fail.
- **Static signatures need fresh objects too**: before trusting an
  nm/objdump recognition signature (rcheck relocations, symbol diffs),
  confirm the object postdates the source (`stat` both, or just clean and
  rebuild) -- an inherited build tree proves nothing about the code you
  are reading.
- **Checked-in test logs are historical documents**, not evidence about
  the current binary; re-run the suite yourself.
- Tool caveat: `objdump -dS`/`--line-numbers` interleaves the LIVE source
  file with the OLD compiled instructions -- on a stale object the
  listing looks self-consistent while showing code that was never
  compiled. The instruction bytes, not the interleaved source, are the
  evidence.

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
