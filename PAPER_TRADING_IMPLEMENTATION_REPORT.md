# Paper Trading — Implementation Report

Fecha: 2026-07-28  
Estado: implementado; pendiente de aprobación

## Entregado

- Pipeline completo `PredictionRun → decisión → orden → trade → posición →
  settlement → performance`.
- Portfolio y ledger virtual con `USD_SIMULATED` y `MANA_SIMULATED`.
- Posiciones binarias long-only, sin leverage y una por mercado.
- Entrada por umbral, dos políticas de sizing y riesgo conservador.
- Modelos de costes cero y conservador, compartidos con baselines.
- Mark-to-market informativo y liquidación YES/NO/CANCELLED; OTHER pendiente.
- Unit of Work SQLAlchemy, idempotencia y migración Alembic `0008`.
- API read-only, filtros, OpenAPI y controles manuales sólo de desarrollo.
- Replay `make replay-trade DATASET=synthetic-lab-v1`.
- ROI simulado, P&L, drawdown, exposición, costes, cobertura, desgloses,
  evidencia, alertas y tres baselines.
- Dashboard bilingüe con Cartera, Operaciones, Posiciones y Rendimiento.
- ADR-0009 y documentación de arquitectura, contabilidad, políticas,
  liquidación, API y replay.

## Evidencia de validación

- Replay integrado ejecutado dos veces contra PostgreSQL con igualdad de hash,
  equity y cantidad de trades.
- Ejecución completa con cadencia diaria: 100 predicciones, 20 trades, 20
  settlements y equity final simulado `105.41900621`.
- Unit tests de invariantes, entrada, sizing, riesgo, costes, métricas,
  cancelaciones y baselines.
- Tests API de filtros, contratos OpenAPI y bloqueo de controles manuales.
- E2E de las cuatro vistas, disclaimer, evidencia y navegación.
- Ruff, mypy, ESLint, TypeScript, build, Alembic y Docker Compose incluidos en
  el chequeo de cierre.

## Preparación de la siguiente etapa

El MVP funcional queda congelable. La siguiente etapa recomendada es
estabilización y validación paper continua: ejecutar datasets más extensos,
observar calidad, revisar concentración y comparar periodos sin optimizar
parámetros automáticamente.

No se añadieron NewsAgent, LLM, Event Bus, proveedores, brokers ni dinero real.
