# AI-Polyphite — Provider SDK

Version: 1.0  
Status: Implemented

## Objetivo

El Provider SDK es la frontera neutral entre AI-Polyphite y cualquier fuente de
mercados de predicción. Normaliza lectura de catálogos, detalle, precios e
historial sin introducir conceptos de un proveedor en Domain, Application, REST
o Frontend.

El SDK no realiza ingesta. El Collector Layer implementado posteriormente lo
consume sin incorporar HTTP, persistencia ni mappers dentro de `providers`.

## Ubicación y dependencias

```text
backend/src/predictionlab/providers/
├── base/       # Contrato, DTOs, capacidades, health y registry
├── manifold/   # Adaptador HTTP read-only para mercados binarios
├── mock/       # Implementación determinista local
├── replay/     # Dataset histórico local con barrera temporal
└── defaults.py # Composición local explícita
```

Regla de dependencia:

```text
Proveedor externo → Provider SDK → Collector Layer → Application → Domain
```

El paquete `providers` no importa FastAPI, SQLAlchemy, Application ni Domain.
Los DTOs externos son deliberadamente distintos de las entidades persistidas.

## Contrato `MarketDataProvider`

Todas las operaciones son asíncronas:

| Operación | Resultado |
|---|---|
| `fetch_markets` | Página normalizada de mercados |
| `fetch_market` | Mercado por ID externo o `None` |
| `fetch_latest_snapshot` | Última observación o `None` |
| `fetch_snapshots` | Página de observaciones históricas |
| `health_check` | Estado, latencia, timestamp y tipo seguro de error |

Los cursores son strings opacos. Un consumidor debe devolver el cursor recibido
sin interpretarlo.

## DTOs normalizados

- `ProviderMarket`: identidad externa, título, descripción, categoría, estado y
  timestamps de la fuente.
- `ProviderMarketSnapshot`: precios, probabilidad, spread, volumen y liquidez.
- `ProviderMarketObservation`: probabilidad, volumen o liquidez nullable sin
  semántica de ejecución.
- `FetchMarketsRequest` y `MarketBatch`: filtros incrementales y paginación.
- `FetchSnapshotsRequest` y `SnapshotBatch`: historial paginado.

Los modelos son Pydantic estrictos, inmutables, sin campos extra, con timestamps
timezone-aware normalizados a UTC y números finitos dentro de rango.

Los campos de snapshot son opcionales porque algunas fuentes no publican todas
las métricas. El futuro mapper decidirá qué datos mínimos requiere cada caso de
uso; el SDK no inventa valores.

## Capacidades

`ProviderCapabilities` evita comprobar tipos concretos. El contrato inicial
reconoce:

- listado de mercados;
- detalle;
- último snapshot;
- última observación;
- snapshots históricos;
- actualización incremental del catálogo.

`require()` falla de forma temprana con `ProviderCapabilityError`.

## Health check

`health_check()` nunca propaga fallos del proveedor. Devuelve:

- `healthy`;
- `degraded`;
- `unhealthy`.

Incluye latencia y el nombre del tipo de error, pero no mensajes remotos,
payloads ni credenciales. Las operaciones de datos producen excepciones tipadas
que el Collector Layer clasifica para retry y backoff.

## Registry y factories

`ProviderRegistry` registra factories por un código estable, valida duplicados y
crea instancias nuevas. No existe un singleton mutable.

La composición local se obtiene así:

```python
from predictionlab.providers import create_default_provider_registry

registry = create_default_provider_registry()
provider = registry.create("mock")
health = await provider.health_check()
```

El registry por defecto contiene únicamente `MockProvider`. El composition root
habilita `ManifoldProvider` sólo cuando aparece en
`AI_POLYPHITE_ENABLED_PROVIDERS`. Su contrato y semántica están documentados en
`19_MANIFOLD_PROVIDER.md`.

## MockProvider

`MockProvider` funciona sin red, secretos ni base de datos. Incluye:

- tres mercados deterministas con estados distintos;
- snapshots deterministas;
- filtros por estado y actualización;
- paginación por cursor;
- detalle, último snapshot e historial;
- latencia y disponibilidad configurables;
- health check real sobre su estado configurado;
- datasets inyectables para tests específicos.

Sirve para desarrollo local, tests de contrato y validación punta a punta del
núcleo existente. No simula HTTP ni pretende reproducir peculiaridades de un
proveedor real.

## Integración

`MarketDataCollector` consume estos DTOs, los mapea a Application Services,
persiste mercados y snapshots y mantiene checkpoints durables. El SDK continúa
sin importar el collector ni las capas internas.

## Añadir un proveedor

Una implementación futura debe:

1. Subclasificar `MarketDataProvider`.
2. Traducir payloads externos a los DTOs normalizados.
3. Declarar sólo capacidades realmente soportadas.
4. Implementar un probe de health acotado.
5. Convertir fallos externos en errores tipados y seguros.
6. Registrar su factory en la composición del entorno.
7. Pasar tests contractuales y de integración.

No debe importar ni devolver entidades de Domain, ejecutar persistencia o
publicar eventos.

`ReplayProvider` es la tercera implementación contractual. No se registra en el
worker periódico: el runtime de experimentos lo compone con un `ReplayClock` y
un dataset explícito.

Los errores HTTP y de protocolo se normalizan como
`ProviderUnavailableError`, `ProviderRateLimitError`,
`ProviderProtocolError` y `ProviderAuthenticationError`.

## Riesgos conocidos

- Los primeros proveedores reales pueden exigir extender DTOs para mercados con
  más de dos resultados.
- La semántica de volumen y liquidez no es idéntica entre fuentes; debe
  documentarse por adaptador.
- Health y disponibilidad no garantizan frescura ni calidad de datos.
- Retries, checkpoints y observabilidad de ingesta pertenecen al Collector
  Layer, documentado en `18_COLLECTOR_LAYER.md`.
