#\!/bin/bash

echo "========================================"
echo "ACCURACY DIAGNOSTIC TEST"
echo "========================================"

# Test cases
tests=(
  "how do I clean my dishwasher|clean,wash,maintenance"
  "where is the water filter|filter,location,replace"
  "ice maker stopped working|ice,water,check"
)

for test_case in "${tests[@]}"; do
  query=$(echo "$test_case" | cut -d'|' -f1)
  keywords=$(echo "$test_case" | cut -d'|' -f2)
  
  echo ""
  echo "📋 Query: $query"
  
  response=$(curl -s http://localhost:8000/query \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"$query\",\"top_k\":5}")
  
  answer=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('answer', ''))" 2>/dev/null)
  citations=$(echo "$response" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('citations', [])))" 2>/dev/null)
  safety=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('safety_flag', False))" 2>/dev/null)
  
  echo "   Safety Flagged: $safety"
  echo "   Citations: $citations"
  echo "   Answer Preview: ${answer:0:150}..."
done

echo ""
echo "========================================"
