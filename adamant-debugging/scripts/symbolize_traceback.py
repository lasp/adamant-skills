#!/usr/bin/env python3
"""Resolve stack-trace addresses from an Adamant Packed_Exception_Occurrence
(or any raw traceback) to symbols, and optionally to file:line.

Two resolution modes, usable together:
  --nm  <file>   nearest-symbol-at-or-below lookup against a sorted nm dump
                 (generate at build time:  <cross>-nm -C -n main.elf > main.nm)
  --elf <file>   file:line via addr2line (requires --prefix for cross
                 binutils, e.g. --prefix riscv32-elf-)

Addresses come from argv or stdin, one or many per line, hex (0x...) or
decimal. Lines of pasted text are scanned for address-like tokens, so an
Ada "Call stack traceback locations:" line or a GDB array print pastes in
directly. Zero addresses (empty trace slots) are skipped.

The symbol file / ELF MUST come from the same build that produced the
trace -- a mismatched file resolves to plausible but wrong names.
"""

import argparse
import bisect
import re
import shutil
import subprocess
import sys

ADDR_RE = re.compile(r"0x[0-9a-fA-F]+|\b\d{6,}\b")  # hex, or >=6-digit decimal


def parse_addresses(chunks):
    """Extract candidate addresses from argv words and/or pasted text."""
    addrs = []
    for chunk in chunks:
        for tok in ADDR_RE.findall(chunk):
            value = int(tok, 16) if tok.lower().startswith("0x") else int(tok)
            if value:  # zero = empty trace slot
                addrs.append(value)
    return addrs


def load_nm(path):
    """Load an nm dump into parallel sorted lists of (address, name)."""
    addresses, names = [], []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.split(maxsplit=2)
            # nm -n lines: <hex-address> <type> <name...>
            if len(parts) == 3 and re.fullmatch(r"[0-9a-fA-F]+", parts[0]):
                addresses.append(int(parts[0], 16))
                names.append(parts[2].strip())
    if not addresses:
        sys.exit(f"error: no symbols parsed from {path}")
    # nm -n output is sorted, but do not rely on it:
    paired = sorted(zip(addresses, names))
    return [a for a, _ in paired], [n for _, n in paired]


def nearest_symbol(addr, addresses, names):
    i = bisect.bisect_right(addresses, addr) - 1
    if i < 0:
        return None, None
    return names[i], addr - addresses[i]


def addr2line(elf, prefix, addrs):
    tool = f"{prefix}addr2line"
    if shutil.which(tool) is None:
        sys.exit(f"error: {tool} not found on PATH (activate the env or fix --prefix)")
    out = subprocess.run(
        [tool, "-f", "-C", "-e", elf] + [hex(a) for a in addrs],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    # addr2line emits two lines per address: function, then file:line
    return [(out[i], out[i + 1]) for i in range(0, len(out) - 1, 2)]


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--nm", help="nm dump file (from '<cross>-nm -C -n <elf>')")
    p.add_argument("--elf", help="ELF for addr2line file:line resolution")
    p.add_argument("--prefix", default="",
                   help="binutils prefix for --elf mode (e.g. riscv32-elf-)")
    p.add_argument("addresses", nargs="*",
                   help="addresses or pasted trace text (stdin if omitted)")
    args = p.parse_args()

    if not args.nm and not args.elf:
        p.error("need --nm and/or --elf")

    chunks = args.addresses if args.addresses else sys.stdin.read().splitlines()
    addrs = parse_addresses(chunks)
    if not addrs:
        sys.exit("error: no addresses found in input")

    nm_data = load_nm(args.nm) if args.nm else None
    lines = addr2line(args.elf, args.prefix, addrs) if args.elf else None

    for i, addr in enumerate(addrs):
        parts = [f"#{i:<2} {hex(addr)}"]
        if nm_data:
            name, offset = nearest_symbol(addr, *nm_data)
            parts.append(f"{name} + {hex(offset)}" if name else "<below first symbol>")
        if lines:
            func, loc = lines[i]
            parts.append(f"{func}  [{loc}]")
        print("  ".join(parts))


if __name__ == "__main__":
    main()
