# Contracts

Contratos versionados que cruzan límites de proceso o lenguaje.

## Contenido previsto

- `events`: schemas de eventos durables.
- `http`: snapshots o artefactos derivados de OpenAPI cuando sean necesarios.

## Reglas

- Un contrato publicado no se modifica de forma incompatible.
- Los cambios incompatibles crean una nueva versión.
- Los ejemplos deben validarse contra su schema.
- Pydantic será la fuente de verdad inicial para la API HTTP.
- Los contratos no contienen lógica de negocio.

Todavía no existe ningún contrato publicado.
