# [Nombre del módulo] — REQ-IDs

> Plantilla para archivos en `behaviors/`. Copiar como `behaviors/<modulo>.md`
> y reemplazar el contenido. Cada REQ-ID debe estar cubierto por al menos un
> test marcado con `@pytest.mark.req("REQ-XXX-NNN")`.
>
> El script `scripts/behavior_coverage.py` falla CI si un REQ-ID declarado acá
> no tiene su test correspondiente.

## Contexto

[Una o dos frases sobre qué módulo cubre este archivo y por qué importa.
Ej: "Autenticación de usuarios via Google OAuth. Crítico para multi-tenant
porque define la identidad de cada request."]

## Requisitos

### REQ-XXX-001: [título corto del requisito]

[Descripción del comportamiento esperado. Incluir caso happy path y edge cases
relevantes. Si hay condiciones de borde explícitas, listarlas como subitems.]

- Precondición: [si aplica]
- Resultado esperado: [comportamiento observable]
- Edge cases: [si aplica]

### REQ-XXX-002: [otro requisito]

[...]

## No-requisitos (qué explícitamente NO hace este módulo)

- [Cosa fuera de scope #1]
- [Cosa fuera de scope #2]

## Notas de implementación

[Decisiones de diseño relevantes, links a docs/ARCHITECTURE.md si aplica.]
