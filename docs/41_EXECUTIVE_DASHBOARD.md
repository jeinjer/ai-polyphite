# 41 — Rediseño del dashboard ejecutivo

Estado: implementado
Fecha: 2026-07-31

## Decisión de producto

El dashboard deja de exponer la topología interna del laboratorio como
navegación principal. La experiencia visible se organiza alrededor de estado,
oportunidades, acciones y mercados. Es una simplificación de presentación, no
una eliminación de observabilidad ni de capacidades del backend.

## Recorridos

### Ver si funciona

El resumen combina salud de fuentes, último ciclo completado y cartera
autónoma. Expresa el resultado en lenguaje directo y conserva la insignia
`100% simulado` en la cabecera.

### Entender una oportunidad

El listado muestra nombre, probabilidad del mercado, probabilidad estimada,
confianza y conclusión. La explicación detallada se carga bajo demanda. Los
agentes, hashes y metadatos continúan almacenados para reconstrucción, pero se
traducen a motivos breves para la pantalla.

### Ver qué hizo el sistema

Actividad reúne operaciones paper y permite distinguir automáticas de
overrides manuales. Excluye ejecuciones históricas de replay para no mezclar
experimentos con la campaña observada en vivo.

### Explorar mercados

Mercados ofrece búsqueda, probabilidad actual y una serie histórica simple.
El detalle evita términos de infraestructura.

## Compatibilidad

- No cambia dominio, agentes, collector, paper trading ni contratos REST.
- La automatización continúa activa y prevalece por defecto.
- El override manual continúa aislado en su portfolio y requiere confirmación.
- La fuente durable de auditoría continúa siendo PostgreSQL.
- Se preservan es-ES y en-US.

## Verificación

Playwright cubre los cuatro recorridos, detalle lazy, acción manual, filtros,
idioma, loading y error. La prueba `live-stack` valida el dashboard desplegado
contra la API real mediante CORS.
