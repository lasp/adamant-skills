#!/bin/bash
# Template: env/activate for an Adamant project
# Replace PROJECT_NAME with your project's short name (uppercase for env var, lowercase for dir)

if test -z "$PROJECT_NAME_DIR"
then
  export PROJECT_NAME_DIR=`readlink -f "${BASH_SOURCE[0]}" | xargs dirname | xargs dirname`
fi

if test -z "$ADAMANT_DIR"
then
  export ADAMANT_DIR=`readlink -f "$PROJECT_NAME_DIR/../adamant"`
fi

if test -n "$PROJECT_NAME_ENVIRONMENT_SET"
then
  return
fi

echo "Setting up project_name environment."

export ADAMANT_CONFIGURATION_YAML=$PROJECT_NAME_DIR/config/project_name.configuration.yaml

# Pass project dir to adamant activate to add it to BUILD_ROOTS
. $ADAMANT_DIR/env/activate $PROJECT_NAME_DIR

export PROJECT_NAME_ENVIRONMENT_SET="yes"

echo "Done."
