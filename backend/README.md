# AI-Polyphite Backend

Backend Python del monolito modular.

## Responsabilidades

- Exponer la API HTTP y WebSocket.
- Ejecutar casos de uso de aplicación.
- Mantener reglas de dominio independientes de frameworks.
- Persistir hechos y proyecciones en PostgreSQL.
- Publicar y consumir eventos durables.
- Ejecutar workers, scheduler y agentes.
- Adaptar proveedores externos y modelos LLM.

## Límites de capas

```text
api
 ↓
application
 ↓
domain
 ↑
infrastructure / integrations
```

- `domain` no importa FastAPI, SQLAlchemy, Redis ni SDKs externos.
- `application` coordina puertos y casos de uso.
- `api` traduce HTTP/WebSocket a comandos y queries.
- `infrastructure` implementa persistencia, eventos y observabilidad.
- `integrations` implementa adaptadores de servicios externos.
- `providers` define la frontera neutral de proveedores de mercados.
- `runtime` contiene entrypoints de workers y scheduler.

## Estado

Existe ingesta multi-provider, histórico reproducible y un pipeline de cuatro
agentes deterministas. `PredictionRun` conserva consenso, resultado estimado,
edge, salidas versionadas y hashes. `CommercialEvaluation` decide por campaña
si la estimación es accionable después de costes. Paper trading reproducible
agrega portfolios, trades, posiciones, settlements, ledger y métricas sólo en
unidades simuladas. La automatización es predeterminada y los overrides
manuales quedan separados y auditados. La ejecución real no existe.

## Contratos técnicos

- `GET /health/live`: confirma que el proceso HTTP está vivo.
- `GET /health/ready`: comprueba PostgreSQL y Redis; devuelve `503` si alguna
  dependencia no está disponible.
- `GET /markets`: listado paginado, filtrado y ordenado.
- `GET /markets/{market_id}`: detalle con provider y último snapshot.
- `GET /predictions`: resumen paginado, filtrable y sin payload de agentes.
- `GET /predictions/{prediction_id}`: agregado completo con agentes,
  evaluación comercial y ejecuciones relacionadas.
- `GET /agent-predictions`: últimas salidas completas para el monitor técnico.
- `POST /paper-trading/manual-trades`: override dev-only exclusivamente
  simulado; nunca reemplaza la automatización.
- `GET /paper-portfolios`: portfolios virtuales y balances reconciliables.
- `GET /paper-trades`: fills simulados con costes y procedencia.
- `GET /paper-positions`: posiciones long-only y estado de liquidación.
- `GET /paper-settlements`: resultados oficiales aplicados.
- Todas las respuestas propagan `X-Correlation-ID` y `traceparent`.

La configuración y los contratos se detallan en
[`../docs/13_PLATFORM_FOUNDATION.md`](../docs/13_PLATFORM_FOUNDATION.md).

## Desarrollo

Desde la raíz:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "./backend[dev]"
uvicorn predictionlab.api.app:app --app-dir backend/src --reload
```

## Calidad

```powershell
pytest backend/tests -m "not integration"
ruff check backend
mypy backend/src
```

Para las pruebas de integración:

```powershell
docker compose up -d --wait postgres redis
pytest backend/tests -m integration
```

Migraciones:

```powershell
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini check
```
