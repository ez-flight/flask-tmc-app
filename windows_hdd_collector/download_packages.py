#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для скачивания пакетов для локальной установки
Использование: python download_packages.py
"""
import os
import subprocess
import sys

def download_packages():
    """Скачивает пакеты в папку packages/"""
    
    # Создаем папку packages если её нет
    packages_dir = "packages"
    if not os.path.exists(packages_dir):
        os.makedirs(packages_dir)
        print(f"Создана папка {packages_dir}/")
    
    # Читаем requirements.txt
    if not os.path.exists("requirements.txt"):
        print("Ошибка: файл requirements.txt не найден!")
        return False
    
    print("Скачивание пакетов в папку packages/...")
    print("=" * 60)
    
    try:
        # Скачиваем пакеты без установки
        result = subprocess.run(
            [sys.executable, "-m", "pip", "download", 
             "-r", "requirements.txt", 
             "-d", packages_dir,
             "--platform", "win_amd64",  # Для 64-bit Windows
             "--only-binary", ":all:"],  # Только бинарные пакеты
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ Пакеты успешно скачаны!")
            print(f"\nФайлы сохранены в: {os.path.abspath(packages_dir)}")
            
            # Показываем список скачанных файлов
            files = [f for f in os.listdir(packages_dir) if f.endswith(('.whl', '.tar.gz', '.zip'))]
            if files:
                print(f"\nСкачано файлов: {len(files)}")
                for f in files:
                    size = os.path.getsize(os.path.join(packages_dir, f))
                    print(f"  - {f} ({size / 1024 / 1024:.2f} MB)")
            
            return True
        else:
            print("✗ Ошибка при скачивании пакетов:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


def download_with_deps():
    """Скачивает пакеты со всеми зависимостями"""
    
    packages_dir = "packages"
    if not os.path.exists(packages_dir):
        os.makedirs(packages_dir)
    
    print("Скачивание пакетов со всеми зависимостями...")
    print("=" * 60)
    
    try:
        # Скачиваем пакеты с зависимостями
        result = subprocess.run(
            [sys.executable, "-m", "pip", "download", 
             "-r", "requirements.txt", 
             "-d", packages_dir],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ Пакеты и зависимости успешно скачаны!")
            return True
        else:
            print("✗ Ошибка при скачивании:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Скачивание пакетов для локальной установки')
    parser.add_argument('--with-deps', action='store_true', 
                       help='Скачать также все зависимости')
    
    args = parser.parse_args()
    
    if args.with_deps:
        success = download_with_deps()
    else:
        success = download_packages()
    
    if success:
        print("\n" + "=" * 60)
        print("Теперь вы можете:")
        print("  1. Скопировать папку packages/ на ПК без интернета")
        print("  2. Запустить install.bat или install_local.bat")
        print("=" * 60)
    else:
        sys.exit(1)

