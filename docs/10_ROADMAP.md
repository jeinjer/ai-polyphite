# AI-Polyphite

# Development Roadmap

Version: 1.0

Status: Draft

---

# 1. Objetivo

Construir una plataforma de investigación de mercados de predicción basada en agentes de inteligencia artificial.

El objetivo inicial no es generar dinero.

El objetivo inicial es:

- recolectar datos,
- generar predicciones,
- medir resultados,
- descubrir si existe una ventaja estadística.

---

# 2. Principios de desarrollo

AI-Polyphite debe desarrollarse siguiendo estos principios:

- Priorizar funcionalidad sobre complejidad.
- Medir antes de optimizar.
- Evitar automatización innecesaria.
- Mantener todo reproducible.
- No utilizar dinero real.
- No asumir que una estrategia funciona sin evidencia.

---

# 3. MVP inicial

El MVP debe permitir:

- Conectarse a mercados.
- Guardar información histórica.
- Ejecutar agentes.
- Generar predicciones.
- Simular operaciones.
- Mostrar resultados.

---

# 4. Componentes MVP

## Backend

Implementar:

- FastAPI.
- PostgreSQL.
- Redis.
- Sistema de eventos.
- API interna.

---

## Frontend

Implementar:

- Dashboard básico.
- Lista de mercados.
- Predicciones.
- Paper trading.
- Métricas principales.

---

## Agentes iniciales

No implementar todos los agentes al principio.

Primera versión:

```
Market Agent

↓

News Agent

↓

Research Agent

↓

Probability Agent

↓

Paper Trading Agent

↓

Evaluation Agent
```

---

# 5. Primera ejecución

Objetivo:

Tener el sistema funcionando de extremo a extremo.

Flujo:

```
Detectar mercado

↓

Recolectar información

↓

Generar predicción

↓

Simular operación

↓

Guardar resultado

```

---

# 6. Experimentación inicial

Duración recomendada:

30 días.

---

Configuración:

Capital virtual:

100 USD

---

Operaciones:

Monto pequeño por operación.

Ejemplo:

1 USD.

---

Objetivo:

Recolectar datos.

No maximizar ganancias.

---

# 7. Métricas iniciales

Medir:

- cantidad de mercados analizados,
- cantidad de predicciones,
- precisión,
- calibración,
- ROI simulado,
- drawdown,
- rendimiento por agente.

---

# 8. Segunda etapa

Después de obtener datos:

Agregar:

- Consensus Agent.
- Adversarial Agent.
- Statistical Agent.
- Memory Agent.

---

Objetivo:

Mejorar calidad de predicciones.

---

# 9. Tercera etapa

Agregar sistema experimental avanzado.

Incluye:

- A/B testing.
- Versionado de prompts.
- Comparación de modelos.
- Optimización controlada.
- Replay histórico.

---

# 10. Cuarta etapa

Mejorar inteligencia.

Agregar:

- RAG.
- Memoria histórica.
- Calibración automática.
- Selección dinámica de modelos.

---

# 11. Quinta etapa

Escalamiento.

Agregar:

- Más fuentes.
- Más mercados.
- Más agentes.
- Infraestructura distribuida.

---

# 12. Funcionalidades fuera del MVP

No implementar inicialmente:

- Trading real.
- Ejecución automática con dinero.
- Optimización automática completa.
- Sistemas complejos de machine learning.
- Infraestructura cloud costosa.

---

# 13. Criterios para avanzar

No avanzar a una nueva etapa solamente por tiempo.

Debe existir evidencia.

Ejemplo:

Para considerar una estrategia prometedora:

- suficientes operaciones,
- resultados consistentes,
- buena calibración,
- bajo riesgo,
- rendimiento superior a baseline.

---

# 14. Baselines

Toda estrategia debe compararse contra:

- azar,
- mercado actual,
- estrategia simple.

Ejemplo:

Si comprar siempre YES obtiene 60%:

Una estrategia avanzada debe superar ese resultado.

---

# 15. Documentación continua

Toda decisión importante debe registrarse.

Utilizar:

- Architecture Decision Records.
- Changelog.
- Versionado.

---

# 16. Organización del repositorio

Estructura propuesta:

```
AI-Polyphite/

├── frontend/

├── backend/

├── agents/

├── workers/

├── database/

├── infrastructure/

├── models/

├── experiments/

└── docs/
```

---

# 17. Primera versión funcional

La primera versión se considera exitosa cuando:

- funciona 24/7,
- analiza mercados automáticamente,
- genera predicciones,
- registra decisiones,
- muestra resultados,
- permite evaluar rendimiento.

---

# 18. Criterio de éxito real

AI-Polyphite será considerado exitoso si demuestra:

- ventaja estadística,
- consistencia temporal,
- buena calibración,
- capacidad de adaptación.

No simplemente si obtiene ganancias durante un período corto.

---

# 19. Principio final

Construir un sistema simple que mida correctamente es más valioso que construir un sistema complejo que nadie entiende.

Primero:

observar.

Después:

experimentar.

Después:

optimizar.

Finalmente:

escalar.