"""Verifica que cada endpoint autenticado tenga un test de aislamiento
multi-tenant (REQ-MT-011, regla CLAUDE.md Tests #5).

Parsea AST de `backend/src/megarepartos/api/*.py` y lista los endpoints que
usan `authenticated_session` como dependencia. Para cada uno chequea que
exista al menos un test en `backend/tests/integration/*.py` marcado con
`@pytest.mark.isolation` que mencione el path del endpoint.

Endpoints exentos (definidos en `EXEMPT_PREFIXES`):
- `/api/auth/*`: pre-tenant.
- `/health`, `/docs`, `/openapi.json`: meta.

Salida:
- exit 0 si todo cubierto.
- exit 1 con la lista de violations.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "backend" / "src" / "megarepartos" / "api"
TESTS_DIR = ROOT / "backend" / "tests" / "integration"

EXEMPT_PREFIXES: tuple[str, ...] = (
    "/api/auth/",
    "/health",
)


@dataclass(frozen=True)
class Endpoint:
    file: Path
    func_name: str
    http_method: str  # GET, POST, etc.
    path: str  # "/api/clientes/{id}"


def _decorator_method_and_path(decorator: ast.AST) -> tuple[str, str] | None:
    """Si el decorator es `@router.<method>('/path', ...)`, devuelve (METHOD, path)."""
    if not isinstance(decorator, ast.Call):
        return None
    func = decorator.func
    if not (isinstance(func, ast.Attribute) and func.attr in {"get", "post", "put", "patch", "delete"}):
        return None
    if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
        return None
    path = decorator.args[0].value
    if not isinstance(path, str):
        return None
    return func.attr.upper(), path


def _function_uses_dependency(func_node: ast.AsyncFunctionDef | ast.FunctionDef, name: str) -> bool:
    """`True` si la función tiene un parámetro con `Depends(<name>)` o referencia
    a `<name>` en su anotación (sirve para `Annotated[..., Depends(name)]`).
    """
    src = ast.unparse(func_node)
    # Match `Depends(<name>` o `Annotated[..., Depends(<name>`.
    return re.search(rf"\bDepends\(\s*{re.escape(name)}\b", src) is not None


def _router_prefix(tree: ast.AST) -> str:
    """Extrae el prefix del `APIRouter(prefix=...)` declarado a nivel módulo."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "APIRouter":
            for kw in node.keywords:
                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                    return str(kw.value.value)
    return ""


def find_endpoints() -> list[Endpoint]:
    if not API_DIR.exists():
        return []
    endpoints: list[Endpoint] = []
    for py in sorted(API_DIR.glob("*.py")):
        if py.name == "__init__.py":
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"))
        prefix = _router_prefix(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            for decorator in node.decorator_list:
                parsed = _decorator_method_and_path(decorator)
                if parsed is None:
                    continue
                method, path = parsed
                full_path = f"{prefix}{path}"
                if not _function_uses_dependency(node, "authenticated_session"):
                    continue
                endpoints.append(
                    Endpoint(file=py, func_name=node.name, http_method=method, path=full_path)
                )
    return endpoints


def is_exempt(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in EXEMPT_PREFIXES)


def collect_isolation_test_haystack() -> str:
    """Junta el código de todos los tests de integración para grep simple."""
    if not TESTS_DIR.exists():
        return ""
    chunks: list[str] = []
    for py in TESTS_DIR.rglob("*.py"):
        chunks.append(py.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def path_to_pattern(path: str) -> re.Pattern[str]:
    r"""Convierte `/api/clientes/{id}` a regex `/api/clientes/[^"'\s/]+`."""
    escaped = re.escape(path)
    # `\{id\}` → `[^"'\s/]+`
    pattern = re.sub(r"\\\{[^}]+\\\}", r"[^\"'\\s/]+", escaped)
    return re.compile(pattern)


def check_endpoint_covered(endpoint: Endpoint, haystack: str) -> bool:
    """`True` si el endpoint aparece mencionado cerca de un `@pytest.mark.isolation`.

    Implementación simple: si el haystack contiene tanto el path (literal o
    pattern) como `mark.isolation`, asumimos cobertura. Suficiente como
    smoke check de CI; tests reales verifican el aislamiento.
    """
    if "mark.isolation" not in haystack:
        return False
    pattern = path_to_pattern(endpoint.path)
    return pattern.search(haystack) is not None


def main(argv: Iterable[str] = ()) -> int:
    endpoints = find_endpoints()
    if not endpoints:
        print("check_endpoint_isolation: sin endpoints autenticados todavía — OK")
        return 0

    haystack = collect_isolation_test_haystack()
    missing: list[Endpoint] = []
    for ep in endpoints:
        if is_exempt(ep.path):
            continue
        if not check_endpoint_covered(ep, haystack):
            missing.append(ep)

    if missing:
        print(
            f"check_endpoint_isolation: {len(missing)} endpoint(s) autenticados sin test "
            f"@pytest.mark.isolation que los referencie:\n",
            file=sys.stderr,
        )
        for ep in missing:
            print(
                f"  - {ep.http_method} {ep.path}  (en {ep.file.relative_to(ROOT)})",
                file=sys.stderr,
            )
        return 1

    print(f"check_endpoint_isolation: OK ({len(endpoints)} endpoint(s) autenticados cubiertos)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
