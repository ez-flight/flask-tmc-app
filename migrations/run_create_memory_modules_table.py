#!/usr/bin/env python3
"""
Скрипт для создания таблицы модулей оперативной памяти (ОЗУ)
Запуск: python3 migrations/run_create_memory_modules_table.py
"""

import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def run_migration():
    """Выполняет миграцию для создания таблицы модулей ОЗУ"""
    migration_file = os.path.join(os.path.dirname(__file__), 'create_memory_modules_table.sql')
    
    if not os.path.exists(migration_file):
        print(f"Ошибка: файл миграции не найден: {migration_file}")
        return False
    
    try:
        with app.app_context():
            print("Чтение файла миграции...")
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            print("Выполнение миграции...")
            db.session.execute(text(sql))
            db.session.commit()
            
            print("✓ Миграция успешно выполнена!")
            print("  Создана таблица pc_memory_modules для модулей оперативной памяти")
            return True
            
    except Exception as e:
        db.session.rollback()
        print(f"✗ Ошибка при выполнении миграции: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Миграция: Создание таблицы модулей оперативной памяти")
    print("=" * 60)
    print()
    
    success = run_migration()
    
    if success:
        print()
        print("Миграция завершена успешно!")
        sys.exit(0)
    else:
        print()
        print("Миграция завершена с ошибками!")
        sys.exit(1)

