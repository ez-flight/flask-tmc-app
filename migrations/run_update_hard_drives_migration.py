#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для выполнения миграции обновления таблицы pc_hard_drives.
Использование: python3 migrations/run_update_hard_drives_migration.py
"""
import os
import sys
from dotenv import load_dotenv
import pymysql

# Загружаем переменные окружения
load_dotenv()

def run_sql_migration(sql_file_path):
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Ошибка: Переменная окружения DATABASE_URL не установлена.")
        sys.exit(1)

    # Парсим URL базы данных
    try:
        parts = db_url.split('://')[1].split('@')
        user_pass = parts[0].split(':')
        host_port_db = parts[1].split('/')
        host_port = host_port_db[0].split(':')

        user = user_pass[0]
        password = user_pass[1]
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 3306
        database = host_port_db[1]
    except Exception as e:
        print(f"Ошибка при парсинге DATABASE_URL: {e}")
        sys.exit(1)

    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cursor:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # Разделяем скрипт на отдельные команды по ';'
            sql_commands = [cmd.strip() for cmd in sql_script.split(';') if cmd.strip() and not cmd.strip().startswith('--')]

            for command in sql_commands:
                if command:
                    try:
                        print(f"Выполнение: {command[:80]}...")
                        cursor.execute(command)
                    except pymysql.Error as e:
                        # Игнорируем ошибки "Duplicate" для индексов и внешних ключей
                        if 'Duplicate' in str(e) or 'already exists' in str(e).lower():
                            print(f"  Пропущено (уже существует): {str(e)[:60]}")
                        else:
                            raise
            
            conn.commit()
        print(f"\n✓ Миграция успешно выполнена!")
        print(f"  Обновлена таблица pc_hard_drives:")
        print(f"    - Удалена колонка manufacturer")
        print(f"    - Добавлена колонка vendor_id с внешним ключом")
        print(f"    - Обновлены обязательные поля")
        print(f"    - Добавлены поля для учета здоровья дисков")
    except pymysql.Error as e:
        print(f"\n✗ Ошибка при выполнении миграции: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migration_file = os.path.join(os.path.dirname(__file__), 'update_pc_hard_drives_table.sql')
    print(f"Выполняется миграция: обновление таблицы pc_hard_drives...")
    print(f"ВНИМАНИЕ: Если в таблице есть данные, убедитесь, что они соответствуют новой структуре!\n")
    run_sql_migration(migration_file)
