# Backend tests

- `unit`: reglas puras y componentes aislados.
- `integration`: PostgreSQL, Redis y adaptadores.
- `contract`: contratos de proveedores externos y eventos.
- `fixtures`: datos de prueba versionados.

La suite actual cubre la base técnica, las invariantes del Market Domain y su
persistencia real en PostgreSQL. Los tests marcados como `integration` requieren
los servicios declarados en Docker Compose.
