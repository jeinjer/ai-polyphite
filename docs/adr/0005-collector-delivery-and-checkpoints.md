# ADR-0005: Ingesta at-least-once con checkpoints durables

- **Estado:** Accepted
- **Fecha:** 2026-07-28
- **Alcance:** Collector Layer de mercados

## Contexto

Los proveedores entregan catálogos paginados y pueden fallar entre páginas. La
ingesta también puede interrumpirse después de persistir datos pero antes de
confirmar progreso. AI-Polyphite necesita reanudar sin perder mercados ni
depender de memoria de proceso.

Una garantía exactly-once entre una API externa y varias transacciones locales
no es alcanzable sin cooperación del proveedor. Intentar simularla añadiría
complejidad y podría ocultar pérdida de datos.

## Decisión

El Collector Layer utiliza procesamiento **at-least-once**:

1. Obtiene una página usando el cursor durable.
2. Sincroniza provider y mercados mediante Application Services.
3. Registra snapshots mediante el caso de uso idempotente existente.
4. Confirma el siguiente cursor sólo después de completar toda la página.

PostgreSQL almacena un checkpoint por código de proveedor:

- `cursor`: progreso dentro del ciclo actual;
- `watermark`: límite confirmado del último ciclo completo;
- `pending_watermark`: límite candidato mientras existen más páginas;
- `updated_at`: timestamp UTC del último avance.

El watermark sólo se promueve cuando el proveedor devuelve una página final. Las
consultas incrementales aplican un pequeño solapamiento temporal para reingresar
el borde y evitar pérdidas por timestamps con igual precisión.

Las ejecuciones del mismo proveedor se excluyen con PostgreSQL transaction-level
advisory locks. El lock se libera automáticamente al terminar la transacción o
cerrarse la conexión.

Los retries se limitan a errores `TransientProviderError`. Usan backoff
exponencial, jitter y `retry_after_seconds` cuando el proveedor informa rate
limit. Errores de validación, protocolo, dominio o persistencia no se reintentan
automáticamente.

## Consecuencias positivas

- Un crash nunca confirma una página incompleta.
- Reprocesar datos es seguro mediante sincronización e idempotencia.
- El proceso puede reanudarse en otra instancia.
- Dos workers no ingieren simultáneamente el mismo proveedor.
- Los fallos permanentes no generan retry storms.

## Consecuencias negativas

- Una página puede procesarse más de una vez.
- Cada entidad y snapshot utiliza su propia transacción de aplicación.
- El collector mantiene una conexión PostgreSQL mientras posee el advisory lock.
- Los cursores pueden expirar según el proveedor; cada adaptador deberá
  documentar su estrategia de recuperación.
- Los hashes de advisory locks tienen una probabilidad de colisión muy baja pero
  no matemáticamente nula.

## Alternativas descartadas

### Exactly-once distribuido

Descartado porque la fuente externa no participa en la transacción PostgreSQL.

### Checkpoint en memoria o Redis sin persistencia

Descartado porque perdería progreso en reinicios y PostgreSQL es la fuente de
verdad durable.

### Confirmar cursor antes de persistir

Descartado porque una caída produciría pérdida silenciosa de mercados.

### Lock local únicamente

Descartado para producción porque no excluye workers en procesos diferentes. Se
mantiene una implementación local sólo para tests y desarrollo unitario.
