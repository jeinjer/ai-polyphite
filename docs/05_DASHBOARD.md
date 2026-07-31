# AI-Polyphite

# Dashboard System Design

> Nota de vigencia (2026-07-31): este documento conserva el catálogo original
> de capacidades técnicas. La experiencia visible actual está definida en
> `24_BEGINNER_UX.md`, `25_NAVIGATION_MAP.md` y
> `41_EXECUTIVE_DASHBOARD.md`; esas decisiones prevalecen para navegación y
> presentación.

Version 1.0

---

# Filosofía

El dashboard es una herramienta de investigación.

No está diseñado para mostrar solamente resultados finales.

Debe permitir entender:

- qué pasó
- por qué pasó
- quién tomó la decisión
- con qué información
- con qué confianza
- cuál fue el resultado

---

# Tecnología

Frontend:

Next.js

TypeScript

TailwindCSS

Shadcn UI

React Query

Zustand

Recharts

WebSockets

---

# Arquitectura Frontend

Pages

|

Components

|

Hooks

|

API Layer

|

WebSocket Layer

|

Backend

---

# Navegación principal

Sidebar:

Dashboard

Markets

Predictions

Paper Trading

Agents

Experiments

Replay

Analytics

Logs

Settings

---

# 1. Home Dashboard

Objetivo:

Vista general del estado del sistema.

---

## Cards principales

Capital virtual

Ejemplo:

$103.42

ROI

+3.42%

Win Rate

62%

Operaciones

243

Edge promedio

+12%

---

## Gráficos

### Capital histórico

Línea temporal:

día

semana

mes

---

### Operaciones

Ganadoras

Perdedoras

Abiertas

---

### Rendimiento por estrategia

Comparación:

Strategy A

Strategy B

Strategy C

---

# 2. Markets

Lista completa de mercados.

---

Tabla:

Market

Categoría

Precio YES

Precio NO

Volumen

Liquidez

Fecha resolución

Estado

---

Filtros:

Categoría

Fecha

Liquidez

Edge detectado

---

Detalle de mercado:

Título

Descripción

Histórico precio

Predicciones

Noticias asociadas

Agentes involucrados

---

# 3. Prediction Center

Pantalla de decisiones.

---

Cada predicción muestra:

Mercado:

...

Precio actual:

42%

Predicción sistema:

61%

Edge:

+19%

Confianza:

78%

---

Participantes:

Probability Agent

62%

Statistical Agent

58%

Claude

64%

Qwen

59%

---

Conclusión:

BUY YES

WAIT

BUY NO

---

# 4. Agent Monitor

Centro de control de agentes.

---

Cada agente tiene una tarjeta:

News Agent

Estado:

🟢 Online

Última ejecución:

20:32

Procesadas:

342 noticias

Tiempo:

4.2 segundos

---

Métricas:

Ejecuciones

Errores

Latencia

Costo

Precisión histórica

---

Detalle agente:

Versión

Modelo

Prompt utilizado

Últimos resultados

---

# 5. Paper Trading

La pantalla más importante.

---

## Portfolio

Capital inicial:

100 USD

Capital actual:

104.25 USD

ROI:

4.25%

---

## Posiciones abiertas

Tabla:

Mercado

Entrada

Actual

P/L

---

## Historial

Operación

Resultado

Motivo

Agentes

---

# 6. Experiment Lab

Laboratorio.

---

Crear experimento:

Nombre:

Hipótesis:

Variables:

Resultado esperado:

---

Ejemplo:

Experimento:

Cambiar modelo Llama → Qwen

---

Resultados:

Antes:

ROI 8%

Después:

ROI 12%

---

# 7. Replay Mode

Una de las funciones más importantes.

---

Permite viajar al pasado.

Ejemplo:

Fecha:

10/05/2026

Hora:

14:30

---

El sistema muestra:

Qué mercados existían.

Qué noticias estaban disponibles.

Qué agentes sabían.

Qué predijeron.

Qué habría pasado.

---

# 8. Analytics

Análisis profundo.

---

Métricas:

ROI

Sharpe

Drawdown

Profit Factor

Expectancy

Calibration

Brier Score

---

## Calibración

Gráfico:

Predicción

vs

Resultado real

---

Ejemplo:

Predicciones 70%

Resultado real:

69%

Excelente.

---

# 9. Agent Intelligence

Pantalla para analizar IA.

---

Mostrar:

Modelo usado

Prompt versión

Respuesta

Tiempo

Costo

Resultado posterior

---

Permite responder:

"¿Este modelo realmente aporta valor?"

---

# 10. Logs

Vista técnica.

---

Filtros:

Servicio

Agente

Nivel

Fecha

---

Ejemplo:

20:31:22

Probability Agent

Calculó:

61%

Fuente:

14 noticias

---

# 11. Alertas

Sistema de avisos.

Ejemplos:

"Agente fallando"

"Modelo degradado"

"Estrategia perdió ventaja"

"Mercado anormal"

---

# Tiempo real

Usar WebSockets.

Eventos:

AgentStarted

AgentFinished

PredictionCreated

TradeOpened

TradeClosed

ExperimentCompleted

---

# Diseño visual

Inspiración:

Bloomberg Terminal

Linear

Vercel Dashboard

Notion

---

# Principios UX

Información importante primero.

Pocas animaciones.

Muchos datos.

Todo debe ser navegable.

Toda métrica debe poder abrir detalle.

---

# Principio final

El dashboard no debe decir solamente:

"Ganaste 5 dólares."

Debe responder:

"Ganaste 5 dólares porque estos agentes analizaron estas fuentes, tomaron esta decisión, con esta confianza, usando esta versión del sistema."
