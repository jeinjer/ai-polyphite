# 29 — Crear datasets de replay

## Regla principal

Un dataset debe contener únicamente hechos que una fuente podría haber
publicado en cada instante. No se deben completar precios, volumen, liquidez o
resultados ausentes.

## Procedimiento

1. Asignar `dataset_id`, versión semántica y `schema_version`.
2. Crear mercados binarios con `provider_market_id` estable.
3. Añadir observaciones en UTC y en orden temporal.
4. Añadir cierres y resoluciones oficiales en su instante real.
5. Ordenar eventos por timestamp, tipo e ID estable.
6. Serializar JSON compacto y determinista.
7. Calcular el SHA-256 del contenido posterior a metadata.
8. Completar rango y contadores.
9. Validar cargándolo con `load_replay_dataset`.
10. Versionar el archivo; nunca editar una versión ya utilizada.

## Dataset sintético incluido

`backend/datasets/replay/synthetic-lab-v1.jsonl` contiene:

- 20 mercados ficticios;
- cinco categorías;
- 80 observaciones;
- cambios durante varios días;
- resultados YES, NO y CANCELLED;
- cero datos reales o personales.

Se regenera de forma determinista con:

```powershell
.\.venv\Scripts\python.exe .\scripts\generate_replay_dataset.py
```

El generador es una herramienta de fixtures. Para datasets provenientes de una
fuente real se debe conservar además su licencia, términos y procedencia.
