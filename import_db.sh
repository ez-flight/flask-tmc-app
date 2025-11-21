#!/bin/bash
# Скрипт для импорта базы данных MySQL
# Автоматически активирует виртуальное окружение и запускает Python скрипт

cd "$(dirname "$0")"
source venv/bin/activate

# Если указан файл как аргумент, передаем его
if [ $# -gt 0 ]; then
    python3 import_database.py "$1"
else
    python3 import_database.py
fi

