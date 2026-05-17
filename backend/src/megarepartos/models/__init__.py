"""SQLAlchemy models. Importar todos acá para que `Base.metadata` los registre.

Alembic env.py importa este módulo para obtener el target_metadata completo.
"""

from megarepartos.models.base import Base
from megarepartos.models.campana import Campana
from megarepartos.models.cliente import Cliente, ProductoHabitual
from megarepartos.models.empresa import Empresa
from megarepartos.models.evento import EventoDominio
from megarepartos.models.extension import TokenExtension
from megarepartos.models.mensaje import MensajeEnviado
from megarepartos.models.plan import Plan
from megarepartos.models.producto import Envase, Producto
from megarepartos.models.respuesta import ConfirmacionPedido, RespuestaLink
from megarepartos.models.sheet import SheetReferencia
from megarepartos.models.template import TemplateFormulario, TemplateMensaje
from megarepartos.models.usuario import Usuario
from megarepartos.models.zona import Zona

__all__ = [
    "Base",
    "Campana",
    "Cliente",
    "ConfirmacionPedido",
    "Empresa",
    "Envase",
    "EventoDominio",
    "MensajeEnviado",
    "Plan",
    "Producto",
    "ProductoHabitual",
    "RespuestaLink",
    "SheetReferencia",
    "TemplateFormulario",
    "TemplateMensaje",
    "TokenExtension",
    "Usuario",
    "Zona",
]
