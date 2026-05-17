"""Captura context técnico (request_id, ip_origen, user_agent) por request.

Se expone via `contextvars` que `event_recorder` lee al persistir un
`EventoDominio`. El middleware se monta en `main.py` antes que cualquier
router.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ContextVars con default None — fuera de un request devuelven None.
current_request_id: ContextVar[str | None] = ContextVar("current_request_id", default=None)
current_ip_origen: ContextVar[str | None] = ContextVar("current_ip_origen", default=None)
current_user_agent: ContextVar[str | None] = ContextVar("current_user_agent", default=None)

REQUEST_ID_HEADER = "X-Request-ID"
USER_AGENT_MAX_LEN = 512


class AuditContextMiddleware(BaseHTTPMiddleware):
    """Setea `request_id`, `ip_origen`, `user_agent` en contextvars por request.

    - Si el request manda `X-Request-ID`, lo respeta. Sino genera UUID nuevo.
    - El response incluye `X-Request-ID` para correlación cliente↔servidor.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming or uuid.uuid4().hex

        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        if ua and len(ua) > USER_AGENT_MAX_LEN:
            ua = ua[:USER_AGENT_MAX_LEN]

        tokens = (
            current_request_id.set(request_id),
            current_ip_origen.set(ip),
            current_user_agent.set(ua),
        )
        try:
            response = await call_next(request)
        finally:
            current_request_id.reset(tokens[0])
            current_ip_origen.reset(tokens[1])
            current_user_agent.reset(tokens[2])

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
