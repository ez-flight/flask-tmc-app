#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для выполнения миграции: добавление уникального индекса на MAC-адрес в таблице machines
"""
import os
import sys

# Добавляем корневую директорию проекта в путь
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import pymysql

# Загружаем переменные окружения
try:
    load_dotenv()
except Exception:
    # Если не удалось загрузить через dotenv, пробуем найти .env вручную
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("Ошибка: DATABASE_URL не установлен")
    sys.exit(1)

# Парсим URL
parts = db_url.replace('mysql+pymysql://', '').split('@')
user_pass = parts[0].split(':')
host_port_db = parts[1].split('/')
host_port = host_port_db[0].split(':')

user = user_pass[0]
password = user_pass[1]
host = host_port[0]
port = int(host_port[1]) if len(host_port) > 1 else 3306
database = host_port_db[1]

try:
    conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset='utf8mb4')
    cursor = conn.cursor()
    
    # Читаем SQL файл миграции
    migration_file = os.path.join(os.path.dirname(__file__), 'add_unique_mac_address_to_machines.sql')
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Выполняем SQL команды по отдельности
    statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
    
    for statement in statements:
        if statement:
            try:
                cursor.execute(statement)
                print(f'✓ Выполнено: {statement[:50]}...')
            except Exception as e:
                if 'Duplicate key name' in str(e) or 'already exists' in str(e).lower():
                    print(f'ℹ Пропущено (уже существует): {statement[:50]}...')
                else:
                    print(f'✗ Ошибка при выполнении: {statement[:50]}...')
                    print(f'  Ошибка: {e}')
                    raise
    
    conn.commit()
    print('\n✓ Миграция успешно выполнена')
    
    # Проверяем результат
    cursor.execute("SHOW INDEX FROM machines WHERE Key_name = 'idx_unique_mac_address'")
    if cursor.fetchone():
        print('✓ Уникальный индекс на mac_address создан')
    
    cursor.execute("DESCRIBE machines")
    print('\nСтруктура таблицы machines:')
    for col in cursor.fetchall():
        if col[0] == 'mac_address':
            print(f'  {col[0]}: {col[1]} {col[2]} {col[3]} {col[4]} {col[5]}')
    
except Exception as e:
    print(f'✗ Ошибка: {e}')
    sys.exit(1)
finally:
    if 'conn' in locals():
        conn.close()

