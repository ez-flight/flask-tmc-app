import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def add_is_composite_column_to_nome():
    print("Запуск миграции: добавление столбца 'is_composite' в таблицу 'nome'...")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Проверяем, существует ли столбец 'is_composite'
            check_column_sql = text("SHOW COLUMNS FROM nome LIKE 'is_composite'")
            result = connection.execute(check_column_sql).fetchone()
            
            if result:
                print("Столбец 'is_composite' уже существует. Пропускаем миграцию.")
            else:
                # Добавляем столбец 'is_composite'
                add_column_sql = text("ALTER TABLE nome ADD COLUMN is_composite BOOLEAN NOT NULL DEFAULT FALSE")
                connection.execute(add_column_sql)
                connection.commit()
                print("✓ Столбец 'is_composite' успешно добавлен в таблицу 'nome'")
    except Exception as e:
        print(f"Ошибка при выполнении миграции: {e}")
        raise
    finally:
        print("Миграция завершена!")

if __name__ == '__main__':
    add_is_composite_column_to_nome()

