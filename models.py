# models.py
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Equipment(db.Model):
    __tablename__ = 'equipment'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    orgid = db.Column(db.Integer, nullable=False)
    placesid = db.Column(db.Integer, nullable=False)
    usersid = db.Column(db.Integer, nullable=False)
    nomeid = db.Column(db.Integer, nullable=False)
    buhname = db.Column(db.String(255), nullable=False)
    datepost = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    cost = db.Column(db.Integer, nullable=False, default=0)
    currentcost = db.Column(db.Integer, nullable=False, default=0)
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
    kntid = db.Column(db.Integer, nullable=False, default=0)
    dtendgar = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    tmcgo = db.Column(db.Integer, nullable=False, default=0)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)

    def __repr__(self):
        return f'<Equipment {self.id}: {self.buhname}>'

class Org(db.Model):
    __tablename__ = 'org'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)  # Исправлено

class Places(db.Model):
    __tablename__ = 'places'
    id = db.Column(db.Integer, primary_key=True)
    orgid = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    active = db.Column(db.Boolean, nullable=False)

class Users(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(40), nullable=False)
    salt = db.Column(db.String(10), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<User {self.login}>'

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