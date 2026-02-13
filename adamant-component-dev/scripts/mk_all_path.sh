#!/bin/bash
# Create .all_path marker file in given directory (or cwd)
# Usage: bash mk_all_path.sh /path/to/component/dir
dir="${1:-.}"
touch "$dir/.all_path"
