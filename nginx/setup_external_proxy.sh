#!/bin/bash
# Скрипт для настройки внешнего прокси на сервере 188.134.84.80

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Настройка внешнего прокси для Flask TMC App ===${NC}"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите скрипт с правами root (sudo)"
    exit 1
fi

# Параметры
EXTERNAL_IP="188.134.84.80"
EXTERNAL_PORT="84"
INTERNAL_IP="192.168.100.106"
INTERNAL_PORT="8443"
PROXY_CONF="/home/flask_tmc_app/nginx/external_proxy.conf"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available/flask-tmc-external"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled/flask-tmc-external"

echo -e "${GREEN}Параметры проксирования:${NC}"
echo "  Внешний адрес: http://$EXTERNAL_IP:$EXTERNAL_PORT"
echo "  Внутренний адрес: https://$INTERNAL_IP:$INTERNAL_PORT"
echo ""

# Проверка установки Nginx
echo -e "${GREEN}Шаг 1: Проверка установки Nginx...${NC}"
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}Nginx не установлен. Устанавливаю...${NC}"
    apt-get update
    apt-get install -y nginx
else
    echo -e "${GREEN}Nginx уже установлен${NC}"
fi

# Проверка порта
echo -e "${GREEN}Шаг 2: Проверка порта $EXTERNAL_PORT...${NC}"
if ss -tlnp | grep -q ":$EXTERNAL_PORT "; then
    echo -e "${YELLOW}ВНИМАНИЕ: Порт $EXTERNAL_PORT уже занят!${NC}"
    echo "Процессы, использующие порт $EXTERNAL_PORT:"
    ss -tlnp | grep ":$EXTERNAL_PORT "
    echo ""
    read -p "Продолжить установку? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Установка отменена${NC}"
        exit 1
    fi
fi

# Копирование конфигурации
echo -e "${GREEN}Шаг 3: Копирование конфигурации прокси...${NC}"
if [ ! -f "$PROXY_CONF" ]; then
    echo -e "${RED}ОШИБКА: Файл конфигурации не найден: $PROXY_CONF${NC}"
    exit 1
fi

cp "$PROXY_CONF" "$NGINX_SITES_AVAILABLE"

# Обновление IP адресов в конфигурации
sed -i "s/server_name .*/server_name $EXTERNAL_IP;/" "$NGINX_SITES_AVAILABLE"
sed -i "s/listen .*/listen $EXTERNAL_PORT;/" "$NGINX_SITES_AVAILABLE"
sed -i "s|proxy_pass https://.*|proxy_pass https://$INTERNAL_IP:$INTERNAL_PORT;|" "$NGINX_SITES_AVAILABLE"

echo -e "${GREEN}Конфигурация скопирована и обновлена${NC}"

# Создание символической ссылки
echo -e "${GREEN}Шаг 4: Создание символической ссылки...${NC}"
ln -sf "$NGINX_SITES_AVAILABLE" "$NGINX_SITES_ENABLED"
echo -e "${GREEN}Символическая ссылка создана${NC}"

# Проверка конфигурации
echo -e "${GREEN}Шаг 5: Проверка конфигурации Nginx...${NC}"
if nginx -t; then
    echo -e "${GREEN}Конфигурация Nginx корректна${NC}"
else
    echo -e "${RED}ОШИБКА: Конфигурация Nginx содержит ошибки!${NC}"
    exit 1
fi

# Запуск Nginx
echo -e "${GREEN}Шаг 6: Перезапуск Nginx...${NC}"
systemctl restart nginx
systemctl enable nginx
echo -e "${GREEN}Nginx перезапущен${NC}"

echo ""
echo -e "${GREEN}=== Настройка завершена! ===${NC}"
echo ""
echo "Проксирование настроено:"
echo "  Внешний адрес: http://$EXTERNAL_IP:$EXTERNAL_PORT"
echo "  → Внутренний адрес: https://$INTERNAL_IP:$INTERNAL_PORT"
echo ""
echo "Проверка работы:"
echo "  curl -I http://$EXTERNAL_IP:$EXTERNAL_PORT"
echo ""
echo "Логи:"
echo "  sudo tail -f /var/log/nginx/flask-tmc-external-access.log"
echo "  sudo tail -f /var/log/nginx/flask-tmc-external-error.log"
echo ""

