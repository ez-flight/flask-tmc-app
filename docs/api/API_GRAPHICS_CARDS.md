# API для видеокарт в API v2

## Обзор

API v2 поддерживает сбор информации о видеокартах вместе с данными о компьютерах и жестких дисках. Видеокарты автоматически связываются с машинами через поле `machine_id`.

## Endpoint

```
POST /api/hdd_collect/v2
```

## Структура запроса для видеокарт

### Объект `graphics_cards`

Массив объектов с данными о видеокартах. Добавляется в корневой объект запроса API v2.

```json
{
  "machine": {
    "hostname": "PC-001",
    "mac_address": "00:1B:44:11:3A:B7"
  },
  "disks": [...],
  "graphics_cards": [
    {
      "model": "NVIDIA GeForce RTX 3060",
      "manufacturer": "NVIDIA",
      "memory_size": 12288,
      "memory_type": "GDDR6",
      "serial_number": "SN123456789"
    }
  ]
}
```

## Детальное описание полей

### Объект `graphics_cards` (элемент массива)

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `model` | string | Да | Модель видеокарты (например, "NVIDIA GeForce RTX 3060") |
| `manufacturer` | string | Нет | Производитель (NVIDIA, AMD, Intel). Если не указан, определяется автоматически по модели |
| `memory_size` | integer | Нет | Объем видеопамяти в МБ |
| `memory_type` | string | Нет | Тип памяти (GDDR5, GDDR6, GDDR6X, etc.) |
| `serial_number` | string | Нет | Серийный номер видеокарты |

## Автоматическое определение производителя

Если поле `manufacturer` не указано, система автоматически определяет производителя по модели:

- **NVIDIA**: если в модели есть "NVIDIA", "GEFORCE", "RTX", "GTX"
- **AMD**: если в модели есть "AMD", "RADEON", "RX"
- **Intel**: если в модели есть "INTEL"
- **Unknown**: в остальных случаях

## Логика обработки

### Идентификация видеокарты

1. **По серийному номеру** (приоритет): если указан `serial_number`, поиск выполняется по этому полю
2. **По модели + машине**: если серийный номер не указан или видеокарта не найдена, поиск выполняется по комбинации `model` + `machine_id`

### Создание новой видеокарты

- Если видеокарта не найдена, создается новая запись
- Автоматически создается производитель в справочнике, если его нет
- Видеокарта связывается с машиной через `machine_id`
- Комментарий автоматически заполняется: "Автоматически добавлена с {hostname} через API v2"

### Обновление существующей видеокарты

- Обновляются поля: `memory_size`, `memory_type`, `serial_number`
- Обновляется производитель, если изменился
- Обновляется связь с машиной (`machine_id`)
- Обновляется комментарий: "Последний раз обнаружена на {hostname}"
- Видеокарта автоматически активируется, если была деактивирована

## Примеры запросов

### Минимальный запрос

```json
{
  "machine": {
    "hostname": "PC-001"
  },
  "graphics_cards": [
    {
      "model": "NVIDIA GeForce RTX 3060"
    }
  ]
}
```

### Полный запрос

```json
{
  "machine": {
    "hostname": "WORKSTATION-05",
    "mac_address": "00:1B:44:11:3A:B7",
    "ip_address": "10.3.3.42"
  },
  "disks": [
    {
      "serial_number": "SN123456789",
      "model": "Samsung 980 PRO 1TB",
      "size_gb": 1000,
      "health_status": "Good"
    }
  ],
  "graphics_cards": [
    {
      "model": "NVIDIA GeForce RTX 3060",
      "manufacturer": "NVIDIA",
      "memory_size": 12288,
      "memory_type": "GDDR6",
      "serial_number": "GPU-SN-123456"
    },
    {
      "model": "AMD Radeon RX 6700 XT",
      "manufacturer": "AMD",
      "memory_size": 12288,
      "memory_type": "GDDR6",
      "serial_number": "GPU-SN-789012"
    }
  ]
}
```

## Формат ответа

### Успешный ответ

```json
{
  "success": true,
  "machine": {
    "id": 42,
    "hostname": "PC-001",
    "status": "updated",
    "message": "Machine information updated"
  },
  "disks": {
    "processed": 2,
    "total": 2,
    "new": 1,
    "updated": 1
  },
  "graphics_cards": {
    "processed": 2,
    "total": 2,
    "new": 1,
    "updated": 1
  },
  "timestamp": "2024-01-15T10:30:15Z"
}
```

### Ответ с ошибками

```json
{
  "success": true,
  "machine": {...},
  "disks": {...},
  "graphics_cards": {
    "processed": 1,
    "total": 2,
    "new": 1,
    "updated": 0,
    "error_count": 1,
    "errors": [
      "Graphics card Model XYZ: could not create vendor for Unknown"
    ]
  },
  "timestamp": "2024-01-15T10:30:15Z"
}
```

## Примеры использования

### cURL

```bash
curl -X POST http://localhost:5000/api/hdd_collect/v2 \
  -H "Content-Type: application/json" \
  -d '{
    "machine": {
      "hostname": "PC-001",
      "mac_address": "00:1B:44:11:3A:B7"
    },
    "graphics_cards": [
      {
        "model": "NVIDIA GeForce RTX 3060",
        "memory_size": 12288,
        "memory_type": "GDDR6"
      }
    ]
  }'
```

### Python

```python
import requests

url = "http://localhost:5000/api/hdd_collect/v2"
data = {
    "machine": {
        "hostname": "PC-001",
        "mac_address": "00:1B:44:11:3A:B7"
    },
    "graphics_cards": [
        {
            "model": "NVIDIA GeForce RTX 3060",
            "manufacturer": "NVIDIA",
            "memory_size": 12288,
            "memory_type": "GDDR6",
            "serial_number": "GPU-SN-123456"
        }
    ]
}

response = requests.post(url, json=data)
print(response.json())
```

## Миграция базы данных

Перед использованием API v2 для видеокарт необходимо применить миграцию:

```bash
mysql -u root -p webuseorg3 < migrations/add_machine_id_to_graphics_cards.sql
```

Или через Python скрипт:

```bash
cd /home/flask_tmc_app
source venv/bin/activate
python3 migrations/run_add_machine_id_to_graphics_cards.py
```

Миграция добавит:
- Колонку `machine_id` в таблицу `pc_graphics_cards`
- Внешний ключ для связи с таблицей `machines`
- Индекс для оптимизации запросов

## Примечания

- Поле `model` является обязательным для видеокарт
- Производитель определяется автоматически, если не указан явно
- Видеокарты автоматически связываются с машиной при создании/обновлении
- Видеокарты, найденные по серийному номеру, обновляются независимо от машины
- Видеокарты без серийного номера идентифицируются по модели + машине
- Деактивированные видеокарты автоматически активируются при обновлении через API

