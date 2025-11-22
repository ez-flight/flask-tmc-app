#!/usr/bin/env python3
"""
Скрипт для выполнения миграции: добавление поля map_image в таблицу places
"""
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from urllib.parse import urlparse

def run_migration():
    """Выполняет миграцию для добавления поля map_image в таблицу places"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Ошибка: DATABASE_URL не установлен в переменных окружения")
        return False
    
    try:
        # Создаем подключение к базе данных
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Проверяем, существует ли колонка
            check_query = text("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'places'
                  AND COLUMN_NAME = 'map_image'
            """)
            
            result = conn.execute(check_query)
            count = result.fetchone()[0]
            
            if count > 0:
                print("✓ Колонка map_image уже существует в таблице places")
                return True
            
            # Выполняем миграцию
            print("Выполняется миграция: добавление поля map_image в таблицу places...")
            
            migration_query = text("""
                ALTER TABLE `places` 
                ADD COLUMN `map_image` VARCHAR(255) NULL DEFAULT '' 
                COMMENT 'Путь к схеме помещения (PNG, JPG, SVG)' 
                AFTER `opgroup`
            """)
            
            conn.execute(migration_query)
            conn.commit()
            
            print("✓ Миграция успешно выполнена!")
            print("  Добавлено поле map_image в таблицу places")
            return True
            
    except Exception as e:
        print(f"✗ Ошибка при выполнении миграции: {e}")
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)

