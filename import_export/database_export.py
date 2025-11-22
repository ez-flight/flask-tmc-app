#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для экспорта базы данных MySQL в корень проекта.
Использует mysqldump для создания дампа базы данных.
"""
import os
import subprocess
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

def parse_database_url(database_url):
    """Парсит DATABASE_URL и извлекает параметры подключения."""
    # Убираем префикс mysql+pymysql://
    if database_url.startswith('mysql+pymysql://'):
        database_url = database_url.replace('mysql+pymysql://', 'mysql://')
    elif database_url.startswith('mysql://'):
        pass
    else:
        raise ValueError(f"Неподдерживаемый формат DATABASE_URL: {database_url}")
    
    parsed = urlparse(database_url)
    
    return {
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 3306,
        'database': parsed.path.lstrip('/')
    }

def export_database():
    """Экспортирует базу данных MySQL в SQL файл."""
    # Загружаем переменные окружения
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Ошибка: DATABASE_URL не найден в переменных окружения")
        print("Убедитесь, что файл .env существует и содержит DATABASE_URL")
        return False
    
    try:
        # Парсим DATABASE_URL
        db_params = parse_database_url(database_url)
        
        print(f"Подключение к базе данных: {db_params['database']} на {db_params['host']}")
        
        # Создаем имя файла с датой и временем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dump_filename = f"database_backup_{db_params['database']}_{timestamp}.sql"
        # Сохраняем в корень проекта
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dump_path = os.path.join(project_root, dump_filename)
        
        # Формируем команду mysqldump
        cmd = [
            'mysqldump',
            f"--user={db_params['user']}",
            f"--password={db_params['password']}",
            f"--host={db_params['host']}",
            f"--port={db_params['port']}",
            '--single-transaction',
            '--routines',
            '--triggers',
            '--events',
            '--add-drop-table',
            '--complete-insert',
            '--extended-insert',
            db_params['database']
        ]
        
        print(f"Экспорт базы данных в файл: {dump_filename}")
        print("Это может занять некоторое время...")
        
        # Выполняем экспорт
        with open(dump_path, 'w', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True
            )
        
        if result.returncode == 0:
            file_size = os.path.getsize(dump_path)
            file_size_mb = file_size / (1024 * 1024)
            print(f"✓ Экспорт успешно завершен!")
            print(f"  Файл: {dump_filename}")
            print(f"  Размер: {file_size_mb:.2f} MB")
            print(f"  Путь: {dump_path}")
            return True
        else:
            print(f"✗ Ошибка при экспорте базы данных:")
            print(result.stderr)
            # Удаляем пустой файл при ошибке
            if os.path.exists(dump_path):
                os.remove(dump_path)
            return False
            
    except ValueError as e:
        print(f"Ошибка парсинга DATABASE_URL: {e}")
        return False
    except FileNotFoundError:
        print("Ошибка: mysqldump не найден в системе")
        print("Установите MySQL client: sudo apt-get install mysql-client")
        return False
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Экспорт базы данных MySQL")
    print("=" * 60)
    print()
    
    success = export_database()
    
    print()
    if success:
        print("Экспорт завершен успешно!")
    else:
        print("Экспорт завершен с ошибками.")
        exit(1)

