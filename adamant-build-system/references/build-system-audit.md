<!-- validated: adamant@80c1f5f 2026-02-18 (main) -->
# Adamant Build System Audit Report

**Date:** 2026-02-14  
**Auditor:** Claude (Subagent)  
**Scope:** Comparison of documented build system capabilities vs actual implementation

## Executive Summary

The audit found the adamant-build-system skill documentation to be **largely accurate** but **incomplete**. Several undocumented targets exist, and some minor discrepancies were identified in target availability and generator listings.

## Findings

### ✅ Correctly Documented Targets

The following targets are accurately documented and implemented:

| Target | Type | Documentation Status |
|--------|------|---------------------|
| `all` | Universal | ✅ Accurate |
| `templates` | Universal | ✅ Accurate |
| `publish` | Universal | ✅ Accurate |
| `targets` | Universal | ✅ Accurate |
| `test` | Conditional | ✅ Accurate |
| `test_all` | Universal | ✅ Accurate |
| `coverage` | Conditional | ✅ Accurate |
| `coverage_all` | Universal | ✅ Accurate |
| `style` | Universal | ✅ Accurate |
| `style_all` | Universal | ✅ Accurate |
| `prove` | Universal | ✅ Accurate |
| `analyze` | Universal | ✅ Accurate |
| `analyze_all` | Universal | ✅ Accurate |
| `pretty` | Universal | ✅ Accurate |
| `clean` | Universal | ✅ Accurate |
| `clean_all` | Universal | ✅ Accurate |
| `clear_cache` | Universal | ✅ Accurate |
| `what` | Universal | ✅ Accurate |
| `what_predefined` | Universal | ✅ Accurate |

### ❌ Missing/Undocumented Targets

The following targets exist in the actual build system but are **NOT documented** in the skill:

| Target | Type | Purpose | Found In |
|--------|------|---------|----------|
| `path` | Universal | Display build path information | `default.do` |
| `print_path` | Universal | Print current build path | `default.do` |
| `recursive` | Universal | Recursive build operation | `default.do` |
| `run` | Conditional | Execute main.elf binaries | `default.do` |
| `yaml_sloc` | Universal | YAML source lines of code counter | `default.do` |

### 🔧 Cross-Compilation Targets Analysis

**Documented targets vs actual implementation:**

| Documented Target | Actual Implementation | Status |
|------------------|----------------------|--------|
| `Linux` (default) | ✅ `Linux` class (alias for Linux_Debug) | ✅ Accurate |
| `Linux_Debug` | ✅ `Linux_Debug` class | ✅ Accurate |
| `Linux_Test` | ✅ `Linux_Test` class | ✅ Accurate |
| `Linux_Coverage` | ✅ `Linux_Coverage` class | ✅ Accurate |
| `Linux_Prove` | ✅ `Linux_Prove` class | ✅ Accurate |
| `Linux_Analyze` | ✅ `Linux_Analyze` class | ✅ Accurate |
| ARM bare board | ✅ `arm_bare_board` base class | ⚠️ Documented as generic, actually base class |
| RISC-V bare board | ✅ `riscv_bare_board` base class | ⚠️ Documented as generic, actually base class |

**Issue:** The documentation describes ARM and RISC-V as specific targets, but they are actually base classes. Real projects would need to inherit from these to create specific targets (e.g., `Pico`, `STM32`, etc.).

### 📦 Code Generators Analysis

**Documented generators vs actual implementation:**

| Documented Generator | Actual File | Status |
|---------------------|-------------|--------|
| `assembly.py` | ✅ `gen/generators/assembly.py` | ✅ Present |
| `component.py` | ✅ `gen/generators/component.py` | ✅ Present |
| `packed_types.py` | ✅ `gen/generators/packed_types.py` | ✅ Present |
| `basic.py` | ✅ `gen/generators/basic.py` | ✅ Present |
| `configuration.py` | ✅ `gen/generators/configuration.py` | ✅ Present |
| `ided_suite.py` | ✅ `gen/generators/ided_suite.py` | ✅ Present |
| `tests.py` | ✅ `gen/generators/tests.py` | ✅ Present |
| `memory_map.py` | ✅ `gen/generators/memory_map.py` | ✅ Present |

**All documented generators are present and correctly listed.**

### 🏗️ Build File Extensions

**Documented vs actual .do file coverage:**

| Extension | .do File | Purpose | Status |
|-----------|----------|---------|--------|
| `.elf` | ✅ `default.elf.do` | Executable binaries | ✅ Documented |
| `.o` | ✅ `default.o.do` | Object files | ❓ Not explicitly documented |
| `.gpr` | ✅ `default.gpr.do` | GPR project files | ❓ Not explicitly documented |
| `.svg` | ✅ `default.svg.do` | SVG diagrams | ✅ Documented |
| `.eps` | ✅ `default.eps.do` | EPS diagrams | ✅ Documented |
| `.png` | ✅ `default.png.do` | PNG diagrams | ✅ Documented |
| `.pdf` | ✅ `default.pdf.do` | PDF documents | ✅ Documented |

### ⚠️ Minor Issues Found

1. **Target Availability Clarity:**
   - The skill lists `test` and `coverage` as universal targets, but they are actually **conditional** (only available in test directories with `test.elf`)
   - The skill correctly notes this limitation but could be clearer in the main target tables

2. **Missing Path Information:**
   - The skill doesn't document the `path` and `print_path` targets which are useful for debugging build path issues
   - The `recursive` target is not documented

3. **Base Class vs Concrete Targets:**
   - ARM and RISC-V targets are documented as concrete targets but are actually base classes
   - Real projects create concrete targets like `Pico` that inherit from `arm_bare_board`

## Recommendations

### 🔧 Documentation Updates Needed

1. **Add missing targets to SKILL.md:**
   ```markdown
   ### Debug & Utility Targets
   ```bash
   redo path            # Show build path information
   redo print_path      # Print current build path  
   redo recursive       # Recursive build operation
   redo run             # Execute main.elf (from assembly main dirs)
   redo yaml_sloc       # Count YAML source lines of code
   ```

2. **Clarify target availability:**
   ```markdown
   ### Conditional Targets (only available in specific directories)
   ```bash
   redo test            # Run unit test (from test/ dir with test.elf)
   redo coverage        # Coverage analysis (from test/ dir)
   redo run             # Execute main.elf (from assembly main dirs)
   ```

3. **Clarify cross-compilation target inheritance:**
   ```markdown
   ### Cross-Compilation Target Architecture
   | Base Class | Purpose | Example Concrete Targets |
   |-----------|---------|--------------------------|
   | `arm_bare_board` | ARM Cortex-M base | Pico, STM32F4, etc. |
   | `riscv_bare_board` | RISC-V base | Custom RISC-V targets |
   ```

### 📊 Build System Health

Overall, the adamant build system implementation is **well-structured** and **comprehensive**:

- ✅ Robust routing system in `default.do`
- ✅ Clean separation of rules in `redo/rules/`
- ✅ Modular target system in `redo/targets/`
- ✅ Complete generator coverage
- ✅ Good documentation coverage (~85% accurate)

The build system is significantly more capable than documented, with several useful utility targets available but not advertised to users.

## Conclusion

The adamant-build-system skill documentation is **substantially accurate** but **incomplete**. The missing targets (`path`, `print_path`, `recursive`, `run`, `yaml_sloc`) would be valuable additions to the documentation, especially for troubleshooting and advanced usage scenarios.

**Recommendation: UPDATE the skill documentation** to include the missing targets and clarify target availability patterns.