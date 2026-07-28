# 22 — Auditoría de sincronizaciones

Estado: implementado  
Fecha: 2026-07-28

`CollectorRun` conserva una auditoría segura de cada intento de sincronización.
Se crea en estado `running` antes de adquirir el lock y termina como
`completed`, `failed` o `skipped_locked`.

Registra tiempos, duración, fuente, correlation ID, retries y contadores de
mercados y observaciones. En fallos sólo persiste `safe_error_type`: no guarda
mensajes remotos, URLs con credenciales ni payloads.

## API

- `GET /collector-runs`
- `GET /collector-runs/{run_id}`

El listado acepta paginación y filtros `provider`, `status`, `from` y `to`.
Ordena por inicio descendente y UUID como desempate.

Esta auditoría responde qué se intentó, cuándo, con qué resultado y cuántos
datos se incorporaron. No reemplaza logs ni métricas agregadas.

La tabla se crea mediante `20260728_0005_add_collector_runs.py`.
