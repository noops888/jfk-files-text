#!/usr/bin/env python3
"""
verify_integrity.py  –  Level‑1 existence/size check (default)
                       Level‑2 --deep body check that ignores
                       • all heading lines starting with '#'
                       • any blank lines immediately after headings
                       • any blank lines at EOF
"""

from pathlib import Path
import sys, argparse, difflib

cli = argparse.ArgumentParser()
cli.add_argument("--orig", default="./releases")
cli.add_argument("--conv", default="./releases_with_metadata")
cli.add_argument("--deep", action="store_true")
cli.add_argument("--maxdiff", type=int, default=3)
args = cli.parse_args()

ROOT = Path(args.orig).resolve()
CONV = Path(args.conv).resolve()
if not ROOT.is_dir() or not CONV.is_dir():
    sys.exit("[ERROR] --orig or --conv folder not found")

def strip_head(lines):
    i = 0
    while i < len(lines) and lines[i].lstrip().startswith("#"):
        i += 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    return lines[i:]

def strip_yaml(lines):
    if not lines or lines[0] != "---":
        return lines
    try:
        j = lines.index("---", 1)
    except ValueError:
        return lines
    j += 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    return lines[j:]

def drop_trailing_blanks(lines):
    while lines and lines[-1].strip() == "":
        lines.pop()
    return lines

missing, smaller, mismatch = [], [], []
for orig in ROOT.rglob("*.md"):
    rel  = orig.relative_to(ROOT)
    conv = CONV / rel
    if not conv.exists():
        missing.append(rel); continue
    if conv.stat().st_size <= orig.stat().st_size:
        smaller.append(rel)
    if args.deep:
        o = drop_trailing_blanks(strip_head(orig.read_text().splitlines()))
        c = drop_trailing_blanks(strip_yaml(conv.read_text().splitlines()))
        if o != c:
            mismatch.append(rel)
            if len(mismatch) <= args.maxdiff:
                print("\n".join(list(difflib.unified_diff(o, c, lineterm=""))[:40]),
                      "\n... diff truncated ...\n")

print(f"\nChecked {len(list(ROOT.rglob('*.md'))):,} files")
print(f"• Missing            : {len(missing)}")
print(f"• Converted smaller  : {len(smaller)}")
if args.deep:
    print(f"• Content mismatches : {len(mismatch)}")
    fail = missing or smaller or mismatch
else:
    fail = missing or smaller

if fail:
    sys.exit(1)
print("✅  Verification passed.")