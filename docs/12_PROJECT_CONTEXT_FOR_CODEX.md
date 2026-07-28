# AI-Polyphite

# Project Context For Codex

Version: 1.0

Status: Initial Context

---

# 1. Introducción

Estamos construyendo AI-Polyphite.

AI-Polyphite es una plataforma experimental basada en agentes de inteligencia artificial para analizar mercados de predicción.

El objetivo no es crear un sistema de apuestas automático.

El objetivo es construir un laboratorio de investigación capaz de:

- recolectar información,
- analizar mercados,
- generar predicciones probabilísticas,
- medir resultados,
- aprender de errores.

---

# 2. Objetivo principal

Crear un sistema que permita responder:

"Si hubiéramos utilizado este sistema durante un período determinado, ¿habría generado una ventaja estadística?"

---

El sistema debe priorizar:

- medición,
- experimentación,
- reproducibilidad.

No debe asumir que existe una ventaja.

Debe demostrarla.

---

# 3. Contexto del proyecto

La idea surge al observar sistemas de predicción con grandes cantidades de mercados analizados diariamente.

El enfoque buscado es:

- analizar cientos o miles de mercados,
- utilizar múltiples agentes IA,
- combinar diferentes perspectivas,
- simular resultados,
- evaluar rendimiento histórico.

---

# 4. Filosofía del sistema

La IA no debe actuar como un oráculo.

La IA funciona como un equipo de analistas.

Ejemplo:

```
Research Agent

↓

Probability Agent

↓

Adversarial Agent

↓

Consensus Agent

↓

Evaluation Agent
```

---

Cada agente tiene una responsabilidad específica.

---

# 5. Objetivo inicial

La primera versión debe funcionar completamente en modo simulación.

No utilizar dinero real.

---

Configuración inicial:

Capital virtual:

100 USD

---

Ejemplo:

Analizar:

100-200 mercados diarios.

Simular:

1 USD por operación.

---

Registrar:

- predicción,
- probabilidad,
- decisión,
- resultado,
- ganancia/pérdida simulada.

---

# 6. Principio fundamental

No queremos un sistema que parezca inteligente.

Queremos un sistema que pueda demostrar con datos si tiene valor.

---

# 7. Arquitectura esperada

Tecnologías principales:

Frontend:

- Next.js.
- TypeScript.
- TailwindCSS.

---

Backend:

- FastAPI.
- Python.

---

Base de datos:

- PostgreSQL.

---

Cache y eventos:

- Redis.

---

IA local:

- Ollama.

---

Contenedores:

- Docker.
- Docker Compose.

---

# 8. Hardware inicial

El desarrollo inicial será realizado en una notebook:

- RTX 4050.
- 16GB RAM DDR5.
- SSD.

---

La infraestructura debe estar optimizada para funcionar localmente.

No asumir servidores externos.

---

# 9. Primera tarea de Codex

Antes de escribir código:

Leer:

```
docs/00_VISION.md

docs/01_ARCHITECTURE.md

docs/02_DATABASE.md

docs/03_AGENTS.md

docs/04_PAPER_TRADING.md

docs/05_DASHBOARD.md

docs/06_AI_SYSTEM.md

docs/07_APIS.md

docs/08_DEPLOYMENT.md

docs/09_TESTING.md

docs/10_ROADMAP.md

docs/11_CODEX_GUIDELINES.md
```

---

Después:

Analizar arquitectura.

Detectar posibles problemas.

Proponer plan inicial.

---

# 10. Primera implementación esperada

La primera versión debe priorizar un flujo completo.

No construir inteligencia avanzada primero.

---

Orden esperado:

```
Base de datos

↓

Backend API

↓

Integración de mercados

↓

Sistema de eventos

↓

Primer agente simple

↓

Paper Trading

↓

Dashboard
```

---

# 11. Restricciones

Codex NO debe:

- cambiar tecnologías principales,
- agregar complejidad innecesaria,
- crear microservicios sin necesidad,
- implementar trading real,
- modificar estrategias automáticamente.

---

# 12. Estilo de desarrollo

Preferimos:

Código simple.

Arquitectura clara.

Módulos pequeños.

Tests.

Documentación.

---

Evitar:

- soluciones rápidas difíciles de mantener,
- código generado sin explicación,
- dependencias innecesarias.

---

# 13. Uso de modelos IA

Los modelos pueden cambiar.

No acoplar la arquitectura a un proveedor.

Debe existir una capa de abstracción.

---

Ejemplo:

```
Agent

↓

LLM Interface

↓

Provider

↓

Model
```

---

# 14. Experimentos

Toda mejora debe poder medirse.

Ejemplo:

Cambiar prompt:

Antes:

Agent v1

Después:

Agent v2

Comparar:

- accuracy,
- calibration,
- ROI simulado,
- costo.

---

# 15. Criterio de éxito

AI-Polyphite será exitoso si:

- funciona de manera autónoma,
- genera predicciones,
- registra resultados,
- permite analizar rendimiento,
- encuentra patrones estadísticamente significativos.

---

No será considerado exitoso solamente porque:

- gana durante pocos días,
- tiene buenas predicciones aisladas,
- produce análisis interesantes.

---

# 16. Primera conversación esperada con Codex

Al iniciar:

No escribir código inmediatamente.

Primero:

1. Leer documentación.

2. Analizar arquitectura.

3. Confirmar entendimiento.

4. Proponer estructura inicial.

5. Crear plan de implementación.

---

# 17. Rol esperado de Codex

Actuar como un ingeniero senior trabajando dentro del proyecto.

Debe:

- cuestionar decisiones débiles,
- detectar riesgos,
- sugerir mejoras,
- mantener orden.

---

# 18. Regla final

AI-Polyphite debe construirse como un experimento científico de ingeniería.

La prioridad es:

Datos.

Medición.

Validación.

Iteración.

No complejidad.

---

# 19. Estado ejecutable actual — 2026-07-28

El código implementa:

- dominio y API read-only de mercados;
- observaciones históricas nullable;
- outcomes oficiales y auditoría de estados;
- Provider SDK con Mock y Manifold read-only;
- collector incremental y worker periódico;
- auditoría `CollectorRun`;
- dashboard es-ES/en-US con vista simple y avanzada.

Reglas vigentes para próximos cambios:

1. `MarketObservation` es informativa; nunca es `ExecutableQuote`.
2. No completar métricas ausentes.
3. Manifold sólo se activa por configuración explícita.
4. API y worker son procesos separados.
5. PostgreSQL continúa como fuente durable de verdad.
6. No mostrar operaciones, P&L o ROI hasta implementar simulación real.
7. Todo texto visible del frontend debe pasar por el catálogo i18n.

Documentos de continuidad:

- `20_MARKET_OBSERVATIONS.md`
- `21_COLLECTOR_WORKER.md`
- `22_COLLECTOR_RUNS.md`
- `23_FRONTEND_I18N.md`
- `24_BEGINNER_UX.md`
- `25_NAVIGATION_MAP.md`
- `26_METRICS_AND_TOOLTIPS.md`
- `adr/0006-observation-vs-executable-quote.md`

---

# 20. Base de replay aprobable — 2026-07-28

El código añade:

- `ReplayProvider` sobre JSONL local versionado;
- `ReplayClock` y `SystemClock`;
- barrera contra observaciones y resoluciones futuras;
- dataset sintético de 20 mercados y 80 observaciones;
- modos step, accelerated, until y reset;
- auditoría durable `ExperimentRun`;
- endpoints y dashboard de experimentos.

Reglas para el siguiente slice:

1. No añadir más infraestructura base antes de los agentes mínimos.
2. Implementar `ReasoningAgent`, `MarketAgent`, `SkepticAgent` y
   `ConsensusAgent`.
3. Persistir predicciones y compararlas con la probabilidad disponible en el
   instante simulado.
4. Los agentes nunca reciben el dataset completo ni información futura.
5. `NewsAgent` queda fuera hasta validar predicciones estructuradas
   reproducibles.
6. No mostrar ROI u operaciones antes del motor de simulación correspondiente.

Documentos de continuidad:

- `27_REPLAY_PROVIDER.md`
- `28_REPLAY_DATASET_FORMAT.md`
- `29_CREATING_REPLAY_DATASETS.md`
- `30_REPLAY_EXPERIMENTS.md`
- `adr/0007-simulated-clock-and-lookahead-barrier.md`
