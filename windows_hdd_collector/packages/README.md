# Папка для локальных пакетов

Поместите сюда файлы пакетов для установки без интернета:

- `.whl` файлы (wheel packages) - предпочтительно
- `.tar.gz` файлы (source distributions)

## Как получить пакеты:

### На ПК с интернетом:

```bash
python download_packages.py
```

Или вручную:

```bash
pip download -r requirements.txt -d packages
```

### Ручное скачивание:

1. Перейдите на https://pypi.org/
2. Найдите нужный пакет
3. Скачайте `.whl` файл для вашей версии Python и Windows
4. Поместите в эту папку

## Структура:

```
packages/
  wmi-1.5.1-py3-none-any.whl
  psutil-5.9.0-cp39-cp39-win_amd64.whl
  requests-2.31.0-py3-none-any.whl
  pywin32-306-cp39-cp39-win_amd64.whl
```

## Установка:

После размещения файлов запустите:

```cmd
install_local.bat
```

Или обычный `install.bat` - он автоматически обнаружит локальные пакеты.

