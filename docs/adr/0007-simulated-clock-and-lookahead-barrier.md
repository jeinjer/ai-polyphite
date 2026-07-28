# ADR-0007: Reloj simulado y barrera contra lookahead

- **Estado:** Accepted
- **Fecha:** 2026-07-28
- **Alcance:** experimentos históricos reproducibles

## Contexto

Una evaluación histórica queda invalidada si una predicción utiliza una
observación o resolución posterior al instante analizado. El tiempo de pared no
puede gobernar un experimento reproducible y entregar el dataset completo a los
consumidores haría depender la seguridad de su disciplina.

## Decisión

Se define el puerto `Clock` con dos implementaciones:

- `SystemClock`, para tiempo real operativo;
- `ReplayClock`, monotónico, reiniciable y gobernado por una secuencia fija de
  instantes UTC.

`ReplayProvider` mantiene privados los registros del dataset y construye cada
respuesta **as of** `ReplayClock.now()`. Mercados todavía no creados,
observaciones futuras y resoluciones futuras no forman parte de la respuesta.
El runtime de replay es la única capa que conoce el calendario completo para
avanzar el reloj.

El collector y los Application Services reciben el mismo reloj simulado. Por
eso `ingested_at`, transiciones e idempotencia son deterministas durante un
experimento. Los tiempos operativos de `ExperimentRun` continúan usando
`SystemClock` y no participan del hash del resultado.

El dataset es un archivo local versionado. PostgreSQL persiste el resultado del
experimento, pero no es la fuente del replay.

## Consecuencias

- Una misma configuración puede repetirse sin esperas reales.
- La resolución sólo se vuelve visible en su evento correspondiente.
- Futuros agentes recibirán read models as-of; no recibirán rutas ni objetos de
  dataset.
- Los tests pueden mover el tiempo sin dormir.
- El proceso de replay debe ejecutar el collector en cada instante de evento
  para conservar todas las observaciones.

## Alternativas descartadas

- Filtrar en los agentes: permitiría errores de lookahead por consumidor.
- Reproducir con `sleep`: sería lento y no determinista.
- Leer el histórico desde PostgreSQL: impediría reconstruir el experimento
  desde un artefacto independiente.
- Publicar todos los eventos y pedir al consumidor que ignore el futuro:
  rompe la barrera por diseño.
