# ProductivityAI - Backend

Application de gestion de productivité avec intégration IA (Ollama).

**Status**: 72/72 tests passing ✅ | Version 0.3.0

## Tech Stack

- FastAPI 0.115+
- PostgreSQL 16 (Docker)
- SQLAlchemy 2.0+
- JWT + bcrypt
- Pytest 8.0+
- Ollama (mistral:7b)

## Quick Start

### Setup

```bash
pip install -r requirements.txt
docker compose up -d
ollama serve &
python -m pytest tests/ -q
```

Expected: `72 passed`

## Test It

### Auth
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"pass123"}'
```

### Get Token
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123"}' | jq -r '.access_token'
```

### Create Page
```bash
TOKEN=<your_token>

curl -X POST http://localhost:8000/pages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"My page","icon":"📚"}'
```

### Summarize with Ollama
```bash
TOKEN=<your_token>

curl -X POST http://localhost:8000/ai-analyze/summarize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Your text here..."}'
```

### Extract Actions
```bash
TOKEN=<your_token>

curl -X POST http://localhost:8000/ai-analyze/extract-actions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Tomorrow call John, then finish the report..."}'
```

## Architecture

```
app/
├── core/      Config, DB, Security
├── models/    6 tables (User, Page, Block, Task, Link, AITrace)
├── schemas/   Pydantic validation
├── routers/   8 endpoints
└── services/  Business logic

tests/
└── 72 unit tests (SQLite)
```

## Endpoints

**Auth**: POST /auth/signup, /auth/login, /auth/refresh

**Pages**: GET/POST/PUT/DELETE /pages

**Blocks**: GET/POST/PUT/DELETE /blocks

**Tasks**: GET/POST/PUT/DELETE /tasks, GET /tasks/today, /tasks/overdue, /tasks/this-week

**Links**: POST/GET/DELETE /links

**AI**: POST /ai-analyze/summarize, /ai-analyze/extract-actions

## Database

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

## Testing

Unit tests use **SQLite** (fast, isolated):
```bash
pytest tests/ -q          # Quick
pytest tests/ -v          # Verbose
pytest tests/ --cov=app   # With coverage
```

## Project Status

| Feature | Status |
|---------|--------|
| Auth + CRUD | ✅ Done |
| Relations + Linking | ✅ Done |
| Ollama Integration | ✅ Done |
| Unit Tests (72/72) | ✅ Done |
| spacy NLP | ⏳ Next |
| Gamification | ⏳ TODO |
| Templates | ⏳ TODO |
| Notifications | ⏳ TODO |

## Notes

- Tests run on SQLite in ~2 seconds
- All traces stored in `ai_traces` table
- Docker container accesses Ollama via `host.docker.internal:11434`
- Soft deletes (is_archived flag)

---

Last Updated: 3 novembre 2025
