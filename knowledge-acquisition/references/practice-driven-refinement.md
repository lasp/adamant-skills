# Practice-Driven Skill Refinement

Pattern for improving skills by building real artifacts and capturing the gaps that compilation/testing reveals.

## When to Use

After initial skill creation (via knowledge-acquisition), shift to this pattern when:
- Skills cover the major concepts but lack precise API details
- You need to verify correctness against real toolchains
- Diminishing returns from reading more source code
- Want to discover unknown unknowns (things you didn't know to look for)

## Process

### 1. Pick a Build Target

Choose something that exercises the skill gaps you want to test:
- **Simple component**: connectors, commands, events, data products (validates core patterns)
- **Component with faults**: fault connector, fault handler generation
- **Component with data deps**: request connector, Get_{Name} pattern, staleness checking
- **Component with enums**: standalone enums.yaml vs preamble enums (different Ada patterns)
- **Component with parameters**: runtime-updateable configuration
- **Assembly**: wiring, scheduling, ID assignment, view filters

### 2. Build Using Only Skills

Write all YAML and Ada files referencing only the skill documentation. Do NOT look at existing framework code unless you hit a compiler error. This is the test.

### 3. Iterate on Compiler Errors

Each error reveals a gap:
```
Error: "Thermal_Controller_Enums" not found
  -> Lesson: preamble enums live in the packed type package, not a separate _Enums package

Error: no selector "Data_Product_Fetch_T_Request"
  -> Lesson: data deps need request connector (not get), and the connector name
     depends on the type name in the YAML

Error: data product name collision with type name
  -> Lesson: data product functions are in scope alongside types; avoid name overlap

Warning: use clause has no effect
  -> Lesson: base class already `with`s certain packages; redundant `use` is harmless
```

### 4. Update Skills Immediately

After each fix, update the relevant skill with the correct pattern. Do NOT batch -- update as you go so the lesson is precise and fresh.

### 5. Save Lessons After Each Component

Update the relevant skill files with any new patterns or corrections discovered during this build.

### 6. Escalate Complexity

Progress through increasingly complex builds:
1. Passive component, no deps, no faults (baseline)
2. Passive with faults and custom packed types
3. Passive with data dependencies and enums
4. Active component with async connectors
5. Assembly wiring multiple components
6. Tests for a custom component

Each level exposes new API patterns the skills need to cover.

## What to Capture

For each compilation error or unexpected behavior:
- **What you expected** (what the skill said or implied)
- **What actually happened** (the compiler error or runtime behavior)
- **The correct pattern** (what the generated code actually does)
- **Which skill to update** (type-system, component-dev, assembly-dev, build-system)

## Anti-Patterns

- **Don't look at framework source first**: the whole point is to test the skills
- **Don't skip the skill update**: lessons must be captured immediately
- **Don't build trivial components**: each build should exercise something new
- **Don't ignore warnings**: they often reveal incorrect assumptions about Ada visibility
- **Don't batch lessons**: update skills immediately while context is fresh
