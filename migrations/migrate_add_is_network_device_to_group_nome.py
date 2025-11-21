import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def add_is_network_device_column_to_group_nome():
    print("Запуск миграции: добавление столбца 'is_network_device' в таблицу 'group_nome'...")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Проверяем, существует ли столбец 'is_network_device'
            check_column_sql = text("SHOW COLUMNS FROM group_nome LIKE 'is_network_device'")
            result = connection.execute(check_column_sql).fetchone()
            
            if result:
                print("Столбец 'is_network_device' уже существует. Пропускаем миграцию.")
            else:
                # Добавляем столбец 'is_network_device'
                add_column_sql = text("ALTER TABLE group_nome ADD COLUMN is_network_device BOOLEAN NOT NULL DEFAULT FALSE")
                connection.execute(add_column_sql)
                connection.commit()
                print("✓ Столбец 'is_network_device' успешно добавлен в таблицу 'group_nome'")
    except Exception as e:
        print(f"Ошибка при выполнении миграции: {e}")
        raise
    finally:
        print("Миграция завершена!")

if __name__ == '__main__':
    add_is_network_device_column_to_group_nome()

