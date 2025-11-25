#!/usr/bin/env python3
"""
Скрипт для выполнения миграции: добавление расширенных полей процессоров.
"""
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import pymysql
from urllib.parse import urlparse

def run_migration():
    """Выполняет миграцию для добавления расширенных полей процессоров."""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("Ошибка: DATABASE_URL не установлен в .env файле")
        sys.exit(1)
    
    # Парсим DATABASE_URL
    parsed = urlparse(database_url.replace('mysql+pymysql://', 'mysql://'))
    
    host = parsed.hostname or 'localhost'
    port = parsed.port or 3306
    user = parsed.username
    password = parsed.password
    database = parsed.path.lstrip('/')
    
    print(f"Подключение к базе данных: {host}:{port}/{database}")
    
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print("Подключение установлено")
        
        # Читаем SQL файл
        migration_file = project_root / 'migrations' / 'add_cpu_extended_fields.sql'
        
        if not migration_file.exists():
            print(f"Ошибка: файл миграции не найден: {migration_file}")
            sys.exit(1)
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Выполняем миграцию
        with connection.cursor() as cursor:
            # Добавляем колонки по одной с обработкой ошибок
            columns_to_add = [
                ('memory_channels', 'INT NULL', 'max_memory_gb'),
                ('memory_frequency_mhz', 'VARCHAR(50) NULL', 'memory_channels'),
                ('cache_l1_kb', 'INT NULL', 'benchmark_rating'),
                ('cache_l2_kb', 'INT NULL', 'cache_l1_kb'),
                ('cache_l3_kb', 'INT NULL', 'cache_l2_kb'),
                ('integrated_graphics', 'BOOLEAN NULL', 'cache_l3_kb'),
                ('graphics_name', 'VARCHAR(100) NULL', 'integrated_graphics'),
                ('graphics_frequency_mhz', 'INT NULL', 'graphics_name'),
                ('pcie_version', 'VARCHAR(20) NULL', 'graphics_frequency_mhz'),
                ('pcie_lanes', 'INT NULL', 'pcie_version'),
                ('unlocked_multiplier', 'BOOLEAN NULL', 'pcie_lanes'),
                ('ecc_support', 'BOOLEAN NULL', 'unlocked_multiplier'),
            ]
            
            for col_name, col_def, after_col in columns_to_add:
                try:
                    # Проверяем, существует ли колонка
                    cursor.execute(f"SHOW COLUMNS FROM pc_cpus LIKE '{col_name}'")
                    if cursor.fetchone():
                        print(f"  Колонка {col_name} уже существует, пропускаем")
                        continue
                    
                    # Добавляем колонку
                    sql = f"ALTER TABLE pc_cpus ADD COLUMN `{col_name}` {col_def} AFTER `{after_col}`"
                    print(f"Выполняем: {sql}")
                    cursor.execute(sql)
                    print(f"  ✓ Колонка {col_name} добавлена")
                except pymysql.err.OperationalError as e:
                    if 'Duplicate column name' in str(e):
                        print(f"  Колонка {col_name} уже существует")
                    else:
                        print(f"  ✗ Ошибка при добавлении {col_name}: {e}")
                        # Пробуем добавить без указания позиции
                        try:
                            sql = f"ALTER TABLE pc_cpus ADD COLUMN `{col_name}` {col_def}"
                            cursor.execute(sql)
                            print(f"  ✓ Колонка {col_name} добавлена (без позиции)")
                        except Exception as e2:
                            print(f"  ✗ Не удалось добавить {col_name}: {e2}")
                            raise
        
        connection.commit()
        print("Миграция успешно выполнена!")
        
    except Exception as e:
        print(f"Ошибка при выполнении миграции: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'connection' in locals():
            connection.close()
            print("Соединение закрыто")

if __name__ == '__main__':
    run_migration()

