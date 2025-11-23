#!/bin/bash
# Скрипт для восстановления удаленных дисков через API

API_URL="http://localhost:5000/api/hdd_collect"

echo "Восстановление дисков через API..."
echo "URL: $API_URL"
echo ""

curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d @restore_disks.json

echo ""
echo "Готово!"

