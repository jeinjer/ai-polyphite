# Políticas de entrada, sizing, riesgo y costes

## EntryPolicy

`ThresholdEntryPolicy` sólo aprueba cuando:

- la predicción está completada;
- el mercado estaba abierto en `predicted_at`;
- probabilidad, edge, confianza y observación están completos;
- los datos no son stale;
- edge y confianza superan los umbrales;
- el nivel de oportunidad está permitido;
- no existe otra posición del portfolio en ese mercado.

El resultado es `buy_yes`, `buy_no`, `abstain` o `rejected`, siempre con checks
y motivos durables.

## PositionSizingPolicy

Implementaciones:

- `FixedFractionSizing`: fracción fija de equity.
- `ConfidenceAdjustedSizing`: reduce por confianza, desacuerdo, baja liquidez y
  antigüedad.

Defaults:

- base: 1% de equity;
- máximo por mercado: 2%;
- máximo por categoría: 15%;
- exposición total: 50%;
- stake mínimo: 0.50;
- stake máximo: 10.00.

## RiskPolicy

`ConservativeRiskPolicy` valida dentro de la transacción:

- cash suficiente;
- límites mínimo y máximo;
- concentración por mercado y categoría;
- exposición total;
- exposición correlacionada declarada.

Un rechazo no crea orden, fill ni posición.

## ExecutionCostModel

- `ZeroCostModel`: control idealizado, sin costes.
- `ConservativeCostModel`: slippage adverso, fee porcentual, fee fijo y
  penalizaciones por baja liquidez o staleness.

La probabilidad observada nunca se denomina precio ejecutable. El trade persiste
probabilidad de entrada, efectiva, fees, slippage, coste neto, pérdida máxima y
modelo/version.

Los baselines usan exactamente el mismo `ExecutionCostModel` que la estrategia.
No se inventan spread, profundidad ni liquidez ausente.

## Configuración

Todas las variables están en `.env.example`. El hash de configuración resuelta
forma parte del portfolio y de las decisiones. Cambiar una política crea una
estrategia experimental distinta; no muta resultados históricos.
