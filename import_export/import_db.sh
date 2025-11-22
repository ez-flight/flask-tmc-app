#!/bin/bash
# Скрипт для импорта базы данных MySQL
# Автоматически активирует виртуальное окружение и запускает Python скрипт

# Переходим в корень проекта (на уровень выше от import_export)
cd "$(dirname "$0")/.."
source venv/bin/activate

# Если указан файл как аргумент, передаем его
if [ $# -gt 0 ]; then
    python3 -m import_export.database_import "$1"
else
    python3 -m import_export.database_import
fi

