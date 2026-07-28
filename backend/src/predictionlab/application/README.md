# Application layer

Coordina comandos, queries y transacciones. Esta capa depende del dominio y de
puertos abstractos, no de implementaciones concretas de FastAPI, SQLAlchemy,
Redis ni proveedores externos.

El módulo `markets` contiene:

- comandos tipados de creación, actualización y observación;
- servicios de aplicación para providers, markets y snapshots;
- puertos de repositorios y Unit of Work;
- persistencia idempotente sin dependencia de SQLAlchemy;
- Query Layer con read models y casos de uso de listado y detalle.
