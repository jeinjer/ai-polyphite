# Hybrid real-time operation — Implementation report

Fecha: 2026-08-12

## Resultado

AI-Polyphite quedó configurado para observar Manifold cada minuto, seleccionar
mercados binarios de resolución corta, analizarlos con un pipeline híbrido local
y ejecutar únicamente decisiones paper automáticas. El dashboard se redujo a
una lectura ejecutiva de estado, predicciones y actividad.

## Cambios principales

- Ollama/Qwen estructurado para ReasoningAgent y SkepticAgent.
- MarketAgent, ConsensusAgent, comercial, riesgo y contabilidad deterministas.
- Filtro semántico, veto de calificación y horizonte 5 min–14 días.
- Semántica YES/NO corregida y selección idempotente por configuración.
- Evaluación live sin lookahead y una muestra por mercado resuelto.
- Ingesta Manifold tolerante a elementos incompatibles.
- Automatización pause/resume durable en Redis.
- UI sin operación manual, traducción ni menús técnicos; tema claro/oscuro.
- Compose con Ollama, modelo local, ciclos de 60 s y lote de una inferencia.

## Alcance explícito

Datos de mercado reales, inferencia local y capital simulado. No se añadió
NewsAgent, ejecución real, scheduler distribuido ni Event Bus.
