#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для импорта базы данных MySQL из SQL файла.
Использует mysql для восстановления базы данных из дампа.
"""
import os
import sys
import subprocess
import glob
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

def list_backup_files():
    """Возвращает список доступных файлов резервных копий."""
    project_root = os.path.dirname(__file__)
    pattern = os.path.join(project_root, 'database_backup_*.sql')
    files = sorted(glob.glob(pattern), reverse=True)  # Сначала самые новые
    return files

def import_database(sql_file=None):
    """Импортирует базу данных MySQL из SQL файла."""
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
        
        # Если файл не указан, показываем список доступных
        if not sql_file:
            backup_files = list_backup_files()
            if not backup_files:
                print("Ошибка: не найдено файлов резервных копий в корне проекта")
                print("Сначала создайте резервную копию с помощью export_database.py")
                return False
            
            print("Доступные файлы резервных копий:")
            for i, file in enumerate(backup_files[:10], 1):  # Показываем последние 10
                filename = os.path.basename(file)
                file_size = os.path.getsize(file) / (1024 * 1024)
                print(f"  {i}. {filename} ({file_size:.2f} MB)")
            
            if len(backup_files) > 10:
                print(f"  ... и еще {len(backup_files) - 10} файлов")
            
            print()
            choice = input("Введите номер файла для импорта (или путь к файлу): ").strip()
            
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(backup_files):
                    sql_file = backup_files[choice_num - 1]
                else:
                    print(f"Ошибка: неверный номер. Выберите от 1 до {len(backup_files)}")
                    return False
            else:
                # Пользователь ввел путь к файлу
                if os.path.exists(choice):
                    sql_file = choice
                else:
                    print(f"Ошибка: файл не найден: {choice}")
                    return False
        else:
            # Файл указан как аргумент
            if not os.path.exists(sql_file):
                print(f"Ошибка: файл не найден: {sql_file}")
                return False
        
        sql_file = os.path.abspath(sql_file)
        filename = os.path.basename(sql_file)
        
        print(f"Подключение к базе данных: {db_params['database']} на {db_params['host']}")
        print(f"Импорт из файла: {filename}")
        print()
        print("⚠️  ВНИМАНИЕ: Это действие перезапишет все данные в базе данных!")
        confirm = input("Вы уверены, что хотите продолжить? (yes/no): ").strip().lower()
        
        if confirm not in ['yes', 'y', 'да', 'д']:
            print("Импорт отменен.")
            return False
        
        print()
        print("Импорт базы данных...")
        print("Это может занять некоторое время...")
        
        # Формируем команду mysql для импорта
        cmd = [
            'mysql',
            f"--user={db_params['user']}",
            f"--password={db_params['password']}",
            f"--host={db_params['host']}",
            f"--port={db_params['port']}",
            db_params['database']
        ]
        
        # Читаем SQL файл и передаем в mysql
        with open(sql_file, 'r', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdin=f,
                stderr=subprocess.PIPE,
                text=True
            )
        
        if result.returncode == 0:
            print("✓ Импорт успешно завершен!")
            print(f"  База данных {db_params['database']} восстановлена из файла {filename}")
            return True
        else:
            print(f"✗ Ошибка при импорте базы данных:")
            print(result.stderr)
            return False
            
    except ValueError as e:
        print(f"Ошибка парсинга DATABASE_URL: {e}")
        return False
    except FileNotFoundError:
        print("Ошибка: mysql не найден в системе")
        print("Установите MySQL client: sudo apt-get install mysql-client")
        return False
    except KeyboardInterrupt:
        print("\nИмпорт прерван пользователем.")
        return False
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Импорт базы данных MySQL")
    print("=" * 60)
    print()
    
    # Проверяем, указан ли файл как аргумент командной строки
    sql_file = None
    if len(sys.argv) > 1:
        sql_file = sys.argv[1]
    
    success = import_database(sql_file)
    
    print()
    if success:
        print("Импорт завершен успешно!")
    else:
        print("Импорт завершен с ошибками.")
        exit(1)

