#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для Windows: сбор информации о жестких дисках и отправка на сервер
Требует: pip install wmi psutil requests
"""
import os
import sys
import json
import socket
import platform
from datetime import datetime
import subprocess

try:
    import wmi
    import psutil
    import requests
except ImportError as e:
    print(f"Ошибка: Не установлены необходимые библиотеки. Установите: pip install -r requirements.txt")
    print(f"Отсутствует: {e}")
    sys.exit(1)

class HDDCollector:
    def __init__(self, server_host, server_port=5000):
        self.server_host = server_host
        self.server_port = server_port
        self.wmi_conn = wmi.WMI()
        
    def get_disk_info_wmi(self):
        """Получение информации о дисках через WMI"""
        disks_info = []
        
        try:
            # Получаем физические диски
            for disk in self.wmi_conn.Win32_DiskDrive():
                disk_info = {
                    'model': disk.Model.strip() if disk.Model else '',
                    'serial_number': disk.SerialNumber.strip() if disk.SerialNumber else '',
                    'size_gb': int(disk.Size) // (1024**3) if disk.Size else None,
                    'interface': disk.InterfaceType if disk.InterfaceType else '',
                    'media_type': disk.MediaType if disk.MediaType else '',
                    'manufacturer': disk.Manufacturer.strip() if disk.Manufacturer else '',
                }
                
                # Получаем S.M.A.R.T. данные если доступны
                smart_data = self.get_smart_data(disk.DeviceID if hasattr(disk, 'DeviceID') else None)
                if smart_data:
                    disk_info.update(smart_data)
                
                disks_info.append(disk_info)
        except Exception as e:
            print(f"Ошибка при получении данных через WMI: {e}")
        
        return disks_info
    
    def get_smart_data(self, device_id=None):
        """Получение S.M.A.R.T. данных через smartctl (требует установки smartmontools)"""
        smart_info = {}
        
        try:
            # Пробуем использовать smartctl если установлен
            if device_id:
                # Преобразуем DeviceID в путь к диску (например, \\.\PhysicalDrive0)
                drive_num = device_id.split('PHYSICALDRIVE')[-1] if 'PHYSICALDRIVE' in device_id else '0'
                
                # Запускаем smartctl
                result = subprocess.run(
                    ['smartctl', '-a', f'\\\\.\\PhysicalDrive{drive_num}'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    
                    # Извлекаем Power_On_Hours
                    for line in output.split('\n'):
                        if 'Power_On_Hours' in line or 'Power-on Hours' in line:
                            try:
                                parts = line.split()
                                hours = None
                                for i, part in enumerate(parts):
                                    if part.isdigit() and i > 0:
                                        hours = int(part)
                                        break
                                if hours:
                                    smart_info['power_on_hours'] = hours
                            except:
                                pass
                        
                        # Извлекаем Power_Cycle_Count
                        if 'Power_Cycle_Count' in line or 'Power Cycles' in line:
                            try:
                                parts = line.split()
                                count = None
                                for i, part in enumerate(parts):
                                    if part.isdigit() and i > 0:
                                        count = int(part)
                                        break
                                if count:
                                    smart_info['power_on_count'] = count
                            except:
                                pass
                        
                        # Извлекаем статус здоровья
                        if 'SMART overall-health self-assessment test result:' in line:
                            if 'PASSED' in line.upper():
                                smart_info['health_status'] = 'Здоров'
                            elif 'FAILED' in line.upper():
                                smart_info['health_status'] = 'Неработает'
                            else:
                                smart_info['health_status'] = 'Тревога'
        except FileNotFoundError:
            # smartctl не установлен - пропускаем
            pass
        except Exception as e:
            print(f"Ошибка при получении S.M.A.R.T. данных: {e}")
        
        return smart_info
    
    def get_disk_info_psutil(self):
        """Альтернативный метод получения информации через psutil"""
        disks_info = []
        
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info = {
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total_gb': usage.total // (1024**3),
                        'used_gb': usage.used // (1024**3),
                        'free_gb': usage.free // (1024**3),
                    }
                    disks_info.append(disk_info)
                except PermissionError:
                    pass
        except Exception as e:
            print(f"Ошибка при получении данных через psutil: {e}")
        
        return disks_info
    
    def collect_all_info(self):
        """Сбор всей информации о дисках"""
        print("Сбор информации о жестких дисках...")
        
        # Основной метод через WMI
        disks = self.get_disk_info_wmi()
        
        if not disks:
            print("WMI не вернул данные, пробуем альтернативный метод...")
            disks = self.get_disk_info_psutil()
        
        # Добавляем метаданные
        result = {
            'hostname': socket.gethostname(),
            'timestamp': datetime.now().isoformat(),
            'platform': platform.platform(),
            'disks': disks
        }
        
        return result
    
    def send_to_server(self, data):
        """Отправка данных на сервер через HTTP POST"""
        try:
            url = f"http://{self.server_host}:{self.server_port}/api/hdd_collect"
            
            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✓ Данные успешно отправлены на сервер {self.server_host}:{self.server_port}")
                result = response.json()
                if 'processed' in result:
                    print(f"  Обработано дисков: {result['processed']}/{result['total']}")
                return True
            else:
                print(f"✗ Ошибка отправки: HTTP {response.status_code}")
                print(f"Ответ сервера: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"✗ Ошибка: Не удалось подключиться к серверу {self.server_host}:{self.server_port}")
            print("Проверьте, что сервер запущен и доступен по сети")
            return False
        except Exception as e:
            print(f"✗ Ошибка при отправке данных: {e}")
            return False
    
    def run(self):
        """Основная функция запуска"""
        print("=" * 60)
        print("Сбор информации о жестких дисках")
        print("=" * 60)
        
        # Собираем информацию
        data = self.collect_all_info()
        
        print(f"\nНайдено дисков: {len(data['disks'])}")
        for i, disk in enumerate(data['disks'], 1):
            print(f"\nДиск {i}:")
            print(f"  Модель: {disk.get('model', 'N/A')}")
            print(f"  Серийный номер: {disk.get('serial_number', 'N/A')}")
            print(f"  Объем: {disk.get('size_gb', 'N/A')} ГБ")
            if 'power_on_hours' in disk:
                print(f"  Наработка: {disk['power_on_hours']} часов")
            if 'power_on_count' in disk:
                print(f"  Включений: {disk['power_on_count']}")
            if 'health_status' in disk:
                print(f"  Здоровье: {disk['health_status']}")
        
        # Отправляем на сервер
        print(f"\nОтправка данных на сервер {self.server_host}:{self.server_port}...")
        if self.send_to_server(data):
            print("\n✓ Готово!")
            return 0
        else:
            print("\n✗ Ошибка при отправке данных")
            return 1


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Сбор информации о жестких дисках и отправка на сервер',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python hdd_collector.py --host 192.168.1.100 --port 5000
  python hdd_collector.py --host server.example.com --save data.json
  python hdd_collector.py --host localhost --port 8080
        """
    )
    parser.add_argument('--host', default='localhost', 
                       help='Адрес сервера (по умолчанию: localhost)')
    parser.add_argument('--port', type=int, default=5000, 
                       help='Порт сервера (по умолчанию: 5000)')
    parser.add_argument('--save', 
                       help='Сохранить данные в JSON файл перед отправкой (опционально)')
    parser.add_argument('--config', 
                       help='Путь к файлу конфигурации (опционально)')
    
    args = parser.parse_args()
    
    # Загрузка конфигурации из файла если указан
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
            args.host = config.get('host', args.host)
            args.port = config.get('port', args.port)
    
    collector = HDDCollector(args.host, args.port)
    
    # Собираем данные
    data = collector.collect_all_info()
    
    # Сохраняем в файл если указано
    if args.save:
        with open(args.save, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Данные сохранены в {args.save}")
    
    # Отправляем на сервер
    exit_code = collector.send_to_server(data)
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()

