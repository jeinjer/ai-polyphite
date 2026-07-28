# Liquidación, performance y API

## Liquidación

Sólo una resolución oficial visible puede cerrar la posición:

- `YES`: paga unidades a posiciones YES.
- `NO`: paga unidades a posiciones NO.
- `CANCELLED`: devuelve el coste neto y registra P&L cero.
- `OTHER`: permanece pendiente y genera alerta; no se inventa un payout.
- `UNRESOLVED`: permanece abierta.

El settlement es idempotente y guarda resultado, timestamp oficial, payouts,
policy, hash y contexto de trazabilidad.

## Métricas simuladas

- capital inicial y final;
- resultado neto y ROI simulado;
- P&L realizado/no realizado;
- costes;
- win rate, profit factor y promedios;
- máximo drawdown y exposición;
- cobertura, abstenciones y rechazos;
- desglose por categoría, oportunidad, edge y confianza;
- mercados resueltos independientes y concentración del beneficio.

El estado de evidencia progresa por umbrales configurables:
`insufficient_sample`, `preliminary_result`, `under_observation` y
`sufficient_to_expand_validation`. Nunca se interpreta como garantía.

## Baselines

- `no_trade`
- `market_follow`
- `fixed_threshold`

Usan mismo capital, stake y costes. CANCELLED se reembolsa; OTHER no se opera.

## API read-only

- `GET /paper-portfolios`
- `GET /paper-portfolios/{id}`
- `GET /paper-portfolios/{id}/performance`
- `GET /paper-portfolios/{id}/equity-curve`
- `GET /paper-trades` y `/{id}`
- `GET /paper-positions` y `/{id}`
- `GET /trade-decisions`
- `GET /paper-settlements`
- `GET /experiment-runs/{id}/paper-performance`

Listados soportan paginación y filtros por portfolio, mercado, categoría, lado,
estado, outcome, experimento y rango temporal donde corresponde.

Controles POST de desarrollo:

- `POST /paper-portfolios`
- `POST /paper-trading/run`
- `POST /paper-trading/settle`

Requieren `AI_POLYPHITE_ENABLE_MANUAL_PAPER_TRADING=true` y siguen bloqueados en
`production` aunque el flag esté presente.

## Dashboard

Las vistas Cartera, Operaciones, Posiciones y Rendimiento tienen modos simple y
avanzado, español/inglés, estados no expresados sólo por color, tooltips,
alertas y hashes en modo avanzado. Todas muestran:

> Resultados simulados. No representan dinero real ni garantizan rendimientos futuros.
