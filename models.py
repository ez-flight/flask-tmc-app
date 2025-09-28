# models.py
# Определение моделей данных для приложения на основе SQLAlchemy.
# Модели описывают структуру таблиц в базе данных и их взаимосвязи.
# Используется в связке с Flask-SQLAlchemy и Flask-Login.

from datetime import datetime, date
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Инициализация объекта SQLAlchemy для работы с базой данных
db = SQLAlchemy()


class Equipment(db.Model):
    """
    Модель оборудования — основная сущность, описывающая единицу техники или имущества.
    Содержит информацию о местоположении, стоимости, состоянии, документации и пр.
    """
    __tablename__ = 'equipment'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    orgid = db.Column(db.Integer, db.ForeignKey('org.id'), nullable=False)
    placesid = db.Column(db.Integer, db.ForeignKey('places.id'), nullable=False)
    usersid = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nomeid = db.Column(db.Integer, db.ForeignKey('nome.id'), nullable=False)
    buhname = db.Column(db.String(255), nullable=False)
    datepost = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    cost = db.Column(db.DECIMAL(precision=12, scale=2), nullable=False, default=Decimal('0.00'))
    currentcost = db.Column(db.DECIMAL(precision=12, scale=2), nullable=False, default=Decimal('0.00'))
    sernum = db.Column(db.String(100), nullable=True, default='')
    invnum = db.Column(db.String(100), nullable=True, default='')
    shtrihkod = db.Column(db.String(50), nullable=True, default='')
    os = db.Column(db.Boolean, nullable=False, default=False)
    mode = db.Column(db.Boolean, nullable=False, default=False)
    comment = db.Column(db.Text, nullable=True, default='')
    photo = db.Column(db.String(255), nullable=True, default='')
    repair = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    ip = db.Column(db.String(100), nullable=True, default='')
    mapx = db.Column(db.String(8), nullable=True, default='')
    mapy = db.Column(db.String(8), nullable=True, default='')
    mapmoved = db.Column(db.Integer, nullable=False, default=0)
    mapyet = db.Column(db.Boolean, nullable=False, default=False)
    kntid = db.Column(db.Integer, db.ForeignKey('knt.id'), nullable=True, default = None)  # ← ИСПРАВЛЕНО
    dtendgar = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    tmcgo = db.Column(db.Integer, nullable=False, default=0)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    date_start = db.Column(db.Date, nullable=False, default=date.today)
    invoice_file = db.Column(db.String(255), nullable=False, default='')
    passport_file = db.Column(db.String(255), nullable=False, default='')

    # Связи
    org = db.relationship('Org', backref='equipment')
    places = db.relationship('Places', backref='equipment')
    users = db.relationship('Users', backref='equipment')
    knt = db.relationship('Knt', backref='equipment')
    nome = db.relationship('Nome', backref='equipment')

    def __repr__(self):
        return f'<Equipment {self.id}: {self.buhname}>'


class Org(db.Model):
    """
    Организации — справочник организаций, к которым может относиться оборудование или пользователи.
    """
    __tablename__ = 'org'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)                  # Название организации
    active = db.Column(db.Boolean, nullable=False, default=True)      # Активна ли организация


class Places(db.Model):
    """
    Места размещения — справочник локаций (офисы, склады, кабинеты и т.д.).
    """
    __tablename__ = 'places'
    id = db.Column(db.Integer, primary_key=True)
    orgid = db.Column(db.Integer, nullable=False)                     # ID связанной организации
    name = db.Column(db.String(150), nullable=False)                  # Название места
    active = db.Column(db.Boolean, nullable=False)                    # Активно ли место

class Knt(db.Model):
    """
    Поставщики — справочник.
    """
    __tablename__ = 'knt'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, nullable=False)
    fullname = db.Column(db.String(200), nullable=False)
    ERPCode = db.Column(db.Integer, nullable=False)
    INN = db.Column(db.String(20), nullable=False)
    KPP = db.Column(db.String(20), nullable=False)
    bayer = db.Column(db.Integer, nullable=False)
    supplier = db.Column(db.Integer, nullable=False)
    dog = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Knt {self.id}: {self.name}>'


class Users(db.Model, UserMixin):
    """
    Пользователи системы — модель для аутентификации и авторизации.
    Наследуется от UserMixin для совместимости с Flask-Login.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    randomid = db.Column(db.String(100), nullable=False)              # Уникальный случайный идентификатор (возможно, для API)
    orgid = db.Column(db.Integer, nullable=False)                     # ID организации пользователя
    login = db.Column(db.String(50), nullable=False, unique=True)     # Логин (уникальный)
    password = db.Column(db.String(40), nullable=False)               # Хеш пароля (предположительно SHA1 или аналог)
    salt = db.Column(db.String(10), nullable=False)                   # Соль для хеширования пароля
    active = db.Column(db.Boolean, nullable=False, default=True)      # Активен ли пользователь

    def get_id(self):
        """Обязательный метод для Flask-Login: возвращает строковое представление ID пользователя."""
        return str(self.id)

    def __repr__(self):
        return f'<User {self.login}>'


class GroupNome(db.Model):
    """
    Группы наименований — категории для классификации оборудования (например, "Компьютеры", "Мебель").
    """
    __tablename__ = 'group_nome'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)                  # Название группы
    active = db.Column(db.Boolean, nullable=False, default=True)      # Активна ли группа


class Vendor(db.Model):
    """
    Производители/поставщики оборудования.
    """
    __tablename__ = 'vendor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(155), nullable=False)                  # Название производителя
    active = db.Column(db.Boolean, nullable=False, default=True)      # Активен ли поставщик


class Nome(db.Model):
    """
    Наименования оборудования — конкретные типы устройств или предметов.
    Связаны с группой и производителем.
    """
    __tablename__ = 'nome'
    id = db.Column(db.Integer, primary_key=True)
    groupid = db.Column(db.Integer, nullable=False)                   # ID группы наименований
    vendorid = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)  # Связь с производителем
    name = db.Column(db.String(200), nullable=False)                  # Название наименования
    active = db.Column(db.Boolean, nullable=False)                    # Активно ли наименование
    photo = db.Column(db.String(255), nullable=False, default='')     # Фото


class Department(db.Model):
    """
    Отделы организации — структурные подразделения (например, "Бухгалтерия", "IT-отдел").
    Может быть связан с оборудованием через поле department_id в Equipment.
    """
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)                  # Название отдела
    code = db.Column(db.String(50), nullable=False)                   # Уникальный код отдела
    active = db.Column(db.Boolean, nullable=False, default=True)      # Активен ли отдел

    def __repr__(self):
        return f'<Department {self.id}: {self.name}>'