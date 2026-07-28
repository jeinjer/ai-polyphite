# ADR-0006: Separar observaciones de cotizaciones ejecutables

- **Estado:** Accepted
- **Fecha:** 2026-07-28
- **Alcance:** datos históricos de mercados

## Contexto

Las fuentes públicas pueden publicar probabilidad, volumen o liquidez sin
ofrecer precios YES/NO, spread ni garantías de ejecución. Tratar esos datos como
una cotización operable introduciría información inventada y contaminaría
futuros experimentos.

`MarketSnapshot` ya existía y exige un conjunto completo de métricas. Eliminarlo
ahora rompería compatibilidad sin aportar una migración segura.

## Decisión

Se introducen tres conceptos distintos:

- `MarketObservation`: observación informativa e histórica; admite métricas
  ausentes y nunca implica que se pueda operar.
- `MarketSnapshot`: contrato legado de métricas completas, conservado durante
  la migración progresiva.
- `ExecutableQuote`: concepto futuro, todavía no implementado, que deberá
  incluir lado, precio, tamaño, vigencia y procedencia verificables.

Una observación es inmutable y se identifica de forma idempotente por
`(market_id, observed_at)`. Un duplicado con el mismo contenido es aceptado; uno
con valores diferentes genera `ObservationConflictError`.

Los adaptadores sólo copian datos publicados. Ninguna capa completa
probabilidad, volumen, liquidez o precios ausentes.

## Consecuencias

- La serie histórica puede incorporar Manifold sin fabricar precios.
- Los futuros módulos de simulación no podrán confundir probabilidad con
  ejecución.
- Durante la transición conviven dos tablas históricas.
- Los consumidores deben elegir explícitamente entre datos informativos y
  ejecutables.

## Alternativas descartadas

- Relajar `MarketSnapshot`: habría cambiado silenciosamente su semántica.
- Inferir YES/NO desde la probabilidad: no representa spread, tamaño ni
  ejecutabilidad.
- Guardar el payload completo: aumenta riesgos de privacidad, acoplamiento y
  retención innecesaria.
