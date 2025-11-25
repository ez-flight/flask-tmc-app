#!/usr/bin/env python3
"""
Скрипт для выполнения миграции: добавление полей для данных из GPU API
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
    """Выполняет миграцию для добавления полей GPU API."""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("Ошибка: DATABASE_URL не установлен в .env файле")
        sys.exit(1)
    
    # Парсим DATABASE_URL
    # Формат: mysql+pymysql://user:password@host:port/database
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
        migration_file = project_root / 'migrations' / 'add_gpu_api_fields_to_graphics_cards.sql'
        
        if not migration_file.exists():
            print(f"Ошибка: файл миграции не найден: {migration_file}")
            sys.exit(1)
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Выполняем миграцию
        with connection.cursor() as cursor:
            # Разделяем SQL на отдельные команды
            statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
            
            for statement in statements:
                if statement:
                    print(f"Выполнение: {statement[:50]}...")
                    try:
                        cursor.execute(statement)
                    except pymysql.err.OperationalError as e:
                        if 'Duplicate column name' in str(e):
                            print(f"Предупреждение: колонка уже существует, пропускаем")
                        else:
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

