#!/usr/bin/env python3
"""
Скрипт для применения миграции: добавление связи видеокарт с машинами
Добавляет колонку machine_id в таблицу pc_graphics_cards
"""
import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def apply_migration():
    """Применяет миграцию для добавления machine_id в таблицу pc_graphics_cards"""
    with app.app_context():
        try:
            # Проверяем, существует ли колонка
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'pc_graphics_cards'
                  AND COLUMN_NAME = 'machine_id'
            """))
            exists = result.fetchone()[0] > 0
            
            if exists:
                print("✓ Колонка machine_id уже существует в таблице pc_graphics_cards")
            else:
                print("→ Добавляем колонку machine_id в таблицу pc_graphics_cards...")
                db.session.execute(text("""
                    ALTER TABLE `pc_graphics_cards`
                    ADD COLUMN `machine_id` INT NULL COMMENT 'Связь с машиной' AFTER `created_at`
                """))
                print("✓ Колонка добавлена")
            
            # Проверяем и добавляем внешний ключ
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'pc_graphics_cards'
                  AND CONSTRAINT_NAME = 'pc_graphics_cards_ibfk_machine'
            """))
            fk_exists = result.fetchone()[0] > 0
            
            if fk_exists:
                print("✓ Внешний ключ pc_graphics_cards_ibfk_machine уже существует")
            else:
                print("→ Добавляем внешний ключ pc_graphics_cards_ibfk_machine...")
                db.session.execute(text("""
                    ALTER TABLE `pc_graphics_cards`
                    ADD CONSTRAINT `pc_graphics_cards_ibfk_machine`
                    FOREIGN KEY (`machine_id`) REFERENCES `machines`(`id`) ON DELETE SET NULL
                """))
                print("✓ Внешний ключ добавлен")
            
            # Проверяем и добавляем индекс
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'pc_graphics_cards'
                  AND INDEX_NAME = 'idx_machine_id'
            """))
            idx_exists = result.fetchone()[0] > 0
            
            if idx_exists:
                print("✓ Индекс idx_machine_id уже существует")
            else:
                print("→ Добавляем индекс idx_machine_id...")
                db.session.execute(text("""
                    ALTER TABLE `pc_graphics_cards`
                    ADD INDEX `idx_machine_id` (`machine_id`)
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

