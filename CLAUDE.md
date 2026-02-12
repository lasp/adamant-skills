# Adamant Agent Skills

Skills for AI-assisted development with the [Adamant](https://github.com/lasp/adamant) embedded software framework. Built through iterative practice against a real GNAT/GNATprove toolchain -- every pattern has been validated by compilation.

## Quick Start

**Start here:** Read `adamant-skill-selector/SKILL.md` first. It routes your task to the right 1-2 skills and avoids loading all ~2200 lines into context.

## Skill Inventory

| Skill | Lines | Purpose |
|-------|-------|---------|
| `adamant-skill-selector` | ~90 | **Read first.** Maps tasks to skills. |
| `adamant-component-dev` | ~520 | Building components: YAML models, generated API, implementation patterns |
| `adamant-assembly-dev` | ~260 | Wiring assemblies: scheduling, routing, ID assignment, COSMOS integration |
| `adamant-build-system` | ~280 | Redo commands, code gen pipeline, build paths, cross-compilation |
| `adamant-framework-components` | ~280 | Catalog of all 55 built-in components by subsystem |
| `adamant-type-system` | ~400 | YAML type definitions, format codes, generated Ada type hierarchy |
| `adamant-testing` | ~470 | Test harness generation, History API, async dispatch, error injection |
| `adamant-algorithm-wrapping` | ~300 | Complete pipeline for wrapping C++ algorithms: C shims, Ada bindings, packed records, component implementation, unit tests |

## Key Principles

- **Every line is framework-specific.** Generic Ada/SPARK knowledge is excluded.
- **Patterns validated by compiler.** Built 5+ components from skills alone; errors fed back as corrections.
- **Naming collision rules are critical.** Data product names, parameter type packages, and enum references all have Ada visibility traps documented in the skills.
- **Skills cross-reference each other.** component-dev links to testing and type-system. assembly-dev links to framework-components. The selector skill manages this.

## Non-Adamant Skills

| Skill | Purpose |
|-------|---------|
| `high-assurance-design` | Design-by-invariant, non-goals, proof strategies (from hadlink project) |
| `knowledge-acquisition` | Systematic codebase study and skill creation methodology |

## Contributing

Skills are maintained via practice-driven refinement: build a real artifact, hit compiler errors, update the skill, commit. See `knowledge-acquisition/references/practice-driven-refinement.md`.
