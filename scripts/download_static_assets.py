#!/usr/bin/env python3
"""
Скрипт для скачивания всех внешних CSS и JS файлов в локальную папку static.
Запустите этот скрипт один раз для загрузки всех необходимых файлов.
"""

import os
import subprocess
import sys
from pathlib import Path

# Создаем необходимые директории
# Переходим на уровень выше, так как скрипт находится в scripts/
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "static"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"
FONTS_DIR = STATIC_DIR / "fonts"

for directory in [CSS_DIR, JS_DIR, FONTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Список файлов для скачивания
files_to_download = [
    {
        "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
        "path": CSS_DIR / "bootstrap.min.css"
    },
    {
        "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
        "path": JS_DIR / "bootstrap.bundle.min.js"
    },
    {
        "url": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css",
        "path": CSS_DIR / "bootstrap-icons.css"
    },
    {
        "url": "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js",
        "path": JS_DIR / "chart.umd.min.js"
    },
    {
        "url": "https://download.tiny.cloud/tinymce/community/tinymce_6.8.3/tinymce.min.js",
        "path": JS_DIR / "tinymce.min.js"
    }
]

# Bootstrap Icons шрифты
bootstrap_icons_fonts = [
    "bootstrap-icons.woff",
    "bootstrap-icons.woff2"
]

def download_file(url, path):
    """Загружает файл используя wget или curl"""
    # Проверяем переменные окружения для прокси
    proxy_env = {}
    for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
        if key in os.environ:
            proxy_env[key] = os.environ[key]
    
    # Пробуем wget
    try:
        cmd = ['wget', '-O', str(path), url]
        # Добавляем прокси, если есть
        if 'https_proxy' in proxy_env or 'HTTPS_PROXY' in proxy_env:
            proxy = proxy_env.get('https_proxy') or proxy_env.get('HTTPS_PROXY')
            cmd.extend(['--proxy', 'on'])
            if proxy:
                os.environ['https_proxy'] = proxy
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, **proxy_env}
        )
        if result.returncode == 0:
            return True
        elif result.stderr:
            print(f"   wget ошибка: {result.stderr[:100]}")
    except subprocess.TimeoutExpired:
        print(f"   Превышено время ожидания")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"   wget исключение: {e}")
    
    # Пробуем curl
    try:
        cmd = ['curl', '-L', '-o', str(path), url]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, **proxy_env}
        )
        if result.returncode == 0:
            return True
        elif result.stderr:
            print(f"   curl ошибка: {result.stderr[:100]}")
    except subprocess.TimeoutExpired:
        print(f"   Превышено время ожидания")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"   curl исключение: {e}")
    
    # Пробуем urllib как запасной вариант
    try:
        import urllib.request
        # Настраиваем прокси для urllib
        if proxy_env:
            proxy_handler = urllib.request.ProxyHandler({
                'http': proxy_env.get('http_proxy') or proxy_env.get('HTTP_PROXY', ''),
                'https': proxy_env.get('https_proxy') or proxy_env.get('HTTPS_PROXY', '')
            })
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)
        urllib.request.urlretrieve(url, path)
        return True
    except Exception as e:
        print(f"   urllib ошибка: {e}")
    
    return False

# Диагностика сети
print("Проверка сетевого подключения...")
try:
    result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                           capture_output=True, timeout=5)
    if result.returncode == 0:
        print("✓ Ping работает")
    else:
        print("⚠ Ping не работает")
except Exception:
    print("⚠ Не удалось проверить ping")

# Проверяем прокси
proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
found_proxy = [var for var in proxy_vars if var in os.environ]
if found_proxy:
    print(f"✓ Найдены настройки прокси: {', '.join(found_proxy)}")
else:
    print("ℹ Прокси не настроен")

print("\nНачинаю загрузку файлов...")

for file_info in files_to_download:
    url = file_info["url"]
    path = file_info["path"]
    
    print(f"Загружаю {path.name}...")
    if download_file(url, path):
        print(f"✓ Успешно загружен: {path.name}")
    else:
        print(f"✗ Ошибка при загрузке {path.name}")

# Загружаем шрифты Bootstrap Icons
print("\nЗагружаю шрифты Bootstrap Icons...")
for font_name in bootstrap_icons_fonts:
    font_url = f"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/fonts/{font_name}"
    font_path = FONTS_DIR / font_name
    print(f"Загружаю {font_name}...")
    if download_file(font_url, font_path):
        print(f"✓ Успешно загружен: {font_name}")
    else:
        print(f"✗ Ошибка при загрузке {font_name}")

# Исправляем пути к шрифтам в bootstrap-icons.css
print("\nИсправляю пути к шрифтам в bootstrap-icons.css...")
bootstrap_icons_css_path = CSS_DIR / "bootstrap-icons.css"
if bootstrap_icons_css_path.exists():
    with open(bootstrap_icons_css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()
    
    # Заменяем пути к шрифтам на локальные
    css_content = css_content.replace(
        "url(./fonts/",
        "url(../fonts/"
    )
    
    with open(bootstrap_icons_css_path, 'w', encoding='utf-8') as f:
        f.write(css_content)
    print("✓ Пути к шрифтам исправлены")

print("\nГотово! Все файлы загружены в папку static/")

