# AI-Polyphite

# Deployment Architecture

Version: 1.0

Status: Draft

---

# 1. Filosofía

AI-Polyphite debe poder ejecutarse en distintos entornos:

- Computadora personal.
- Servidor privado.
- Infraestructura cloud.

La arquitectura debe mantenerse independiente del entorno donde se ejecute.

El objetivo inicial es validar el sistema con el menor costo posible.

---

# 2. Deployment Inicial

La primera versión será ejecutada localmente.

Hardware objetivo:

- Notebook personal.
- GPU RTX 4050.
- 16GB RAM DDR5.
- SSD.

Objetivo:

Ejecutar un experimento continuo de 30 días utilizando paper trading.

---

# 3. Arquitectura Local

```
                 Browser

                    |

             Next.js Frontend

                    |

             FastAPI Backend

                    |

        -------------------------

        Redis          PostgreSQL

        -------------------------

                    |

              Workers

                    |

              AI Agents

                    |

                 Ollama

                    |

             Local Models
```

---

# 4. Docker

Todo el sistema debe ejecutarse mediante Docker Compose.

La infraestructura estará dividida en servicios independientes.

Servicios:

```
frontend

backend

postgres

redis

worker

scheduler

ollama

monitoring
```

---

# 5. Servicios

## Frontend

Responsabilidad:

- Dashboard.
- Visualización de datos.
- Control del sistema.
- Navegación.

Tecnología:

- Next.js.
- TypeScript.
- TailwindCSS.

---

## Backend

Responsabilidad:

- API principal.
- Autenticación.
- Gestión de usuarios.
- Comunicación con agentes.
- Lógica de negocio.

Tecnología:

- FastAPI.
- Python.

---

## PostgreSQL

Responsabilidad:

Almacenamiento permanente.

Guarda:

- Mercados.
- Noticias.
- Predicciones.
- Experimentos.
- Operaciones.
- Métricas.
- Logs.

---

## Redis

Responsabilidad:

- Event Bus.
- Cache.
- Colas de tareas.
- Comunicación entre workers.

---

## Workers

Responsabilidad:

Ejecutar agentes independientes.

Ejemplos:

```
News Agent Worker

Probability Agent Worker

Evaluation Agent Worker
```

Cada worker debe poder reiniciarse sin afectar al resto.

---

## Scheduler

Responsabilidad:

Ejecutar tareas programadas.

Ejemplos:

Cada 5 minutos:

- Actualizar mercados.

Cada 10 minutos:

- Analizar noticias.

Cada hora:

- Evaluar predicciones.

Cada día:

- Generar reportes.

---

## Ollama

Responsabilidad:

Ejecutar modelos de inteligencia artificial localmente.

Ejemplos:

- Qwen.
- Llama.
- Mistral.

---

# 6. Gestión de GPU

La GPU RTX 4050 será utilizada para:

- Modelos locales.
- Embeddings.
- Procesamiento IA.

No será utilizada para:

- Base de datos.
- Backend.
- Frontend.

---

# 7. Uso estimado de recursos

Configuración inicial:

## PostgreSQL

Uso esperado:

1-2GB RAM.

---

## Redis

Uso esperado:

Menos de 1GB RAM.

---

## Backend

Uso esperado:

1GB RAM aproximadamente.

---

## Frontend

Uso esperado:

500MB-1GB RAM.

---

## Modelos IA

Variable según modelo.

Modelos recomendados:

7B-8B parámetros.

---

# 8. Modelos Locales

Hardware disponible:

RTX 4050.

RAM:

16GB.

---

Modelos recomendados:

- Qwen 2.5 7B.
- Llama 3.x 8B.
- Mistral 7B.

---

Evitar inicialmente:

- Modelos mayores a 20B.
- Ejecuciones simultáneas pesadas.

---

# 9. Ejecución 24/7

La notebook puede mantenerse funcionando durante largos períodos.

Recomendaciones:

- Mantener conectada a corriente.
- Desactivar suspensión automática.
- Controlar temperatura.
- Mantener ventilación adecuada.
- Monitorizar consumo.

---

# 10. Logs

Todos los servicios deben generar logs estructurados.

Registrar:

- Errores.
- Ejecuciones.
- Duración.
- Uso de recursos.
- Decisiones tomadas.

---

Los logs deben tener:

- Timestamp.
- Servicio.
- Nivel.
- Mensaje.
- Contexto.

---

# 11. Backup

Realizar backups automáticos.

Contenido:

- Base de datos PostgreSQL.
- Configuraciones.
- Experimentos.
- Resultados históricos.

Frecuencia inicial:

Diaria.

---

# 12. Migración a servidor

Cuando el sistema supere las capacidades locales:

Migración:

```
Notebook

↓

Servidor privado

↓

Cloud
```

---

# 13. Cuándo migrar

No migrar antes de necesitarlo.

Migrar cuando exista:

- Falta de memoria.
- Falta de almacenamiento.
- Necesidad de disponibilidad permanente.
- Mayor volumen de datos.
- Mayor cantidad de agentes.

---

# 14. Monitoring

Sistema de monitoreo:

- Prometheus.
- Grafana.
- OpenTelemetry.

---

Métricas:

Hardware:

- CPU.
- RAM.
- GPU.
- Temperatura.

Sistema:

- Latencia.
- Errores.
- Tiempo de ejecución.

IA:

- Tokens.
- Costos.
- Modelo utilizado.

---

# 15. Ambientes

Separar ambientes:

```
Development

Testing

Production
```

Cada ambiente debe tener:

- Configuración propia.
- Base de datos propia.
- Variables propias.

---

# 16. Variables de entorno

Nunca almacenar secretos dentro del código.

Ejemplo:

```
DATABASE_URL=

REDIS_URL=

LLM_PROVIDER=

API_KEY=
```

---

# 17. Seguridad

Incluso en entorno local:

- Proteger credenciales.
- Actualizar dependencias.
- No exponer servicios innecesarios.
- Mantener backups.

---

# 18. Principio final

AI-Polyphite debe demostrar valor antes de requerir infraestructura costosa.

Primero:

- validar hipótesis,
- medir resultados,
- mejorar modelos.

Después:

- escalar infraestructura.