# AI-Polyphite

AI-Polyphite es un laboratorio experimental para investigar si un sistema basado
en agentes de IA puede encontrar ventajas estadísticas en mercados de predicción
mediante simulación.

> [!IMPORTANT]
> AI-Polyphite no ejecuta operaciones con dinero real. El alcance actual incluye
> paper trading reproducible exclusivamente con unidades simuladas.

## Estado

El repositorio ya ejecuta ingesta, replay histórico determinista y cuatro
agentes reproducibles, persiste predicciones y simula portfolios, operaciones y
liquidaciones auditables. Los resultados y baselines se muestran en un dashboard
bilingüe. El entorno Python aislado conserva `MockProvider` como default seguro;
Docker Compose inicia la campaña autónoma read-only con Manifold.

Consulta:

- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) para el estado verificable actual.
- [`TASKS.md`](TASKS.md) para el backlog ordenado.
- [`CHANGELOG.md`](CHANGELOG.md) para cambios relevantes.
- [`HISTORICAL_FOUNDATION_IMPLEMENTATION_REPORT.md`](HISTORICAL_FOUNDATION_IMPLEMENTATION_REPORT.md)
  para el resumen verificable de este slice.
- [`REPLAY_PROVIDER_IMPLEMENTATION_REPORT.md`](REPLAY_PROVIDER_IMPLEMENTATION_REPORT.md)
  para el cierre verificable de replay y experimentos.
- [`PREDICTION_AGENTS_IMPLEMENTATION_REPORT.md`](PREDICTION_AGENTS_IMPLEMENTATION_REPORT.md)
  para el cierre verificable de agentes y predicciones.
- [`PAPER_TRADING_IMPLEMENTATION_REPORT.md`](PAPER_TRADING_IMPLEMENTATION_REPORT.md)
  para el cierre verificable del MVP simulado.
- [`CONTINUOUS_PAPER_VALIDATION_IMPLEMENTATION_REPORT.md`](CONTINUOUS_PAPER_VALIDATION_IMPLEMENTATION_REPORT.md)
  para el cierre verificable del runtime de estabilización.
- [`AUTONOMOUS_OPERATION_IMPLEMENTATION_REPORT.md`](AUTONOMOUS_OPERATION_IMPLEMENTATION_REPORT.md)
  para rutas, datos públicos, operación continua y verificación de arranque.
- [`docs/`](docs/) para la especificación completa.
- [`docs/adr/`](docs/adr/) para decisiones arquitectónicas aceptadas.
- [`docs/14_MARKET_DOMAIN.md`](docs/14_MARKET_DOMAIN.md) para el primer vertical
  slice.
- [`docs/17_PROVIDER_SDK.md`](docs/17_PROVIDER_SDK.md) para la frontera
  multi-provider.
- [`docs/18_COLLECTOR_LAYER.md`](docs/18_COLLECTOR_LAYER.md) para ingesta,
  retries y checkpoints.
- [`docs/19_MANIFOLD_PROVIDER.md`](docs/19_MANIFOLD_PROVIDER.md) para endpoints,
  semántica, límites y restricciones del primer proveedor real.
- [`docs/20_MARKET_OBSERVATIONS.md`](docs/20_MARKET_OBSERVATIONS.md) para
  observaciones históricas y resolución oficial.
- [`docs/21_COLLECTOR_WORKER.md`](docs/21_COLLECTOR_WORKER.md) y
  [`docs/22_COLLECTOR_RUNS.md`](docs/22_COLLECTOR_RUNS.md) para ejecución y
  auditoría.
- [`docs/23_FRONTEND_I18N.md`](docs/23_FRONTEND_I18N.md) y
  [`docs/24_BEGINNER_UX.md`](docs/24_BEGINNER_UX.md) para interfaz y UX.
- [`docs/27_REPLAY_PROVIDER.md`](docs/27_REPLAY_PROVIDER.md),
  [`docs/28_REPLAY_DATASET_FORMAT.md`](docs/28_REPLAY_DATASET_FORMAT.md) y
  [`docs/30_REPLAY_EXPERIMENTS.md`](docs/30_REPLAY_EXPERIMENTS.md) para replay.
- [`docs/31_PREDICTION_AGENT_ARCHITECTURE.md`](docs/31_PREDICTION_AGENT_ARCHITECTURE.md),
  [`docs/32_PREDICTION_RUNS_AND_API.md`](docs/32_PREDICTION_RUNS_AND_API.md) y
  [`docs/33_PREDICTION_EVALUATION.md`](docs/33_PREDICTION_EVALUATION.md) para
  el pipeline predictivo.
- [`docs/34_PAPER_TRADING_ARCHITECTURE.md`](docs/34_PAPER_TRADING_ARCHITECTURE.md)
  y [`docs/35_PAPER_PORTFOLIO_AND_ACCOUNTING.md`](docs/35_PAPER_PORTFOLIO_AND_ACCOUNTING.md)
  para arquitectura y contabilidad virtual.
- [`docs/36_PAPER_TRADING_POLICIES.md`](docs/36_PAPER_TRADING_POLICIES.md),
  [`docs/37_PAPER_SETTLEMENT_PERFORMANCE_AND_API.md`](docs/37_PAPER_SETTLEMENT_PERFORMANCE_AND_API.md)
  y [`docs/38_REPLAY_TRADE.md`](docs/38_REPLAY_TRADE.md) para políticas,
  liquidación, métricas, API y replay.
- [`docs/39_CONTINUOUS_PAPER_VALIDATION.md`](docs/39_CONTINUOUS_PAPER_VALIDATION.md)
  para ciclos periódicos, auditoría, reconciliación y operación de 30 días.

## Arquitectura

AI-Polyphite utiliza un monolito modular con varios procesos:

```text
Next.js ──REST/WebSocket── FastAPI
                              │
                    Application / Domain
                              │
             PostgreSQL ── Outbox / Inbox
                              │
                         Redis Streams
                              │
                    Workers / Scheduler
                              │
                    LLM Provider Interface
                              │
                           Ollama
```

PostgreSQL es la fuente de verdad. Redis se utilizará como transporte y cache,
pero no como registro histórico único.

## Stack

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- TanStack Query
- Zustand
- shadcn/ui
- Recharts
- Playwright

### Backend

- Python 3.13
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Pytest

### Infraestructura

- PostgreSQL
- Redis
- Ollama
- Docker
- Docker Compose

## Requisitos

- Docker 28 o compatible.
- Docker Compose 2.30 o superior.
- Python 3.13 para desarrollo local del backend.
- Node.js 22 y npm 10 para desarrollo local del frontend.
- Ollama en el host, opcional en esta etapa.

## Inicio rápido con Docker

1. Crea el archivo local de configuración:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Revisa los valores de `.env`. Los defaults solo están pensados para
   desarrollo local.

3. Construye y levanta el scaffold:

   ```powershell
   docker compose up --build
   ```

   Con los defaults versionados, Compose ejecuta automáticamente y sin dinero
   real:

   ```text
   Manifold público → collector (60 min) → predicciones nuevas
   → evaluación comercial → campañas paper automáticas
   → liquidación/reconciliación
   ```

   Sólo se predice un mercado cuando existe una observación pública posterior a
   su última predicción live. PostgreSQL se respalda cada 24 horas en
   `backups/`, con validación del archivo y retención de 7 días. Los logs de
   cada contenedor rotan a 5 archivos de 10 MB.

4. Verifica:

   - Frontend: <http://127.0.0.1:3000>
   - Backend liveness: <http://127.0.0.1:8000/health/live>
   - Backend readiness: <http://127.0.0.1:8000/health/ready>
   - Mercados: <http://127.0.0.1:8000/markets>
   - Fuentes: <http://127.0.0.1:8000/sources>
   - Sincronizaciones: <http://127.0.0.1:8000/collector-runs>
   - Datasets: <http://127.0.0.1:8000/replay-datasets>
   - Experimentos: <http://127.0.0.1:8000/experiment-runs>
   - Predicciones: <http://127.0.0.1:8000/predictions>
   - Portfolios simulados: <http://127.0.0.1:8000/paper-portfolios>
   - Operaciones simuladas: <http://127.0.0.1:8000/paper-trades>
   - OpenAPI: <http://127.0.0.1:8000/docs>

   Todas las secciones del dashboard tienen URL propia: `/markets`,
   `/predictions`, `/agents`, `/portfolio`, `/trades`, `/positions`,
   `/performance`, `/experiments`, `/sources`, `/system` y `/settings`.
   Los detalles usan `/markets/{market_id}` y
   `/predictions/{prediction_id}`.

PostgreSQL y Redis solo publican puertos en `127.0.0.1`.

`liveness` indica que el proceso responde. `readiness` comprueba PostgreSQL y
Redis y devuelve `503` si una dependencia no está disponible.

## Configuración y observabilidad

El backend valida toda su configuración al arrancar. La precedencia es:
valores explícitos, variables de entorno, archivo `.env` y defaults de
desarrollo. Se puede seleccionar otro archivo con
`AI_POLYPHITE_ENV_FILE`. El alias legado `PREDICTIONLAB_ENV_FILE` se mantiene
temporalmente para no romper entornos existentes.

Los logs se emiten como JSON. Cada request recibe o propaga:

- `X-Correlation-ID`, para correlación operativa;
- `traceparent`, compatible con W3C Trace Context.

Ambos headers se devuelven en la respuesta. Los valores inválidos se reemplazan
por identificadores seguros. La especificación completa está en
[`docs/13_PLATFORM_FOUNDATION.md`](docs/13_PLATFORM_FOUNDATION.md).

El frontend obtiene la URL pública de la API exclusivamente desde
`NEXT_PUBLIC_API_URL`. El entorno local usa `http://127.0.0.1:8000`. FastAPI
autoriza explícitamente ambos origins de desarrollo
(`http://127.0.0.1:3000` y `http://localhost:3000`) mediante
`CORS_ALLOWED_ORIGINS`; no se utiliza una allowlist global.

Fuentes y worker:

```env
AI_POLYPHITE_ENABLED_PROVIDERS=manifold
AI_POLYPHITE_COLLECTOR_INTERVAL_SECONDS=3600
AI_POLYPHITE_PROVIDER_INTERVALS_SECONDS=manifold=3600
AI_POLYPHITE_COLLECTOR_RUN_IMMEDIATELY=true
AI_POLYPHITE_COLLECTOR_PAGE_SIZE=1000
AI_POLYPHITE_COLLECTOR_MAX_PAGES_PER_RUN=1
AI_POLYPHITE_MANIFOLD_SYNC_MODE=recent
```

Para desarrollo aislado sin red se puede volver al proveedor mock:

```env
AI_POLYPHITE_ENABLED_PROVIDERS=mock
AI_POLYPHITE_PROVIDER_INTERVALS_SECONDS=mock=300
```

Ejecución manual:

```powershell
make collect-once PROVIDER=manifold
make collector-worker
```

Replay histórico:

```powershell
make replay DATASET=synthetic-lab-v1 MODE=accelerated
make replay-step DATASET=synthetic-lab-v1
make replay-reset DATASET=synthetic-lab-v1
make replay-predict DATASET=synthetic-lab-v1 PREDICTION_INTERVAL_HOURS=24
make replay-trade DATASET=synthetic-lab-v1 PREDICTION_INTERVAL_HOURS=24
```

`replay-trade` deriva cada decisión de un `PredictionRun` persistido, usa el
mismo reloj anti-lookahead y liquida sólo resoluciones ya visibles.

Validación paper continua:

```powershell
make paper-validate-once
make paper-validation-worker
docker compose up -d --build
```

Para iniciar toda la operación cotidiana con un solo comando en Windows:

```powershell
.\scripts\start.ps1
```

El script inicia Docker Desktop si está cerrado, levanta todos los servicios,
espera los health checks y muestra las URLs del dashboard y de la API.
También se puede hacer doble clic en `INICIAR_AI_POLYPHITE.cmd`; al terminar,
el lanzador abre el dashboard automáticamente en el navegador.

Compose mantiene el servicio activo por defecto. Cada ciclo usa una
configuración hasheada, registra su auditoría y verifica ledger y balances antes
de declararse completo. La campaña conservadora prevalece por defecto y una
campaña experimental usa un portfolio separado con edge neto mínimo de 0,015.

El botón `Operar` de `/predictions` crea un override exclusivamente simulado:
permite elegir YES/NO y stake aunque la evaluación no recomiende entrar, pero
no pausa ni reemplaza la automatización. Mantiene revalidación de mercado,
límites de riesgo, motivo e idempotencia.

La arquitectura y sus contratos están documentados en
[`docs/40_PREDICTIONS_V2_AND_MANUAL_OVERRIDES.md`](docs/40_PREDICTIONS_V2_AND_MANUAL_OVERRIDES.md).

## Desarrollo local

### Backend

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "./backend[dev]"
uvicorn predictionlab.api.app:app --app-dir backend/src --reload
```

Tests y calidad:

```powershell
pytest backend/tests -m "not integration"
ruff check backend
mypy backend/src
```

Tests de integración con dependencias reales:

```powershell
docker compose up -d --wait postgres redis
pytest backend/tests -m integration
```

Aplicar y verificar migraciones:

```powershell
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini check
```

Desde la imagen de backend:

```powershell
docker compose run --rm backend alembic -c /app/alembic.ini upgrade head
```

### Frontend

```powershell
Set-Location frontend
npm ci
npm run dev
```

Checks:

```powershell
npm run lint
npm run typecheck
npm run build
```

Los tests E2E requieren instalar previamente el navegador de Playwright:

```powershell
npx playwright install chromium
npm run test:e2e
```

También pueden utilizar un Chrome local sin descargar el navegador empaquetado:

```powershell
$env:PLAYWRIGHT_BROWSER_CHANNEL = "chrome"
npm run test:e2e
```

Para ejecutar los checks locales de una vez:

```powershell
.\scripts\check.ps1
.\scripts\check.ps1 -Integration -E2E
```

## Estructura

```text
.
├── backend/          API, dominio, integraciones y runtime Python
├── frontend/         Dashboard Next.js
├── contracts/        Contratos versionados entre procesos
├── infrastructure/   Configuración de despliegue y observabilidad
├── tests/            Pruebas de sistema y E2E
├── scripts/          Automatización de desarrollo
└── docs/             Especificación y ADRs
```

Los límites internos se documentan en los README de cada carpeta. No deben
introducirse dependencias cruzadas que salten las capas definidas.

## Convenciones iniciales

- Código, nombres de contratos y commits en inglés.
- Documentación de producto en español.
- Fechas y timestamps en UTC.
- Dinero y probabilidades nunca se representan con `float` en el dominio.
- Cada ejecución futura deberá registrar versión, configuración y trazabilidad.
- Ninguna integración de trading real forma parte de este repositorio.

## Flujo de trabajo

Cada cambio funcional debe incluir:

1. Explicación y alcance.
2. Implementación pequeña.
3. Unit tests.
4. Integration tests cuando corresponda.
5. Documentación actualizada.
6. Validación antes de continuar con la siguiente tarea.
