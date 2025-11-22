@echo off
REM Скрипт для установки зависимостей ТОЛЬКО из локальных файлов
echo ========================================
echo Windows HDD Collector - Локальная установка
echo ========================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    pause
    exit /b 1
)

REM Проверяем наличие папки packages
if not exist "packages\" (
    echo [ОШИБКА] Папка packages\ не найдена!
    echo.
    echo Создайте папку packages\ и поместите туда файлы пакетов:
    echo   - .whl файлы (wheel)
    echo   - .tar.gz файлы (source distribution)
    echo.
    echo Пример структуры:
    echo   packages\
    echo     wmi-1.5.1-py3-none-any.whl
    echo     psutil-5.9.0-cp39-cp39-win_amd64.whl
    echo     requests-2.31.0-py3-none-any.whl
    echo     pywin32-306-cp39-cp39-win_amd64.whl
    echo.
    pause
    exit /b 1
)

echo [OK] Папка packages\ найдена
echo.

REM Устанавливаем все пакеты из папки packages
echo Установка пакетов из локальных файлов...
echo.

for %%f in (packages\*.whl) do (
    if exist "%%f" (
        echo [Установка] %%f
        pip install "%%f" --no-deps --force-reinstall
        if errorlevel 1 (
            echo [ОШИБКА] Не удалось установить %%f
        )
    )
)

for %%f in (packages\*.tar.gz) do (
    if exist "%%f" (
        echo [Установка] %%f
        pip install "%%f" --no-deps --force-reinstall
        if errorlevel 1 (
            echo [ОШИБКА] Не удалось установить %%f
        )
    )
)

REM Теперь устанавливаем зависимости из requirements.txt с использованием локальных пакетов
if exist "requirements.txt" (
    echo.
    echo Установка зависимостей из requirements.txt...
    pip install -r requirements.txt --no-index --find-links packages --no-deps
    if errorlevel 1 (
        echo [ПРЕДУПРЕЖДЕНИЕ] Некоторые зависимости не найдены локально
        echo Попробуйте установить их вручную или добавьте в packages\
    )
)

echo.
echo ========================================
echo Локальная установка завершена!
echo ========================================
echo.
pause

