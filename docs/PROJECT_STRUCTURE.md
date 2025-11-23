# Структура проекта

## Обзор

Проект организован следующим образом:

```
flask_tmc_app/
├── app.py                 # Главный файл приложения Flask
├── models.py              # Модели базы данных
├── requirements.txt       # Зависимости Python
├── README.md              # Основная документация
│
├── migrations/            # Миграции базы данных
│   ├── README.md
│   ├── migrate_*.py       # Скрипты миграций
│   └── *.sql             # SQL скрипты
│
├── scripts/               # Вспомогательные скрипты
│   ├── README.md
│   ├── download_static_assets.py
│   ├── extract_static_files.py
│   ├── test_mode.py
│   ├── restore/          # Скрипты восстановления данных
│   │   ├── README.md
│   │   ├── restore_disks_simple.py
│   │   ├── restore_disks.py
│   │   ├── restore_disks.json
│   │   └── restore_disks.sh
│   └── test.py
│
├── docs/                  # Документация
│   ├── README.md
│   ├── PROJECT_STRUCTURE.md
│   ├── COMPATIBILITY.md
│   ├── REORGANIZATION_SUMMARY.md
│   ├── api/              # API документация
│   │   ├── README.md
│   │   └── API_HDD_ENDPOINTS.md
│   └── ...
│
├── templates/             # HTML шаблоны
│   ├── base.html
│   ├── auth/
│   ├── tmc/
│   ├── news/
│   └── ...
│
├── static/                # Статические файлы
│   ├── css/              # CSS файлы
│   ├── js/               # JavaScript файлы
│   ├── fonts/            # Шрифты
│   ├── uploads/          # Загруженные файлы
│   └── ...
│
├── nginx/                 # Конфигурация Nginx
│
├── config/                # Конфигурационные файлы
│
├── instance/              # Экземпляр приложения (не в git)
└── venv/                  # Виртуальное окружение (не в git)
```

## Описание директорий

### `/migrations`
Все миграции базы данных. Каждая миграция должна быть идемпотентной.

**Запуск миграций:**
```bash
python3 migrations/migrate_name.py
```

### `/scripts`
Вспомогательные скрипты для:
- Загрузки статических файлов
- Тестирования
- Утилит
- Восстановления данных (`restore/`)

**Запуск скриптов:**
```bash
python3 scripts/script_name.py
python3 scripts/restore/restore_disks_simple.py
```

### `/docs`
Дополнительная документация проекта:
- Общая документация
- API документация (`api/`)
- Руководства по использованию

**Структура:**
- `api/` - Документация по API endpoints
- Общие документы проекта

### `/templates`
HTML шаблоны Flask. Организованы по модулям:
- `auth/` - Аутентификация
- `tmc/` - Управление ТМЦ
- `news/` - Новости
- `users/` - Пользователи
- и т.д.

### `/static`
Статические файлы:
- `css/` - Стили (Bootstrap, кастомные)
- `js/` - JavaScript (Bootstrap, Chart.js, TinyMCE)
- `fonts/` - Шрифты (Bootstrap Icons)
- `uploads/` - Загруженные пользователями файлы

### `/nginx`
Конфигурационные файлы для Nginx.

### `/config`
Конфигурационные файлы приложения.

## Основные файлы

- **`app.py`** - Главный файл приложения, содержит все маршруты
- **`models.py`** - SQLAlchemy модели базы данных
- **`requirements.txt`** - Список зависимостей Python

## Примечания

- Папки `instance/`, `venv/` и `__pycache__/` не должны попадать в систему контроля версий
- Все миграции находятся в одной папке для удобства управления
- Скрипты организованы отдельно от основного кода приложения
- Документация централизована в папке `docs/` с подпапками по категориям
- API документация находится в `docs/api/`
- Скрипты восстановления данных находятся в `scripts/restore/`

## Организация файлов

### Документация
- **`docs/`** - Общая документация проекта
- **`docs/api/`** - API документация (endpoints, примеры использования)
- **`docs/PROJECT_STRUCTURE.md`** - Структура проекта (этот файл)

### Скрипты
- **`scripts/`** - Основные вспомогательные скрипты
- **`scripts/restore/`** - Скрипты для восстановления данных через API

### Миграции
- **`migrations/`** - Все миграции базы данных (Python и SQL)

### Конфигурация
- **`nginx/`** - Конфигурация Nginx и SSL
- **`.env`** - Переменные окружения (не в git)

