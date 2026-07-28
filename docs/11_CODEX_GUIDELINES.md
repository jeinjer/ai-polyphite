# AI-Polyphite

# Codex Development Guidelines

Version: 1.0

Status: Draft

---

# 1. Objetivo

Este documento define las reglas de trabajo para cualquier agente de desarrollo basado en IA.

El objetivo es mantener:

- código mantenible,
- arquitectura consistente,
- cambios controlados,
- documentación actualizada.

---

# 2. Rol de Codex

Codex funciona como un desarrollador asistente.

Sus responsabilidades:

- implementar funcionalidades,
- crear código siguiendo arquitectura existente,
- detectar problemas,
- proponer mejoras,
- escribir tests,
- documentar cambios.

---

Codex NO debe:

- cambiar arquitectura sin aprobación,
- eliminar funcionalidades existentes,
- modificar estrategias automáticamente,
- tomar decisiones de negocio.

---

# 3. Antes de escribir código

Antes de implementar una funcionalidad:

Codex debe:

1. Leer documentación relevante.

2. Entender arquitectura actual.

3. Revisar código existente.

4. Identificar dependencias.

5. Proponer un plan corto.

---

Ejemplo:

Antes de crear un nuevo agente:

Revisar:

```
docs/03_AGENTS.md

docs/06_AI_SYSTEM.md

estructura actual de agentes
```

---

# 4. Principio de cambios pequeños

Evitar cambios gigantes.

Preferir:

```
Cambio pequeño

↓

Test

↓

Validación

↓

Siguiente cambio
```

---

No realizar:

- refactors masivos,
- migraciones completas,
- cambios de stack,

sin aprobación.

---

# 5. Arquitectura primero

El código debe respetar la arquitectura definida.

Ejemplo:

Incorrecto:

```
Agent

↓

API externa directamente
```

---

Correcto:

```
Agent

↓

Service Layer

↓

API Adapter

↓

External Source
```

---

# 6. Organización del código

Mantener separación clara.

Ejemplo:

```
backend/

├── api/

├── services/

├── models/

├── repositories/

├── agents/

├── workers/

└── tests/
```

---

Cada componente debe tener una responsabilidad.

---

# 7. Calidad del código

Todo código debe priorizar:

- claridad,
- simplicidad,
- legibilidad,
- mantenibilidad.

---

Evitar:

- código duplicado,
- funciones gigantes,
- lógica mezclada,
- archivos demasiado grandes.

---

# 8. Documentación

Toda funcionalidad nueva debe incluir:

- descripción,
- propósito,
- configuración necesaria,
- ejemplos.

---

Actualizar:

- README.
- Documentación técnica.
- Changelog.

---

# 9. Testing obligatorio

Toda nueva funcionalidad debe incluir pruebas.

Tipos:

- Unit tests.
- Integration tests.
- Regression tests.

---

No aceptar:

"Funciona en mi máquina".

---

# 10. Manejo de errores

Todo sistema externo puede fallar.

El código debe manejar:

- timeouts,
- errores de red,
- datos incompletos,
- respuestas inválidas.

---

Nunca:

```
try:

hacer todo

except:

ignorar error
```

---

# 11. Variables y configuración

Nunca escribir:

- API keys,
- passwords,
- tokens,

dentro del código.

---

Utilizar:

```
.env

environment variables

configuration files
```

---

# 12. Git Workflow

Cada cambio debe tener:

- commit descriptivo,
- explicación clara.

---

Ejemplo:

Correcto:

```
Add Polymarket market ingestion service
```

Incorrecto:

```
update stuff
```

---

# 13. Commits pequeños

Preferir:

```
Commit 1:
Create database model

Commit 2:
Add repository

Commit 3:
Add API endpoint

Commit 4:
Add tests
```

---

Evitar:

```
Complete entire system
```

---

# 14. Uso de Inteligencia Artificial

Los modelos IA deben utilizarse como herramientas.

Nunca asumir:

- que el código generado es correcto,
- que una solución es óptima,
- que una predicción es verdadera.

---

Todo debe validarse.

---

# 15. Cambios en agentes IA

Modificar agentes requiere especial cuidado.

Antes de cambiar:

- prompts,
- modelos,
- lógica,

registrar:

- versión anterior,
- versión nueva,
- motivo,
- resultado esperado.

---

# 16. Experimentos

Todo experimento debe ser reproducible.

Registrar:

- fecha,
- versión del código,
- modelo utilizado,
- configuración,
- resultado.

---

Ejemplo:

```
Experiment:

Agent v1.3

Model:

Qwen 7B

Markets:

500

Result:

ROI simulated +4%
```

---

# 17. Seguridad

Codex debe priorizar seguridad.

Nunca:

- exponer secretos,
- desactivar validaciones,
- eliminar controles.

---

# 18. Dependencias

Antes de agregar una librería:

Evaluar:

- necesidad real,
- mantenimiento,
- compatibilidad,
- tamaño.

---

Evitar dependencias innecesarias.

---

# 19. Cuando exista incertidumbre

Codex debe preguntar.

Ejemplos:

- cambios arquitectónicos,
- decisiones de negocio,
- eliminación de código,
- cambios de stack.

---

No asumir.

---

# 20. Regla principal

Codex debe optimizar para:

```
Comprensión

>

Velocidad

>

Cantidad de código
```

Un sistema pequeño y entendible es superior a un sistema enorme imposible de mantener.

---

# 21. Objetivo final

Codex debe ayudar a construir AI-Polyphite como un proyecto profesional:

- modular,
- probado,
- documentado,
- reproducible,
- escalable.