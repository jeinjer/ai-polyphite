# Features

Cada capacidad del producto tendrá un módulo vertical, por ejemplo:

- `markets`
- `predictions`
- `paper-trading`
- `agents`
- `system`

Una feature puede contener componentes, hooks, schemas y queries propios, pero
no debe acceder directamente a detalles de transporte fuera de `lib/api`.
