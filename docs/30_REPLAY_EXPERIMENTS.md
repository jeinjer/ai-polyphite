# 30 — Ejecutar experimentos históricos

Estado: implementado

## Modos

- `step`: procesa el siguiente instante con eventos;
- `accelerated`: procesa todos los instantes sin esperas reales;
- `until`: procesa hasta un timestamp UTC incluido;
- `reset`: devuelve un `ReplayClock` al inicio.

El modo programático permite repetir `step` sobre una misma instancia. Los
comandos CLI son ejecuciones autocontenidas: `replay-step` procesa un paso desde
el inicio y `replay-reset` valida el dataset e inicializa su reloj en el origen.

## CLI

```powershell
make replay DATASET=synthetic-lab-v1 MODE=accelerated
make replay DATASET=synthetic-lab-v1 MODE=until UNTIL=2026-01-04T00:00:00Z
make replay-step DATASET=synthetic-lab-v1
make replay-reset DATASET=synthetic-lab-v1
```

Ejecución directa:

```powershell
.\.venv\Scripts\python.exe -m predictionlab.runtime.replay_cli run `
  --dataset synthetic-lab-v1 --mode accelerated --seed 0
```

## ExperimentRun

Cada ejecución registra UUID, dataset y versión, tiempos operativo y simulado,
estado, semilla, hash de configuración, versión de código opcional, hash de
resultado, correlation ID y tipo seguro de error.

`configuration_hash` deriva de dataset, hash de contenido, modo, límite y
semilla. `result_hash` añade el fin simulado alcanzado. No incluye UUIDs,
duraciones de pared ni IDs internos de persistencia.

## API

- `GET /replay-datasets`
- `GET /experiment-runs`
- `GET /experiment-runs/{run_id}`

El dashboard muestra el catálogo y la auditoría sólo en vista avanzada. La
vista simple muestra “Laboratorio histórico disponible”.

## Reproducibilidad

En una base limpia, una ejecución completa persiste 20 mercados, 80
observaciones y sus estados finales. Una reejecución con igual configuración
conserva el mismo contenido semántico y el mismo `result_hash`.

Esto no demuestra calidad predictiva. Sólo establece una base temporal y
auditable para los próximos `ReasoningAgent`, `MarketAgent`, `SkepticAgent` y
`ConsensusAgent`.
