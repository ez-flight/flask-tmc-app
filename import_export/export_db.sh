#!/bin/bash
# Скрипт для экспорта базы данных MySQL
# Автоматически активирует виртуальное окружение и запускает Python скрипт

# Переходим в корень проекта (на уровень выше от import_export)
cd "$(dirname "$0")/.."
source venv/bin/activate
python3 -m import_export.database_export

