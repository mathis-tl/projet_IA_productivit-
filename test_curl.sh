#!/bin/bash

# Script de test curl pour Jalon 2

echo "=== TEST CURL JALON 2 ==="
echo ""

# 1. Login
echo "1️⃣ LOGIN"
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"curl_test@example.com","password":"pass123"}' | jq -r '.access_token')

echo "Token obtenu: ${TOKEN:0:20}..."
echo ""

# 2. Créer 2 pages
echo "2️⃣ CRÉER PAGES"
PAGE1=$(curl -s -X POST http://localhost:8000/pages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Page 1","description":"First page"}' | jq '.id')

PAGE2=$(curl -s -X POST http://localhost:8000/pages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Page 2","description":"Second page"}' | jq '.id')

echo "Pages créées: $PAGE1, $PAGE2"
echo ""

# 3. Créer un lien
echo "3️⃣ CRÉER LIEN"
curl -s -X POST http://localhost:8000/links \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"source_page_id\":$PAGE1,\"target_page_id\":$PAGE2,\"type\":\"related\"}" | jq .
echo ""

# 4. Récupérer les liens
echo "4️⃣ LISTER LES LIENS"
curl -s -X GET "http://localhost:8000/links" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo ""

# 5. Créer une AITrace
echo "5️⃣ CRÉER AI TRACE"
curl -s -X POST http://localhost:8000/ai-traces \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"page_id\":$PAGE1,\"analysis_type\":\"summarize\",\"generated_content\":\"This is a summary\",\"model_used\":\"mistral:7b\",\"success\":true}" | jq .
echo ""

# 6. Récupérer les AI traces
echo "6️⃣ LISTER AI TRACES"
curl -s -X GET "http://localhost:8000/ai-traces" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo ""

# 7. Créer une tâche
echo "7️⃣ CRÉER TÂCHE"
TASK=$(curl -s -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"My Task","description":"Do something","priority":"high","status":"todo"}' | jq '.id')

echo "Tâche créée: $TASK"
echo ""

# 8. Récupérer les tâches d'aujourd'hui
echo "8️⃣ TÂCHES D'AUJOURD'HUI"
curl -s -X GET "http://localhost:8000/tasks/today" \
  -H "Authorization: Bearer $TOKEN" | jq . | head -20
echo ""

echo "✅ Tests curl terminés!"
