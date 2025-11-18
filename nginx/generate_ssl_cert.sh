#!/bin/bash
# Скрипт для генерации самоподписанного SSL сертификата

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Пути
SSL_DIR="/etc/nginx/ssl"
CERT_FILE="$SSL_DIR/flask-tmc.crt"
KEY_FILE="$SSL_DIR/flask-tmc.key"

echo -e "${GREEN}=== Генерация самоподписанного SSL сертификата ===${NC}"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите скрипт с правами root (sudo)"
    exit 1
fi

# Создание директории для сертификатов
echo -e "${GREEN}Создание директории для сертификатов...${NC}"
mkdir -p "$SSL_DIR"
chmod 700 "$SSL_DIR"

# Получение IP адреса сервера
SERVER_IP=$(hostname -I | awk '{print $1}')
if [ -z "$SERVER_IP" ]; then
    SERVER_IP=$(ip addr show | grep -oP 'inet \K[\d.]+' | grep -v '127.0.0.1' | head -1)
fi

# Запрос доменного имени (опционально)
echo -e "${YELLOW}Введите доменное имя (или нажмите Enter для использования IP: $SERVER_IP):${NC}"
read -r DOMAIN_NAME

if [ -z "$DOMAIN_NAME" ]; then
    DOMAIN_NAME="$SERVER_IP"
    SUBJECT_ALT_NAME="IP:$SERVER_IP"
else
    SUBJECT_ALT_NAME="DNS:$DOMAIN_NAME,DNS:www.$DOMAIN_NAME,IP:$SERVER_IP"
fi

echo -e "${GREEN}Генерация приватного ключа...${NC}"
openssl genrsa -out "$KEY_FILE" 2048
chmod 600 "$KEY_FILE"

echo -e "${GREEN}Генерация самоподписанного сертификата...${NC}"
openssl req -new -x509 -key "$KEY_FILE" -out "$CERT_FILE" -days 365 \
    -subj "/C=RU/ST=State/L=City/O=Organization/CN=$DOMAIN_NAME" \
    -addext "subjectAltName=$SUBJECT_ALT_NAME"

chmod 644 "$CERT_FILE"

echo ""
echo -e "${GREEN}=== Сертификат успешно создан! ===${NC}"
echo "Сертификат: $CERT_FILE"
echo "Приватный ключ: $KEY_FILE"
echo "Действителен: 365 дней"
echo ""
echo -e "${YELLOW}ВНИМАНИЕ: Это самоподписанный сертификат.${NC}"
echo "Браузеры будут показывать предупреждение о безопасности."
echo "Для продакшена рекомендуется использовать сертификаты от Let's Encrypt."
echo ""

