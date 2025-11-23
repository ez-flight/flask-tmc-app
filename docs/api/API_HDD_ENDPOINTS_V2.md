# API v2 для сбора данных о компьютерах и жестких дисках

## Обзор

API v2 - расширенная версия API для сбора данных о жестких дисках, которая позволяет отправлять не только информацию о дисках, но и полную информацию о компьютере/машине, на которой эти диски установлены.

## Endpoint

```
POST /api/hdd_collect/v2
```

## Основные возможности

1. **Идентификация машины**: Уникальная идентификация компьютера по hostname
2. **Инвентаризация**: Полная информация о конфигурации ПК (ОС, железо, сеть)
3. **Отслеживание**: История изменений конфигурации и расположения дисков
4. **Автоматизация**: Полностью автоматический сбор данных без ручного ввода
5. **Связи**: Понятная связь между дисками и машинами

## Структура запроса

### Минимальный запрос (по hostname)

```json
{
  "machine": {
    "hostname": "PC-001"
  },
  "disks": [
    {
      "serial_number": "SN123456789",
      "model": "Samsung 980 PRO 1TB",
      "size_gb": 1000,
      "health_status": "Good"
    }
  ]
}
```

### Минимальный запрос (по MAC-адресу)

```json
{
  "machine": {
    "mac_address": "00:1B:44:11:3A:B7"
  },
  "disks": [
    {
      "serial_number": "SN123456789",
      "model": "Samsung 980 PRO 1TB",
      "size_gb": 1000,
      "health_status": "Good"
    }
  ]
}
```

### Минимальный запрос (только видеокарты)

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
    "ip_address": "10.3.3.42",
    "mac_address": "00:1B:44:11:3A:B7",
    "os": {
      "name": "Windows",
      "version": "10",
      "build": "19045",
      "edition": "Pro",
      "architecture": "x64"
    },
    "hardware": {
      "processor": "Intel Core i7-9700K CPU @ 3.60GHz",
      "memory_gb": 32,
      "motherboard": "ASUS PRIME B360M-A",
      "bios_version": "BIOS Date: 03/15/19 10:15:45 Ver: 05.0000C"
    },
    "network": {
      "domain": "WORKGROUP",
      "computer_role": "WORKSTATION",
      "dns_suffix": "local"
    }
  },
  "collection_info": {
    "timestamp": "2024-01-15T10:30:00Z",
    "collector_version": "1.2.0",
    "collector_type": "CrystalDiskInfo",
    "comment": "Плановый сбор данных. Проверка после замены HDD на SSD."
  },
  "disks": [
    {
      "serial_number": "S6P7NS0X639479A",
      "model": "Samsung SSD 970 EVO Plus 1TB",
      "size_gb": 976,
      "media_type": "NVMe",
      "manufacturer": "Samsung",
      "interface": "NVMe",
      "power_on_hours": 843,
      "power_on_count": 291,
      "health_status": "Good"
    },
    {
      "serial_number": "AA000000000000000480",
      "model": "XrayDisk 512GB SSD",
      "size_gb": 500,
      "media_type": "SSD",
      "interface": "SATA",
      "power_on_hours": 4462,
      "power_on_count": 1455,
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
    }
  ],
  "memory_modules": [
    {
      "capacity_gb": 8,
      "memory_type": "DDR4",
      "speed_mhz": 3200,
      "manufacturer": "Kingston",
      "part_number": "KVR32N22D8/8",
      "serial_number": "RAM-SN-001",
      "location": "DIMM0"
    },
    {
      "capacity_gb": 8,
      "memory_type": "DDR4",
      "speed_mhz": 3200,
      "manufacturer": "Kingston",
      "part_number": "KVR32N22D8/8",
      "serial_number": "RAM-SN-002",
      "location": "DIMM1"
    }
  ]
}
```

## Детальное описание полей

### Корневой объект

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `machine` | object | Да | Информация о компьютере/машине |
| `collection_info` | object | Нет | Метаданные о сборе данных |
| `disks` | array | Нет | Массив объектов с данными о дисках |
| `graphics_cards` | array | Нет | Массив объектов с данными о видеокартах |
| `memory_modules` | array | Нет | Массив объектов с данными о модулях ОЗУ |
| `confirm` | boolean | Нет | Подтверждение обновления данных (требуется при поиске машины по hostname) |

### Объект `machine`

#### Базовые поля

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `hostname` | string | Условно* | Имя компьютера (используется как идентификатор, если нет MAC-адреса) |
| `ip_address` | string | Нет | IP-адрес машины в локальной сети |
| `mac_address` | string | Условно* | MAC-адрес основного сетевого адаптера (приоритетный идентификатор) |

\* Требуется хотя бы один из полей: `hostname` или `mac_address`

#### Объект `os` (операционная система)

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `name` | string | Нет | Название ОС (Windows, Linux, macOS) |
| `version` | string | Нет | Версия ОС (10, 11, etc.) |
| `build` | string | Нет | Номер сборки ОС |
| `edition` | string | Нет | Издание ОС (Pro, Home, Enterprise) |
| `architecture` | string | Нет | Архитектура (x64, x86, ARM64) |

#### Объект `hardware` (аппаратное обеспечение)

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `processor` | string | Нет | Модель процессора (например, "Intel Core i7-9700K CPU @ 3.60GHz") |
| `memory_gb` | integer | Нет | Объем оперативной памяти (ОЗУ) в ГБ (например, 8, 16, 32) |
| `motherboard` | string | Нет | Модель материнской платы |
| `bios_version` | string | Нет | Версия BIOS/UEFI |

**Примечание:** Поле `memory_gb` указывает общий объем установленной оперативной памяти в гигабайтах. Например, если установлено 2 модуля по 8 ГБ, указывайте `16`.

#### Объект `network` (сетевая информация)

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `domain` | string | Нет | Домен или рабочая группа |
| `computer_role` | string | Нет | Роль компьютера (WORKSTATION, SERVER, DOMAIN_CONTROLLER) |
| `dns_suffix` | string | Нет | DNS суффикс |

### Объект `collection_info`

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `timestamp` | string (ISO 8601) | Нет | Время сбора данных в формате UTC |
| `collector_version` | string | Нет | Версия программы-сборщика |
| `collector_type` | string | Нет | Тип сборщика (CrystalDiskInfo, PowerShell, etc.) |
| `comment` | string | Нет | Комментарий пользователя |

### Объект `disks`

Структура массива дисков идентична API v1. См. [API_HDD_ENDPOINTS.md](API_HDD_ENDPOINTS.md) для детального описания.

### Объект `graphics_cards`

Массив объектов с данными о видеокартах. См. [API_GRAPHICS_CARDS.md](API_GRAPHICS_CARDS.md) для детального описания.

#### Основные поля

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `model` | string | Да | Модель видеокарты |
| `manufacturer` | string | Нет | Производитель (NVIDIA, AMD, Intel). Определяется автоматически, если не указан |
| `memory_size` | integer | Нет | Объем видеопамяти в МБ |
| `memory_type` | string | Нет | Тип памяти (GDDR5, GDDR6, GDDR6X, etc.) |
| `serial_number` | string | Нет | Серийный номер видеокарты |

### Объект `memory_modules`

Массив объектов с данными о модулях оперативной памяти (ОЗУ). Каждый объект представляет один физический модуль памяти.

#### Основные поля

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `capacity_gb` | integer | Да | Объем модуля в ГБ (например, 4, 8, 16, 32) |
| `memory_type` | string | Нет | Тип памяти (DDR, DDR2, DDR3, DDR4, DDR5) |
| `speed_mhz` | integer | Нет | Частота работы памяти в МГц (например, 1600, 2400, 3200) |
| `manufacturer` | string | Нет | Производитель модуля (например, Kingston, Corsair, Samsung) |
| `part_number` | string | Нет | Номер партии/модель модуля (например, "KVR32N22D8/8") |
| `serial_number` | string | Нет | Серийный номер модуля |
| `location` | string | Нет | Расположение слота (BankLabel или DeviceLocator, например, "DIMM0", "DIMM1", "ChannelA-DIMM0") |

**Примечание:** 
- Поле `capacity_gb` является обязательным для каждого модуля
- Модули идентифицируются по `serial_number` (приоритет) или по комбинации `location` + `machine_id`
- Если модуль найден, он обновляется; если не найден, создается новый
- Модули автоматически связываются с машиной через `machine_id`

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
    "processed": 3,
    "total": 3,
    "new": 1,
    "updated": 2
  },
  "graphics_cards": {
    "processed": 1,
    "total": 1,
    "new": 1,
    "updated": 0
  },
  "memory_modules": {
    "processed": 2,
    "total": 2,
    "new": 2,
    "updated": 0
  },
  "timestamp": "2024-01-15T10:30:15Z"
}
```

### Ответ с требованием подтверждения

Если машина найдена по `hostname` (а не по MAC-адресу), требуется подтверждение для обновления данных:

```json
{
  "success": false,
  "requires_confirmation": true,
  "machine": {
    "id": 42,
    "hostname": "PC-001",
    "current_hostname": "PC-001",
    "requested_hostname": "PC-001",
    "ip_address": "192.168.1.100",
    "mac_address": "00:1B:44:11:3A:B7"
  },
  "message": "Машина найдена по hostname \"PC-001\". Требуется подтверждение для записи данных. Отправьте запрос повторно с параметром \"confirm=true\" в JSON или query string для подтверждения обновления.",
  "timestamp": "2024-01-15T10:30:15Z"
}
```

Для подтверждения отправьте запрос повторно с параметром `confirm: true` в JSON или `?confirm=true` в URL.

### Ответ с ошибками

```json
{
  "success": false,
  "error": "Field \"machine.hostname\" is required",
  "timestamp": "2024-01-15T10:30:15Z"
}
```

## Логика работы

### Для машин

1. **Идентификация машины**: 
   - **Приоритет 1**: По полю `mac_address` (если указан)
   - **Приоритет 2**: По полю `hostname` (если MAC-адрес не указан или не найден)
   - Требуется хотя бы один из идентификаторов: `mac_address` или `hostname`

2. **Если найдена по MAC-адресу**:
   - Обновить поле `last_seen = текущее время`
   - Обновить все поля из запроса, если они изменились
   - **Обновление hostname**: 
     - Если hostname изменился, обновляется принудительно
     - Если новый hostname уже используется другой машиной, старый hostname освобождается (устанавливается `OLD-{hostname}-{id}`)
     - Это позволяет отслеживать изменения имени компьютера
   - Записать изменения в `machine_history`

3. **Если найдена по hostname**:
   - **Требуется подтверждение**: Если машина найдена по hostname (без MAC-адреса), требуется подтверждение для обновления данных
   - Отправьте запрос повторно с параметром `confirm: true` в JSON или `?confirm=true` в query string
   - Без подтверждения данные не обновляются, возвращается ответ с `requires_confirmation: true`
   - Обновляется только поле `last_seen` для отслеживания активности

4. **Если не найдена**:
   - Создать новую запись в таблице `machines`
   - Если нет hostname, но есть MAC-адрес, используется `MAC-{mac_address}` как hostname
   - Записать в `machine_history` событие "Machine created"

### Для дисков

1. **Связь с машиной**: При создании/обновлении диска устанавливать `machine_id`
2. **Идентификация**: По `serial_number` (как в v1)
3. **Обновление связей**: Если диск уже был привязан к другой машине, обновить связь
4. **История**: Создается запись в истории диска при каждом обновлении

### Для видеокарт

1. **Связь с машиной**: При создании/обновлении видеокарты устанавливать `machine_id`
2. **Идентификация**: 
   - По `serial_number` (приоритет)
   - По `model` + `machine_id` (если серийный номер не указан)
3. **Автоматическое определение производителя**: Если не указан, определяется по модели
4. **Автоматическая активация**: Деактивированные видеокарты активируются при обновлении

### Для модулей ОЗУ

1. **Связь с машиной**: При создании/обновлении модуля устанавливать `machine_id`
2. **Идентификация**: 
   - По `serial_number` (приоритет)
   - По `location` + `machine_id` (если серийный номер не указан)
3. **Обновление**: Если модуль найден, обновляются все поля из запроса
4. **Автоматическая активация**: Деактивированные модули активируются при обновлении

## Примеры использования

### cURL

```bash
curl -X POST http://localhost:5000/api/hdd_collect/v2 \
  -H "Content-Type: application/json" \
  -d '{
    "machine": {
      "hostname": "PC-001",
      "ip_address": "192.168.1.100"
    },
    "disks": [
      {
        "serial_number": "SN123",
        "model": "Samsung 980 PRO",
        "size_gb": 1000,
        "health_status": "Good"
      }
    ]
  }'
```

### Python

```python
import requests
import json

url = "http://localhost:5000/api/hdd_collect/v2"
data = {
    "machine": {
        "hostname": "PC-001",
        "mac_address": "00:1B:44:11:3A:B7",
        "ip_address": "192.168.1.100",
        "os": {
            "name": "Windows",
            "version": "10"
        },
        "hardware": {
            "processor": "Intel Core i7-9700K",
            "memory_gb": 16,
            "motherboard": "ASUS PRIME B360M-A"
        }
    },
    "disks": [
        {
            "serial_number": "SN123",
            "model": "Samsung 980 PRO",
            "size_gb": 1000,
            "health_status": "Good"
        }
    ],
    "memory_modules": [
        {
            "capacity_gb": 8,
            "memory_type": "DDR4",
            "speed_mhz": 3200,
            "manufacturer": "Kingston",
            "location": "DIMM0"
        }
    ],
    "confirm": True  # Подтверждение обновления (если требуется)
}

response = requests.post(url, json=data)
print(response.json())
```

### Python с подтверждением

Если получен ответ с `requires_confirmation: true`, отправьте запрос повторно с подтверждением:

```python
import requests

url = "http://localhost:5000/api/hdd_collect/v2"
data = {
    "machine": {
        "hostname": "PC-001"
    },
    "disks": [...]
}

# Первый запрос
response = requests.post(url, json=data)
result = response.json()

# Если требуется подтверждение
if result.get('requires_confirmation'):
    print("Требуется подтверждение. Отправляю запрос с подтверждением...")
    data['confirm'] = True
    response = requests.post(url, json=data)
    result = response.json()

print(result)
```

## Обратная совместимость

Старый endpoint `/api/hdd_collect` (v1) продолжает работать без изменений. Рекомендуется использовать новую версию для полной инвентаризации.

## Преимущества v2

1. **Полная инвентаризация**: Вся информация о ПК в одном запросе (ОС, железо, сеть, диски, видеокарты, ОЗУ)
2. **Отслеживание**: История изменений конфигурации машин
3. **Идентификация**: Уникальная идентификация машин по MAC-адресу (приоритет) или hostname
4. **Безопасность**: Требуется подтверждение при обновлении данных по hostname
5. **Связи**: Понятная связь между дисками, видеокартами, модулями ОЗУ и машинами
6. **Детальная информация об ОЗУ**: Учет каждого модуля памяти с полной информацией (тип, частота, производитель, расположение)
7. **Аналитика**: Возможность анализа по типам машин, ОС, конфигурациям, объемам памяти
8. **Расширяемость**: Легко добавлять новые поля без изменения структуры

## Миграция базы данных

Перед использованием API v2 необходимо применить миграцию:

```bash
python3 migrations/run_create_machines_tables.py
```

Миграция создаст:
- Таблицу `machines` для хранения информации о компьютерах
- Таблицу `machine_history` для истории изменений
- Добавит поле `machine_id` в таблицу `pc_hard_drives`
- Добавит поле `machine_id` в таблицу `pc_graphics_cards`
- Создаст таблицу `pc_memory_modules` для модулей ОЗУ

Для создания таблицы модулей ОЗУ выполните:
```bash
python3 migrations/run_create_memory_modules_table.py
```

## Примечания

- Требуется хотя бы одно из полей: `machine.hostname` или `machine.mac_address`
- **Идентификация машин**: 
  - Сначала по `mac_address` (приоритет, так как MAC-адрес реже меняется)
  - Если MAC-адрес не указан или машина не найдена по MAC, поиск по `hostname`
- **Обновление hostname**:
  - Если машина найдена по MAC-адресу, hostname обновляется принудительно, даже если он уже используется другой машиной
  - Старый hostname освобождается (устанавливается `OLD-{hostname}-{id}`)
  - Это позволяет отслеживать изменения имени компьютера
- **Подтверждение обновления**:
  - Если машина найдена по hostname (без MAC-адреса), требуется подтверждение для обновления данных
  - Отправьте запрос повторно с параметром `confirm: true` в JSON или `?confirm=true` в query string
  - Без подтверждения данные не обновляются, только обновляется `last_seen`
- При каждом обновлении машины записывается история изменений
- Диски автоматически связываются с машиной при создании/обновлении
- История дисков создается при каждом обновлении через API v2
- Видеокарты автоматически связываются с машиной при создании/обновлении
- Модули ОЗУ автоматически связываются с машиной при создании/обновлении
- MAC-адрес автоматически нормализуется (приводится к верхнему регистру)
- Подробнее о видеокартах см. [API_GRAPHICS_CARDS.md](API_GRAPHICS_CARDS.md)

