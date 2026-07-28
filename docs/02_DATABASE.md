# AI-Polyphite

Database Design

Version 1.0

---

# Filosofía

La base de datos NO almacena solamente información.

Almacena conocimiento.

Cada decisión tomada por el sistema debe poder reconstruirse.

Nunca se elimina información histórica.

Todo es inmutable.

---

# Motor

PostgreSQL

UUID como Primary Keys

Timestamps UTC

Soft Delete únicamente donde sea necesario.

---

# Tabla Providers

provider_id

code

name

enabled

created_at

updated_at

---

# Tabla Markets

market_id

provider_id

provider_market_id

title

description

category

resolution_at

status

source_created_at (nullable)

ingested_at

updated_at

---

# Tabla MarketSnapshots

snapshot_id

market_id

observed_at

yes_price

no_price

spread

volume

liquidity

probability

Esto permite reconstruir la evolución del mercado.

---

# Tabla News

news_id

title

body

summary

source

url

published_at

language

hash

embedding_id (opcional)

created_at

---

# Tabla Sources

source_id

name

trust_score

bias

country

rss_url

api_url

enabled

---

# Tabla Agents

agent_id

name

version

description

status

model

configuration

created_at

---

# Tabla AgentRuns

run_id

agent_id

started_at

finished_at

duration

cpu

ram

vram

tokens

cost

status

error

logs

---

# Tabla LLMCalls

call_id

provider

model

temperature

prompt_version

input_tokens

output_tokens

latency

cost

created_at

response_hash

No guardar prompts sensibles en texto plano si no hace falta.

---

# Tabla Prompts

prompt_id

name

version

content

created_at

deprecated

---

# Tabla Predictions

prediction_id

market_id

strategy_id

agent_id

probability

confidence

edge

reasoning

created_at

---

# Tabla Strategies

strategy_id

name

version

description

status

parameters

---

# Tabla Trades

trade_id

strategy_id

market_id

entry_price

exit_price

quantity

capital_used

opened_at

closed_at

result

pnl

roi

paper_trade (boolean)

---

# Tabla Experiments

experiment_id

name

description

hypothesis

started_at

finished_at

status

winner

---

# Tabla ExperimentResults

result_id

experiment_id

strategy_id

roi

profit

drawdown

win_rate

profit_factor

sharpe

expectancy

---

# Tabla Metrics

metric_id

strategy_id

date

roi

capital

win_rate

drawdown

profit_factor

expectancy

trades

wins

losses

---

# Tabla MarketEvents

event_id

market_id

type

description

source

timestamp

---

# Tabla Memory

memory_id

category

title

content

embedding_id

confidence

created_at

---

# Tabla Embeddings (opcional)

embedding_id

provider

model

dimension

vector_reference

created_at

---

# Tabla Logs

log_id

service

agent

level

message

payload

timestamp

---

# Tabla Alerts

alert_id

type

title

description

severity

status

created_at

---

# Tabla Configurations

config_id

key

value

version

created_at

---

# Relaciones

Markets

↓

Snapshots

↓

Predictions

↓

Trades

↓

Metrics

Noticias

↓

Research

↓

Predictions

↓

Experiments

↓

Dashboard

---

# Indexes

Markets

resolution_date

category

status

Snapshots

market_id

timestamp

News

published_at

source

hash

Trades

opened_at

closed_at

strategy

Predictions

market

strategy

confidence

---

# Auditoría

Toda modificación genera registro.

Nunca sobrescribir.

Nunca borrar.

Toda estrategia queda registrada.

Todo experimento queda registrado.

---

# Backup

Backup diario.

Snapshots automáticos.

Migraciones mediante Alembic.

---

# Principio Final

La base de datos debe permitir reconstruir completamente cualquier decisión tomada por AI-Polyphite incluso meses después.
