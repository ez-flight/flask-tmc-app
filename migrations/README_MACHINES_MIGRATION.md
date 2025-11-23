# Миграция: Добавление поддержки машин/компьютеров

## Проблема

Ошибка: `Unknown column 'pc_hard_drives.machine_id' in 'field list'`

Это означает, что в базе данных отсутствует колонка `machine_id` в таблице `pc_hard_drives`.

## Решение

### Вариант 1: Простая миграция (только колонка machine_id)

Если таблицы `machines` и `machine_history` уже созданы, выполните:

```bash
mysql -u root -p webuseorg3 < migrations/add_machine_id_column.sql
```

### Вариант 2: Полная миграция (все таблицы)

Если нужно создать все таблицы с нуля:

```bash
mysql -u root -p webuseorg3 < migrations/create_machines_tables.sql
```

### Вариант 3: Через Python скрипт (если есть все зависимости)

```bash
cd /home/flask_tmc_app
source venv/bin/activate
python3 migrations/run_create_machines_tables.py
```

## Что делает миграция

1. Создает таблицу `machines` для хранения информации о компьютерах
2. Создает таблицу `machine_history` для истории изменений
3. Добавляет колонку `machine_id` в таблицу `pc_hard_drives`
4. Создает индекс и внешний ключ для связи

## Проверка

После применения миграции проверьте:

```sql
-- Проверка колонки
SHOW COLUMNS FROM pc_hard_drives LIKE 'machine_id';

-- Проверка таблиц
SHOW TABLES LIKE 'machines';
SHOW TABLES LIKE 'machine_history';
```

