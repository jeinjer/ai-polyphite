# Changelog

Todos los cambios relevantes de AI-Polyphite se documentarán en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) y el
proyecto utilizará versionado semántico cuando exista la primera entrega
versionada.

## [Unreleased]

### Added

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

### Security

- Servicios de datos publicados únicamente en localhost por defecto.
- Ausencia deliberada de wallets, claves y adaptadores de trading real.
- Resumen de configuración basado en lista permitida, sin URLs ni credenciales.
- Respuestas de readiness sin detalles internos de errores.
