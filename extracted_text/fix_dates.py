# fix_dates.py
import re
from pathlib import Path

RE = re.compile(r"^(\s*document_date\s*:\s*)(['\"]?)00/00/0000\2\s*$")
for md in Path("releases").rglob("*.md"):
    text = md.read_text(encoding="utf-8").splitlines(keepends=True)
    in_fm = False
    changed = False
    for i, line in enumerate(text):
        if line.strip() == "---":
            in_fm = not in_fm
            continue
        if in_fm:
            m = RE.match(line)
            if m:
                text[i] = f"{m.group(1)}''\n"
                changed = True
    if changed:
        md.write_text("".join(text), encoding="utf-8")
        print(f"Patched {md}")

        