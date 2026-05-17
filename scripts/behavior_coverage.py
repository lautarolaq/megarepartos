"""Lista REQ-IDs declarados en `behaviors/*.md` y verifica que cada uno tenga al
menos un test que lo cubra vía `@pytest.mark.req("REQ-XXX-YYY")` (regla CLAUDE.md
Tests #2).

Placeholder en TASK-000: `behaviors/` solo tiene el template. Cuando aparezcan
los primeros REQ-IDs reales (TASK-001+) este script empieza a fallar si no se
agregan tests.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEHAVIORS_DIR = ROOT / "behaviors"
TESTS_DIR = ROOT / "backend" / "tests"

REQ_PATTERN = re.compile(r"\bREQ-[A-Z]+-\d+\b")


def collect_reqs_from_behaviors() -> set[str]:
    reqs: set[str] = set()
    if not BEHAVIORS_DIR.exists():
        return reqs
    for md in BEHAVIORS_DIR.glob("*.md"):
        if md.name.startswith("_"):  # `_template.md` no cuenta
            continue
        reqs.update(REQ_PATTERN.findall(md.read_text(encoding="utf-8")))
    return reqs


def collect_reqs_from_tests() -> set[str]:
    reqs: set[str] = set()
    if not TESTS_DIR.exists():
        return reqs
    for py in TESTS_DIR.rglob("*.py"):
        reqs.update(REQ_PATTERN.findall(py.read_text(encoding="utf-8")))
    return reqs


def main() -> int:
    declared = collect_reqs_from_behaviors()
    covered = collect_reqs_from_tests()

    missing = sorted(declared - covered)
    if missing:
        print("REQ-IDs declarados en behaviors/ sin test asociado:\n", file=sys.stderr)
        for r in missing:
            print(f"  - {r}", file=sys.stderr)
        return 1

    if not declared:
        print("behavior_coverage: sin REQ-IDs todavía (esperado en TASK-000)")
        return 0

    print(f"behavior_coverage: OK ({len(declared)} REQ-IDs cubiertos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
