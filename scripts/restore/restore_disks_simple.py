#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для восстановления удаленных жестких дисков через API
Использует встроенный urllib вместо requests
"""

import urllib.request
import urllib.parse
import json

# URL API endpoint
API_URL = "http://localhost:5000/api/hdd_collect"

# Данные для восстановления
disks_data = {
    "hostname": "PC-Restore",
    "disks": [
        {
            "serial_number": "S6P7NS0X639479A",
            "model": "Samsung SSD 970 EVO Plus 1TB",
            "size_gb": 0,
            "media_type": "NVMe",
            "manufacturer": "Samsung",
            "interface": "NVMe",
            "power_on_hours": 842,
            "power_on_count": 291,
            "health_status": "Good"
        },
        {
            "serial_number": "AA000000000000000480",
            "model": "XrayDisk 512GB SSD",
            "size_gb": 0,
            "media_type": "SSD",
            "interface": "SATA",
            "power_on_hours": 4462,
            "power_on_count": 1455,
            "health_status": "Good"
        }
    ]
}

def restore_disks():
    """Восстанавливает диски через API"""
    print("Восстановление дисков через API...")
    print(f"URL: {API_URL}")
    print(f"Количество дисков: {len(disks_data['disks'])}")
    print("")
    
    try:
        # Подготовка данных
        data = json.dumps(disks_data).encode('utf-8')
        
        # Создание запроса
        req = urllib.request.Request(
            API_URL,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        # Отправка запроса
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            print("Результат:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("")
            
            if result.get('new', 0) > 0:
                print(f"✓ Успешно создано новых дисков: {result['new']}")
            if result.get('updated', 0) > 0:
                print(f"✓ Обновлено существующих дисков: {result['updated']}")
            if result.get('error_count', 0) > 0:
                print(f"⚠ Ошибок: {result['error_count']}")
                if 'errors' in result:
                    for error in result['errors']:
                        print(f"  - {error}")
            
            return result
            
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP ошибка: {e.code} - {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            print(f"Ответ сервера: {error_body}")
        except:
            pass
        return None
    except urllib.error.URLError as e:
        print(f"✗ Ошибка подключения: {e.reason}")
        print("Убедитесь, что сервер запущен на http://localhost:5000")
        return None
    except json.JSONDecodeError as e:
        print(f"✗ Ошибка при разборе ответа: {e}")
        return None
    except Exception as e:
        print(f"✗ Неожиданная ошибка: {e}")
        return None

if __name__ == "__main__":
    restore_disks()

