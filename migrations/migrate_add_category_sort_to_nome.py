#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Миграция: Добавление поля category_sort (Категория/сорт) в таблицу nome
Значение от 1 до 5 для группы ТМЦ
"""

import sys
import os
from sqlalchemy import text

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db

def migrate():
    with app.app_context():
        print("Начало миграции: Добавление поля category_sort в таблицу nome")
        try:
            # Проверяем, существует ли уже поле
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('nome')]
            
            if 'category_sort' not in columns:
                db.session.execute(text("""
                    ALTER TABLE nome 
                    ADD COLUMN category_sort INT NULL COMMENT 'Категория (сорт) - значение от 1 до 5'
                """))
                db.session.commit()
                print("✓ Добавлено поле category_sort")
            else:
                print("⚠ Поле category_sort уже существует")
            
            print("\n✓ Миграция успешно завершена!")
            print("\nПримечание: Поле category_sort может содержать значения от 1 до 5.")
            print("Необходимо заполнить это поле для существующих групп ТМЦ через интерфейс редактирования.")
            
        except Exception as e:
            print(f"❌ Ошибка при выполнении миграции: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate()

