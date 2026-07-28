# 23 — Internacionalización del frontend

Estado: implementado  
Fecha: 2026-07-28

La interfaz usa un catálogo tipado central:

```text
frontend/src/i18n/messages.ts
```

Idiomas:

- `es-ES`: default y lenguaje inicial del documento;
- `en-US`: selección opcional.

Los componentes sólo referencian `MessageKey`; TypeScript falla si una clave no
existe en el catálogo español. El catálogo inglés implementa el mismo contrato.
Las variables se interpolan con `{name}`.

La preferencia se guarda en `localStorage` bajo
`ai-polyphite-locale`, se sincroniza entre pestañas y actualiza el atributo
`lang` del documento. Fechas y números visibles usan el locale activo cuando
corresponde.

## Convenciones

- No escribir texto visible directamente en componentes.
- Añadir primero la clave española y luego su traducción inglesa.
- No traducir contenido externo como títulos de mercados.
- Mostrar conceptos internos con lenguaje de producto: “Fuente de datos”,
  “Sincronización”, “Observación” y “Estado del sistema”.
- Centralizar explicaciones educativas en `educational.ts`.
