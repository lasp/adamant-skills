#!/usr/bin/env python3
"""
Adamant Ada Style Pre-Checker

A lightweight style checker for Adamant projects that catches common violations
before the expensive `redo style` round-trip. Runs without Docker dependencies.

Based on rules from the adamant-style skill.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set


class StyleViolation:
    def __init__(self, filename: str, line_num: int, level: str, description: str):
        self.filename = filename
        self.line_num = line_num
        self.level = level  # "ERROR" or "WARN"
        self.description = description
    
    def __str__(self):
        return f"{self.filename}:{self.line_num}: [{self.level}] {self.description}"


class AdaStyleChecker:
    def __init__(self, check_yaml: bool = False, auto_fix: bool = False):
        self.check_yaml = check_yaml
        self.auto_fix = auto_fix
        self.violations = []
        self.files_fixed = []
    
    def add_violation(self, filename: str, line_num: int, level: str, description: str):
        """Add a style violation."""
        self.violations.append(StyleViolation(filename, line_num, level, description))
    
    def find_ada_files(self, paths: List[str]) -> List[str]:
        """Find all .adb/.ads (and optionally .yaml) files in given paths."""
        files = []
        extensions = ['.adb', '.ads']
        if self.check_yaml:
            extensions.extend(['.yaml', '.yml'])
        
        for path_str in paths:
            path = Path(path_str)
            if path.is_file():
                if path.suffix.lower() in extensions:
                    files.append(str(path))
            elif path.is_dir():
                for ext in extensions:
                    files.extend([str(p) for p in path.rglob(f"*{ext}")])
        
        return files
    
    def check_file(self, filename: str):
        """Check a single file for style violations."""
        try:
            with open(filename, 'rb') as f:
                raw_content = f.read()
            
            # Check for DOS line endings (rule 4)
            has_dos_endings = b'\r\n' in raw_content
            if has_dos_endings:
                self.add_violation(filename, 1, "ERROR", "DOS line endings (CR+LF) found, use Unix LF only")
            
            # Decode content for text analysis
            try:
                content = raw_content.decode('utf-8')
            except UnicodeDecodeError:
                self.add_violation(filename, 1, "ERROR", "File is not valid UTF-8")
                return
            
            lines = content.splitlines()
            fixed_lines = []
            file_modified = False
            
            # Check YAML document start (rule 11)
            if filename.endswith(('.yaml', '.yml')) and lines:
                if not lines[0].strip().startswith('---'):
                    self.add_violation(filename, 1, "ERROR", "Missing '---' document start in YAML file")
            
            consecutive_blank_lines = 0
            
            for i, line in enumerate(lines, 1):
                original_line = line
                stripped_line = line.strip()  # Define stripped_line here
                
                # Rule 1: Trailing whitespace
                if line.rstrip() != line:
                    self.add_violation(filename, i, "ERROR", "Trailing whitespace")
                    if self.auto_fix:
                        line = line.rstrip()
                        file_modified = True
                
                # Rule 2: Multiple consecutive blank lines
                if stripped_line == '':
                    consecutive_blank_lines += 1
                    if consecutive_blank_lines > 1:
                        self.add_violation(filename, i, "ERROR", "Multiple consecutive blank lines")
                        if self.auto_fix:
                            # Skip this line during fix
                            continue
                else:
                    consecutive_blank_lines = 0
                
                # Rule 3: Tab characters
                if '\t' in line:
                    self.add_violation(filename, i, "ERROR", "Tab character found, use spaces only")
                    if self.auto_fix:
                        line = line.replace('\t', '   ')  # Replace with 3 spaces
                        file_modified = True
                
                # Skip other checks for non-Ada files
                if not filename.endswith(('.adb', '.ads')):
                    fixed_lines.append(line)
                    continue
                
                # Rule 5: Wrong indentation (not multiple of 3 spaces)
                # Only check base indentation, not continuation line alignment
                # Skip this check for now as it's generating too many false positives
                # The main issue is distinguishing base indentation from continuation alignment
                # which is complex in Ada
                pass
                
                # Rule 6: (others => vs [others => for arrays
                # This is tricky - we need to distinguish arrays from records
                if '(others =>' in line:
                    # Simple heuristic: if it looks like an array context, warn
                    # This is not perfect but catches common cases
                    stripped = line.strip()
                    if (stripped.startswith('(others =>') or 
                        'Buffer := (others =>' in line or
                        'Array' in line or
                        ':= (others =>' in line):
                        self.add_violation(filename, i, "WARN", "Consider '[others =>' instead of '(others =>' for arrays (Ada 2022)")
                
                # Rule 7: Boolean or/and without else/then
                # Skip comment lines for this check too
                if not stripped_line.startswith('--'):
                    # Only check within if/elsif conditions, and be more careful about detection
                    if re.search(r'\b(if|elsif)\b.*\bor\b(?!\s+else\b)', line):
                        # Skip if it looks like bitwise operation or other non-boolean context
                        if not re.search(r'(16#|[0-9]+\s*or\s*[0-9#]+)', line):
                            self.add_violation(filename, i, "ERROR", "Use 'or else' instead of 'or' in boolean conditions")
                    elif re.search(r'\b(if|elsif)\b.*\band\b(?!\s+then\b)', line):
                        # Skip if it looks like bitwise operation 
                        if not re.search(r'(16#|[0-9]+\s*and\s*[0-9#]+)', line):
                            self.add_violation(filename, i, "ERROR", "Use 'and then' instead of 'and' in boolean conditions")
                
                # Rule 8: Missing space before ( in type conversions
                # Pattern: Identifier( without space
                if re.search(r'\b[A-Za-z_][A-Za-z0-9_]*\(', line):
                    # Exclude function/procedure definitions and pragma statements
                    if not re.search(r'\b(function|procedure|pragma)\b', line):
                        self.add_violation(filename, i, "ERROR", "Missing space before '(' in type conversion")
                
                # Rule 9: return ( - unnecessary parentheses (but not record aggregates)
                if re.search(r'\breturn\s*\(', line) and not re.search(r'\breturn\s*\(.*=>', line):
                    self.add_violation(filename, i, "ERROR", "Unnecessary parentheses around return value")
                
                # Rule 10: Statements on same line as then/else
                # Skip this check if the line is entirely a comment
                stripped_line = line.strip()
                if stripped_line.startswith('--'):
                    pass  # Skip comment lines entirely
                else:
                    # Check for control flow 'then' (not "and then")
                    if re.search(r'\bthen\b', line) and 'and then' not in line and 'or then' not in line:
                        if not stripped_line.endswith('then'):
                            # Check if there's actual code after 'then' (not just comments)
                            then_match = re.search(r'\bthen\b', line)
                            if then_match:
                                after_then = line[then_match.end():].strip()
                                if after_then and not after_then.startswith('--'):
                                    self.add_violation(filename, i, "ERROR", "Statement found on same line as 'then'")
                    
                    # Check for control flow 'else' (not "or else")
                    if re.search(r'\belse\b', line) and 'or else' not in line:
                        if not stripped_line.endswith('else'):
                            # Check if there's actual code after 'else' (not just comments)
                            else_match = re.search(r'\belse\b', line)
                            if else_match:
                                after_else = line[else_match.end():].strip()
                                if after_else and not after_else.startswith('--'):
                                    self.add_violation(filename, i, "ERROR", "Statement found on same line as 'else'")
                
                fixed_lines.append(line)
            
            # Write back fixed content if auto-fix is enabled and file was modified
            if self.auto_fix and file_modified:
                # Handle DOS line ending fix
                line_ending = '\n'
                fixed_content = line_ending.join(fixed_lines) + line_ending
                
                with open(filename, 'w', encoding='utf-8', newline='') as f:
                    f.write(fixed_content)
                
                self.files_fixed.append(filename)
        
        except Exception as e:
            self.add_violation(filename, 1, "ERROR", f"Failed to process file: {e}")
    
    def check_files(self, filenames: List[str]):
        """Check multiple files for style violations."""
        for filename in filenames:
            self.check_file(filename)
    
    def has_errors(self) -> bool:
        """Return True if any ERROR level violations found."""
        return any(v.level == "ERROR" for v in self.violations)
    
    def print_results(self):
        """Print all violations to stdout."""
        for violation in self.violations:
            print(violation)
        
        if self.auto_fix and self.files_fixed:
            print(f"\nFixed whitespace issues in {len(self.files_fixed)} files:", file=sys.stderr)
            for filename in self.files_fixed:
                print(f"  {filename}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Adamant Ada Style Pre-Checker - catches common style violations before 'redo style'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s src/                          # Check all .adb/.ads files in src/
  %(prog)s file1.adb file2.ads          # Check specific files
  %(prog)s --yaml src/                   # Also check .yaml files
  %(prog)s --fix src/                    # Auto-fix whitespace issues
  
Exit codes:
  0: No errors found (warnings are OK)
  1: Errors found that need manual fixing
        """
    )
    
    parser.add_argument('paths', nargs='+', 
                       help='Files or directories to check')
    parser.add_argument('--yaml', action='store_true',
                       help='Also check .yaml/.yml files')
    parser.add_argument('--fix', action='store_true',
                       help='Auto-fix whitespace issues (trailing spaces, tabs, DOS endings, multiple blank lines)')
    
    args = parser.parse_args()
    
    # Validate paths exist
    for path in args.paths:
        if not os.path.exists(path):
            print(f"Error: Path '{path}' does not exist", file=sys.stderr)
            return 1
    
    # Create checker and find files
    checker = AdaStyleChecker(check_yaml=args.yaml, auto_fix=args.fix)
    files = checker.find_ada_files(args.paths)
    
    if not files:
        extensions = "*.adb, *.ads" + (", *.yaml, *.yml" if args.yaml else "")
        print(f"No files found matching: {extensions}", file=sys.stderr)
        return 0
    
    # Check files and print results
    checker.check_files(files)
    checker.print_results()
    
    # Exit with error code if errors found
    return 1 if checker.has_errors() else 0


if __name__ == '__main__':
    sys.exit(main())