"""Check local Markdown file links; this is not a biosignal validation suite."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    documents = sorted(root.rglob("*.md"))
    failures = []
    links_checked = 0
    for document in documents:
        if ".git" in document.relative_to(root).parts:
            continue
        text = document.read_text(encoding="utf-8")
        # Repository docs use inline links with no embedded parentheses in paths.
        for target in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)\)", text):
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            links_checked += 1
            linked = (document.parent / unquote(parts.path)).resolve()
            if not linked.is_relative_to(root) or not linked.exists():
                failures.append(f"{document.relative_to(root)}: broken local link {target}")
    for failure in failures:
        print(failure, file=sys.stderr)
    print(f"Documentation only: {len(documents)} Markdown files, "
          f"{links_checked} local links, {len(failures)} broken links.")
    print("No application tests or scientific benchmarks were run.")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
