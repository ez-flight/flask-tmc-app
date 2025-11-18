"""
Миграция: Добавление поля lost (статус "Потерян") в таблицу equipment
"""
from sqlalchemy import text

def migrate_add_lost_status(db):
    """
    Добавляет поле lost в таблицу equipment для статуса "Потерян".
    """
    try:
        # Проверяем, существует ли уже поле lost
        result = db.session.execute(text("""
            SELECT COUNT(*) as cnt 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'equipment' 
            AND COLUMN_NAME = 'lost'
        """))
        
        exists = result.fetchone()[0] > 0
        
        if not exists:
            # Добавляем поле lost
            db.session.execute(text("""
                ALTER TABLE `equipment` 
                ADD COLUMN `lost` TINYINT(1) NOT NULL DEFAULT 0 
                COMMENT 'Статус: Потерян (0=False, 1=True)' 
                AFTER `repair`
            """))
            
            db.session.commit()
            print("✅ Поле 'lost' успешно добавлено в таблицу 'equipment'")
            return True
        else:
            print("ℹ️  Поле 'lost' уже существует в таблице 'equipment'")
            return False
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка при добавлении поля 'lost': {e}")
        return False

if __name__ == '__main__':
    # Для запуска напрямую
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from app import app, db
    
    with app.app_context():
        migrate_add_lost_status(db)

