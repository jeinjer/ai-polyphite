# AI-Polyphite — Project Status

Última actualización: 2026-07-28

## Estado general

**Fase:** predicciones deterministas reproducibles completas

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

Mercado visible as-of
  → Reasoning / Market / Skeptic / Consensus
  → PredictionRun durable
  → API / dashboard Predicciones y Agentes
  → evaluación posterior contra baselines
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
- Contratos `PredictionAgent` y `ModelBackend`.
- Backends deterministas RuleBased y Mock sin I/O externo.
- ReasoningAgent, MarketAgent, SkepticAgent y ConsensusAgent versionados.
- Orquestador transaccional, observable e idempotente.
- `PredictionRun` y cuatro `AgentPrediction` reconstruibles.
- Edge YES/NO, niveles configurables y abstención explícita.
- Lecturas PostgreSQL as-of con barrera contra observaciones futuras.
- `make replay-predict` con cadencia o timestamps explícitos.
- API de predicciones por mercado y experimento.
- Brier, log loss, error absoluto, accuracy, cobertura y calibración.
- MarketBaseline y ConstantBaseline.
- Vistas Predicciones y Agentes sin ROI ficticio.
- Docker Compose para migración, API, frontend, PostgreSQL, Redis y worker.

## Decisiones vigentes

Ocho ADR aceptados:

1. Monolito modular.
2. Sistema de eventos durable como arquitectura futura.
3. Límites de paper trading.
4. Frontera neutral del Provider SDK.
5. Ingesta at-least-once con checkpoints.
6. Observaciones separadas de cotizaciones ejecutables.
7. Reloj simulado y barrera contra lookahead.
8. Agentes deterministas antes de integrar LLM.

## No implementado

- Noticias, backend LLM u Ollama.
- Event Bus, outbox/inbox o Redis Streams funcional.
- Paper trading, operaciones, cartera, P&L o ROI.
- Ejecución real, wallets, brokers o credenciales de trading.
- HistoricalProvider, Metaculus o Polymarket.
- Scheduler distribuido, WebSockets o autenticación.

## Siguiente slice obligatorio

Implementar paper trading sobre `PredictionRun`:

1. estrategias versionadas;
2. portfolio y ledger virtual;
3. decisiones idempotentes;
4. posiciones YES/NO long-only;
5. liquidación oficial;
6. P&L y métricas exclusivamente simuladas.

No añadir NewsAgent, LLM, proveedores ni Event Bus antes de este slice.

## Fuente de verdad

Este archivo describe el código actual. [`TASKS.md`](TASKS.md) contiene el
backlog y [`docs/`](docs/) explica contratos y decisiones.
