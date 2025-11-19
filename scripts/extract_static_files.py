#!/usr/bin/env python3
"""
Скрипт для распаковки и установки статических файлов из папки static_downloads.
Поместите все скачанные файлы в папку static_downloads/ и запустите этот скрипт.
"""

import os
import shutil
from pathlib import Path

# Создаем необходимые директории
# Переходим на уровень выше, так как скрипт находится в scripts/
BASE_DIR = Path(__file__).parent.parent
DOWNLOAD_DIR = BASE_DIR / "static_downloads"
STATIC_DIR = BASE_DIR / "static"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"
FONTS_DIR = STATIC_DIR / "fonts"

# Создаем структуру директорий
for directory in [CSS_DIR, JS_DIR, FONTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Маппинг файлов: имя_файла -> целевая_директория
files_mapping = {
    # CSS файлы
    "bootstrap.min.css": CSS_DIR,
    "bootstrap-icons.css": CSS_DIR,
    
    # JavaScript файлы
    "bootstrap.bundle.min.js": JS_DIR,
    "chart.umd.min.js": JS_DIR,
    "tinymce.min.js": JS_DIR,
    
    # Шрифты
    "bootstrap-icons.woff": FONTS_DIR,
    "bootstrap-icons.woff2": FONTS_DIR,
}

print("Проверяю наличие файлов в static_downloads/...\n")

# Проверяем наличие папки static_downloads
if not DOWNLOAD_DIR.exists():
    print(f"❌ Папка {DOWNLOAD_DIR} не найдена!")
    print(f"   Создайте папку и поместите туда все скачанные файлы.")
    exit(1)

# Список файлов для обработки
found_files = []
missing_files = []

for filename, target_dir in files_mapping.items():
    source_path = DOWNLOAD_DIR / filename
    target_path = target_dir / filename
    
    if source_path.exists():
        found_files.append((filename, source_path, target_path))
        print(f"✓ Найден: {filename}")
    else:
        missing_files.append(filename)
        print(f"✗ Отсутствует: {filename}")

print()

if missing_files:
    print(f"⚠ Внимание: не найдено {len(missing_files)} файл(ов):")
    for filename in missing_files:
        print(f"   - {filename}")
    print("\nПродолжить с имеющимися файлами? (y/n): ", end="")
    response = input().strip().lower()
    if response != 'y':
        print("Отменено.")
        exit(0)

if not found_files:
    print("❌ Не найдено ни одного файла для установки!")
    print(f"   Поместите файлы в папку {DOWNLOAD_DIR}")
    exit(1)

print(f"\nНачинаю копирование {len(found_files)} файл(ов)...\n")

# Копируем файлы
success_count = 0
for filename, source_path, target_path in found_files:
    try:
        shutil.copy2(source_path, target_path)
        print(f"✓ Установлен: {filename} -> {target_path.relative_to(BASE_DIR)}")
        success_count += 1
    except Exception as e:
        print(f"✗ Ошибка при копировании {filename}: {e}")

# Исправляем пути к шрифтам в bootstrap-icons.css
print("\nИсправляю пути к шрифтам в bootstrap-icons.css...")
bootstrap_icons_css_path = CSS_DIR / "bootstrap-icons.css"
if bootstrap_icons_css_path.exists():
    try:
        with open(bootstrap_icons_css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Заменяем пути к шрифтам на локальные
        import re
        original_content = css_content
        # Заменяем все варианты путей: url(./fonts/, url('./fonts/, url("./fonts/
        # Включая пути с query параметрами (например, ?1bb88866b4085542c8ed5fb61b9393dd)
        css_content = re.sub(r'url\(["\']?\./fonts/', r'url("../fonts/', css_content)
        
        if css_content != original_content:
            with open(bootstrap_icons_css_path, 'w', encoding='utf-8') as f:
                f.write(css_content)
            print("✓ Пути к шрифтам исправлены")
        else:
            print("ℹ Пути к шрифтам уже корректны или не требуют исправления")
    except Exception as e:
        print(f"⚠ Не удалось исправить пути к шрифтам: {e}")

print(f"\n{'='*50}")
print(f"Готово! Установлено {success_count} из {len(found_files)} файл(ов)")
print(f"{'='*50}")

if missing_files:
    print(f"\n⚠ Не забудьте скачать и установить отсутствующие файлы:")
    for filename in missing_files:
        print(f"   - {filename}")

