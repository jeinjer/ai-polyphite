# AI-Polyphite repository instructions

Estas instrucciones aplican a todo el repositorio.

## Antes de modificar código

1. Leer `PROJECT_STATUS.md` y `TASKS.md`.
2. Leer la documentación relevante en `docs/`.
3. Leer los ADR relacionados en `docs/adr/`.
4. Revisar el código existente y sus tests.
5. Proponer un cambio pequeño y verificable.

## Restricciones

- Nunca implementar trading con dinero real.
- No añadir wallets, firmas ni credenciales de ejecución.
- No cambiar el stack principal sin aprobación y un ADR.
- No crear microservicios ni contenedores por agente.
- No hacer que el dominio dependa de frameworks o proveedores.
- No permitir llamadas directas de agentes a APIs externas.
- No sobrescribir hechos históricos ni experimentos.
- No añadir dependencias sin justificar necesidad y mantenimiento.

## Arquitectura backend

La dirección de dependencias es:

```text
api -> application -> domain
integrations/infrastructure -> application/domain ports
runtime -> application
```

`domain` no puede importar FastAPI, SQLAlchemy, Redis ni SDKs externos.

## Calidad

Todo cambio funcional debe incluir:

- Unit tests.
- Integration tests cuando cruza infraestructura.
- Contract tests para proveedores y eventos.
- E2E tests cuando modifica un flujo visible.
- Documentación y estado actualizados.

Ejecutar antes de entregar:

```powershell
.\scripts\check.ps1
```

Si un check no puede ejecutarse, documentar el motivo exacto.

## Datos y observabilidad

- Usar UTC.
- Usar `Decimal` para dominio financiero.
- Propagar correlation y causation IDs.
- No registrar secretos.
- Tratar PostgreSQL como fuente de verdad durable.
- Diseñar consumidores de eventos idempotentes.

## ADRs

No reescribir un ADR aceptado para cambiar una decisión. Crear un ADR nuevo que
lo reemplace y actualizar el índice.

## Trabajo iterativo

Mantener cambios pequeños. Después de cada tarea:

1. Actualizar `CHANGELOG.md`.
2. Actualizar `PROJECT_STATUS.md`.
3. Actualizar `TASKS.md`.
4. Entregar resultados de tests.
5. Esperar aprobación antes de iniciar la siguiente tarea.
