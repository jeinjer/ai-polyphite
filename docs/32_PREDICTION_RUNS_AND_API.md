# PredictionRun, orquestación y API

Versión: 1.0

Estado: Implementado

## Agregado durable

`PredictionRun` representa una ejecución completa sobre un mercado y un
timestamp. Guarda:

- vínculo opcional a `ExperimentRun`;
- probabilidad del mercado visible y consenso;
- confianza, recomendación, edge YES y edge equivalente NO;
- nivel de oportunidad y desacuerdo;
- estado `completed`, `abstained` o `failed`;
- hashes de configuración, entrada y resultado;
- duración, error seguro y motivo de abstención;
- correlation/causation IDs;
- pesos y cuatro `AgentPrediction`.

`AgentPrediction` conserva versión, probabilidad, confianza, recomendación,
resumen, evidencia JSON, advertencias, hashes y duración. No guarda prompts
secretos ni razonamiento privado.

## Edge

```text
edge_yes = consensus_probability - market_probability
edge_no  = -edge_yes
```

Clasificación predeterminada:

| Edge absoluto | Nivel |
|---|---|
| `< 0.03` | none |
| `0.03–<0.08` | weak |
| `0.08–<0.15` | moderate |
| `>= 0.15` | strong |

Los límites se configuran mediante variables `PREDICTION_*`. Edge es una
diferencia probabilística experimental, no una ganancia esperada ni una
cotización ejecutable.

## Transacción e idempotencia

El orquestador calcula fuera de la base y persiste el agregado completo mediante
`PredictionUnitOfWork`.

La idempotencia queda acotada por experimento:

```text
experiment_run_id + market_id + predicted_at + agent_configuration_hash
```

Para ejecuciones sin experimento existe un índice parcial equivalente donde
`experiment_run_id IS NULL`. Una repetición devuelve el agregado existente.
Experimentos distintos conservan sus propias relaciones, aunque sus hashes
semánticos sean idénticos.

## Barrera as-of

`SqlAlchemyPredictionMarketRepository` reconstruye:

- el último estado con `occurred_at <= predicted_at`;
- hasta 100 observaciones con `observed_at <= predicted_at`;
- mercados cuya ingesta ya era visible.

No entrega outcomes ni timestamps de resolución efectiva al agente. El
`ReplayProvider` y `ReplayClock` continúan siendo la barrera primaria durante
la ingesta histórica.

Los campos descriptivos del dataset sintético son inmutables. Un futuro
proveedor que permita editar retroactivamente título, descripción o cierre
programado necesitará historizar esos campos antes de usarlos en backtests
generales.

## Replay con predicciones

```powershell
make replay-predict DATASET=synthetic-lab-v1
```

El comando:

1. valida y reproduce el JSONL;
2. ejecuta el collector en cada evento;
3. libera timestamps programados sólo cuando son visibles;
4. genera predicciones para los mercados abiertos as-of;
5. vincula los runs al experimento;
6. incorpora los hashes de predicción al `result_hash`.

Cadencia:

```env
AI_POLYPHITE_REPLAY_PREDICTION_INTERVAL_HOURS=24
```

La CLI acepta `--interval-hours` o múltiples `--at <ISO-8601>`.

## API

Lectura:

- `GET /predictions`
- `GET /predictions/{prediction_id}`
- `GET /markets/{market_id}/predictions`
- `GET /experiment-runs/{experiment_id}/predictions`
- `GET /experiment-runs/{experiment_id}/prediction-evaluation`

Filtros del listado:

- `from`, `to`;
- `market_id`, `category`;
- `recommendation`, `status`, `opportunity_level`;
- `experiment_run_id`;
- `page`, `page_size`.

Ejecución manual:

- `POST /predictions/run`

Está deshabilitada por defecto. Sólo funciona fuera de producción cuando
`AI_POLYPHITE_ENABLE_MANUAL_PREDICTION_RUNS=true`. En producción devuelve
`403` aunque la variable se active accidentalmente.

## Dashboard

“Predicciones” presenta mercado, estimación, diferencia, confianza,
recomendación, abstención y advertencias. “Agentes” muestra roles, versiones y
últimas salidas.

La vista avanzada agrega evidencia, pesos, desacuerdo, duración y hashes. No
muestra ROI, P&L ni rentabilidad porque todavía no existe paper trading.
