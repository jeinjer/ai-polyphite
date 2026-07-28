# ADR-0004: Provider SDK neutral y extensible

- **Estado:** Accepted
- **Fecha:** 2026-07-28
- **Alcance:** Integración con proveedores de mercados de predicción

## Contexto

AI-Polyphite investiga mercados de predicción, no un proveedor concreto. Acoplar
la ingesta a Polymarket, Manifold o cualquier API particular trasladaría sus
identificadores, payloads y limitaciones al dominio y a los casos de uso.

El Market Domain, Application Services, Query Layer, API REST y frontend ya
constituyen un núcleo aprobado. Incorporar múltiples fuentes no debe obligar a
modificar esas capas.

## Decisión

Se crea un Provider SDK en `predictionlab.providers` como frontera externa
independiente.

El SDK define:

- La interfaz asíncrona `MarketDataProvider`.
- DTOs externos normalizados e inmutables.
- Capacidades explícitas por proveedor.
- Un resultado de health check normalizado.
- Un registry de factories explícito, sin estado global.
- `MockProvider` como implementación local determinista.

La dirección de dependencias es:

```text
API externa
    ↓
MarketDataProvider concreto
    ↓
DTOs normalizados del Provider SDK
    ↓
collector / mapper futuro
    ↓
Application Services → Domain
```

Domain, Application, REST y Frontend no importan el Provider SDK. El SDK tampoco
importa esas capas ni SQLAlchemy. El futuro collector será responsable de mapear,
coordinar idempotencia, persistencia y eventos.

Los cursores son opacos para el consumidor. Las funcionalidades opcionales se
declaran mediante `ProviderCapabilities`; no se detectan inspeccionando clases
concretas.

## Consecuencias positivas

- Un proveedor puede añadirse sin cambiar el núcleo existente.
- Los payloads externos no contaminan el modelo persistido.
- Los consumidores pueden validar capacidades antes de ejecutar una operación.
- `MockProvider` permite desarrollo reproducible sin red ni credenciales.
- El registry es aislable por test y admite composición distinta por proceso.

## Consecuencias negativas

- Existe duplicación deliberada entre DTOs externos y entidades del dominio.
- Cada proveedor necesita normalización y un mapper de ingesta.
- El contrato común puede evolucionar cuando aparezcan mercados no binarios.
- El health check mide disponibilidad del adaptador, no la calidad de todos sus
  datos.

## Alternativas descartadas

### Adaptador específico de Polymarket como contrato inicial

Descartado porque convertiría decisiones de una API en decisiones de plataforma.

### Usar entidades de dominio como respuesta del proveedor

Descartado porque acoplaría la integración a invariantes, identidad y ciclo de
vida internos.

### Registry global mutable

Descartado porque dificulta tests, composición por entorno y concurrencia segura.

### Ocultar diferencias bajo un mínimo común sin capacidades

Descartado porque impediría expresar historial, detalle o actualización
incremental sin métodos ambiguos o errores tardíos.
