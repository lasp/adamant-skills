---
name: adamant-project-setup
description: Setting up new Adamant projects with build system, environment, configuration, and Docker integration
---

# Adamant Project Setup

Create standalone Adamant projects outside the framework source tree. Projects need: build scripts, environment activation, configuration, and proper directory structure.

## Project Structure

```
project_name/
├── .gitignore                          # Exclude **/build/
├── README.md
├── config/
│   └── project.configuration.yaml      # Buffer sizes, stack margin
├── env/
│   └── activate                        # Shell script to set up environment
├── src/
│   ├── types/                          # Custom type definitions
│   │   └── my_types/
│   │       ├── .all_path
│   │       └── my_type.record.yaml
│   ├── components/                     # Component implementations
│   │   └── my_component/
│   │       ├── .all_path
│   │       └── ...
│   └── assembly/                       # System assemblies
│       └── my_assembly/
│           ├── .all_path
│           ├── my_assembly.assembly.yaml
│           └── main/
│               ├── .all_path
│               └── main.adb
├── clean.do                            # Copied from adamant/
├── default.do                          # Copied from adamant/
├── default.elf.do                      # Copied from adamant/
├── default.eps.do                      # Copied from adamant/
├── default.gpr.do                      # Copied from adamant/
├── default.o.do                        # Copied from adamant/
├── default.pdf.do                      # Copied from adamant/
├── default.png.do                      # Copied from adamant/
├── default.svg.do                      # Copied from adamant/
└── default.uf2.do                      # Copied from adamant/
```

## Build Scripts (.do files)

Copy ALL `.do` files from the adamant root directory into your project root. These are the redo build rules that drive code generation and compilation. They are NOT symlinks -- they must be actual copies because redo resolves rules relative to the working directory.

```bash
cp $ADAMANT_DIR/*.do $PROJECT_DIR/
```

## Environment Script (env/activate)

The activate script sets up the build environment by sourcing adamant's own activate with your project as an extra build root. This ensures BUILD_ROOTS contains both adamant AND your project, making custom types in src/types/ discoverable.

```bash
#!/bin/bash

if test -z "$PROJECT_DIR"
then
  export PROJECT_DIR=`readlink -f "${BASH_SOURCE[0]}" | xargs dirname | xargs dirname`
fi

if test -z "$ADAMANT_DIR"
then
  export ADAMANT_DIR=`readlink -f "$PROJECT_DIR/../adamant"`
fi

# Only set the environment once:
if test -n "$PROJECT_ENVIRONMENT_SET"
then
  return
fi

echo "Setting up project environment."

# Set the path to our configuration file:
export ADAMANT_CONFIGURATION_YAML=$PROJECT_DIR/config/project.configuration.yaml

# Activate the Adamant environment with this project as extra build root:
. $ADAMANT_DIR/env/activate $PROJECT_DIR

# Signify the environment is set up:
export PROJECT_ENVIRONMENT_SET="yes"

echo "Done."
```

**CRITICAL**: The key line is `. $ADAMANT_DIR/env/activate $PROJECT_DIR` -- passing the project directory as an argument adds it to BUILD_ROOTS. Without this, custom types in src/types/ are invisible to the build system.

## Configuration (config/project.configuration.yaml)

```yaml
---
description: Configuration for the project.
# Buffer sizes -- must be large enough for your largest types
data_product_buffer_size: 32
command_buffer_size: 128
event_buffer_size: 32
parameter_buffer_size: 32
fault_buffer_size: 8
ccsds_packet_buffer_size: 512
packet_buffer_size: 480
# Stack safety margin (bytes subtracted from stack size for overflow detection)
stack_margin: 1000
# Delay (ms) after command registration during Set_Up
command_registration_delay: 250
```

Increase buffer sizes if you get runtime storage errors. `command_buffer_size` must fit your largest command argument type.

## Docker Integration

If using the Adamant Docker environment, add a compose override to mount your project:

```yaml
# docker-compose.override.yml (alongside adamant's docker-compose.yml)
services:
  adamant:
    volumes:
      - /path/to/project:/home/user/project_name
```

Build commands from host:
```bash
# Using project's own activate (recommended):
docker compose -f $ADAMANT_DIR/docker/docker-compose.yml \
  -f $ADAMANT_DIR/docker/docker-compose.override.yml \
  exec adamant bash -c "source /home/user/project_name/env/activate && cd /home/user/project_name && redo <target>"

# Using adamant's activate with extra arg (alternative):
docker compose -f $ADAMANT_DIR/docker/docker-compose.yml \
  -f $ADAMANT_DIR/docker/docker-compose.override.yml \
  exec adamant bash -c "source /home/user/adamant/env/activate /home/user/project_name && cd /home/user/project_name && redo <target>"
```

Both approaches work. The project's own activate script just wraps the second form.

## .gitignore

```
**/build/
```

All build artifacts go in `build/` subdirectories at each level. A single glob catches everything.

## Build Commands

```bash
# From component directory:
redo all                                    # Generate + compile component

# From assembly directory:
redo all                                    # Generate + compile assembly (may fail on HTML gen)

# From assembly/main directory:
redo build/bin/Linux/main.elf              # Build native executable
redo run                                    # Build and run

# From project root:
redo src/components/my_comp/build/obj/Linux/my_comp.o   # Build specific object
```

## Initialization Checklist

1. Create project directory structure (src/types/, src/components/, src/assembly/)
2. Copy .do files from adamant root
3. Create env/activate with proper ADAMANT_DIR path
4. Create config/project.configuration.yaml
5. Create .gitignore with `**/build/`
6. Add Docker compose override if using containers
7. Initialize git repo
8. Create custom types (if any) with .all_path files
9. Create components with .all_path files
10. Create assembly with .all_path and main/main.adb

## Common Pitfalls

- **Missing .all_path**: Every directory with source files needs an empty `.all_path` file for the build system to discover it. This includes types, components, assemblies, and main directories.
- **Wrong activate script**: Using `source adamant/env/activate` without the extra project argument means BUILD_ROOTS only has adamant -- your custom types won't be found.
- **Build directory pollution**: Never manually create `build/` directories in component/assembly dirs. The build system creates them. If they exist with stale content, `redo` may skip regeneration.
- **Buffer too small**: If you get `Storage_Error` at runtime, increase the relevant buffer size in configuration.yaml.
- **HTML generation errors**: Some framework component HTML generators may have template bugs. Building the ELF directly (`redo build/bin/Linux/main.elf` from main/) bypasses HTML generation.
