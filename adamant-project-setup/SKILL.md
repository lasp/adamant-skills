---
name: adamant-project-setup
description: Setting up new Adamant projects with build system, environment, configuration, and Docker integration. Use when starting a new Adamant project from scratch, configuring Docker environments, or setting up build roots and activation scripts.
---

# Adamant Project Setup

Create standalone Adamant projects outside the framework source tree.

## Project Structure

```
<project_dir>/
├── .gitignore
├── alire.toml                          # Alire crate manifest (Ada dependencies)
├── config/
│   └── project.configuration.yaml      # Adamant sizing & project-specific config
├── docker/
│   ├── docker-compose.yml              # Container definition
│   └── adamant_env.sh                  # start/stop/login helper
├── env/
│   ├── activate                        # Environment setup (sources adamant/env/activate)
│   └── requirements*.txt               # Python deps (auto-installed by adamant/env/activate)
├── src/
│   ├── types/                          # Custom type definitions
│   │   └── .all_path                   # Empty marker file (REQUIRED)
│   ├── components/
│   │   └── <component_name>/
│   │       └── .all_path               # Empty marker in EACH component dir
│   └── assembly/
│       ├── .all_path
│       └── main/
│           └── .all_path
├── clean.do                            # All .do files copied from adamant root
├── default.do
└── default.*.do                        # (elf, gpr, o, svg, pdf, png, eps, uf2)
```

## Setup Steps

### 1. Copy build scripts
```bash
cp $ADAMANT_DIR/*.do <project_dir>/
```
Must be copies, not symlinks (redo resolves rules relative to working directory).

### 2. Create env/activate

Template -- replace `PROJECT` with your project's short name (e.g., `DEMO`, `EXAMPLE`):

```bash
#!/bin/bash

# Resolve project directory from this script's location
if test -z "$PROJECT_DIR"
then
  export PROJECT_DIR=`readlink -f "${BASH_SOURCE[0]}" | xargs dirname | xargs dirname`
fi

# Adamant must be a sibling directory
if test -z "$ADAMANT_DIR"
then
  export ADAMANT_DIR=`readlink -f "$PROJECT_DIR/../adamant"`
fi

# Guard: only activate once per shell session
if test -n "$PROJECT_ENVIRONMENT_SET"
then
  return
fi

echo "Setting up Project environment."

# Point to this project's configuration YAML
export ADAMANT_CONFIGURATION_YAML=$PROJECT_DIR/config/project.configuration.yaml

# Activate the Adamant environment WITH this project as an extra build root.
# The argument ($PROJECT_DIR) is CRITICAL -- it adds the project to BUILD_ROOTS
# so the build system can discover custom types, components, and assemblies.
. $ADAMANT_DIR/env/activate $PROJECT_DIR

# Mark environment as set
export PROJECT_ENVIRONMENT_SET="yes"

echo "Done."
```

#### How BUILD_ROOTS Works

`BUILD_ROOTS` is a colon-separated list of directories the build system searches for source files. When you run `. $ADAMANT_DIR/env/activate $PROJECT_DIR`, adamant's activate script:

1. Prepends `$ADAMANT_DIR` to the paths if not already present
2. Iterates each path, running `alr build`, setting up GPR paths, and activating Python configs
3. Exports `BUILD_ROOTS="$ADAMANT_DIR:$PROJECT_DIR"`

The build system uses BUILD_ROOTS to locate `.all_path` markers and discover all source directories. **Without your project in BUILD_ROOTS, custom types/components are invisible.**

You can also set BUILD_ROOTS manually before sourcing activate to override -- the script respects pre-set values.

#### Key Environment Variables Set by activate

| Variable | Purpose |
|---|---|
| `ADAMANT_DIR` | Path to adamant framework |
| `ADAMANT_CONFIGURATION_YAML` | Path to project config YAML |
| `ADAMANT_PYTHON_ENV` | Python venv location (default: `~/.py_env`) |
| `BUILD_ROOTS` | Colon-separated source search paths |
| `GPR_PROJECT_PATH` | GNAT project file search path (set by alire) |
| `SCHEMAPATH` | `$ADAMANT_DIR/gen/schemas` |
| `TEMPLATEPATH` | `$ADAMANT_DIR/gen/templates` |

### 3. Create Configuration YAML

File: `config/project.configuration.yaml`

```yaml
---
# Description (informational only)
description: Configuration for My Project.

#############################################################################
# REQUIRED -- Adamant Core Type Sizing
#############################################################################

# Size of serialization buffer in data product type (bytes).
# Must fit the largest data product in your system.
data_product_buffer_size: 32

# Size of serialization buffer in command type (bytes).
# Must fit the largest command argument payload.
command_buffer_size: 128

# Size of serialization buffer in event type (bytes).
# Must fit the largest event parameter payload.
event_buffer_size: 32

# Size of serialization buffer in parameter type (bytes).
parameter_buffer_size: 32

# Size of serialization buffer in fault type (bytes).
fault_buffer_size: 8

# CCSDS space packet buffer size (bytes).
# Default 512 is fine if not using CCSDS. ISS LRT max = 1274.
ccsds_packet_buffer_size: 512

# Packet buffer size (bytes). Typically ccsds_packet_buffer_size minus
# header/checksum overhead (~28 bytes for ISS LRT).
packet_buffer_size: 480

#############################################################################
# REQUIRED -- Other Core Settings
#############################################################################

# Stack margin (bytes). Used by Stack Monitor for "usable" stack calculation.
# Must be > stack used before first Cycle call, and < smallest task stack.
# Only affects bareboard runtimes; Linux uses hardcoded 12KB.
stack_margin: 1000

# Command registration delay (microseconds). Sleep between successive
# command registrations to avoid overflowing Command Router's queue.
# Increase if registrations are dropped at init.
command_registration_delay: 250

#############################################################################
# OPTIONAL -- Project-Specific Variables
#############################################################################
# Define custom key-value pairs usable in YAML (Jinja: {{ var_name }})
# or Ada (with Configuration package).
#
# project_specific_variable: 17
# project_specific_string: "hello"
```

**Sizing guidance:**
- `Storage_Error` at runtime → increase the relevant buffer size
- Start with conservative defaults (above), increase as needed
- Buffer sizes affect RAM usage on embedded targets -- don't over-allocate

### 4. Docker Setup

Each project gets its own `docker/` directory. **Do NOT put docker-compose overrides in the adamant repo.**

#### docker-compose.yml Template

```yaml
name: <project_name>
services:
    <project_name>:
        image: ghcr.io/lasp/adamant:0.1
        container_name: <project_name>_container
        volumes:
            - type: bind
              source: ../../adamant          # Relative to docker/ dir
              target: /home/user/adamant
            - type: bind
              source: ../../<project_name>   # Relative to docker/ dir
              target: /home/user/<project_name>
        network_mode: host
        extra_hosts:
            - host.docker.internal:host-gateway
        command: sleep infinity
```

**Notes:**
- Volume sources are relative to docker-compose.yml location (inside `docker/`)
- `sleep infinity` keeps container running for `exec` commands
- `network_mode: host` gives container access to host networking
- Container naming convention: `<project_name>_container`

#### adamant_env.sh Commands

The helper script auto-detects project name from its parent directory.

| Command | Action |
|---|---|
| `bash docker/adamant_env.sh start` | Pull image (if missing) + start container + run first-time env/activate |
| `bash docker/adamant_env.sh stop` | Stop container |
| `bash docker/adamant_env.sh login` | Interactive bash shell as `user` |
| `bash docker/adamant_env.sh pull` | Pull latest image |
| `bash docker/adamant_env.sh remove` | Remove container, network, volumes (destructive!) |

**First `start`** runs env/activate inside the container, which:
1. Creates Python venv (`~/.py_env`) and installs requirements
2. Builds alire dependencies (`alr build --release`)
3. Sets BUILD_ROOTS, GPR paths, etc.
4. Touches `~/.initialized` so subsequent starts skip this

The script supports both `docker` and `podman` -- falls back to podman if docker is not found.

#### Interactive Development (Preferred)

**Always prefer `adamant_env.sh login` for interactive work.** The login shell sources the correct activate script via `.bashrc`, ensuring BUILD_ROOTS is set correctly with both adamant and the project.

```bash
cd <project_dir>
bash docker/adamant_env.sh login
# Inside container:
cd src/components && redo style_all
cd src/components && redo test_all
```

#### Non-interactive command execution

For scripted/automated commands, use `docker exec` with the project's activate:

```bash
docker exec -u user <project_name>_container bash -c \
  "source /home/user/<project_name>/env/activate 2>/dev/null && \
  cd /home/user/<project_name> && redo <target>"
```

**Why login is preferred over raw `docker exec`:**
- The base adamant image's `.bashrc` sources `adamant/env/activate`, which sets `ADAMANT_ENVIRONMENT_SET`. This guard variable prevents the project's activate from re-running adamant's activate with the project as an extra build root.
- A custom Dockerfile that overrides `.bashrc` to source the project's activate instead solves this. The `adamant_env.sh start` script also handles first-time activation.
- Raw `docker exec` with `source project/env/activate` works IF the environment hasn't been previously activated in that shell session. But login shells may have already sourced `.bashrc`.
- **Bottom line:** `adamant_env.sh login` handles all edge cases. Use it.

### 5. Set Up .gitignore

Recommended patterns:

```gitignore
# Build artifacts (redo creates build/ dirs everywhere)
**/build/

# Python
*.pyc
__pycache__/

# Alire (managed, not checked in)
/alire/
/config/
!/config/README.md
!/config/<project>.configuration.yaml

# OS/editor
.DS_Store
*.swp
*.tmp
~$*

# Vagrant/misc
.vagrant
.Trash*
.pyenv/
.tmp
.unison*
GNAT-*
```

The critical pattern is `**/build/` -- redo creates `build/` subdirectories in every source directory during compilation.

### 6. Directory Rules: .all_path and env.py

#### .all_path Marker Files

Every directory containing source files that should be discoverable by the build system **must** have an empty `.all_path` file. This includes:
- `src/types/`
- `src/components/<each_component>/`
- `src/assembly/`
- `src/assembly/main/`

The build system scans BUILD_ROOTS for `.all_path` files to build its source file index. Missing `.all_path` = invisible directory.

#### env.py (Python Path Configuration)

Each build root can have Python configuration activated via `set_python_path.sh`. Python files in later paths override earlier ones -- adamant is always first, so project-specific Python always wins.

## Build Commands

```bash
redo all                                    # Build everything from any dir
redo build/bin/Linux/main.elf              # Native ELF (from main/ dir)
redo run                                    # Build and run (from main/ dir)
redo clean                                  # Remove all build artifacts
redo style_all                              # Check style across project
```

## First Build Walkthrough

When you run `redo all` or build a target for the first time:

1. **Environment check** -- redo verifies BUILD_ROOTS and ADAMANT_CONFIGURATION_YAML are set
2. **Code generation** -- YAML model files are processed through Jinja templates to generate Ada specs/bodies. Configuration values from your YAML are substituted (e.g., `{{ data_product_buffer_size }}` → `32`)
3. **Dependency resolution** -- redo scans `.all_path` directories across all BUILD_ROOTS, building a dependency graph
4. **Compilation** -- gprbuild compiles Ada sources using GPR files from `redo/targets/gpr/`
5. **Linking** -- produces ELF binary in `build/bin/<Target>/`

**Expected first-build behavior:**
- Takes several minutes (compiling all of adamant framework)
- Creates `build/` directories throughout the source tree
- Downloads/builds alire dependencies if not cached
- Subsequent builds are incremental (much faster)

## Multi-Project Setups

For projects that depend on both adamant and another shared library project:

```bash
# In env/activate, pass multiple paths separated by colons:
. $ADAMANT_DIR/env/activate $PROJECT_DIR:$OTHER_PROJECT_DIR
```

Or set BUILD_ROOTS manually before sourcing:
```bash
export BUILD_ROOTS="$ADAMANT_DIR:$SHARED_LIB_DIR:$PROJECT_DIR"
. $ADAMANT_DIR/env/activate
```

The order matters: later paths override earlier ones for Python configuration. Adamant is always prepended if not already present.

## Common Setup Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `Storage_Error` at runtime | Buffer too small for data being serialized | Increase relevant `*_buffer_size` in configuration YAML |
| Custom types not found during build | Project dir not in BUILD_ROOTS | Ensure env/activate passes `$PROJECT_DIR` to adamant's activate |
| `file not found` for generated Ada | Missing `.all_path` in source directory | Add empty `.all_path` file |
| Duplicate file name error | Two files with same name across BUILD_ROOTS | Rename -- file names must be unique across entire build path |
| Permission denied in container | SELinux bind mount permissions | adamant/env/activate auto-fixes with `chown`; or run `sudo chown -R user:user /home/user/<project>` |
| Command registrations dropped at init | `command_registration_delay` too low or Command Router queue too small | Increase `command_registration_delay` or enlarge queue |
| `alr` build fails on first start | Network issue or alire cache corrupted | `rm -rf alire/` and re-run `alr build` |
| HTML gen fails on framework components | Known issue with some components | Build ELF directly (`redo build/bin/Linux/main.elf`) to bypass |
| `.do` files not working | Symlinked instead of copied | Replace symlinks with copies: `cp $ADAMANT_DIR/*.do .` |

## Docker Image Details

`ghcr.io/lasp/adamant:0.1` (~1.3GB) includes:
- GNAT native compiler (via alire)
- GNAT ARM ELF cross-compiler (via alire)
- GNATprove (SPARK formal verification)
- redo build system
- Python 3 + pip
- Standard development tools

## Related Skills

- **Build system**: [adamant-build-system](../adamant-build-system/SKILL.md)
- **Component dev**: [adamant-component-dev](../adamant-component-dev/SKILL.md)
- **Style**: [adamant-style](../adamant-style/SKILL.md) -- run `redo style_all` to validate entire project
