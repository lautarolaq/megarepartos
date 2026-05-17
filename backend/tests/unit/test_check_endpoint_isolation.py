"""Tests del script `scripts/check_endpoint_isolation.py` (REQ-MT-011 / 012)."""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

# Cargar el script como módulo (no es un package importable).
SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "check_endpoint_isolation.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("check_endpoint_isolation", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # Registrar antes de exec_module — dataclasses con `from __future__ import
    # annotations` resuelve tipos vía sys.modules[cls.__module__].
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def module() -> Any:
    return _load_module()


@pytest.mark.unit
def test_path_to_pattern_matches_concrete_paths(module: Any) -> None:
    """Pattern para `/api/clientes/{id}` matchea un UUID concreto pero no
    `/api/clientes/{id}/algo`."""
    pattern = module.path_to_pattern("/api/clientes/{id}")
    assert pattern.search("/api/clientes/abc-123")
    assert pattern.search('"/api/clientes/abc-123"')
    # No matchea otro recurso.
    assert not pattern.search("/api/productos/abc-123")


@pytest.mark.unit
def test_is_exempt_acepta_auth_endpoints(module: Any) -> None:
    assert module.is_exempt("/api/auth/google/url")
    assert module.is_exempt("/api/auth/me")
    assert module.is_exempt("/health")
    assert not module.is_exempt("/api/clientes")
    assert not module.is_exempt("/api/productos/123")


@pytest.mark.unit
@pytest.mark.req("REQ-MT-011")
def test_REQ_MT_011_check_endpoint_isolation_falla_si_falta_test(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si hay un endpoint autenticado sin test de aislamiento, el script
    devuelve exit 1."""
    api_dir = tmp_path / "backend" / "src" / "megarepartos" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "clientes.py").write_text(
        textwrap.dedent(
            """
            from typing import Annotated
            from fastapi import APIRouter, Depends
            from megarepartos.infra.auth import authenticated_session

            router = APIRouter(prefix="/api/clientes")

            @router.get("")
            async def listar(session: Annotated[object, Depends(authenticated_session)]):
                return []
            """
        ),
        encoding="utf-8",
    )

    tests_dir = tmp_path / "backend" / "tests" / "integration"
    tests_dir.mkdir(parents=True)
    # Sin test de aislamiento → debería fallar.

    monkeypatch.setattr(module, "API_DIR", api_dir)
    monkeypatch.setattr(module, "TESTS_DIR", tests_dir)
    monkeypatch.setattr(module, "ROOT", tmp_path)

    code = module.main([])
    assert code == 1


@pytest.mark.unit
@pytest.mark.req("REQ-MT-011")
def test_REQ_MT_011_check_endpoint_isolation_pasa_con_test_presente(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si el test existe y referencia el path, el script pasa."""
    api_dir = tmp_path / "backend" / "src" / "megarepartos" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "clientes.py").write_text(
        textwrap.dedent(
            """
            from typing import Annotated
            from fastapi import APIRouter, Depends
            from megarepartos.infra.auth import authenticated_session

            router = APIRouter(prefix="/api/clientes")

            @router.get("")
            async def listar(session: Annotated[object, Depends(authenticated_session)]):
                return []
            """
        ),
        encoding="utf-8",
    )

    tests_dir = tmp_path / "backend" / "tests" / "integration"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_clientes.py").write_text(
        textwrap.dedent(
            """
            import pytest

            @pytest.mark.isolation
            async def test_clientes_aislamiento(app_client):
                resp = await app_client.get("/api/clientes")
                assert resp.status_code == 200
            """
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "API_DIR", api_dir)
    monkeypatch.setattr(module, "TESTS_DIR", tests_dir)
    monkeypatch.setattr(module, "ROOT", tmp_path)

    code = module.main([])
    assert code == 0


@pytest.mark.unit
@pytest.mark.req("REQ-MT-012")
def test_REQ_MT_012_check_corre_en_ci(module: Any) -> None:
    """El workflow CI llama a `scripts/check_endpoint_isolation.py`."""
    ci_yml = SCRIPT_PATH.parent.parent / ".github" / "workflows" / "ci.yml"
    contenido = ci_yml.read_text(encoding="utf-8")
    assert "check_endpoint_isolation.py" in contenido
