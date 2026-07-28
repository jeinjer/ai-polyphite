# AI-Polyphite — ReplayProvider Implementation Report

Fecha: 2026-07-28  
Estado: implementado y validado

## Resultado

AI-Polyphite puede reconstruir experimentos históricos deterministas desde un
artefacto local independiente:

```text
JSONL versionado + SHA-256
  → ReplayClock
  → ReplayProvider con barrera anti-lookahead
  → MarketDataCollector existente
  → Application Services
  → PostgreSQL
  → ExperimentRun
  → API / dashboard
```

## Entregado

- `Clock`, `SystemClock` y `ReplayClock`.
- Modos step, accelerated, until y reset.
- `ReplayProvider` compatible con `MarketDataProvider`.
- Dataset JSONL sintético con 20 mercados y 80 observaciones.
- Outcomes YES, NO y CANCELLED en varios días.
- Validación de schema, referencias, UTC, contadores, rangos y SHA-256.
- Protección contra observaciones y resoluciones futuras.
- `ExperimentRun` durable con hashes de configuración y resultado.
- Migración Alembic `20260728_0006`.
- Endpoints:
  - `GET /replay-datasets`;
  - `GET /experiment-runs`;
  - `GET /experiment-runs/{run_id}`.
- CLI Python y comandos Make.
- Dashboard de Experimentos en vista avanzada.
- Aviso “Laboratorio histórico disponible” en vista simple.
- ADR y guías de proveedor, formato, creación y ejecución.

## Validación

- Backend: 165 tests aprobados.
- Contract tests: Mock, Manifold y Replay.
- Integración real con PostgreSQL y reejecución idempotente.
- Alembic: migraciones aplicadas y sin drift.
- Ruff y mypy: aprobados.
- Frontend: lint, typecheck y build productivo aprobados.
- Playwright: 8 escenarios E2E aprobados.
- npm audit: 0 vulnerabilidades.
- CLI acelerado: ejecución completa aprobada.
- Docker Compose: API, frontend, PostgreSQL, Redis y worker saludables.
- Smoke test:
  - readiness `ready`;
  - 1 dataset;
  - 20 mercados de replay;
  - 80 observaciones declaradas;
  - experimento reproducible;
  - frontend HTTP 200.

## Límites conservados

No se implementaron agentes, LLM, predicciones, noticias, Event Bus, paper
trading, operaciones, cartera, ROI, brokers ni ejecución con dinero real.

## Próximo slice obligatorio

1. `ReasoningAgent`;
2. `MarketAgent`;
3. `SkepticAgent`;
4. `ConsensusAgent`;
5. persistencia de predicciones;
6. comparación contra la probabilidad disponible del mercado.

`NewsAgent` queda fuera hasta validar predicciones reproducibles con datos
estructurados.
