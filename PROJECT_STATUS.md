# AI-Polyphite — Project Status

Última actualización: 2026-07-28

## Estado general

**Fase:** base histórica reproducible completa  
**Estado:** implementado y validado; pendiente de aprobación del usuario  
**Dinero real:** prohibido y no implementado

## Flujos disponibles

```text
MockProvider o ManifoldProvider
  → MarketDataCollector
  → Application Services
  → PostgreSQL
  → API read-only
  → dashboard es-ES / en-US

JSONL versionado
  → ReplayClock
  → ReplayProvider
  → MarketDataCollector
  → PostgreSQL
  → ExperimentRun
  → API / dashboard avanzado
```

## Implementado

- Market Domain, observaciones nullable, resolución y auditoría de estados.
- Provider SDK con Mock, Manifold read-only y Replay.
- Collector incremental, worker periódico y auditoría `CollectorRun`.
- `Clock`, `SystemClock` y `ReplayClock` monotónico.
- Barrera anti-lookahead dentro de `ReplayProvider`.
- JSONL con metadata, schema, rangos, contadores y validación SHA-256.
- Dataset sintético con 20 mercados y 80 observaciones.
- Modos `step`, `accelerated`, `until` y `reset`.
- `ExperimentRun` durable con configuración y resultado hasheados.
- Reejecución idempotente con persistencia semánticamente idéntica.
- API:
  - mercados, observaciones e historial;
  - sincronizaciones y fuentes;
  - `GET /replay-datasets`;
  - `GET /experiment-runs`;
  - `GET /experiment-runs/{run_id}`.
- Dashboard bilingüe, simple/avanzado, responsive y accesible.
- Experimentos visibles en modo avanzado; aviso educativo mínimo en simple.
- Docker Compose para migración, API, frontend, PostgreSQL, Redis y worker.

## Decisiones vigentes

Siete ADR aceptados:

1. Monolito modular.
2. Sistema de eventos durable como arquitectura futura.
3. Límites de paper trading.
4. Frontera neutral del Provider SDK.
5. Ingesta at-least-once con checkpoints.
6. Observaciones separadas de cotizaciones ejecutables.
7. Reloj simulado y barrera contra lookahead.

## No implementado

- Agentes, consenso, noticias o abstracción LLM.
- Predicciones y comparación contra el mercado.
- Event Bus, outbox/inbox o Redis Streams funcional.
- Paper trading, operaciones, cartera, P&L o ROI.
- Ejecución real, wallets, brokers o credenciales de trading.
- HistoricalProvider, Metaculus o Polymarket.
- Scheduler distribuido, WebSockets o autenticación.

## Siguiente slice obligatorio

Implementar, sin añadir más infraestructura base:

1. `ReasoningAgent`;
2. `MarketAgent`;
3. `SkepticAgent`;
4. `ConsensusAgent`;
5. persistencia de predicciones;
6. comparación reproducible contra la probabilidad del mercado.

`NewsAgent` queda expresamente postergado hasta demostrar que el sistema puede
producir y evaluar predicciones reproducibles con datos estructurados.

## Fuente de verdad

Este archivo describe el código actual. [`TASKS.md`](TASKS.md) contiene el
backlog y [`docs/`](docs/) explica contratos y decisiones.
