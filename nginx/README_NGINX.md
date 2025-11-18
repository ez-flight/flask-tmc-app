# Настройка Nginx для Flask TMC App

## Текущая ситуация

Порт 80 занят Apache. Есть два варианта:

### Вариант 1: Остановить Apache и использовать только Nginx (рекомендуется)

```bash
# Остановить Apache
sudo systemctl stop apache2
sudo systemctl disable apache2

# Установить конфигурацию Nginx
sudo cp /home/flask_tmc_app/nginx/flask-tmc.conf /etc/nginx/sites-available/flask-tmc
sudo ln -sf /etc/nginx/sites-available/flask-tmc /etc/nginx/sites-enabled/

# Удалить дефолтную конфигурацию (если есть)
sudo rm -f /etc/nginx/sites-enabled/default

# Проверить конфигурацию
sudo nginx -t

# Запустить Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Вариант 2: Использовать Nginx на другом порту (например, 8080)

Если нужно оставить Apache, измените в конфигурации:

```nginx
listen 8080;
```

И обновите конфигурацию:

```bash
sudo cp /home/flask_tmc_app/nginx/flask-tmc.conf /etc/nginx/sites-available/flask-tmc
# Отредактируйте порт в файле
sudo nano /etc/nginx/sites-available/flask-tmc
sudo ln -sf /etc/nginx/sites-available/flask-tmc /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Запуск Flask приложения

### Вариант 1: Встроенный сервер Flask (для разработки)

```bash
cd /home/flask_tmc_app
source venv/bin/activate
python3 app.py
```

### Вариант 2: Gunicorn (для продакшена - рекомендуется)

```bash
# Установить Gunicorn
cd /home/flask_tmc_app
source venv/bin/activate
pip install gunicorn

# Запустить Gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

### Вариант 3: Systemd service для Gunicorn

Создайте файл `/etc/systemd/system/flask-tmc.service`:

```ini
[Unit]
Description=Flask TMC App Gunicorn daemon
After=network.target

[Service]
User=flaskuser
Group=flaskuser
WorkingDirectory=/home/flask_tmc_app
Environment="PATH=/home/flask_tmc_app/venv/bin"
ExecStart=/home/flask_tmc_app/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app

Restart=always

[Install]
WantedBy=multi-user.target
```

Активация:

```bash
sudo systemctl daemon-reload
sudo systemctl start flask-tmc
sudo systemctl enable flask-tmc
```

## Проверка работы

1. Проверьте статус Nginx:
```bash
sudo systemctl status nginx
```

2. Проверьте логи:
```bash
sudo tail -f /var/log/nginx/flask-tmc-access.log
sudo tail -f /var/log/nginx/flask-tmc-error.log
```

3. Откройте в браузере: `http://192.168.100.106` (или `http://192.168.100.106:8080` если используете порт 8080)

## Настройка файрвола (если используется UFW)

```bash
sudo ufw allow 'Nginx Full'
# или для конкретного порта
sudo ufw allow 80/tcp
sudo ufw allow 8080/tcp  # если используете порт 8080
```

## Обновление конфигурации

После изменения конфигурации:

```bash
sudo nginx -t  # Проверка синтаксиса
sudo systemctl reload nginx  # Перезагрузка без остановки
# или
sudo systemctl restart nginx  # Полный перезапуск
```

