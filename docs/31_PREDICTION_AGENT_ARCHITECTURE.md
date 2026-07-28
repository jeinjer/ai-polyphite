# Agentes deterministas y contrato de predicción

Versión: 1.0

Estado: Implementado

## Objetivo

Este slice incorpora el primer núcleo de predicción reproducible de
AI-Polyphite. No intenta simular conocimiento externo ni utiliza un LLM. Su
objetivo es establecer contratos, trazabilidad y evaluación antes de añadir
modelos más complejos.

## Límites

```text
PredictionOrchestrator
  → ReasoningAgent
  → MarketAgent
  → SkepticAgent
  → ConsensusAgent
  → PredictionUnitOfWork
```

- Los agentes no acceden a proveedores, HTTP, SQLAlchemy ni PostgreSQL.
- Ningún agente ejecuta operaciones.
- El orquestador coordina; los agentes no se llaman entre sí.
- Las salidas previas se entregan como datos inmutables y tipados.
- No se persiste chain-of-thought. Sólo se guarda un resumen breve, evidencia
  estructurada y advertencias.

## `PredictionAgent`

El puerto asíncrono expone:

```python
async def predict(agent_input: PredictionAgentInput) -> AgentPrediction
```

La entrada contiene:

- identidad, título, descripción, categoría y estado del mercado;
- `predicted_at` UTC;
- probabilidad, volumen y liquidez visibles;
- observaciones ordenadas cuyo `observed_at <= predicted_at`;
- contexto estructurado explícito;
- experimento, semilla y configuración;
- salidas previas cuando el rol las necesita.

La entidad rechaza observaciones futuras antes de ejecutar el backend. El hash
de entrada incluye datos, semilla, configuración y hashes previos, pero excluye
identificadores operativos del experimento para que dos repeticiones produzcan
el mismo artefacto semántico.

La salida normalizada contiene:

- nombre y versión del agente;
- probabilidad opcional y confianza como `Decimal`;
- recomendación `yes`, `no` o `abstain`;
- resumen, evidencia, advertencias y pesos;
- hashes de entrada y salida;
- duración operativa.

Los hashes no incluyen duración porque el reloj de CPU no es determinista.

## `ModelBackend`

`ModelBackend` separa el rol del agente del mecanismo que genera una
evaluación:

```python
async def assess(
    *,
    agent_name: str,
    agent_input: PredictionAgentInput,
) -> ModelAssessment
```

Implementaciones actuales:

- `RuleBasedModelBackend`: reglas deterministas, sin I/O.
- `MockModelBackend`: respuestas programadas para tests.

Un backend LLM futuro deberá implementar el mismo puerto. No requerirá cambios
en el orquestador, la API, la persistencia ni el dominio.

## Roles iniciales

### ReasoningAgent 1.0.0

Genera una estimación conservadora anclada a la probabilidad visible. Considera
definición del evento, categoría, tendencia visible, cercanía al cierre y un
ajuste estructurado explícito si existe. No inventa conocimiento del mundo.

### MarketAgent 1.0.0

Usa exclusivamente probabilidad actual, tendencia, volatilidad, volumen,
liquidez y antigüedad. No consume noticias ni APIs.

### SkepticAgent 1.0.0

Compara Reasoning y Market, modera edges grandes, penaliza desacuerdo y advierte
por señales incompletas o liquidez ausente.

### ConsensusAgent 1.0.0

Pondera rol y confianza. No usa un promedio simple. Normaliza los pesos
efectivos, reduce la confianza por desacuerdo y puede abstenerse.

## Consenso

Los pesos base iniciales son:

- Reasoning: 0.25.
- Market: 0.35.
- Skeptic: 0.40.

Cada peso base se multiplica por la confianza del agente y después se
normaliza. La configuración puede versionar estos valores. La probabilidad
oficial sólo se publica si supera todas las reglas de abstención.

## Abstención

El consenso registra un motivo explícito cuando:

- el mercado no está abierto;
- falta probabilidad u observaciones;
- la observación es demasiado antigua;
- faltan estimaciones previas;
- el desacuerdo supera el máximo;
- la confianza es menor al mínimo;
- el edge absoluto es menor al umbral débil;
- una probabilidad extrema no tiene observaciones suficientes.

Una abstención no publica probabilidad oficial ni edge. Las estimaciones
intermedias permanecen disponibles para auditar la decisión.

## Observabilidad

Cada agente registra inicio, fin, error, mercado, versión, hashes, recomendación
y duración. El orquestador registra el run completo y propaga `correlation_id`,
`causation_id` y `experiment_run_id`.

Los logs operativos no reemplazan la persistencia durable.

## Restricciones vigentes

- No NewsAgent.
- No búsquedas web.
- No Ollama ni APIs LLM.
- No Event Bus en este slice.
- No paper trading ni dinero real.
