import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def create_equipment_comments_table():
    print("Запуск миграции: создание таблицы 'equipment_comments'...")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Проверяем, существует ли таблица
            check_table_sql = text("SHOW TABLES LIKE 'equipment_comments'")
            result = connection.execute(check_table_sql).fetchone()
            
            if result:
                print("Таблица 'equipment_comments' уже существует. Пропускаем миграцию.")
            else:
                # Создаем таблицу
                create_table_sql = text("""
                    CREATE TABLE equipment_comments (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        equipment_id INT NOT NULL,
                        comment TEXT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        created_by INT NULL,
                        FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
                        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
                        INDEX idx_equipment_id (equipment_id),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                connection.execute(create_table_sql)
                connection.commit()
                print("✓ Таблица 'equipment_comments' успешно создана")
    except Exception as e:
        print(f"Ошибка при выполнении миграции: {e}")
        raise
    finally:
        print("Миграция завершена!")

if __name__ == '__main__':
    create_equipment_comments_table()

