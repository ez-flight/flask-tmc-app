#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для тестового режима работы приложения без реальной БД.
Создает мок-объекты пользователей и переопределяет функции загрузки пользователей.
"""

from flask_login import UserMixin
from datetime import datetime
import hashlib
import random
import string
import os

class MockUser(UserMixin):
    """Мок-класс пользователя для тестового режима."""
    
    def __init__(self, user_id, login, mode=0, orgid=1, roles=None):
        self.id = user_id
        self.login = login
        self.mode = mode  # 1 = Admin, 0 = обычный пользователь
        self.orgid = orgid
        self.randomid = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
        self.email = f"{login}@test.local"
        self.active = True
        self.salt = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        self.password = self._hash_password('test123', self.salt)
        self._roles = roles or []
    
    def _hash_password(self, plain_password, salt):
        """Генерирует хеш пароля для тестового режима."""
        first_hash = hashlib.sha1(plain_password.encode('utf-8')).hexdigest()
        combined = first_hash + salt
        return hashlib.sha1(combined.encode('utf-8')).hexdigest()
    
    def get_id(self):
        return str(self.id)

# Тестовые пользователи
TEST_USERS = {
    'admin': MockUser(1, 'admin', mode=1, orgid=1, roles=[1, 2]),  # Администратор
    'mol': MockUser(2, 'mol', mode=0, orgid=1, roles=[1]),  # МОЛ
    'user': MockUser(3, 'user', mode=0, orgid=1, roles=[]),  # Обычный пользователь
    'test': MockUser(4, 'test', mode=0, orgid=1, roles=[1]),  # Тестовый пользователь
}

# Тестовые пароли для всех пользователей
TEST_PASSWORD = 'test123'

def get_test_user(login):
    """Возвращает тестового пользователя по логину."""
    # Нормализуем логин (приводим к нижнему регистру и убираем пробелы)
    login_normalized = login.strip().lower() if login else ''
    return TEST_USERS.get(login_normalized)

def check_test_password(login, password):
    """Проверяет пароль для тестового режима."""
    # Нормализуем входные данные
    login_normalized = login.strip().lower() if login else ''
    password_normalized = password.strip() if password else ''
    
    user = get_test_user(login_normalized)
    if not user:
        return False
    return password_normalized == TEST_PASSWORD

