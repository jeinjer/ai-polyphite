# ADR-0001: Monolito modular multiproceso

- **Estado:** Accepted
- **Fecha:** 2026-07-27
- **Alcance:** Backend y topología de ejecución

## Contexto

AI-Polyphite necesita API, ejecución asíncrona, scheduler, agentes,
persistencia, integraciones y observabilidad. También debe ejecutarse inicialmente
en una notebook con recursos limitados.

Crear un microservicio o contenedor por agente aumentaría:

- Consumo de memoria.
- Superficie operativa.
- Complejidad de despliegue.
- Contratos distribuidos.
- Dificultad de debugging y testing.

La independencia requerida para los agentes es independencia de
responsabilidades, contratos y versionado; no implica despliegue independiente
desde el primer día.

## Decisión

AI-Polyphite se implementará como un **monolito modular** dentro de un único
paquete Python.

El mismo artefacto de backend podrá ejecutarse mediante tres tipos de proceso:

1. **API:** REST, WebSocket, health y queries.
2. **Worker:** comandos, eventos y agentes.
3. **Scheduler:** publicación de comandos periódicos.

Los procesos compartirán:

- Dominio.
- Casos de uso.
- Contratos.
- Adaptadores.
- Esquema PostgreSQL.

No compartirán memoria de proceso ni dependerán de llamadas directas entre
agentes.

## Límites de capas

```text
api
 ↓
application
 ↓
domain
 ↑
infrastructure / integrations
```

### Domain

- Contiene reglas y tipos de negocio.
- No depende de FastAPI, SQLAlchemy, Redis ni SDKs externos.
- No realiza I/O.

### Application

- Coordina comandos, queries, transacciones y puertos.
- Depende del dominio.
- No conoce detalles HTTP ni SDKs de proveedores.

### API

- Traduce HTTP y WebSocket a comandos y queries.
- No contiene reglas de negocio.
- No accede directamente a SQLAlchemy.

### Infrastructure

- Implementa persistencia, eventos, cache y observabilidad.
- Puede depender de interfaces definidas en application/domain.

### Integrations

- Implementa adaptadores de mercados, noticias y LLM.
- Los agentes no consumen APIs externas directamente.

### Runtime

- Proporciona entrypoints para workers y scheduler.
- Gestiona lifecycle técnico, no reglas del dominio.

## Reglas para agentes

- Un agente es un componente lógico especializado.
- Un agente recibe entradas tipadas y produce salidas tipadas.
- El runtime gestiona logs, métricas, errores y publicación de eventos.
- Un agente no llama directamente a otro agente.
- Un agente no se convierte en servicio o contenedor independiente sin un ADR.

## Despliegue inicial

Docker Compose ejecutará:

- Frontend.
- Backend API.
- PostgreSQL.
- Redis.

Worker y scheduler se añadirán como procesos del mismo artefacto cuando exista
el runtime de eventos. No se crearán procesos placeholder.

Ollama podrá ejecutarse en el host y se accederá mediante una URL configurable.

## Consecuencias positivas

- Desarrollo y debugging más simples.
- Menor consumo de recursos.
- Transacciones locales más claras.
- Refactors entre módulos controlables.
- Testing sin infraestructura distribuida innecesaria.
- Posibilidad de extraer módulos posteriormente.

## Consecuencias negativas

- Un error grave del artefacto compartido puede afectar varios procesos.
- Los límites dependen de disciplina y tests de arquitectura.
- Los despliegues de módulos no son independientes inicialmente.
- Escalar un módulo exige escalar el proceso que lo contiene.

## Criterios para reconsiderar

La extracción de un módulo podrá evaluarse si existe evidencia de:

- Necesidad de escalado independiente sostenida.
- Aislamiento de fallos imposible dentro del proceso actual.
- Requisitos de seguridad distintos.
- Ritmos de despliegue incompatibles.
- Cuellos de botella medidos, no hipotéticos.

Toda extracción requiere un nuevo ADR.

## Alternativas descartadas

### Microservicio por agente

Descartado por complejidad operativa y consumo local sin evidencia de necesidad.

### Aplicación completamente síncrona

Descartada porque la ingesta, los modelos locales y las evaluaciones necesitan
ejecución asíncrona y reintentos.

### Repositorios independientes desde el inicio

Descartados porque dificultarían cambios coordinados de contratos durante el MVP.
