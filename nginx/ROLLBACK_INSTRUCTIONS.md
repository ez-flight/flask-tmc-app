# Инструкция по откату изменений Nginx

## Быстрый откат

Выполните скрипт отката:

```bash
sudo /home/flask_tmc_app/nginx/rollback_nginx.sh
```

Скрипт автоматически:
- Остановит и отключит Nginx
- Удалит все конфигурации Nginx
- Опционально удалит Nginx полностью
- Опционально удалит systemd service для Flask

## Ручной откат

### 1. Остановить Nginx

```bash
sudo systemctl stop nginx
sudo systemctl disable nginx
```

### 2. Удалить конфигурации

```bash
sudo rm -f /etc/nginx/sites-enabled/flask-tmc
sudo rm -f /etc/nginx/sites-available/flask-tmc
sudo rm -f /etc/nginx/sites-enabled/flask-tmc-external
sudo rm -f /etc/nginx/sites-available/flask-tmc-external
```

### 3. Удалить systemd service (если был создан)

```bash
sudo systemctl stop flask-tmc
sudo systemctl disable flask-tmc
sudo rm -f /etc/systemd/system/flask-tmc.service
sudo systemctl daemon-reload
```

### 4. Удалить Nginx (опционально)

```bash
sudo apt-get remove --purge nginx nginx-common
sudo apt-get autoremove
```

## Запуск Flask приложения напрямую

После отката Nginx, Flask приложение можно запустить напрямую:

### Вариант 1: Встроенный сервер Flask (для разработки)

```bash
cd /home/flask_tmc_app
source venv/bin/activate
python3 app.py
```

Приложение будет доступно по адресу: `http://192.168.100.106:5000`

### Вариант 2: Gunicorn (для продакшена)

```bash
cd /home/flask_tmc_app
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Вариант 3: Gunicorn с systemd service (без Nginx)

Если хотите использовать systemd service без Nginx, создайте файл `/etc/systemd/system/flask-tmc.service`:

```ini
[Unit]
Description=Flask TMC App Gunicorn daemon
After=network.target mysql.service

[Service]
User=flaskuser
Group=flaskuser
WorkingDirectory=/home/flask_tmc_app
Environment="PATH=/home/flask_tmc_app/venv/bin"
Environment="FLASK_ENV=production"
ExecStart=/home/flask_tmc_app/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 --access-logfile /var/log/flask-tmc/access.log --error-logfile /var/log/flask-tmc/error.log app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:

```bash
sudo systemctl daemon-reload
sudo systemctl start flask-tmc
sudo systemctl enable flask-tmc
```

## Проверка работы

```bash
# Проверка статуса Flask приложения
sudo systemctl status flask-tmc

# Проверка доступности
curl http://192.168.100.106:5000

# Логи
sudo tail -f /var/log/flask-tmc/access.log
sudo tail -f /var/log/flask-tmc/error.log
```

## Настройка файрвола

Убедитесь, что порт 5000 открыт:

```bash
sudo ufw allow 5000/tcp
```

## Восстановление Apache (если был)

Если Apache был остановлен, его можно запустить обратно:

```bash
sudo systemctl start apache2
sudo systemctl enable apache2
```

## Удаление SSL сертификатов (опционально)

Если SSL сертификаты больше не нужны:

```bash
sudo rm -rf /etc/nginx/ssl
```

