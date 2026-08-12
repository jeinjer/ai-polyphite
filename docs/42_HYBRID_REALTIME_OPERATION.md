# Operación híbrida de corto horizonte

## Objetivo

El runtime prioriza feedback verificable: analiza mercados binarios públicos
que deberían resolverse entre cinco minutos y catorce días. No promete que cada
ciclo produzca un trade; sí garantiza que la ingesta, la decisión y el motivo
queden observables.

## Cadencia

- Collector Manifold: 60 segundos, una página reciente de 300 mercados.
- Validador paper: 60 segundos.
- Lote generativo: un mercado nuevo por ciclo en la configuración local.
- Dashboard: refresco de lecturas cada 30 segundos.

El límite de un mercado evita que dos llamadas secuenciales a Ollama por mercado
generen ciclos permanentemente atrasados en CPU. Puede aumentarse mediante
`PREDICTION_MAXIMUM_CANDIDATES_PER_BATCH` después de medir el hardware.

## Selección

Un candidato debe estar abierto, tener `resolution_at`, caer dentro del
horizonte configurado y poseer una observación posterior a la última predicción
live de la misma configuración. La consulta prioriza la resolución más próxima.

Preguntas triviales como `1 + 1 = 2`, circulares, personales, privadas o sin
criterio público pueden ser rechazadas antes del consenso. Ese veto no puede ser
anulado por otros dos agentes.

## Híbrido y fallback

Ollama sólo participa en Reasoning y Skeptic. Market y Consensus son
deterministas. Si Ollama falla, un circuit breaker evita insistir durante cinco
minutos y usa el baseline rule-based con un warning auditable.

El modelo predeterminado es `qwen3:1.7b`. El primer inicio de Compose descarga
el modelo y puede tardar. La configuración de modelo, prompts, temperatura,
seed, horizonte y política comercial forma parte de hashes durables.

## Evaluación

`GET /prediction-evaluation` calcula métricas sobre mercados live resueltos.
Para evitar inflar artificialmente la muestra, toma una sola predicción —la
última anterior a la resolución— por mercado. Compara sistema, market baseline
y constant baseline sin lookahead.

## Control del espectador

`GET /automation` informa el estado. `POST /automation/pause` y
`POST /automation/resume` detienen o reanudan nuevas predicciones/operaciones.
Las posiciones ya abiertas continúan registradas y se liquidan según el outcome
oficial; no se ofrece operación manual en la UI.

## Seguridad

- Manifold se consume read-only.
- No existen credenciales de ejecución, wallets ni dinero real.
- Las operaciones y balances usan `MANA_SIMULATED`.
- El sistema no consulta noticias ni inventa métricas ausentes del proveedor.
