# Adamant Framework Internals Skill Validation - Round 1

## Executive Summary

I validated the `adamant-framework-internals` skill by reading the actual code and comparing it to the skill's descriptions. The skill is generally accurate but has several gaps, inaccuracies, and areas where guidance could be clearer. The most critical finding is that the skill correctly identifies the `==` vs `is` pitfall but could provide better debugging guidance.

## Exercise 1: Navigate base.py

### What the skill told me to do:
- Check if `__eq__` compares by filename as described
- Verify `__new__` and `__init__` behavior matches the description  
- Confirm "no in-memory cache" claim and understand caching mechanics
- Look for other debugging-relevant methods

### What I actually found in the code:

#### `__eq__` Implementation - **MATCHES SKILL**
```python
def __eq__(self, other):
    return self and other and self.full_filename == other.full_filename
```
✅ **Accurate**: The skill correctly describes that `__eq__` compares by `full_filename`, not Python object identity.

#### `__new__` and `__init__` Behavior - **MATCHES BUT INCOMPLETE**
✅ **Accurate**: `__new__` does check cache via `load_from_cache` and returns cached objects with `from_cache=True`
✅ **Accurate**: `__init__` skips loading when `from_cache=True`

**Gap**: The skill doesn't explain the `base_meta` metaclass that filters `ignore_cache` parameter between `__new__` and `__init__`. This is important for understanding the parameter flow.

#### Caching Mechanism - **SKILL DESCRIPTION ACCURATE**
✅ **Confirmed**: There is no in-memory Python object cache. Every `load_from_cache` call goes through SQLite → `pickle.loads` → fresh Python object.

Two cache validation paths confirmed:
1. **This-session path**: Checks `ADAMANT_SESSION_ID` match, still calls `pickle.loads`
2. **Cross-session path**: Validates timestamps, still calls `pickle.loads`

**Minor gap**: The skill mentions "no in-memory cache" but doesn't explain that the session ID check only skips timestamp validation, not object deserialization.

#### Other Methods That Matter for Debugging - **SKILL MISSES THESE**
**Major gaps identified**:
- `get_dependencies()`: Returns model dependency list, critical for understanding why cache invalidation occurs
- `save_to_cache()`: Shows when models get stored, helpful for debugging cache issues
- `__hash__()`: Uses `full_filename`, related to the `__eq__` pitfall
- `__repr__()` and `__str__()`: Show basename in debugging output
- `warning()` and `warn()`: Model-specific error reporting

## Exercise 2: Navigate assembly.py

### What the skill told me to do:
- Verify the 6-step assembly load sequence matches actual code
- Check if any steps are omitted
- Understand how `set_component_instance_data` works
- Verify subassembly merging description

### What I actually found in the code:

#### 6-Step Assembly Load Sequence - **MOSTLY ACCURATE WITH GAPS**

The skill lists:
1. `subassembly.load()` - ✅ **Found in `super(assembly, self).load()`**
2. Named subassemblies loaded recursively - ✅ **Found in subassembly loading loop**  
3. `connection.connect(self.components)` for unconnected - ✅ **Found in connection loop**
4. `set_component_instance_data` - ✅ **Found, called per component instance**
5. `component.set_assembly(assembly)` per instance - ✅ **Found in component loop**
6. `final()` - ✅ **Found at end of load**

**Critical gap**: The skill omits **ID generation and assignment** which happens between steps 5 and 6 in `_generate_component_ids()`. This is a major omission since it's crucial for understanding when IDs become available.

**Additional gap**: The skill doesn't mention the **complex type loading** step (`_load_complex_types()`) which also happens after step 5.

#### Steps the skill omits:
- **ID generation phase**: `_generate_component_ids()` - assigns IDs to all events, commands, data products, etc.
- **Complex type resolution**: `_load_complex_types()` - builds dependency-ordered type dictionaries
- **Task priority assignment**: Happens during component categorization
- **Connector validation**: Warns about unattached connectors

#### How `set_component_instance_data` actually works - **SKILL LACKS DETAIL**
✅ **Accurate**: The skill correctly states it "mutates each component model in-place"

**Major gaps in skill**:
- Doesn't explain the line number assignment: `self.lineno = component_instance_data.lc.line + 1`
- Doesn't cover generic type resolution for connectors
- Doesn't explain queue size calculation logic
- Missing details about task instance data handling
- No mention of unconstrained connector array resolution

#### Subassembly Merging - **ACCURATE BUT INCOMPLETE**
✅ **Confirmed**: "Subassembly components are merged into `assembly.components` by **direct reference** (not copied)"

**Gap**: The skill doesn't explain the validation logic that checks for duplicate component names across subassemblies, which is important for debugging assembly composition errors.

## Exercise 3: Navigate component.py

### What the skill told me to do:
- Understand how `set_assembly()` propagates to submodels
- Learn what `component_submodel` base class provides
- See how `load_component()` works

### What I actually found in the code:

#### How `set_assembly()` propagates to submodels - **MATCHES SKILL**
✅ **Confirmed**: In `component.set_assembly()`:
```python
for m in self.submodels.values():
    m.set_assembly(assembly)
```

**Gap**: The skill doesn't mention that `self.instance_assembly_model = assembly` is also set, which might be useful for debugging.

#### What `component_submodel` base class provides - **SKILL ACCURATE BUT INCOMPLETE**
✅ **Found**: `load_component()`, `set_component()`, `set_assembly()` base implementations
✅ **Found**: `submodel_name()` method for attachment naming

**Missing from skill**:
- `final()` method for post-processing hooks
- `load()` initialization that sets `self.component = None` and `self.assembly = None`

#### How `load_component()` works - **MATCHES SKILL PATTERN**
✅ **Confirmed**: Similar to `assembly_submodel.load_assembly()` - loads component, updates self with fresher version from `component.submodels`, saves to cache.

**Gap**: The skill doesn't explain the model name parsing logic using `redo_arg.split_model_filename()`.

## Exercise 4: Navigate a real custom override

### What the skill told me to do:
- Check if "Custom set_assembly() Pattern" matches real implementation
- Compare what it actually does vs what skill says
- Verify if it uses `is` or `==` (the bugfix)

### What I actually found in the code:

#### Does the pattern match? - **PARTIALLY**
✅ **Pattern structure matches**: The code follows the general pattern of inheriting from `packets`, overriding `set_assembly()`, calling `super()` at the end.

**Critical deviation**: The real code does **NOT** follow the skill's example of using `is` for instance comparison!

#### What does it actually do vs what the skill says? - **MAJOR GAP**
**What the skill shows**: Using `is` for component comparison:
```python
if conn.to_component is self.component  # Skill example uses 'is'
```

**What the real code does**: The `parameters_packets.py` doesn't traverse connections at all! Instead it:
1. Looks up parameter table configuration from `self.component.init` 
2. Finds the parameter table package name
3. Resolves the autogenerated record model path
4. Replaces packet entities with new packet objects using the resolved type

**Critical finding**: This code doesn't exhibit the `==` vs `is` bug the skill is designed to help debug! It's solving a different problem (dynamic type resolution).

#### Does it use `is` or `==`? - **NEITHER**
❌ **The code doesn't do component comparisons at all**. It directly accesses `self.component` and iterates through assembly components by value, not by comparison.

The only comparison is string-based:
```python
if comp.name == "Parameters":  # String comparison, not object comparison
```

**This is a major gap**: The skill's primary example doesn't demonstrate the bug pattern it's teaching about!

## Exercise 5: Navigate model_cache_database.py

### What the skill told me to do:
- Verify session ID mechanism accuracy
- Check cache invalidation logic
- Look for surprising behavior

### What I actually found in the code:

#### Session ID mechanism - **SKILL ACCURATE**
✅ **Confirmed**: Session ID is stored with `environ["ADAMANT_SESSION_ID"]` in `store_model()`
✅ **Confirmed**: `mark_cached_model_up_to_date_for_session()` updates session ID to current session
✅ **Confirmed**: Cache lookup checks session ID match for this-session path

#### Cache invalidation logic - **MATCHES SKILL DESCRIPTION**
✅ **Confirmed**: Two validation paths exist as described
✅ **Confirmed**: Timestamp validation compares `cache_time_stamp >= file_time_stamp`
✅ **Confirmed**: Dependency checking validates all model dependencies haven't changed

#### Surprising behavior found:
1. **Submodel tracking**: The code stores `submodel_paths` for dependency invalidation when new submodels are created. The skill mentions this briefly but doesn't explain its importance.

2. **Database mode switching**: `store_model()` and `mark_cached_model_up_to_date_for_session()` appear to require `READ_WRITE` mode but the methods don't explicitly manage this - it's up to the caller.

3. **Persistent vs non-persistent cache**: The code supports both modes based on `ENABLE_PERSISTENT_MODEL_CACHE` environment variable, but the skill doesn't mention this.

## Exercise 6: Attempt the debugging workflow

### Following the skill's "Investigation Workflow"

**Scenario**: Debugging `parameters_packets.py` producing wrong output for multi-instance Parameter_Store.

#### Step 1: "Identify the generator or model responsible" - **HELPFUL**
✅ The skill's guidance to trace back from `build/src/` is sound.

#### Step 2: "Find the Python model class" - **HELPFUL** 
✅ The skill correctly points to look for `gen/models/` in component source.

#### Step 3: "Read `set_assembly()` in the model class" - **HELPFUL**
✅ This is the right place to look for assembly-scope logic.

#### Step 4: "Check all `==` comparisons on component objects" - **NOT APPLICABLE**
❌ **Major gap**: As discovered in Exercise 4, the real `parameters_packets.py` doesn't do component comparisons! This step would find nothing.

#### Step 5: "Trace the connection topology" - **NOT APPLICABLE**
❌ **Gap**: Again, the real code doesn't trace connections, so this guidance doesn't apply to the actual implementation.

#### Step 6: "Add temporary debug prints" - **HELPFUL**
✅ The suggested debug pattern is useful, though the specific example wouldn't help with the real parameters_packets.py issue.

#### Step 7: "Verify with `redo clear_cache`" - **CRITICAL AND HELPFUL**
✅ This is excellent advice that would definitely help with debugging.

### Where the skill's guidance falls short:
1. **Wrong bug pattern**: The skill assumes connection-tracing bugs, but the real parameters_packets.py has type resolution bugs
2. **Missing type resolution debugging**: No guidance for debugging dynamic type loading issues
3. **No mention of `redo_ifchange` circular dependencies**: The real code has `redo.redo_ifchange(model_path)` which can cause circular dependencies

### Where the skill is helpful:
- Cache clearing advice
- General model location guidance  
- Debug printing patterns
- Understanding of assembly load sequence

## Summary of Gaps and Inaccuracies

### Critical Issues:
1. **Wrong primary example**: `parameters_packets.py` doesn't demonstrate the `==` vs `is` bug pattern the skill teaches
2. **Missing ID generation step**: The 6-step sequence omits the crucial ID assignment phase
3. **Incomplete debugging workflow**: Focused on connection-tracing bugs, not type resolution bugs

### Important Gaps:
1. **Missing base.py methods**: No mention of `get_dependencies()`, debugging helpers
2. **Incomplete assembly loading**: Missing ID generation, complex types, validation phases  
3. **Shallow debugging coverage**: Real-world debugging involves more than connection tracing

### Minor Inaccuracies:
1. **Metaclass omission**: Doesn't explain `base_meta` parameter filtering
2. **Cache mode details**: Doesn't explain persistent vs non-persistent modes
3. **Error handling gaps**: Missing details about line number tracking, error contexts

## Recommendations for Skill Improvement:

1. **Find a better primary example** that actually demonstrates the `==` vs `is` bug
2. **Add the missing ID generation step** to the assembly load sequence
3. **Expand debugging workflow** to cover type resolution and circular dependency issues
4. **Document additional base.py methods** relevant for debugging
5. **Add guidance for `redo_ifchange` circular dependency debugging**