# Windows HDD Collector

Скрипт для автоматического сбора информации о жестких дисках на Windows ПК и отправки данных на сервер Flask по TCP/IP.

## Возможности

- ✅ Сбор информации о всех физических дисках через WMI
- ✅ Получение S.M.A.R.T. данных (требует smartmontools)
- ✅ Автоматическая отправка данных на сервер
- ✅ Сохранение данных в JSON файл
- ✅ Поддержка конфигурационных файлов
- ✅ Автоматическое определение производителя и типа диска

## Требования

- Windows 7/8/10/11
- Python 3.7 или выше
- Права администратора (для доступа к WMI)

## Установка

### Вариант 1: Установка из интернета

#### 1. Клонируйте или скачайте проект

```bash
git clone <repository_url>
cd windows_hdd_collector
```

#### 2. Установите зависимости

```bash
pip install -r requirements.txt
```

Или используйте скрипт установки:

```cmd
install.bat
```

### Вариант 2: Установка из локальных файлов (без интернета)

#### 1. На ПК с интернетом - скачайте пакеты

```bash
python download_packages.py
```

Это создаст папку `packages/` с файлами `.whl` и `.tar.gz`

#### 2. Скопируйте папку `packages/` на целевой ПК

Скопируйте всю папку `windows_hdd_collector` включая `packages/` на ПК без интернета

#### 3. Установите из локальных файлов

```cmd
install_local.bat
```

Или используйте обычный `install.bat` - он автоматически обнаружит папку `packages/` и использует локальные файлы

#### 4. Структура папки packages

```
packages/
  wmi-1.5.1-py3-none-any.whl
  psutil-5.9.0-cp39-cp39-win_amd64.whl
  requests-2.31.0-py3-none-any.whl
  pywin32-306-cp39-cp39-win_amd64.whl
```

**Примечание:** Для скачивания пакетов со всеми зависимостями используйте:
```bash
python download_packages.py --with-deps
```

### 3. (Опционально) Установите smartmontools

Для получения S.M.A.R.T. данных установите [smartmontools](https://www.smartmontools.org/):
- Скачайте установщик с официального сайта
- Установите и добавьте в PATH

## Использование

### Базовое использование

```bash
python hdd_collector.py --host 192.168.1.100 --port 5000
```

### Параметры командной строки

- `--host` - IP адрес или доменное имя сервера (по умолчанию: localhost)
- `--port` - Порт сервера (по умолчанию: 5000)
- `--save` - Сохранить данные в JSON файл перед отправкой
- `--config` - Путь к файлу конфигурации

### Примеры

```bash
# Отправка на удаленный сервер
python hdd_collector.py --host 192.168.1.100 --port 5000

# Сохранение данных в файл
python hdd_collector.py --host 192.168.1.100 --save hdd_data.json

# Использование конфигурационного файла
python hdd_collector.py --config config.json
```

## Конфигурационный файл

Создайте файл `config.json`:

```json
{
  "host": "192.168.1.100",
  "port": 5000
}
```

Затем запустите:

```bash
python hdd_collector.py --config config.json
```

## Собираемая информация

Для каждого жесткого диска собирается:

- **Модель** - модель диска
- **Серийный номер** - уникальный серийный номер
- **Объем** - объем диска в ГБ
- **Производитель** - производитель диска
- **Интерфейс** - тип интерфейса (SATA, SAS, NVMe)
- **Тип** - тип диска (HDD, SSD, SAS)
- **Наработка (часы)** - количество часов работы (если доступно)
- **Количество включений** - число включений (если доступно)
- **Здоровье** - статус здоровья диска (если доступно)

## Автоматизация

### Планировщик задач Windows

1. Откройте "Планировщик задач" (Task Scheduler)
2. Создайте новую задачу
3. Настройте триггер (например, ежедневно в 9:00)
4. В действии укажите:
   - **Программа:** `python.exe`
   - **Аргументы:** `C:\path\to\hdd_collector.py --host 192.168.1.100`
   - **Рабочая папка:** `C:\path\to\windows_hdd_collector`
5. В настройках безопасности выберите "Запускать с наивысшими правами"

### Пример задачи для ежедневного запуска

```xml
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2025-01-01T09:00:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>python.exe</Command>
      <Arguments>C:\path\to\hdd_collector.py --host 192.168.1.100</Arguments>
      <WorkingDirectory>C:\path\to\windows_hdd_collector</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

## API Endpoint

Сервер должен иметь endpoint: `POST http://<server>:<port>/api/hdd_collect`

### Формат отправляемых данных

```json
{
  "hostname": "PC-NAME",
  "timestamp": "2025-11-22T15:30:00",
  "platform": "Windows-10-10.0.19041-SP0",
  "disks": [
    {
      "model": "WD5003ABYX",
      "serial_number": "WMAYP3205431",
      "size_gb": 500,
      "manufacturer": "Western Digital",
      "interface": "SATA",
      "media_type": "Fixed hard disk media",
      "power_on_hours": 37554,
      "power_on_count": 3059,
      "health_status": "Здоров"
    }
  ]
}
```

## Устранение неполадок

### Ошибка подключения к серверу

- Проверьте, что сервер запущен и доступен
- Проверьте настройки firewall
- Убедитесь, что указан правильный IP и порт
- Проверьте сетевое подключение: `ping <server_ip>`

### Ошибка получения данных о дисках

- Убедитесь, что скрипт запущен от имени администратора
- Проверьте установку pywin32: `pip install pywin32`
- Проверьте доступность WMI: `wmic diskdrive list brief`

### S.M.A.R.T. данные не собираются

- Установите smartmontools
- Убедитесь, что smartctl доступен в PATH
- Проверьте вручную: `smartctl -a \\.\PhysicalDrive0`

### Ошибка импорта модулей

```bash
pip install --upgrade -r requirements.txt
```

## Лицензия

MIT License

## Автор

Создано для системы учета ТМЦ Flask TMC App

