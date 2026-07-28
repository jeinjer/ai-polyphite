# Alembic migrations

Esta carpeta contiene únicamente migraciones versionadas de PostgreSQL.

Reglas:

- No editar una migración ya aplicada en un ambiente compartido.
- Las migraciones de esquema y backfills grandes deben separarse.
- Toda migración debe ser revisable y tener una estrategia de rollback o una
  explicación explícita de por qué no es reversible.
- `20260727_0001` crea `providers`, `markets` y `market_snapshots`.

Validación de que los modelos y la última migración coinciden:

```powershell
python -m alembic -c backend/alembic.ini check
```
