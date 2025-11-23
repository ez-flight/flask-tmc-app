#!/bin/bash
# Скрипт для применения миграции создания таблиц машин
# Использование: ./apply_machines_migration.sh [database_name] [mysql_user] [mysql_password]

DB_NAME="${1:-webuseorg3}"
DB_USER="${2:-root}"
DB_PASS="${3:-}"

if [ -z "$DB_PASS" ]; then
    echo "Использование: $0 [database_name] [mysql_user] [mysql_password]"
    echo "Или: mysql -u $DB_USER -p $DB_NAME < migrations/create_machines_tables.sql"
    exit 1
fi

echo "Применение миграции для базы данных: $DB_NAME"
mysql -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < migrations/create_machines_tables.sql

if [ $? -eq 0 ]; then
    echo "✓ Миграция успешно применена!"
else
    echo "✗ Ошибка при применении миграции"
    exit 1
fi

