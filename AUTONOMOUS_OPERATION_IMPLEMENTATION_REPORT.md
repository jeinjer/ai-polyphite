# Operación autónoma — Resumen de implementación

Fecha: 2026-07-29  
Estado: implementado, exclusivamente read-only y paper trading

## Flujo

```text
API pública oficial de Manifold
  → catálogo binario reciente (máximo 1.000)
  → MarketDataCollector
  → PostgreSQL
  → predicción sólo si cambió la observación
  → decisión y operación simuladas
  → settlement y reconciliación
  → dashboard con refresco automático
```

No existen credenciales de trading, wallets, órdenes reales ni movimiento de
dinero. Las probabilidades de Manifold son observaciones informativas.

## Operación sin intervención

- collector Manifold cada hora;
- validador paper cada hora;
- reinicio automático de contenedores mediante `unless-stopped`;
- dashboard actualizado cada 60 segundos;
- backup PostgreSQL diario verificado, con 7 días de retención;
- logs Docker rotados, con un máximo de 50 MB por servicio;
- versión de campaña congelada como `autonomous-v1`;
- errores y ciclos trazables mediante correlation IDs, logs y tablas de
  auditoría existentes.

## Navegación

Cada sección tiene una URL estable. El detalle de un mercado queda enlazado como
`/markets/{market_id}` y funciona con navegación directa, atrás y adelante.

## Control de volumen

El adaptador usa una única página `last-updated` de la API oficial y reutiliza
el mismo payload para persistir observaciones. No consulta nuevamente el detalle
de cada mercado ni anuncia snapshots ejecutables inexistentes. El pipeline no
crea otra predicción si la observación no cambió.

## Verificación de arranque

El 2026-07-29 se validó el stack reconstruido contra la API pública:

- 1.000 mercados y 1.000 observaciones Manifold persistidos en 19,3 segundos;
- 936 mercados abiertos procesados por los cuatro agentes;
- 936 decisiones paper, con abstención segura cuando no había evidencia
  suficiente para abrir una posición;
- reconciliación contable completada sin discrepancias;
- backup inicial creado y validado;
- Playwright confirmó dashboard, rutas, API real y CORS.
