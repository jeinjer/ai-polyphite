# 25 — Mapa de navegación

Estado: implementado  
Fecha: 2026-07-28

```text
Inicio
├── KPIs
├── cambios principales
└── avisos
Mercados
├── listado
└── detalle
    ├── probabilidad
    ├── serie histórica
    └── timeline (vista avanzada)
Historial
├── cambios de mercados
├── observaciones
└── sincronizaciones
Experimentos (vista avanzada)
├── datasets disponibles
└── ejecuciones reproducibles
Cartera simulada
├── capital, cash y exposición
└── estado de evidencia y trazabilidad
Operaciones
└── entrada, riesgo, costes, resultado y predicción
Posiciones
└── abiertas, liquidadas y mark informativo
Rendimiento
├── equity curve y drawdown
├── métricas y alertas
└── baselines y desgloses
Fuentes de datos
Estado del sistema
Configuración
├── vista simple/avanzada
└── es-ES/en-US
```

En móvil la navegación usa un panel desplegable; en escritorio permanece
visible. Seleccionar un cambio principal abre el mercado correspondiente.
En vista simple no aparece la navegación de Experimentos; las cuatro vistas de
paper trading sí están disponibles con detalle reducido y disclaimer fijo. La
vista avanzada agrega hashes, IDs, checks, configuración y trazabilidad.

## Rutas

| Sección | Ruta |
| --- | --- |
| Inicio | `/` |
| Mercados | `/markets` |
| Detalle de mercado | `/markets/{market_id}` |
| Historial | `/history` |
| Predicciones | `/predictions` |
| Agentes | `/agents` |
| Cartera | `/portfolio` |
| Operaciones | `/trades` |
| Posiciones | `/positions` |
| Rendimiento | `/performance` |
| Experimentos | `/experiments` |
| Fuentes | `/sources` |
| Sistema | `/system` |
| Configuración | `/settings` |

Las rutas son enlazables, soportan navegación atrás/adelante y carga directa.
TanStack Query refresca los datos cada 60 segundos, incluso con la pestaña en
segundo plano.
