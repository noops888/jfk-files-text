# check_dates.py
import glob
import frontmatter
from dateutil.parser import parse as dt_parse
from pathlib import Path
from collections import Counter

INVALID_PLACEHOLDERS = {"01/01/0000", "0000-00-00"}

def is_date_key(k):
    return "date" in k.lower()

def validate_dates(root="releases"):
    problems = []
    for path in Path(root).rglob("*.md"):
        post = frontmatter.load(path)
        for key, val in post.metadata.items():
            if isinstance(val, str) and is_date_key(key):
                raw = val.strip()
                # skip if no date provided
                if not raw:
                    continue
                if raw in INVALID_PLACEHOLDERS:
                    problems.append((path, key, raw, "placeholder zero"))
                    continue
                try:
                    # try parsing (allows times, mixed formats, etc.)
                    parsed = dt_parse(raw)
                except Exception as e:
                    problems.append((path, key, raw, str(e)))
    return problems

if __name__ == "__main__":
    problems = validate_dates()
    # Detailed list of issues
    for p, key, raw, reason in problems:
        print(f"{str(p):60}  {key:15}  {raw:20}  → {reason}")
    # Summary
    print("\nSummary of issues:")
    by_reason = Counter(reason for _, _, _, reason in problems)
    for reason, count in by_reason.items():
        print(f"  {count}× {reason}")
    print("\nUnique raw values:")
    by_raw = Counter(raw for _, _, raw, _ in problems)
    for raw, count in by_raw.items():
        print(f"  {count}× {raw!r}")