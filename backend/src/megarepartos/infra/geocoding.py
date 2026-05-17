"""Cliente HTTP para Google Maps Geocoding API.

Best-effort: si la API key no está configurada o Google falla, devuelve None
sin levantar excepción (REQ-GEO-002 / 003 / 005).
"""

from __future__ import annotations

import httpx

from megarepartos.config import get_settings
from megarepartos.infra.logging import get_logger

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

_logger = get_logger(__name__)


async def geocodear(direccion: str) -> tuple[float, float] | None:
    """Devuelve `(lat, lng)` de la primera coincidencia o `None`.

    No levanta excepciones — geocoding es fail-soft.
    """
    settings = get_settings()
    api_key = getattr(settings, "google_maps_api_key", None)
    if not api_key:
        _logger.debug("geocoding.skip", reason="no_api_key")
        return None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                GOOGLE_GEOCODE_URL,
                params={"address": direccion, "key": api_key},
            )
        if resp.status_code != 200:
            _logger.warning(
                "geocoding.http_error",
                status_code=resp.status_code,
                direccion_preview=direccion[:60],
            )
            return None
        body = resp.json()
        if body.get("status") != "OK" or not body.get("results"):
            _logger.warning(
                "geocoding.no_match",
                google_status=body.get("status"),
                direccion_preview=direccion[:60],
            )
            return None
        loc = body["results"][0]["geometry"]["location"]
        return float(loc["lat"]), float(loc["lng"])
    except Exception as exc:  # pragma: no cover — defensa contra timeouts/dns
        _logger.warning(
            "geocoding.exception",
            error=str(exc),
            direccion_preview=direccion[:60],
        )
        return None
