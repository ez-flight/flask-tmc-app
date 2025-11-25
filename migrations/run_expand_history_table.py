#!/usr/bin/env python3
"""
Скрипт для выполнения миграции расширения таблицы истории жестких дисков.
Добавляет все поля диска для полного отслеживания изменений.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
import pymysql

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем DATABASE_URL из переменных окружения
database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("Ошибка: переменная окружения DATABASE_URL не установлена")
    print("Убедитесь, что файл .env существует и содержит DATABASE_URL")
    sys.exit(1)

# Парсим DATABASE_URL
# Формат: mysql+pymysql://user:password@host:port/database
parsed = urlparse(database_url.replace('mysql+pymysql://', 'mysql://'))

host = parsed.hostname or 'localhost'
port = parsed.port or 3306
user = parsed.username
password = parsed.password
database = parsed.path.lstrip('/')

if not all([host, user, password, database]):
    print("Ошибка: некорректный формат DATABASE_URL")
    sys.exit(1)

# Читаем SQL файл
sql_file = project_root / 'migrations' / 'expand_hard_drive_history_table.sql'
if not sql_file.exists():
    print(f"Ошибка: файл миграции не найден: {sql_file}")
    sys.exit(1)

with open(sql_file, 'r', encoding='utf-8') as f:
    sql_script = f.read()

try:
    # Подключаемся к базе данных
    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    print(f"Подключение к базе данных {database} на {host}:{port} установлено")
    
    try:
        with connection.cursor() as cursor:
            # Проверяем существующие колонки
            cursor.execute('DESCRIBE pc_hard_drive_history')
            existing_columns = [row['Field'] for row in cursor.fetchall()]
            
            # Добавляем колонки по одной с проверкой
            new_columns = [
                ('drive_type', 'VARCHAR(50) NULL', 'AFTER `check_date`'),
                ('vendor_id', 'INT NULL', 'AFTER `drive_type`'),
                ('model', 'VARCHAR(200) NULL', 'AFTER `vendor_id`'),
                ('capacity_gb', 'INT NULL', 'AFTER `model`'),
                ('serial_number', 'VARCHAR(100) NULL', 'AFTER `capacity_gb`'),
                ('interface', 'VARCHAR(50) NULL', 'AFTER `serial_number`'),
                ('purchase_date', 'DATE NULL', 'AFTER `health_status`'),
                ('purchase_cost', 'DECIMAL(12, 2) NULL', 'AFTER `purchase_date`'),
                ('machine_id', 'INT NULL', 'AFTER `purchase_cost`'),
                ('active', 'BOOLEAN NULL', 'AFTER `machine_id`')
            ]
            
            for col_name, col_def, position in new_columns:
                if col_name not in existing_columns:
                    try:
                        sql = f'ALTER TABLE pc_hard_drive_history ADD COLUMN `{col_name}` {col_def} {position}'
                        print(f'Добавляем колонку: {col_name}...')
                        cursor.execute(sql)
                        print(f'  ✓ Успешно')
                    except pymysql.err.OperationalError as e:
                        if 'Duplicate column name' in str(e):
                            print(f'  ⚠ Колонка уже существует, пропускаем')
                        else:
                            raise
                else:
                    print(f'Колонка {col_name} уже существует, пропускаем')
            
            # Добавляем индексы
            print('\nДобавляем индексы...')
            cursor.execute('SHOW INDEX FROM pc_hard_drive_history')
            existing_indexes = [row['Key_name'] for row in cursor.fetchall()]
            
            if 'idx_vendor_id' not in existing_indexes:
                try:
                    cursor.execute('ALTER TABLE pc_hard_drive_history ADD INDEX idx_vendor_id (vendor_id)')
                    print('  ✓ Индекс idx_vendor_id добавлен')
                except pymysql.err.OperationalError as e:
                    if 'Duplicate key name' in str(e):
                        print('  ⚠ Индекс уже существует, пропускаем')
                    else:
                        raise
            else:
                print('  Индекс idx_vendor_id уже существует, пропускаем')
            
            if 'idx_machine_id' not in existing_indexes:
                try:
                    cursor.execute('ALTER TABLE pc_hard_drive_history ADD INDEX idx_machine_id (machine_id)')
                    print('  ✓ Индекс idx_machine_id добавлен')
                except pymysql.err.OperationalError as e:
                    if 'Duplicate key name' in str(e):
                        print('  ⚠ Индекс уже существует, пропускаем')
                    else:
                        raise
            else:
                print('  Индекс idx_machine_id уже существует, пропускаем')
            
            # Добавляем внешние ключи
            print('\nДобавляем внешние ключи...')
            cursor.execute('''
                SELECT CONSTRAINT_NAME 
                FROM information_schema.TABLE_CONSTRAINTS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'pc_hard_drive_history' 
                AND CONSTRAINT_TYPE = 'FOREIGN KEY'
            ''')
            existing_fks = [row['CONSTRAINT_NAME'] for row in cursor.fetchall()]
            
            if 'fk_history_vendor' not in existing_fks:
                try:
                    cursor.execute('''
                        ALTER TABLE pc_hard_drive_history 
                        ADD CONSTRAINT fk_history_vendor 
                        FOREIGN KEY (vendor_id) REFERENCES vendor (id) ON DELETE SET NULL
                    ''')
                    print('  ✓ Внешний ключ fk_history_vendor добавлен')
                except pymysql.err.OperationalError as e:
                    if 'Duplicate key name' in str(e) or 'already exists' in str(e).lower():
                        print('  ⚠ Внешний ключ уже существует, пропускаем')
                    else:
                        raise
            else:
                print('  Внешний ключ fk_history_vendor уже существует, пропускаем')
            
            if 'fk_history_machine' not in existing_fks:
                try:
                    cursor.execute('''
                        ALTER TABLE pc_hard_drive_history 
                        ADD CONSTRAINT fk_history_machine 
                        FOREIGN KEY (machine_id) REFERENCES machines (id) ON DELETE SET NULL
                    ''')
                    print('  ✓ Внешний ключ fk_history_machine добавлен')
                except pymysql.err.OperationalError as e:
                    if 'Duplicate key name' in str(e) or 'already exists' in str(e).lower():
                        print('  ⚠ Внешний ключ уже существует, пропускаем')
                    else:
                        raise
            else:
                print('  Внешний ключ fk_history_machine уже существует, пропускаем')
            
            connection.commit()
            print("\n✅ Миграция успешно выполнена!")
            print("  Расширена таблица pc_hard_drive_history:")
            print("    - Добавлены поля: drive_type, vendor_id, model, capacity_gb, serial_number, interface")
            print("    - Добавлены поля: purchase_date, purchase_cost, machine_id, active")
            print("    - Добавлены индексы и внешние ключи")
            
    except Exception as e:
        connection.rollback()
        print(f"\n❌ Ошибка при выполнении миграции: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'connection' in locals():
            connection.close()
            print("Соединение закрыто")
        
except Exception as e:
    print(f"❌ Ошибка подключения к базе данных: {e}")
    sys.exit(1)

