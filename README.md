# ProductivityAI - Backend

Application de gestion de productivité avec intégration IA (Ollama).

**Statut**: Version 0.3.0 | Backend fonctionnel

## Stack Technique

- FastAPI 0.115+
- PostgreSQL 16 (Docker)
- SQLAlchemy 2.0+
- JWT + bcrypt
- Pytest 8.0+
- Ollama (mistral:7b)

## Démarrage Rapide

### Installation

```bash
pip install -r requirements.txt
docker compose up -d
ollama serve &
python -m pytest tests/ -q
```

Résultat attendu: Les tests passent

## Test de l'API

### Authentification
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"pass123"}'
```

### Obtenir un token
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123"}' | jq -r '.access_token'
```

### Créer une page
```bash
TOKEN=<votre_token>

curl -X POST http://localhost:8000/pages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Ma page","icon":"📚"}'
```

### Résumer avec Ollama
```bash
TOKEN=<votre_token>

curl -X POST http://localhost:8000/ai-analyze/summarize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Votre texte ici..."}'
```

### Extraire des actions
```bash
TOKEN=<votre_token>

curl -X POST http://localhost:8000/ai-analyze/extract-actions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Demain appeler Jean, puis finir le rapport..."}'
```

## Architecture

```
app/
├── core/      Config, DB, Sécurité
├── models/    6 tables (User, Page, Block, Task, Link, AITrace)
├── schemas/   Validation Pydantic
├── routers/   8 endpoints
└── services/  Logique métier

tests/
└── Tests unitaires (SQLite)
```

## Endpoints

**Auth**: POST /auth/signup, /auth/login, /auth/refresh

**Pages**: GET/POST/PUT/DELETE /pages

**Blocks**: GET/POST/PUT/DELETE /blocks

**Tasks**: GET/POST/PUT/DELETE /tasks, GET /tasks/today, /tasks/overdue, /tasks/this-week

**Links**: POST/GET/DELETE /links

**IA**: POST /ai-analyze/summarize, /ai-analyze/extract-actions

## Base de données

```
users           pages           blocks          tasks
├─ id           ├─ id           ├─ id           ├─ id
├─ email        ├─ user_id      ├─ page_id      ├─ user_id
├─ username     ├─ title        ├─ content      ├─ title
└─ password     └─ icon         └─ order        └─ due_date

links           ai_traces
├─ id           ├─ id
├─ user_id      ├─ user_id
├─ source_id    ├─ analysis_type
└─ target_id    └─ generated_content
```

## Tests

Les tests unitaires utilisent **SQLite** (rapide, isolé):
```bash
pytest tests/ -q          # Rapide
pytest tests/ -v          # Détaillé
pytest tests/ --cov=app   # Avec couverture
```

## Statut du Projet

| Feature | Statut |
|---------|--------|
| Auth + CRUD | ✅ Fait |
| Relations + Liens | ✅ Fait |
| Intégration Ollama | ✅ Fait |
| Tests unitaires | ✅ Fait |
| NLP spacy | ⏳ Prochainement |
| Gamification | ⏳ À faire |
| Templates | ⏳ À faire |
| Notifications | ⏳ À faire |

## Notes

- Tests exécutés en ~2 secondes sur SQLite
- Toutes les traces stockées dans `ai_traces`
- Le container Docker accède à Ollama via `host.docker.internal:11434`
- Soft delete (flag is_archived)

---

Mis à jour: 3 novembre 2025
