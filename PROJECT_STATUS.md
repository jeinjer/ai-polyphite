# AI-Polyphite — Project Status

Última actualización: 2026-08-12

## Estado general

**Fase:** MVP autónomo de investigación y paper trading con razonamiento híbrido.

**Estado:** operativo en Docker Compose con datos públicos reales de Manifold,
predicciones locales y capital exclusivamente simulado.

**Dinero real:** prohibido y no implementado.

## Flujo operativo actual

```text
Manifold público (read-only, cada 60 s)
  → Collector idempotente
  → PostgreSQL
  → filtro semántico y temporal (5 min–14 días)
  → ReasoningAgent + SkepticAgent en Ollama
  → MarketAgent + ConsensusAgent deterministas
  → evaluación comercial y riesgo deterministas
  → paper trading y settlement
  → dashboard ejecutivo con refresco cada 30 s
```

El lote local procesa como máximo un mercado nuevo por ciclo para no solapar
inferencias en una máquina sin GPU dedicada. Una observación sólo vuelve a
analizarse si es nueva para la versión configurada del pipeline.

## Implementado y activo

- Provider SDK neutral con Mock, Replay y Manifold read-only.
- Ingesta incremental observable, tolerante a payloads incompatibles y con
  cuarentena por elemento.
- Predicciones limitadas a mercados binarios abiertos con resolución objetiva
  entre cinco minutos y catorce días.
- Rechazo previo de preguntas triviales, bait, circulares, personales o no
  reproducibles; el rechazo semántico bloquea el consenso.
- Arquitectura híbrida:
  - Ollama/Qwen para interpretación semántica y crítica adversarial;
  - reglas deterministas para señales de mercado, consenso, costes, riesgo y
    contabilidad;
  - circuit breaker y fallback reproducible si Ollama no responde.
- Probabilidades YES/NO con semántica uniforme entre agentes y consenso.
- Predicciones, evidencia, hashes, decisiones y operaciones reconstruibles.
- Evaluación live contra resultados oficiales usando una única predicción por
  mercado resuelto y barrera anti-lookahead.
- Dos campañas paper aisladas, reconciliación contable y portfolios versionados
  por configuración.
- Automatización pausable y reanudable; la interfaz no ofrece operaciones
  manuales.
- Dashboard ejecutivo con tres recorridos: Resumen, Predicciones y Actividad.
- Capital invertido, reserva, diferencia, fecha actual, última ingesta y última
  predicción visibles en el encabezado.
- Tema claro/oscuro, navegación lateral, detalle lazy y listado paginado.
- PostgreSQL, Redis, FastAPI, Next.js, workers, Ollama y backup en Compose.
- Inicio cotidiano con `INICIAR_AI_POLYPHITE.cmd` o `scripts/start.ps1`.

## Qué significan “datos reales” y “autónomo”

- Los mercados, probabilidades y resoluciones provienen de la API pública de
  Manifold.
- Las probabilidades de los agentes son estimaciones del laboratorio; no son
  hechos ni señales financieras verificadas externamente.
- Todo el capital, las órdenes, los trades y el P&L son simulados.
- Mientras Docker y la computadora permanezcan activos, collector y validador
  trabajan sin intervención. Tras suspensión o reinicio, `INICIAR_AI_POLYPHITE.cmd`
  reanuda el stack sin duplicar los ciclos completados.

## Limitaciones conocidas

- Sólo hay un proveedor real activo.
- No existe NewsAgent, búsqueda web, RAG ni conocimiento externo en tiempo real.
- La inferencia local depende del rendimiento de CPU/GPU del host; por eso el
  lote está acotado.
- “Sin operación” puede ser una salida correcta por falta de edge neto, riesgo,
  mercado no evaluable o desacuerdo. El dashboard expone el motivo.
- La evidencia estadística seguirá siendo insuficiente hasta acumular una
  cantidad material de mercados resueltos; la UI no presenta ROI ficticio.
- No se evita la suspensión del sistema operativo desde la aplicación.

## Decisiones vigentes

Once ADR aceptados. ADR-0011 reemplaza la postura temporal de ADR-0008 y adopta
razonamiento generativo local bajo controles deterministas.

## Fuera de alcance

- Ejecución con dinero real, wallets, brokers o credenciales de trading.
- Event Bus durable, microservicios, scheduler distribuido o WebSockets.
- Noticias, proveedores LLM cloud y optimización automática de estrategias.
- HistoricalProvider, Metaculus y Polymarket.

## Siguiente validación

Mantener la configuración congelada durante 30 días, observar disponibilidad,
latencia, cobertura, Brier score, edge neto, concentración y drawdown, y publicar
un informe sin optimización retrospectiva. No agregar NewsAgent hasta comprobar
si el sistema aprende algo útil con datos estructurados.

## Fuente de verdad

Este archivo describe el código actual. [`TASKS.md`](TASKS.md) contiene el
backlog y [`docs/`](docs/) explica los contratos y decisiones.
