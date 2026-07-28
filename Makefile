.PHONY: collect-once collector-worker paper-validate-once paper-validation-worker replay replay-predict replay-trade replay-step replay-reset

PROVIDER ?= mock
DATASET ?= synthetic-lab-v1
MODE ?= accelerated
UNTIL ?=
PREDICTION_INTERVAL_HOURS ?= 24

collect-once:
	.venv/Scripts/python.exe -m predictionlab.runtime.collector_cli once --provider $(PROVIDER)

collector-worker:
	.venv/Scripts/python.exe -m predictionlab.runtime.collector_cli worker

paper-validate-once:
	.venv/Scripts/python.exe -m predictionlab.runtime.paper_validation_cli once

paper-validation-worker:
	.venv/Scripts/python.exe -m predictionlab.runtime.paper_validation_cli worker

replay:
	.venv/Scripts/python.exe -m predictionlab.runtime.replay_cli run --dataset $(DATASET) --mode $(MODE) $(if $(UNTIL),--until $(UNTIL),)

replay-predict:
	.venv/Scripts/python.exe -m predictionlab.runtime.replay_cli predict --dataset $(DATASET) --mode $(MODE) --interval-hours $(PREDICTION_INTERVAL_HOURS) $(if $(UNTIL),--until $(UNTIL),)

replay-trade:
	.venv/Scripts/python.exe -m predictionlab.runtime.replay_cli trade --dataset $(DATASET) --mode $(MODE) --interval-hours $(PREDICTION_INTERVAL_HOURS) $(if $(UNTIL),--until $(UNTIL),)

replay-step:
	.venv/Scripts/python.exe -m predictionlab.runtime.replay_cli run --dataset $(DATASET) --mode step

replay-reset:
	.venv/Scripts/python.exe -m predictionlab.runtime.replay_cli reset --dataset $(DATASET)
