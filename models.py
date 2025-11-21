# models.py
# Определение моделей данных для приложения на основе SQLAlchemy.
# Модели описывают структуру таблиц в базе данных и их взаимосвязи.
# Используется в связке с Flask-SQLAlchemy и Flask-Login.
from datetime import datetime, date
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy # <-- Только SQLAlchemy
from sqlalchemy import DateTime # <-- DateTime из sqlalchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Category(db.Model):
    """
    Категории ТМЦ — справочник основных категорий (например, "Компьютеры", "Мебель").
    """
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True) # Уникальное название
    description = db.Column(db.Text, nullable=True)               # Описание (опционально)
    active = db.Column(db.Boolean, nullable=False, default=True)  # Активна ли категория

    # Отношение "один ко многим" с GroupNome
    groups = db.relationship('GroupNome', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.id}: {self.name}>'

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
    repair = db.Column(db.Boolean, nullable=False, default=False)  # В ремонте
    lost = db.Column(db.Boolean, nullable=False, default=False)  # Потерян
    active = db.Column(db.Boolean, nullable=False, default=True)
    ip = db.Column(db.String(100), nullable=True, default='')
    mapx = db.Column(db.String(8), nullable=True, default='')
    mapy = db.Column(db.String(8), nullable=True, default='')
    mapmoved = db.Column(db.Integer, nullable=False, default=0)
    mapyet = db.Column(db.Boolean, nullable=False, default=False)
    kntid = db.Column(db.Integer, db.ForeignKey('knt.id'), nullable=True, default = None)  # ← ИСПРАВЛЕНО
    dtendgar = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    tmcgo = db.Column(db.Integer, nullable=False, default=0)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    date_start = db.Column(db.Date, nullable=False, default=date.today)
    invoice_file = db.Column(db.String(255), nullable=False, default='')
    passport_filename = db.Column(db.String(255), nullable=True)
    dtendlife = db.Column(db.Date, nullable=True)
    # Дополнительные поля для Формы 8 (необязательные)
    warehouse_rack = db.Column(db.String(100), nullable=True)  # Стеллаж
    warehouse_cell = db.Column(db.String(100), nullable=True)  # Ячейка
    unit_name = db.Column(db.String(50), nullable=True)  # Единица измерения (наименование)
    unit_code = db.Column(db.String(10), nullable=True)  # Единица измерения (код)
    profile = db.Column(db.String(100), nullable=True)  # Профиль
    size = db.Column(db.String(100), nullable=True)  # Размер
    stock_norm = db.Column(db.String(50), nullable=True)  # Норма запаса
    invoice_links = db.relationship('InvoiceEquipment', back_populates='equipment')
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
    comment = db.Column(db.Text, nullable=False, default='')           # Комментарий к помещению
    opgroup = db.Column(db.Integer, nullable=False, default=0)         # Группа операций

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
    email = db.Column(db.String(100), nullable=False)  # ← тоже стоит добавить
    mode = db.Column(db.Integer, nullable=False, default=0)  # ← ОБЯЗАТЕЛЬНО ДОБАВИТЬ
    salt = db.Column(db.String(10), nullable=False)                   # Соль для хеширования пароля
    active = db.Column(db.Boolean, nullable=False, default=True)      # Активен ли пользователь
 #   sessionid = db.Column(db.String(50), nullable=True)
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
    name = db.Column(db.String(255), nullable=False)
    comment = db.Column(db.Text, nullable=True)  # Добавляем поле comment
    active = db.Column(db.Boolean, nullable=False, default=True)

    # Новый внешний ключ, связывающий GroupNome с Category
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True) # Может быть NULL, если не назначена

    # Отношение "многие к одному" с Category (уже определено в backref выше, но можно явно указать)
    # category = db.relationship('Category', backref='groups')

class Vendor(db.Model):
    """
    Производители/поставщики оборудования.
    """
    __tablename__ = 'vendor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(155), nullable=False)                  # Название производителя
    active = db.Column(db.Boolean, nullable=False, default=True)      # Активен ли поставщик
    comment = db.Column(db.Text, nullable=True, default='')          # Комментарий

class Nome(db.Model):
    """
    Наименования оборудования — конкретные типы устройств или предметов.
    Связаны с группой и производителем.
    """
    __tablename__ = 'nome'
    id = db.Column(db.Integer, primary_key=True)
    groupid = db.Column(db.Integer, db.ForeignKey('group_nome.id'), nullable=False)  # Изменяем ForeignKey
    vendorid = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    active = db.Column(db.Boolean, nullable=False)
    photo = db.Column(db.String(255), nullable=False, default='')
    comment = db.Column(db.Text, nullable=True)  # Text позволяет хранить большие текстовые
    is_component = db.Column(db.Boolean, default=False, nullable=False)
    is_composite = db.Column(db.Boolean, default=False, nullable=False)  # Флаг составного ТМЦ
    category_sort = db.Column(db.Integer, nullable=True)  # Категория (сорт) - значение от 1 до 5
    # Добавляем отношение
    group = db.relationship('GroupNome', backref='nomes')

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

class Invoices(db.Model):
    """
    Накладные — документы передачи ТМЦ между МОЛами (материально-ответственными лицами)
    или между складом и МОЛом.
    """
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_number = db.Column(db.String(50), nullable=False, comment='Номер накладной')
    invoice_date = db.Column(db.Date, nullable=False, comment='Дата накладной')
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True, comment='Отдел (например, ОТО)')
    type = db.Column(db.Enum('Склад-МОЛ', 'МОЛ-МОЛ', 'МОЛ-Склад'), nullable=False, comment='Тип накладной')
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, comment='МОЛ отправителя')
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, comment='МОЛ получателя')
    pdf_path = db.Column(db.String(255), nullable=False, comment='Путь к PDF-файлу на сервере')
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    from_knt_id = db.Column(db.Integer, db.ForeignKey('knt.id'), nullable=True)
    to_knt_id = db.Column(db.Integer, db.ForeignKey('knt.id'), nullable=True)
    # ЕДИНСТВЕННОЕ определение отношения — через back_populates
    invoice_equipment = db.relationship('InvoiceEquipment', back_populates='invoice', cascade='all, delete-orphan')
    # Связи
    department = db.relationship('Department', backref='invoices')
    from_user = db.relationship('Users', foreign_keys=[from_user_id])
    to_user = db.relationship('Users', foreign_keys=[to_user_id])
    from_knt = db.relationship('Knt', foreign_keys=[from_knt_id])
    to_knt = db.relationship('Knt', foreign_keys=[to_knt_id])
    def __repr__(self):
        return f'<Invoice {self.id}: {self.invoice_number} от {self.invoice_date}>'

class InvoiceEquipment(db.Model):
    __tablename__ = 'invoice_equipment'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    # Явные связи — без backref в обе стороны, чтобы избежать конфликта
    invoice = db.relationship('Invoices', back_populates='invoice_equipment')
    equipment = db.relationship('Equipment', back_populates='invoice_links')

class Move(db.Model):
    __tablename__ = 'move'
    id = db.Column(db.Integer, primary_key=True)
    eqid = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    dt = db.Column(db.DateTime, nullable=False)
    orgidfrom = db.Column(db.Integer, nullable=False)
    orgidto = db.Column(db.Integer, nullable=False)
    placesidfrom = db.Column(db.Integer, nullable=False)
    placesidto = db.Column(db.Integer, nullable=False)
    useridfrom = db.Column(db.Integer, nullable=False)
    useridto = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)

class UsersRoles(db.Model):
    __tablename__ = 'usersroles'
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, nullable=False)
    role = db.Column(db.Integer, nullable=False)

class UsersProfile(db.Model):
    __tablename__ = 'users_profile'
    id = db.Column(db.Integer, primary_key=True)
    usersid = db.Column(db.Integer, nullable=False)
    fio = db.Column(db.String(100), nullable=False)
    jpegphoto = db.Column(db.String(40), nullable=False, default='noimage.jpg')
    # остальные поля можно добавить по необходимости

class AppComponents(db.Model):
    """Модель для комплектующих, связанных с основным средством."""
    __tablename__ = 'app_components'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_main_asset = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False) # Ссылка на основное средство
    id_nome_component = db.Column(db.Integer, db.ForeignKey('nome.id'), nullable=False) # Ссылка на тип комплектующего
    ser_num_component = db.Column(db.String(255), nullable=True) # Серийный номер комплектующего
    comment_component = db.Column(db.Text, nullable=True) # Комментарии к комплектующему
    doc_path = db.Column(db.String(500), nullable=True) # Путь к документации комплектующего
    sw_image_path = db.Column(db.String(500), nullable=True) # Путь к образу ПО комплектующего
    disposed = db.Column(db.Boolean, default=False) # Статус списания (0=False, 1=True)

    # Отношения
    main_asset = db.relationship('Equipment', backref='components') # Обратная связь к основному средству
    component_nome = db.relationship('Nome', backref='component_instances') # Связь с типом комплектующего

    def __repr__(self):
        return f'<AppComponents {self.id}: Component {self.id_nome_component} for Asset {self.id_main_asset}>'


class NomeComponents(db.Model):
    """Модель для шаблона комплекта, привязанного к типу ТМЦ (nome)."""
    __tablename__ = 'nome_components'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_nome_main = db.Column(db.Integer, db.ForeignKey('nome.id'), nullable=False) # Основной тип ТМЦ
    id_nome_component = db.Column(db.Integer, db.ForeignKey('nome.id'), nullable=False) # Тип комплектующего
    sort_order = db.Column(db.Integer, nullable=False, default=0) # Порядок в списке

    # Отношения
    main_nome = db.relationship('Nome', foreign_keys=[id_nome_main], backref='component_template')
    component_nome = db.relationship('Nome', foreign_keys=[id_nome_component])

class PostUsers(db.Model):
    __tablename__ = 'post_users'

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, nullable=False)
    orgid = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    post = db.Column(db.String(100), nullable=True) # Поле post хранит должность (может быть NULL)

    def __repr__(self):
        return f'<PostUsers {self.post} for User ID {self.userid}>'

# --- Конец добавления ---
    def __repr__(self):
        return f'<NomeComponents for {self.id_nome_main}: Component {self.id_nome_component}>'
    
class News(db.Model):
    """
    Модель для хранения новостей — совместима с существующей таблицей `news`.
    """
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)      # ← старое поле
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)                                 # ← вместо 'content'
    stiker = db.Column(db.Boolean, nullable=False, default=False)             # ← вместо 'is_active'
    pinned = db.Column(db.Boolean, nullable=False, default=False)              # ← закрепленная новость

    # author_id отсутствует в таблице — не добавляем

    def __repr__(self):
        return f'<News {self.id}: {self.title}>'
    
class EquipmentTempUsage(db.Model):
    __tablename__ = 'equipment_temp_usage'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    mol_userid = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_temp_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    dt_start = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    dt_end = db.Column(db.DateTime, nullable=True)
    returned = db.Column(db.Boolean, nullable=False, default=False)
    comment = db.Column(db.Text, nullable=True)

    # Связи
    equipment = db.relationship('Equipment', backref='temp_usages')
    mol_user = db.relationship('Users', foreign_keys=[mol_userid])
    temp_user = db.relationship('Users', foreign_keys=[user_temp_id])

    def __repr__(self):
        return f'<TempUsage {self.id}: Eq {self.equipment_id} → User {self.user_temp_id}>'

class EquipmentComments(db.Model):
    """Модель для хранения истории комментариев к ТМЦ."""
    __tablename__ = 'equipment_comments'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Связи
    equipment = db.relationship('Equipment', backref='comment_history')
    creator = db.relationship('Users', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<EquipmentComment {self.id}: Eq {self.equipment_id} at {self.created_at}>'