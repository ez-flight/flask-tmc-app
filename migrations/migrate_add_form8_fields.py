#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Миграция для добавления полей для Формы 8 в таблицу equipment.
Добавляет необязательные поля: warehouse_rack, warehouse_cell, unit_name, unit_code, profile, size, stock_norm.
"""

import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Equipment

def migrate():
    """Добавляет новые поля в таблицу equipment."""
    with app.app_context():
        try:
            # Проверяем, существуют ли уже поля
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('equipment')]
            
            from sqlalchemy import text
            
            if 'warehouse_rack' not in columns:
                db.session.execute(text("""
                    ALTER TABLE equipment 
                    ADD COLUMN warehouse_rack VARCHAR(100) NULL COMMENT 'Стеллаж'
                """))
                db.session.commit()
                print("✓ Добавлено поле warehouse_rack")
            else:
                print("⚠ Поле warehouse_rack уже существует")
            
            if 'warehouse_cell' not in columns:
                db.session.execute(text("""
                    ALTER TABLE equipment 
                    ADD COLUMN warehouse_cell VARCHAR(100) NULL COMMENT 'Ячейка'
                """))
                db.session.commit()
                print("✓ Добавлено поле warehouse_cell")
            else:
                print("⚠ Поле warehouse_cell уже существует")
            
            if 'unit_name' not in columns:
                db.session.execute(text("""
                    ALTER TABLE equipment 
                    ADD COLUMN unit_name VARCHAR(50) NULL COMMENT 'Единица измерения (наименование)'
                """))
                db.session.commit()
                print("✓ Добавлено поле unit_name")
            else:
                print("⚠ Поле unit_name уже существует")
            
            if 'unit_code' not in columns:
                db.session.execute(text("""
                    ALTER TABLE equipment 
                    ADD COLUMN unit_code VARCHAR(10) NULL COMMENT 'Единица измерения (код)'
                """))
                db.session.commit()
                print("✓ Добавлено поле unit_code")
            else:
                print("⚠ Поле unit_code уже существует")
            
            if 'profile' not in columns:
                db.session.execute(text("""
                    ALTER TABLE equipment 
                    ADD COLUMN profile VARCHAR(100) NULL COMMENT 'Профиль'
                """))
                db.session.commit()
                print("✓ Добавлено поле profile")
            else:
                print("⚠ Поле profile уже существует")
            
            if 'size' not in columns:
                db.session.execute(text("""
                    ALTER TABLE equipment 
                    ADD COLUMN size VARCHAR(100) NULL COMMENT 'Размер'
                """))
                db.session.commit()
                print("✓ Добавлено поле size")
            else:
                print("⚠ Поле size уже существует")
            
            if 'stock_norm' not in columns:
                db.session.execute(text("""
                    ALTER TABLE equipment 
                    ADD COLUMN stock_norm VARCHAR(50) NULL COMMENT 'Норма запаса'
                """))
                db.session.commit()
                print("✓ Добавлено поле stock_norm")
            else:
                print("⚠ Поле stock_norm уже существует")
            
            print("\n✓ Миграция успешно завершена!")
            
        except Exception as e:
            print(f"❌ Ошибка при выполнении миграции: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    migrate()

