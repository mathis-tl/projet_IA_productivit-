#!/bin/sh

set -e

mkdir -p app/routers tests

touch app/__init__.py
touch app/routers/__init__.py

cat > requirements.txt << 'EOF'
fastapi>=0.115
uvicorn[standard]>=0.30
pydantic>=2.7
psycopg[binary]>=3.2
sqlalchemy>=2.0
alembic>=1.13
python-jose[cryptography]>=3.3
passlib[bcrypt]>=1.7
pytest>=8.0
EOF

cat > Dockerfile << 'EOF'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOF

cat > docker-compose.yml << 'EOF'
services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - .:/app
    depends_on:
      - db
    mem_limit: "512m"
    cpus: "0.75"
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: studypilot
      POSTGRES_PASSWORD: studypilot
      POSTGRES_DB: studypilot
      PGDATA: /var/lib/postgresql/data/pgdata
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
    command: >
      -c shared_buffers=64MB
      -c work_mem=4MB
      -c max_connections=20
      -c effective_cache_size=256MB
    mem_limit: "512m"
    cpus: "0.50"
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  pgdata:
EOF

cat > .dockerignore << 'EOF'
.git
.gitignore
.env
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
.venv
venv
env/
build/
dist/
node_modules/
.DS_Store
data/
datasets/
*.pdf
*.ipynb
EOF

cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.env
.venv/
.DS_Store
.pytest_cache/
.idea/
.vscode/
EOF

cat > .env.example << 'EOF'
DATABASE_URL=postgresql+psycopg://studypilot:studypilot@db:5432/studypilot
JWT_SECRET=change-me
JWT_EXPIRE_MIN=15
JWT_REFRESH_EXPIRE_MIN=43200
EOF

cat > Makefile << 'EOF'
.PHONY: up down test fmt lint prune logs

up:
	docker compose up --build

down:
	docker compose down -v

test:
	docker compose run --rm api pytest -q

fmt:
	docker compose run --rm api python -m black app tests || true

lint:
	docker compose run --rm api python -m ruff app tests || true

prune:
	docker image prune -f
	docker volume prune -f
	docker builder prune -f

logs:
	docker compose logs -f api
EOF

cat > app/main.py << 'EOF'
from fastapi import FastAPI
from .routers.health import router as health_router

app = FastAPI(title="StudyPilot API", version="0.1.0")
app.include_router(health_router, prefix="/health")
EOF

cat > app/routers/health.py << 'EOF'
from fastapi import APIRouter

router = APIRouter()

@router.get("/z")
def healthz():
    return {"status": "ok"}
EOF

cat > tests/test_health.py << 'EOF'
from fastapi.testclient import TestClient
from app.main import app

def test_healthz():
    c = TestClient(app)
    r = c.get("/health/z")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
EOF

cat > README.md << 'EOF'
# StudyPilot API — Démarrage (backend-first, minimal-IA)

## Objectif
Démarrage du projet. La logique métier (utilisateurs, auth, documents, embeddings, quiz, etc.) sera ajoutée ensuite **à la main**.

## Prérequis
- Docker Desktop : limitez à ~2 CPU et 2–4 Go de RAM si votre machine est modeste.

## Lancer
1) cp .env.example .env
2) docker compose up --build
3) docker compose run --rm api pytest -q

## Éviter la saturation
- Images légères, logs bornés, limites `mem_limit`/`cpus`.
- `make down` pour arrêter et libérer les volumes du projet.
- `make prune` pour nettoyer les images/volumes **inutilisés** (dangling).

## Prochaines étapes (métier)
- Modèle User + Auth (JWT)
- Ingestion PDF + extraction texte
- Chunking + pgvector
- Génération résumés/quiz
EOF

chmod +x bootstrap.sh

echo "Scaffold créé. Exécutez: cp .env.example .env && docker compose up --build"
