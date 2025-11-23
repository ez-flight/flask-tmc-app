# Реорганизация проекта - 2025

## Обзор изменений

Проект был реорганизован для улучшения структуры и удобства навигации. Однотипные файлы были рассортированы по соответствующим папкам.

## Изменения структуры

### Документация

**Было:**
```
flask_tmc_app/
├── API_HDD_ENDPOINTS.md
├── PROJECT_STRUCTURE.md
└── README.md
```

**Стало:**
```
flask_tmc_app/
├── README.md (основной)
└── docs/
    ├── PROJECT_STRUCTURE.md
    ├── api/
    │   ├── README.md
    │   └── API_HDD_ENDPOINTS.md
    └── ... (другая документация)
```

### Скрипты восстановления

**Было:**
```
flask_tmc_app/
├── restore_disks_simple.py
├── restore_disks.py
├── restore_disks.json
└── restore_disks.sh
```

**Стало:**
```
flask_tmc_app/
└── scripts/
    └── restore/
        ├── README.md
        ├── restore_disks_simple.py
        ├── restore_disks.py
        ├── restore_disks.json
        └── restore_disks.sh
```

## Новые папки

### `docs/api/`
- Содержит документацию по API endpoints
- `API_HDD_ENDPOINTS.md` - полная документация по API для жестких дисков
- `README.md` - описание содержимого папки

### `scripts/restore/`
- Содержит скрипты для восстановления данных через API
- Все скрипты восстановления дисков
- `README.md` - инструкции по использованию

## Обновленные файлы

### `README.md`
- Обновлены ссылки на документацию
- Добавлена информация о новой структуре

### `docs/PROJECT_STRUCTURE.md`
- Обновлена структура проекта
- Добавлены описания новых папок
- Обновлены пути к файлам

## Преимущества реорганизации

1. **Лучшая организация** - однотипные файлы сгруппированы по папкам
2. **Удобная навигация** - легче найти нужные файлы
3. **Масштабируемость** - проще добавлять новые файлы в соответствующие папки
4. **Чистота корня проекта** - в корне остались только основные файлы приложения

## Миграция

Если вы использовали старые пути к файлам, обновите их:

### Документация
- `API_HDD_ENDPOINTS.md` → `docs/api/API_HDD_ENDPOINTS.md`
- `PROJECT_STRUCTURE.md` → `docs/PROJECT_STRUCTURE.md`

### Скрипты восстановления
- `restore_disks_simple.py` → `scripts/restore/restore_disks_simple.py`
- `restore_disks.py` → `scripts/restore/restore_disks.py`
- `restore_disks.json` → `scripts/restore/restore_disks.json`
- `restore_disks.sh` → `scripts/restore/restore_disks.sh`

## Дата реорганизации

2025-11-23

