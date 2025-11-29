#!/usr/bin/env python3
"""
Скрипт для добавления расширенных полей для видеокарт из API gpu-info-api.
Добавляет поля только если они еще не существуют.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pymysql
from urllib.parse import urlparse

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Загружаем переменные окружения
load_dotenv()

# Получаем URL базы данных из переменной окружения
database_url = os.getenv('DATABASE_URL')

if not database_url:
    print("Ошибка: переменная окружения DATABASE_URL не установлена")
    sys.exit(1)

# Парсим URL базы данных
# Формат: mysql+pymysql://user:password@host:port/database
try:
    # Заменяем mysql+pymysql:// на mysql:// для правильного парсинга
    parsed = urlparse(database_url.replace('mysql+pymysql://', 'mysql://'))
    
    host = parsed.hostname or 'localhost'
    port = parsed.port or 3306
    user = parsed.username
    password = parsed.password
    database = parsed.path.lstrip('/')
    
    if not database:
        print("Ошибка: не указана база данных в DATABASE_URL")
        sys.exit(1)
    
    print(f"Подключение к базе данных: {host}:{port}/{database}")
    
except Exception as e:
    print(f"Ошибка при парсинге DATABASE_URL: {e}")
    sys.exit(1)

# Подключаемся к базе данных
try:
    connection = pymysql.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    print(f"✅ Подключение к базе данных {database} установлено")
    
    # Читаем SQL-скрипт
    script_path = project_root / 'migrations' / 'add_extended_gpu_fields.sql'
    
    if not script_path.exists():
        print(f"Ошибка: файл миграции не найден: {script_path}")
        sys.exit(1)
    
    with open(script_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    # Разделяем скрипт на отдельные команды
    # Обрабатываем многострочные команды
    sql_commands = []
    current_command = []
    
    for line in sql_script.split('\n'):
        line = line.strip()
        # Пропускаем пустые строки и комментарии
        if not line or line.startswith('--'):
            continue
        
        # Убираем комментарии в конце строки
        if '--' in line:
            line = line.split('--')[0].strip()
        
        if line:
            current_command.append(line)
            # Если строка заканчивается точкой с запятой, завершаем команду
            if line.endswith(';'):
                full_command = ' '.join(current_command)
                # Убираем точку с запятой в конце
                full_command = full_command.rstrip(';').strip()
                if full_command:
                    sql_commands.append(full_command)
                current_command = []
    
    # Если осталась незавершенная команда
    if current_command:
        full_command = ' '.join(current_command).strip()
        if full_command:
            sql_commands.append(full_command)
    
    print(f"Найдено {len(sql_commands)} SQL-команд для выполнения")
    
    # Выполняем каждую команду отдельно
    with connection.cursor() as cursor:
        added_count = 0
        skipped_count = 0
        
        for i, sql_command in enumerate(sql_commands, 1):
            try:
                # Проверяем, существует ли колонка, перед добавлением
                # Извлекаем название колонки из команды ALTER TABLE
                if 'ADD COLUMN' in sql_command:
                    # Парсим название колонки
                    parts = sql_command.split('ADD COLUMN')
                    if len(parts) > 1:
                        column_part = parts[1].strip().split()[0]
                        column_name = column_part.strip()
                        
                        # Проверяем существование колонки
                        check_sql = """
                            SELECT COUNT(*) as count 
                            FROM information_schema.COLUMNS 
                            WHERE TABLE_SCHEMA = %s 
                            AND TABLE_NAME = 'pc_graphics_cards' 
                            AND COLUMN_NAME = %s
                        """
                        cursor.execute(check_sql, (database, column_name))
                        result = cursor.fetchone()
                        
                        if result['count'] > 0:
                            print(f"⏭️  [{i}/{len(sql_commands)}] Колонка {column_name} уже существует, пропускаем")
                            skipped_count += 1
                            continue
                
                # Выполняем команду
                cursor.execute(sql_command)
                if 'ADD COLUMN' in sql_command:
                    # Извлекаем название колонки для вывода
                    parts = sql_command.split('ADD COLUMN')
                    if len(parts) > 1:
                        column_name = parts[1].strip().split()[0].strip()
                        print(f"✅ [{i}/{len(sql_commands)}] Добавлена колонка: {column_name}")
                        added_count += 1
                else:
                    print(f"✅ [{i}/{len(sql_commands)}] Команда выполнена успешно")
                
            except pymysql.err.OperationalError as e:
                error_code = e.args[0] if e.args else 0
                if error_code == 1060 or 'Duplicate column name' in str(e):
                    print(f"⏭️  [{i}/{len(sql_commands)}] Колонка уже существует, пропускаем")
                    skipped_count += 1
                else:
                    print(f"❌ [{i}/{len(sql_commands)}] Ошибка при выполнении команды: {e}")
                    print(f"   SQL: {sql_command[:150]}...")
            except Exception as e:
                print(f"❌ [{i}/{len(sql_commands)}] Ошибка при выполнении команды: {e}")
                print(f"   SQL: {sql_command[:150]}...")
        
        print(f"\n📊 Итого: добавлено {added_count} колонок, пропущено {skipped_count}")
    
    # Применяем изменения
    connection.commit()
    print("✅ Все изменения применены успешно")
    
    connection.close()
    print("✅ Соединение с базой данных закрыто")
    
except pymysql.Error as e:
    print(f"❌ Ошибка базы данных: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Неожиданная ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

