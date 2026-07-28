# Domain layer

Contendrá reglas de negocio puras y tipos del dominio.

Subdominios previstos:

- `markets`
- `evidence`
- `predictions`
- `paper_trading`
- `agents`
- `experiments`

No puede importar FastAPI, SQLAlchemy, Redis ni SDKs de proveedores.

## Markets

`markets` contiene las entidades puras `Provider`, `Market` y
`MarketSnapshot`, sus estados y sus invariantes. Utiliza UUID, timestamps UTC y
`Decimal`; no importa infraestructura.
