# Validación paper continua

Versión: 2.0
Estado: Implementado
Fecha: 2026-07-28

## Objetivo

Ejecutar de forma repetible el pipeline ya aprobado sobre datos visibles en
PostgreSQL:

```text
mercados abiertos as-of scheduled_for
  → PredictionOrchestrator
  → campaña conservadora automática
  → campaña experimental automática separada
  → settlement / mark-to-market
  → reconciliación contable
  → PaperValidationRun durable
```

No agrega agentes, cambia políticas ni habilita ejecución real.

## Semántica del ciclo

Cada ciclo usa un `scheduled_for` UTC alineado a la cadencia configurada. Su
`cycle_key` incorpora ese timestamp y el hash de configuración congelada de
predicción y paper trading.

- `PredictionRun` evita duplicados por mercado, timestamp y configuración.
- `TradeDecision` evita duplicados por portfolio y predicción.
- settlement y snapshots conservan su idempotencia previa.
- un advisory lock PostgreSQL permite un único ciclo activo.
- repetir un ciclo completado registra `skipped_completed` sin side effects.
- la contención entre procesos registra `skipped_locked`.
- el modo autónomo filtra por proveedor y sólo selecciona mercados cuya última
  observación sea posterior a la última predicción live.

Cada intento queda en `paper_validation_runs` como `running`, `completed`,
`failed`, `skipped_locked` o `skipped_completed`. Sólo se persisten tipos de
error seguros, IDs de trazabilidad, contadores, hashes y el resultado de
reconciliación; no se guardan secretos ni mensajes remotos.

Las dos campañas reutilizan exactamente el mismo batch de predicciones por
slot. Cada una conserva portfolio, evaluación comercial, configuración,
decisiones y métricas independientes. Un override manual no participa de
ninguna de las dos y no detiene el worker.

## Reconciliación

Después de operar y liquidar, el runtime reconstruye:

- cash desde la suma append-only del ledger;
- reserva y exposición desde posiciones abiertas;
- P&L realizado desde settlements;
- P&L no realizado desde marks de posiciones abiertas;
- equity desde `cash + reserva + P&L no realizado`;
- cantidad exacta de entradas de capital inicial.

Compara esos valores con el estado materializado del portfolio. Una discrepancia
no se repara automáticamente: el ciclo termina `failed` con
`PaperAccountingReconciliationError` y códigos estables de diferencia. Esto
evita ocultar corrupción contable.

Antes de aplicar nuevos marks, el agregado materializado de P&L no realizado se
reconstruye desde las posiciones abiertas durables usando la precisión
`NUMERIC(28, 8)` de persistencia. Esto corrige únicamente deriva de redondeo;
una diferencia material de cash, reserva, ledger, exposición o P&L continúa
fallando la reconciliación.

## Configuración congelada

Defaults del MVP:

```env
AI_POLYPHITE_PAPER_VALIDATION_INTERVAL_SECONDS=3600
AI_POLYPHITE_PAPER_VALIDATION_RUN_IMMEDIATELY=true
AI_POLYPHITE_PAPER_VALIDATION_PORTFOLIO_NAME=Autonomous Manifold paper validation
AI_POLYPHITE_PAPER_VALIDATION_RANDOM_SEED=17
AI_POLYPHITE_PAPER_VALIDATION_PROVIDER_CODES=manifold
AI_POLYPHITE_PAPER_VALIDATION_ONLY_NEW_OBSERVATIONS=true
AI_POLYPHITE_EXPERIMENTAL_CAMPAIGN_ENABLED=true
AI_POLYPHITE_EXPERIMENTAL_MIN_NET_EDGE=0.015
```

El hash incluye los umbrales predictivos, el hash completo de políticas paper,
la semilla, unidad, capital inicial, cadencia, nombre de campaña y
`AI_POLYPHITE_CODE_VERSION`. Si cambia cualquier valor relevante, se crea otro
portfolio identificado por el nuevo hash y no se mezcla evidencia.

Para una ventana de 30 días se debe conservar el mismo `.env`, imagen y
`AI_POLYPHITE_CODE_VERSION`. No se deben retocar parámetros según resultados
intermedios.

La campaña conservadora preserva su política congelada. `experimental-v1`
reduce el gate predictivo y opera sólo si el edge neto estimado alcanza 0,015.
Su portfolio se denomina `Experimental paper validation` más el prefijo del
hash correspondiente.

## Operación

Una ejecución manual:

```powershell
make paper-validate-once
.\scripts\paper-validation.ps1 -Mode once
```

Un timestamp lógico explícito sirve para reintentos operativos:

```powershell
.\scripts\paper-validation.ps1 `
  -Mode once `
  -ScheduledFor "2026-07-28T12:00:00Z"
```

Worker local:

```powershell
make paper-validation-worker
```

Docker Compose lo inicia por defecto como parte de la campaña autónoma:

```powershell
docker compose up -d --build
docker compose logs -f paper-validator
```

El proceso usa la misma imagen del monolito modular y una composition root
separada; no es un microservicio ni una nueva fuente de verdad.

## Respuesta operativa

- `completed`: revisar contadores y `reconciliation_ok=true`.
- `skipped_completed`: comportamiento esperado ante retry del mismo slot.
- `skipped_locked`: otro proceso ejecutaba el ciclo; no requiere reparación.
- `failed`: inspeccionar correlation ID y `safe_error_type`; corregir la causa y
  repetir el mismo `scheduled_for`.
- reconciliación fallida: detener la campaña, preservar la base y diagnosticar
  ledger/posición/portfolio. Nunca editar balances para silenciar la alerta.

El worker continúa tras un ciclo fallido y respeta SIGINT/SIGTERM de forma
cooperativa.

Las campañas del mismo slot se ejecutan de forma aislada: el fallo de la
conservadora no omite la experimental, ni viceversa. El primer error se vuelve
a propagar después de intentar todas las campañas. Las esperas se reevalúan en
segmentos máximos de 60 segundos, de modo que una suspensión y reanudación del
host no deja al proceso bloqueado durante el resto del intervalo anterior.

## Límites

- No contiene scheduler distribuido.
- No expone todavía `paper_validation_runs` por REST.
- No demuestra ventaja estadística ni ejecutabilidad real.
- No sustituye una campaña de 30 días ni el informe final.
- No permite dinero real, brokers, wallets, leverage, short ni cierre anticipado.
