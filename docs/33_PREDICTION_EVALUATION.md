# Evaluación probabilística inicial

Versión: 2.0

Estado: Implementado

## Separación obligatoria

```text
Generación en predicted_at
  ≠ resolución posterior
  ≠ evaluación
```

Los agentes reciben estado y observaciones as-of. No reciben
`resolution_outcome`. `PredictionEvaluationService` consulta el outcome
binario sólo después de persistida la predicción y resuelto el mercado.

Mercados cancelados u outcomes no binarios no se puntúan.

## Métricas

Para probabilidad `p` y resultado `y ∈ {0,1}`:

- Brier Score: `(p - y)²`.
- Log loss: `-[y log(p) + (1-y) log(1-p)]`, con clipping numérico.
- Error absoluto: `|p-y|`.
- Accuracy direccional: compara el lado de `0.5` con el outcome.
- Cobertura: emitidas / (emitidas + abstenciones).
- Calibración: buckets de ancho 0.1 con probabilidad media y frecuencia
  observada.

Menor Brier, log loss y error absoluto es mejor. Accuracy no reemplaza las
métricas probabilísticas.

## Baselines

### MarketBaseline

Usa la probabilidad visible que quedó guardada en `PredictionRun`.

### ConstantBaseline

Usa siempre `0.50`.

La salida del sistema debe compararse principalmente contra MarketBaseline. Un
resultado por encima del azar no demuestra ventaja si no mejora la probabilidad
del propio mercado.

## Abstenciones

Las abstenciones participan de cobertura pero no reciben una probabilidad
inventada para puntuarlas. Una estrategia puede reducir errores absteniéndose
demasiado; por eso las métricas siempre deben leerse junto con cobertura y
cantidad de muestras.

Desde `ConsensusAgent` 2.0, confianza baja y edge pequeño ya no cuentan como
abstenciones predictivas. La conveniencia se mide en
`CommercialEvaluation`, separada de Brier, log loss y calibración.

## Limitaciones

- La calibración inicial es descriptiva; no reajusta agentes.
- No existe validación de significancia estadística todavía.
- Las métricas financieras simuladas existen en paper trading, pero no forman
  parte de esta evaluación probabilística.
- El dataset sintético valida el mecanismo, no demuestra edge real.
