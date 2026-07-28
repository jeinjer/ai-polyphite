# Portfolio virtual y contrato contable

## Unidades

Sólo existen:

- `USD_SIMULATED`
- `MANA_SIMULATED`

No son dinero, depósitos ni activos canjeables. Un portfolio no mezcla unidades.

## Estado materializado

`PaperPortfolio` mantiene:

- capital inicial;
- cash disponible;
- capital reservado;
- P&L realizado y no realizado;
- equity;
- exposición total;
- estado y hash de configuración.

Invariantes:

```text
total_exposure = reserved_balance
equity = cash_balance + reserved_balance + unrealized_pnl
cash_balance >= 0
reserved_balance >= 0
```

Abrir una posición reserva `net_cost`. No existe préstamo ni leverage. El ledger
append-only registra capital inicial, apertura, settlement o devolución por
cancelación. Los saldos materializados optimizan lectura y deben reconciliar con
el ledger.

## Contrato binario

Para lado YES se usa `p`; para NO, `1 - p`.

```text
units = contract_budget / effective_probability
maximum_loss = net_cost
winning_payout = units
losing_payout = 0
```

`Decimal` se usa en dominio, API y persistencia. Los timestamps son UTC.

## Mark-to-market

Una posición abierta puede valorarse con la última probabilidad visible:

```text
mark_value = units × side_probability
unrealized_pnl = mark_value - invested_amount
```

Este valor es informativo. No presupone liquidez, spread ejecutable ni posibilidad
de cierre anticipado.

## Procedencia

Cada decisión referencia el `PredictionRun`, su hash, mercado, experimento,
configuración, correlation ID y causation ID. Trade, posición, settlement,
ledger y snapshots conservan sus propias claves e hashes.
