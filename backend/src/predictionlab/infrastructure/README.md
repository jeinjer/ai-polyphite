# Infrastructure

Implementaciones técnicas de puertos definidos por aplicación y dominio.

- `database`: SQLAlchemy, repositorios y Alembic.
- `events`: outbox, inbox y Redis Streams.
- `cache`: Redis cache.
- `observability`: logs, métricas y trazas.

La base SQLAlchemy incluye modelos y repositorios asíncronos para `Provider`,
`Market` y `MarketSnapshot`. Los repositorios hacen `flush`, pero el commit y
rollback pertenecen al caso de uso que controla la transacción.

El read-side de mercados usa un repositorio específico de consultas para
paginación, filtros y joins optimizados sin contaminar el dominio.
