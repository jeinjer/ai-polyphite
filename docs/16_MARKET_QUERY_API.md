# 16 — Market Query Layer y API REST

Estado: implementado  
Fecha: 2026-07-28

## Alcance

Este slice expone consultas de solo lectura sobre el catálogo interno. No añade
endpoints de escritura, frontend, collectors ni integraciones externas.

## Query Layer

La capa de aplicación define read models independientes del dominio:

- `ProviderSummary`;
- `SnapshotSummary`;
- `MarketSummary`;
- `MarketDetail`;
- `MarketPage`.

`MarketQueryService` implementa listado y detalle mediante el puerto
`MarketReadRepository`. La implementación SQLAlchemy:

- utiliza una sesión de lectura por operación;
- obtiene provider y último snapshot sin N+1;
- calcula el total para la paginación;
- aplica un segundo orden por `market_id` para resultados deterministas.

## `GET /markets`

Devuelve una página de mercados con provider y último snapshot.

| Parámetro | Default | Descripción |
|---|---:|---|
| `page` | `1` | Página basada en uno |
| `page_size` | `20` | Entre 1 y 100 |
| `status` | — | `open`, `closed`, `resolved` o `cancelled` |
| `provider` | — | Código exacto del provider |
| `category` | — | Categoría exacta |
| `order_by` | `updated_at` | `updated_at`, `ingested_at`, `resolution_at` o `title` |
| `direction` | `desc` | `asc` o `desc` |

Los filtros se combinan con `AND`.

Cada mercado expone `source_created_at` nullable, informado por el proveedor, e
`ingested_at`, asignado por la persistencia local. La API no presenta ambos
conceptos bajo un timestamp ambiguo.

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "pages": 0
}
```

## `GET /markets/{market_id}`

Devuelve los metadatos completos, provider y último snapshot.

- `200`: mercado encontrado.
- `404`: mercado inexistente.
- `422`: UUID o parámetros inválidos.

El endpoint no expande todo el historial para evitar respuestas sin límite. Los
snapshots históricos permanecen en PostgreSQL.

## Precisión numérica

Los valores `Decimal` se serializan como strings JSON. Esto evita introducir
errores binarios antes de que el frontend decida cómo representarlos.

## OpenAPI

FastAPI documenta esquemas, enums, límites y errores. Los operation IDs estables
son `list_markets` y `get_market`. La interfaz está disponible en `/docs`.

## Observabilidad

Cada request:

- recibe o propaga `X-Correlation-ID`;
- recibe o propaga W3C `traceparent`;
- genera un log JSON con método, ruta real, plantilla, estado y latencia;
- actualiza métricas por método, plantilla de ruta y estado.

Usar `/markets/{market_id}` como etiqueta evita cardinalidad ilimitada por UUID.
Las métricas registran count, duración total, promedio y máximo. Son locales al
proceso; la exportación a Prometheus/OpenTelemetry sigue pendiente.

El Query Service también registra resultado, total, filtros y duración sin
incluir payloads completos.

## Testing

Los unit tests cubren validación, paginación, not found, mapeo HTTP, OpenAPI y
métricas. Los integration tests contra PostgreSQL cubren filtros combinados,
ordenamiento, último snapshot, detalle, `404`, correlation ID y rutas
normalizadas.

## Próxima etapa

El siguiente slice puede construir un frontend mínimo para listar mercados y
abrir su detalle.
