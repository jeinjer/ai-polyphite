# AI-Polyphite — Project Status

Última actualización: 2026-07-30

## Estado general

**Fase:** estabilización del MVP con predicciones v2 y validación paper continua

**Estado:** campaña autónoma read-only/paper preparada para ejecución continua
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
  → CommercialEvaluation por campaña
  → API / dashboard Predicciones y Agentes
  → evaluación posterior contra baselines y costes

PredictionRun durable
  → campañas automáticas separadas
  → políticas de entrada, sizing, riesgo y costes
  → decisión, orden, trade y posición simulados
  → settlement oficial y ledger
  → métricas, baselines y dashboard

Mercados abiertos visibles por slot UTC
  → predicciones y decisiones idempotentes
  → settlement / mark-to-market
  → reconciliación ledger ↔ portfolio
  → auditoría PaperValidationRun

Intervención humana opcional
  → lado, stake y motivo explícitos
  → revalidación actual y RiskPolicy
  → portfolio manual separado
  → TradeDecision(source=manual_override)
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
- `ConsensusAgent` 2.0 publica estimación aun con confianza o edge comercial
  bajos y conserva warnings.
- `PredictionRun.predicted` con `estimated_outcome` YES/NO para runs nuevos.
- `CommercialEvaluation` durable con edge bruto/neto, costes, frescura,
  motivos y etiqueta por campaña/portfolio.
- Orquestador transaccional, observable e idempotente.
- `PredictionRun` y cuatro `AgentPrediction` reconstruibles.
- Edge YES/NO, niveles configurables y abstención explícita.
- Lecturas PostgreSQL as-of con barrera contra observaciones futuras.
- `make replay-predict` con cadencia o timestamps explícitos.
- API de predicciones por mercado y experimento.
- `GET /predictions` liviano, paginado, filtrable y ordenable sin N+1.
- Detalle lazy `/predictions/{id}` con agentes, evaluación y artefactos paper.
- `GET /agent-predictions` separado para el monitor técnico.
- Brier, log loss, error absoluto, accuracy, cobertura y calibración.
- MarketBaseline y ConstantBaseline.
- Vistas Predicciones y Agentes sin ROI ficticio.
- Portfolio y ledger virtual en `USD_SIMULATED` o `MANA_SIMULATED`.
- Decisiones idempotentes derivadas exclusivamente de `PredictionRun`.
- Posiciones YES/NO long-only, sin leverage y una por mercado.
- Políticas versionadas de entrada, sizing, riesgo y costes.
- Apertura y liquidación transaccionales con procedencia completa.
- Mark-to-market explícitamente informativo.
- Liquidación YES, NO y CANCELLED; OTHER queda pendiente con alerta.
- Replay trade determinista integrado al mismo reloj histórico.
- Métricas simuladas, evidencia, alertas y baselines comparables.
- API read-only de portfolios, decisiones, trades, posiciones y settlements.
- Vistas bilingües Cartera, Operaciones, Posiciones y Rendimiento.
- Hosts locales unificados en `127.0.0.1` y CORS validado para ambos origins
  de desarrollo mediante tests y Playwright contra Docker.
- Docker Compose para migración, API, frontend, PostgreSQL, Redis y worker.
- Runtime `once`/`worker` para validación paper continua por slots UTC.
- Configuración congelada mediante hash y portfolio estable por estrategia.
- Advisory lock y retries sin duplicar predicciones, decisiones ni operaciones.
- Auditoría durable `PaperValidationRun` para cada intento.
- Reconciliación automática de ledger, balances, P&L, equity y exposición.
- Runbook operativo para validación paper continua.
- Campañas conservadora y `experimental-v1` automáticas, con portfolios,
  hashes y métricas separados y un único batch predictivo por slot.
- Override manual exclusivamente simulado, con lado/stake libres, motivo,
  idempotencia y límites de riesgo; no reemplaza la automatización.
- Rutas URL para todas las secciones y detalle enlazable de mercado.
- Refresco automático del dashboard cada 60 segundos.
- Manifold read-only como fuente autónoma de Compose, con catálogo reciente
  acotado a 1.000 mercados y una consulta HTTP por ciclo.
- Predicciones live limitadas a Manifold y a observaciones nuevas.
- Collector y validador paper cada hora con recuperación tras reinicio.
- Backups PostgreSQL diarios verificados y con retención de 7 días.
- Rotación de logs Docker acotada a 50 MB por servicio.
- Reinicio `unless-stopped` para API, frontend, collector, validador y backup.
- CI del backend carga la configuración estricta de Mypy y su plugin de
  Pydantic sin perder la selección tipada del archivo de entorno.

## Decisiones vigentes

Diez ADR aceptados:

1. Monolito modular.
2. Sistema de eventos durable como arquitectura futura.
3. Límites de paper trading.
4. Frontera neutral del Provider SDK.
5. Ingesta at-least-once con checkpoints.
6. Observaciones separadas de cotizaciones ejecutables.
7. Reloj simulado y barrera contra lookahead.
8. Agentes deterministas antes de integrar LLM.
9. Frontera estructural de simulación y evaluación.
10. Separación entre predicción, evaluación comercial y ejecución simulada.

## No implementado

- Noticias, backend LLM u Ollama.
- Event Bus, outbox/inbox o Redis Streams funcional.
- Ejecución real, wallets, brokers o credenciales de trading.
- HistoricalProvider, Metaculus o Polymarket.
- Scheduler distribuido, WebSockets o autenticación.

## Siguiente etapa recomendada

Congelar el MVP y estabilizarlo mediante validación paper continua:

1. ejecutar datasets históricos más extensos sin cambiar parámetros;
2. observar errores, staleness, concentración y drawdown;
3. comparar periodos y categorías contra los mismos baselines;
4. ejecutar la ventana paper continua preparada durante 30 días;
5. revisar evidencia antes de añadir NewsAgent o LLM.

No añadir ejecución real, optimización automática ni nuevos agentes durante la
estabilización.

## Fuente de verdad

Este archivo describe el código actual. [`TASKS.md`](TASKS.md) contiene el
backlog y [`docs/`](docs/) explica contratos y decisiones.
