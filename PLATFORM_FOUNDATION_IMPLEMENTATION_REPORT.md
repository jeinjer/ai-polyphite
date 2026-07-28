# AI-Polyphite — Resumen de implementación de la base transversal

Fecha: 2026-07-27  
Estado: completado y validado  
Alcance: infraestructura técnica, sin lógica de negocio

## Objetivo

Preparar una base observable y verificable antes de comenzar el primer vertical
slice funcional de AI-Polyphite.

## Implementado

- Configuración tipada mediante Pydantic Settings.
- Precedencia explícita:
  1. valores proporcionados al construir `Settings`;
  2. variables de entorno;
  3. archivo `.env` o el indicado por `AI_POLYPHITE_ENV_FILE` (con alias legado
     `PREDICTIONLAB_ENV_FILE`);
  4. valores seguros de desarrollo.
- Separación entre URLs locales y URLs internas de Docker Compose.
- Logging estructurado en JSON.
- Exclusión de URLs y credenciales del resumen de configuración.
- Propagación y generación de `X-Correlation-ID`.
- Propagación de W3C Trace Context mediante `traceparent`.
- Registro por request de método, ruta, estado, duración y contexto.
- Endpoint `GET /health/live`.
- Endpoint `GET /health/ready`.
- Readiness concurrente para PostgreSQL y Redis.
- Timeout individual para dependencias.
- Respuestas de readiness sin detalles internos ni datos sensibles.
- Pipeline CI separado para backend, frontend y contenedores.
- Compatibilidad de tests asíncronos con `psycopg` en Windows.
- Documentación y scripts locales actualizados.

## Contratos técnicos

### `GET /health/live`

Comprueba únicamente que el proceso HTTP puede responder.

Respuesta esperada:

```json
{
  "status": "ok"
}
```

### `GET /health/ready`

Comprueba PostgreSQL y Redis. Devuelve:

- `200` cuando todas las dependencias están disponibles;
- `503` cuando alguna dependencia no está disponible.

Ejemplo:

```json
{
  "status": "ready",
  "checks": [
    {
      "name": "postgres",
      "status": "up",
      "latency_ms": 1.25
    },
    {
      "name": "redis",
      "status": "up",
      "latency_ms": 0.5
    }
  ]
}
```

Todas las respuestas HTTP incluyen:

- `X-Correlation-ID`;
- `traceparent`.

## Archivos principales

```text
.github/workflows/ci.yml
.env.example
docker-compose.yml
backend/src/predictionlab/
├── api/
│   ├── app.py
│   ├── middleware/request_context.py
│   └── routes/health.py
├── application/health.py
├── core/
│   ├── context.py
│   ├── logging.py
│   └── settings.py
└── infrastructure/
    ├── resources.py
    └── health/readiness.py

backend/tests/
├── conftest.py
├── integration/test_readiness_dependencies.py
└── unit/

docs/13_PLATFORM_FOUNDATION.md
scripts/check.ps1
```

También se actualizaron:

- `README.md`;
- `backend/README.md`;
- `CHANGELOG.md`;
- `PROJECT_STATUS.md`;
- `TASKS.md`;
- `frontend/next.config.ts`;
- `frontend/playwright.config.ts`.

## Integración continua

El workflow de CI contiene tres jobs:

1. **Backend**
   - Ruff.
   - mypy.
   - Pytest.
   - PostgreSQL y Redis reales como servicios de integración.

2. **Frontend**
   - Auditoría de dependencias.
   - ESLint.
   - TypeScript.
   - Build de Next.js.
   - Playwright.

3. **Containers**
   - Validación de Docker Compose.
   - Build de las imágenes de backend y frontend.

El workflow no publica imágenes ni realiza despliegues.

## Validación realizada

- Backend: `16/16` tests aprobados.
- Integration test real: PostgreSQL y Redis aprobados.
- Ruff: aprobado.
- mypy estricto: aprobado.
- `npm audit`: cero vulnerabilidades detectadas.
- ESLint: aprobado.
- TypeScript: aprobado.
- Build de Next.js: aprobado.
- Playwright: `1/1` test aprobado.
- Build de imágenes Docker: aprobado.
- Backend, frontend, PostgreSQL y Redis: saludables en Compose.
- Liveness: `ok`.
- Readiness: `ready`.
- Frontend: HTTP `200`.

## Comandos útiles

Checks locales sin infraestructura:

```powershell
.\scripts\check.ps1
```

Checks con PostgreSQL y Redis:

```powershell
docker compose up -d --wait postgres redis
.\scripts\check.ps1 -Integration
```

Checks incluyendo Playwright:

```powershell
$env:PLAYWRIGHT_BROWSER_CHANNEL = "chrome"
.\scripts\check.ps1 -Integration -E2E
```

Inicio completo:

```powershell
docker compose up -d --build --wait
```

## Fuera de alcance

No se implementaron:

- modelos o migraciones de negocio;
- ingesta de mercados;
- agentes;
- integración LLM;
- predicciones;
- estrategias;
- portfolios o ledger;
- paper trading;
- trading real.

## Próxima tarea recomendada

Implementar el primer vertical slice de mercados en tareas pequeñas:

1. contratos de provider, market y market snapshot;
2. modelo de persistencia y migración inicial;
3. repositorio y servicio de aplicación;
4. fixtures contractuales de Polymarket;
5. adaptador read-only;
6. persistencia idempotente de snapshots;
7. query REST paginada;
8. vista inicial de mercados.

No comenzar esta etapa sin aprobación explícita.
