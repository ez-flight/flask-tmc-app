@echo off
REM Скрипт установки зависимостей для Windows HDD Collector
REM Поддерживает установку из локальных файлов (папка packages/)
echo ========================================
echo Windows HDD Collector - Установка
echo ========================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo.
    echo Установите Python 3.7+ с https://www.python.org/
    echo Убедитесь, что Python добавлен в PATH
    echo.
    pause
    exit /b 1
)

echo [OK] Python найден
python --version
echo.

REM Проверяем наличие локальных пакетов
if exist "packages\" (
    echo [INFO] Найдена папка packages с локальными пакетами
    echo Установка из локальных файлов...
    echo.
    
    REM Устанавливаем из локальных файлов
    for %%f in (packages\*.whl packages\*.tar.gz packages\*.zip) do (
        if exist "%%f" (
            echo Установка: %%f
            pip install "%%f" --no-index --find-links packages
        )
    )
    
    REM Устанавливаем остальные из requirements.txt, используя локальные пакеты если доступны
    if exist "requirements.txt" (
        echo.
        echo Установка зависимостей из requirements.txt...
        pip install -r requirements.txt --no-index --find-links packages
        if errorlevel 1 (
            echo [ПРЕДУПРЕЖДЕНИЕ] Не все пакеты найдены локально, пробуем из интернета...
            pip install -r requirements.txt
        )
    )
) else (
    echo Установка библиотек из интернета...
    echo.
    
    if exist "requirements.txt" (
        pip install -r requirements.txt
    ) else (
        echo [ОШИБКА] Файл requirements.txt не найден!
        pause
        exit /b 1
    )
)

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось установить зависимости
    echo Попробуйте:
    echo   1. Запустить от имени администратора
    echo   2. Добавить локальные пакеты в папку packages\
    echo   3. Проверить подключение к интернету
    pause
    exit /b 1
)

echo.
echo ========================================
echo Установка завершена успешно!
echo ========================================
echo.
echo Для использования запустите:
echo   python hdd_collector.py --host ^<IP_СЕРВЕРА^> --port 5000
echo.
echo Пример:
echo   python hdd_collector.py --host 192.168.1.100 --port 5000
echo.
echo Для установки из локальных файлов:
echo   1. Создайте папку packages\
echo   2. Поместите .whl или .tar.gz файлы в packages\
echo   3. Запустите install.bat
echo.
pause
