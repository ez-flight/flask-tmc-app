# Быстрый старт: Настройка Nginx с HTTPS

## Автоматическая установка (рекомендуется)

```bash
sudo /home/flask_tmc_app/nginx/setup_nginx.sh
```

Скрипт автоматически:
- Установит Nginx (если не установлен)
- Сгенерирует самоподписанный SSL сертификат
- Настроит HTTPS конфигурацию с редиректом HTTP → HTTPS
- Проверит и решит конфликт с Apache (если порт 80 занят)
- Создаст systemd service для Flask приложения
- Запустит и включит Nginx в автозагрузку

## Ручная установка

### 1. Генерация SSL сертификата

```bash
sudo /home/flask_tmc_app/nginx/generate_ssl_cert.sh
```

### 2. Скопировать HTTPS конфигурацию

```bash
sudo cp /home/flask_tmc_app/nginx/flask-tmc-https.conf /etc/nginx/sites-available/flask-tmc
sudo ln -sf /etc/nginx/sites-available/flask-tmc /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
```

### 3. Проверить конфигурацию

```bash
sudo nginx -t
```

### 4. Решить конфликт с Apache (если порт 80 занят)

**Вариант A: Остановить Apache**
```bash
sudo systemctl stop apache2
sudo systemctl disable apache2
```

**Вариант B: Использовать другой порт**
Отредактируйте `/etc/nginx/sites-available/flask-tmc`:
```nginx
listen 8080;  # вместо listen 80;
```

### 5. Запустить Nginx

```bash
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 6. Установить Gunicorn (для продакшена)

```bash
cd /home/flask_tmc_app
source venv/bin/activate
pip install gunicorn
```

### 7. Настроить systemd service для Flask

```bash
sudo cp /home/flask_tmc_app/nginx/flask-tmc.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start flask-tmc
sudo systemctl enable flask-tmc
```

## Проверка работы

```bash
# Статус Nginx
sudo systemctl status nginx

# Статус Flask приложения
sudo systemctl status flask-tmc

# Логи Nginx
sudo tail -f /var/log/nginx/flask-tmc-access.log
sudo tail -f /var/log/nginx/flask-tmc-error.log

# Логи Flask
sudo tail -f /var/log/flask-tmc/access.log
sudo tail -f /var/log/flask-tmc/error.log
```

## Доступ к приложению

Откройте в браузере: `https://192.168.100.106`

**Важно:** Браузер покажет предупреждение о самоподписанном сертификате. Это нормально - нажмите "Дополнительно" → "Перейти на сайт (небезопасно)" для продолжения.

HTTP запросы автоматически перенаправляются на HTTPS.

## Полезные команды

```bash
# Перезагрузить конфигурацию Nginx без остановки
sudo systemctl reload nginx

# Перезапустить Nginx
sudo systemctl restart nginx

# Перезапустить Flask приложение
sudo systemctl restart flask-tmc

# Проверить синтаксис конфигурации
sudo nginx -t
```

