# AI-Polyphite

Version: 1.0

Status:
Draft

Author:
OpenAI + Stefano Tommasi

---

# Vision

AI-Polyphite es una plataforma de investigación cuantitativa basada en Inteligencia Artificial para mercados de predicción.

El objetivo NO es construir un bot de apuestas.

El objetivo es construir un laboratorio capaz de:

- observar mercados
- recopilar información
- analizar miles de fuentes
- estimar probabilidades
- generar hipótesis
- ejecutar paper trading
- medir resultados
- aprender de los experimentos
- permitir mejorar estrategias con evidencia

AI-Polyphite nunca tomará decisiones financieras automáticamente durante las primeras etapas.

Todo será simulado.

---

# Filosofía

Toda decisión debe poder responder estas preguntas.

¿Por qué ocurrió?

¿Qué información utilizó?

¿Qué agentes participaron?

¿Qué confianza tenía?

¿Cuánto hubiera ganado?

¿Cuánto hubiera perdido?

¿Qué versión del sistema tomó la decisión?

Todo debe ser reproducible.

Nada debe ser una caja negra.

---

# Objetivos

Construir una plataforma modular.

Construir una plataforma completamente auditable.

Permitir experimentar con nuevas estrategias.

Permitir reemplazar cualquier agente sin modificar el resto.

Permitir comparar modelos de IA.

Permitir comparar estrategias.

Permitir reproducir cualquier decisión histórica.

---

# Objetivos NO funcionales

Escalable.

Modular.

Observable.

Versionable.

Reproducible.

Containerizada.

Orientada a eventos.

---

# MVP

El MVP deberá ser capaz de:

✔ Leer mercados de Polymarket

✔ Guardarlos

✔ Obtener noticias

✔ Analizar noticias

✔ Estimar probabilidades

✔ Compararlas con el mercado

✔ Ejecutar paper trading

✔ Mostrar resultados

✔ Mostrar métricas

✔ Registrar absolutamente todo

---

# Principios

Nunca borrar información.

Nunca modificar datos históricos.

Nunca sobrescribir experimentos.

Todo cambio genera una nueva versión.

Todo agente es independiente.

Todo agente debe poder apagarse.

Todo agente debe poder reemplazarse.

---

# Regla más importante

NO utilizar dinero real.

AI-Polyphite solamente realizará paper trading hasta demostrar evidencia estadística suficiente.

---

# Arquitectura

AI-Polyphite será construido como una plataforma distribuida basada en módulos.

No existirá un "agente principal".

Existirá un conjunto de agentes especializados.

Cada agente resolverá un problema específico.

---

# Los agentes

News Agent

Market Agent

Research Agent

Probability Agent

Evaluation Agent

Experiment Agent

Paper Trading Agent

Optimization Agent

Report Agent

Memory Agent

Cada agente tendrá:

objetivo

entradas

salidas

métricas

versionado

logs

tests

---

# IA

La IA no toma decisiones.

La IA propone hipótesis.

El sistema valida esas hipótesis.

La evidencia decide.

No el LLM.

---

# Experimentación

AI-Polyphite fue diseñado como un laboratorio.

No existe una estrategia perfecta.

Existen miles de hipótesis.

El objetivo del laboratorio es descubrir cuáles funcionan.

---

# Métrica de éxito

NO ganar dinero.

La métrica principal es descubrir estrategias con ventaja estadística.

Si la plataforma demuestra que una estrategia NO funciona, también es un éxito.

Porque evita perder dinero real.

---

# Paper Trading

Todo comienza con capital virtual.

Capital inicial configurable.

Ejemplo:

100 USD

Cada operación tendrá:

fecha

mercado

entrada

salida

resultado

ROI

explicación

confianza

modelo utilizado

agentes participantes

tiempo de ejecución

---

# Dashboard

AI-Polyphite tendrá un dashboard profesional.

No será únicamente una interfaz bonita.

Será una herramienta de investigación.

Permitirá navegar cada decisión tomada por el sistema.

---

# Principio de ingeniería

Toda decisión del sistema debe poder reconstruirse meses después.

Nada puede depender de memoria temporal.

Todo queda almacenado.

---

# Visión futura

Si algún día AI-Polyphite demuestra una ventaja consistente durante un largo período de paper trading, podrá incorporarse un módulo opcional de ejecución real.

Ese módulo NO forma parte del MVP.

No será implementado hasta que exista evidencia suficiente.