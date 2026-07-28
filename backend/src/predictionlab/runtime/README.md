# Runtime

Composition roots y procesos explícitos del monolito modular:

- `collector_cli`: ingesta manual o periódica por proveedor.
- `replay_cli`: replay, predicciones y paper trading histórico.
- `paper_validation_cli`: validación paper continua manual o periódica.

Los workers usan apagado cooperativo y PostgreSQL como fuente de verdad. No se
incluyen Celery, scheduler distribuido ni procesos placeholder.
