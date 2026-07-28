# ADR-0008: Agentes deterministas antes de integrar LLM

- **Estado:** Accepted
- **Fecha:** 2026-07-28
- **Alcance:** generación y evaluación inicial de predicciones

## Contexto

AI-Polyphite necesita demostrar que puede reconstruir una predicción, impedir
lookahead, repetir resultados y medirlos contra baselines. Introducir primero
un LLM añadiría variabilidad, dependencias externas, prompts, costos y errores
de protocolo antes de validar ese circuito experimental.

El sistema también necesita una frontera que no ate los casos de uso a Ollama,
OpenAI, Anthropic u otro proveedor.

## Decisión

Los primeros cuatro agentes usan contratos tipados y
`RuleBasedModelBackend`, completamente determinista y sin I/O.

`ModelBackend` es el puerto estable para mecanismos futuros.
`MockModelBackend` permite contract y orchestration tests. Ningún backend LLM se
implementa en este slice.

Los agentes son componentes lógicos dentro del monolito modular. El
`PredictionOrchestrator` coordina las etapas y pasa salidas inmutables; un agente
no llama a otro, no accede a proveedores y no persiste.

Los hashes semánticos excluyen duración, correlation IDs e identificadores
aleatorios de experimentos. La duración se conserva como telemetría.

## Consecuencias positivas

- Replay y tests producen artefactos comparables.
- Los errores de datos, dominio y evaluación pueden aislarse.
- Existe un baseline de complejidad mínima.
- Añadir un backend LLM no cambia persistencia ni API.
- Las explicaciones guardadas son breves y auditables.

## Consecuencias negativas

- Las reglas no incorporan conocimiento externo.
- La calidad predictiva inicial será limitada.
- Los pesos y umbrales deberán evaluarse, no asumirse correctos.
- El dataset sintético valida reproducibilidad, no eficacia real.

## Alternativas descartadas

### Ollama desde el primer agente

Descartado porque mezcla validación del pipeline con disponibilidad y
variabilidad del modelo.

### Llamadas directas del agente al proveedor LLM

Descartado porque acopla lógica, transporte y credenciales.

### Guardar razonamiento completo

Descartado por trazabilidad innecesariamente sensible y porque el contrato sólo
requiere resumen y evidencia estructurada.

### Promediar agentes sin pesos

Descartado porque ignora rol, confianza y desacuerdo.

## Criterio para avanzar

Un backend LLM sólo deberá añadirse cuando exista una hipótesis verificable y
se pueda comparar contra este baseline mediante replay, Brier Score, log loss,
calibración y cobertura.
