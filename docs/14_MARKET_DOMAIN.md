# 14 — Market Domain

Estado: implementado  
Fecha: 2026-07-27

## Alcance

Este slice introduce el modelo de mercados y su persistencia. No contiene
integraciones externas, collectors, eventos, workers, API REST ni interfaz de
usuario.

## Modelo

```text
Provider 1 ─── N Market 1 ─── N MarketSnapshot
                         ├─── N MarketObservation
                         └─── N MarketStateChange
```

### Provider

Representa una fuente de mercados sin acoplar el dominio a un proveedor
concreto.

- `provider_id`: UUID interno.
- `code`: identificador estable, único y normalizado.
- `name`: nombre visible.
- `enabled`: disponibilidad lógica.
- `created_at` y `updated_at`: timestamps UTC.

### Market

Representa la identidad y los metadatos actuales de un mercado binario.

- `market_id`: UUID interno.
- `provider_id`: referencia al provider.
- `provider_market_id`: identidad asignada por el provider.
- `title`, `description` y `category`.
- `resolution_at`: cierre programado, si se conoce; no es el resultado real.
- `status`: `open`, `closed`, `resolved` o `cancelled`.
- `resolution_outcome`: `unresolved`, `yes`, `no`, `cancelled` u `other`.
- `resolved_at` y `resolution_source`: confirmación oficial nullable.
- `source_created_at`: creación externa opcional informada por el provider.
- `ingested_at`: primera persistencia local UTC.
- `updated_at`: última actualización local UTC.

La combinación `(provider_id, provider_market_id)` es única.

### MarketSnapshot

Representa una observación temporal inmutable.

- `snapshot_id`: UUID interno.
- `market_id`: mercado observado.
- `observed_at`: instante UTC de observación.
- `yes_price` y `no_price`.
- `probability`.
- `spread`.
- `volume`.
- `liquidity`.

La combinación `(market_id, observed_at)` es única. El servicio de aplicación
utiliza esta clave para persistencia idempotente y detección de conflictos.

`MarketSnapshot` es un contrato legado de métricas completas. Las observaciones
informativas y nullable se modelan como `MarketObservation`; consultar
[`20_MARKET_OBSERVATIONS.md`](20_MARKET_OBSERVATIONS.md).

## Invariantes

- Todos los identificadores son UUID no nulos.
- Todos los timestamps son timezone-aware y se normalizan a UTC.
- Strings obligatorios no pueden estar vacíos y tienen límites explícitos.
- El código de provider solo acepta minúsculas, números, `_` y `-`.
- Precios, probabilidad y spread pertenecen al rango `[0, 1]`.
- Volumen y liquidez no pueden ser negativos.
- Los valores numéricos del dominio deben ser `Decimal` finitos.
- Un snapshot validado contra un mercado debe pertenecer a ese mercado y, cuando
  `source_created_at` es conocido, no puede preceder la creación externa.
- Una resolución confirmada es terminal y coherente con el estado.
- Un mercado `closed` puede reabrirse para tolerar correcciones del provider.

No se exige que `yes_price + no_price == 1`. Esos campos pueden representar
observaciones con spread y no una partición probabilística exacta.

## Persistencia

Los modelos SQLAlchemy son adaptadores separados de las entidades de dominio.
PostgreSQL replica las invariantes críticas mediante:

- claves primarias UUID;
- claves foráneas con `ON DELETE RESTRICT`;
- constraints de rango y no negatividad;
- unicidad de provider, referencia externa y observación;
- índices por estado, categoría, resolución e historial temporal.

La migración inicial es:

```text
backend/alembic/versions/20260727_0001_create_market_domain.py
```

La migración compatible que separa timestamps es:

```text
backend/alembic/versions/20260728_0003_split_market_timestamps.py
```

Renombra `markets.created_at` a `ingested_at` sin reescribir datos y añade
`source_created_at` nullable. Así no se atribuye una fecha externa falsa a filas
existentes.

La migración `20260728_0004_add_market_observations_and_resolution.py` añade
observaciones, resultados oficiales e historial de estados sin eliminar datos.

## Repositorios

Los puertos se encuentran en `application/markets/repositories.py` y sus
adaptadores en `infrastructure/database/repositories/markets.py`.

Existen repositorios separados para:

- providers;
- markets;
- market snapshots.
- market observations;
- historial de estado.

Todos reciben una `AsyncSession`. Ejecutan `flush` para detectar errores dentro
de la operación, pero nunca hacen `commit` ni `rollback`. La futura capa de
aplicación será responsable de la transacción completa.

Los repositorios no ofrecen eliminación. Los snapshots tampoco ofrecen
actualización; `add_if_absent` realiza una inserción atómica y devuelve el
registro existente ante duplicados.

## Decisiones y trade-offs

### Provider normalizado

`docs/02_DATABASE.md` representaba originalmente el provider como texto dentro
de `markets`. El requerimiento de una entidad `Provider` llevó a normalizarlo,
evitando duplicación y permitiendo habilitar o deshabilitar una integración sin
acoplarla al mercado.

### Metadatos actuales e historia temporal

`Market` mantiene el catálogo actual y `MarketSnapshot` conserva las
observaciones históricas. El futuro sistema de eventos deberá auditar cambios
de metadatos del mercado para cumplir completamente el principio de no perder
historia.

### Resultado oficial

YES, NO, CANCELLED y outcomes incompatibles ya se conservan con fecha y fuente
cuando el proveedor ofrece evidencia. Un mercado legado resuelto sin outcome
conocido se migra a `other`, nunca se adivina.

## Validación

Los unit tests cubren:

- validación de entidades;
- timestamps UTC;
- precisión decimal;
- ciclo de estados;
- relaciones entre mercado y snapshot.

Los integration tests contra PostgreSQL cubren:

- aplicación de la migración;
- round-trip de los tres repositorios;
- precisión de `Numeric`;
- orden temporal;
- claves únicas;
- constraints de rango.

El drift entre metadata SQLAlchemy y Alembic se valida con:

```powershell
python -m alembic -c backend/alembic.ini check
```

La imagen de backend incluye los scripts de Alembic, pero el arranque de la API
no aplica migraciones automáticamente. El despliegue debe ejecutarlas como un
paso explícito antes de habilitar tráfico.

## Preparación para la siguiente etapa

Los casos de uso transaccionales e idempotentes se documentan en
`docs/15_MARKET_APPLICATION_SERVICES.md`. El siguiente slice puede exponer
queries REST de solo lectura sin introducir dependencias externas en el dominio.
