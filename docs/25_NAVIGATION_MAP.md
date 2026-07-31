# 25 — Mapa de navegación ejecutivo

Estado: implementado
Fecha: 2026-07-31

```text
Resumen (/)
├── estado del laboratorio
├── resultado y capital simulados
├── evolución de la cartera
└── actividad reciente
Oportunidades (/predictions)
├── listado paginado y filtros simples
├── detalle lazy (/predictions/{prediction_id})
└── simulación manual opcional
Actividad (/trades)
├── todas
├── automáticas
└── manuales
Mercados (/markets)
├── listado y búsqueda
└── detalle (/markets/{market_id})
```

Estas son las únicas cuatro entradas visibles. En escritorio se presentan en
una barra superior; en móvil conservan el mismo orden en una navegación
horizontal compacta. No existe un selector simple/avanzado.

Las rutas históricas (`/agents`, `/portfolio`, `/positions`, `/performance`,
`/experiments`, `/history`, `/sources`, `/system` y `/settings`) se conservan
temporalmente como enlaces compatibles, pero muestran el resumen y no aparecen
en el menú. La capacidad técnica subyacente sigue disponible en la API.

TanStack Query mantiene el refresco de fondo. El listado de oportunidades es
liviano y paginado; la explicación, los agentes y los artefactos relacionados
se solicitan sólo al abrir una oportunidad.
