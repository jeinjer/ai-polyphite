# AI-Polyphite Frontend

Dashboard técnico construido con Next.js.

## Responsabilidades

- Consultar estado mediante REST.
- Recibir actualizaciones mediante WebSocket.
- Mostrar mercados, predicciones, operaciones, agentes y métricas.
- Permitir reconstruir la trazabilidad de una decisión.

## Organización

- `src/app`: rutas, layouts y providers globales.
- `src/features`: módulos de producto por capacidad.
- `src/components`: componentes compartidos y shadcn/ui.
- `src/lib`: cliente API y utilidades.
- `src/stores`: estado cliente que no pertenece al servidor.
- `public`: assets estáticos.

TanStack Query será la fuente de verdad para estado remoto. Zustand se reservará
para estado local de interfaz.

## Estado

Solo existe una página técnica para validar el build. No se ha implementado
ninguna vista de negocio.

## Desarrollo

```powershell
npm ci
npm run dev
```

## Calidad

```powershell
npm run lint
npm run typecheck
npm run build
```
