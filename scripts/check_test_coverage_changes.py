"""Verifica que cambios en `backend/src/megarepartos/{domain,api}/X.py` vengan
acompañados de cambios en `backend/tests/.../test_X.py` (regla CLAUDE.md Tests #1).

Se compara el diff contra `origin/main`. Placeholder en TASK-000: cuando existan
archivos en `domain/` y `api/`, la lógica de matching se completa.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND_SRC = Path("backend/src/megarepartos")
BACKEND_TESTS = Path("backend/tests")
WATCHED_LAYERS = ("domain", "api")


def _changed_files(base: str = "origin/main") -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode()
    except subprocess.CalledProcessError:
        # Sin base de comparación (primer push) → no se aplica este check.
        return []
    return [Path(p) for p in out.splitlines() if p]


def main() -> int:
    changed = _changed_files()
    if not changed:
        print("check_test_coverage_changes: sin cambios para verificar")
        return 0

    src_files = [
        f
        for f in changed
        if any(
            f.is_relative_to(BACKEND_SRC / layer) and f.suffix == ".py"
            for layer in WATCHED_LAYERS
        )
    ]
    test_files = [f for f in changed if f.is_relative_to(BACKEND_TESTS)]

    missing: list[str] = []
    for src in src_files:
        stem = src.stem
        if stem in {"__init__", "_events"}:
            continue
        expected_pattern = f"test_{stem}"
        has_test_change = any(expected_pattern in t.name for t in test_files)
        if not has_test_change:
            missing.append(f"{src} → falta cambio en `tests/.../test_{stem}.py`")

    if missing:
        print("Archivos de dominio/API modificados sin test asociado:\n", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1

    print("check_test_coverage_changes: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
