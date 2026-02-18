# Adamant Framework Internals Skill - Validation Round 6

**Date**: February 18, 2026  
**Validator**: Subagent performing final pass/fail validation  
**Target Score**: 8+ on accuracy, completeness, and usability

---

## EXERCISE 1: Full Cold-Start Debugging Walkthrough

**Scenario**: Component `product_packetizer` has 3 instances in an assembly. Instance `Hk_Packet_Packetizer` generates packets from the wrong data source -- it has packets that should belong to `Science_Packet_Packetizer`.

### Step-by-Step Debug Process (Using ONLY the skill)

#### Step 1: Identify the Generator/Model Responsible
**Skill guidance**: *"Check `build/src/` for the generated file. Trace to the generator... from database.generator_database import generator_database..."*

Rating: **CLEAR** - The skill provides specific Python code to identify which generator/model produced the wrong output.

Would I be stuck? **NO** - The exact import and method call are provided.

#### Step 2: Find the Python Model Class
**Skill guidance**: *"Look for `gen/models/` in the component's source tree. If absent, the generic framework model applies."*

Rating: **CLEAR** - Specific directory path and fallback behavior documented.

Would I be stuck? **NO** - Clear directory structure guidance.

#### Step 3: Examine the Model Override
**Skill guidance**: From override-examples.md, I can see `product_packetizer_packets.py` uses Pattern 1: Init Parameter Type Resolution.

Rating: **CLEAR** - The exact override pattern is documented with code example.

Would I be stuck? **NO** - The reference shows the exact override implementation.

#### Step 4: Analyze the Type Resolution Logic
**Skill guidance**: *"Extract model name from discriminant (init parameter)"* - the example shows the component uses `self.component.discriminant.get_parameter_value("Packet_List")` to resolve packet types.

Rating: **SUFFICIENT** - I can see the resolution is based on init parameters, but would need to examine the specific parameter values for each instance.

Would I be stuck? **PARTIALLY** - I'd know WHERE to look (discriminant parameter) but would need to inspect the actual YAML values.

#### Step 5: Check for Instance Identity Bug
**Skill guidance**: *"Always use `is` (Python identity operator) when comparing component model objects... Rule: Always use `is`... Never use `==` for instance comparisons"*

Rating: **CLEAR** - The most common bug pattern is explicitly documented with examples.

Would I be stuck? **NO** - The skill clearly explains the `==` vs `is` pitfall.

#### Step 6: Verify Instance-Specific Resolution
**Skill guidance**: *"Wrong component's data for one assembly instance → Connection trace finds first match, not correct match"* and *"`set_assembly` receives stale/incorrect assembly → Subassembly merge order"*

Rating: **SUFFICIENT** - The skill identifies this as a known symptom pattern, but the product_packetizer example doesn't use connection tracing.

Would I be stuck? **NO** - I'd understand this is likely an init parameter resolution issue specific to each instance.

#### Step 7: Debug the Init Parameter Values
**Skill guidance**: *"For type resolution bugs: Verify the model name/path being looked up, check `model_types` filter"*

Rating: **SUFFICIENT** - General guidance provided, but would need to examine actual discriminant values per instance.

Would I be stuck? **PARTIALLY** - I'd know to check init parameters but would need external knowledge of how to inspect them.

#### Step 8: Add Debug Prints
**Skill guidance**: Provides exact debug print pattern: `print(f"[DEBUG] instance={self.component.instance_name}", file=sys.stderr)`

Rating: **CLEAR** - Specific debug code provided.

Would I be stuck? **NO** - Exact code to add is shown.

#### Step 9: Clear Cache and Test Fix
**Skill guidance**: *"Always `redo clear_cache` before testing any model fix. Stale pickled objects mask code changes."*

Rating: **CLEAR** - Explicit warning about cache invalidation with specific command.

Would I be stuck? **NO** - Clear command and reasoning provided.

**Overall Exercise 1 Assessment**: I can follow the complete debugging workflow using only the skill, though some steps require inspecting actual data values not covered in the skill scope.

---

## EXERCISE 2: Verify Round 5 Critical Gaps Are Fixed

### a) Can you now find the generator database import path and usage?

**Answer**: **FIXED**

**Evidence**: The skill now includes:
```python
from database.generator_database import generator_database
with generator_database() as db:
    module_name, module_file, class_name, input_file = db.get_generator("path/to/output.ads")
```

The import path, context manager usage, and return values are explicitly documented.

### b) Can you now distinguish cache bugs from model bugs?

**Answer**: **FIXED**

**Evidence**: The skill now includes explicit guidance:
*"Cache vs. model debugging: If the problem disappears after `redo clear_cache` + rebuild, investigate missing `redo_ifchange` calls in custom overrides or stale dependency declarations in `get_dependencies()`. If it persists, the bug is in model code."*

This provides a clear decision tree to distinguish cache from model issues.

---

## EXERCISE 3: Final Scoring

### Accuracy: 9/10
- Technical content is accurate throughout
- Code examples are correct and executable
- Symptom-to-cause mappings are precise
- Only minor gap: some debugging steps require external data inspection

### Completeness (for stated scope): 8/10
- Covers model lifecycle comprehensively
- Code generation debugging workflow is complete
- Assembly loading sequence is detailed
- Override patterns are well-documented
- Missing: More details on connector resolution debugging

### Usability (cold-start agent can follow): 8/10
- Step-by-step debugging workflow is clear
- Code examples are copy-pasteable
- Common pitfalls are explicitly called out
- Debug print patterns provided
- Reference examples are well-annotated

### Reference Quality: 9/10
- Override examples cover all major patterns
- Real code examples with annotation
- Common mistakes section is valuable
- Cross-references between skill and examples work well

---

## EXERCISE 4: Remaining Improvements

**Assessment**: Diminishing returns reached.

The skill now scores 8+ on all criteria. Potential improvements would only provide marginal value:

1. **Connector resolution debugging details** - Would move completeness from 8 to 8.5, but this is narrow scope
2. **Init parameter inspection methods** - Would help usability slightly, but is assembly-specific knowledge
3. **More debug print examples** - Would be helpful but not transformative

All major gaps from previous rounds have been addressed. The skill provides comprehensive coverage of its stated scope (model lifecycle and code generation debugging) with clear, actionable guidance that a cold-start agent can follow.

**FINAL VERDICT**: **PASS** - Skill meets 8+ threshold on all criteria.