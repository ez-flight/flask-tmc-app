# Исправление ошибки "400 Bad Request - The plain HTTP request was sent to HTTPS port"

## Проблема

При попытке доступа к `http://188.134.84.80:84/` возникает ошибка:
```
400 Bad Request
The plain HTTP request was sent to HTTPS port
```

## Причина

Ошибка возникает, когда внешний прокси пытается отправить HTTP запрос на HTTPS порт внутреннего сервера, или когда заголовки неправильно настроены.

## Решение

### Вариант 1: Обновить конфигурацию на внешнем сервере

На внешнем сервере (188.134.84.80) обновите файл `/etc/nginx/sites-available/flask-tmc-external`:

```nginx
server {
    listen 84;
    server_name 188.134.84.80;

    access_log /var/log/nginx/flask-tmc-external-access.log;
    error_log /var/log/nginx/flask-tmc-external-error.log;

    client_max_body_size 20M;

    location / {
        # ВАЖНО: Используем https:// для подключения к внутреннему серверу
        proxy_pass https://192.168.100.106:8443;
        
        # Заголовки
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;  # ВАЖНО: указываем https
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # SSL настройки
        proxy_ssl_verify off;  # Отключаем проверку SSL
        proxy_ssl_server_name on;
        proxy_ssl_name 192.168.100.106;
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Буферизация
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        
        # HTTP версия
        proxy_http_version 1.1;
    }
}
```

**Ключевые изменения:**
1. `proxy_pass https://192.168.100.106:8443;` - используем `https://`
2. `proxy_set_header X-Forwarded-Proto https;` - указываем HTTPS
3. `proxy_ssl_verify off;` - отключаем проверку SSL
4. `proxy_ssl_server_name on;` - включаем SNI

### Вариант 2: Использовать исправленный файл

```bash
# На внешнем сервере
sudo cp /home/flask_tmc_app/nginx/external_proxy_fixed.conf /etc/nginx/sites-available/flask-tmc-external

# Обновите IP адреса в конфигурации
sudo sed -i 's/server_name .*/server_name 188.134.84.80;/' /etc/nginx/sites-available/flask-tmc-external
sudo sed -i 's/listen .*/listen 84;/' /etc/nginx/sites-available/flask-tmc-external

# Проверьте и перезапустите
sudo nginx -t
sudo systemctl reload nginx
```

## Проверка

После обновления конфигурации:

```bash
# Проверка синтаксиса
sudo nginx -t

# Перезагрузка конфигурации
sudo systemctl reload nginx

# Проверка доступности
curl -I http://188.134.84.80:84

# Проверка логов
sudo tail -f /var/log/nginx/flask-tmc-external-error.log
```

## Альтернативное решение: Проксирование на HTTP порт

Если проблема сохраняется, можно проксировать на HTTP порт внутреннего сервера (8080) вместо HTTPS:

```nginx
location / {
    # Проксирование на HTTP порт
    proxy_pass http://192.168.100.106:8080;
    
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $server_name;
    proxy_set_header X-Forwarded-Port $server_port;
    
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

**Примечание:** Это менее безопасно, так как трафик между серверами будет незашифрованным.

## Диагностика

Если проблема сохраняется, проверьте:

1. **Доступность внутреннего сервера:**
```bash
curl -k https://192.168.100.106:8443
```

2. **Проверка портов:**
```bash
# На внешнем сервере
ss -tlnp | grep :84

# На внутреннем сервере
ss -tlnp | grep :8443
```

3. **Логи Nginx:**
```bash
sudo tail -50 /var/log/nginx/flask-tmc-external-error.log
```

4. **Проверка конфигурации:**
```bash
sudo nginx -T | grep -A 20 "location /"
```

## Дополнительная информация

- Убедитесь, что на внутреннем сервере Nginx слушает на порту 8443 с SSL
- Проверьте, что самоподписанный сертификат правильно настроен
- Убедитесь, что между серверами нет файрвола, блокирующего соединение

