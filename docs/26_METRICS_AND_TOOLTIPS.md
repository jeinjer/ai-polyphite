# 26 — Catálogo de métricas y tooltips

Estado: implementado  
Fecha: 2026-07-28

Los textos canónicos viven en:

```text
frontend/src/i18n/educational.ts
frontend/src/i18n/messages.ts
```

| Concepto | Explicación visible |
|---|---|
| Probabilidad del mercado | Estimación colectiva publicada; no garantiza el resultado |
| Cambio | Diferencia entre las dos probabilidades más recientes |
| Volumen | Actividad acumulada registrada por la fuente |
| Liquidez | Facilidad informada por la fuente; en Manifold no implica ejecución real |
| Antigüedad | Tiempo desde la observación más reciente |
| Datos desactualizados | Superaron el intervalo esperado |
| Resolución | Resultado oficial publicado por la fuente |
| Calidad de datos | Porcentaje de mercados con historia disponible |
| Estado general | Resumen de fuentes y últimas sincronizaciones |
| Equity simulado | Cash más capital reservado y P&L no realizado |
| Exposición | Capital virtual reservado en posiciones abiertas |
| Drawdown | Mayor caída desde un máximo previo del equity simulado |
| ROI simulado | Resultado neto dividido por capital virtual inicial |
| Mark | Valoración orientativa, no un precio de salida ejecutable |
| Estado de evidencia | Tamaño, independencia y concentración de la muestra |

Cada métrica técnica visible enlaza su explicación mediante un tooltip y un
`aria-label` autosuficiente. Edge, Drawdown, Exposure, P&L y ROI aparecen sólo
en contextos simulados. Spread no se muestra porque las observaciones actuales
no son cotizaciones ejecutables.
