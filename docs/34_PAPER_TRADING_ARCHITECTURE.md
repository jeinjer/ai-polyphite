# Arquitectura de paper trading

Versión: 2.0
Estado: Implementado

## Objetivo

Evaluar `PredictionRun` reproducibles mediante una simulación binaria
conservadora, sin dinero real y sin duplicar dominio de mercados o predicciones.

## Flujo

```text
PredictionRun durable + contexto de mercado as-of predicted_at
  → CommercialEvaluation por campaña
  → EntryPolicy
  → PositionSizingPolicy
  → RiskPolicy
  → TradeDecision durable
  → PaperOrder + PaperTrade + PaperPosition
  → mark-to-market informativo
  → resolución oficial
  → PaperSettlement + ledger
  → métricas y baselines
```

El orquestador pertenece a Application. Las entidades y políticas son puras. El
adaptador SQLAlchemy implementa repositorios y Unit of Work. Replay y FastAPI
son composition roots; no contienen reglas de trading.

La ejecución automática es el comportamiento predeterminado. Existe una rama
manual excepcional:

```text
PredictionRun + lado/stake/motivo humano
  → revalidación actual de mercado y portfolio
  → RiskPolicy
  → TradeDecision(source=manual_override)
  → artefactos paper
```

Esta rama puede ignorar abstenciones o una evaluación `not_actionable`, pero no
puede omitir frescura, contabilidad, idempotencia ni riesgo. Usa un portfolio
separado y nunca reemplaza o desactiva la campaña automática.

## Módulos

- `domain/paper_trading/entities.py`: contabilidad e invariantes.
- `domain/paper_trading/policies.py`: entrada, sizing, riesgo, costes y baselines.
- `domain/paper_trading/evaluation.py`: métricas puras.
- `application/paper_trading/`: comandos, puertos, orquestador y queries.
- `infrastructure/database/`: modelos, repositorios, UoW y lecturas.
- `runtime/paper_trading*.py`: configuración y replay.
- `api/routes/paper_trading.py`: API read-only y controles dev-only.

## Temporalidad

El repositorio reconstruye estado, observación, liquidez y resolución con
timestamps `<= predicted_at` o `<= settled_at`. Si no hay historial visible, la
operación se detiene: nunca usa el estado actual como fallback.

## Atomicidad e idempotencia

- `portfolio + capital inicial` es atómico.
- `decision + order + trade + position + portfolio + ledger` es atómico.
- La clave durable de decisión es `(portfolio_id, prediction_run_id)`.
- Los overrides agregan una clave de idempotencia por portfolio y guardan
  motivo obligatorio.
- La posición es única por `(portfolio_id, market_id)`.
- El settlement es único por posición.
- Un portfolio de replay es único por experimento y hash de estrategia.

Los duplicados compatibles recuperan el resultado existente; entradas
incompatibles producen conflicto explícito.

## Observabilidad

Logs estructurados incluyen portfolio, predicción, experimento, configuración,
resultado, correlation ID, causation ID y marca `simulation_only`. La API hereda
correlation IDs y métricas HTTP normalizadas del middleware existente.

## Fuera de alcance

No hay Event Bus, NewsAgent, brokers, wallets, short, leverage, mercados
múltiples ni dinero real.
