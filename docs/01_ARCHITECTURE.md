# AI-Polyphite

# Architecture

Version 1.0

---

# Filosofía

AI-Polyphite NO será un bot.

AI-Polyphite será un sistema operativo para investigación cuantitativa.

Cada componente debe poder existir independientemente.

Cada componente debe poder ser reemplazado.

Todo debe ser desacoplado.

Toda comunicación será mediante eventos.

---

# Arquitectura General

                    Next.js Dashboard

                           │

                    REST + WebSockets

                           │

                    FastAPI Backend

                           │

                  Event Bus (Redis)

                           │

──────────────────────────────────────────────────────

                Scheduler / Task Manager

                           │

──────────────────────────────────────────────────────

News Agent

Market Agent

Research Agent

Probability Agent

Memory Agent

Evaluation Agent

Experiment Agent

Paper Trading Agent

Optimization Agent

Report Agent

──────────────────────────────────────────────────────

                           │

                     PostgreSQL

                           │

                      Object Storage

                           │

                          Logs

                           │

                     Monitoring

---

# Tecnologías

Frontend

Next.js

TypeScript

TailwindCSS

React Query

Zustand

Recharts

TanStack Table

Shadcn UI

Backend

Python

FastAPI

SQLAlchemy

Pydantic

Alembic

Celery (o Dramatiq/RQ)

Redis

PostgreSQL

Docker

Docker Compose

Observabilidad

Prometheus

Grafana

OpenTelemetry

Logging estructurado

---

# Comunicación

NO habrá llamadas directas entre agentes.

Todo ocurre mediante eventos.

Ejemplo:

NewNewsArrived

↓

News Agent

↓

NewsProcessed

↓

Probability Agent

↓

ProbabilityCalculated

↓

PaperTradingAgent

↓

TradeExecuted

↓

DashboardUpdated

---

# ¿Por qué eventos?

Porque permite:

desacoplamiento

escalabilidad

reintentos

logs

reproducción

pruebas

---

# Scheduler

Un Scheduler coordina tareas periódicas.

Ejemplos

Cada minuto

Actualizar mercados.

Cada cinco minutos

Buscar noticias.

Cada diez minutos

Actualizar embeddings si los hubiera.

Cada hora

Evaluar experimentos.

Cada noche

Calcular métricas agregadas.

---

# Capas

Presentación

Dashboard

↓

API

↓

Servicios

↓

Agentes

↓

Persistencia

↓

Infraestructura

Nunca saltar capas.

---

# Event Bus

Redis será el Event Bus del MVP.

Eventos:

MarketUpdated

NewsCollected

ProbabilityReady

TradeOpened

TradeClosed

ExperimentFinished

ModelEvaluated

DashboardRefresh

---

# Interfaces

Todos los agentes implementan una interfaz común.

run()

validate()

emit()

health()

metrics()

shutdown()

No importa si el agente usa IA o no.

Todos exponen el mismo contrato.

---

# Base de datos

No guardar solamente resultados.

Guardar absolutamente todo.

Noticias.

Prompts.

Respuestas.

Versiones.

Logs.

Costos.

Tokens.

Experimentos.

Configuraciones.

Errores.

---

# Versionado

Cada estrategia tiene versión.

Cada prompt tiene versión.

Cada modelo tiene versión.

Cada agente tiene versión.

Cada experimento tiene versión.

Nunca sobrescribir.

---

# Configuración

Toda configuración fuera del código.

.env

config.yaml

Nunca hardcodear.

---

# IA

Los agentes nunca conocen qué modelo utilizan.

Existe una capa:

LLM Provider

↓

Ollama

Claude

OpenAI

Gemini

etc.

El agente solo solicita:

Generate()

No sabe quién responde.

---

# Cache

Redis también funciona como cache.

Noticias repetidas.

Consultas frecuentes.

Embeddings.

Resultados intermedios.

---

# Paper Trading

El módulo de trading nunca consulta IA.

Recibe únicamente:

probabilidad

edge

confianza

riesgo

reglas

y decide si abrir o no una operación.

---

# Seguridad

API Keys

Variables de entorno

Nunca subir secretos.

Nunca registrar claves en logs.

---

# Logs

Cada decisión genera un log.

Ejemplo:

20:31

News Agent

Lee Reuters

↓

Genera resumen

↓

Probability Agent

61%

↓

Trading Agent

No compra

↓

Confianza insuficiente

Todo queda registrado.

---

# Observabilidad

Cada agente expone:

latencia

errores

CPU

RAM

VRAM (si usa modelo local)

tokens

costos

tiempo promedio

---

# Dashboard

Todo en tiempo real.

WebSockets.

No polling constante.

---

# Testing

Cada agente posee:

Unit Tests

Integration Tests

Smoke Tests

---

# Docker

Servicios:

frontend

backend

postgres

redis

worker

scheduler

ollama (opcional)

Todo inicia con un solo comando.

docker compose up

---

# Escalabilidad

El sistema debe soportar:

1 agente

10 agentes

100 agentes

sin cambiar arquitectura.

---

# Principio Final

AI-Polyphite debe comportarse como una plataforma científica.

Cada hipótesis debe poder probarse.

Cada resultado debe poder reproducirse.

Cada mejora debe medirse.

Nada se acepta por intuición.

Toda decisión debe estar respaldada por evidencia.