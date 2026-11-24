from __future__ import annotations

import re
import sys
from pathlib import Path

CHECKLIST = Path("specs/001-soc-triage-correlacao/checklists/pilot-evaluation-sc007.md")

# Linhas de dados de caso: começam com '| T'/'| C'/'| Q'/'| CT' (IDs dos casos SC-007)
CASE_ROW_RE = re.compile(r"^\|\s*(T\d+|C\d+|Q\d+|CT\d+)_", re.IGNORECASE)


def count_case_rows(text: str) -> tuple[int, list[str]]:
    rows = []
    for line in text.splitlines():
        if CASE_ROW_RE.match(line.strip()):
            rows.append(line.strip())
    return len(rows), rows


def main() -> int:
    if not CHECKLIST.exists():
        print(f"ERRO: checklist não encontrado: {CHECKLIST}", file=sys.stderr)
        return 2
    text = CHECKLIST.read_text(encoding="utf-8", errors="replace")
    count, rows = count_case_rows(text)
    print(f"CHECKLIST={CHECKLIST.as_posix()}")
    print(f"CASE_ROWS={count}")
    for i, r in enumerate(rows, 1):
        case_id = r.split("|", 2)[1].strip()
        print(f"CASE_{i:02d}={case_id}")
    return 0 if count == 20 else 1


if __name__ == "__main__":
    raise SystemExit(main())
