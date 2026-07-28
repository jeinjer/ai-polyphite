# AI-Polyphite

# External APIs & Data Sources Architecture

Version: 1.0

Status: Draft

---

# 1. Filosofía

AI-Polyphite debe poder funcionar aunque una fuente externa desaparezca.

Ningún proveedor debe convertirse en una dependencia crítica.

Todas las integraciones externas deben estar abstraídas mediante interfaces.

Arquitectura general:

```
External Source

↓

API Adapter

↓

Data Normalizer

↓

Event System

↓

Agents
```

---

# 2. API Layer

Todas las fuentes externas deben utilizar adaptadores independientes.

Ejemplo:

```
MarketDataProvider implementations

News Adapter

Social Adapter

LLM Adapter

Historical Data Adapter
```

Los agentes nunca deben consumir APIs directamente.

La responsabilidad de los agentes es analizar datos, no obtenerlos.

---

# 3. Prediction Market Provider SDK

## Objetivo

Obtener información de mercados de predicción sin acoplar el sistema a una
fuente concreta.

El contrato común se define mediante `MarketDataProvider`, DTOs externos
normalizados, capacidades y health checks. Manifold, Metaculus, Polymarket,
Replay e Historical serán implementaciones independientes cuando corresponda.

---

## Datos obtenidos

### Market Information

- ID del mercado.
- Título.
- Descripción.
- Categoría.
- Fecha de resolución.
- Estado.

---

### Price Data

- Precio YES.
- Precio NO.
- Volumen.
- Liquidez.
- Spread.

---

### Historical Data

- Cambios de precio.
- Cambios de volumen.
- Actividad temporal.
- Historial de operaciones disponible.

---

# 4. Market Data Pipeline

Flujo:

```
External Provider API

↓

Concrete MarketDataProvider

↓

Normalized Provider DTOs

↓

Collector / Mapper

↓

Database

↓

MarketUpdated Event
```

---

# 5. Actualización de mercados

Frecuencia inicial:

Cada 1-5 minutos.

La frecuencia puede variar según:

- volumen del mercado,
- liquidez,
- fecha de resolución,
- interés del sistema.

---

# 6. News APIs

## Objetivo

Obtener información externa relevante.

---

## Fuentes posibles

- RSS.
- APIs de noticias.
- Blogs oficiales.
- Comunicados empresariales.
- Fuentes gubernamentales.

---

## Datos almacenados

- Título.
- Contenido.
- Fecha.
- Fuente.
- Autor.
- Idioma.
- URL.
- Hash del contenido.

---

# 7. News Pipeline

```
News Source

↓

News Adapter

↓

Duplicate Detector

↓

News Database

↓

NewsCollected Event
```

---

# 8. Detección de duplicados

Muchas noticias pueden representar el mismo evento.

El sistema debe detectar:

- contenido idéntico,
- artículos replicados,
- similitud semántica.

Ejemplo:

```
Reuters publica una noticia.

↓

10 medios la replican.

↓

AI-Polyphite identifica un único evento.
```

---

# 9. Social Data

Módulo opcional.

Fuentes:

- Reddit.
- X/Twitter.
- Comunidades especializadas.

---

Datos:

- publicaciones,
- sentimiento,
- volumen,
- velocidad de crecimiento,
- usuarios relevantes.

---

# 10. Limitaciones de redes sociales

Las redes sociales contienen:

- ruido,
- bots,
- manipulación,
- sesgos,
- información falsa.

Nunca deben utilizarse como única fuente.

---

# 11. LLM APIs

Todos los modelos utilizan una interfaz común.

Ejemplo:

```
LLM Provider

↓

generate()

↓

response
```

---

# Proveedores

## Local

- Ollama.
- Modelos open source.

## Cloud

- OpenAI.
- Claude.
- Gemini.

---

# 12. Model Routing

El sistema debe seleccionar modelos según la tarea.

Ejemplo:

```
Clasificación simple

↓

Modelo local
```

```
Análisis complejo

↓

Modelo avanzado
```

---

# 13. Embedding APIs

Utilizadas para:

- memoria histórica,
- búsqueda semántica,
- RAG.

---

Opciones:

Local:

- Sentence Transformers.
- Modelos compatibles con Ollama.

Cloud:

- APIs comerciales.

---

# 14. Historical Data

Necesaria para:

- Backtesting.
- Replay.
- Evaluación.

---

Guardar:

- mercados resueltos,
- precios históricos,
- noticias históricas,
- resultados finales.

---

# 15. Rate Limits

Toda integración debe manejar:

- límites de requests,
- errores,
- timeouts,
- reintentos.

Ejemplo:

```
Request

↓

Error 429

↓

Esperar

↓

Retry

↓

Registrar resultado
```

---

# 16. Cache System

Los datos frecuentes deben almacenarse temporalmente.

Tecnología:

Redis.

---

Ejemplos:

- mercados recientes,
- respuestas LLM,
- resultados intermedios,
- consultas frecuentes.

---

# 17. Error Handling

Una API caída no debe detener el sistema completo.

Ejemplo:

```
News API caída

↓

Registrar error

↓

Usar fuentes alternativas

↓

Crear alerta
```

---

# 18. Data Quality Agent

Nuevo agente.

## Objetivo

Validar la calidad de los datos antes de utilizarlos.

---

Analiza:

- fuente,
- credibilidad,
- fecha,
- contradicciones,
- información incompleta,
- posible manipulación.

---

Salida:

```
Data Quality Score

0-100
```

---

# 19. API Monitoring

Cada integración debe registrar:

- disponibilidad,
- latencia,
- errores,
- cantidad de datos,
- costos.

---

# 20. Secret Management

Nunca almacenar:

- API Keys.
- Tokens.
- Credenciales.

Dentro del código.

---

Utilizar:

- variables de entorno,
- archivos .env,
- gestores de secretos.

---

# 21. Configuración

Ejemplo:

```env
MARKET_PROVIDER=mock

MARKET_UPDATE_INTERVAL=300

NEWS_UPDATE_INTERVAL=600

MAX_RETRIES=3

LLM_PROVIDER=ollama
```

---

# 22. Principio final

Las APIs son los sensores de AI-Polyphite.

No son la inteligencia.

El sistema debe poder reemplazar cualquier fuente externa sin modificar la arquitectura principal.
