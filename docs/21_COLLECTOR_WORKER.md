# 21 — Worker de sincronización

Estado: implementado  
Fecha: 2026-07-28

## Diseño

El worker es un proceso separado de FastAPI. Compone un
`MarketDataCollector` por fuente habilitada y ejecuta ciclos independientes con
`asyncio.TaskGroup`. Los retries siguen perteneciendo al Collector Layer y la
exclusión entre procesos usa el advisory lock PostgreSQL existente.

No se introducen Celery, scheduler distribuido ni Redis como fuente de verdad.

## Configuración

```env
AI_POLYPHITE_ENABLED_PROVIDERS=mock,manifold
AI_POLYPHITE_COLLECTOR_INTERVAL_SECONDS=300
AI_POLYPHITE_PROVIDER_INTERVALS_SECONDS=mock=300,manifold=600
AI_POLYPHITE_COLLECTOR_RUN_IMMEDIATELY=true
```

Los códigos se validan al iniciar. Los únicos adaptadores actuales son `mock` y
`manifold`; un código desconocido detiene el arranque con un error explícito.
El default habilita únicamente `mock`, por lo que tests y desarrollo no llaman
a una fuente real accidentalmente.

## Ejecución

```powershell
make collect-once PROVIDER=manifold
make collector-worker
```

Equivalente en PowerShell:

```powershell
.\scripts\collect.ps1 -Mode Once -Provider manifold
.\scripts\collect.ps1 -Mode Worker
```

Docker Compose incluye el servicio `worker`, que espera la migración y comparte
PostgreSQL con la API.

## Ciclo de vida

Cada ciclo crea `run_id` y correlation ID. SIGINT/SIGTERM activa un apagado
cooperativo: no se programa otro ciclo, se libera el lock y se cierran clientes
HTTP y conexiones. Una fuente fallida no finaliza los loops de las demás.
