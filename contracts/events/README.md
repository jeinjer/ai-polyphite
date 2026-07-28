# Event contracts

Los eventos seguirán el envelope definido en `docs/adr/0002-durable-event-system.md`.

Las versiones se organizarán como:

```text
events/
└── v1/
    ├── event-envelope.schema.json
    └── examples/
```

El schema se implementará junto con outbox/inbox para evitar mantener un
contrato especulativo sin consumidores.
