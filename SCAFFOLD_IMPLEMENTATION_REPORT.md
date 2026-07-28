# AI-Polyphite — Informe de implementación del scaffold

## Estado

**Tarea:** creación del esqueleto inicial del repositorio  
**Resultado:** completada  
**Fecha:** 2026-07-27  
**Lógica de negocio implementada:** ninguna

## Objetivo de la tarea

Crear una base limpia, documentada y verificable para comenzar el desarrollo de
AI-Polyphite respetando la arquitectura aprobada.

El scaffold debía incluir:

- Estructura de carpetas.
- Documentación raíz.
- Configuración de entorno.
- Docker Compose.
- Backend.
- Frontend.
- Contratos.
- Infraestructura.
- Tests.
- Scripts.
- Architecture Decision Records imprescindibles.

## Resultado

El repositorio quedó preparado como un monolito modular multiproceso.

La estructura principal es:

```text
.
├── backend/
├── frontend/
├── contracts/
├── infrastructure/
├── tests/
├── scripts/
└── docs/
    └── adr/
```

No se implementaron:

- Mercados.
- Agentes.
- Predicciones.
- Integraciones externas.
- Eventos.
- Outbox o inbox.
- Workers ejecutables.
- Scheduler ejecutable.
- Estrategias.
- Portfolios.
- Paper trading.
- Resoluciones.
- Métricas de negocio.
- Autenticación.

Solo se añadieron dos elementos técnicos mínimos para validar el scaffold:

- Endpoint de liveness del backend.
- Página estática de estado del frontend.

---

## Documentación raíz

Se crearon o actualizaron:

- `README.md`
- `CHANGELOG.md`
- `PROJECT_STATUS.md`
- `TASKS.md`
- `AGENTS.md`
- `.gitignore`
- `.gitattributes`
- `.editorconfig`
- `.env.example`
- `docker-compose.yml`

### README

Documenta:

- Objetivo del proyecto.
- Prohibición de trading real.
- Arquitectura general.
- Stack tecnológico.
- Requisitos.
- Inicio mediante Docker Compose.
- Desarrollo local.
- Comandos de calidad.
- Convenciones iniciales.

### PROJECT_STATUS

Separa explícitamente:

- Lo implementado.
- Lo no implementado.
- Los servicios actuales.
- El criterio para avanzar a la siguiente fase.

### TASKS

Contiene un backlog ordenado por dependencias:

- Foundation.
- Market vertical slice.
- Durable event runtime.
- Evidence and AI.
- Paper trading.
- Dashboard and operations.
- Funcionalidades posteriores.
- Elementos explícitamente fuera de alcance.

### AGENTS

Define reglas para futuros agentes de desarrollo:

- Leer estado, tareas, documentación y ADRs.
- Respetar la dirección de dependencias.
- No introducir trading real.
- No crear microservicios por agente.
- Incluir tests y documentación.
- Actualizar estado al finalizar cada tarea.

---

## Backend

El backend utiliza:

- Python 3.13.
- FastAPI.
- SQLAlchemy.
- Alembic.
- Pydantic.
- PostgreSQL mediante Psycopg.
- Redis.
- Pytest.
- Ruff.
- Mypy.

Estructura:

```text
backend/
├── alembic/
├── src/
│   └── predictionlab/
│       ├── api/
│       ├── application/
│       ├── domain/
│       │   ├── agents/
│       │   ├── evidence/
│       │   ├── experiments/
│       │   ├── markets/
│       │   ├── paper_trading/
│       │   └── predictions/
│       ├── integrations/
│       │   ├── llm/
│       │   ├── news/
│       │   └── polymarket/
│       ├── infrastructure/
│       │   ├── cache/
│       │   ├── database/
│       │   ├── events/
│       │   └── observability/
│       └── runtime/
│           ├── scheduler/
│           └── workers/
└── tests/
    ├── unit/
    ├── integration/
    ├── contract/
    └── fixtures/
```

### Dirección de dependencias

```text
api
 ↓
application
 ↓
domain
 ↑
infrastructure / integrations
```

El dominio no debe importar:

- FastAPI.
- SQLAlchemy.
- Redis.
- SDKs externos.

### Elementos técnicos implementados

- Aplicación FastAPI mínima.
- Endpoint `GET /health/live`.
- Base declarativa vacía de SQLAlchemy.
- Configuración inicial de Alembic.
- Dockerfile con usuario no privilegiado.
- Test unitario del endpoint de liveness.

No existen modelos persistentes ni migraciones de dominio.

---

## Frontend

El frontend utiliza:

- Next.js.
- React.
- TypeScript.
- Tailwind CSS.
- TanStack Query.
- Zustand.
- shadcn/ui preparado.
- Recharts.
- Playwright.

Estructura:

```text
frontend/
├── public/
├── src/
│   ├── app/
│   ├── components/
│   │   └── ui/
│   ├── features/
│   ├── lib/
│   │   └── api/
│   └── stores/
└── tests/
    └── e2e/
```

### Convenciones

- TanStack Query será la fuente de verdad del estado remoto.
- Zustand se utilizará únicamente para estado local de interfaz.
- Las features se organizarán verticalmente.
- Los componentes shadcn/ui vivirán en `components/ui`.
- El acceso HTTP y WebSocket se centralizará en `lib/api`.

### Elementos técnicos implementados

- App Router.
- Layout global.
- Provider de TanStack Query.
- Tailwind CSS.
- Configuración shadcn/ui.
- Utilidad `cn`.
- Página estática que muestra el estado del scaffold.
- Dockerfile standalone con usuario no privilegiado.
- Test E2E de la página inicial.

No existen vistas de negocio.

---

## Docker Compose

El archivo `docker-compose.yml` incluye:

| Servicio | Puerto local | Estado validado |
|---|---:|---|
| Frontend | 3000 | Healthy |
| Backend | 8000 | Healthy |
| PostgreSQL | 5432 | Healthy |
| Redis | 6379 | Healthy |

Características:

- Puertos publicados únicamente en `127.0.0.1`.
- Health checks.
- Volúmenes persistentes para PostgreSQL y Redis.
- Redis con AOF habilitado.
- Dependencias condicionadas por health.
- Red interna dedicada.
- Ollama configurable en el host mediante `OLLAMA_BASE_URL`.

No se añadieron servicios ficticios de worker o scheduler. Se incorporarán
cuando exista el runtime real.

---

## Contratos

Se creó:

```text
contracts/
├── events/
│   └── v1/
└── http/
```

Todavía no se publicó ningún schema.

Los contratos de eventos se implementarán junto con el sistema outbox/inbox para
evitar mantener contratos especulativos sin productores ni consumidores.

FastAPI OpenAPI será inicialmente el contrato canónico de HTTP.

---

## Infraestructura

Se creó:

```text
infrastructure/
├── docker/
└── monitoring/
    ├── grafana/
    ├── opentelemetry/
    └── prometheus/
```

No se añadieron configuraciones placeholder de observabilidad.

La topología de Prometheus, Grafana y OpenTelemetry se definirá cuando se
implemente observabilidad.

---

## Scripts

### `scripts/bootstrap.ps1`

- Crea `.venv`.
- Instala el backend en modo editable.
- Instala dependencias frontend mediante `npm ci`.
- Detiene la ejecución si algún comando falla.

### `scripts/check.ps1`

Ejecuta:

- Pytest.
- Ruff.
- Mypy.
- npm audit.
- ESLint.
- TypeScript.
- Next.js build.
- Validación de Docker Compose.
- Playwright opcional mediante `-E2E`.

Ejemplo:

```powershell
$env:PLAYWRIGHT_BROWSER_CHANNEL = "chrome"
.\scripts\check.ps1 -E2E
```

---

## ADRs aceptados

Solo se crearon los tres ADR imprescindibles aprobados.

### ADR-0001: Monolito modular multiproceso

Archivo:

`docs/adr/0001-modular-monolith.md`

Decisiones:

- Un único paquete backend.
- Procesos API, worker y scheduler.
- Agentes como módulos lógicos.
- No crear un microservicio o contenedor por agente.
- Separación estricta de capas.
- Posibilidad de extraer módulos únicamente con evidencia y un nuevo ADR.

### ADR-0002: Sistema de eventos durable

Archivo:

`docs/adr/0002-durable-event-system.md`

Decisiones:

- PostgreSQL como fuente de verdad.
- Transactional outbox.
- Redis Streams como transporte.
- Consumer inbox.
- Entrega at least once.
- Consumidores idempotentes.
- No prometer exactly-once.
- Event envelope versionado.
- Reintentos y dead-letter stream.
- WebSocket como notificación, no como fuente de verdad.

### ADR-0003: Paper trading

Archivo:

`docs/adr/0003-paper-trading-boundaries.md`

Decisiones:

- Solo capital virtual.
- Mercados binarios.
- Posiciones long-only YES/NO.
- Stake fijo configurable, default `1.00 USD`.
- Liquidación al resultado oficial.
- Sin cierre anticipado en el MVP.
- Uso obligatorio de `Decimal`.
- Ledger append-only.
- Portfolio aislado por versión de estrategia.
- Apertura y liquidación idempotentes.
- Prohibición estructural de trading real.

---

## Seguridad de dependencias

El audit inicial detectó vulnerabilidades transitivas en dependencias
empaquetadas por Next.js y ESLint.

No se ejecutó `npm audit fix --force`, ya que proponía cambios incompatibles.

Se fijaron versiones transitivas corregidas mediante `overrides` para:

- `minimatch`.
- `postcss`.
- `sharp`.

Resultado final:

```text
found 0 vulnerabilities
```

---

## Validaciones ejecutadas

### Backend

```text
Pytest: 1 passed
Ruff: all checks passed
Mypy: no issues found in 26 source files
```

### Frontend

```text
npm audit: 0 vulnerabilities
ESLint: passed
TypeScript: passed
Next.js production build: passed
Playwright: 1 passed
```

### Docker

```text
Backend image: built
Frontend image: built
PostgreSQL: healthy
Redis: healthy
Backend: healthy
Frontend: healthy
```

Comprobaciones HTTP:

```text
GET http://127.0.0.1:8000/health/live
HTTP 200
{"status":"ok"}

GET http://127.0.0.1:3000
HTTP 200
```

También se validó:

- `docker compose config`.
- `git diff --check`.
- Ausencia de errores en logs de los servicios.

Los contenedores se detuvieron al finalizar la validación y los volúmenes se
conservaron.

---

## Estado actual verificable

AI-Polyphite tiene una base funcional para comenzar desarrollo, pero todavía
no tiene un flujo de negocio.

El sistema puede:

- Instalar dependencias.
- Ejecutar tests.
- Construir backend y frontend.
- Construir imágenes Docker.
- Levantar PostgreSQL y Redis.
- Servir una API de liveness.
- Servir una página frontend.

El sistema todavía no puede:

- Obtener mercados.
- Guardar mercados.
- Ejecutar agentes.
- Generar predicciones.
- Simular operaciones.
- Liquidar posiciones.
- Mostrar métricas reales.

---

## Próxima tarea recomendada

Implementar la base transversal de plataforma:

1. Configuración tipada.
2. Precedencia de variables de entorno.
3. Logging estructurado.
4. Correlation ID y trace context.
5. Readiness checks para PostgreSQL y Redis.
6. CI para audit, lint, typing, tests y builds.

Esta siguiente tarea no debería incorporar todavía mercados ni lógica de paper
trading.

Debe comenzar únicamente después de la aprobación explícita del scaffold.
