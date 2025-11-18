# Настройка внешнего прокси для Flask TMC App

## Описание

Настройка проксирования с внешнего сервера `188.134.84.80:84` на внутренний сервер `192.168.100.106:8443`.

## Вариант 1: Автоматическая установка (рекомендуется)

На внешнем сервере (188.134.84.80) выполните:

```bash
# Скопируйте файлы на внешний сервер
scp /home/flask_tmc_app/nginx/external_proxy.conf root@188.134.84.80:/tmp/
scp /home/flask_tmc_app/nginx/setup_external_proxy.sh root@188.134.84.80:/tmp/

# На внешнем сервере
ssh root@188.134.84.80
chmod +x /tmp/setup_external_proxy.sh
/tmp/setup_external_proxy.sh
```

## Вариант 2: Ручная установка

### 1. Создайте конфигурацию на внешнем сервере

Создайте файл `/etc/nginx/sites-available/flask-tmc-external`:

```nginx
server {
    listen 84;
    server_name 188.134.84.80;

    access_log /var/log/nginx/flask-tmc-external-access.log;
    error_log /var/log/nginx/flask-tmc-external-error.log;

    client_max_body_size 20M;

    location / {
        proxy_pass https://192.168.100.106:8443;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Отключение проверки SSL (для самоподписанного сертификата)
        proxy_ssl_verify off;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. Активируйте конфигурацию

```bash
sudo ln -sf /etc/nginx/sites-available/flask-tmc-external /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Вариант 3: Использование Apache (если Apache уже установлен)

Если на внешнем сервере используется Apache, можно настроить проксирование через Apache:

### 1. Включите необходимые модули

```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod ssl
sudo a2enmod headers
```

### 2. Создайте виртуальный хост

Создайте файл `/etc/apache2/sites-available/flask-tmc-external.conf`:

```apache
<VirtualHost *:84>
    ServerName 188.134.84.80
    
    ProxyPreserveHost On
    ProxyRequests Off
    
    # Проксирование на внутренний сервер
    ProxyPass / https://192.168.100.106:8443/
    ProxyPassReverse / https://192.168.100.106:8443/
    
    # Отключение проверки SSL
    SSLProxyEngine on
    SSLProxyVerify none
    SSLProxyCheckPeerCN off
    SSLProxyCheckPeerName off
    
    # Заголовки
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "84"
    
    # Логирование
    ErrorLog ${APACHE_LOG_DIR}/flask-tmc-external-error.log
    CustomLog ${APACHE_LOG_DIR}/flask-tmc-external-access.log combined
</VirtualHost>
```

### 3. Активируйте конфигурацию

```bash
sudo a2ensite flask-tmc-external
sudo systemctl restart apache2
```

## Проверка работы

### 1. Проверка доступности

```bash
curl -I http://188.134.84.80:84
```

### 2. Проверка логов

**Nginx:**
```bash
sudo tail -f /var/log/nginx/flask-tmc-external-access.log
sudo tail -f /var/log/nginx/flask-tmc-external-error.log
```

**Apache:**
```bash
sudo tail -f /var/log/apache2/flask-tmc-external-access.log
sudo tail -f /var/log/apache2/flask-tmc-external-error.log
```

### 3. Проверка статуса

**Nginx:**
```bash
sudo systemctl status nginx
```

**Apache:**
```bash
sudo systemctl status apache2
```

## Настройка файрвола

Убедитесь, что порт 84 открыт в файрволе:

```bash
# UFW
sudo ufw allow 84/tcp

# iptables
sudo iptables -A INPUT -p tcp --dport 84 -j ACCEPT
```

## Устранение проблем

### Ошибка: "502 Bad Gateway"

1. Проверьте доступность внутреннего сервера:
```bash
curl -k https://192.168.100.106:8443
```

2. Проверьте, что Flask приложение запущено:
```bash
ssh user@192.168.100.106
sudo systemctl status flask-tmc
```

3. Проверьте логи:
```bash
sudo tail -f /var/log/nginx/flask-tmc-external-error.log
```

### Ошибка: "SSL certificate problem"

Это нормально для самоподписанных сертификатов. Убедитесь, что в конфигурации есть:
```nginx
proxy_ssl_verify off;
```

### Ошибка: "Connection refused"

1. Проверьте, что порт 8443 открыт на внутреннем сервере
2. Проверьте сетевую связность между серверами:
```bash
ping 192.168.100.106
telnet 192.168.100.106 8443
```

## Безопасность

### Рекомендации:

1. **Ограничьте доступ по IP** (если возможно):
```nginx
location / {
    allow 192.168.0.0/16;  # Только внутренняя сеть
    deny all;
    proxy_pass https://192.168.100.106:8443;
    # ...
}
```

2. **Используйте базовую аутентификацию** (опционально):
```nginx
location / {
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass https://192.168.100.106:8443;
    # ...
}
```

3. **Настройте rate limiting**:
```nginx
limit_req_zone $binary_remote_addr zone=flask_limit:10m rate=10r/s;

location / {
    limit_req zone=flask_limit burst=20;
    proxy_pass https://192.168.100.106:8443;
    # ...
}
```

## Обновление конфигурации

После изменения конфигурации:

```bash
# Nginx
sudo nginx -t
sudo systemctl reload nginx

# Apache
sudo apache2ctl configtest
sudo systemctl reload apache2
```

