#!/bin/bash
# Скрипт для экспорта базы данных MySQL
# Автоматически активирует виртуальное окружение и запускает Python скрипт

cd "$(dirname "$0")"
source venv/bin/activate
python3 export_database.py

