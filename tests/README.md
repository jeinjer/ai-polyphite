# System tests

Pruebas y fixtures que cruzan aplicaciones o procesos.

- `e2e`: reservado para orquestación multiservicio futura.
- `fixtures`: datasets mínimos compartidos por pruebas de sistema.

Los specs Playwright actuales viven en `frontend/tests/e2e`, donde Node puede
resolver las dependencias del paquete frontend. Las pruebas unitarias e
integración del backend viven en `backend/tests`.
