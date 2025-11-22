#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для выполнения миграции создания таблиц комплектующих ПК.
Использование: python3 migrations/run_pc_components_migration.py
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
    # Пример: mysql+pymysql://user:password@host:port/database
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
            # и фильтруем пустые строки
            sql_commands = [cmd.strip() for cmd in sql_script.split(';') if cmd.strip()]

            for command in sql_commands:
                if command: # Убедимся, что команда не пустая
                    print(f"Выполнение команды: {command[:75]}...") # Логируем часть команды
                    cursor.execute(command)
            conn.commit()
        print(f"✓ Миграция успешно выполнена!")
        print(f"  Созданы таблицы:")
        print(f"    - pc_graphics_cards (видеокарты)")
        print(f"    - pc_hard_drives (жесткие диски)")
        print(f"    - pc_component_links (связь комплектующих с ПК)")
    except pymysql.Error as e:
        print(f"✗ Ошибка при выполнении миграции: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migration_file = os.path.join(os.path.dirname(__file__), 'create_pc_components_tables.sql')
    print(f"Выполняется миграция: создание таблиц для комплектующих ПК...")
    run_sql_migration(migration_file)

