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

Cada métrica técnica visible enlaza su explicación mediante un tooltip enfocable
con teclado y un `aria-label` autosuficiente. Los términos de futuros módulos
—Edge, Drawdown, Exposure, P&L, Spread y Brier Score— están traducidos en el
catálogo, pero no se muestran como resultados porque todavía no existen.
