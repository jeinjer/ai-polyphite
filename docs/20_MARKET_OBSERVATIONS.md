# 20 — Observaciones y resolución de mercados

Estado: implementado  
Fecha: 2026-07-28

## MarketObservation

`MarketObservation` representa datos públicos no ejecutables observados en un
instante UTC:

| Campo | Semántica |
|---|---|
| `observation_id` | UUID interno |
| `market_id` | mercado normalizado |
| `observed_at` | instante que representa la observación |
| `probability` | estimación publicada, nullable y entre 0 y 1 |
| `volume` | actividad acumulada publicada, nullable |
| `liquidity` | liquidez informada por la fuente, nullable |
| `source_updated_at` | actualización declarada por la fuente |
| `ingested_at` | persistencia local |
| `provider_code` | procedencia normalizada |
| `raw_payload_hash` | SHA-256 opcional; nunca contiene el payload |

Al menos una de las tres métricas debe existir. Todos los valores son `Decimal`
finitos. La clave `(market_id, observed_at)` es única. Las filas no se
actualizan.

Manifold aporta observaciones mediante `fetch_latest_observation`. Sus valores
ausentes permanecen `NULL`. `MarketSnapshot` se conserva por compatibilidad y
sólo se persiste cuando todos sus campos ejecutables están presentes. Ver
[ADR-0006](adr/0006-observation-vs-executable-quote.md).

## Resultado oficial

`Market` incorpora:

- `resolution_outcome`: `unresolved`, `yes`, `no`, `cancelled` u `other`;
- `resolved_at`: instante oficial nullable;
- `resolution_source`: origen de la confirmación nullable.

Un mercado abierto o cerrado permanece `unresolved`. Un mercado `resolved`
admite YES, NO u OTHER; uno `cancelled` exige CANCELLED. Una resolución
confirmada es terminal: puede enriquecerse idempotentemente con metadatos
compatibles, pero no sobrescribirse con otro resultado.

`resolution_at` conserva por compatibilidad el cierre programado. No representa
la resolución real. En Manifold, `resolved_at` sólo procede de
`resolutionTime`.

Cada creación o cambio de estado/outcome añade una fila inmutable a
`market_state_history`.

## API

- `GET /markets/{market_id}/observations`: serie descendente, paginada y
  filtrable por `from` y `to`.
- `GET /markets/{market_id}/history`: timeline determinista con creación
  externa, ingesta local, estados, observaciones, cierre y resolución.

Los `Decimal` se serializan como strings. `GET /markets` y el detalle incluyen
la observación más reciente y el cambio entre las dos probabilidades más
recientes.

## Migración

`20260728_0004` es aditiva. Conserva todas las filas existentes y asigna:

- `open`/`closed` → `unresolved`;
- `cancelled` → `cancelled`;
- `resolved` legado → `other`, porque el resultado exacto era desconocido.

Ese `other` legado, si no tiene fuente ni fecha, puede recibir posteriormente
la primera confirmación real. Un outcome con evidencia ya registrada continúa
siendo terminal.
