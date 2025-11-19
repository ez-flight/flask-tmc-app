# Миграции базы данных

Эта папка содержит все миграции базы данных для проекта.

## Структура

Все миграционные скрипты находятся в этой папке. Каждая миграция должна быть идемпотентной (безопасной для повторного запуска).

## Запуск миграций

Миграции можно запускать напрямую:

```bash
# Из корневой директории проекта
python3 migrations/migrate_add_pinned_to_news.py
python3 migrations/migrate_group_photos.py
python3 migrations/migrate_add_category_sort_to_nome.py
# и т.д.
```

Или из папки migrations:

```bash
cd migrations
python3 migrate_add_pinned_to_news.py
```

## Список миграций

- `migrate_add_pinned_to_news.py` - Добавление столбца 'pinned' в таблицу 'news'
- `migrate_group_photos.py` - Реорганизация фотографий групп в подпапку group_label/
- `migrate_add_category_sort_to_nome.py` - Добавление поля category_sort в таблицу nome
- `migrate_add_equipment_comments.py` - Создание таблицы equipment_comments
- `migrate_add_form8_fields.py` - Добавление полей для формы 8
- `migrate_add_is_composite_to_nome.py` - Добавление столбца is_composite в таблицу nome
- `migrate_add_lost_status.py` - Добавление статуса "потеряно"
- `add_lost_column.sql` - SQL скрипт для добавления столбца lost

## Примечания

- Все миграции проверяют, была ли уже выполнена миграция, перед применением изменений
- Миграции используют переменную окружения `DATABASE_URL` для подключения к БД
- Некоторые миграции требуют контекст приложения Flask (используют `app.app_context()`)

