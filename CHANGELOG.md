# Changelog

Todos los cambios relevantes de AI-Polyphite se documentarán en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) y el
proyecto utilizará versionado semántico cuando exista la primera entrega
versionada.

## [Unreleased]

### Fixed

- La ingesta Manifold conserva resoluciones confirmadas ante correcciones
  incompatibles del proveedor, registra el conflicto y continúa el catálogo.
- La valoración paper usa la misma precisión decimal que PostgreSQL y
  reconstruye la proyección agregada desde posiciones durables antes de
  reconciliar, evitando falsos fallos por redondeos sub-centesimales.
- Un fallo de una campaña paper ya no impide ejecutar las campañas restantes
  del mismo slot.
- Collector y validador revisan sus esperas cada 60 segundos para reanudar el
  trabajo rápidamente después de una suspensión del host.
- El dashboard selecciona por defecto la cartera autónoma, filtra todas las
  lecturas por cartera y distingue operaciones automáticas de overrides
  manuales.
- El backend CI carga su configuración estricta de Mypy, aplica las
  migraciones sobre PostgreSQL limpio y aísla los tests de configuración de
  variables heredadas del runner.

### Added

- `CommercialEvaluation` durable para separar estimación probabilística de
  conveniencia comercial por campaña y portfolio.
- Campaña automática `experimental-v1` con portfolio independiente y edge neto
  mínimo configurable.
- Overrides manuales exclusivamente paper con lado, stake, motivo,
  idempotencia y `decision_source` auditables.
- Listado liviano y paginado de predicciones con filtros y ordenamiento del
  lado del servidor.
- Detalle lazy de predicción con agentes, hashes, evaluación comercial y
  ejecuciones simuladas relacionadas.
- Dashboard de predicciones con filtros, modal de confirmación y rutas
  `/predictions/{prediction_id}`.
- ADR-0010 para separar predicción, evaluación comercial y ejecución simulada.
- Rutas navegables y enlazables para todas las secciones del dashboard y
  `/markets/{market_id}` para el detalle.
- Refresco automático en segundo plano cada 60 segundos.
- Operación autónoma Compose con Manifold público, collector y validador paper
  cada hora.
- Selección de predicciones por proveedor y sólo ante observaciones nuevas.
- Aislamiento de conflictos de observación externos para que un timestamp
  inconsistente no detenga todo el catálogo.
- Backups diarios de PostgreSQL, validación del archivo y retención de 7 días.
- Rotación de logs Docker para proteger el disco en campañas largas.
- Scaffold inicial del monorepo.
- Configuración base de backend FastAPI y frontend Next.js.
- Docker Compose para frontend, backend, PostgreSQL y Redis.
- Estructura para contratos, infraestructura, pruebas y scripts.
- Documentación de estado y backlog.
- ADRs iniciales para monolito modular, eventos durables y paper trading.
- Configuración de backend tipada con precedencia explícita.
- Logging estructurado JSON y contexto por request.
- Propagación de correlation ID y W3C trace context.
- Endpoints separados de liveness y readiness.
- Comprobaciones concurrentes de PostgreSQL y Redis con timeout.
- Tests unitarios e integración para la base transversal.
- Pipeline CI para backend, frontend y builds de contenedores.
- Documentación operativa de la base de plataforma.
- Entidades de dominio `Provider`, `Market` y `MarketSnapshot`.
- Estados e invariantes del ciclo de vida de mercados.
- Modelos SQLAlchemy y migración Alembic inicial del Market Domain.
- Repositorios asíncronos para providers, markets y snapshots.
- Tests unitarios de dominio e integración contra PostgreSQL.
- Verificación automática de drift entre Alembic y metadata SQLAlchemy.
- Documento técnico del Market Domain.
- Comandos y servicios transaccionales para providers y mercados.
- Unit of Work SQLAlchemy con transacciones explícitas.
- Registro atómico e idempotente de market snapshots.
- Detección de observaciones duplicadas con contenido conflictivo.
- Tests unitarios de aplicación y tests de concurrencia en PostgreSQL.
- Documento técnico de Market Application Services.
- Query Layer y read models de mercados.
- `GET /markets` con paginación, filtros y ordenamiento.
- `GET /markets/{market_id}` con provider y último snapshot.
- Documentación OpenAPI con enums, límites y errores.
- Métricas HTTP por método, plantilla de ruta, estado y duración.
- Tests unitarios e integración de la API de mercados.
- Provider SDK neutral con interfaz asíncrona `MarketDataProvider`.
- DTOs externos normalizados, capacidades y health checks de proveedores.
- Registry explícito de factories sin estado global.
- `MockProvider` determinista con filtros, cursores, detalle e historial.
- Test de integración MockProvider → Application → PostgreSQL → REST.
- ADR y documentación técnica de la frontera multi-provider.
- Collector Layer incremental basado en `MarketDataProvider`.
- Sincronización idempotente de providers y mercados por referencia externa.
- Checkpoints durables con cursor, watermark y progreso provisional.
- Retries transitorios con backoff exponencial, jitter y `Retry-After`.
- Advisory locks PostgreSQL para excluir collectors concurrentes.
- Logs y resultados observables por ejecución y página.
- Migración Alembic de `collector_checkpoints`.
- Tests unitarios e integración del flujo MockProvider → PostgreSQL → API.
- Marca visible actualizada a AI-Polyphite, conservando los
  namespaces técnicos internos para evitar una migración destructiva.
- Separación de `Market.source_created_at` externo y `Market.ingested_at` local.
- Migración Alembic compatible que preserva los timestamps de mercados
  existentes.
- `ManifoldProvider` read-only sobre la API pública oficial para mercados
  binarios.
- Paginación por cursor, rate limiting, timeouts, health check y errores tipados
  para Manifold.
- Fixtures HTTP sanitizadas y contract tests compartidos del Provider SDK.
- Integración Manifold fixture → Collector → PostgreSQL → REST.
- Entidad y persistencia `MarketObservation` con métricas nullable, procedencia,
  idempotencia y conflictos tipados.
- Resolución oficial de mercados con outcomes YES, NO, CANCELLED y OTHER e
  historial inmutable de estados.
- Migración compatible para observaciones, resolución y auditoría.
- Capacidad `LATEST_OBSERVATION` en Provider SDK y persistencia de
  probabilidades de Manifold.
- Configuración explícita de fuentes con default seguro `mock`.
- Worker periódico por fuente, apagado cooperativo y ciclo manual.
- Auditoría durable `CollectorRun` y endpoints read-only filtrables.
- Endpoints paginados de observaciones y timeline de mercados.
- Dashboard inicial responsive con vista simple y avanzada.
- Internacionalización tipada `es-ES`/`en-US`, español predeterminado.
- KPIs, series de probabilidad, timeline, estados accesibles, minialertas y
  tooltips educativos centralizados.
- ADR de separación entre observaciones y cotizaciones ejecutables.
- Documentación operativa del histórico, worker, auditoría, i18n y UX.
- Abstracción temporal `Clock` con `SystemClock` y `ReplayClock`.
- `ReplayProvider` determinista con barrera explícita contra lookahead.
- Formato JSONL versionado con metadata e integridad SHA-256.
- Dataset sintético controlado con 20 mercados y 80 observaciones.
- Modos de replay step, accelerated, until y reset.
- Entidad y persistencia durable `ExperimentRun`.
- Endpoints read-only de datasets y ejecuciones históricas.
- CLI y comandos Make para experimentos reproducibles.
- Sección Experimentos en el dashboard avanzado y aviso educativo en vista
  simple.
- ADR de reloj simulado y prevención de lookahead.
- Tests de determinismo, integridad, resolución temporal, persistencia,
  API, CLI y frontend.
- Contratos neutrales `PredictionAgent` y `ModelBackend`.
- Backends `RuleBasedModelBackend` y `MockModelBackend` sin dependencias
  externas.
- ReasoningAgent, MarketAgent, SkepticAgent y ConsensusAgent deterministas.
- `PredictionOrchestrator` transaccional con correlation/causation IDs,
  ejecución batch e idempotencia por experimento.
- Persistencia `PredictionRun`/`AgentPrediction` y migración Alembic.
- Edge YES/NO, niveles configurables y estrategia explícita de abstención.
- Consultas as-of que excluyen estados y observaciones futuras.
- Comando `make replay-predict` con hashes reproducibles.

### Changed

- `ConsensusAgent` 2.0 conserva probabilidad y resultado estimado con confianza
  o edge bajos; esos umbrales pasan a la evaluación comercial.
- La automatización paper continúa siendo la ruta predeterminada. El botón
  manual funciona como excepción separada y no desactiva el worker.
- El runtime continuo reutiliza un único batch de predicciones entre las
  campañas conservadora y experimental, sin mezclar portfolios o métricas.
- API REST de predicciones, historial por mercado/experimento y evaluación.
- Brier Score, log loss, error absoluto, accuracy, calibración, cobertura,
  MarketBaseline y ConstantBaseline.
- Secciones bilingües Predicciones y Agentes con vista simple/avanzada.
- ADR de agentes deterministas antes de integrar LLM.
- Tests unitarios, integración y E2E del pipeline predictivo.
- Dominio completo de paper trading con portfolios, decisiones, órdenes,
  trades, posiciones, settlements, ledger y snapshots de performance.
- Unidades inequívocas `USD_SIMULATED` y `MANA_SIMULATED`.
- Políticas versionadas de entrada por umbral, sizing fijo o ajustado,
  límites de exposición y costes simulados.
- Migración Alembic para ocho tablas durables de simulación y auditoría.
- Unit of Work transaccional e idempotencia por experimento, predicción y
  posición.
- Liquidación oficial YES/NO/CANCELLED y tratamiento conservador de OTHER.
- Mark-to-market informativo con barrera temporal estricta.
- `make replay-trade` y replay doble con resultados deterministas.
- ROI y P&L simulados, drawdown, exposición, costes, cobertura, desgloses,
  estado de evidencia, alertas y baselines comparables.
- API read-only de portfolio, decisiones, trades, posiciones, settlements,
  equity curve y performance; controles POST bloqueados en producción.
- Dashboard bilingüe de Cartera, Operaciones, Posiciones y Rendimiento.
- ADR de frontera estructural entre simulación y ejecución real.
- Tests unitarios, integración PostgreSQL, OpenAPI y Playwright del slice.
- Runtime periódico y manual de validación paper continua por slots UTC.
- Configuración congelada mediante hash y portfolio estable por estrategia.
- Advisory lock PostgreSQL e idempotencia end-to-end de cada ciclo.
- Auditoría durable `PaperValidationRun` con estados, contadores y trazabilidad.
- Reconciliación automática de ledger, balances, P&L, equity y exposición.
- CLI, script PowerShell y perfil Compose opt-in para campañas de validación.
- Tests unitarios e integración PostgreSQL de retries y drift contable.

### Security

- Servicios de datos publicados únicamente en localhost por defecto.
- Ausencia deliberada de wallets, claves y adaptadores de trading real.
- Resumen de configuración basado en lista permitida, sin URLs ni credenciales.
- Respuestas de readiness sin detalles internos de errores.

### Fixed

- Corregida la allowlist CORS local para reconocer explícitamente
  `127.0.0.1:3000` y `localhost:3000`.
- Unificados frontend, Compose, Dockerfile y documentación sobre
  `http://127.0.0.1:8000` mediante `NEXT_PUBLIC_API_URL`.
- Añadidos tests de origin permitido/no permitido, headers CORS, preflight
  `OPTIONS`, endpoints del dashboard y navegación Playwright contra el stack
  Docker real.
