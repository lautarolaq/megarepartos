# MEGAREPARTOS - Especificación completa

**Versión**: 1.1  
**Fecha**: Mayo 2026  
**Autor**: Lautaro  
**Estado**: Listo para desarrollo con Claude Code

---

## TABLA DE CONTENIDOS

### Parte 1: Producto

1. [Visión del producto](#1-visión-del-producto)
2. [Mercado objetivo](#2-mercado-objetivo)
3. [Arquitectura conceptual](#3-arquitectura-conceptual)
4. [Stack técnico](#4-stack-técnico)
5. [Modelo de datos](#5-modelo-de-datos)
6. [Funcionalidades del producto](#6-funcionalidades-del-producto)
7. [Integración con Google Sheets](#7-integración-con-google-sheets)
8. [Extensión Chrome](#8-extensión-chrome)
9. [Sistema de campañas](#9-sistema-de-campañas)
10. [Seguridad y multi-tenant](#10-seguridad-y-multi-tenant)
11. [Backups y datos](#11-backups-y-datos)
12. [Pricing y planes](#12-pricing-y-planes)

### Parte 2: Filosofía de desarrollo

13. [Filosofía de desarrollo / Vibe coding](#13-filosofía-de-desarrollo--vibe-coding)
14. [Sistema de Testing](#14-sistema-de-testing)
15. [Observabilidad](#15-observabilidad)
16. [Mantenimiento](#16-mantenimiento)
17. [Estructura del repo](#17-estructura-del-repo)
18. [CI/CD](#18-cicd)
19. [CLAUDE.md (Reglas de codeo)](#19-claudemd-reglas-de-codeo)
20. [Sistema de Tareas (tarea.yaml)](#20-sistema-de-tareas-tareayaml)

### Parte 3: Operación

21. [Convenciones de código](#21-convenciones-de-código)
22. [Plan de sprints](#22-plan-de-sprints)
23. [Decisiones explícitas tomadas](#23-decisiones-explícitas-tomadas)
24. [Lo que NO está en el producto](#24-lo-que-no-está-en-el-producto)
25. [Roadmap post-MVP](#25-roadmap-post-mvp)

---

# PARTE 1: PRODUCTO

---

## 1. VISIÓN DEL PRODUCTO

### Qué es Megarepartos

**Megarepartos es una plataforma de campañas de WhatsApp para negocios de reparto recurrente.**

Permite a una empresa enviar mensajes masivos a sus clientes y, opcionalmente, capturar respuestas estructuradas vía formularios web. Los casos de uso típicos son consulta de pedidos antes de visitar, cobranzas, encuestas post-servicio y promociones.

### Qué problema resuelve

Negocios de reparto recurrente (soderías, garrafas, viandas, verduras, distribuidoras) hoy gestionan la comunicación con sus clientes de forma manual:

- Mandan broadcast lists por WhatsApp preguntando "¿necesitás X mañana?".
- Reciben respuestas variadas que alguien tipea en Excel.
- Filtran respuestas, arman listas para repartidor.
- Para cobranzas: mandan mensajes uno por uno con CBU y monto.

Esto puede consumir una persona dedicada full-time. Megarepartos automatiza estas tareas y libera ese tiempo.

### Filosofía

**Complemento, no reemplazo.** Megarepartos NO reemplaza el sistema actual de la sodería (Reparto de Agua, Sodaher, Yaku, Excel, lo que sea). Se complementa con cualquier sistema existente vía exportaciones e importaciones Google Sheets.

### Modelo de negocio

SaaS con planes mensuales en pesos argentinos. Suscripción recurrente. Sin permanencia.

---

## 2. MERCADO OBJETIVO

### Vertical inicial: soderías

- ~4000 soderías en Argentina (estimado).
- La mayoría son chicas (1-2 camionetas, 100-400 clientes).
- Algunas medianas (3-5 camionetas, 500-1500 clientes).
- Pocas grandes (10+ camionetas, 2000+ clientes).

### Verticales futuros (mismo producto)

- Reparto de garrafas de gas.
- Reparto semanal de cajones de verduras/frutas.
- Viandas semanales.
- Distribuidoras mayoristas a kioskos.
- Lavaderos a domicilio.
- Otros negocios de reparto recurrente.

### Decisión

Producto horizontal pero **go-to-market focalizado en soderías** durante el primer año. Cuando haya 5-10 soderías pagando, expansión a garrafas (el más similar).

---

## 3. ARQUITECTURA CONCEPTUAL

El producto tiene dos motores y un sistema operativo:

### Motor 1: Envío masivo por WhatsApp

- Toma una lista de destinatarios + un template de mensaje con variables.
- Envía vía extensión Chrome propia que controla WhatsApp Web del usuario.
- Delays aleatorios entre 3-8 segundos.
- Tracking de qué se envió, falló, cuándo.

### Motor 2: Formularios via link único

- Genera links únicos firmados por destinatario.
- Cada link abre una página configurable.
- Captura respuestas estructuradas en DB.
- Exporta resultados a Google Sheets.

### Sistema operativo: campañas

Una campaña es la unidad operativa que combina:

- Una lista de destinatarios (clientes filtrados o sheet subido).
- Un template de mensaje (motor 1).
- Un template de formulario asociado (motor 2, opcional).
- Una fecha de ejecución.
- Resultados acumulados.

### Tipos de campaña pre-armados

1. **Consulta de pedido**: con link a formulario para confirmar/modificar pedido habitual.
2. **Aviso/recordatorio**: solo mensaje, sin link.
3. **Cobranza**: solo mensaje con monto y datos de pago.
4. **Encuesta**: con link a formulario simple de feedback.

---

## 4. STACK TÉCNICO

### Backend

- **Lenguaje**: Python 3.12+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0 con asyncio
- **Migraciones**: Alembic
- **Validación**: Pydantic v2
- **Auth**: JWT con google-auth para OAuth
- **Logging**: structlog con JSON output
- **Workers/jobs**: Background tasks con FastAPI + Cloud Run jobs si hace falta

### Frontend (app web)

- **Framework**: Vite + React 18 + TypeScript
- **Routing**: React Router v6
- **State**: Zustand (más simple que Redux)
- **UI**: Tailwind CSS + Headless UI
- **Forms**: React Hook Form + Zod validation
- **HTTP**: TanStack Query (React Query)
- **PWA**: vite-plugin-pwa para offline básico

### Frontend (página pública del link)

- **Framework**: mismo stack o un componente standalone simple.
- **Mobile-first**: prioritario.
- **Sin login**: público con token firmado.

### Extensión Chrome

- **Manifest V3** (obligatorio en 2026).
- **TypeScript** para mantenibilidad.
- **Content scripts** que manipulan DOM de WhatsApp Web.
- **Background script** que coordina con backend.
- **UI** en popup con React.

### Base de datos

- **Neon Postgres** (serverless, free tier inicial).
- **Branching** por feature para desarrollo.
- **Row-Level Security** habilitado.

### Hosting

- **Backend**: Google Cloud Run (free tier).
- **Frontend**: Cloud Storage + Cloud CDN (free tier).
- **Page público del link**: mismo deploy del frontend.

### Auth

- **Google OAuth 2.0** para usuarios de la app.
- **Scope incremental**: email primero, drive.file cuando se necesite.

### Storage

- **Google Cloud Storage** para backups de DB.

### Secretos

- **Google Secret Manager** para todas las credenciales.

### Geocoding

- **Google Maps Geocoding API** (free tier cubre el uso esperado).

### Testing

- **Backend**: pytest + httpx + hypothesis + testcontainers.
- **Frontend**: Vitest + React Testing Library.
- **E2E**: Playwright.
- **Tests obligatorios**: aislamiento multi-tenant en cada endpoint.

### CI/CD

- **GitHub Actions** (gratis para proyectos chicos).
- **Deploys automáticos**: PR review + merge a main = deploy a producción.

### Observabilidad

- **Cloud Logging** (free tier).
- **Cloud Monitoring** para alertas (free tier).
- **UptimeRobot** o **Cloud Scheduler** para synthetic monitoring (gratis).

---

## 5. MODELO DE DATOS

### Entidades principales

#### empresa

```
- id (uuid, pk)
- nombre
- tipo_negocio (sodería, garrafas, verduras, etc.)
- plan_id (fk)
- estado_suscripcion (trial, activa, suspendida, cancelada)
- fecha_creacion
- fecha_cancelacion (nullable)
- direccion_deposito (texto)
- coordenadas_deposito (lat, lng)
- timezone (default 'America/Argentina/Cordoba')
- config_jsonb (preferencias)
```

#### usuario

```
- id (uuid, pk)
- empresa_id (fk)
- email
- nombre
- rol (admin, operador)
- google_oauth_token (encriptado)
- google_oauth_scopes (array)
- ultima_sesion
- activo (bool)
- fecha_creacion
```

#### producto

```
- id (uuid, pk)
- empresa_id (fk)
- nombre
- descripcion (nullable)
- precio_unitario_default
- es_retornable (bool)
- envase_id (nullable, fk a envase)
- activo (bool)
- orden_display (int)
```

#### envase

```
- id (uuid, pk)
- empresa_id (fk)
- nombre (ej "Botellón de plástico 20L")
- valor_referencial (precio si no se devuelve)
- activo (bool)
```

#### zona

```
- id (uuid, pk)
- empresa_id (fk)
- nombre (ej "Nueva Córdoba", "General Paz")
- dia_visita (lunes/martes/.../domingo)
- camioneta_asignada (texto libre, nullable)
- color_display (para visualización en mapa)
- activo (bool)
```

#### cliente

```
- id (uuid, pk)
- empresa_id (fk)
- nombre_completo
- telefono (normalizado a formato internacional)
- email (nullable)
- direccion (texto)
- coordenadas (lat, lng, nullable)
- zona_id (fk)
- modalidad (fijo, consulta, demanda)
- frecuencia (semanal, quincenal, mensual)
- observaciones_permanentes (texto, nullable)
- lista_precios_id (fk, nullable)
- condicion_pago (contado, cuenta_corriente)
- activo (bool, soft delete)
- fecha_creacion
- fecha_modificacion
- ultima_consulta
- ultima_visita
```

#### producto_habitual

```
- id (uuid, pk)
- cliente_id (fk)
- producto_id (fk)
- cantidad
```

#### campana

```
- id (uuid, pk)
- empresa_id (fk)
- usuario_creador_id (fk)
- nombre (ej "Consulta Norte Jueves 15/05")
- tipo (consulta, aviso, cobranza, encuesta)
- template_mensaje_id (fk)
- template_formulario_id (fk, nullable)
- estado (borrador, enviando, enviada, cerrada)
- fecha_programada
- fecha_envio_inicio (nullable)
- fecha_envio_fin (nullable)
- destinatarios_origen (jsonb: filtros aplicados o sheet_id)
- estadisticas (jsonb: enviados, respondidos, fallidos, etc.)
- fecha_creacion
```

#### template_mensaje

```
- id (uuid, pk)
- empresa_id (fk, nullable si es preset del sistema)
- nombre
- tipo (consulta, aviso, cobranza, encuesta)
- contenido (con variables {nombre}, {monto}, {link}, etc.)
- es_preset (bool)
- activo (bool)
```

#### template_formulario

```
- id (uuid, pk)
- empresa_id (fk, nullable si es preset)
- nombre
- tipo (confirmar_pedido, encuesta_feedback, etc.)
- config_jsonb (campos, validaciones, branding)
- es_preset (bool)
- activo (bool)
```

#### mensaje_enviado

```
- id (uuid, pk)
- campana_id (fk)
- cliente_id (fk, nullable si destinatario es sheet)
- destinatario_telefono
- destinatario_nombre (snapshot al momento)
- contenido_final (mensaje resuelto con variables)
- link_unico (nullable)
- token_link (nullable, único, firmado)
- estado (pendiente, enviado, fallido, leido)
- fecha_envio (nullable)
- fecha_lectura (nullable, si detectamos)
- error_detalle (nullable)
```

#### respuesta_link

```
- id (uuid, pk)
- mensaje_enviado_id (fk)
- token_usado
- fecha_acceso
- ip_acceso
- user_agent
- accion (confirmo, rechazo, en_proceso)
- datos_jsonb (respuestas del formulario)
- fecha_accion (nullable)
```

#### confirmacion_pedido

```
- id (uuid, pk)
- respuesta_link_id (fk)
- cliente_id (fk)
- fecha_propuesta
- productos_solicitados (jsonb)
- envases_a_devolver (jsonb)
- observacion_cliente (texto)
```

#### evento_dominio

```
- id (uuid, pk)
- empresa_id (fk)
- usuario_id (fk, nullable si sistema)
- entidad_tipo (cliente, campana, producto, etc.)
- entidad_id
- accion (creado, modificado, borrado, exportado, etc.)
- detalles_jsonb (diff de cambios)
- fecha
- ip_origen
- user_agent
```

#### token_extension

```
- id (uuid, pk)
- empresa_id (fk)
- usuario_id (fk)
- token (uuid único)
- fecha_creacion
- fecha_ultima_validacion
- revocado (bool)
- detalles_jsonb (info de la instalación)
```

#### sheet_referencia

```
- id (uuid, pk)
- empresa_id (fk)
- tipo (importacion_clientes, cobranzas, export_confirmados, export_ruta)
- google_sheet_id
- google_sheet_url
- nombre
- fecha_creacion
- fecha_ultima_lectura
- estado (activo, procesado, archivado)
- campana_id (nullable, fk si está asociado)
```

### Decisiones de modelado

- **Multi-tenant**: cada tabla tiene `empresa_id`. RLS de Postgres lo enforce a nivel DB.
- **Soft delete**: `activo (bool)` en entidades importantes. Hard delete solo por pedido legal.
- **Auditoría completa**: `evento_dominio` registra todo cambio significativo.
- **Snapshots**: en `mensaje_enviado` guardamos el snapshot del nombre/teléfono al momento de enviar, no solo la FK, por si el cliente se borra después.
- **JSONB**: para datos estructurados que pueden evolucionar (configuraciones, estadísticas, datos de formularios).

---

## 6. FUNCIONALIDADES DEL PRODUCTO

### 6.1 Onboarding inicial

#### Paso 1: Registro
- Login con Google OAuth.
- Verificación de email.
- Si es primera vez: wizard de setup.

#### Paso 2: Configuración de empresa
- Nombre de la empresa.
- Rubro (sodería, garrafas, verdura, viandas, distribuidora, otro).
- Dirección del depósito (origen de las rutas).
- Timezone (default según rubro/región).

#### Paso 3: Productos
- Sugiere productos según rubro:
  - Sodería: Bidón 20L, Soda 1.5L, Agua mineral 500ml, etc.
  - Garrafas: Garrafa 10kg, Garrafa 15kg, etc.
- El usuario edita / agrega / borra.
- Define cuáles son retornables.

#### Paso 4: Envases retornables
- Configura envases asociados a productos retornables.

#### Paso 5: Zonas
- Configura sus zonas geográficas.
- Asigna día y camioneta a cada zona.

#### Paso 6: Importar clientes
- Sugiere fuertemente importar.
- Salteable, banner persistente si no se hace.

#### Paso 7: Listo
- Dashboard principal con CTA "Crear primera campaña".

### 6.2 CRUDs principales (en la app, NO en sheets)

#### Productos
- Listar / buscar / filtrar.
- Crear / editar / desactivar.
- Reorganizar orden de display.

#### Envases
- Listar / crear / editar / desactivar.

#### Zonas
- Listar (con preview en mapa).
- Crear / editar / desactivar.
- Sugerencia de partición automática si una zona crece mucho.
- Mover clientes entre zonas (drag & drop o selección masiva).

#### Clientes
- Listar / buscar / filtrar (por zona, modalidad, día, activo).
- Búsqueda difusa por nombre/teléfono.
- Crear / editar / desactivar.
- Detalle con histórico de visitas, confirmaciones, observaciones.
- Edición de productos habituales con cantidades.

#### Usuarios
- Listar usuarios de la empresa.
- Invitar usuarios (envío de email con link de aceptación).
- Cambiar roles.
- Desactivar.

#### Templates de mensaje y formulario
- Listar (incluye presets del sistema).
- Crear / editar (solo los propios).
- Preview con datos de ejemplo.

### 6.3 Importación masiva de clientes

#### Flujo
1. Usuario aprieta "Importar clientes desde Sheets".
2. Modal: explica que se va a crear un sheet en su Drive.
3. OAuth incremental para `drive.file` si no se dio antes.
4. Sistema crea sheet en `Megarepartos/Clientes/2026-05-15 - Importación inicial`.
5. Sheet tiene template fijo con encabezados protegidos.
6. Frontend abre sheet en nueva pestaña.
7. Usuario rellena.
8. Vuelve a la app y aprieta "Procesar".
9. Sistema lee sheet, valida, muestra preview.
10. Usuario confirma y se importan.

#### Template del sheet

**Hoja "Clientes"** con columnas:
- Nombre completo (obligatorio)
- Teléfono (obligatorio)
- Dirección (obligatorio)
- Zona (dropdown con zonas configuradas)
- Día de visita (dropdown)
- Modalidad (dropdown: Fijo / Consulta / Demanda)
- Frecuencia (dropdown: Semanal / Quincenal / Mensual)
- Email (opcional)
- Observaciones permanentes (opcional)
- Lista de precios (dropdown, opcional)
- Condición de pago (dropdown: Contado / Cuenta corriente)
- Una columna por producto del catálogo, con la cantidad habitual.

**Hoja "Instrucciones"** con explicación detallada y ejemplos.

Encabezados y validaciones protegidos. Filas de datos editables.

#### Manejo de errores
- Filas vacías: ignoradas.
- Errores: lista detallada por fila con sugerencia de fix.
- Advertencias: ej dirección no geocodificable, ofrece ajuste manual con mapa.
- El usuario puede importar solo válidos, dejando erróneos para después.

#### Re-importaciones
- Mismo sheet o uno nuevo.
- Si un cliente ya existe (matching difuso): se avisa, no se sobreescribe sin confirmación.
- Nunca borrar por ausencia en sheet.

### 6.4 Sistema de campañas

#### Crear campaña

Pantalla con wizard:

**Paso 1: Tipo de campaña**
- Consulta de pedido
- Aviso/recordatorio
- Cobranza
- Encuesta
- Custom

**Paso 2: Destinatarios**

Tres formas combinables:

A. **Filtros sobre clientes**:
- Por zona (multi-select).
- Por modalidad.
- Por día de visita.
- Por frecuencia.
- Por última visita (rango).
- Por condición de pago.

B. **Subida de sheet**:
- Botón "Subir desde Google Sheet".
- Crea sheet con template del tipo de campaña.
- Usuario rellena (puede pegar desde otro sistema).
- Sistema parsea y matchea con clientes existentes.

C. **Selección manual**:
- Listado con checkboxes para elegir uno por uno.

**Paso 3: Mensaje**
- Selecciona template (preset o propio).
- Preview con cliente de ejemplo.
- Variables disponibles: `{nombre}`, `{productos}`, `{monto}`, `{dias_mora}`, `{link}`, `{empresa}`.

**Paso 4: Formulario** (si aplica)
- Selecciona template de formulario.
- Configuración específica si aplica.
- Preview.

**Paso 5: Programación y envío**
- Fecha y hora de envío (ahora o programado).
- Estimación de duración (basado en cantidad).
- Confirmación final.

#### Ejecución
- Estado "enviando" mientras la extensión procesa.
- Panel en vivo con counters.
- Posibilidad de pausar/reanudar.
- Tracking individual por destinatario.

#### Resultados
- Panel con estadísticas: enviados, respondidos, sin respuesta, fallidos.
- Detalle por destinatario.
- Filtros y export.
- Botón "Duplicar campaña" para re-usar configuración.

### 6.5 Página pública del link

#### Características
- URL: `megarepartos.com.ar/c/{token}` (o subdominio dedicado).
- Token único firmado, expirable.
- Mobile-first, responsive.
- Sin login.
- Branding de la empresa (logo, color).

#### Contenido (para "consulta de pedido")

```
[Logo empresa]
Sodería Las Marías

Hola Juan!

Mañana jueves pasamos. ¿Te llevamos tu pedido?

TU PEDIDO HABITUAL

Bidón 20L
¿Cuántos llenos querés?     [- 2 +]
¿Cuántos vacíos devolvés?   [- 2 +]

──────────

Soda 1.5L
¿Cuántas llenas querés?     [- 1 +]
¿Cuántas vacías devolvés?   [- 1 +]

──────────

¿Querés agregar algo?
[campo de texto libre]

[ ✓ SÍ, PASEN MAÑANA ]
[ ✗ ESTA SEMANA NO ]

Sodería Las Marías
Te atendemos al 351-...
```

#### Comportamiento
- Pedido pre-llenado con productos habituales del cliente.
- Inputs +/- grandes para mobile (mínimo 60x60px).
- Solo retornables muestran "vacíos a devolver".
- Campo texto para observaciones.
- Botón Sí grande, Botón No también grande.
- Si rechaza, pregunta si quiere pausar consultas futuras.

#### Confirmación
Pantalla de éxito con resumen:
```
¡Listo, Juan!

Mañana pasamos con:
  • 2 bidones 20L
  • 1 soda 1.5L

Llevamos para devolución:
  • 2 bidones vacíos
  • 1 soda vacía

Sodería Las Marías
```

#### Rechazo
```
Listo Juan!

No pasamos esta semana.

¿Querés que te pregunte la próxima semana?

[ Sí, preguntame ]
[ Pausá por ahora ]
```

### 6.6 Cobranzas

#### Flujo
1. Usuario va a "Nueva campaña" → tipo "Cobranza".
2. Sistema crea sheet en `Megarepartos/Cobranzas/2026-05-15 - Cobranzas.gsheet`.
3. Usuario rellena con sus morosos (puede pegar desde otro sistema).
4. Vuelve a la app y aprieta "Procesar".
5. Sistema parsea sheet, matchea con clientes, asigna templates por nivel de mora.
6. Preview:
   ```
   Procesado: 47 morosos
   Total adeudado: $1.245.000
   
   Asignación automática:
     1-15 días:  12 clientes → Amable
     16-30 días: 22 clientes → Firme
     30+ días:   13 clientes → Último aviso
   
   3 nombres no matcheados (requieren acción).
   
   [Cancelar] [Enviar todos]
   ```
7. Al confirmar, ejecuta envío vía extensión.

#### Template del sheet de cobranzas

Columnas obligatorias:
- Nombre cliente
- Teléfono (opcional si se matchea por nombre)
- Monto adeudado
- Días de mora

Columnas opcionales:
- Email
- Observación particular

#### Stateless
- Megarepartos NO guarda estado de pagos.
- Cada ronda es independiente.
- Cierre del pago: al día siguiente, cuando se sube nuevo sheet, los que ya no figuran como morosos se asumen pagados.

#### Templates por nivel de mora

**Amable (1-15 días)**:
```
Hola {nombre}! Te escribo de {empresa}.
Quería recordarte que tenés un saldo de ${monto} pendiente.
Cualquier cosa avisame.
CBU: {cbu}
Alias: {alias}
```

**Firme (16-30 días)**:
```
Hola {nombre}, te paso el resumen de tu cuenta.
Saldo pendiente: ${monto}
Días sin pagar: {dias_mora}
Por favor regularizá cuando puedas.
CBU: {cbu}
```

**Último aviso (30+ días)**:
```
{nombre}, tenés una deuda de ${monto} hace {dias_mora} días.
Necesito que regularices esta semana para no suspender el servicio.
CBU: {cbu}
Cualquier cosa, llamame al {telefono_empresa}.
```

Todos los templates editables por la empresa.

### 6.7 Export de pedidos confirmados

Al cierre de una campaña tipo "consulta", el sistema permite exportar los resultados:

#### Sheet "Pedidos confirmados"

Se crea en `Megarepartos/Rutas/2026-05-15 - Pedidos Norte.gsheet`.

Columnas:
- Cliente (nombre)
- Dirección
- Teléfono
- Zona
- Productos a entregar (uno por línea)
- Envases vacíos a recibir
- Observaciones del cliente
- Observaciones permanentes del cliente

Esto es **lo que la sodería usa** para cargar en Reparto de Agua o cualquier sistema que tenga. O imprimir directamente.

#### Sheet "Pedidos rechazados"

Lista de clientes que dijeron "esta semana no" para que la sodería tenga visibilidad.

### 6.8 Panel en vivo durante campaña

Mientras se envía y los clientes responden:

```
CAMPAÑA: Consulta Norte - Jueves 15/05
Estado: Enviando (127/215)

NORTE              CENTRO            SUR
✓ 52   ✗ 8         ✓ 41  ✗ 5         ✓ 38  ✗ 11
⏳ 18              ⏳ 19             ⏳ 23

Últimas confirmaciones:
14:35 — PÉREZ, M (Norte) confirmó
14:33 — LÓPEZ, A (Centro) rechazó: "vacaciones"
14:30 — GARCÍA, J (Sur) confirmó con nota: "después 15h"

[Pausar envío] [Ver pendientes] [Ver confirmados]
```

### 6.9 Manejo de pendientes

Para clientes que no respondieron en X horas:

- Lista de pendientes filtrable.
- Acciones: reenviar, marcar manual (sí/no), descartar.
- Regla por defecto configurable por empresa: "si no responde en 24hs, asumir sí/no/decidir manualmente".

---

## 7. INTEGRACIÓN CON GOOGLE SHEETS

### 7.1 Filosofía

Sheets es **mecanismo de input/output puntual**, no fuente de verdad.

- Datos persistentes (clientes, productos, etc.): viven en nuestra DB, se editan desde la app.
- Datos transaccionales (importación inicial, cobranzas, exports): usan Sheets como interfaz.

### 7.2 OAuth incremental

- Login inicial: solo `email`.
- Cuando se necesita Sheets/Drive: se solicita `drive.file` con popup.
- Scope `drive.file` permite acceso solo a archivos creados por la app, no a todo el Drive.

### 7.3 Estructura de carpetas

```
Mi unidad/
  Megarepartos/
    Clientes/
      2026-05-15 - Importación inicial.gsheet
      2026-05-20 - Agregar lote nuevo.gsheet
    Cobranzas/
      2026-05-15 - Cobranzas.gsheet
      2026-05-22 - Cobranzas.gsheet
    Rutas/
      2026-05-15 - Pedidos Norte.gsheet
      2026-05-15 - Pedidos Centro.gsheet
      2026-05-15 - Pedidos Sur.gsheet
    Encuestas/
      2026-05-30 - Encuesta satisfacción.gsheet
```

### 7.4 Naming convention

Formato: `YYYY-MM-DD - Descripción.gsheet`

Esto permite ordenar alfabéticamente en Drive y obtener orden cronológico natural.

### 7.5 Templates fijos

Cada tipo de sheet tiene template fijo definido por nosotros:

- Importación clientes
- Cobranzas
- Pedidos confirmados (export)
- Pedidos rechazados (export)
- Resultados de encuesta (export)
- Lista de campaña custom (input genérico)

Los templates pueden iterarse en el futuro, pero el usuario no los modifica.

### 7.6 Protección de encabezados

Los encabezados de cada sheet están protegidos (Google Sheets feature nativa). El usuario no puede modificarlos accidentalmente.

### 7.7 Parseo flexible

- Parseo por nombre de columna, no por posición.
- Columnas en blanco se ignoran.
- Si falta una columna obligatoria: error claro al procesar.
- Tolerancia a espacios extra, tildes inconsistentes, mayúsculas/minúsculas.

### 7.8 No eliminación automática

Megarepartos nunca borra sheets del Drive del usuario. Los crea pero la limpieza es responsabilidad del usuario.

---

## 8. EXTENSIÓN CHROME

### 8.1 Propósito

Automatizar el envío masivo de mensajes vía WhatsApp Web del usuario sin necesidad de pagar API de Meta.

### 8.2 Cómo funciona

1. Usuario instala extensión desde Chrome Web Store (unlisted).
2. Al instalar, autoriza vía OAuth con su cuenta Megarepartos.
3. Extensión queda vinculada a la empresa del usuario.
4. Cuando hay una campaña ejecutándose:
   - Extensión recibe lista de mensajes a enviar desde backend.
   - Abre WhatsApp Web en una pestaña.
   - Navega a cada chat individual.
   - Pega el mensaje (resuelve template con variables).
   - Aprieta enter automáticamente.
   - Espera delay aleatorio 3-8 segundos.
   - Pasa al siguiente.
5. Reporta estado al backend en tiempo real.

### 8.3 Características de seguridad

#### Validación contra backend
- Cada envío chequea contra backend: token válido + suscripción activa.
- Si algo falla, se detiene y avisa al usuario.

#### Sesión vinculada
- Solo funciona si el usuario tiene sesión activa en `megarepartos.com.ar` en otra pestaña.
- Lee cookie de sesión, valida con backend.

#### Kill switch
- Backend mantiene lista de tokens revocados.
- Extensión chequea cada hora.
- Si está revocado, deja de funcionar inmediatamente.

#### Límites por plan
- El backend reporta a la extensión cuántos envíos puede hacer según plan.
- Extensión enforce los límites.

#### Ofuscación
- Código ofuscado para dificultar ingeniería inversa.
- Seguridad real está en el backend.

### 8.4 Anti-detección

#### Delays aleatorios
- Entre 3 y 8 segundos entre mensajes.
- Variabilidad para parecer humano.

#### Simulación humana
- Movimientos de mouse simulados antes de cada acción.
- Typing variable (no instantáneo).
- Pausas naturales.

#### Límites de sesión
- Máximo 250 mensajes seguidos.
- Después: pausa obligatoria de 30 minutos.
- Esto evita patrones detectables.

#### Modo lento
- Opcional, configurable.
- Delays mayores (10-20 segundos).
- Para usuarios paranóicos o números nuevos.

### 8.5 Distribución

- Chrome Web Store como extensión "unlisted".
- No aparece en búsquedas.
- Se accede solo con link directo (que damos a clientes pagos).
- Actualizaciones automáticas vía store.

### 8.6 Mantenimiento

- WhatsApp Web cambia DOM cada 2-4 meses.
- Tests automáticos diarios verifican que los selectores siguen funcionando.
- Alertas a Lautaro si rompe.
- Hotfix esperado: 24-48 horas.

### 8.7 UI de la extensión

Popup simple con:
- Estado de conexión (verde/rojo).
- Empresa vinculada.
- Plan actual + límite.
- Botón "Abrir Megarepartos".
- Versión de la extensión.

---

## 9. SISTEMA DE CAMPAÑAS

### 9.1 Tipos de campaña pre-armados

#### Consulta de pedido
- **Tipo**: con link.
- **Destinatarios típicos**: clientes con modalidad "consulta" del día siguiente.
- **Template mensaje**: pregunta + link.
- **Template formulario**: confirmar/modificar pedido habitual con +/-.
- **Output esperado**: lista de pedidos confirmados para esa ruta.

#### Aviso/recordatorio
- **Tipo**: solo mensaje, sin link.
- **Destinatarios típicos**: clientes con modalidad "fijo" del día siguiente.
- **Template mensaje**: "Hola, mañana pasamos a las XX.".
- **Output esperado**: confirmación de envío.

#### Cobranza
- **Tipo**: solo mensaje, sin link.
- **Destinatarios típicos**: morosos (sube sheet).
- **Template mensaje**: monto + CBU/alias + tono según mora.
- **Output esperado**: confirmación de envío.

#### Encuesta
- **Tipo**: con link.
- **Destinatarios típicos**: clientes recientemente atendidos.
- **Template mensaje**: "¿Cómo te atendimos?".
- **Template formulario**: rating + comentario.
- **Output esperado**: respuestas tabuladas.

### 9.2 Permisos

- **Admin**: todo.
- **Operador**: crear, enviar, ver resultados. No borra campañas pasadas.

### 9.3 Estados

- **Borrador**: en armado.
- **Programada**: lista para envío en fecha futura.
- **Enviando**: en ejecución.
- **Enviada**: terminó envío.
- **Cerrada**: ya no se aceptan respuestas (manual o automático tras X días).

### 9.4 Duplicar campaña

Cualquier campaña pasada se puede duplicar para crear una nueva con la misma configuración. El usuario edita lo que cambie (destinatarios actualizados, fecha nueva).

### 9.5 Campañas recurrentes

**No en MVP**. Se evaluará después según pedido de clientes.

---

## 10. SEGURIDAD Y MULTI-TENANT

### 10.1 Capas de defensa

#### Capa 1: Middleware
- Cada request HTTP valida JWT.
- Extrae `usuario_id` y `empresa_id`.
- Inyecta en contexto del request.
- Endpoints toman `empresa_id` del contexto, no de parámetros.

#### Capa 2: Row-Level Security (RLS)
- Habilitado en Postgres.
- Cada tabla con policy que filtra por `empresa_id` del session context.
- Aún si código olvida filtrar, DB rechaza.

#### Capa 3: Repositorios
- Toda interacción con DB pasa por repositorios.
- Repositorios inyectan `empresa_id` automáticamente.
- Sin queries directas en endpoints.

#### Capa 4: Tests de aislamiento
- Por cada endpoint: test que verifica que un usuario de empresa A no puede ver/modificar data de empresa B.
- CI bloquea merges si falla.

#### Capa 5: Auditoría
- Todo acceso a datos sensibles queda en `evento_dominio`.
- Logs centralizados en Cloud Logging.

#### Capa 6: Validación de IDs
- Cuando endpoint recibe ID, valida que pertenezca a la empresa del usuario.
- Devuelve 404 (no 403) para no leak info.

### 10.2 Otras medidas

#### Encryption
- At rest: Neon encrypts by default.
- In transit: HTTPS siempre.

#### Secretos
- Google Secret Manager.
- Nunca en código o env vars expuestas.

#### Rate limiting
- Login: 5 intentos / 5 min.
- API: 100 req/min por usuario.
- Endpoints públicos: 30 req/min por IP.

#### 2FA
- Heredado de Google OAuth (si usuario tiene 2FA en su Google).
- 2FA propio: no en MVP.

#### Logs de seguridad
- Logins exitosos/fallidos.
- Cambios de roles.
- Accesos a datos sensibles.
- Exports masivos.
- Cambios de suscripción.

### 10.3 Eliminación de datos

- **Soft delete por default**: `activo=false`.
- **Hard delete por pedido legal**: anonimización + remoción.
- **Cancelación de suscripción**: 90 días grace, después 90 días congelado, después hard delete + notificación.

### 10.4 Export de datos

- Pantalla "Exportá todos tus datos" en config.
- Genera ZIP con CSVs.
- Disponible siempre, sin demora.

---

## 11. BACKUPS Y DATOS

### 11.1 Backups dobles

- **Neon**: backups automáticos diarios (built-in).
- **Adicional propio**: dump diario a GCS, retención 30 días.
- **Restore test**: mensual automatizado (ver sección 16).

### 11.2 Histórico

- Todo en DB principal por 2-3 años.
- Después: archivado a tabla histórica (no destructivo).

### 11.3 Estadísticas internas (uso por nosotros)

Datos que recolectamos para entender uso:
- Número de campañas por empresa.
- Mensajes enviados.
- Tasa de respuesta.
- Features usadas.
- Errores.

Esto NO se comparte con terceros. Solo para mejorar producto.

---

## 12. PRICING Y PLANES

### 12.1 Planes

| Plan | Precio/mes | Clientes | Usuarios | Target |
|---|---|---|---|---|
| **Inicio** | $30.000 | 150 | 1 | Chico/pueblo |
| **Estándar** | $50.000 | 300 | 2 | Promedio (ancla) |
| **Pro** | $90.000 | 700 | 4 | Mediana (Luciano) |
| **Premium** | $150.000 | Ilimitado | Ilimitado | Grande |

### 12.2 Diferenciadores por plan

Todos los planes incluyen:
- Consultas previas con link único.
- Cobranzas stateless.
- Extensión Chrome.
- Catálogo de productos y clientes.
- Templates personalizables.
- Exportación a Sheets.
- Auditoría.
- Soporte por mail.

Diferenciadores:
- **Pro**: + soporte por WhatsApp (priority).
- **Premium**: + onboarding personal + soporte premium + multi-sucursal (cuando esté).

### 12.3 Políticas

- **Trial gratuito**: 14 días sin tarjeta.
- **Piloto (primeros 5 clientes)**: 50% off por 6 meses.
- **Pago anual**: 10 meses por 12 (descuento ~16%).
- **Sin permanencia**: cancelan cuando quieran, válido hasta fin del mes pagado.
- **Sin setup fee**.
- **Ajuste por IPC**: trimestral.
- **Cambio de plan**: prorrateado.

### 12.4 Cobranza

- **Mensual**: MercadoPago suscripciones.
- **Anual**: transferencia bancaria.
- **Cancelación**: desde la app, efectiva al fin del período pagado.

### 12.5 Pricing piloto

Primeros 5 clientes pagan 50% por 6 meses:
- Inicio: $15.000
- Estándar: $25.000
- Pro: $45.000
- Premium: $75.000

A los 6 meses pasan al precio normal con aviso de 30 días.

---

# PARTE 2: FILOSOFÍA DE DESARROLLO

---

## 13. FILOSOFÍA DE DESARROLLO / VIBE CODING

### 13.1 Contexto

**Lautaro NO va a revisar código línea por línea.** Toda la implementación está delegada a Claude Code. Esto es un side project part-time y necesita compensar la falta de review humano con:

1. **Especificación clara** (este documento).
2. **REQ-IDs ejecutables** vía tests automáticos.
3. **Reglas no negociables** en `CLAUDE.md` del repo.
4. **Estructura de carpetas rígida** que enforce arquitectura.
5. **CI/CD estricto** que bloquea merges sin tests.
6. **Smoke checks locales** que Lautaro corre antes de mergear.

### 13.2 Workflow concreto

Cada feature/cambio sigue el siguiente flujo:

1. **Diseño**: Lautaro y Claude (en chat web/mobile) discuten la feature.
2. **Tarea**: Claude genera un `tareas/TASK-XXX.yaml` con REQ-IDs, archivos a tocar, criterios de aceptación.
3. **Aprobación**: Lautaro revisa la tarea y la commitea al repo.
4. **Implementación**: Lautaro abre Claude Code y le dice "implementá `tareas/TASK-XXX.yaml`".
5. **Claude Code lee**: `CLAUDE.md` (reglas), la tarea, los archivos relevantes.
6. **Implementa**: codifica, crea tests, abre PR.
7. **CI corre**: lint, tests unit, tests integration, tests E2E, checks de arquitectura, checks de cobertura, security audit.
8. **Smoke checks locales**: Lautaro corre `make health` y `make integrity` localmente.
9. **Si todo verde**: Lautaro mergea. Deploy automático a producción.
10. **Tests de regresión**: cualquier bug detectado en producción requiere un test que lo reproduzca antes de fixearlo.

### 13.3 Reglas operativas

- **Feature no se acepta** hasta que Lautaro la usó personalmente al menos una vez.
- **Ningún bug se da por resuelto** sin test de regresión.
- **Ninguna PR sin tests** (CI lo enforce).
- **Ninguna PR sin checks verdes** (branch protection en main).
- **Dependencias en lista blanca**: agregar una nueva requiere justificación en el PR.

### 13.4 Lo que NO se automatiza con API de Claude

Para mantener costo cero del proyecto, NO usamos la API de Claude para:

- ❌ Guardian bot que revisa PRs automáticamente.
- ❌ QA bot diario que prueba la app.
- ❌ Generación automática de tests con LLM.

En su lugar:

- ✅ Claude Code invocado manualmente por Lautaro cuando hace falta (review puntual, debugging visual, análisis semanal).
- ✅ Synthetic monitoring vía Cloud Scheduler cada 30 min (gratis).
- ✅ Tests automáticos exhaustivos (escritos por Claude Code en cada feature).
- ✅ Reporte semanal automático (sin LLM, métricas calculadas).

### 13.5 Compromiso de calidad

Cada feature implementada debe cumplir, sin excepción:

- ✅ Pasa lint (`ruff` + `mypy` + `biome`).
- ✅ Tests unit pasan.
- ✅ Tests integration pasan.
- ✅ Tests E2E pasan (para flujos UI).
- ✅ Coverage del módulo tocado no baja.
- ✅ Cada REQ-ID tiene su test (`@pytest.mark.req("REQ-XXX-001")`).
- ✅ Test de aislamiento multi-tenant para cada endpoint nuevo.
- ✅ Sin secretos en código.
- ✅ Sin dependencias nuevas fuera de la lista blanca.

---

## 14. SISTEMA DE TESTING

### Filosofía

**4 capas, todas automatizables, todas ejecutables sin intervención humana excepto la última.**

### Capa 1: Tests unitarios (`tests/unit/`)

- Foco: lógica de dominio (matching difuso de clientes, generación de campañas, resolución de templates, validaciones).
- Stack: `pytest`, `pytest-asyncio`, `hypothesis` para property-based.
- DB: no usa DB real, todo in-memory o mockeado.
- Velocidad: <5 segundos toda la suite.
- Coverage objetivo: 90%+ en `domain/`.

Ejemplos clave para Megarepartos:
- Matching difuso de clientes por nombre y teléfono.
- Resolución de templates con variables (`{nombre}`, `{monto}`, etc.).
- Validación de teléfonos (formato argentino).
- Lógica de "qué clientes corresponden a la fecha X" según modalidad/frecuencia/día.
- Asignación de templates de cobranza por nivel de mora.
- Validación de transiciones de estado de campaña.
- Generación y validación de tokens firmados.

### Capa 2: Tests de integración API (`tests/integration/`)

- Foco: endpoints completos con DB real.
- Stack: `pytest` + `httpx.AsyncClient` + `testcontainers-python` para Postgres.
- DB: container Postgres efímero por sesión de tests, schema completo aplicado.
- Cada test corre en transacción que se rollbackea al final.
- Velocidad: 1-3 minutos toda la suite.
- Coverage objetivo: **100% de endpoints tienen al menos**:
  - 1 test happy path.
  - 1 test de auth (sin token → 401).
  - 1 test de aislamiento multi-tenant (empresa A no ve datos de empresa B).

Helpers obligatorios:
- `factory_boy` factories para cada entidad de dominio (`EmpresaFactory`, `ClienteFactory`, `ProductoFactory`, etc.).
- Fixture `auth_client(rol="admin", empresa=...)` que retorna httpx client autenticado.
- Fixture `seeded_db(escenario="basico" | "completo")` que carga data demo.

### Capa 3: Tests E2E con Playwright (`tests/e2e/`)

- Foco: flujos completos a través de la UI real.
- Stack: Playwright (Python).
- DB: usa rama de Neon dedicada para tests E2E (creada por CI).
- Viewport mobile (375x667) para la página pública del link.
- Viewport desktop (1280x720) para flujos de admin/oficina.
- Velocidad: 3-10 minutos toda la suite.
- Cada test toma screenshots en hitos clave que quedan como artifacts de CI.

Flujos cubiertos en E2E (mínimo):
- **E2E-01**: login con Google + ver dashboard.
- **E2E-02**: onboarding completo (empresa, productos, zonas, primer cliente).
- **E2E-03**: importar clientes desde sheet de prueba + verificar matching.
- **E2E-04**: crear campaña de consulta + simular envío + cliente accede a link público + confirma pedido + ver respuesta en panel.
- **E2E-05**: crear campaña de cobranza desde sheet + procesar + ver preview con asignaciones.
- **E2E-06**: aislamiento — usuario de empresa A no puede acceder a recursos de empresa B (intenta URLs directas).
- **E2E-07**: cancelación de suscripción + acceso bloqueado tras grace period.

### Capa 4: Smoke checks locales

Comandos que Lautaro corre con `make`:

- **`make health`**: arranca servidor, hace login con Google, crea empresa demo, productos, clientes, una campaña de prueba, simula envío, verifica respuesta del link, limpia. Si pasa, el sistema base está vivo.
- **`make integrity`**: corre validaciones de integridad sobre la DB local:
  - Clientes sin empresa.
  - Mensajes enviados sin campaña.
  - Tokens públicos expirados que siguen activos.
  - Usuarios sin método de auth válido.
  - Sheets en DB sin existir en Drive.
- **`make security-check`**: corre suite específica de aislamiento multi-tenant.
- **`make smoke-mobile`**: arranca Playwright en viewport mobile, ejecuta flujo del link público con cliente de prueba, screenshots a `tests/screenshots/`.

### Tests obligatorios por feature

Regla codificada en CI:

> Si un PR toca `domain/X.py` o `api/X.py`, debe haber cambios en `tests/unit/test_X.py` o `tests/integration/test_X.py`.

Detector: script `scripts/check_test_coverage_changes.py` corrido en CI.

### Behavior coverage

Cada archivo en `behaviors/` lista REQ-IDs. Cada REQ-ID debe tener al menos un test que lo verifique (vía marker pytest):

```python
@pytest.mark.req("REQ-CAMP-001")
def test_campana_no_se_envia_sin_destinatarios(...): ...
```

Comando: `make behavior-coverage` lista REQs sin test. Falla CI si hay alguno.

### Property-based tests para invariantes

Usar `hypothesis` para invariantes del modelo:

- Para cualquier conjunto de clientes y filtros, el resultado siempre incluye solo clientes que cumplen TODOS los filtros aplicados.
- Resolver un template con variables siempre produce string válido (sin variables sin resolver).
- Generar un token + validarlo inmediatamente siempre da true.
- Generar un token + esperar TTL + validarlo da false (expirado).
- Para cualquier sheet bien formado, parsearlo es idempotente (parsear dos veces da el mismo resultado).

### Mutation testing (semanal)

Job cron en CI semanal con `mutmut`. Reporta mutaciones que no fueron detectadas por tests. No falla CI, solo informa.

### Tests de regresión por bug

Regla operativa: **ningún bug se da por resuelto sin agregar un test que lo reproduzca y verifique el fix**.

Estos tests se ubican en `tests/regression/test_bug_XXX.py` con referencia al issue/incidente.

### Tests específicos de la extensión Chrome

Como la extensión depende de DOM de WhatsApp Web (que cambia), tiene su propio régimen:

- **Tests unitarios** de la lógica interna (sin DOM).
- **Test diario automatizado** (Playwright contra WhatsApp Web staging):
  - Verifica que selectores DOM siguen funcionando.
  - Falla → alerta a Lautaro.
  - Cron: 06:00 ART.

---

## 15. OBSERVABILIDAD

### Tres capas

1. **Logs técnicos** (`structlog` → stdout → GCP Cloud Logging): requests, errores, métricas técnicas.
2. **Eventos de dominio** (Postgres `evento_dominio`): qué hizo cada usuario, persistente, consultable.
3. **Métricas de producto** (Postgres queries → dashboard interno): MRR, churn, uso por feature.

### Logs técnicos

Stack: `structlog` con procesador JSON, stdout, recogido por Cloud Logging.

Cada log lleva contexto:
```json
{
  "timestamp": "2026-05-15T12:30:00Z",
  "level": "info",
  "request_id": "req_abc123",
  "empresa_id": "uuid",
  "usuario_id": "uuid",
  "usuario_rol": "admin",
  "endpoint": "POST /api/campanas",
  "status": 201,
  "duracion_ms": 145,
  "msg": "campaña creada"
}
```

Middleware FastAPI:
- Genera `request_id` (UUID) por cada request.
- Inyecta contexto (`empresa_id`, `usuario_id`, `rol`) desde JWT.
- Loggea inicio y fin de cada request con duración.
- Loggea errores con stack trace.

Niveles:
- `DEBUG`: solo en desarrollo local.
- `INFO`: requests normales, eventos importantes.
- `WARNING`: cosas raras no críticas (rate limit, validación fallida).
- `ERROR`: excepciones, fallos.
- `CRITICAL`: corrupción, security breach, datos inconsistentes detectados.

### Eventos de dominio

Ya cubierto en sección 5. Cada operación de escritura genera evento. Consultable por dueño de cada empresa vía `/api/eventos`.

Ejemplos de eventos:
- `cliente.creado`, `cliente.modificado`, `cliente.desactivado`.
- `campana.creada`, `campana.enviada`, `campana.cerrada`.
- `mensaje.enviado`, `mensaje.fallido`.
- `respuesta.recibida`.
- `sheet.importado`, `sheet.exportado`.
- `usuario.invitado`, `usuario.rol_cambiado`.
- `suscripcion.cambiada`, `suscripcion.cancelada`.

### Métricas de producto

Calculadas on-demand desde Postgres. Endpoints internos (no para clientes):

- `/admin-interno/metrics/mrr`: MRR estimado por empresa.
- `/admin-interno/metrics/active-users`: usuarios activos últimos 7/30 días por empresa.
- `/admin-interno/metrics/feature-usage`: uso de cada feature (campañas creadas, sheets generados, etc.).
- `/admin-interno/metrics/health-by-tenant`: por empresa, qué tan saludable está su uso (señales de churn).
- `/admin-interno/metrics/extension-status`: cuántas extensiones activas por empresa.

Acceso restringido a Lautaro (email hardcoded en config + check específico en middleware).

### Alertas

Cloud Monitoring + email a Lautaro:
- Uptime check cada 5 min: si falla 2 veces seguidas, alerta.
- Tasa de error 5xx > 1% en 5 min: alerta.
- Latency p95 > 3 segundos en 5 min: alerta.
- Cron jobs que fallan: alerta.
- Test diario de extensión falla: alerta crítica.

No usamos Sentry (suma servicio, free tier limitado). Cloud Logging + Cloud Monitoring alcanza.

### Synthetic monitoring

Cloud Scheduler corre cada 30 min:
- Health check completo: login con cuenta de monitoring, hace request, verifica respuesta.
- Synthetic transaction: crea campaña en empresa de monitoring, genera link, accede vía Playwright headless, verifica respuesta.

Si falla, alerta.

### Dashboard interno

Página simple `/admin-interno/dashboard` (auth solo Lautaro) con:
- Resumen del día: empresas activas, requests, errores, campañas creadas, mensajes enviados.
- Top empresas por uso.
- Alertas activas.
- Últimos errores.
- Estado de la extensión Chrome (versiones desplegadas, tests diarios).

---

## 16. MANTENIMIENTO

### Backups

Cloud Scheduler nocturno (3 AM Argentina):
1. Job ejecuta `pg_dump` contra Neon (Cloud Run job efímero).
2. Sube dump a `gs://megarepartos-backups/YYYY/MM/DD.sql.gz`.
3. Retención: 30 días en bucket estándar, después se borran (Cloud Storage lifecycle policy).

Restore test mensual:
- Job: baja último backup, lo restaura en branch nuevo de Neon, corre `make integrity`.
- Si pasa, OK. Si no, alerta.

### Cleanup automático

Cron diario (4 AM):
- Magic links expirados > 7 días se borran.
- Tokens públicos de campañas expirados > 30 días se invalidan.
- Sesiones JWT cuyo refresh expiró se limpian.
- Sheets registrados en DB pero borrados del Drive se marcan como `archivado`.

Cron mensual:
- Eventos de dominio > 2 años se archivan a Cloud Storage (CSV comprimido), se eliminan de Postgres.
- Mensajes enviados > 1 año se archivan también (mantenemos el agregado por campaña).

### Auto-update de dependencias

Dependabot configurado:
- Backend: weekly, agrupa minor/patch, auto-merge si CI verde.
- Frontend: weekly, agrupa minor/patch, auto-merge si CI verde.
- Extensión Chrome: weekly, manual review (cambios pueden romper anti-detección).
- Major updates: PR queda abierto para revisión manual.
- Security updates: prioridad máxima, alerta vía email.

### pip-audit / npm audit

CI corre en cada PR:
- `pip-audit` en backend.
- `npm audit --audit-level=moderate` en frontend.
- `npm audit --audit-level=moderate` en extensión.
- Si hay CVE high o critical, falla CI.

### Política de versionado

- `main` siempre deployable.
- Tags semver: v0.1.0, v0.2.0, etc.
- Cada deploy a prod genera tag automático.
- CHANGELOG.md auto-mantenido vía commits convencionales (`feat:`, `fix:`, `chore:`, etc.).

### Política de PRs

- Branch protection en `main`: no commit directo, solo via PR.
- Checks obligatorios en CI:
  - `lint` (ruff + mypy + biome para frontend).
  - `test-unit`.
  - `test-integration`.
  - `test-e2e` (puede ser opcional para PRs pequeñas con label `skip-e2e`).
  - `check-arquitectura`.
  - `check-test-coverage-changes`.
  - `behavior-coverage`.
  - `pip-audit / npm-audit`.

### Reporte semanal automático

Cron lunes 9 AM:
- Genera markdown con métricas de la semana (PRs mergeados, deploys, MRR, errores, alertas, tests del extension, clientes activos).
- Lo guarda en `gs://megarepartos-reports/YYYY-WW.md`.
- Manda email a Lautaro.

---

## 17. ESTRUCTURA DEL REPO

```
megarepartos/
├── README.md
├── CLAUDE.md                    # Reglas para Claude Code
├── CHANGELOG.md
├── Makefile                     # Comandos canónicos
├── .gitignore
├── .env.example
├── docker-compose.yml           # Postgres local para dev
├── Dockerfile                   # Backend image
├── pyproject.toml               # Root config
│
├── .github/
│   └── workflows/
│       ├── ci.yml               # Cada PR
│       ├── deploy-prod.yml      # Push a main
│       ├── nightly.yml          # Cron diario
│       └── extension-test.yml   # Cron diario de extensión
│
├── docs/
│   ├── MEGAREPARTOS_SPEC.md     # Este documento
│   ├── ARCHITECTURE.md          # Decisiones técnicas detalladas
│   ├── DEVELOPMENT.md           # Cómo desarrollar localmente
│   ├── ONBOARDING.md            # Cómo onboardear nuevos clientes
│   └── RUNBOOK.md               # Qué hacer si X cosa falla
│
├── behaviors/                   # REQ-IDs como specs ejecutables
│   ├── _template.md
│   ├── auth.md
│   ├── empresa.md
│   ├── clientes.md
│   ├── productos.md
│   ├── zonas.md
│   ├── campanas.md
│   ├── cobranzas.md
│   ├── sheets.md
│   ├── extension.md
│   └── multi_tenant.md
│
├── tareas/                      # TASK-XXX.yaml de cada feature
│   ├── _template.yaml
│   ├── TASK-000-setup.yaml
│   └── ...
│
├── scripts/
│   ├── check_arquitectura.py    # AST parsing de reglas no negociables
│   ├── check_test_coverage_changes.py
│   ├── behavior_coverage.py
│   ├── seed_demo.py
│   └── restore_test.py
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_schema_inicial.py
│   ├── src/megarepartos/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Pydantic settings
│   │   ├── infra/
│   │   │   ├── db.py            # SQLAlchemy async engine
│   │   │   ├── logging.py       # structlog setup
│   │   │   ├── auth.py          # JWT + Google OAuth
│   │   │   └── deps.py          # FastAPI dependencies
│   │   ├── models/              # SQLAlchemy models (DB)
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── empresa.py
│   │   │   ├── usuario.py
│   │   │   ├── cliente.py
│   │   │   ├── producto.py
│   │   │   ├── zona.py
│   │   │   ├── campana.py
│   │   │   ├── mensaje.py
│   │   │   ├── respuesta.py
│   │   │   ├── template.py
│   │   │   ├── sheet.py
│   │   │   └── evento.py
│   │   ├── schemas/             # Pydantic models (API)
│   │   │   ├── __init__.py
│   │   │   ├── empresa.py
│   │   │   ├── cliente.py
│   │   │   └── ...
│   │   ├── api/                 # FastAPI routers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── empresa.py
│   │   │   ├── clientes.py
│   │   │   ├── productos.py
│   │   │   ├── zonas.py
│   │   │   ├── campanas.py
│   │   │   ├── sheets.py
│   │   │   ├── extension.py
│   │   │   ├── publico.py       # Página del link, sin auth
│   │   │   └── admin_interno.py
│   │   ├── domain/              # Lógica de negocio pura
│   │   │   ├── __init__.py
│   │   │   ├── _events.py       # event_recorder
│   │   │   ├── clientes.py
│   │   │   ├── campanas.py
│   │   │   ├── templates.py     # Resolución de variables
│   │   │   ├── matching.py      # Fuzzy matching
│   │   │   ├── cobranzas.py     # Asignación por mora
│   │   │   └── tokens.py        # Generación y validación
│   │   ├── integrations/
│   │   │   ├── google_drive.py
│   │   │   ├── google_sheets.py
│   │   │   ├── google_maps.py   # Geocoding
│   │   │   └── mercadopago.py
│   │   └── services/            # Servicios de alto nivel
│   │       ├── importar_clientes.py
│   │       ├── procesar_cobranzas.py
│   │       └── enviar_campana.py
│   └── tests/
│       ├── conftest.py
│       ├── factories.py
│       ├── unit/
│       │   ├── test_matching.py
│       │   ├── test_templates.py
│       │   ├── test_cobranzas.py
│       │   └── ...
│       ├── integration/
│       │   ├── test_clientes_api.py
│       │   ├── test_campanas_api.py
│       │   ├── test_aislamiento.py  # CRÍTICO
│       │   └── ...
│       ├── e2e/
│       │   ├── test_onboarding.py
│       │   ├── test_consulta_completa.py
│       │   └── ...
│       └── regression/
│           └── (uno por bug histórico)
│
├── frontend/                    # App web (admin/operador)
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   ├── public/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                 # Cliente HTTP, hooks de React Query
│   │   ├── components/
│   │   │   ├── ui/              # Botón, Input, Modal, etc.
│   │   │   └── ...
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Clientes.tsx
│   │   │   ├── Campanas.tsx
│   │   │   ├── publico/         # Página del link (sin auth)
│   │   │   │   └── Link.tsx
│   │   │   └── ...
│   │   ├── hooks/
│   │   ├── stores/              # Zustand
│   │   ├── lib/
│   │   │   ├── google.ts        # OAuth, Drive helpers
│   │   │   └── format.ts
│   │   └── styles/
│   └── tests/                   # Vitest + RTL
│
├── extension/                   # Extensión Chrome
│   ├── package.json
│   ├── webpack.config.js
│   ├── manifest.json
│   ├── src/
│   │   ├── background/
│   │   │   └── index.ts
│   │   ├── content/
│   │   │   ├── whatsapp.ts      # DOM manipulation
│   │   │   └── selectors.ts     # Selectores centralizados
│   │   ├── popup/
│   │   │   ├── index.tsx
│   │   │   └── App.tsx
│   │   └── shared/
│   │       ├── api.ts           # Comunicación con backend
│   │       └── types.ts
│   └── tests/
│       ├── unit/
│       └── e2e/                 # Test diario contra WhatsApp Web
│
└── infra/                       # Terraform / scripts de infra
    ├── README.md
    └── ...
```

### Reglas de estructura

- **`api/` NO importa de `models/`**: solo de `domain/`, `schemas/`, `infra/auth`.
- **`domain/` NO importa de `api/` ni `schemas/`**: es lógica pura.
- **`models/` NO importa de nada del proyecto**: solo SQLAlchemy.
- **Mutaciones de DB críticas** (mensajes enviados, tokens) **solo desde `domain/`**.
- **Cada operación de escritura usa `event_recorder`** de `domain/_events.py`.

Estas reglas se enforce vía `scripts/check_arquitectura.py` que parsea AST y falla CI si se violan.

---

## 18. CI/CD

### Workflow `ci.yml` (cada PR)

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]

jobs:
  lint:
    # ruff + mypy en backend
    # biome en frontend
    # eslint en extensión
  
  test-unit:
    # pytest tests/unit (backend)
    # vitest (frontend)
  
  test-integration:
    # pytest tests/integration con Postgres testcontainer
  
  test-e2e:
    # Playwright contra preview deploy
  
  check-arquitectura:
    # python scripts/check_arquitectura.py
  
  check-tests-changed:
    # python scripts/check_test_coverage_changes.py
  
  behavior-coverage:
    # python scripts/behavior_coverage.py
  
  security:
    # pip-audit + npm-audit (backend + frontend + extension)
  
  build:
    # docker build (no push en PR)
    # frontend build
    # extension build
```

Branch protection: todos los jobs deben pasar antes de mergear.

### Workflow `deploy-prod.yml` (push a main)

```yaml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    steps:
      - Build Docker image
      - Push to Artifact Registry (us-central1)
      - Run alembic migrate (Cloud Run job)
      - Deploy to Cloud Run
      - Smoke test post-deploy
      - Tag release vYY.MM.DD
      - Notify (email a Lautaro)
  
  deploy-frontend:
    steps:
      - Build con Vite
      - Upload a Cloud Storage
      - Invalidate CDN cache
  
  deploy-extension:
    # Manual trigger only (Chrome Web Store no se actualiza solo)
    if: workflow_dispatch
    steps:
      - Build con webpack
      - Crear ZIP
      - Subir a Chrome Web Store (manual review)
```

### Workflow `nightly.yml` (cron)

```yaml
name: Nightly
on:
  schedule:
    - cron: '0 6 * * *'  # 03:00 ART
jobs:
  mutation-tests:
    # mutmut, informa, no falla
  
  restore-test:
    # baja último backup, restaura en branch Neon, corre integrity
  
  archive-eventos:
    # archivado de eventos > 2 años
  
  reporte-semanal:
    # solo lunes, genera reporte y lo manda por email
```

### Workflow `extension-test.yml` (cron diario)

```yaml
name: Extension Daily Test
on:
  schedule:
    - cron: '0 9 * * *'  # 06:00 ART

jobs:
  test-selectors:
    # Playwright headed contra WhatsApp Web staging
    # Verifica que selectores DOM siguen funcionando
    # Si falla, alerta crítica a Lautaro
```

### Preview deployments

Cada PR genera:
1. Branch nueva de Neon (`pr-{number}`).
2. Deploy a Cloud Run service efímero (`megarepartos-pr-{number}`).
3. URL preview comentada en el PR.
4. E2E corre contra esa URL.

Al cerrar PR: branch Neon y Cloud Run efímeros se destruyen.

---

## 19. CLAUDE.md (REGLAS DE CODEO)

> Este archivo va en el root del repo. Claude Code lo lee automáticamente.

```markdown
# CLAUDE.md — Reglas del proyecto Megarepartos

## Contexto

Megarepartos es una plataforma de campañas de WhatsApp para negocios de reparto recurrente.
Backend Python (FastAPI + SQLAlchemy 2 async + Postgres).
Frontend React (Vite + TS + Tailwind).
Extensión Chrome propia que controla WhatsApp Web del usuario.

La especificación completa está en `docs/MEGAREPARTOS_SPEC.md`. Léela si necesitás contexto
sobre arquitectura, modelo de datos, o flujos.

## Workflow

1. Toda feature nueva nace como `tareas/TASK-XXX.yaml`.
2. Si no existe el TASK.yaml, pedímelo antes de codear.
3. Trabajá en una rama `feature/TASK-XXX-descripcion-corta`.
4. Al terminar, abrí PR. CI tiene que pasar todo.
5. Si CI rompe, debuggá y arreglalo antes de pedir review.

## Reglas no negociables

### Backend

1. **Multi-tenancy SIEMPRE**: toda query a tablas de negocio filtra por `empresa_id` del
   usuario logueado. Sin excepciones. Si no podés filtrar (caso público con token), justificalo
   en el código con un comentario explícito.

2. **Toda operación de escritura usa `event_recorder`**: importá desde `domain/_events.py`
   y envolvé la operación. Genera el `evento_dominio` automáticamente.

3. **Mutaciones de mensajes enviados solo desde `domain/campanas.py`**: ningún otro archivo
   puede hacer INSERT en `mensaje_enviado`. Si necesitás registrar un envío, llamá a la
   función correspondiente.

4. **Tokens firmados solo desde `domain/tokens.py`**: generación, validación y revocación.

5. **API solo en `api/*.py`, lógica solo en `domain/*.py`**: los endpoints validan input
   y delegan. Nada de lógica de negocio en endpoints.

6. **`api/*.py` NO importa de `models/`**: solo de `domain/`, `schemas/`, `infra/auth`.

7. **`domain/*.py` NO importa de `api/` ni `schemas/`**: es lógica pura.

8. **Async siempre**: FastAPI + SQLAlchemy 2 async. Nada de DB calls sincrónicos.

9. **Idempotencia en endpoints críticos**: POST `/api/campanas/{id}/enviar` y similares
   aceptan header `Idempotency-Key` y dedupean.

10. **Errores con códigos estándar**: 400 (validación), 401 (no auth), 403 (sin permiso),
    404 (no existe), 409 (conflicto), 422 (semántico), 500 (server). Body siempre
    `{error: {code, message, details}}`.

11. **Página pública del link**: NO requiere auth pero valida token firmado.
    Endpoint `/api/publico/c/{token}` es la única excepción a multi-tenancy normal.

12. **Comunicación con la extensión**: endpoints en `/api/extension/*` requieren
    `X-Extension-Token` header válido.

### Frontend

1. **TanStack Query para todo lo que viene del server**: nada de `useEffect + fetch`.
2. **Zustand solo para estado cliente**: nunca para datos del server.
3. **Tailwind solo, sin CSS modules ni styled-components**.
4. **Componentes UI reusables en `components/ui/`**: Button, Input, Modal, etc. Variantes vía props.
5. **Mobile-first para `pages/publico/*`**: viewport 375px como base.
6. **Google OAuth via `lib/google.ts`**: nunca llamar SDK directo desde componentes.
7. **Variables de campañas resueltas en backend**: frontend nunca renderiza placeholders.

### Extensión

1. **Selectores DOM centralizados en `content/selectors.ts`**: nunca hardcoded en otros archivos.
2. **Delays aleatorios obligatorios**: nunca enviar dos mensajes sin pausa de 3-8s.
3. **Validación contra backend en cada envío**: si falla, detener inmediatamente.
4. **No leer cookies fuera de WhatsApp Web y Megarepartos**: privacy.
5. **Sin telemetría externa**: solo nuestro backend.

### Tests

1. **Toda feature tiene test**: si tocás `domain/X.py` o `api/X.py`, tenés que tocar
   `tests/.../test_X.py`.
2. **REQ-IDs del `behaviors/X.md` se mapean a tests vía `@pytest.mark.req("REQ-X-001")`**.
3. **Tests de integración corren contra Postgres real** (testcontainer).
4. **Property-based tests para invariantes**: usar hypothesis.
5. **Mínimo en cada API endpoint**: 1 happy path + 1 auth + 1 aislamiento multi-tenant.
6. **Bug fixes requieren test de regresión** en `tests/regression/`.

### Dependencias

1. **No agregar librerías sin justificación**: si necesitás una nueva, explicala en el PR.
2. **Lista blanca** (puedo agregar otras con justificación):
   - **Backend**: fastapi, sqlalchemy, alembic, pydantic, pydantic-settings, structlog,
     httpx, pytest, pytest-asyncio, hypothesis, factory-boy, testcontainers, asyncpg,
     python-jose, python-multipart, google-auth, google-api-python-client, mercadopago.
   - **Frontend**: react, react-dom, react-router-dom, @tanstack/react-query, zustand,
     axios, date-fns, lucide-react, vite-plugin-pwa, react-hook-form, zod, @headlessui/react.
   - **Extensión**: webpack, typescript, react (popup), zod.

## Commits

Convención: `tipo(scope): mensaje` en español.

- `feat(campanas): agrega endpoint POST /api/campanas/{id}/enviar`
- `fix(matching): corrige fuzzy matching cuando hay tildes`
- `test(cobranzas): cubre REQ-COBR-007`
- `docs(spec): actualiza sección 9`
- `chore(deps): actualiza fastapi`

## Comandos canónicos

- `make dev`: arranca backend + frontend local con Postgres en Docker.
- `make test`: corre todos los tests.
- `make test-fast`: corre unit + integration, skipea E2E.
- `make lint`: ruff + mypy + biome.
- `make health`: smoke test completo.
- `make integrity`: validaciones de integridad sobre DB local.
- `make security-check`: aislamiento multi-tenant.
- `make seed-demo`: carga data demo en DB local.
- `make migrate`: alembic upgrade head.
- `make migration-new "descripcion"`: alembic revision --autogenerate.
- `make extension-dev`: arranca extensión en modo dev (watch mode).
- `make extension-build`: build de producción de la extensión.

## Catálogo de errores estándar

Códigos de error que retorna la API. Definir constantes en `infra/errors.py`.

- `AUTH_REQUIRED`: 401 — no se proveyó token.
- `AUTH_INVALID`: 401 — token inválido o expirado.
- `PERMISO_DENEGADO`: 403 — usuario sin permiso para esta acción.
- `RECURSO_NO_ENCONTRADO`: 404 — entidad no existe o no pertenece a tu empresa.
- `VALIDACION_INPUT`: 400 — body o query params mal formados.
- `VALIDACION_SEMANTICA`: 422 — input válido pero viola regla de negocio.
- `CONFLICTO_ESTADO`: 409 — operación no válida en el estado actual.
- `LIMITE_PLAN`: 402 — superó el límite de su plan.
- `RATE_LIMIT`: 429 — demasiadas requests.
- `EXTERNO_FALLO`: 503 — falló dependencia externa (Google, MercadoPago).
- `INTERNO`: 500 — error inesperado del servidor.

## Cuando dudes

Si tenés duda sobre una decisión de diseño, **preguntá antes de implementar**. Mejor
5 minutos de pregunta que 2 horas de rehacer.

Especialmente preguntá si:
- La feature parece ambigua respecto al SPEC.
- Una dependencia nueva podría ser útil.
- Hay tradeoff entre simplicidad y robustez.
- Una decisión podría afectar la performance o el costo de infra.
```

---

## 20. SISTEMA DE TAREAS (TAREA.YAML)

### Template

`tareas/_template.yaml`:

```yaml
# Identificación
id: TASK-XXX
nombre: ""
tipo: feature  # feature | bugfix | refactor | docs | infra
sprint: 0
prioridad: media  # alta | media | baja

# Contexto
contexto: |
  Por qué se necesita esto. Qué problema resuelve.

# Comportamiento esperado (se vuelca a behaviors/X.md)
comportamiento:
  - "REQ-XXX-001: descripción del requisito"
  - "REQ-XXX-002: otro requisito"

no_debe:
  - "Cosa que no debe hacer"

# Archivos
archivos_nuevos: []
archivos_a_modificar: []
archivos_NO_tocar: []

# Tests
tests:
  - "test_REQ_XXX_001_descripcion"

# Aceptación
aceptacion:
  - "make test verde"
  - "make check-arquitectura verde"
  - "make behavior-coverage verde"

# Dependencias
depende_de: []

# Notas
notas: |
  Cualquier contexto adicional.
```

### Ejemplo completo: TASK-000 (setup inicial)

```yaml
id: TASK-000
nombre: "Setup inicial del proyecto Megarepartos"
tipo: infra
sprint: 0
prioridad: alta

contexto: |
  Crear el andamiaje del proyecto: estructura de carpetas según sección 17 del SPEC,
  configs base, Docker para dev local, CI inicial, conexión a Neon, primer endpoint
  /health. Esta tarea es prerrequisito de todas las demás.

comportamiento:
  - "REQ-SETUP-001: Existe `docker-compose.yml` que levanta Postgres local en localhost:5432."
  - "REQ-SETUP-002: `make dev` arranca backend en localhost:8000 y frontend en localhost:5173."
  - "REQ-SETUP-003: GET /health retorna 200 con {status: ok, db: ok}."
  - "REQ-SETUP-004: Alembic configurado, primera migración crea schema completo de SPEC sección 5."
  - "REQ-SETUP-005: pytest configurado y `make test` corre sin tests (suite vacía pasa)."
  - "REQ-SETUP-006: Conexión a Neon configurable via NEON_DATABASE_URL env var."
  - "REQ-SETUP-007: Frontend Vite arranca con TypeScript y Tailwind configurados."
  - "REQ-SETUP-008: Página `/` muestra 'Megarepartos - en construcción' (stub)."
  - "REQ-SETUP-009: Existe CLAUDE.md con contenido de sección 19 del SPEC."
  - "REQ-SETUP-010: Existe .github/workflows/ci.yml que ejecuta lint+test+build."
  - "REQ-SETUP-011: Existe `scripts/check_arquitectura.py` (puede estar vacío, solo placeholder)."
  - "REQ-SETUP-012: Existe `behaviors/_template.md` con estructura base."
  - "REQ-SETUP-013: Existe `tareas/_template.yaml` con estructura base."

no_debe:
  - "Implementar features de negocio. Solo setup."
  - "Usar SQLAlchemy sincrónico."
  - "Agregar librerías fuera de la lista blanca de CLAUDE.md."
  - "Tocar la carpeta `extension/` (se hace en TASK posterior)."

archivos_nuevos:
  - "README.md"
  - "CLAUDE.md"
  - "CHANGELOG.md"
  - "Makefile"
  - ".gitignore"
  - ".env.example"
  - "docker-compose.yml"
  - "Dockerfile"
  - ".github/workflows/ci.yml"
  - "backend/pyproject.toml"
  - "backend/alembic.ini"
  - "backend/alembic/env.py"
  - "backend/alembic/versions/0001_schema_inicial.py"
  - "backend/src/megarepartos/main.py"
  - "backend/src/megarepartos/config.py"
  - "backend/src/megarepartos/infra/db.py"
  - "backend/src/megarepartos/infra/logging.py"
  - "backend/src/megarepartos/api/__init__.py"
  - "backend/src/megarepartos/models/__init__.py"
  - "backend/src/megarepartos/models/base.py"
  - "backend/src/megarepartos/models/empresa.py"
  - "backend/src/megarepartos/models/usuario.py"
  - "backend/src/megarepartos/models/cliente.py"
  - "backend/src/megarepartos/models/producto.py"
  - "backend/src/megarepartos/models/zona.py"
  - "backend/src/megarepartos/models/campana.py"
  - "backend/src/megarepartos/models/mensaje.py"
  - "backend/src/megarepartos/models/template.py"
  - "backend/src/megarepartos/models/sheet.py"
  - "backend/src/megarepartos/models/evento.py"
  - "backend/tests/conftest.py"
  - "frontend/package.json"
  - "frontend/tsconfig.json"
  - "frontend/vite.config.ts"
  - "frontend/tailwind.config.js"
  - "frontend/index.html"
  - "frontend/src/main.tsx"
  - "frontend/src/App.tsx"
  - "scripts/check_arquitectura.py"
  - "scripts/check_test_coverage_changes.py"
  - "scripts/behavior_coverage.py"
  - "behaviors/_template.md"
  - "tareas/_template.yaml"
  - "docs/MEGAREPARTOS_SPEC.md"
  - "docs/ARCHITECTURE.md"
  - "docs/DEVELOPMENT.md"

archivos_a_modificar: []
archivos_NO_tocar:
  - "extension/**"  # No tocar aún

tests:
  - "test_health_endpoint_responde_200"
  - "test_health_db_responde_ok_con_conexion_valida"

aceptacion:
  - "make dev arranca sin errores"
  - "GET http://localhost:8000/health retorna {status: ok, db: ok}"
  - "GET http://localhost:5173/ muestra 'Megarepartos - en construcción'"
  - "make test pasa (suite vacía)"
  - "make lint pasa"
  - "alembic upgrade head crea todas las tablas del schema"
  - "CI pasa todos los checks"

depende_de: []

notas: |
  Esta tarea define la base. Tomate tiempo para hacerla bien.
  Cuando termines, todas las tareas siguientes asumen este estado.
  
  El schema SQL de la sección 5 del SPEC va completo en la primera migración
  (0001_schema_inicial.py). No partir en varias migraciones.
  
  La extensión Chrome NO se toca en esta tarea. Es TASK posterior.
```

### Cómo se usa

1. **Lautaro describe** en lenguaje natural lo que quiere.
2. **Claude (en chat web/mobile)** genera el `tarea.yaml` con REQ-IDs específicos.
3. **Lautaro lo aprueba** y commitea al repo en `tareas/TASK-XXX.yaml`.
4. **Lautaro abre Claude Code** y le dice: "implementá `tareas/TASK-XXX.yaml`".
5. **Claude Code lee** la tarea + `CLAUDE.md` + archivos relevantes, implementa.
6. **Claude Code abre PR** con tests incluidos.
7. **CI corre** todos los checks.
8. **Si todo verde**, Lautaro mergea. Deploy automático.

### TASKs planeados para el sprint 0 y 1

Lista inicial de tasks. Claude (en chat) los irá detallando uno por uno:

- **TASK-000**: Setup inicial (definido arriba).
- **TASK-001**: Auth con Google OAuth (login básico, JWT, refresh).
- **TASK-002**: Modelo `empresa` + `usuario` + creación al primer login.
- **TASK-003**: Multi-tenant middleware + RLS Postgres.
- **TASK-004**: Repositorios base con `empresa_id` automático.
- **TASK-005**: Auditoría base (`evento_dominio` + `event_recorder`).
- **TASK-006**: Tests de aislamiento como suite base.
- **TASK-007**: Roles admin/operador + control de acceso por endpoint.

---

# PARTE 3: OPERACIÓN

---

## 21. CONVENCIONES DE CÓDIGO

### 21.1 Naming

#### Idioma
- **Dominio** (modelos, lógica de negocio): **español**. Ej `Cliente`, `Producto`, `Campana`, `Zona`, `MensajeEnviado`.
- **Infraestructura técnica**: **inglés**. Ej `Repository`, `AuthMiddleware`, `BaseModel`, `Settings`.

#### Convenciones técnicas
- **Python**: snake_case para variables/funciones, PascalCase para clases.
- **TypeScript**: camelCase para vars/funciones, PascalCase para tipos/componentes.
- **DB**: snake_case (Postgres standard).
- **URLs API**: kebab-case en español. Ej `/api/clientes`, `/api/campanas`, `/api/zonas`.

#### Ejemplos de nombres
- ✅ `Cliente`, `crear_cliente()`, `obtener_clientes_por_zona()`.
- ✅ `BaseModel`, `Repository`, `Settings`, `AuthMiddleware`.
- ✅ `/api/campanas/{id}/enviar`.
- ❌ `Customer`, `getCustomersByZone` (no usamos inglés en dominio).
- ❌ `crear_Cliente` (mezcla convenciones).

### 21.2 Logging

- **structlog** con JSON output.
- **Cada request** tiene `request_id` único.
- **Eventos importantes** se loggean a INFO con contexto.
- **Errores** a ERROR con stack trace.
- **Sin datos sensibles** en logs (passwords, tokens completos, datos personales completos).

### 21.3 Comentarios

- **Cuándo SÍ comentar**:
  - Decisión no obvia ("usamos lock pesimista acá porque X").
  - Excepciones a reglas no negociables (con justificación).
  - Workarounds temporales (con link a issue).
  - TODOs con issue asociado.
- **Cuándo NO comentar**:
  - Para explicar QUÉ hace el código (eso es nombre).
  - Para repetir lo que dice el código.

### 21.4 Idempotencia

Endpoints que pueden ser llamados múltiples veces sin querer (envíos, cobranzas) aceptan `Idempotency-Key` header. El backend mantiene tabla de keys con TTL 24h.

### 21.5 Versionado de API

- API versionada con `/api/v1/...`.
- Cambios incompatibles requieren `/api/v2/...` con `v1` deprecada gradualmente.
- En MVP solo hay v1.

### 21.6 Configuración

- Toda config vía env vars (`.env` local, Secret Manager prod).
- Pydantic settings valida al startup.
- Falla rápido si falta config crítica.

---

## 22. PLAN DE SPRINTS

### Sprint 0: Setup técnico (1 semana)

**Objetivos**: andamiaje del proyecto, CI/CD básico, deploy a Cloud Run, Neon conectado.

Tasks:
- TASK-000: Setup inicial.

Aceptación:
- `make dev` arranca sin errores.
- GET /health responde 200.
- CI pasa.
- Deploy a Cloud Run funciona.

---

### Sprint 1: Multi-tenant + auth + seguridad (2 semanas)

**Objetivos**: base segura sobre la que construir todo.

Tasks:
- TASK-001: Google OAuth.
- TASK-002: Modelo empresa + usuario.
- TASK-003: Multi-tenant middleware + RLS.
- TASK-004: Repositorios base.
- TASK-005: Auditoría base.
- TASK-006: Tests de aislamiento.
- TASK-007: Roles + permisos.

Aceptación:
- Login con Google funciona.
- Usuario A no ve datos de empresa B (con tests).
- Todo cambio en DB genera evento de dominio.
- Coverage de aislamiento al 100%.

---

### Sprint 2: CRUDs core (2 semanas)

**Objetivos**: gestión de catálogo y clientes.

Tasks:
- TASK-008: CRUD productos.
- TASK-009: CRUD envases.
- TASK-010: CRUD zonas.
- TASK-011: CRUD clientes (con búsqueda difusa).
- TASK-012: CRUD usuarios.
- TASK-013: Geocoding de direcciones.

Aceptación:
- Toda entidad CRUDable desde UI.
- Búsqueda difusa de clientes funciona.
- Direcciones se geocodifican al guardar.

---

### Sprint 3: Integración Google Sheets + Importación de clientes (2 semanas)

**Objetivos**: importar clientes masivamente desde sheet.

Tasks:
- TASK-014: OAuth incremental para `drive.file`.
- TASK-015: Creación de carpetas en Drive.
- TASK-016: Templates de sheets (sistema base).
- TASK-017: Importador de clientes con preview.
- TASK-018: Validaciones y manejo de errores.
- TASK-019: Matching difuso para re-importación.

Aceptación:
- Usuario importa 100 clientes desde sheet en < 1 minuto.
- Errores claros y específicos.
- Re-importación no duplica.

---

### Sprint 4: Motor de templates + formularios + links (2 semanas)

**Objetivos**: capacidad de generar mensajes con variables y formularios públicos.

Tasks:
- TASK-020: Motor de templates con variables.
- TASK-021: Sistema de tokens firmados.
- TASK-022: Página pública del link (mobile-first).
- TASK-023: Template "confirmar pedido" con +/- por producto.
- TASK-024: Captura y persistencia de respuestas.
- TASK-025: Pantallas de confirmación/rechazo.

Aceptación:
- Token generado se valida correctamente.
- Cliente en mobile completa pedido en < 30 segundos.
- Respuestas quedan en DB con todos los datos.

---

### Sprint 5: Sistema de campañas (1-2 semanas)

**Objetivos**: orquestar todo lo anterior bajo el concepto de "campaña".

Tasks:
- TASK-026: Modelo de campañas.
- TASK-027: Wizard de creación.
- TASK-028: Listado e histórico.
- TASK-029: Duplicar campaña.
- TASK-030: Panel en vivo durante envío.
- TASK-031: Manejo de pendientes.

Aceptación:
- Crear campaña de prueba con 10 destinatarios en < 2 minutos.
- Panel en vivo actualiza al recibir respuestas.

---

### Sprint 6: Extensión Chrome (3-4 semanas)

**Objetivos**: el componente más sensible y complejo del producto.

Tasks:
- TASK-032: Setup Manifest V3 + estructura.
- TASK-033: Content scripts básicos para WhatsApp Web.
- TASK-034: Selectores DOM centralizados.
- TASK-035: Sistema de licenciamiento (token + validación).
- TASK-036: OAuth de extensión.
- TASK-037: Comunicación con backend (WebSocket o polling).
- TASK-038: Anti-detección (delays, simulación humana).
- TASK-039: UI del popup.
- TASK-040: Test diario automatizado.
- TASK-041: Distribución en Chrome Web Store.

Aceptación:
- Extensión envía 50 mensajes con delays variables sin ser detectada en 5 sesiones de prueba consecutivas.
- Kill switch funciona en < 1 hora.
- Test diario verde por 7 días seguidos.

---

### Sprint 7: Cobranzas + exportaciones (1 semana)

**Objetivos**: completar el segundo caso de uso principal.

Tasks:
- TASK-042: Tipo campaña cobranza.
- TASK-043: Templates por nivel de mora.
- TASK-044: Parseo de sheet de morosos.
- TASK-045: Matching con clientes + UI de revisión.
- TASK-046: Export de pedidos confirmados a sheet.
- TASK-047: Export de respuestas de campañas.

Aceptación:
- Cobranzas: 50 morosos procesados y enviados en < 5 minutos.
- Pedidos confirmados exportados a sheet listo para Reparto de Agua.

---

### Sprint 8: Onboarding + landing (1 semana)

**Objetivos**: que un nuevo cliente pueda usar el producto solo.

Tasks:
- TASK-048: Wizard de onboarding.
- TASK-049: Videos de Loom embebidos.
- TASK-050: Landing page en megarepartos.com.ar.
- TASK-051: Documentación básica para clientes.

Aceptación:
- Sodero desconocido completa setup hasta primera campaña en < 30 minutos sin intervención.

---

### Sprint 9: Pricing + suscripciones (1 semana)

**Objetivos**: cobrar.

Tasks:
- TASK-052: Modelo de planes.
- TASK-053: Integración con MercadoPago suscripciones.
- TASK-054: Trial automático + transición.
- TASK-055: Manejo de cambios de plan.
- TASK-056: Cancelación + grace period.

Aceptación:
- Sodero hace trial → pasa a pago → cancela → grace period funciona.

---

### Sprint 10: QA + piloto Luciano (1 semana)

**Objetivos**: producto listo para piloto real.

Tasks:
- Tests E2E completos.
- Bug fixing.
- Onboarding personal de Luciano.
- Documentación final.
- Setup de monitoreo y alertas.

Aceptación:
- Luciano usa Megarepartos en producción al menos 1 semana.
- 0 bugs críticos abiertos.
- 0 alertas falsas activas.

---

**Total estimado: 16-19 semanas, ~5-6 meses part-time**.

---

## 23. DECISIONES EXPLÍCITAS TOMADAS

Este es el log de decisiones para que Claude Code no las cuestione.

### Sobre producto

- ✅ Megarepartos es complemento, no reemplaza otros sistemas.
- ✅ No hay flujo del repartidor en MVP.
- ✅ No hay optimización de ruta en MVP.
- ✅ No hay cuenta corriente propia.
- ✅ No hay cobros en campo.
- ✅ Cobranzas son stateless.
- ✅ Producto genérico, vertical inicial: soderías.

### Sobre tecnología

- ✅ Stack: Python/FastAPI + React/Vite/TS + Postgres/Neon + Cloud Run.
- ✅ Google Sheets como input/output puntual.
- ✅ Datos persistentes en DB, no en Sheets.
- ✅ Extensión Chrome propia, no API de Meta en MVP.
- ✅ Google OAuth incremental con scope `drive.file`.
- ✅ Geocoding con Google Maps (free tier).
- ✅ Multi-tenant con `empresa_id` + RLS Postgres.

### Sobre negocio

- ✅ Pricing en pesos argentinos.
- ✅ Plan ancla: $50k/mes para 300 clientes.
- ✅ 4 tiers: Inicio / Estándar / Pro / Premium.
- ✅ Trial 14 días sin tarjeta.
- ✅ Piloto: 50% off por 6 meses para primeros 5 clientes.

### Sobre desarrollo

- ✅ Todo el código generado por Claude Code.
- ✅ Lautaro no revisa código línea por línea (delegación total).
- ✅ Calidad enforced por tests obligatorios y CI estricto.
- ✅ Convenciones de naming: español en dominio, inglés en infra.
- ✅ Sistema TASK-XXX.yaml para tareas.
- ✅ CLAUDE.md con reglas no negociables.
- ✅ 4 capas de testing (unit, integration, E2E, smoke).
- ✅ Property-based tests con hypothesis para invariantes.
- ✅ Mutation testing semanal informativo.
- ✅ Tests de regresión obligatorios para cada bug.
- ✅ Sin guardian bot ni API de Claude (costo cero).
- ✅ Synthetic monitoring vía Cloud Scheduler.
- ✅ Backups dobles (Neon + GCS) con restore test mensual.

---

## 24. LO QUE NO ESTÁ EN EL PRODUCTO

Para que quede explícito, MVP NO incluye:

- ❌ App o flujo del repartidor.
- ❌ Optimización de ruta con OR-Tools.
- ❌ Múltiples vehículos / clustering geográfico.
- ❌ Link del repartidor para marcar visitas.
- ❌ Cuenta corriente propia.
- ❌ Facturación / AFIP.
- ❌ Procesamiento de pagos a clientes finales.
- ❌ Campañas recurrentes automáticas.
- ❌ Bot conversacional vía API de Meta.
- ❌ Multi-sucursal (Premium lo mencionará "próximamente").
- ❌ Integración directa con Reparto de Agua u otros sistemas (solo via Sheets).
- ❌ IA para clasificar respuestas (puede sumarse después).
- ❌ App móvil nativa (web responsive alcanza).
- ❌ Reportes avanzados (básicos sí, dashboards complejos no).

---

## 25. ROADMAP POST-MVP

Orden tentativo de features post-launch:

### v1.1 (mes 1-2 post-lanzamiento)
- Mejoras según feedback del piloto.
- Reportes mejorados.
- IA para clasificar respuestas que llegan por WhatsApp (no por link).
- Campañas programadas.

### v1.2 (mes 3-4)
- Integración con MercadoPago para cobrar a clientes finales de la sodería.
- Encuestas más sofisticadas.
- Campañas recurrentes automáticas.

### v2.0 (mes 6+)
- Expansión a verticales: garrafas, verduras, viandas.
- Multi-sucursal real.
- API pública para integraciones.
- Bot conversacional vía API de Meta (plan enterprise).
- Optimización de ruta (si el mercado lo pide).

### v3.0 (año 2)
- Producto completo tipo Sodapp original (si tracción lo justifica).
- Flujo del repartidor con PWA offline.
- Reemplazo de sistemas legacy.

---

## DOCUMENTOS RELACIONADOS

- **SODAPP_SPEC.md**: especificación original del producto completo tipo ERP. **En standby**, no se desarrolla pero se mantiene como referencia.
- **MEGAREPARTOS_SPEC.md** (este documento): especificación del producto actual a desarrollar.

---

## CHECKLIST PRE-PRODUCCIÓN (sprint 10)

Antes del piloto con Luciano, verificar:

### Funcional
- [ ] Onboarding completo de extremo a extremo funciona sin asistencia.
- [ ] Importación de 200+ clientes via sheet funciona.
- [ ] Campaña de consulta con 100 destinatarios funciona end-to-end.
- [ ] Campaña de cobranza con 50 destinatarios funciona end-to-end.
- [ ] Extensión Chrome envía sin trabarse en 1000 mensajes consecutivos (con pausas).
- [ ] Exportación de pedidos confirmados a sheet usable por Reparto de Agua.

### Técnico
- [ ] CI/CD funcionando con todos los checks verdes.
- [ ] Deploys automáticos a producción.
- [ ] Backups diarios funcionando + restore test mensual probado.
- [ ] Alertas configuradas y testeadas.
- [ ] Synthetic monitoring corriendo cada 30 min.
- [ ] Test diario de extensión verde por 14 días seguidos.
- [ ] Logs centralizados en Cloud Logging.
- [ ] Dashboard interno funcional.

### Seguridad
- [ ] RLS habilitado en todas las tablas con `empresa_id`.
- [ ] Suite de tests de aislamiento al 100% verde.
- [ ] Rate limiting funcionando.
- [ ] Secrets solo en Secret Manager.
- [ ] HTTPS en todos los endpoints.
- [ ] Audit log completo de cambios sensibles.

### Negocio
- [ ] Landing page publicada.
- [ ] Política de privacidad y términos publicados.
- [ ] MercadoPago suscripciones configurado.
- [ ] Email de soporte funcionando.
- [ ] Documentación de cliente lista.
- [ ] Videos de onboarding grabados.

---

**Fin del documento.**

Para iniciar desarrollo: comenzar por TASK-000 (Sprint 0 - Setup técnico).
