"""Verifica reglas no negociables de arquitectura (CLAUDE.md > Backend > 6, 7).

Reglas:
- `api/*.py` NO puede importar de `megarepartos.models`.
- `domain/*.py` NO puede importar de `megarepartos.api` ni `megarepartos.schemas`.
- (Más reglas se agregan en TASKs siguientes a medida que el código las exija).

Placeholder en TASK-000: cuando `backend/src/megarepartos/{api,domain,schemas}/`
existan con código real, este script va a parsear AST y reportar violaciones.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src" / "megarepartos"

# (layer_directory, modules_que_no_puede_importar)
FORBIDDEN_IMPORTS: dict[str, tuple[str, ...]] = {
    "api": ("megarepartos.models",),
    "domain": ("megarepartos.api", "megarepartos.schemas"),
}


def _imports_in_file(path: Path) -> set[str]:
    """Devuelve los módulos importados en `path` (vía `import x` o `from x import ...`)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        print(f"WARN: no se pudo parsear {path}: {exc}", file=sys.stderr)
        return set()

    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def check_layer(layer: str, forbidden: tuple[str, ...]) -> list[str]:
    layer_dir = BACKEND_SRC / layer
    if not layer_dir.exists():
        return []

    violations: list[str] = []
    for file in layer_dir.rglob("*.py"):
        for imp in _imports_in_file(file):
            for prefix in forbidden:
                if imp == prefix or imp.startswith(prefix + "."):
                    violations.append(
                        f"{file.relative_to(BACKEND_SRC.parent.parent.parent)}: "
                        f"importa `{imp}` (prohibido en `{layer}/`)"
                    )
    return violations


def main() -> int:
    all_violations: list[str] = []
    for layer, forbidden in FORBIDDEN_IMPORTS.items():
        all_violations.extend(check_layer(layer, forbidden))

    if all_violations:
        print("Violaciones de arquitectura detectadas:\n", file=sys.stderr)
        for v in all_violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print("check_arquitectura: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
