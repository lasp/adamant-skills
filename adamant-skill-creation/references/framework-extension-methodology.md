# Framework Extension Methodology

Pattern for creating skills that go BEYOND existing framework templates and examples, into territory that can be inferred from the framework's architecture and design but has no direct precedent. This is the next level after framework-verified skill correction.

## When to Use

- All existing patterns are well-covered by skills (campaigns converge quickly)
- The framework's architecture implies capabilities that no existing component demonstrates
- You need to test whether agents can REASON about Adamant, not just follow recipes
- Skill quality has plateaued at current complexity and needs escalation beyond existing examples

## The Distinction

**Framework-verified correction** (T4 base pattern): The framework already does X; the skill may describe X wrong; study source to get X right.

**Framework extension** (this pattern): The framework's architecture SUPPORTS X but no existing component does X; design X from architectural principles and verify it compiles.

Examples:
- No existing generator uses `component_submodel` (all 15 use `assembly_submodel`), but the base class exists and the discovery mechanism supports it
- No existing generator creates a 3-stage dependency chain, but `depends_on()` and redo's dependency graph fully support it
- No existing generator cross-references multiple YAML model types, but the model loading API allows loading any model by name at any time

## The Loop

```
Architecture Study -> Capability Inference -> Minimal Proof -> Skill Encoding -> Campaign-Test -> Difficulty Ratchet
```

### 1. Architecture Study

Go deeper than individual component generators. Study the BASE CLASSES and INFRASTRUCTURE:

**Priority targets:**
- Base classes (`generator_base`, `basic_generator`, `assembly_submodel`, `component_submodel`, `base`)
- Discovery/registration (`meta.py`, `create.py`, `_setup.py`, `set_python_path.sh`)
- Dependency resolution (`redo_ifchange`, `depends_on()`, generator database)
- Model loading (`model_loader.py`, `try_load_model_by_name`, model cache)
- Schema validation (`pykwalify`, `base.__init__` validation chain)

**What to look for:**
- Abstract methods that have more capability than any concrete implementation exercises
- Base class features that no subclass uses
- Configuration parameters with valid but untested values
- API entry points that no generator calls
- Combinations of existing patterns that have never been composed together

### 2. Capability Inference

Form claims about what the framework CAN do, even though nothing currently does it.

**Format:**
```
C<N>: <capability claim>
Basis: <architectural evidence -- base class, API, infrastructure>
Novel: <why no existing implementation exercises this>
Risk: <what might prevent it from working despite architectural support>
Test: <minimal proof-of-concept to verify>
```

**Critical distinction from hypotheses:** Hypotheses test claims about existing behavior. Capability inferences test claims about POSSIBLE behavior that has never been exercised.

**Risk categories:**
- **Low risk**: Base class method exists, just not called by any subclass (e.g., `component_submodel.load_component()`)
- **Medium risk**: Infrastructure supports it but may have untested edge cases (e.g., 3-stage dependency chain through redo)
- **High risk**: Requires combining subsystems that have never interacted (e.g., cross-model type resolution)

### 3. Minimal Proof

Build the simplest possible artifact that exercises the inferred capability. Unlike framework-verified correction (which tests existing behavior), this tests NOVEL behavior.

**Rules:**
- Absolute minimum complexity to prove the capability works
- Build inside Docker, verify it compiles and (if applicable) runs
- If it fails, determine: was the inference wrong, or is there a fixable gap?
- Document the working proof PRECISELY -- it becomes the seed for the skill

**Failure modes (productive):**
- **Missing infrastructure**: The base class exists but a required hook isn't called by the build system -> file a finding, work around it
- **Circular dependency**: The dependency chain creates a cycle redo can't resolve -> document the constraint, design around it
- **Model loading order**: The framework loads models in an order that prevents cross-referencing -> document the ordering constraints

### 4. Skill Encoding

Write skill content that teaches the PATTERN, not the specific proof. The skill should enable agents to build novel generators without having seen the exact proof artifact.

**Encoding rules:**
- Describe the architectural principle, not just the recipe
- Show the proof-of-concept as an example but explain WHY it works
- Document constraints discovered during minimal proof
- Include explicit "this has no framework precedent" markers so agents know they're in novel territory
- Cross-reference the base class source locations

### 5. Campaign-Test

Cold-start agents with loose prompts that require the novel pattern. These prompts should describe a GOAL, not a method.

**Prompt design for extension scenarios:**
- Bad: "Create a generator that inherits from component_submodel" (tells the method)
- Good: "Create a generator for a component that validates its state machine YAML against the component's own connectors" (describes the goal, agent must infer the method)
- Best: "This component needs a config YAML that is validated at build time against the component's connector topology. Design the generator infrastructure." (maximally open)

**Expect more iterations.** Extension scenarios SHOULD fail more than verification scenarios. 3-5 iterations with fixes is normal. 10+ iterations means the skill needs more architectural context.

### 6. Difficulty Ratchet

After convergence, the ratchet can only go UP. Never return to a lower difficulty.

**Ratchet dimensions:**
- **Composition**: Combine two extension patterns that have each converged independently
- **Scale**: More components, more connections, more generated files
- **Constraint**: Add requirements that force non-obvious design choices
- **Novelty**: Move further from any existing example

**The goal**: Find the boundary where the skill fails. That boundary is where the framework's implicit capability becomes ambiguous or requires architectural knowledge not in the skill.

## Difficulty Spectrum

```
Level 1: Follow existing template (copy-paste with modifications)
Level 2: Combine two existing patterns (both well-documented)
Level 3: Apply existing pattern in a new context (documented mechanism, novel use)
Level 4: Infer pattern from architecture (no existing example)
Level 5: Compose multiple inferred patterns (no existing example, novel interaction)
Level 6: Design at architectural level (agent proposes the generator infrastructure)
```

Levels 1-3 are framework-verified correction territory.
Levels 4-6 are framework extension territory.

## Integration with Campaign Methodology

- **Campaign plan**: Extension scenarios go AFTER verification scenarios converge
- **Decision points**: Extension DPs test REASONING, not just output. Did the agent choose the right base class? Did it identify the dependency ordering?
- **Failure interpretation**: More generous on first iterations (novel territory). But 5+ iterations on the same failure = skill gap, not difficulty
- **Convergence**: Same rule (5 consecutive clean) but expect higher iteration counts before convergence
- **MEMORY.md**: Log both the pattern AND the architectural insight that made it possible

## Anti-Patterns

- **Testing extensions before verifications converge**: Verify existing patterns first, then extend
- **Leaking the method into the prompt**: The whole point is testing whether the skill teaches enough for the agent to INFER the method
- **Conflating agent confusion with framework limitation**: If the framework supports it but the agent can't figure it out, the skill is incomplete
- **Encoding only the proof, not the principle**: Future scenarios will differ from the proof; the skill needs the generalization
- **Skipping the minimal proof**: Inferring a capability without building it leads to skills that describe impossible patterns
