#!/usr/bin/env bash
# adamant_env.sh - Cached environment wrapper for docker exec commands
#
# First call: runs full activation, caches env to /tmp/adamant_env_cache_<container>.sh
# Subsequent calls: sources cached env (instant, no Alire/dep checks)
#
# Usage:
#   # Run a command with cached env:
#   adamant_env.sh <container> <project_activate_path> <command...>
#
#   # Example:
#   adamant_env.sh adamant_skill_validation_container \
#     /home/user/adamant_skill_validation/env/activate \
#     python3 /tmp/adamant_validate.py src/components/foo
#
#   # Force re-cache (rebuild cached env snapshot):
#   adamant_env.sh --refresh <container> <project_activate_path> <command...>
#
#   Note: The upstream adamant_env.sh (docker/adamant_env.sh) uses
#   "adamant_env.sh refresh" as a subcommand. This agent wrapper uses
#   "--refresh" as a flag before the container/path/command arguments.

set -e

REFRESH=false
if [ "$1" = "--refresh" ]; then
    REFRESH=true
    shift
fi

CONTAINER="$1"
ACTIVATE_PATH="$2"
shift 2

CACHE_FILE="/tmp/adamant_env_cache.sh"

# Check if cache exists inside container
if [ "$REFRESH" = "false" ]; then
    CACHE_EXISTS=$(docker exec "$CONTAINER" bash -c "[ -f $CACHE_FILE ] && echo yes || echo no" 2>/dev/null)
else
    CACHE_EXISTS="no"
fi

if [ "$CACHE_EXISTS" = "no" ]; then
    # First run: activate and capture env
    docker exec "$CONTAINER" bash -c "
        # Capture env before
        env | sort > /tmp/_env_before.txt

        # Run activation (suppress output)
        source $ACTIVATE_PATH >/dev/null 2>&1

        # Capture env after and generate cache script
        echo '#!/usr/bin/env bash' > $CACHE_FILE
        echo '# Auto-generated Adamant environment cache' >> $CACHE_FILE
        echo '# Regenerate with: adamant_env.sh --refresh' >> $CACHE_FILE

        # Export all new/changed env vars
        while IFS='=' read -r key value; do
            # Skip volatile/irrelevant vars
            case \"\$key\" in
                OLDPWD|_|SHLVL|PS1|BASH_*|FUNCNAME|LINENO|PIPESTATUS) continue ;;
            esac
            # Check if this var is new or changed
            old_val=\$(grep \"^\${key}=\" /tmp/_env_before.txt | cut -d= -f2-)
            if [ \"\$old_val\" != \"\$value\" ]; then
                echo \"export \$key=\\\"\$value\\\"\" >> $CACHE_FILE
            fi
        done < <(env | sort)

        rm -f /tmp/_env_before.txt
    " 2>/dev/null
fi

# Run command with cached env
docker exec "$CONTAINER" bash -c "source $CACHE_FILE && cd \$(grep PROJECT_DIR $CACHE_FILE | cut -d'\"' -f2) && $*"
