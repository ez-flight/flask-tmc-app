#!/bin/bash
# Скрипт для установки и настройки Nginx для Flask TMC App

set -e

echo "=== Настройка Nginx для Flask TMC App ==="

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите скрипт с правами root (sudo)"
    exit 1
fi

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Пути
APP_DIR="/home/flask_tmc_app"
NGINX_CONF="$APP_DIR/nginx/flask-tmc.conf"
NGINX_HTTPS_CONF="$APP_DIR/nginx/flask-tmc-https.conf"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available/flask-tmc"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled/flask-tmc"
SERVICE_FILE="$APP_DIR/nginx/flask-tmc.service"
SYSTEMD_SERVICE="/etc/systemd/system/flask-tmc.service"
SSL_DIR="/etc/nginx/ssl"
SSL_CERT="$SSL_DIR/flask-tmc.crt"
SSL_KEY="$SSL_DIR/flask-tmc.key"
SSL_GEN_SCRIPT="$APP_DIR/nginx/generate_ssl_cert.sh"

echo -e "${GREEN}Шаг 1: Проверка установки Nginx...${NC}"
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}Nginx не установлен. Устанавливаю...${NC}"
    apt-get update
    apt-get install -y nginx
else
    echo -e "${GREEN}Nginx уже установлен${NC}"
fi

echo -e "${GREEN}Шаг 2: Проверка порта 80...${NC}"
PORT_80_OCCUPIED=false
ALTERNATIVE_HTTP_PORT=8080
ALTERNATIVE_HTTPS_PORT=8443

if ss -tlnp | grep -q ":80 "; then
    PORT_80_OCCUPIED=true
    echo -e "${YELLOW}ВНИМАНИЕ: Порт 80 уже занят!${NC}"
    echo "Процессы, использующие порт 80:"
    ss -tlnp | grep ":80 "
    echo ""
    read -p "Остановить Apache и использовать Nginx на порту 80? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Останавливаю Apache...${NC}"
        systemctl stop apache2 2>/dev/null || true
        systemctl disable apache2 2>/dev/null || true
        echo -e "${GREEN}Apache остановлен${NC}"
        PORT_80_OCCUPIED=false
    else
        echo -e "${YELLOW}Используйте порт $ALTERNATIVE_HTTP_PORT для HTTP и $ALTERNATIVE_HTTPS_PORT для HTTPS${NC}"
        sed -i 's/listen 80;/listen 8080;/' "$NGINX_CONF"
    fi
fi

echo -e "${GREEN}Шаг 3: Настройка SSL сертификатов...${NC}"
if [ ! -f "$SSL_CERT" ] || [ ! -f "$SSL_KEY" ]; then
    echo -e "${YELLOW}SSL сертификаты не найдены. Генерирую...${NC}"
    if [ -f "$SSL_GEN_SCRIPT" ]; then
        bash "$SSL_GEN_SCRIPT"
    else
        echo -e "${RED}Скрипт генерации сертификата не найден!${NC}"
        echo "Запустите вручную: sudo $SSL_GEN_SCRIPT"
        exit 1
    fi
else
    echo -e "${GREEN}SSL сертификаты уже существуют${NC}"
fi

echo -e "${GREEN}Шаг 4: Копирование конфигурации Nginx (HTTPS)...${NC}"
if [ -f "$NGINX_HTTPS_CONF" ]; then
    cp "$NGINX_HTTPS_CONF" "$NGINX_SITES_AVAILABLE"
    echo -e "${GREEN}HTTPS конфигурация скопирована${NC}"
    
    # Если порт 80 занят, изменяем порты в HTTPS конфигурации
    if [ "$PORT_80_OCCUPIED" = true ]; then
        echo -e "${YELLOW}Изменяю порты в конфигурации: HTTP -> $ALTERNATIVE_HTTP_PORT, HTTPS -> $ALTERNATIVE_HTTPS_PORT${NC}"
        sed -i "s/listen 80;/listen $ALTERNATIVE_HTTP_PORT;/" "$NGINX_SITES_AVAILABLE"
        sed -i "s/listen 443 ssl http2;/listen $ALTERNATIVE_HTTPS_PORT ssl http2;/" "$NGINX_SITES_AVAILABLE"
        echo -e "${GREEN}Порты изменены${NC}"
    fi
else
    echo -e "${YELLOW}HTTPS конфигурация не найдена, используем HTTP...${NC}"
    cp "$NGINX_CONF" "$NGINX_SITES_AVAILABLE"
    echo -e "${GREEN}HTTP конфигурация скопирована${NC}"
fi

echo -e "${GREEN}Шаг 5: Создание символической ссылки...${NC}"
ln -sf "$NGINX_SITES_AVAILABLE" "$NGINX_SITES_ENABLED"
echo -e "${GREEN}Символическая ссылка создана${NC}"

echo -e "${GREEN}Шаг 6: Удаление дефолтной конфигурации...${NC}"
rm -f /etc/nginx/sites-enabled/default
echo -e "${GREEN}Дефолтная конфигурация удалена${NC}"

echo -e "${GREEN}Шаг 7: Проверка конфигурации Nginx...${NC}"
if nginx -t; then
    echo -e "${GREEN}Конфигурация Nginx корректна${NC}"
else
    echo -e "${RED}ОШИБКА: Конфигурация Nginx содержит ошибки!${NC}"
    exit 1
fi

echo -e "${GREEN}Шаг 8: Создание директории для логов...${NC}"
mkdir -p /var/log/flask-tmc
chown flaskuser:flaskuser /var/log/flask-tmc 2>/dev/null || chown $USER:$USER /var/log/flask-tmc

echo -e "${GREEN}Шаг 9: Проверка установки Gunicorn...${NC}"
if [ ! -f "$APP_DIR/venv/bin/gunicorn" ]; then
    echo -e "${YELLOW}Gunicorn не установлен. Устанавливаю...${NC}"
    cd "$APP_DIR"
    source venv/bin/activate
    pip install gunicorn
    deactivate
    echo -e "${GREEN}Gunicorn установлен${NC}"
else
    echo -e "${GREEN}Gunicorn уже установлен${NC}"
fi

echo -e "${GREEN}Шаг 10: Настройка systemd service...${NC}"
cp "$SERVICE_FILE" "$SYSTEMD_SERVICE"
systemctl daemon-reload
echo -e "${GREEN}Systemd service настроен${NC}"

echo -e "${GREEN}Шаг 11: Запуск Nginx...${NC}"
systemctl restart nginx
systemctl enable nginx
echo -e "${GREEN}Nginx запущен и включен в автозагрузку${NC}"

echo ""
echo -e "${GREEN}=== Настройка завершена! ===${NC}"
echo ""
echo "Следующие шаги:"
echo "1. Запустите Flask приложение через Gunicorn:"
echo "   sudo systemctl start flask-tmc"
echo "   sudo systemctl enable flask-tmc"
echo ""
echo "2. Или запустите вручную:"
echo "   cd $APP_DIR"
echo "   source venv/bin/activate"
echo "   gunicorn -w 4 -b 127.0.0.1:5000 app:app"
echo ""
echo "3. Проверьте статус:"
echo "   sudo systemctl status nginx"
echo "   sudo systemctl status flask-tmc"
echo ""
if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
    if [ "$PORT_80_OCCUPIED" = true ]; then
        echo "4. Откройте в браузере: https://192.168.100.106:$ALTERNATIVE_HTTPS_PORT"
        echo "   (Браузер покажет предупреждение о самоподписанном сертификате - это нормально)"
        echo "   HTTP редирект работает на порту $ALTERNATIVE_HTTP_PORT"
    else
        echo "4. Откройте в браузере: https://192.168.100.106"
        echo "   (Браузер покажет предупреждение о самоподписанном сертификате - это нормально)"
    fi
else
    if [ "$PORT_80_OCCUPIED" = true ]; then
        echo "4. Откройте в браузере: http://192.168.100.106:$ALTERNATIVE_HTTP_PORT"
    else
        echo "4. Откройте в браузере: http://192.168.100.106"
    fi
fi
echo ""

