# models.py
# Определение моделей данных для приложения на основе SQLAlchemy.
# Модели описывают структуру таблиц в базе данных и их взаимосвязи.
# Используется в связке с Flask-SQLAlchemy и Flask-Login.

from datetime import datetime

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

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Уникальный идентификатор записи
    orgid = db.Column(db.Integer, nullable=False)                     # ID организации, к которой относится оборудование
    placesid = db.Column(db.Integer, nullable=False)                  # ID места размещения (офис, склад и т.д.)
    usersid = db.Column(db.Integer, nullable=False)                   # ID ответственного пользователя
    nomeid = db.Column(db.Integer, nullable=False)                    # ID наименования из справочника nome
    buhname = db.Column(db.String(255), nullable=False)               # Бухгалтерское наименование оборудования
    datepost = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Дата добавления записи
    cost = db.Column(db.Integer, nullable=False, default=0)           # Первоначальная стоимость (в условных единицах)
    currentcost = db.Column(db.Integer, nullable=False, default=0)    # Текущая остаточная стоимость
    sernum = db.Column(db.String(100), nullable=True, default='')     # Серийный номер
    invnum = db.Column(db.String(100), nullable=True, default='')     # Инвентарный номер
    shtrihkod = db.Column(db.String(50), nullable=True, default='')   # Штрихкод
    os = db.Column(db.Boolean, nullable=False, default=False)         # Является ли объектом основных средств (ОС)
    mode = db.Column(db.Boolean, nullable=False, default=False)       # Режим эксплуатации (например, тестовый/боевой)
    comment = db.Column(db.Text, nullable=True, default='')           # Дополнительные комментарии
    photo = db.Column(db.String(255), nullable=True, default='')      # Путь к фото оборудования
    repair = db.Column(db.Boolean, nullable=False, default=False)     # Находится ли в ремонте
    active = db.Column(db.Boolean, nullable=False, default=True)      # Активно ли оборудование (не списано)
    ip = db.Column(db.String(100), nullable=True, default='')         # IP-адрес (если применимо)
    mapx = db.Column(db.String(8), nullable=True, default='')         # Координата X на карте размещения
    mapy = db.Column(db.String(8), nullable=True, default='')         # Координата Y на карте размещения
    mapmoved = db.Column(db.Integer, nullable=False, default=0)       # Счётчик перемещений по карте
    mapyet = db.Column(db.Boolean, nullable=False, default=False)     # Отмечено ли на карте
    kntid = db.Column(db.Integer, nullable=False, default=0)          # Идентификатор контрагента (поставщика)
    dtendgar = db.Column(db.Date, nullable=False, default=datetime.utcnow)  # Дата окончания гарантии
    tmcgo = db.Column(db.Integer, nullable=False, default=0)          # Код ТМЦ (товарно-материальных ценностей)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)  # Связь с отделом
    date_start = db.Column(db.Date, nullable=False, default=datetime.utcnow)  # Дата начала эксплуатации
    invoice_file = db.Column(db.String(255), nullable=False, default='')      # Путь к файлу накладной
    passport_file = db.Column(db.String(255), nullable=False, default='')     # Путь к файлу паспорта/документации

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