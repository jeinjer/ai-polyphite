# ADR-0003: Límites y contabilidad inicial del paper trading

- **Estado:** Accepted
- **Fecha:** 2026-07-27
- **Alcance:** Simulación, portfolios, posiciones y liquidación

## Contexto

AI-Polyphite no es un sistema de ejecución financiera. Su objetivo es medir qué
habría ocurrido bajo reglas explícitas y reproducibles.

Sin una semántica contable única, diferentes interpretaciones de stake, shares,
precios, costos y resolución producirían resultados incompatibles.

El MVP debe priorizar corrección y auditabilidad por encima de realismo
microestructural avanzado.

## Decisión de alcance

El MVP de paper trading soportará únicamente:

- Capital virtual denominado en USD.
- Mercados binarios.
- Posiciones long-only.
- Compra de resultado `YES` o `NO`.
- Stake fijo configurable, con default de `1.00 USD`.
- Liquidación al resultado oficial.
- Una cuenta separada por versión de estrategia.

No soportará inicialmente:

- Dinero real.
- Wallets.
- Firmas.
- Órdenes contra un exchange.
- Short selling.
- Leverage.
- Venta o cierre anticipado.
- Kelly sizing.
- Mercados con más de dos resultados.
- Reinversión o transferencias entre estrategias.

No existirá un flag que convierta una operación simulada en real. Una eventual
ejecución real requeriría otro sistema, controles adicionales y un nuevo ADR.

## Tipos numéricos

- Dinero, precios, cantidades, fees, P&L y ratios financieros usarán `Decimal`.
- `float` queda prohibido dentro del dominio financiero.
- La precisión y el redondeo se definirán explícitamente en el modelo antes de
  persistir operaciones.
- Timestamps se almacenarán en UTC.

## Apertura de posición

Una decisión de apertura utilizará un snapshot exacto e inmutable que incluya:

- Mercado y resultado seleccionado.
- Precio observado.
- Timestamp de observación.
- Precio de ejecución simulado.
- Stake.
- Fees y slippage modelados.
- Estrategia y versión.
- Predicción y versión.
- Configuración resuelta.
- Idempotency key.

Para una posición:

```text
quantity = stake / simulated_execution_price
entry_cash_outflow = stake + entry_fees
```

El stake representa capital utilizado para comprar shares, no la cantidad de
shares ni el payout máximo.

## Liquidación

Al resolverse oficialmente el mercado:

```text
winning gross settlement = quantity × 1.00 USD
losing gross settlement = 0.00 USD
realized P&L = gross settlement - entry cash outflow - settlement fees
```

El resultado oficial, la fuente, el timestamp y el identificador de resolución
deben persistirse antes de liquidar.

Estados mínimos de resolución:

- `pending`
- `resolved_yes`
- `resolved_no`
- `cancelled`
- `disputed`
- `invalid`

Mercados `disputed` permanecen pendientes.

Para el MVP, una posición en un mercado `cancelled` o `invalid` revierte el cash
outflow y finaliza con P&L cero. Esta regla debe registrarse en la liquidación.

## Ledger

Los movimientos de capital serán append-only.

Como mínimo existirán conceptos para:

- Capital inicial.
- Reserva de stake.
- Fees de entrada.
- Liquidación ganadora o perdedora.
- Reversión por cancelación o invalidez.

El balance actual será una proyección derivada del ledger, no una cifra histórica
sobrescrita sin evidencia.

Debe mantenerse la invariante:

```text
available cash + committed capital = portfolio equity before mark-to-market
```

Las métricas realizadas no incorporarán valores no realizados salvo que estén
etiquetadas explícitamente como mark-to-market.

## Aislamiento de estrategias

Cada versión de estrategia tendrá:

- Portfolio independiente.
- Capital inicial propio.
- Configuración inmutable.
- Operaciones propias.
- Métricas propias.

Las comparaciones deben utilizar datos disponibles en el mismo momento lógico.

## Idempotencia y concurrencia

- Una misma decisión no puede abrir dos posiciones accidentalmente.
- La apertura, reserva de capital y ledger se ejecutarán en una transacción.
- Los límites de exposición se comprobarán dentro de esa transacción.
- Los eventos duplicados devolverán el resultado previo o no producirán side
  effects adicionales.
- La liquidación también será idempotente.

## Costos de simulación

La estructura soportará:

- Spread.
- Slippage.
- Fees.
- Latencia.

El modelo exacto de costos se versionará. Si no hay datos suficientes, no se
inventará precisión: el trade quedará etiquetado con el modelo simplificado que
se utilizó.

## Información temporal

Una operación solo puede utilizar información cuyo
`available_to_system_at <= decision_at`.

La posición debe referenciar:

- Market snapshot.
- Predicción.
- Evidencia disponible.
- Agent runs.
- Configuración.
- Versión del código o build.

## Modos

Se distinguirán:

- **Research:** genera análisis y predicciones.
- **Shadow:** registra qué habría decidido sin reservar capital.
- **Paper:** reserva capital virtual y crea posiciones.

Ningún modo ejecuta operaciones reales.

## Consecuencias positivas

- P&L reproducible.
- Menor superficie de errores.
- Comparación justa entre estrategias.
- Separación estructural respecto al trading real.
- Invariantes comprobables mediante tests.

## Consecuencias negativas

- No modela cierres anticipados ni estrategias complejas.
- El realismo de slippage será limitado al inicio.
- Mercados no binarios quedan fuera.
- Algunas posiciones pueden permanecer abiertas durante mucho tiempo.

## Alternativas descartadas

### Una tabla `trades` con balance mutable

Descartada porque dificulta auditoría, concurrencia y reconstrucción.

### Usar `float`

Descartado por errores de precisión financiera.

### Compartir portfolios entre estrategias

Descartado porque contamina la comparación experimental.

### Incluir un booleano `paper_trade`

Descartado porque crea una ruta accidental hacia ejecución real dentro del mismo
modelo.

### Cierre anticipado en el MVP

Descartado porque exige modelar liquidez, profundidad, fills y reglas de salida
antes de validar el flujo básico.
