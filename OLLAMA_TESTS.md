# Ollama Integration Tests

Documentation des appels à Ollama 

## Configuration

- **Model**: mistral:7b
- **URL**: http://host.docker.internal:11434 (from Docker container)
- **Timeout**: 180 secondes
- **Base URL local**: http://localhost:11434

## Test 1: Summarize

### Request
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"tuteur@test.com","password":"password123"}' | jq -r '.access_token')

curl -s -X POST http://localhost:8000/ai-analyze/summarize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"ProductivityAI is an amazing application that helps users manage tasks with AI capabilities. It integrates Ollama for content summarization and uses PostgreSQL for data storage."}'
```

### Response
```json
{
  "summary": "ProductivityAI is a task management app equipped with AI features, utilizing Ollama for content summarization and PostgreSQL for data storage.",
  "tokens_used": 91,
  "execution_time_ms": 45310,
  "trace_id": 4
}
```

### Database Trace (AITrace)
```sql
SELECT * FROM ai_traces WHERE id = 4;
```

| id | user_id | analysis_type | model_used | tokens_used | execution_time_ms | success |
|---|---|---|---|---|---|---|
| 4 | 79 | summarize | mistral:7b | 91 | 45310 | true |

### Server Logs
```
[OLLAMA] Calling generate_summary with model=mistral:7b, content_length=183
[OLLAMA] ✓ Summary generated: 117 chars, 91 tokens, 45310ms
[API] User 79 requested summarize: content_length=183
[API] Summarize success: 45310ms, 91 tokens
[API] Trace saved: trace_id=4
```

---

## Test 2: Extract Actions

### Request
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"tuteur@test.com","password":"password123"}' | jq -r '.access_token')

curl -s -X POST http://localhost:8000/ai-analyze/extract-actions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Demain je dois appeler Jean pour discuter du projet, puis finaliser le rapport, et envoyer un email à Sophie."}'
```

### Response
```json
{
  "actions": [
    "1. Appeler Jean",
    "2. Discuter du projet avec Jean",
    "3. Finaliser le rapport",
    "4. Envoyer un email à Sophie"
  ],
  "tokens_used": 84,
  "execution_time_ms": 26239,
  "trace_id": 5
}
```

### Database Trace (AITrace)
```sql
SELECT * FROM ai_traces WHERE id = 5;
```

| id | user_id | analysis_type | model_used | tokens_used | execution_time_ms | success |
|---|---|---|---|---|---|---|
| 5 | 79 | extract_actions | mistral:7b | 84 | 26239 | true |

### Server Logs
```
[OLLAMA] Calling extract_actions with model=mistral:7b, content_length=123
[OLLAMA] ✓ Actions extracted: 4 actions, 84 tokens, 26239ms
[API] User 79 requested extract_actions: content_length=123
[API] Extract-actions success: 26239ms, 84 tokens, 4 actions
[API] Trace saved: trace_id=5
```

---

## Performance Notes

| Operation | Time | Tokens | Notes |
|---|---|---|---|
| Summarize | 45.3s | 91 | First call, model cold start |
| Extract Actions | 26.2s | 84 | Subsequent call, model warm |

**Observations:**
- First call is slower (model needs to load completely)
- Subsequent calls are faster (model in memory)
- Mistral:7b is quantized Q4_K_M (4GB model)

---

## Error Handling

### Test: Ollama Not Running
```json
{
  "detail": "Ollama is not running. Start it with: ollama run mistral:7b"
}
```

### Solution
The fix was to change from `localhost:11434` to `host.docker.internal:11434` because:
- FastAPI runs inside Docker container
- `localhost` from inside container ≠ `localhost` from macOS
- `host.docker.internal` is special hostname on macOS/Windows that routes to host machine
- Linux users would use `172.17.0.1`

---

## Docker Network Setup

### docker-compose.yml
```yaml
services:
  api:
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### app/services/ai_service.py
```python
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
REQUEST_TIMEOUT = 180  # 3 minutes for slow model
```

---

## Trace Storage in Database

All Ollama calls are logged in the `ai_traces` table:

```sql
SELECT id, user_id, analysis_type, tokens_used, execution_time_ms, success, created_at 
FROM ai_traces 
ORDER BY created_at DESC;
```

Fields captured:
- `user_id`: Which user made the request
- `analysis_type`: "summarize" or "extract_actions"
- `generated_content`: The actual output from Ollama
- `tokens_used`: Total tokens processed
- `execution_time_ms`: How long the API call took
- `model_used`: "mistral:7b"
- `success`: true/false
- `error_message`: If failed, what went wrong

---

## How to Run Tests

```bash
# 1. Start services
docker compose up -d

# 2. Wait for Ollama to be ready (if not already running)
ollama serve &  # on macOS

# 3. Test via API
# Use the curl commands above

# 4. Check logs
docker compose logs api | grep "\[OLLAMA\]"
docker compose logs api | grep "\[API\]"

# 5. Query traces in database
docker compose exec db psql -U studypilot -d studypilot \
  -c "SELECT * FROM ai_traces ORDER BY created_at DESC LIMIT 10;"
```

---

## Cleanup

To reset traces:
```sql
DELETE FROM ai_traces;
```

To stop Ollama:
```bash
pkill -f "ollama serve"
```

To stop services:
```bash
docker compose down
```
