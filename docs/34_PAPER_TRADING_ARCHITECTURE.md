# Arquitectura de paper trading

Versión: 1.0  
Estado: Implementado

## Objetivo

Evaluar `PredictionRun` reproducibles mediante una simulación binaria
conservadora, sin dinero real y sin duplicar dominio de mercados o predicciones.

## Flujo

```text
PredictionRun durable + contexto de mercado as-of predicted_at
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

No hay Event Bus, scheduler de paper trading, ejecución continua, NewsAgent,
brokers, wallets, short, leverage, mercados múltiples ni dinero real.
