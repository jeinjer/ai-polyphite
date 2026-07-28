# 15 — Market Application Services

Estado: implementado  
Fecha: 2026-07-28

## Alcance

Este módulo contiene casos de uso transaccionales para administrar el catálogo
interno y registrar observaciones. El Collector Layer lo consume, pero los
servicios continúan sin importar providers externos ni collectors.

## Servicios

### ProviderService

- Crea providers con código único.
- Actualiza nombre y estado habilitado.
- Sincroniza de forma idempotente mediante el código estable.
- Mantiene estable el código de identidad.

### MarketService

- Crea mercados únicamente para providers existentes y habilitados.
- Evita referencias externas duplicadas por provider.
- Actualiza metadatos actuales.
- Aplica las transiciones de estado definidas por el dominio.
- Sincroniza mediante `(provider_id, provider_market_id)` e informa si creó,
  actualizó o mantuvo la entidad.

### MarketSnapshotService

- Valida que el mercado exista.
- Valida la relación y el orden temporal.
- Persiste observaciones de forma idempotente.
- Nunca actualiza ni sobrescribe snapshots existentes.

## Idempotencia

La clave de idempotencia es:

```text
(market_id, observed_at)
```

PostgreSQL ejecuta un `INSERT ... ON CONFLICT DO NOTHING`, por lo que dos
procesos concurrentes no pueden crear dos observaciones para la misma clave.

- Si los valores coinciden, el servicio devuelve el snapshot existente con
  `created=false`.
- Si los valores difieren, lanza `SnapshotConflictError`.

Esto evita convertir una colisión o corrección del proveedor en una
actualización histórica silenciosa.

## Transacciones

Los servicios dependen del puerto `MarketUnitOfWork`, no de SQLAlchemy. Cada
caso de uso:

1. abre un Unit of Work;
2. consulta y valida;
3. escribe mediante repositorios;
4. hace commit explícito;
5. ejecuta rollback ante cualquier excepción.

`SqlAlchemyMarketUnitOfWork` crea una `AsyncSession` por operación. Los
repositorios no deciden el límite transaccional.

## Comandos

La entrada de cada caso de uso es una dataclass tipada:

- `CreateProvider`;
- `UpdateProvider`;
- `SynchronizeProvider`;
- `CreateMarket`;
- `UpdateMarket`;
- `SynchronizeMarket`;
- `RecordMarketSnapshot`.

Estos comandos son internos y no constituyen todavía contratos HTTP ni de un
proveedor externo.

## Testing

Los unit tests utilizan repositorios y Unit of Work falsos para validar reglas,
commits, rollback y errores de aplicación.

Los integration tests contra PostgreSQL validan:

- flujo completo de creación y actualización;
- commits visibles desde otra transacción;
- reintentos idénticos;
- conflictos con valores distintos;
- dos escrituras concurrentes de la misma observación.

## Integración posterior

La Query API y el Collector Layer consumen estos casos de uso sin introducir
FastAPI, SQLAlchemy ni Provider SDK dentro de Application. La ingesta incremental
se documenta en `18_COLLECTOR_LAYER.md`.
