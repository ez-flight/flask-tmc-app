# Настройка HTTPS с самоподписанным сертификатом

## Автоматическая установка (рекомендуется)

Скрипт `setup_nginx.sh` автоматически настроит HTTPS:

```bash
sudo /home/flask_tmc_app/nginx/setup_nginx.sh
```

Скрипт автоматически:
- Сгенерирует самоподписанный SSL сертификат (если его нет)
- Настроит Nginx для работы с HTTPS
- Настроит редирект с HTTP на HTTPS
- Запустит и включит Nginx в автозагрузку

## Ручная установка

### 1. Генерация SSL сертификата

```bash
sudo /home/flask_tmc_app/nginx/generate_ssl_cert.sh
```

Скрипт запросит:
- Доменное имя (или использует IP адрес по умолчанию)
- Создаст сертификат и приватный ключ в `/etc/nginx/ssl/`

### 2. Копирование HTTPS конфигурации

```bash
sudo cp /home/flask_tmc_app/nginx/flask-tmc-https.conf /etc/nginx/sites-available/flask-tmc
sudo ln -sf /etc/nginx/sites-available/flask-tmc /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
```

### 3. Обновление IP адреса в конфигурации (если нужно)

Отредактируйте `/etc/nginx/sites-available/flask-tmc`:

```nginx
server_name ваш_IP_или_домен;
```

### 4. Проверка и запуск

```bash
sudo nginx -t
sudo systemctl restart nginx
```

## Особенности самоподписанного сертификата

### Предупреждение в браузере

При первом посещении браузер покажет предупреждение о безопасности, так как сертификат не подписан доверенным центром сертификации.

**Это нормально для самоподписанных сертификатов!**

### Как принять сертификат в браузере

#### Chrome/Edge:
1. Нажмите "Дополнительно" или "Advanced"
2. Нажмите "Перейти на сайт (небезопасно)" или "Proceed to site (unsafe)"

#### Firefox:
1. Нажмите "Дополнительно" или "Advanced"
2. Нажмите "Принять риск и продолжить" или "Accept the Risk and Continue"

#### Safari:
1. Нажмите "Показать подробности" или "Show Details"
2. Нажмите "Посетить этот веб-сайт" или "Visit this Website"

### Для продакшена

Для продакшена рекомендуется использовать сертификаты от Let's Encrypt (бесплатные, автоматически обновляемые):

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Проверка работы HTTPS

### 1. Проверка сертификата

```bash
openssl x509 -in /etc/nginx/ssl/flask-tmc.crt -text -noout
```

### 2. Проверка подключения

```bash
openssl s_client -connect 192.168.100.106:443 -servername 192.168.100.106
```

### 3. Проверка в браузере

Откройте: `https://192.168.100.106`

Должен быть редирект с HTTP на HTTPS.

## Обновление сертификата

Сертификат действителен 365 дней. Для обновления:

```bash
sudo /home/flask_tmc_app/nginx/generate_ssl_cert.sh
sudo systemctl reload nginx
```

## Настройки безопасности в конфигурации

Конфигурация включает:

- **TLS 1.2 и TLS 1.3** - современные протоколы
- **HSTS** - принудительное использование HTTPS
- **Безопасные шифры** - только проверенные алгоритмы
- **Отключение старых протоколов** - SSLv2, SSLv3, TLS 1.0, TLS 1.1

## Устранение проблем

### Ошибка: "SSL certificate not found"

```bash
sudo /home/flask_tmc_app/nginx/generate_ssl_cert.sh
```

### Ошибка: "bind() to 0.0.0.0:443 failed"

Проверьте, что порт 443 свободен:

```bash
sudo ss -tlnp | grep :443
```

### Браузер не принимает сертификат

1. Убедитесь, что сертификат содержит правильный IP/домен
2. Проверьте, что дата на сервере корректна
3. Очистите кэш браузера

### Редирект не работает

Проверьте конфигурацию:

```bash
sudo nginx -t
sudo tail -f /var/log/nginx/flask-tmc-error.log
```

## Файлы

- **Сертификат**: `/etc/nginx/ssl/flask-tmc.crt`
- **Приватный ключ**: `/etc/nginx/ssl/flask-tmc.key`
- **Конфигурация**: `/etc/nginx/sites-available/flask-tmc`
- **Логи**: `/var/log/nginx/flask-tmc-*.log`

