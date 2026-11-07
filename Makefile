PYTHON ?= python
.PHONY: demo test all verify
demo:
	$(PYTHON) -m swarm.experiments.run_all --demo
test:
	$(PYTHON) -m pytest -q
all:
	$(PYTHON) -m swarm.experiments.run_all
verify:
	$(PYTHON) -m swarm.experiments.verify
