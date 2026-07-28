# AI-Polyphite — cierre del slice de agentes y predicciones

Fecha: 2026-07-28

Estado: implementado y validado

## Resultado

El sistema ya puede tomar el estado visible de un mercado, ejecutar
ReasoningAgent, MarketAgent, SkepticAgent y ConsensusAgent, persistir un
`PredictionRun` reconstruible, repetirlo mediante replay y evaluarlo después de
la resolución.

No se incorporaron noticias, LLM, paper trading ni dinero real.

## Flujo entregado

```text
ReplayProvider / PostgreSQL as-of
  → PredictionOrchestrator
  → cuatro agentes deterministas
  → PredictionUnitOfWork
  → PredictionRun + AgentPrediction
  → REST
  → dashboard Predicciones / Agentes
  → evaluación posterior contra dos baselines
```

## Controles principales

- `Decimal` y timestamps UTC.
- Rechazo de observaciones futuras en contrato y repositorio.
- Configuración y semilla hasheadas.
- Idempotencia por experimento, mercado, timestamp y configuración.
- Hashes semánticos independientes de duración e IDs aleatorios.
- Correlation y causation IDs.
- Abstención explícita.
- Edge YES/NO sin interpretación de rentabilidad.
- Endpoint manual apagado por defecto y siempre bloqueado en producción.
- Sin chain-of-thought ni prompts secretos.

## Superficie

- Migración `20260728_0007`.
- `make replay-predict DATASET=synthetic-lab-v1`.
- Endpoints de predicciones por listado, detalle, mercado y experimento.
- Evaluación por experimento.
- Vistas bilingües simple y avanzada.

## Validación específica

- 184 tests backend aprobados.
- 10 tests E2E Playwright aprobados.
- Ruff y mypy sin errores.
- Alembic sin drift respecto de SQLAlchemy.
- `npm audit` con cero vulnerabilidades.
- TypeScript, ESLint y build de producción aprobados.
- Docker Compose reconstruido con API, frontend, PostgreSQL, Redis y worker
  saludables o en ejecución según su contrato.
- Unit tests de contratos, determinismo, abstención, consenso y métricas.
- Integration test con observación futura presente: la predicción utilizó la
  probabilidad visible `0.55` e ignoró `0.99`.
- Dos replay-predict independientes produjeron el mismo `result_hash`.
- Persistencia y consultas REST verificadas contra PostgreSQL.
- E2E de explicación simple, tooltips, trazabilidad avanzada, agentes,
  accesibilidad y ausencia de ROI.

## Próximo paso obligatorio

Paper trading exclusivamente sobre `PredictionRun`, manteniendo las fronteras
del ADR-0003. No corresponde añadir proveedores, Event Bus, NewsAgent o LLM
antes de ese slice.
