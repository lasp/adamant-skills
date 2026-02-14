# Adamant Build Commands Reference

Complete examples for all redo build targets. All commands assume the Adamant environment is activated (`source env/activate`).

## Docker Execution Pattern

```bash
# Interactive
bash docker/adamant_env.sh login
source env/activate
cd src/components/my_component && redo all

# Non-interactive (from host)
docker exec <container> bash -c "source /home/user/<project>/env/activate 2>/dev/null && cd /home/user/<project> && redo <target>"
```

## Building

```bash
# Build everything in current directory
redo all

# Parallel build (gprbuild uses -j0 internally)
redo -j

# Build a specific object
redo build/obj/Linux/my_package.o

# Build an executable
redo build/bin/Linux/main.elf

# Build for a different target
TARGET=Pico redo build/bin/Pico/main.elf

# Generate implementation stubs (copy from build/template/)
redo templates

# List what can be built here
redo what

# Show available cross-compilation targets
redo targets
```

## Testing

```bash
# Run unit test (from a test/ directory containing test.adb)
cd src/components/my_component/test
redo test

# Run ALL tests recursively from project root
cd src
redo test_all

# Test output is in build/log/test.elf.log
```

## Coverage

```bash
# IMPORTANT: Must clean first! Coverage needs fresh build with gcov flags
cd src/components/my_component/test
redo clean
redo coverage

# Recursive coverage
cd src
redo coverage_all

# Coverage report in build/coverage/
```

## Style Checking

```bash
# Check style in current directory (Ada + Python + YAML + spelling)
redo style

# Recursive style check
redo style_all

# Style log output
cat build/style/style.log

# Manual style-checked compilation
CHECK_STYLE=True redo build/obj/Linux/my_package.o
```

## SPARK Prove

```bash
# Prove current directory (needs all.prove.yaml)
redo prove

# With higher proof level
PROVE_SWITCHES="--level=4" redo prove

# all.prove.yaml example:
# level: 2
# mode: "gold"
```

## Static Analysis

```bash
# GNAT SAS analysis
redo analyze

# Recursive
redo analyze_all
```

## Diagrams & Documentation

```bash
# Generate SVG architecture diagram
redo build/svg/my_assembly.assembly.svg

# Generate HTML documentation
redo build/html/my_component.component.html

# Other formats
redo build/eps/my_record.record.eps
redo build/png/my_record.record.png
redo build/pdf/my_assembly.assembly.pdf
```

## Cleaning

```bash
# Clean current directory
redo clean

# Clean everything recursively
redo clean_all

# Clear model cache (fixes stale generation issues)
redo clear_cache
```

## Code Formatting

```bash
# Auto-format Ada source code
redo pretty
```

## Common Workflows

### New Component Development
```bash
cd src/components/my_component
touch .all_path                    # Add to build path
# Create my_component.component.yaml
redo templates                     # Generate stubs in build/template/
cp build/template/*.ad? .         # Copy stubs to source dir
# Edit implementation files
redo all                           # Build
cd test && redo test               # Test
```

### Full Verification Pass
```bash
cd src
redo clean_all
redo style_all    # Style + lint + spell check
redo test_all     # All unit tests
redo coverage_all # Coverage analysis
```

### Cross-Compilation Build
```bash
export TARGET=Pico
cd assembly/main
redo build/bin/Pico/main.elf
```

### Debugging Build Issues
```bash
redo what              # What targets are available?
redo targets           # What cross-compilation targets exist?
redo clear_cache       # Fix stale model cache
redo clean && redo all # Clean rebuild
```
