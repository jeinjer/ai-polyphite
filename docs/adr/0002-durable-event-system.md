# ADR-0002: Sistema de eventos durable

- **Estado:** Accepted
- **Fecha:** 2026-07-27
- **Alcance:** Eventos internos, workers y trazabilidad

## Contexto

AI-Polyphite necesita desacoplar ingesta, análisis, predicciones, paper trading
y evaluación. También exige:

- Reintentos.
- Auditoría.
- Idempotencia.
- Reconstrucción histórica.
- Trazabilidad completa.

Redis Pub/Sub no conserva mensajes ni permite recuperar consumidores caídos. Una
cola de tareas por sí sola tampoco constituye un registro histórico de hechos de
negocio.

La escritura de datos y la publicación de eventos en sistemas separados
introduce el problema de dual write.

## Decisión

Se utilizarán:

- **PostgreSQL** como registro durable y fuente de verdad.
- **Transactional outbox** para publicar eventos de manera consistente con los
  cambios de negocio.
- **Redis Streams** como transporte entre procesos.
- **Consumer inbox** para deduplicación e idempotencia.
- Entrega **at least once**.

No se afirmará ni intentará implementar exactly-once delivery.

## Flujo de publicación

```text
Application transaction
        │
        ├── Domain data
        └── Outbox record
                │
           Dispatcher
                │
          Redis Stream
                │
            Consumer
                │
       Inbox + side effects
```

El dato de negocio y el registro outbox se escribirán dentro de la misma
transacción PostgreSQL.

El dispatcher podrá publicar un evento más de una vez. Los consumidores deben
ser idempotentes.

## Event envelope

Todo evento publicado incluirá:

- `event_id`: UUID único.
- `event_type`: nombre estable en pasado.
- `event_version`: versión positiva del payload.
- `occurred_at`: momento del hecho en UTC.
- `recorded_at`: momento de persistencia en UTC.
- `producer`: módulo productor.
- `producer_version`: versión ejecutada.
- `correlation_id`: flujo completo al que pertenece.
- `causation_id`: comando o evento que lo causó.
- `trace_id`: vínculo con observabilidad.
- `aggregate_type`: tipo de entidad asociada cuando corresponda.
- `aggregate_id`: identificador de entidad cuando corresponda.
- `payload`: datos tipados y versionados.
- `metadata`: contexto técnico no perteneciente al payload.

Los contratos públicos de eventos se almacenarán en `contracts/events`.

## Eventos y comandos

- Un **comando** solicita que se intente realizar una acción.
- Un **evento** describe un hecho que ya ocurrió.

El scheduler publica comandos, no eventos que afirman resultados todavía no
producidos.

Ejemplos:

- Comando: `RefreshMarkets`.
- Evento: `MarketsRefreshed`.
- Comando: `GeneratePrediction`.
- Evento: `PredictionGenerated`.

## Orden

No existe orden global.

Cuando sea necesario, el orden se garantizará por aggregate o stream lógico y
se validará con versión esperada. Los consumidores deben tolerar:

- Duplicados.
- Retrasos.
- Redelivery.
- Eventos de otros aggregates intercalados.

No se tolerarán silenciosamente eventos incompatibles o corruptos.

## Reintentos y dead letter

- Los fallos transitorios se reintentarán con backoff y límite configurable.
- Los fallos permanentes se enviarán a un dead-letter stream.
- Todo fallo conservará evento, consumidor, intento, timestamp y error.
- El replay será una acción explícita y auditable.
- Un evento no se eliminará por haber sido procesado.

## Inbox e idempotencia

Cada consumidor registrará como mínimo:

- `consumer_name`.
- `event_id`.
- Estado.
- Número de intentos.
- Timestamps de inicio y finalización.
- Error final cuando corresponda.

La combinación `consumer_name + event_id` será única.

Las operaciones de negocio también utilizarán idempotency keys cuando exista una
acción externa o financiera simulada.

## Uso de Redis

Redis se utilizará para:

- Streams y consumer groups.
- Cache reconstruible.
- Estado técnico efímero.
- Notificaciones de tiempo real.

Redis no será la única copia de:

- Predicciones.
- Operaciones.
- Agent runs.
- Eventos históricos.
- Configuraciones.

## WebSocket

WebSocket notificará cambios al frontend, pero no será fuente de verdad.

El frontend:

1. Obtendrá un snapshot inicial mediante REST.
2. Consumirá notificaciones en tiempo real.
3. Reconciliará el estado mediante REST después de reconectar.

## Seguridad y datos

- No se incluirán secretos en payloads.
- Los contenidos sensibles usarán referencias o artefactos con política de
  acceso.
- Logs y metadata no duplicarán prompts o respuestas completas sin necesidad.

## Consecuencias positivas

- Elimina el dual write entre datos y outbox.
- Permite auditoría y replay.
- Tolera consumidores temporalmente caídos.
- Hace explícita la idempotencia.
- Proporciona correlation y causation tracking.

## Consecuencias negativas

- Requiere dispatcher, inbox y mantenimiento de streams.
- Aumenta el número de estados operativos.
- Los consumidores deben diseñarse para duplicados.
- El replay requiere controles para no repetir side effects incorrectamente.

## Alternativas descartadas

### Redis Pub/Sub

Descartado como transporte principal porque no es durable.

### Redis Streams sin outbox

Descartado porque no resuelve la consistencia entre PostgreSQL y Redis.

### Celery, Dramatiq o RQ como registro de eventos

No se descartan como ejecutores futuros de tareas, pero no serán la fuente de
verdad de eventos de negocio.

### Exactly-once delivery

Descartada como garantía irrealista entre sistemas distribuidos. Se utilizará
at-least-once más idempotencia.
