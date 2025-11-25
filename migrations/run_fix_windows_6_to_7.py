#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления 'Windows 6' на 'Windows 7' в базе данных.
Обновляет все записи в таблице machines, где os_version = '6'.
Дата: 2025-11-24
"""

import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Импортируем только то, что нужно для работы с БД
from dotenv import load_dotenv
load_dotenv()

from app import app, db
from models import Machine

def migrate():
    """Исправляет 'Windows 6' на 'Windows 7' в базе данных."""
    try:
        with app.app_context():
            # Находим все машины с os_version = '6'
            machines_with_windows_6 = Machine.query.filter_by(os_version='6').all()
            
            count = len(machines_with_windows_6)
            
            if count == 0:
                print("✓ Записей с 'Windows 6' не найдено. Обновление не требуется.")
                return True
            
            print(f"Найдено {count} записей с os_version = '6'. Начинаю обновление...")
            
            # Обновляем каждую запись
            updated_count = 0
            for machine in machines_with_windows_6:
                print(f"  Обновляю машину ID {machine.id} (hostname: {machine.hostname})")
                machine.os_version = '7'
                updated_count += 1
            
            # Сохраняем изменения
            db.session.commit()
            
            print(f"✓ Успешно обновлено {updated_count} записей.")
            print(f"  Все записи с 'Windows 6' исправлены на 'Windows 7'.")
            return True
            
    except Exception as e:
        print(f"✗ Ошибка при выполнении миграции: {str(e)}")
        db.session.rollback()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Миграция: Исправление 'Windows 6' на 'Windows 7'")
    print("=" * 60)
    
    success = migrate()
    
    if success:
        print("\n✓ Миграция успешно завершена!")
        sys.exit(0)
    else:
        print("\n✗ Миграция завершилась с ошибкой!")
        sys.exit(1)

