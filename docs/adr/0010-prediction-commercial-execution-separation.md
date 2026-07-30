# ADR-0010: Separar predicción, evaluación comercial y ejecución simulada

- **Estado:** Accepted
- **Fecha:** 2026-07-30
- **Alcance:** predicciones, campañas experimentales y paper trading

## Contexto

`ConsensusAgent` 1.x utilizaba algunos umbrales comerciales —confianza, edge y
desacuerdo— para decidir si publicaba una predicción. Esto mezclaba dos
preguntas diferentes:

1. ¿qué probabilidad estima el sistema?
2. ¿conviene abrir una operación bajo una campaña y sus costes?

El resultado era una cobertura predictiva muy baja y hacía imposible estudiar
la calibración de estimaciones que no superaban el umbral de entrada.

Además, el dashboard necesita permitir una intervención humana excepcional sin
detener ni reemplazar la campaña automática. Esa intervención sigue siendo
exclusivamente simulada.

## Decisión

El flujo durable queda separado en tres artefactos:

```text
PredictionRun
  → CommercialEvaluation
  → TradeDecision
```

- `ConsensusAgent` 2.0 publica probabilidad, resultado estimado, confianza y
  warnings siempre que existan datos estructurales suficientes.
- Confianza baja y edge pequeño dejan de ser causas de abstención predictiva.
- `CommercialEvaluation` calcula edge bruto, costes estimados, edge neto y la
  etiqueta `actionable`, `not_actionable` o `not_evaluable`.
- Cada evaluación pertenece a una campaña y portfolio concretos; no modifica
  ni sobrescribe la predicción.
- La campaña conservadora existente continúa siendo la ejecución automática
  predeterminada.
- Una campaña experimental paralela usa su propio portfolio y exige un edge
  neto mínimo de 0,015 por defecto.
- El override manual permite elegir YES/NO y stake aunque los agentes o la
  evaluación comercial no recomienden operar.
- El override manual sólo omite el gate predictivo/comercial. Mantiene mercado
  abierto, datos vigentes, idempotencia, límites de riesgo y contabilidad.
- Toda decisión manual guarda `decision_source=manual_override`, motivo y clave
  de idempotencia, y usa un portfolio simulado separado.
- No existe ninguna ruta de ejecución con dinero real.

Los registros históricos permanecen append-only. La migración agrega datos
opcionales y no recalcula predicciones pasadas.

## Consecuencias positivas

- Se puede medir cobertura y calibración sin confundirlas con ejecutabilidad.
- Una misma predicción puede evaluarse bajo campañas con costes distintos.
- La política automática sigue siendo reproducible y comparable.
- Las hipótesis manuales quedan auditables sin contaminar métricas automáticas.
- El detalle de una predicción puede reconstruir agentes, evaluación y
  ejecuciones relacionadas.

## Consecuencias negativas

- Aumenta la cantidad de artefactos y relaciones persistidas.
- La lista debe elegir explícitamente qué evaluación comercial mostrar cuando
  existen varias campañas.
- Un override humano puede perder capital simulado aunque el sistema automático
  lo hubiera evitado.
- Las campañas paralelas requieren interpretar métricas por portfolio y fuente
  de decisión, nunca mezcladas.

## Relación con decisiones anteriores

Este ADR extiende ADR-0008 y ADR-0009. No elimina los agentes deterministas ni
la frontera estructural de simulación. Reemplaza únicamente la interpretación
de abstención comercial dentro del consenso inicial.

## Alternativas descartadas

### Forzar al consenso a operar siempre

Descartado porque predecir no equivale a ejecutar. Los datos estructuralmente
inválidos todavía deben producir una abstención y los gates comerciales siguen
siendo necesarios.

### Convertir el botón manual en el flujo principal

Descartado porque impediría la observación autónoma y mezclaría decisiones
humanas con la campaña automática.

### Guardar la etiqueta comercial dentro de `PredictionRun`

Descartado porque la conveniencia depende de costes, portfolio, riesgo,
frescura y campaña, que pueden cambiar sin alterar la estimación.
