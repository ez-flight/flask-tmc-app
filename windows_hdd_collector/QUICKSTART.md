# Быстрый старт

## 1. Установка

### С интернетом:

```cmd
install.bat
```

### Без интернета (из локальных файлов):

1. На ПК с интернетом скачайте пакеты:
   ```cmd
   python download_packages.py
   ```

2. Скопируйте папку `packages/` на целевой ПК

3. Установите:
   ```cmd
   install_local.bat
   ```

## 2. Настройка

Создайте файл `config.json` на основе `config.example.json`:

```json
{
  "host": "192.168.1.100",
  "port": 5000
}
```

## 3. Запуск

```cmd
python hdd_collector.py --host 192.168.1.100 --port 5000
```

Или с использованием конфига:

```cmd
python hdd_collector.py --config config.json
```

## 4. Автоматизация

Настройте Планировщик задач Windows для ежедневного запуска.

Подробности в [README.md](README.md)

