# 27 — ReplayProvider

Estado: implementado  
Fecha: 2026-07-28

## Propósito

`ReplayProvider` implementa `MarketDataProvider` sobre un dataset JSONL local,
inmutable y versionado. No usa red ni PostgreSQL como fuente. Sus DTOs son los
mismos que consume `MarketDataCollector`, por lo que no existe un pipeline
histórico paralelo.

```text
JSONL validado
  → ReplayClock
  → ReplayProvider
  → MarketDataCollector
  → Application Services
  → PostgreSQL
```

## Capacidades

- listado paginado de mercados;
- detalle de mercado;
- última observación disponible;
- actualización incremental;
- health check local.

No declara snapshots ejecutables ni historial de snapshots. El dataset contiene
`MarketObservation`, no `ExecutableQuote`.

## Barrera temporal

Toda lectura se calcula con `ReplayClock.now()`:

- un mercado no existe antes de `available_at`;
- una observación no aparece antes de `observed_at`;
- un cambio de estado no aparece antes de `occurred_at`;
- una resolución no aparece antes de su `occurred_at`;
- `source_updated_at` nunca usa un evento futuro.

Los registros completos permanecen privados en el adaptador. El runtime conoce
únicamente el calendario necesario para avanzar. Ver
[ADR-0007](adr/0007-simulated-clock-and-lookahead-barrier.md).

## Paginación

El cursor `replay:<offset>` es opaco para el collector. Una página representa
el catálogo visible en el instante simulado. El reloj no avanza durante una
página.

## Compatibilidad

`MockProvider` y `ManifoldProvider` conservan su contrato y tests. Replay no se
añade al worker periódico ni a `AI_POLYPHITE_ENABLED_PROVIDERS`: sólo se crea
mediante el runtime explícito de experimentos.
