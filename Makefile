.PHONY: up down test fmt lint prune logs

DOCKER := /Applications/Docker.app/Contents/Resources/bin/docker

up:
	$(DOCKER) compose up --build

down:
	$(DOCKER) compose down -v

test:
	$(DOCKER) compose run --rm api pytest -q

fmt:
	$(DOCKER) compose run --rm api python -m black app tests || true

lint:
	$(DOCKER) compose run --rm api python -m ruff app tests || true

prune:
	$(DOCKER) image prune -f
	$(DOCKER) volume prune -f
	$(DOCKER) builder prune -f

logs:
	$(DOCKER) compose logs -f api
