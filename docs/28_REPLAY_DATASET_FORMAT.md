# 28 — Formato de datasets de replay

Estado: implementado  
Schema: `1`

El formato canónico es UTF-8 JSONL. La primera línea contiene metadata; cada
línea posterior contiene un evento. Las líneas vacías se ignoran al cargar,
pero los datasets versionados se generan sin ellas.

## Metadata

```json
{
  "type": "metadata",
  "dataset_id": "synthetic-lab",
  "version": "1.0.0",
  "schema_version": "1",
  "created_at": "2026-01-01T00:00:00Z",
  "description": "Descripción segura",
  "content_sha256": "<64 caracteres hex>",
  "replay_start": "2026-01-01T00:00:00Z",
  "replay_end": "2026-01-08T14:00:00Z",
  "market_count": 20,
  "observation_count": 80
}
```

`content_sha256` es el SHA-256 de todas las líneas posteriores, unidas con `\n`
y con un `\n` final. Se valida antes de exponer cualquier dato.

## Registros

### Mercado

Campos: `type=market`, `provider_market_id`, `available_at`, `title`,
`description`, `category`, `resolution_at` e `initial_status=open`.

### Observación

Campos: `type=observation`, `provider_market_id`, `observed_at`, probabilidad,
volumen y liquidez nullable, `source_updated_at` y hash opcional. Al menos una
métrica debe existir.

### Cambio de estado

Campos: `type=state_change`, `provider_market_id`, `occurred_at` y `status`.
Schema 1 admite `open` y `closed`; el resultado terminal pertenece al registro
de resolución.

### Resolución

Campos: `type=resolution`, `provider_market_id`, `occurred_at`, `outcome`
(`yes`, `no`, `cancelled`) y `source`.

## Validaciones

- todos los timestamps incluyen zona y se normalizan a UTC;
- IDs de mercado únicos y referencias existentes;
- eventos no anteriores a la creación del mercado;
- rango y contadores coincidentes con metadata;
- observaciones únicas por mercado e instante;
- una única resolución por mercado;
- hash correcto.

Fallos estructurales producen `ReplayDatasetFormatError`; un hash distinto
produce `ReplayDatasetIntegrityError`.
