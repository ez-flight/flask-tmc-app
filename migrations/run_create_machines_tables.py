#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для применения миграции: создание таблиц для машин/компьютеров
Дата: 2025-11-23
"""

import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Импортируем только то, что нужно для работы с БД
from dotenv import load_dotenv
load_dotenv()

import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def migrate():
    """Применяет миграцию создания таблиц для машин."""
    try:
        # Получаем параметры подключения из переменных окружения
        import os
        database_url = os.getenv('DATABASE_URL', '')
        
        if not database_url:
            print("✗ DATABASE_URL не установлен в .env файле")
            return False
        
        # Парсим DATABASE_URL (формат: mysql+pymysql://user:password@host/database)
        from urllib.parse import urlparse
        parsed = urlparse(database_url.replace('mysql+pymysql://', 'mysql://'))
        
        db_user = parsed.username
        db_password = parsed.password
        db_host = parsed.hostname or 'localhost'
        db_port = parsed.port or 3306
        db_name = parsed.path.lstrip('/')
        
        # Создаем подключение напрямую через pymysql
        connection = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
            charset='utf8mb4'
        )
        
        try:
            # Читаем SQL файл
            sql_file_path = os.path.join(os.path.dirname(__file__), 'create_machines_tables.sql')
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Выполняем SQL команды
            with connection.cursor() as cursor:
                # Выполняем весь скрипт
                for statement in sql_content.split(';'):
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        try:
                            cursor.execute(statement)
                            print(f"✓ Выполнено: {statement[:50]}...")
                        except Exception as e:
                            # Игнорируем ошибки "уже существует"
                            if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower() or '1050' in str(e):
                                print(f"⚠ Пропущено (уже существует): {statement[:50]}...")
                            else:
                                print(f"✗ Ошибка: {str(e)}")
                                print(f"  Команда: {statement[:100]}")
                                raise
                
                connection.commit()
            
            print("\n✓ Миграция успешно применена!")
            return True
            
        finally:
            connection.close()
            
    except Exception as e:
        print(f"\n✗ Ошибка при применении миграции: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Применение миграции: создание таблиц для машин/компьютеров")
    print("=" * 60)
    success = migrate()
    sys.exit(0 if success else 1)

