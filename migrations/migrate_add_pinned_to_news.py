# migrate_add_pinned_to_news.py
"""
Скрипт для добавления столбца 'pinned' в таблицу 'news'.
Запустите этот скрипт один раз для обновления структуры базы данных.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Загружаем переменные окружения
load_dotenv()

# Получаем URL базы данных
database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("Ошибка: DATABASE_URL не найден в переменных окружения")
    exit(1)

# Создаем подключение к базе данных
engine = create_engine(database_url)

def migrate():
    """Добавляет столбец 'pinned' в таблицу 'news'."""
    try:
        with engine.connect() as conn:
            # Проверяем, существует ли уже столбец
            check_query = text("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'news' 
                AND COLUMN_NAME = 'pinned'
            """)
            result = conn.execute(check_query)
            count = result.fetchone()[0]
            
            if count > 0:
                print("Столбец 'pinned' уже существует в таблице 'news'. Миграция не требуется.")
                return
            
            # Добавляем столбец
            alter_query = text("""
                ALTER TABLE news 
                ADD COLUMN pinned BOOLEAN NOT NULL DEFAULT FALSE
            """)
            conn.execute(alter_query)
            conn.commit()
            print("✓ Столбец 'pinned' успешно добавлен в таблицу 'news'")
            
    except Exception as e:
        print(f"Ошибка при выполнении миграции: {e}")
        raise

if __name__ == '__main__':
    print("Запуск миграции: добавление столбца 'pinned' в таблицу 'news'...")
    migrate()
    print("Миграция завершена!")

