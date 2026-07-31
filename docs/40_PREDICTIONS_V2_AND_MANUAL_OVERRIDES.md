# Predicciones v2, evaluación comercial y overrides manuales

Versión: 2.0
Estado: Implementado
Fecha: 2026-07-30

## Objetivo

Separar la estimación probabilística de la decisión comercial y de la
ejecución paper. El sistema automático continúa funcionando por defecto; la
intervención manual es una excepción explícita, trazable y simulada.

## Flujo automático predeterminado

```text
mercado + observaciones visibles
  → cuatro agentes deterministas
  → PredictionRun
  → CommercialEvaluation de campaña
  → política automática de entrada y riesgo
  → TradeDecision automática
  → orden, trade y posición paper
```

`PredictionRun` responde qué estima el sistema. `CommercialEvaluation` responde
si esa estimación justifica una entrada bajo costes, frescura, portfolio y
umbrales concretos. `TradeDecision` registra qué hizo la simulación.

## ConsensusAgent 2.0

Cuando el input es válido, el consenso persiste:

- `consensus_probability`;
- `estimated_outcome` (`yes` o `no`, usando 0,5 como frontera);
- `consensus_confidence`;
- edge YES y NO;
- desacuerdo, pesos, evidencia y warnings.

Confianza baja o edge pequeño se guardan como warnings y no eliminan la
predicción. Sigue existiendo abstención ante un mercado no abierto, ausencia o
antigüedad excesiva de datos, estimaciones insuficientes, desacuerdo
estructuralmente incompatible o una probabilidad extrema sin evidencia mínima.

Los runs nuevos usan estado `predicted`. Los estados históricos `completed`,
`abstained` y `failed` siguen siendo legibles y no se reescriben.

## Evaluación comercial

Una evaluación pertenece a `(prediction, portfolio, campaign, configuration)`.
Guarda:

- lado potencial `buy_yes`, `buy_no` o `none`;
- edge bruto;
- fees, slippage y otros costes estimados;
- edge neto;
- frescura de datos;
- confianza;
- motivos, warnings y hashes;
- etiqueta `actionable`, `not_actionable` o `not_evaluable`.

La campaña conservadora mantiene los umbrales anteriores. La campaña
`experimental-v1`, habilitada por defecto en el runtime continuo, usa otro
portfolio y exige:

```env
AI_POLYPHITE_EXPERIMENTAL_MIN_NET_EDGE=0.015
```

Ambas campañas reutilizan el mismo batch inmutable de predicciones por ciclo.
No vuelven a ejecutar los agentes ni mezclan balances.

## Override manual

`POST /paper-trading/manual-trades` permite probar una hipótesis humana:

```json
{
  "prediction_run_id": "uuid",
  "side": "yes",
  "requested_stake": "2.00",
  "reason": "Hipótesis explícita y auditable",
  "idempotency_key": "uuid-generado-por-el-cliente"
}
```

Si no se indica portfolio, la API usa uno estable llamado
`Manual paper overrides`. El botón del dashboard:

- no pausa ni desactiva la campaña automática;
- deja elegir YES o NO independientemente de los agentes;
- exige motivo y confirmación;
- muestra claramente que no usa dinero real;
- registra `decision_source=manual_override`;
- conserva idempotencia, mercado abierto, datos actuales y límites de riesgo.

Una evaluación `not_actionable` no bloquea el override. Un portfolio pausado,
mercado cerrado, datos no vigentes, stake inválido o límite de riesgo sí pueden
rechazarlo.

## API de predicciones

### Listado liviano

`GET /predictions` devuelve sólo campos de lista y la evaluación comercial más
reciente. Si no se filtra una campaña, prioriza `conservative-v1`, que es la
ruta automática predeterminada. No carga las salidas de agentes.

Parámetros principales:

- `page` y `page_size` (`25` o `50`);
- `commercial_label`;
- `estimated_outcome`;
- `provider_code`, `category`, `portfolio_id` y `campaign_id`;
- `from`, `to`;
- `sort`: `predicted_at`, `market_probability`,
  `consensus_probability`, `consensus_confidence` o `net_edge`;
- `direction`: `asc` o `desc`.

### Detalle bajo demanda

`GET /predictions/{prediction_id}` carga agentes, hashes, evaluación comercial
y ejecuciones paper relacionadas. El frontend sólo solicita este payload al
abrir `/predictions/{prediction_id}`.

`GET /agent-predictions` conserva la lectura técnica completa utilizada por el
monitor de agentes.

## Dashboard

`/predictions` ofrece lista paginada, filtros y ordenamiento del lado del
servidor. Cada fila presenta:

- mercado;
- probabilidad del mercado;
- probabilidad estimada;
- confianza;
- resultado estimado;
- conveniencia;
- `Operar` u `Operar igualmente`;
- enlace al detalle.

React Query mantiene la página anterior durante la carga de la siguiente. El
detalle y sus agentes se cargan de forma diferida, evitando el payload global
anterior.

## Configuración

```env
AI_POLYPHITE_EXPERIMENTAL_CAMPAIGN_ENABLED=true
AI_POLYPHITE_EXPERIMENTAL_MIN_NET_EDGE=0.015
AI_POLYPHITE_ENABLE_MANUAL_PAPER_OVERRIDES=true
```

El backend bloquea overrides en producción aunque se configure
accidentalmente la variable. No existen brokers, wallets, claves, firmas ni
dinero real.

## Trazabilidad y métricas

Las decisiones deben segmentarse por:

- `decision_source`: `automatic` o `manual_override`;
- portfolio;
- campaign y hash de configuración.

No se deben combinar resultados manuales y automáticos en una única métrica de
estrategia. Los logs incluyen IDs, correlation/causation IDs y
`simulation_only=true`, nunca secretos.

Las vistas `/portfolio`, `/trades`, `/positions` y `/performance` comparten un
selector de cartera. El dashboard prioriza `Autonomous Manifold paper
validation`, filtra cada query por su `portfolio_id` y muestra en cada trade
`Automática` o `Manual`. Cambiar el selector es la única forma de mezclar el
contexto visible; las métricas siguen consultándose por cartera.
