# Integrations

Adaptadores de proveedores externos.

- Los proveedores de mercados utilizan el SDK neutral de `../providers`.
- `polymarket` es sólo un directorio reservado del scaffold; no está implementado.
- `news`: RSS y otras fuentes de evidencia.
- `llm`: Ollama y futuros proveedores intercambiables.

Los agentes no deben llamar SDKs o APIs externas directamente.
