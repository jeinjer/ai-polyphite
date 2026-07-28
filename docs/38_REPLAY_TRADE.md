# Replay reproducible con paper trading

## Ejecución

```powershell
make replay-trade DATASET=synthetic-lab-v1
```

Parámetros:

```powershell
make replay-trade DATASET=synthetic-lab-v1 MODE=accelerated PREDICTION_INTERVAL_HOURS=24
```

El comando compone el mismo Collector, PredictionOrchestrator y
PaperTradingOrchestrator de la aplicación:

```text
dataset JSONL
  → ReplayClock
  → mercado visible
  → predicciones debidas
  → decisiones y posiciones
  → settlements visibles
  → ExperimentRun + hashes
```

## Reproducibilidad

El resultado semántico depende de:

- SHA-256 y versión del dataset;
- rango temporal;
- cadencia de predicción;
- seed;
- configuración de agentes;
- configuración de paper trading;
- versión de políticas y costes.

IDs operativos, latencias y correlation IDs no entran en hashes semánticos.
Dos ejecuciones iguales producen los mismos hashes, conteos y equity final,
aunque tengan IDs de experimento distintos.

## Barrera anti-lookahead

En cada timestamp sólo son visibles estados y observaciones anteriores o iguales
al reloj simulado. La resolución futura no se usa para decidir. El settlement
se ejecuta únicamente cuando `resolved_at <= visible_at`.

## Verificación

```powershell
.\scripts\check.ps1 -Integration -E2E
```

Incluye replay doble contra PostgreSQL real, queries, métricas, drift Alembic,
tests unitarios, integración, build frontend y Playwright.

## Interpretación

El replay evalúa una hipótesis sobre datos controlados. No demuestra
ejecutabilidad, liquidez futura ni rendimiento real. El dataset sintético sirve
para probar invariantes y reproducibilidad, no para afirmar ventaja estadística.
