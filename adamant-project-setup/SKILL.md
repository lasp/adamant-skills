---
name: adamant-project-setup
description: Setting up new Adamant projects with build system, environment, configuration, and Docker integration
---

# Adamant Project Setup

Create standalone Adamant projects outside the framework source tree.

## Project Structure

```
<project_dir>/
├── .gitignore                          # **/build/
├── config/
│   └── project.configuration.yaml
├── env/
│   └── activate                        # Environment setup
├── src/
│   ├── types/                          # Custom type definitions (.all_path each)
│   ├── components/                     # Components (.all_path each)
│   └── assembly/                       # Assemblies (.all_path + main/)
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
```bash
#!/bin/bash
if test -z "$PROJECT_DIR"; then
  export PROJECT_DIR=`readlink -f "${BASH_SOURCE[0]}" | xargs dirname | xargs dirname`
fi
if test -z "$ADAMANT_DIR"; then
  export ADAMANT_DIR=`readlink -f "$PROJECT_DIR/../adamant"`
fi
if test -n "$PROJECT_ENVIRONMENT_SET"; then return; fi
export ADAMANT_CONFIGURATION_YAML=$PROJECT_DIR/config/project.configuration.yaml
. $ADAMANT_DIR/env/activate $PROJECT_DIR    # Adds project to BUILD_ROOTS
export PROJECT_ENVIRONMENT_SET="yes"
```

**CRITICAL**: `. $ADAMANT_DIR/env/activate $PROJECT_DIR` — the project dir argument adds it to BUILD_ROOTS. Without it, custom types are invisible.

### 3. Create configuration
```yaml
# config/project.configuration.yaml
data_product_buffer_size: 32
command_buffer_size: 128
event_buffer_size: 32
parameter_buffer_size: 32
fault_buffer_size: 8
packet_buffer_size: 480
ccsds_packet_buffer_size: 512
stack_margin: 1000
command_registration_delay: 250
```

Increase buffer sizes if you get `Storage_Error` at runtime.

### 4. Docker compose override (if using containers)
```yaml
services:
  adamant:
    volumes:
      - /path/to/<project_dir>:/home/user/<project_name>
```

Build from host:
```bash
docker compose -f $ADAMANT_DIR/docker/docker-compose.yml \
  -f $ADAMANT_DIR/docker/docker-compose.override.yml \
  exec adamant bash -c "source /home/user/<project_name>/env/activate && cd /home/user/<project_name> && redo <target>"
```

## Build Commands

```bash
redo all                                    # Build from any dir
redo build/bin/Linux/main.elf              # Native build (from main/)
redo run                                    # Build and run (from main/)
```

## Common Pitfalls

- Every source directory needs empty `.all_path` (types, components, assembly, main)
- Never manually create `build/` directories
- Using adamant's activate WITHOUT the project dir arg = custom types invisible
- HTML gen may fail on some framework components — build ELF directly to bypass
