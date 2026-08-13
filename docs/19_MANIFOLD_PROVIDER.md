# AI-Polyphite — Manifold Provider

Versión: 1.1
Estado: implementado  
Documentación oficial revisada: 2026-08-13

## Alcance

`ManifoldProvider` es el primer proveedor real read-only de AI-Polyphite.
Consume únicamente la API pública oficial de Manifold Markets y devuelve DTOs
normalizados del Provider SDK. No contiene autenticación, persistencia,
SQLAlchemy, collector, scheduler ni lógica de trading.

Sólo soporta mercados binarios. El runtime habilita Manifold cuando
`AI_POLYPHITE_ENABLED_PROVIDERS` contiene `manifold`. Compose lo usa por defecto
para la campaña autónoma; el default aislado de `Settings` continúa siendo
`MockProvider`.

## Endpoints oficiales

URL base: `https://api.manifold.markets`

| Endpoint | Uso |
|---|---|
| `GET /v0/search-markets` | Catálogo binario, paginación y health probe |
| `GET /v0/market/{id}` | Detalle directo fuera del ciclo de catálogo |

Las operaciones de lectura utilizadas no requieren API key. Aun así, una
respuesta HTTP `401` o `403` se transforma en `ProviderAuthenticationError` para
detectar un posible cambio de política.

Referencias:

- [Documentación oficial de la API](https://docs.manifold.markets/api)
- [Términos de servicio de Manifold](https://docs.manifold.markets/terms)

## Filtro binario

La consulta de catálogo envía `contractType=BINARY`. El adaptador también exige
localmente `outcomeType == "BINARY"`, porque los filtros y payloads externos no
se consideran confiables por sí solos.

Se ignoran explícitamente:

- mercados numéricos;
- mercados de opción múltiple;
- polls, pseudo-numéricos y futuros tipos incompatibles;
- payloads inválidos, que generan `ProviderProtocolError` en lugar de completar
  datos por suposición.

Un detalle incompatible devuelve `None`.

## Paginación

Cada página utiliza:

```text
sort=newest
filter=all
contractType=BINARY
limit=<tamaño solicitado>
beforeTime=<createdTime del último resultado crudo>
```

El cursor público es opaco y se codifica como
`manifold:created-time:<milisegundos>`. El collector no lo interpreta. El avance
se calcula desde el último resultado crudo, incluidos los incompatibles, para
que el filtrado local no bloquee la paginación.

Limitación conocida: `beforeTime` se basa en creación, no en actualización.
Manifold no anuncia `INCREMENTAL_MARKETS`; cada ciclo completo recorre el
catálogo actual y delega la idempotencia a Application. Varios mercados creados
en el mismo milisegundo del borde constituyen un riesgo de precisión externo.

La operación autónoma usa `AI_POLYPHITE_MANIFOLD_SYNC_MODE=recent`. Cada ciclo
realiza dos consultas acotadas y fusiona por `provider_market_id`:

```text
sort=last-updated
filter=all
contractType=BINARY
limit=<tamaño solicitado>

sort=last-updated
filter=resolved
contractType=BINARY
limit=<tamaño solicitado>
```

Ese modo no emite cursor. El primer barrido mantiene los mercados activos; el
segundo recupera resoluciones recientes aunque Manifold no avance
`lastUpdatedTime` al resolver y el mercado ya haya quedado fuera del listado
general. Si un mercado aparece en ambos, prevalece el payload del barrido
`resolved`. El modo `catalog` conserva la paginación completa para importaciones
explícitas.

## Mapeo de estados

| Datos de Manifold | Estado normalizado |
|---|---|
| `isResolved=true`, `resolution=CANCEL` | `cancelled` |
| `isResolved=true`, otra resolución | `resolved` |
| no resuelto y `closeTime <= now` | `closed` |
| no resuelto y sin cierre vencido | `open` |

Los resultados YES, NO y CANCEL se normalizan y persisten. Otros outcomes
resueltos se conservan como `other`. `resolution_at` recibe `closeTime` como
cierre programado; `resolved_at` sólo recibe `resolutionTime` cuando
`isResolved=true`.

## Timestamps y provenance

- Los timestamps Unix en milisegundos se convierten a UTC timezone-aware.
- `source_created_at` proviene de `createdTime`.
- `source_updated_at` proviene de `lastUpdatedTime` cuando existe.
- `observed_at` es la hora UTC local en que AI-Polyphite vio una combinación
  nueva de probabilidad, volumen, liquidez o resolución.
- El adaptador no asigna `ingested_at`; Application registra la hora local de
  persistencia.
- `provider_market_id` conserva sin cambios el `id` de Manifold.

La migración renombra el anterior `markets.created_at` local a `ingested_at`
conservando todos sus valores, y añade `source_created_at` nullable. Las filas
existentes siguen siendo válidas sin atribuirles una fecha externa ficticia.

## Probabilidad, observaciones y snapshots

La `probability` de Manifold se normaliza como `Decimal` y representa la
probabilidad actual publicada por la API. No se considera una cotización
ejecutable.

`fetch_latest_observation` expone la observación actual si el payload contiene
probabilidad, volumen o liquidez:

- `probability`, `volume` y `totalLiquidity` se copian sólo si existen;
- las métricas ausentes permanecen en `None`;
- `yes_price`, `no_price` y `spread` no forman parte de la observación;
- no se anuncia historial de snapshots;
- no se infieren complementos ni defaults.

El Collector persiste esos datos como `MarketObservation`. El payload ya
devuelto por `search-markets` se reutiliza para la observación, por lo que no se
hace una consulta de detalle por mercado. Manifold no anuncia
`LATEST_SNAPSHOT`: así se construye historia sin fabricar precios operables.
El adaptador conserva una firma del contenido durante la vida del worker y
reutiliza `observed_at` mientras los valores sean idénticos; así un polling
horario no crea observaciones ni predicciones duplicadas. `lastUpdatedTime`
permanece separado porque Manifold puede no actualizarlo cuando cambian métricas
de mercado.
Si Manifold cambia métricas conservando el mismo `lastUpdatedTime`, la
observación inmutable ya persistida prevalece: el conflicto se registra y se
omite sin detener el resto del catálogo.

Una resolución YES/NO ya confirmada también es append-only. Si la API pasa a
publicar `CANCELLED` u otro resultado incompatible para el mismo ID, el
Collector registra `collector_market_resolution_conflict_skipped`, conserva el
hecho histórico y continúa procesando y checkpointando el catálogo. El
adaptador no decide ni reescribe este conflicto.

## Confiabilidad

- Timeout por request: 10 segundos por defecto.
- Límite cooperativo local: 450 requests/minuto por defecto.
- Límite oficial documentado: 500 requests/minuto por IP.
- El modo `recent` usa dos requests de catálogo por ciclo: general y resueltos.
- HTTP `429` genera `ProviderRateLimitError` y conserva un `Retry-After` válido.
- timeouts, fallos de red y `5xx` generan `ProviderUnavailableError`.
- JSON inválido, schemas incompatibles, cursores inválidos y `4xx` inesperados
  generan `ProviderProtocolError`.
- `401` y `403` generan `ProviderAuthenticationError`.

Retries y backoff permanecen en `MarketDataCollector`; cada request HTTP del
adaptador es acotado y atraviesa el mismo rate limiter. El rate limiter es local
al proceso. Antes de ejecutar collectors Manifold concurrentes será necesario
coordinar el límite agregado.

## Health check

El probe consulta un único resultado binario del endpoint de búsqueda y valida
su schema. `health_check()` devuelve el modelo normalizado sin filtrar payloads
ni mensajes remotos.

## Términos y restricciones

La implementación respeta las restricciones publicadas por Manifold:

- la automatización usa la API pública y respeta sus límites;
- no se realiza scraping fuera de esa API;
- este proyecto sigue siendo investigación no comercial y paper trading;
- Manifold exige otra licencia para determinados usos comerciales de
  entrenamiento de IA;
- la API está marcada como alpha y puede cambiar.

Este resumen es una restricción de ingeniería, no asesoramiento legal. Los
términos deberán revisarse antes de cualquier uso comercial o cambio material
en el uso de datos.

## Tests

Las fixtures HTTP son sintéticas y sanitizadas: modelan el schema oficial sin
datos personales ni copiar contenido real. La cobertura incluye:

- filtro binario y avance del cursor;
- estados open, closed, resolved y cancelled;
- normalización UTC y `Decimal`;
- rate limiting, timeouts y errores HTTP tipados;
- contract tests reutilizables de `MarketDataProvider`;
- Manifold fixture → Collector → PostgreSQL → `GET /markets`;
- resolución tardía visible sólo en `filter=resolved` → Collector → PostgreSQL;
- persistencia de observaciones y outcomes YES/CANCEL;
- reutilización del catálogo sin requests de detalle redundantes;
- modo reciente acotado y verificación de que no se crean snapshots inventados.
