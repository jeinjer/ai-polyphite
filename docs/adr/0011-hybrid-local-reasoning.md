# ADR-0011: razonamiento local híbrido bajo controles deterministas

- Estado: Accepted
- Fecha: 2026-08-12
- Reemplaza parcialmente: ADR-0008

## Contexto

El pipeline determinista permitió validar persistencia, replay, evaluación y
paper trading, pero sus agentes compartían reglas demasiado parecidas. Eso
limitaba la interpretación del contrato, producía un “debate” artificial y no
detectaba de forma suficiente mercados bait, personales o ambiguos.

Se necesita razonamiento semántico sin entregar a un modelo generativo las
invariantes financieras ni comprometer reproducibilidad y disponibilidad.

## Decisión

Adoptar un pipeline híbrido:

1. `ReasoningAgent` usa Ollama con salida JSON validada para calificar el
   contrato y estimar P(YES).
2. `MarketAgent` permanece determinista y usa únicamente observaciones.
3. `SkepticAgent` usa Ollama para revisar adversarialmente las salidas previas.
4. `ConsensusAgent`, evaluación comercial, sizing, riesgo, ejecución y
   contabilidad permanecen deterministas.
5. Un filtro determinista mínimo rechaza casos inequívocos y horizontes fuera
   de 5 minutos–14 días antes de consumir inferencia.
6. La abstención semántica de `ReasoningAgent` actúa como veto del consenso.
7. Ollama tiene timeout, contrato tipado, circuit breaker y fallback al baseline
   reproducible. El fallback queda señalado en warnings.
8. Modelo, versiones de prompts, temperaturas, políticas y seed participan de
   los hashes de configuración.

## Consecuencias positivas

- Interpretación y crítica realmente distintas de las señales cuantitativas.
- Las reglas financieras críticas siguen siendo comprobables y reproducibles.
- El sistema continúa funcionando cuando Ollama falla.
- Cambiar el modelo no modifica dominio, aplicación ni paper trading.

## Costes y riesgos

- Una misma entrada puede producir estimaciones distintas dentro del rango
  permitido por la temperatura.
- La inferencia local aumenta latencia, uso de RAM y CPU/GPU.
- El modelo puede equivocarse o inventar argumentos; el contrato, la ausencia
  de fuentes externas y los controles deterministas reducen, pero no eliminan,
  ese riesgo.
- Los resultados de distintas configuraciones no deben mezclarse; se separan
  mediante hashes y portfolios.

## Alternativas descartadas

- Hacer generativos todos los agentes: demasiada variabilidad en riesgo y
  contabilidad.
- Mantener todos los agentes deterministas: no resuelve la falta de análisis
  semántico ni el debate redundante.
- Añadir NewsAgent ahora: introduce una fuente adicional de errores antes de
  demostrar valor con datos estructurados.
