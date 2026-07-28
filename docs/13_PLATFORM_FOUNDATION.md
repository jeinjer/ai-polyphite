# 13 — Base transversal de plataforma

Este documento describe la infraestructura técnica disponible antes de
implementar lógica de negocio.

## Configuración

El backend carga una configuración tipada con Pydantic Settings. La precedencia,
de mayor a menor, es:

1. valores pasados explícitamente al construir `Settings`;
2. variables de entorno del proceso;
3. archivo indicado por `AI_POLYPHITE_ENV_FILE`, o `.env` por defecto (el alias
   legado `PREDICTIONLAB_ENV_FILE` sigue aceptándose durante la transición);
4. valores seguros de desarrollo definidos en código.

Las variables utilizadas dentro de contenedores tienen el prefijo
`CONTAINER_` en `.env.example`. Docker Compose las traduce a los nombres que
consume la aplicación. Esto evita que un mismo hostname intente representar al
host local y a la red interna de Compose.

Los defaults locales de PostgreSQL y Redis usan `127.0.0.1` para evitar
resoluciones IPv4/IPv6 ambiguas y latencias artificiales en Windows.

El resumen de configuración escrito en logs es una lista permitida de campos
no sensibles. Las URLs de PostgreSQL, Redis y proveedores no se registran.

## Logging estructurado

La salida del backend es JSON, una línea por evento. Cada registro contiene como
mínimo:

- `timestamp` en UTC;
- `level`;
- `logger`;
- `message`;
- `service`;
- `environment`;
- `correlation_id` y `trace_id` cuando existe contexto de request.

El middleware HTTP emite un evento `http_request_completed` o
`http_request_failed` con método, ruta, estado y duración. Uvicorn access logs
se desactivan para evitar duplicados.

Además mantiene métricas por método, plantilla de ruta y estado. Se usa la
plantilla de FastAPI para evitar cardinalidad ilimitada en rutas con UUID. La
exportación externa de estas métricas aún no forma parte de la base.

## Correlación y trace context

La API acepta `X-Correlation-ID` y `traceparent`. Solo propaga valores válidos:

- un correlation ID inválido se reemplaza por un UUID;
- un `traceparent` W3C inválido inicia un trace nuevo;
- la respuesta siempre devuelve `X-Correlation-ID` y `traceparent`.

El contexto se conserva mediante `contextvars`, por lo que los logs emitidos
durante el request reciben los identificadores sin acoplar la lógica de
aplicación a FastAPI.

Esta etapa propaga contexto, pero todavía no exporta spans a un backend de
OpenTelemetry.

## Health checks

La API expone dos contratos técnicos distintos:

| Endpoint | Significado | Dependencias |
|---|---|---|
| `GET /health/live` | El proceso puede responder HTTP | Ninguna |
| `GET /health/ready` | El proceso puede servir tráfico | PostgreSQL y Redis |

Readiness ejecuta las comprobaciones en paralelo, aplica un timeout individual
y devuelve `503` cuando al menos una dependencia no está disponible. La
respuesta expone estado y latencia, pero no incluye credenciales ni mensajes de
error internos.

## Pruebas

Las pruebas unitarias no requieren servicios externos:

```powershell
pytest backend/tests -m "not integration"
```

Las pruebas de integración validan conexiones reales. Primero se deben levantar
PostgreSQL y Redis:

```powershell
docker compose up -d --wait postgres redis
pytest backend/tests -m integration
```

## Integración continua

`.github/workflows/ci.yml` separa tres responsabilidades:

1. backend: lint, tipos, unit tests e integration tests con PostgreSQL y Redis;
2. frontend: audit, lint, tipos, build y Playwright;
3. contenedores: validación de Compose y build de las imágenes de aplicación.

No se publican imágenes ni se despliega desde este workflow.
