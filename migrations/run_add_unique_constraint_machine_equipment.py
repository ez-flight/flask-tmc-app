#!/usr/bin/env python3
"""
Скрипт для применения миграции: добавление уникального ограничения на связь машины с ТМЦ
Обеспечивает связь один к одному между Machine и Equipment
"""
import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def apply_migration():
    """Применяет миграцию для добавления уникального ограничения на equipment_id"""
    with app.app_context():
        try:
            # Проверяем, существует ли уникальный индекс
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'machines'
                  AND COLUMN_NAME = 'equipment_id'
                  AND NON_UNIQUE = 0
            """))
            exists = result.fetchone()[0] > 0
            
            if exists:
                print("✓ Уникальный индекс на equipment_id уже существует")
            else:
                print("→ Добавляем уникальный индекс на equipment_id...")
                db.session.execute(text("""
                    ALTER TABLE `machines`
                    ADD UNIQUE INDEX `idx_equipment_id_unique` (`equipment_id`)
                """))
                print("✓ Уникальный индекс добавлен")
            
            db.session.commit()
            print("\n✅ Миграция успешно применена!")
            print("Теперь связь между машинами и ТМЦ является один к одному.")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Ошибка при применении миграции: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)

