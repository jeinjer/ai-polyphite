# AI-Polyphite — Collector Layer

Version: 1.0  
Status: Implemented

## Objetivo

El Collector Layer conecta el Provider SDK con los Application Services
existentes. Obtiene mercados normalizados, los sincroniza por referencia
externa, registra el último snapshot disponible y confirma progreso durable.

No contiene HTTP, scheduler, Event Bus ni lógica específica de Manifold,
Metaculus o Polymarket.

## Flujo

```text
MarketDataProvider
        ↓
fetch_markets(cursor, updated_after)
        ↓
MarketDataCollector
        ↓
ProviderService / MarketService / MarketObservationService / MarketSnapshotService
        ↓
PostgreSQL
        ↓
checkpoint confirmado
```

`collectors` depende de puertos de Application y del contrato del Provider SDK.
No importa SQLAlchemy. Los adaptadores PostgreSQL viven en `infrastructure`.

## Sincronización idempotente

Application incorpora dos casos de uso neutrales:

- `ProviderService.synchronize`, identificado por `code`;
- `MarketService.synchronize`, identificado por
  `(provider_id, provider_market_id)`.

Cada operación informa si creó, actualizó o dejó intacta la entidad. Una
actualización externa de `open` a `resolved` atraviesa internamente `closed` para
respetar las transiciones del dominio.

`MarketSnapshotService.record` conserva su clave idempotente
`(market_id, observed_at)`. Un duplicado idéntico no crea otra fila y un
duplicado conflictivo continúa fallando.

`MarketObservationService.record` aplica el mismo patrón sin exigir precios,
spread, volumen o liquidez completos. El collector persiste una observación
cuando la fuente publica al menos una métrica real.

## Checkpoint incremental

La tabla `collector_checkpoints` conserva:

| Campo | Propósito |
|---|---|
| `provider_code` | Stream independiente por proveedor |
| `cursor` | Próxima página del ciclo activo |
| `watermark` | Timestamp confirmado del último ciclo completo |
| `pending_watermark` | Máximo provisional durante la paginación |
| `updated_at` | Último avance UTC |

Una página se confirma después de persistir todas sus entidades. Si el proceso
falla antes, el cursor anterior se reutiliza y la página se procesa nuevamente.

El watermark no avanza hasta completar el catálogo. El collector consulta desde
un segundo antes del watermark por defecto; ese solapamiento evita perder
actualizaciones con el mismo timestamp y se apoya en la idempotencia.

## Concurrencia

`PostgresProviderCollectionLock` utiliza un advisory lock transaccional derivado
del código del proveedor. Sólo una ejecución por proveedor puede avanzar, aun si
existen varios procesos. Proveedores diferentes pueden ejecutarse en paralelo.

`LocalProviderCollectionLock` existe para tests y ejecución estrictamente local;
no reemplaza al lock PostgreSQL en workers reales.

## Retries

Sólo se reintentan errores que heredan de `TransientProviderError`:

- indisponibilidad temporal;
- rate limit.

La política configura intentos máximos, delay inicial, delay máximo y jitter.
`ProviderRateLimitError` puede indicar `retry_after_seconds`.

No se reintentan automáticamente:

- cursores inválidos;
- capacidades ausentes;
- DTOs inválidos;
- invariantes de dominio;
- conflictos de snapshots;
- errores de checkpoint o base de datos.

Estas condiciones necesitan corrección o intervención, no repetición inmediata.

## Snapshots

El collector consulta `fetch_latest_snapshot` sólo cuando el proveedor declara
esa capacidad. Nunca inventa métricas:

- un snapshot incompleto se omite y contabiliza;
- una referencia a otro mercado falla como violación de protocolo;
- una observación anterior a `source_created_at`, cuando el proveedor informó
  ese timestamp, falla como violación de protocolo.

`ingested_at` representa únicamente la persistencia local y no limita
observaciones externas históricas. Si `source_created_at` es desconocido, el
collector no inventa el dato ni rechaza una observación por compararla con la
hora local de ingesta.

## Observaciones

`fetch_latest_observation` es una capacidad independiente. Probabilidad,
volumen y liquidez se copian como `Decimal` sólo cuando existen. La procedencia,
hora externa, hora de ingesta y hash opcional permiten reconstruir el dato sin
guardar payloads externos.

Una observación nunca se considera una cotización ejecutable. Ver
[ADR-0006](adr/0006-observation-vs-executable-quote.md).

## Observabilidad

Cada ejecución genera un `run_id` y propaga correlation y causation IDs. Los logs
estructurados registran:

- inicio, página completada, fin, fallo o exclusión por lock;
- provider y presencia del siguiente cursor;
- duración;
- mercados obtenidos, creados, actualizados e intactos;
- snapshots obtenidos, creados, duplicados y omitidos;
- observaciones obtenidas, creadas, duplicadas y omitidas;
- retries y tipo seguro de error.

`CollectorRunResult` expone los mismos contadores al worker. Cada ejecución se
audita en `collector_runs`; no se registran payloads ni mensajes remotos.

## Flujos validados

Los tests ejecutan el flujo completo:

```text
MockProvider
  → MarketDataCollector
  → Application Services
  → PostgreSQL
  → GET /markets
```

También validan reingesta incremental, checkpoints, retries agotados, snapshots
incompletos y exclusión distribuida.

El primer proveedor real también recorre:

```text
ManifoldProvider con fixture HTTP sanitizada
  → MarketDataCollector
  → Application Services
  → PostgreSQL
  → GET /markets
```

Manifold publica probabilidad actual, pero no precios ni spread completos. El
collector la guarda como `MarketObservation` y omite el `MarketSnapshot`
incompleto sin inventar valores.

El flujo histórico recorre exactamente el mismo collector:

```text
ReplayProvider + ReplayClock
  → MarketDataCollector
  → Application Services
  → PostgreSQL
  → API
```

El runtime avanza evento por evento incluso en modo acelerado para no perder
observaciones intermedias.

## Fuera de alcance

- Scheduler distribuido.
- Event Bus y publicación de eventos.
- Historial completo de snapshots.
- Recuperación específica de cursores expirados.
- Scheduler y rate limiting distribuido entre procesos.
