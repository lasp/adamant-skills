#!/bin/bash
# Generate skill selector routing summary from skill frontmatter
# Usage: ./generate_selector.sh [skills_dir]
# Outputs markdown table of all Adamant skills with descriptions

SKILLS_DIR="${1:-$(dirname "$0")/../../}"
echo "# Auto-Generated Skill Index"
echo ""
echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""
echo "| Skill | Description | Lines | Refs |"
echo "|-------|-------------|-------|------|"

for skill_dir in "$SKILLS_DIR"/adamant-*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    skill_md="$skill_dir/SKILL.md"
    [ -f "$skill_md" ] || continue

    # Extract description from frontmatter
    desc=$(sed -n '/^---$/,/^---$/{ /^description:/{ s/^description: *//; p; q; } }' "$skill_md")
    lines=$(wc -l < "$skill_md" | tr -d ' ')

    # Count reference lines
    ref_lines=0
    if [ -d "$skill_dir/references" ]; then
        ref_lines=$(find "$skill_dir/references" -name '*.md' -o -name '*.yaml' | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
        [ -z "$ref_lines" ] && ref_lines=0
    fi

    echo "| \`$skill_name\` | $desc | $lines | $ref_lines |"
done

echo ""
echo "## Non-Adamant Skills"
echo ""
for skill_dir in "$SKILLS_DIR"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    [[ "$skill_name" == adamant-* ]] && continue
    [ "$skill_name" = "scripts" ] && continue
    skill_md="$skill_dir/SKILL.md"
    [ -f "$skill_md" ] || continue
    desc=$(sed -n '/^---$/,/^---$/{ /^description:/{ s/^description: *//; p; q; } }' "$skill_md")
    echo "- **$skill_name**: $desc"
done
