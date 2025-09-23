# models.py
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Equipment(db.Model):
    __tablename__ = 'equipment'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    orgid = db.Column(db.Integer, nullable=False)        # Организация
    placesid = db.Column(db.Integer, nullable=False)     # Место нахождения
    usersid = db.Column(db.Integer, nullable=False)      # Ответственный пользователь
    nomeid = db.Column(db.Integer, nullable=False)       # Наименование (номенклатура)
    buhname = db.Column(db.String(255), nullable=False)  # Бухгалтерское наименование
    datepost = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Дата поступления
    cost = db.Column(db.Integer, nullable=False, default=0)           # Стоимость
    currentcost = db.Column(db.Integer, nullable=False, default=0)    # Текущая стоимость
    sernum = db.Column(db.String(100), nullable=True, default='')     # Серийный номер
    invnum = db.Column(db.String(100), nullable=True, default='')     # Инвентарный номер
    shtrihkod = db.Column(db.String(50), nullable=True, default='')   # Штрихкод
    os = db.Column(db.Boolean, nullable=False, default=False)         # ОС?
    mode = db.Column(db.Boolean, nullable=False, default=False)       # Режим?
    comment = db.Column(db.Text, nullable=True, default='')           # Комментарий
    photo = db.Column(db.String(255), nullable=True, default='')      # Фото
    repair = db.Column(db.Boolean, nullable=False, default=False)     # На ремонте?
    active = db.Column(db.Boolean, nullable=False, default=True)      # Активен?
    ip = db.Column(db.String(100), nullable=True, default='')         # IP-адрес
    mapx = db.Column(db.String(8), nullable=True, default='')         # Координата X на карте
    mapy = db.Column(db.String(8), nullable=True, default='')         # Координата Y на карте
    mapmoved = db.Column(db.Integer, nullable=False, default=0)       # Перемещался на карте?
    mapyet = db.Column(db.Boolean, nullable=False, default=False)     # На карте?
    kntid = db.Column(db.Integer, nullable=False, default=0)          # Контрагент
    dtendgar = db.Column(db.Date, nullable=False, default=datetime.utcnow) # Дата окончания гарантии
    tmcgo = db.Column(db.Integer, nullable=False, default=0)          # ТМЦ в движении?
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)

    def __repr__(self):
        return f'<Equipment {self.id}: {self.buhname}>'
    
class Org(db.Model):
    __tablename__ = 'org'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Integer, nullable=False)

class Places(db.Model):
    __tablename__ = 'places'
    id = db.Column(db.Integer, primary_key=True)
    orgid = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    active = db.Column(db.Boolean, nullable=False)

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), nullable=False)
    active = db.Column(db.Boolean, nullable=False)

class GroupNome(db.Model):
    __tablename__ = 'group_nome'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

class Vendor(db.Model):
    __tablename__ = 'vendor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(155), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

class Nome(db.Model):
    __tablename__ = 'nome'
    id = db.Column(db.Integer, primary_key=True)
    groupid = db.Column(db.Integer, nullable=False)
    vendorid = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    active = db.Column(db.Boolean, nullable=False)

class Department(db.Model):
    __tablename__ = 'department'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f'<Department {self.id}: {self.name}>'