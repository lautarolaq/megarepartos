"""Domain de campañas — unidad de organización de envíos en lote.

Una `Campana` representa una operación de envío: el sodero genera links de
confirmación (broadcast o bulk individual), persistimos un row de Campana,
y todas las confirmaciones que entren por esos links quedan taggeadas con
`campana_id`. Eso permite agrupar/filtrar pedidos por campaña en el dashboard.

NOTA: las campañas viejas del modelo (`tipo` consulta|aviso|cobranza|encuesta)
asumían `template_mensaje_id` NOT NULL y un flujo de programación. Acá usamos
una variante simplificada: `template_mensaje_id = NULL`, mensaje snapshoteado
en `destinatarios_origen.mensaje`, estado pasa directo a "enviada".
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from megarepartos.models.campana import Campana

TipoEnvio = Literal["broadcast", "bulk_individual"]


@dataclass(slots=True)
class CampanaResumen:
    id: uuid.UUID
    nombre: str
    tipo_envio: str  # broadcast | bulk_individual
    zona_id: uuid.UUID | None
    zona_nombre: str | None
    mensaje: str
    fecha_creacion: Any
    n_confirmados: int
    n_rechazados: int


@dataclass(slots=True)
class RespuestaCampana:
    cliente_id: uuid.UUID
    cliente_nombre: str
    cliente_telefono: str
    accion: str  # confirmo | rechazo
    fecha: Any
    productos: list[dict[str, Any]]


@dataclass(slots=True)
class CampanaDetalle:
    id: uuid.UUID
    nombre: str
    tipo_envio: str
    zona_id: uuid.UUID | None
    zona_nombre: str | None
    mensaje: str
    fecha_creacion: Any
    respuestas: list[RespuestaCampana]


async def crear_campana(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    nombre: str,
    tipo_envio: TipoEnvio,
    zona_id: uuid.UUID | None,
    mensaje: str,
) -> Campana:
    """Persiste una nueva campaña en estado "enviada" (no manejamos drafts
    todavía — el sodero arma + envía en un solo acto).

    El mensaje se snapshotea en `destinatarios_origen` JSONB para que la
    campaña sea reproducible aunque después se edite el default de la empresa.
    """
    campana = Campana(
        empresa_id=empresa_id,
        usuario_creador_id=usuario_id,
        nombre=nombre.strip()[:255],
        tipo="consulta",  # único tipo que usamos por ahora del enum legacy
        template_mensaje_id=None,
        estado="enviada",
        destinatarios_origen={
            "tipo_envio": tipo_envio,
            "zona_id": str(zona_id) if zona_id else None,
            "mensaje": mensaje,
        },
    )
    session.add(campana)
    await session.flush()
    await session.refresh(campana)
    return campana


async def listar_campanas(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[CampanaResumen]:
    """Lista campañas con conteos de confirmados/rechazados (extraídos del
    event_dominio con accion='respondio_link'). RLS filtra por empresa.
    """
    # Una sola query con LEFT JOIN al evento_dominio agregado.
    sql = text("""
        SELECT
            c.id, c.nombre, c.destinatarios_origen, c.fecha_creacion,
            z.nombre AS zona_nombre,
            COALESCE(SUM(CASE WHEN ed.detalles_jsonb->>'accion' = 'confirmo' THEN 1 ELSE 0 END), 0) AS n_confirmados,
            COALESCE(SUM(CASE WHEN ed.detalles_jsonb->>'accion' = 'rechazo' THEN 1 ELSE 0 END), 0) AS n_rechazados
        FROM campana c
        LEFT JOIN zona z
          ON c.destinatarios_origen->>'zona_id' IS NOT NULL
         AND z.id = (c.destinatarios_origen->>'zona_id')::uuid
        LEFT JOIN evento_dominio ed
          ON ed.empresa_id = c.empresa_id
         AND ed.accion = 'respondio_link'
         AND ed.detalles_jsonb->>'campana_id' IS NOT NULL
         AND (ed.detalles_jsonb->>'campana_id')::uuid = c.id
        WHERE c.empresa_id = :empresa_id
        GROUP BY c.id, c.nombre, c.destinatarios_origen, c.fecha_creacion, z.nombre
        ORDER BY c.fecha_creacion DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = (
        await session.execute(
            sql,
            {"empresa_id": empresa_id, "limit": limit, "offset": offset},
        )
    ).all()

    out: list[CampanaResumen] = []
    for r in rows:
        dor = r.destinatarios_origen or {}
        out.append(
            CampanaResumen(
                id=r.id,
                nombre=r.nombre,
                tipo_envio=dor.get("tipo_envio", "broadcast"),
                zona_id=uuid.UUID(dor["zona_id"]) if dor.get("zona_id") else None,
                zona_nombre=r.zona_nombre,
                mensaje=dor.get("mensaje", ""),
                fecha_creacion=r.fecha_creacion,
                n_confirmados=int(r.n_confirmados),
                n_rechazados=int(r.n_rechazados),
            )
        )
    return out


async def obtener_campana_detalle(
    session: AsyncSession,
    *,
    empresa_id: uuid.UUID,
    campana_id: uuid.UUID,
) -> CampanaDetalle | None:
    """Devuelve la campaña + lista de respuestas con datos del cliente."""
    campana = (
        await session.execute(
            select(Campana).where(Campana.id == campana_id, Campana.empresa_id == empresa_id)
        )
    ).scalar_one_or_none()
    if campana is None:
        return None

    dor = campana.destinatarios_origen or {}

    # Zona nombre (opcional)
    zona_nombre: str | None = None
    if dor.get("zona_id"):
        zona_nombre = (
            await session.execute(
                text("SELECT nombre FROM zona WHERE id = :id"),
                {"id": dor["zona_id"]},
            )
        ).scalar_one_or_none()

    # Respuestas de esta campaña + datos del cliente.
    sql_resp = text("""
        SELECT
            (ed.entidad_id) AS cliente_id,
            cl.nombre_completo,
            cl.telefono,
            ed.detalles_jsonb->>'accion' AS accion,
            ed.fecha,
            COALESCE(ed.detalles_jsonb->'productos', '[]'::jsonb) AS productos
        FROM evento_dominio ed
        LEFT JOIN cliente cl ON cl.id = ed.entidad_id
        WHERE ed.empresa_id = :empresa_id
          AND ed.accion = 'respondio_link'
          AND ed.detalles_jsonb->>'campana_id' IS NOT NULL
          AND (ed.detalles_jsonb->>'campana_id')::uuid = :campana_id
        ORDER BY ed.fecha DESC
    """)
    rows = (
        await session.execute(sql_resp, {"empresa_id": empresa_id, "campana_id": campana_id})
    ).all()

    respuestas = [
        RespuestaCampana(
            cliente_id=r.cliente_id,
            cliente_nombre=r.nombre_completo or "—",
            cliente_telefono=r.telefono or "—",
            accion=r.accion or "—",
            fecha=r.fecha,
            productos=list(r.productos or []),
        )
        for r in rows
    ]

    return CampanaDetalle(
        id=campana.id,
        nombre=campana.nombre,
        tipo_envio=dor.get("tipo_envio", "broadcast"),
        zona_id=uuid.UUID(dor["zona_id"]) if dor.get("zona_id") else None,
        zona_nombre=zona_nombre,
        mensaje=dor.get("mensaje", ""),
        fecha_creacion=campana.fecha_creacion,
        respuestas=respuestas,
    )
