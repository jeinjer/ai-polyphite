# Architecture Decision Records

Los ADR registran decisiones arquitectónicas que condicionan el diseño y son
costosas de cambiar.

## Estados

- **Proposed:** pendiente de aprobación.
- **Accepted:** decisión vigente.
- **Superseded:** reemplazada por otro ADR.
- **Deprecated:** ya no debe aplicarse.

Los ADR aceptados no se reescriben para reflejar una decisión nueva. Se crea un
nuevo ADR que referencia y reemplaza al anterior.

## Índice

| ADR | Estado | Decisión |
|---|---|---|
| [0001](0001-modular-monolith.md) | Accepted | Monolito modular multiproceso |
| [0002](0002-durable-event-system.md) | Accepted | Eventos durables con PostgreSQL y Redis Streams |
| [0003](0003-paper-trading-boundaries.md) | Accepted | Límites y contabilidad inicial del paper trading |
| [0004](0004-provider-sdk-boundary.md) | Accepted | Provider SDK neutral y extensible |
| [0005](0005-collector-delivery-and-checkpoints.md) | Accepted | Ingesta at-least-once con checkpoints durables |
| [0006](0006-observation-vs-executable-quote.md) | Accepted | Observaciones separadas de cotizaciones ejecutables |
| [0007](0007-simulated-clock-and-lookahead-barrier.md) | Accepted | Reloj simulado y barrera contra lookahead |
| [0008](0008-deterministic-agents-before-llm.md) | Accepted | Agentes deterministas antes de integrar LLM |
| [0009](0009-simulated-performance-boundary.md) | Accepted | Frontera estructural de simulación y evaluación |
| [0010](0010-prediction-commercial-execution-separation.md) | Accepted | Predicción, evaluación comercial y ejecución simulada separadas |
