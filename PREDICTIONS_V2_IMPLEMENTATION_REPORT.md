# Predictions v2 — Implementation Report

Fecha: 2026-07-30
Estado: implementado y validado
Ejecución real: no existe

## Resultado

AI-Polyphite separa ahora:

```text
PredictionRun → CommercialEvaluation → TradeDecision
```

La operación automática continúa activa y es la ruta predeterminada. El botón
manual crea una excepción de paper trading que puede elegir YES/NO y stake
ignorando la recomendación de agentes, pero conserva mercado abierto, datos
vigentes, riesgo, contabilidad e idempotencia.

## Backend

- `ConsensusAgent` 2.0 conserva probabilidad, resultado estimado y warnings
  cuando confidence o edge no alcanzan umbrales comerciales.
- Migración Alembic compatible y append-only para runs históricos.
- Dominio, servicio y persistencia de `CommercialEvaluation`.
- Campañas automáticas conservadora y experimental con portfolios separados.
- `TradeDecision.decision_source` diferencia `automatic` de
  `manual_override`.
- `POST /paper-trading/manual-trades` crea únicamente operaciones simuladas.
- `GET /predictions` devuelve un resumen paginado sin agentes.
- `GET /predictions/{id}` carga detalle completo bajo demanda.
- `GET /agent-predictions` alimenta el monitor técnico existente.

## Frontend

- Lista de predicciones con paginación de 25/50.
- Filtros de conveniencia, resultado y ordenamiento.
- Ruta lazy `/predictions/{prediction_id}`.
- Modal de override con lado, stake, motivo y advertencia de simulación.
- Texto explícito: la automatización sigue activa y prevalece por defecto.

## Configuración

```env
AI_POLYPHITE_EXPERIMENTAL_CAMPAIGN_ENABLED=true
AI_POLYPHITE_EXPERIMENTAL_MIN_NET_EDGE=0.015
AI_POLYPHITE_ENABLE_MANUAL_PAPER_OVERRIDES=true
```

Los overrides están bloqueados en `production`, independientemente de la
variable.

## Trazabilidad

- Evaluaciones por campaign, portfolio y hashes de configuración/resultado.
- Decisiones manuales con motivo e idempotency key.
- Correlation y causation IDs propagados.
- Métricas automáticas y manuales separables por portfolio y
  `decision_source`.
- Ningún registro histórico se recalcula o sobrescribe.

## Validación

- 236 tests backend aprobados.
- Ruff y mypy sin errores.
- Integración PostgreSQL de predicción, campaña doble y override manual.
- 12 E2E Playwright aislados de lista, detalle y confirmación manual.
- E2E adicional aprobado contra frontend/backend Docker y PostgreSQL reales.
- Alembic upgrade/check sin drift.
- ESLint, TypeScript y build de producción Next.js aprobados.

## Verificación operativa

Se reconstruyó Compose sin borrar PostgreSQL y se ejecutó un ciclo paper
explícito sobre observaciones públicas de Manifold:

- 945 mercados procesados;
- 939 `PredictionRun` con estado `predicted`;
- 6 abstenciones estructurales;
- 945 evaluaciones conservadoras y 945 experimentales;
- 9 operaciones automáticas simuladas en la campaña conservadora;
- 29 operaciones automáticas simuladas en la experimental;
- reconciliación contable correcta en ambos portfolios.

No se creó ningún override manual durante la verificación: esa decisión queda
en manos del usuario desde el dashboard.

## Documentación

- `docs/40_PREDICTIONS_V2_AND_MANUAL_OVERRIDES.md`.
- ADR-0010.
- README, backend README, changelog, estado y backlog actualizados.
