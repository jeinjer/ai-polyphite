# AI-Polyphite — Tasks

Este backlog está ordenado por dependencia. Una tarea no debe marcarse como
completada hasta que su código, tests y documentación hayan sido validados.

## Completed

- [x] Leer y analizar la documentación inicial.
- [x] Aprobar la arquitectura base.
- [x] Crear el scaffold del repositorio.
- [x] Registrar ADR de monolito modular.
- [x] Registrar ADR del sistema de eventos.
- [x] Registrar ADR de paper trading.
- [x] Implementar configuración tipada y precedencia de variables.
- [x] Implementar logging estructurado.
- [x] Propagar correlation ID y trace context en la API.
- [x] Añadir readiness checks para PostgreSQL y Redis.
- [x] Configurar CI para lint, typing, tests y builds.
- [x] Unificar hosts locales y validar CORS/preflight del dashboard.
- [x] Modelar `Provider`, `Market` y `MarketSnapshot`.
- [x] Implementar invariantes del Market Domain.
- [x] Crear modelos SQLAlchemy y migración inicial de mercados.
- [x] Crear repositorios asíncronos de mercados.
- [x] Probar dominio y persistencia real en PostgreSQL.
- [x] Crear casos de uso transaccionales de registro y actualización.
- [x] Implementar persistencia idempotente de snapshots.
- [x] Añadir tests de concurrencia para observaciones duplicadas.
- [x] Crear Query Layer de mercados.
- [x] Exponer queries REST paginadas, filtradas y ordenadas.
- [x] Añadir detalle REST de mercado y documentación OpenAPI.
- [x] Instrumentar métricas HTTP por ruta normalizada.
- [x] Definir el Provider SDK neutral.
- [x] Crear DTOs externos y capacidades de proveedores.
- [x] Implementar health checks y registry de factories.
- [x] Implementar MockProvider determinista.
- [x] Validar MockProvider contra persistencia y API existentes.
- [x] Registrar ADR de la frontera del Provider SDK.
- [x] Añadir sincronización idempotente por referencia externa.
- [x] Implementar Collector Layer incremental.
- [x] Persistir cursores y watermarks en PostgreSQL.
- [x] Implementar retries selectivos con backoff y jitter.
- [x] Excluir ejecuciones concurrentes mediante advisory locks.
- [x] Validar MockProvider → Collector → PostgreSQL → REST.
- [x] Registrar ADR de entrega at-least-once y checkpoints.

## Next — First real market provider

- [x] Aplicar la marca visible AI-Polyphite.
- [x] Separar creación externa e ingesta local de mercados.
- [x] Migrar datos existentes sin perder timestamps.
- [x] Definir fixtures contractuales del primer proveedor real.
- [x] Implementar el adaptador read-only de Manifold Markets.
- [x] Validar rate limits, errores, timeouts y normalización.
- [x] Validar Manifold fixture → Collector → PostgreSQL → REST.

## Completed — Historical foundation and beginner dashboard

- [x] Modelar y persistir `MarketObservation`.
- [x] Implementar idempotencia y conflictos tipados de observaciones.
- [x] Separar observaciones del futuro `ExecutableQuote`.
- [x] Persistir outcomes YES, NO, CANCELLED y OTHER.
- [x] Auditar cambios de estado y resolución.
- [x] Activar fuentes mediante configuración validada.
- [x] Implementar worker periódico y ejecución manual.
- [x] Persistir y consultar `CollectorRun`.
- [x] Exponer observaciones y timeline por API.
- [x] Ingerir probabilidades de Manifold sin inventar precios.
- [x] Crear dashboard español orientado a principiantes.
- [x] Añadir idioma inglés y catálogo tipado.
- [x] Añadir KPIs, gráficos, timeline, alertas y tooltips.
- [x] Cubrir accesibilidad básica, loading, empty y error.
- [x] Documentar modelo, worker, auditoría, i18n, UX y navegación.
- [x] Registrar ADR Observation vs ExecutableQuote.

## Completed — Deterministic replay

- [x] Definir `Clock`, `SystemClock` y `ReplayClock`.
- [x] Implementar `ReplayProvider` contra `MarketDataProvider`.
- [x] Crear formato JSONL versionado y validación SHA-256.
- [x] Crear dataset sintético de 20 mercados y 80 observaciones.
- [x] Implementar barrera anti-lookahead.
- [x] Implementar modos step, accelerated, until y reset.
- [x] Reutilizar Collector y Application Services existentes.
- [x] Modelar, persistir y consultar `ExperimentRun`.
- [x] Añadir endpoints y CLI de replay.
- [x] Añadir Experimentos al dashboard avanzado.
- [x] Validar determinismo y persistencia idéntica.
- [x] Registrar ADR de reloj simulado y lookahead.

## Completed — Minimal agents and predictions

- [x] Definir contrato neutral y runtime observable mínimo de agentes.
- [x] Implementar `ReasoningAgent`.
- [x] Implementar `MarketAgent`.
- [x] Implementar `SkepticAgent`.
- [x] Implementar `ConsensusAgent`.
- [x] Persistir predicciones reconstruibles y versionadas.
- [x] Comparar predicciones contra la probabilidad disponible del mercado.
- [x] Evaluar predicciones sobre ReplayProvider sin lookahead.
- [x] Integrar `make replay-predict` con múltiples timestamps.
- [x] Exponer queries, API y dashboard de predicciones y agentes.
- [x] Comparar Brier, log loss y error contra Market y Constant baselines.
- [x] No implementar `NewsAgent` en este slice.

## Later — Provider data sources

- [ ] Implementar HistoricalProvider.
- [ ] Evaluar un scheduler distribuido sólo si el worker explícito deja de ser
      suficiente.
- [ ] Evaluar adaptadores para Metaculus y Polymarket.

## Durable event runtime

- [ ] Definir `EventEnvelope` v1.
- [ ] Crear tablas outbox e inbox.
- [ ] Implementar publicación transaccional.
- [ ] Implementar Redis Streams y consumer groups.
- [ ] Implementar reintentos y dead-letter handling.
- [ ] Probar duplicados, redelivery y reinicios.

## Evidence and AI — later

- [ ] Modelar fuentes, documentos y evidencia.
- [ ] Implementar ingesta RSS inicial.
- [ ] Definir la interfaz LLM.
- [ ] Implementar provider falso determinista.
- [ ] Implementar provider Ollama.
- [ ] Implementar `NewsAgent` sólo después de validar datos estructurados.

## Completed — Paper trading

- [x] Modelar estrategias y versiones.
- [x] Modelar portfolios y ledger.
- [x] Implementar decisiones simuladas idempotentes.
- [x] Implementar posiciones YES/NO long-only.
- [x] Implementar liquidación oficial.
- [x] Implementar P&L, drawdown, exposición, costes y baselines.
- [x] Integrar replay determinista de predicciones y trades.
- [x] Exponer API read-only y controles dev-only.
- [x] Crear vistas bilingües de portfolio, trades, posiciones y performance.
- [x] Probar invariantes financieras, atomicidad, idempotencia y determinismo.
- [x] Registrar ADR de separación estructural entre simulación y trading real.

## Dashboard and operations

- [ ] Crear API de trazabilidad.
- [ ] Implementar actualizaciones WebSocket.
- [x] Crear overview inicial del sistema.
- [ ] Crear detalle reconstruible de predicción.
- [x] Crear vistas de portfolio, posiciones y agent runs.
- [ ] Añadir métricas de CPU, RAM, GPU y latencia.
- [ ] Crear backup y restore test.
- [ ] Preparar ejecución continua de 30 días.

## Next — MVP stabilization

- [ ] Congelar políticas y configuración del MVP.
- [ ] Ejecutar validación paper continua sobre datos más extensos.
- [ ] Añadir reconciliación operativa automatizada de ledger y balances.
- [ ] Medir concentración por periodo, categoría y mercado.
- [ ] Definir criterios de promoción o descarte de una estrategia.
- [ ] Publicar un informe de 30 días sin optimización retrospectiva.

## Later

- [ ] Adversarial Agent.
- [ ] Statistical Agent.
- [ ] Replay histórico avanzado.
- [ ] Experimentos A/B.
- [ ] RAG y memoria histórica.
- [ ] Proveedores LLM cloud.

## Explicitly out of scope

- Trading con dinero real.
- Wallets y firmas.
- Credenciales de ejecución en mercados.
- Optimización automática de estrategias.
- Microservicios por agente.
