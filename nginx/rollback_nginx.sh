#!/bin/bash
# Скрипт для отката всех изменений Nginx и возврата к исходной конфигурации

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Откат изменений Nginx ===${NC}"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите скрипт с правами root (sudo)"
    exit 1
fi

echo -e "${YELLOW}Этот скрипт:${NC}"
echo "  1. Остановит и отключит Nginx"
echo "  2. Удалит конфигурации Nginx"
echo "  3. Оставит SSL сертификаты (на случай, если понадобятся)"
echo ""

read -p "Продолжить откат? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Откат отменен${NC}"
    exit 0
fi

# Остановка Nginx
echo -e "${GREEN}Шаг 1: Остановка Nginx...${NC}"
systemctl stop nginx 2>/dev/null || true
systemctl disable nginx 2>/dev/null || true
echo -e "${GREEN}Nginx остановлен${NC}"

# Удаление конфигураций
echo -e "${GREEN}Шаг 2: Удаление конфигураций Nginx...${NC}"
rm -f /etc/nginx/sites-enabled/flask-tmc
rm -f /etc/nginx/sites-available/flask-tmc
rm -f /etc/nginx/sites-enabled/flask-tmc-external
rm -f /etc/nginx/sites-available/flask-tmc-external
echo -e "${GREEN}Конфигурации удалены${NC}"

# Удаление systemd service для Flask (опционально)
echo -e "${GREEN}Шаг 3: Проверка systemd service для Flask...${NC}"
if [ -f "/etc/systemd/system/flask-tmc.service" ]; then
    read -p "Удалить systemd service для Flask? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl stop flask-tmc 2>/dev/null || true
        systemctl disable flask-tmc 2>/dev/null || true
        rm -f /etc/systemd/system/flask-tmc.service
        systemctl daemon-reload
        echo -e "${GREEN}Systemd service удален${NC}"
    else
        echo -e "${YELLOW}Systemd service оставлен${NC}"
    fi
else
    echo -e "${GREEN}Systemd service не найден${NC}"
fi

# Удаление Nginx (опционально)
echo -e "${GREEN}Шаг 4: Удаление Nginx...${NC}"
read -p "Полностью удалить Nginx? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    apt-get remove --purge -y nginx nginx-common 2>/dev/null || true
    apt-get autoremove -y 2>/dev/null || true
    echo -e "${GREEN}Nginx удален${NC}"
else
    echo -e "${YELLOW}Nginx оставлен установленным${NC}"
fi

# SSL сертификаты оставляем (на случай, если понадобятся)
echo -e "${GREEN}Шаг 5: SSL сертификаты...${NC}"
if [ -d "/etc/nginx/ssl" ]; then
    echo -e "${YELLOW}SSL сертификаты сохранены в /etc/nginx/ssl${NC}"
    echo "   (Вы можете удалить их вручную, если не нужны)"
fi

echo ""
echo -e "${GREEN}=== Откат завершен! ===${NC}"
echo ""
echo "Теперь Flask приложение можно запустить напрямую:"
echo "  cd /home/flask_tmc_app"
echo "  source venv/bin/activate"
echo "  python3 app.py"
echo ""
echo "Или через Gunicorn:"
echo "  gunicorn -w 4 -b 0.0.0.0:5000 app:app"
echo ""
echo "Приложение будет доступно по адресу: http://192.168.100.106:5000"
echo ""

