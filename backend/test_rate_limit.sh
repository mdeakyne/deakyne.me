#!/bin/bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJyYXRlbGltaXRlc3RAdGVzdC5jb20iLCJleHAiOjE3NjIwMzk1NjMsImlhdCI6MTc2MTQzNDc2MywidHlwZSI6ImFwaV9rZXkifQ.36Vk2DFLG64oLzaYp1YJikDjxaLBOmaa4pRj8zif8p4"

echo "Testing rate limiting (limit: 10 requests/hour)..."
echo ""

for i in {1..11}; do
  RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"Test $i\"}")

  if echo "$RESPONSE" | grep -q "Rate limit"; then
    echo "Request $i: ❌ RATE LIMITED"
  elif echo "$RESPONSE" | grep -q "response"; then
    echo "Request $i: ✅ Success"
  else
    echo "Request $i: ⚠️  Error"
  fi
done
