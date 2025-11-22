#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания таблицы истории состояний жестких дисков
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import pymysql

load_dotenv()

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("Ошибка: DATABASE_URL не установлен")
    sys.exit(1)

# Парсим URL
parts = db_url.replace('mysql+pymysql://', '').split('@')
user_pass = parts[0].split(':')
host_port_db = parts[1].split('/')
host_port = host_port_db[0].split(':')

user = user_pass[0]
password = user_pass[1]
host = host_port[0]
port = int(host_port[1]) if len(host_port) > 1 else 3306
database = host_port_db[1]

conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset='utf8mb4')
cursor = conn.cursor()

sql = """CREATE TABLE IF NOT EXISTS pc_hard_drive_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hard_drive_id INT NOT NULL,
    check_date DATE NOT NULL,
    power_on_hours INT NULL,
    power_on_count INT NULL,
    health_status VARCHAR(50) NULL,
    comment TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hard_drive_id) REFERENCES pc_hard_drives(id) ON DELETE CASCADE,
    INDEX idx_hard_drive_id (hard_drive_id),
    INDEX idx_check_date (check_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""

try:
    cursor.execute(sql)
    conn.commit()
    print('✓ Таблица pc_hard_drive_history создана')
except Exception as e:
    if 'already exists' in str(e).lower() or 'Duplicate' in str(e):
        print('ℹ Таблица уже существует')
    else:
        print(f'✗ Ошибка: {e}')
        sys.exit(1)

cursor.execute('DESCRIBE pc_hard_drive_history')
print('\nСтруктура таблицы:')
for col in cursor.fetchall():
    print(f'  {col[0]}: {col[1]} {col[2]}')

conn.close()

