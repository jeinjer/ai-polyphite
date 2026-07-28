# ADR-0009: Frontera estructural de simulación y evaluación

- **Estado:** Accepted
- **Fecha:** 2026-07-28
- **Alcance:** Paper trading, métricas y separación de ejecución real

## Contexto

AI-Polyphite necesita evaluar predicciones reproducibles mediante una cartera
virtual. El sistema no debe sugerir que una observación de mercado es una
cotización ejecutable ni permitir que una configuración convierta el flujo en
trading real.

El ADR-0003 fijó los límites iniciales. Este slice necesita además dos unidades
simuladas y políticas de sizing intercambiables.

## Decisión

El pipeline queda limitado estructuralmente a:

```text
PredictionRun persistido
  → TradeDecision
  → PaperOrder
  → PaperTrade
  → PaperPosition
  → PaperSettlement
  → PaperPerformance
```

- Las únicas unidades son `USD_SIMULATED` y `MANA_SIMULATED`.
- No existen brokers, wallets, firmas, claves, depósitos ni retiros.
- No existe un flag `real`, un adaptador de ejecución ni una interfaz común con
  trading real.
- Sólo se admiten posiciones binarias long-only YES/NO, sin leverage ni short.
- Una posición por mercado y portfolio.
- La entrada consume exclusivamente un `PredictionRun` durable y datos visibles
  en `predicted_at`.
- Observaciones y marks son informativos; el coste de ejecución usa un modelo
  explícito y versionado.
- Decisión, orden, fill, posición, balance y ledger se escriben en una única
  transacción.
- Ledger, decisiones, fills, settlements y snapshots de performance conservan
  hashes o procedencia suficiente para reconstrucción.
- Las métricas se denominan siempre simuladas y se acompañan de advertencias
  visibles.

## Extensión de ADR-0003

Este ADR reemplaza sólo estos detalles del ADR-0003:

- “capital virtual denominado en USD” pasa a unidades inequívocas
  `USD_SIMULATED` y `MANA_SIMULATED`;
- “stake fijo” pasa a políticas versionadas `FixedFractionSizing` y
  `ConfidenceAdjustedSizing`.

Permanecen vigentes sus límites contables, uso de `Decimal`, liquidación
oficial, ledger auditable, idempotencia y prohibición de ejecución real.

## Consecuencias

### Positivas

- No hay ruta accidental hacia dinero real.
- Estrategias y baselines se comparan bajo el mismo modelo de costes.
- Los resultados son repetibles por dataset, semilla y configuración.
- La interfaz puede distinguir capital, exposición, riesgo y evidencia.

### Negativas

- No representa profundidad, fills parciales ni cierre anticipado.
- El mark-to-market no prueba que una salida hubiera sido ejecutable.
- Las correlaciones sólo se rechazan cuando están identificadas; no se infieren.

## Alternativas descartadas

- Reutilizar contratos de brokers: ampliaría innecesariamente la superficie de
  riesgo.
- Llamar USD a la unidad virtual: puede confundirse con saldo real.
- Derivar operaciones desde salidas de agentes no persistidas: rompe
  reproducibilidad.
- Optimizar automáticamente parámetros: produciría sobreajuste antes de contar
  con evidencia suficiente.
