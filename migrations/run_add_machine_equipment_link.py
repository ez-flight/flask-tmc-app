#!/usr/bin/env python3
"""
Скрипт для применения миграции: добавление связи машины с ТМЦ
Добавляет колонку equipment_id в таблицу machines
"""
import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def apply_migration():
    """Применяет миграцию для добавления equipment_id в таблицу machines"""
    with app.app_context():
        try:
            # Проверяем, существует ли колонка
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'machines'
                  AND COLUMN_NAME = 'equipment_id'
            """))
            exists = result.fetchone()[0] > 0
            
            if exists:
                print("✓ Колонка equipment_id уже существует в таблице machines")
            else:
                print("→ Добавляем колонку equipment_id в таблицу machines...")
                db.session.execute(text("""
                    ALTER TABLE `machines`
                    ADD COLUMN `equipment_id` INT NULL COMMENT 'Связь с ТМЦ' AFTER `updated_at`
                """))
                print("✓ Колонка добавлена")
            
            # Проверяем и добавляем внешний ключ
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'machines'
                  AND CONSTRAINT_NAME = 'machines_ibfk_equipment'
            """))
            fk_exists = result.fetchone()[0] > 0
            
            if fk_exists:
                print("✓ Внешний ключ machines_ibfk_equipment уже существует")
            else:
                print("→ Добавляем внешний ключ machines_ibfk_equipment...")
                db.session.execute(text("""
                    ALTER TABLE `machines`
                    ADD CONSTRAINT `machines_ibfk_equipment`
                    FOREIGN KEY (`equipment_id`) REFERENCES `equipment`(`id`) ON DELETE SET NULL
                """))
                print("✓ Внешний ключ добавлен")
            
            # Проверяем и добавляем индекс
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'machines'
                  AND INDEX_NAME = 'idx_equipment_id'
            """))
            idx_exists = result.fetchone()[0] > 0
            
            if idx_exists:
                print("✓ Индекс idx_equipment_id уже существует")
            else:
                print("→ Добавляем индекс idx_equipment_id...")
                db.session.execute(text("""
                    ALTER TABLE `machines`
                    ADD INDEX `idx_equipment_id` (`equipment_id`)
                """))
                print("✓ Индекс добавлен")
            
            db.session.commit()
            print("\n✅ Миграция успешно применена!")
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

