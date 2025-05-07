# fix_dates.py
import re
from pathlib import Path
import argparse

# Match any YAML key containing 'date' whose value is exactly 01/01/0000 or 00/00/00
PATTERN = re.compile(r"^(\s*\w*date\w*\s*:\s*)(['\"]?)(?:01/01/0000|00/00/00)\2\s*$")


def dry_run(root="releases"):
    matches = []
    for md in Path(root).rglob("*.md"):
        lines = md.read_text(encoding="utf-8").splitlines()
        in_fm = False
        for idx, line in enumerate(lines, start=1):
            if line.strip() == "---":
                in_fm = not in_fm
                continue
            if in_fm and PATTERN.match(line):
                matches.append((md, idx, line.strip()))
    return matches


def patch_dates(root="releases"):
    for md in Path(root).rglob("*.md"):
        text = md.read_text(encoding="utf-8").splitlines(keepends=True)
        in_fm = False
        changed = False
        for i, line in enumerate(text):
            if line.strip() == "---":
                in_fm = not in_fm
                continue
            if in_fm:
                m = PATTERN.match(line)
                if m:
                    text[i] = f"{m.group(1)}''\n"
                    changed = True
        if changed:
            md.write_text("".join(text), encoding="utf-8")
            print(f"Patched {md}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect/fix placeholder zero dates in YAML front matter.")
    parser.add_argument("--apply", action="store_true", help="Apply fixes in place; otherwise do a dry run.")
    args = parser.parse_args()

    if args.apply:
        print("Applying fixes...")
        patch_dates()
    else:
        print("Dry run: no changes will be made.")
        results = dry_run()
        for md, lineno, text in results:
            print(f"{md}:{lineno}: {text}")
        print(f"\nTotal placeholder-zero matches: {len(results)}")