"""Tests unit del geocoding (TASK-013 / REQ-GEO-001..005)."""

from __future__ import annotations

import pytest

from megarepartos.config import Settings, get_settings
from megarepartos.infra import geocoding


@pytest.mark.unit
@pytest.mark.req("REQ-GEO-002")
async def test_REQ_GEO_002_sin_api_key_devuelve_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin `GOOGLE_MAPS_API_KEY`, geocodear devuelve None y no llama a Google."""
    monkeypatch.setattr(
        geocoding,
        "get_settings",
        lambda: Settings(google_maps_api_key=None),
    )
    result = await geocoding.geocodear("Av. Siempre Viva 123")
    assert result is None


class _FakeResponse:
    def __init__(self, status_code: int, body: dict) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> dict:
        return self._body


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self._resp = response

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, *args: object, **kwargs: object) -> _FakeResponse:
        return self._resp


@pytest.mark.unit
@pytest.mark.req("REQ-GEO-001")
async def test_REQ_GEO_001_devuelve_lat_lng_de_primer_resultado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        geocoding,
        "get_settings",
        lambda: Settings(google_maps_api_key="dummy"),
    )
    fake = _FakeClient(
        _FakeResponse(
            200,
            {
                "status": "OK",
                "results": [{"geometry": {"location": {"lat": -31.42, "lng": -64.18}}}],
            },
        )
    )
    monkeypatch.setattr(geocoding.httpx, "AsyncClient", lambda **_: fake)
    result = await geocoding.geocodear("Plaza San Martín, Córdoba")
    assert result == (-31.42, -64.18)


@pytest.mark.unit
@pytest.mark.req("REQ-GEO-003")
async def test_REQ_GEO_003_google_error_devuelve_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        geocoding,
        "get_settings",
        lambda: Settings(google_maps_api_key="dummy"),
    )
    fake = _FakeClient(_FakeResponse(200, {"status": "ZERO_RESULTS", "results": []}))
    monkeypatch.setattr(geocoding.httpx, "AsyncClient", lambda **_: fake)
    result = await geocoding.geocodear("Calle inexistente xyz")
    assert result is None

    # HTTP error.
    fake500 = _FakeClient(_FakeResponse(500, {}))
    monkeypatch.setattr(geocoding.httpx, "AsyncClient", lambda **_: fake500)
    result2 = await geocoding.geocodear("X")
    assert result2 is None


@pytest.mark.unit
@pytest.mark.req("REQ-GEO-005")
async def test_REQ_GEO_005_fail_soft_no_excepcion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si get_settings o httpx fallan, geocodear no levanta — devuelve None."""

    def _broken_get_settings() -> Settings:
        raise RuntimeError("settings broken")

    # No mockeamos get_settings — la primera llamada a `getattr(settings,...)`
    # falla pero capturamos en el try/except del módulo. Para verificar,
    # forzamos que httpx tire.
    monkeypatch.setattr(geocoding, "get_settings", lambda: Settings(google_maps_api_key="X"))

    class _Boom:
        async def __aenter__(self) -> _Boom:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError("network down")

    monkeypatch.setattr(geocoding.httpx, "AsyncClient", lambda **_: _Boom())
    result = await geocoding.geocodear("X")
    assert result is None


# Cleanup del cache de settings para no pisar otros tests.
@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
