# -*- coding: utf-8 -*-
"""
Основной файл Flask-приложения для учёта ТМЦ (техники, оборудования и т.п.).
Интегрируется с существующей БД `webuseorg3`, включая совместимость с оригинальной
системой хеширования паролей: SHA1(salt + password)., пока что работает только наоборот
"""
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
import os
import hashlib
from sqlalchemy import func, case
from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal, InvalidOperation
from sqlalchemy.exc import IntegrityError

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user


from models import Equipment, Nome, Org, Places, Users, db, GroupNome, Vendor, Department, Knt, Invoices, InvoiceEquipment, UsersRoles, UsersProfile, Category, Move, AppComponents, NomeComponents, PostUsers, News, EquipmentTempUsage

# Загружаем переменные окружения из .env
load_dotenv()

# Создаём Flask-приложение
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-for-dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # маршрут для перенаправления неавторизованных пользователей

app.jinja_env.globals['date'] = date
# === ФУНКЦИИ БЕЗОПАСНОСТИ ===

def check_password(plain_password: str, salt: str, hashed_password: str) -> bool:
    """
    Проверяет пароль в соответствии с логикой PHP-кода:
    hashed_password = SHA1( SHA1(plain_password) + salt )
    
    :param plain_password: исходный пароль в открытом виде
    :param salt: соль из БД (строка)
    :param hashed_password: сохранённый хеш из БД (в нижнем регистре, 40 символов)
    :return: True если совпадает
    """
    # Шаг 1: SHA1 от пароля → получаем hex-строку
    first_hash = hashlib.sha1(plain_password.encode('utf-8')).hexdigest()
    
    # Шаг 2: конкатенируем hex-строку с солью (внимание: соль идёт ПОСЛЕ!)
    combined = first_hash + salt
    
    # Шаг 3: SHA1 от результата
    final_hash = hashlib.sha1(combined.encode('utf-8')).hexdigest()
    
    # Сравнение (регистронезависимо, но обычно всё в нижнем)
    return final_hash == hashed_password.lower()

def current_user_has_role(role_id):
    """
    Проверяет, есть ли у текущего пользователя роль с указанным ID.
    """
    from models import UsersRoles
    return db.session.query(UsersRoles).filter_by(userid=current_user.id, role=role_id).first() is not None

def user_has_role(user_id, role_id):
    """
    Проверяет, имеет ли пользователь с user_id роль role_id.
    """
    from models import UsersRoles
    return db.session.query(UsersRoles).filter_by(userid=user_id, role=role_id).first() is not None

# === ЗАГРУЗКА ПОЛЬЗОВАТЕЛЯ ДЛЯ Flask-Login ===

@login_manager.user_loader
def load_user(user_id):
    """Загружает пользователя по ID для Flask-Login."""
    return db.session.get(Users, int(user_id))


# === НАСТРОЙКИ ЗАГРУЗКИ ФАЙЛОВ ===

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 МБ максимум
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



"""Проверяет, разрешено ли расширение файла."""
def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_document(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


# === ОДНОКРАТНОЕ СОЗДАНИЕ ТАБЛИЦ ===

@app.before_request
def create_tables_once():
    """Создаёт таблицы при первом запросе (только в dev-режиме)."""
    if not hasattr(app, 'tables_created'):
        db.create_all()
        app.tables_created = True


# === МАРШРУТЫ ===

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа."""
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']

        # Ищем активного пользователя по логину
        user = Users.query.filter_by(login=login, active=1).first()
        if user and check_password(password, user.salt, user.password):
            login_user(user)
            response = redirect(url_for('index'))
            # Устанавливаем куку, как в оригинальной системе
            response.set_cookie('user_randomid_w3', user.randomid, max_age=60*60*24*30)  # 30 дней
            return response
        else:
            flash('Неверный логин или пароль', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Выход из системы."""
    logout_user()
    flash('Вы вышли из системы.', 'info')
    response = redirect(url_for('index'))
    response.set_cookie('user_randomid_w3', '', expires=0)
    return response



@app.route('/')
@login_required
def index():
    is_admin = current_user.mode == 1

    # Запрос ТМЦ для пользователя или всех (если админ)
    if is_admin:
        tmc_query = Equipment.query.filter_by(active=True, os=True)
    else:
        tmc_query = Equipment.query.filter_by(usersid=current_user.id, active=True, os=True)

    tmc_count = tmc_query.count()
    total_cost = db.session.query(func.coalesce(func.sum(Equipment.cost), 0)).filter(
        Equipment.id.in_([eq.id for eq in tmc_query.all()])
    ).scalar()

    # Подсчёт активных пользователей (только для админа)
    active_users = 0
    stats_data = {}
    
    if is_admin:
        active_users = db.session.query(Equipment.usersid).filter(
            Equipment.active == True,
            Equipment.os == True
        ).distinct().count()
        
        # Статистика по категориям (количество ТМЦ)
        category_stats = db.session.query(
            Category.name.label('category_name'),
            func.count(Equipment.id).label('count')
        ).join(GroupNome, Category.id == GroupNome.category_id)\
         .join(Nome, GroupNome.id == Nome.groupid)\
         .join(Equipment, Nome.id == Equipment.nomeid)\
         .filter(Equipment.active == True, Equipment.os == True)\
         .group_by(Category.id, Category.name)\
         .order_by(func.count(Equipment.id).desc())\
         .all()
        
        stats_data['category_labels'] = [row.category_name for row in category_stats] if category_stats else []
        stats_data['category_counts'] = [row.count for row in category_stats] if category_stats else []
        
        # Статистика по категориям (стоимость)
        category_cost_stats = db.session.query(
            Category.name.label('category_name'),
            func.coalesce(func.sum(Equipment.cost), 0).label('total_cost')
        ).join(GroupNome, Category.id == GroupNome.category_id)\
         .join(Nome, GroupNome.id == Nome.groupid)\
         .join(Equipment, Nome.id == Equipment.nomeid)\
         .filter(Equipment.active == True, Equipment.os == True)\
         .group_by(Category.id, Category.name)\
         .order_by(func.sum(Equipment.cost).desc())\
         .all()
        
        stats_data['category_cost_labels'] = [row.category_name for row in category_cost_stats] if category_cost_stats else []
        stats_data['category_costs'] = [float(row.total_cost) for row in category_cost_stats] if category_cost_stats else []
        
        # Статистика по отделам
        department_stats = db.session.query(
            Department.name.label('department_name'),
            func.count(Equipment.id).label('count')
        ).join(Equipment, Department.id == Equipment.department_id)\
         .filter(Equipment.active == True, Equipment.os == True)\
         .group_by(Department.id, Department.name)\
         .order_by(func.count(Equipment.id).desc())\
         .limit(10)\
         .all()
        
        stats_data['department_labels'] = [row.department_name for row in department_stats] if department_stats else []
        stats_data['department_counts'] = [row.count for row in department_stats] if department_stats else []
        
        # Топ пользователей по количеству ТМЦ
        user_stats = db.session.query(
            Users.login.label('user_login'),
            func.count(Equipment.id).label('count')
        ).join(Equipment, Users.id == Equipment.usersid)\
         .filter(Equipment.active == True, Equipment.os == True)\
         .group_by(Users.id, Users.login)\
         .order_by(func.count(Equipment.id).desc())\
         .limit(10)\
         .all()
        
        stats_data['user_labels'] = [row.user_login for row in user_stats] if user_stats else []
        stats_data['user_counts'] = [row.count for row in user_stats] if user_stats else []
        
        # Динамика добавления ТМЦ по месяцам (последние 12 месяцев)
        twelve_months_ago = datetime.now() - relativedelta(days=365)
        
        # Получаем все ТМЦ за последний год
        all_equipment = Equipment.query.filter(
            Equipment.active == True,
            Equipment.os == True,
            Equipment.datepost >= twelve_months_ago
        ).all()
        
        # Группируем по месяцам в Python
        monthly_dict = {}
        for eq in all_equipment:
            month_key = eq.datepost.strftime('%Y-%m') if eq.datepost else None
            if month_key:
                monthly_dict[month_key] = monthly_dict.get(month_key, 0) + 1
        
        # Сортируем по месяцам
        sorted_months = sorted(monthly_dict.keys())
        stats_data['monthly_labels'] = sorted_months if sorted_months else []
        stats_data['monthly_counts'] = [monthly_dict[month] for month in sorted_months] if sorted_months else []
        
        # Статусы ТМЦ
        repair_count = Equipment.query.filter_by(active=True, os=True, repair=True).count()
        active_count = Equipment.query.filter_by(active=True, os=True, repair=False).count()
        
        stats_data['status_labels'] = ['Активные', 'В ремонте']
        stats_data['status_counts'] = [active_count, repair_count]
        
        # Общее количество комплектующих
        components_count = Equipment.query.filter_by(active=True, os=False).count()
        stats_data['components_count'] = components_count

    moves = Move.query.order_by(Move.dt.desc()).limit(5).all()

    # Фото пользователя
    from models import UsersProfile
    profile = UsersProfile.query.filter_by(usersid=current_user.id).first()
    if profile and profile.jpegphoto and profile.jpegphoto != 'noimage.jpg':
        user_photo = url_for('static', filename=f'uploads/{profile.jpegphoto}')
    else:
        user_photo = url_for('static', filename='uploads/noimage.jpg')

    # Новости
    news_list = News.query.filter_by(stiker=True).order_by(News.dt.desc()).limit(5).all()

    return render_template('index.html',
                           user_login=current_user.login,
                           user_photo=user_photo,
                           tmc_count=tmc_count,
                           total_cost=total_cost,
                           is_admin=is_admin,
                           news_list=news_list,
                           moves=moves,
                           active_users=active_users,
                           stats_data=stats_data if is_admin else {})


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_tmc():
    # Получаем nome_id из URL-параметра (если есть)
    nome_id = request.args.get('nome_id', type=int)
    preselected_nome = None
    preselected_group = None
    preselected_vendor = None

    if nome_id:
        preselected_nome = Nome.query.get_or_404(nome_id)
        preselected_group = GroupNome.query.get(preselected_nome.groupid)
        preselected_vendor = Vendor.query.get(preselected_nome.vendorid)

    """Добавление нового ТМЦ."""
    if request.method == 'POST':
        # Получаем данные формы
        nomeid = int(request.form['nomeid'])
        buhname = request.form['buhname']
        sernum = request.form.get('sernum', '')
        invnum = request.form.get('invnum', '')
        comment = request.form.get('comment', '')
        groupid = int(request.form['groupid'])
        vendorid = int(request.form['vendorid'])
        nomeid = int(request.form['nomeid'])
        orgid = int(request.form['orgid'])
        placesid = int(request.form['placesid'])
        usersid = int(request.form['usersid'])
        department_id = request.form.get('department_id')
        department_id = int(department_id) if department_id else None

        # Обработка фото
        photo_filename = ''
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_image(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ext = filename.rsplit('.', 1)[1].lower()
                # Создаём подпапку group_label
                group_label_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'group_label')
                os.makedirs(group_label_dir, exist_ok=True)
                # photo_filename = f"{timestamp}.{ext}" # <-- Уже должно быть так, если предыдущие изменения применены
                photo_filename = f"{timestamp}.{ext}" # <-- Убедитесь, что именно так
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
        
        # Обработка паспорта
        passport_filename = ''
        if 'passport' in request.files:
            file = request.files['passport']
            if file and file.filename != '':
                if not allowed_document(file.filename):
                    flash('Файл паспорта должен быть в формате PDF (с расширением .pdf)', 'danger')
                    return redirect(request.url)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                passport_filename = f"passport_{timestamp}.pdf"
                passport_dir = os.path.join('static', 'passports')
                os.makedirs(passport_dir, exist_ok=True)
                file.save(os.path.join(passport_dir, passport_filename))

        # Получаем kntid из формы или устанавливаем None
        kntid = request.form.get('kntid')
        kntid = int(kntid) if kntid else None

        # === СОЗДАЁМ ОБЪЕКТ СРАЗУ ===
        new_tmc = Equipment(
            buhname=buhname,
            sernum=sernum,
            invnum=invnum,
            comment=comment,
            orgid=orgid,
            placesid=placesid,
            usersid=usersid,
            nomeid=nomeid,
            department_id=department_id,
            photo=photo_filename,
            passport_filename=passport_filename,
            kntid=kntid,
            # Временные значения — будут перезаписаны ниже
            datepost=datetime.utcnow(),
            dtendgar=datetime.utcnow().date(),
            dtendlife=datetime.utcnow().date(),  # ← ДОБАВЛЕНО
            cost=0,
            currentcost=0,
            os=True,
            mode=False,
            repair=False,
            active=True,
            ip='',
            mapx='',
            mapy='',
            mapmoved=0,
            mapyet=False,
            tmcgo=0,
        )

        # === Теперь корректно обрабатываем даты ===
        date_start_str = request.form.get('date_start')

        if date_start_str:
            date_start = datetime.strptime(date_start_str, '%Y-%m-%d')
            new_tmc.datepost = date_start
            # Автоматически рассчитываем гарантию (+1 год) и срок службы (+5 лет)
            new_tmc.dtendgar = (date_start + relativedelta(years=1)).date()
            new_tmc.dtendlife = (date_start + relativedelta(years=5)).date()
        # Если дата не указана — остаются значения по умолчанию (сегодня)

        try:
            db.session.add(new_tmc)
            db.session.commit()
            flash('ТМЦ успешно добавлен!', 'success')
            return redirect(url_for('index'))
        except IntegrityError as e:
            db.session.rollback()
            flash('Ошибка при сохранении: нарушено ограничение целостности данных', 'danger')
            return redirect(url_for('add_tmc'))

    # GET: отображаем форму
    organizations = Org.query.all()
    places = Places.query.all()
    users = db.session.query(Users)\
        .join(UsersRoles, Users.id == UsersRoles.userid)\
        .filter(Users.active == True, UsersRoles.role == 1)\
        .order_by(Users.login)\
        .all()
    departments = Department.query.filter_by(active=True).all()

    return render_template('add_tmc.html',
                           organizations=organizations,
                           places=places,
                           users=users,
                           departments=departments,
                           datetime=datetime,
                           preselected_nome=preselected_nome,
                           preselected_group=preselected_group,
                           preselected_vendor=preselected_vendor)

@app.route('/edit/<int:tmc_id>', methods=['GET', 'POST'])
@login_required
def edit_tmc(tmc_id):
    """Редактирование ТМЦ."""
    tmc = Equipment.query.get_or_404(tmc_id)
    if request.method == 'POST':
        tmc.buhname = request.form['buhname']
        tmc.sernum = request.form.get('sernum', '')
        tmc.invnum = request.form.get('invnum', '')
        tmc.comment = request.form.get('comment', '')
        tmc.orgid = int(request.form['orgid'])
        tmc.placesid = int(request.form['placesid'])
        tmc.usersid = int(request.form['usersid'])
        department_id = request.form.get('department_id')
        tmc.department_id = int(department_id) if department_id else None

        # Обработка фото
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_image(file.filename):
                # Удаляем старое фото, если оно больше нигде не используется
                if tmc.photo:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], tmc.photo)
                    if os.path.exists(old_path):
                        other = Equipment.query.filter(
                            Equipment.photo == tmc.photo,
                            Equipment.id != tmc_id
                        ).first()
                        if not other:
                            os.remove(old_path)
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ext = filename.rsplit('.', 1)[1].lower()
                photo_filename = f"{timestamp}.{ext}" # <-- Убедитесь, что именно так
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
                tmc.photo = photo_filename

        # Обработка паспорта при редактировании
        if 'passport' in request.files:
            file = request.files['passport']
            if file and file.filename != '':
                if not allowed_document(file.filename):
                    flash('Файл паспорта должен быть в формате PDF (с расширением .pdf)', 'danger')
                    return redirect(request.url)
                # Удаляем старый паспорт
                if tmc.passport_filename:
                    old_path = os.path.join('static', 'passports', tmc.passport_filename)
                    if os.path.exists(old_path):
                        other = Equipment.query.filter(
                            Equipment.passport_filename == tmc.passport_filename,
                            Equipment.id != tmc.id
                        ).first()
                        if not other:
                            os.remove(old_path)
                # Сохраняем новый
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                passport_filename = f"passport_{timestamp}.pdf"
                passport_dir = os.path.join('static', 'passports')
                os.makedirs(passport_dir, exist_ok=True)
                file.save(os.path.join(passport_dir, passport_filename))
                tmc.passport_filename = passport_filename

        # else: файл не выбран — ничего не делаем, оставляем старое значение

         # Исправлено: убрано дублирующее присваивание tmc.nomeid
        tmc.nomeid = int(request.form['nomeid'])
         # Обработка стоимости
        cost_str = request.form.get('cost', '').strip()
        currentcost_str = request.form.get('currentcost', '').strip()
        try:
            tmc.cost = Decimal(cost_str) if cost_str else Decimal('0.00')
            tmc.currentcost = Decimal(currentcost_str) if currentcost_str else Decimal('0.00')
        except InvalidOperation:
            flash('Некорректный формат стоимости. Используйте формат: 12345.67', 'danger')
            return redirect(request.url)
        # === Обработка дат ===
        date_start_str = request.form.get('date_start')
        dtendgar_str = request.form.get('dtendgar')
        dtendlife_str = request.form.get('dtendlife')  # если будет поле ввода

        if date_start_str:
            date_start = datetime.strptime(date_start_str, '%Y-%m-%d')
            tmc.datepost = date_start  # ← основная дата
            # Автоматический пересчёт гарантии и срока службы
            if not dtendgar_str:
                tmc.dtendgar = (date_start + relativedelta(years=1)).date()
            if not dtendlife_str:
                tmc.dtendlife = (date_start + relativedelta(years=5)).date()


        # Если дата гарантии указана вручную — сохраняем её
        if dtendgar_str:
            tmc.dtendgar = datetime.strptime(dtendgar_str, '%Y-%m-%d').date()

        # Если дата срока службы указана вручную — сохраняем её
        if dtendlife_str:
            tmc.dtendlife = datetime.strptime(dtendlife_str, '%Y-%m-%d').date()

        if request.form.get('delete_passport'):
            if tmc.passport_filename:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], tmc.passport_filename)
                if os.path.exists(old_path):
                    # Проверяем, используется ли файл у других ТМЦ
                    other = Equipment.query.filter(
                        Equipment.passport_filename == tmc.passport_filename,
                        Equipment.id != tmc_id
                    ).first()
                    if not other:
                        os.remove(old_path)
                tmc.passport_filename = None  # Очищаем поле в БД

        db.session.commit()
        flash('ТМЦ успешно обновлён!', 'success')
        return redirect(url_for('list_by_nome', nome_id=tmc.nomeid))

    # GET: подготовка данных для формы
    organizations = Org.query.all()
    places = Places.query.all()
    users = db.session.query(Users)\
        .join(UsersRoles, Users.id == UsersRoles.userid)\
        .filter(Users.active == True, UsersRoles.role == 1)\
        .order_by(Users.login)\
        .all()
    groups = GroupNome.query.filter_by(active=True).all()
    departments = Department.query.filter_by(active=True).all()

    current_nome = Nome.query.get(tmc.nomeid)
    current_vendor = Vendor.query.get(current_nome.vendorid) if current_nome else None
    current_group = GroupNome.query.get(current_nome.groupid) if current_nome else None

    # Получаем вендоров и номенклатуру для динамических выпадающих списков
    vendors = []
    if current_group:
        vendors = db.session.query(Vendor).join(Nome, Vendor.id == Nome.vendorid)\
            .filter(Nome.groupid == current_group.id, Vendor.active == True)\
            .distinct().order_by(Vendor.name).all()

    nomenclatures = []
    if current_group and current_vendor:
        nomenclatures = Nome.query.filter_by(
            groupid=current_group.id,
            vendorid=current_vendor.id,
            active=True
        ).order_by(Nome.name).all()

    return render_template('edit_tmc.html',
                           tmc=tmc,
                           organizations=organizations,
                           places=places,
                           users=users,
                           groups=groups,
                           departments=departments,
                           current_group=current_group,
                           current_vendor=current_vendor,
                           current_nome=current_nome,
                           vendors=vendors,
                           nomenclatures=nomenclatures)


@app.route('/delete/<int:tmc_id>', methods=['POST'])
@login_required
def delete_tmc(tmc_id):
    tmc = Equipment.query.get_or_404(tmc_id)
    # Удаление фото
    if tmc.photo:
        path = os.path.join(app.config['UPLOAD_FOLDER'], tmc.photo)
        if os.path.exists(path):
            other = Equipment.query.filter(
                Equipment.photo == tmc.photo,
                Equipment.id != tmc_id
            ).first()
            if not other:
                os.remove(path)
    # Удаление паспорта
    if tmc.passport_filename:
        path = os.path.join('static', 'passports', tmc.passport_filename)
        if os.path.exists(path):
            other = Equipment.query.filter(
                Equipment.passport_filename == tmc.passport_filename,
                Equipment.id != tmc_id
            ).first()
            if not other:
                os.remove(path)
    db.session.delete(tmc)
    db.session.commit()
    flash('ТМЦ успешно удалён!', 'danger')
    return redirect(url_for('index'))


# === API для динамических выпадающих списков ===

@app.route('/get_vendors_by_group/<int:group_id>')
def get_vendors_by_group(group_id):
    """
    Возвращает список вендоров, у которых есть номенклатура в указанной группе.
    Исправлено: раньше возвращались все вендоры, теперь — только релевантные.
    """
    vendors = db.session.query(Vendor).join(Nome, Vendor.id == Nome.vendorid)\
        .filter(Nome.groupid == group_id, Vendor.active == True)\
        .distinct().order_by(Vendor.name).all()
    return {
        'vendors': [{'id': v.id, 'name': v.name} for v in vendors]
    }


@app.route('/get_nomenclatures_by_group_and_vendor/<int:group_id>/<int:vendor_id>')
def get_nomenclatures_by_group_and_vendor(group_id, vendor_id):
    """Возвращает номенклатуру по группе и вендору."""
    noms = Nome.query.filter_by(
        groupid=group_id,
        vendorid=vendor_id,
        active=True
    ).order_by(Nome.name).all()
    return {
        'nomenclatures': [{'id': n.id, 'name': n.name} for n in noms]
    }


@app.route('/add_nomenclature', methods=['POST'])
@login_required
def add_nomenclature():
    """Добавление новой номенклатуры через AJAX."""
    group_id = request.form.get('groupid', type=int)
    vendor_id = request.form.get('vendorid', type=int)
    name = request.form.get('name', '').strip()
    if not group_id or not vendor_id or not name:
        return {'success': False, 'message': 'Все поля обязательны'}, 400
    existing = Nome.query.filter_by(groupid=group_id, vendorid=vendor_id, name=name).first()
    if existing:
        return {'success': False, 'message': 'Такое наименование уже существует'}, 409
    new_nome = Nome(groupid=group_id, vendorid=vendor_id, name=name, active=True)
    db.session.add(new_nome)
    db.session.commit()
    return {'success': True, 'id': new_nome.id, 'name': new_nome.name}

@app.route('/edit_nome/<int:nome_id>', methods=['GET', 'POST'])
def edit_nome(nome_id):
    nome = Nome.query.get_or_404(nome_id)

    if request.method == 'POST':
        nome.name = request.form['name']
        nome.groupid = int(request.form['groupid'])
        nome.vendorid = int(request.form['vendorid'])

        # Обработка фото
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_image(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ext = filename.rsplit('.', 1)[1].lower()
                # --- ИСПРАВЛЕНИЕ: Добавляем поддиректорию ---
                # photo_filename = f"group_label/{timestamp}.{ext}" # <-- Удалить 'group_label/'
                photo_filename = f"{timestamp}.{ext}" # <-- Добавить эту строку
                group_label_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'group_label')
                os.makedirs(group_label_dir, exist_ok=True) # Убедимся, что папка существует
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

        db.session.commit()
        flash('Наименование успешно обновлено!', 'success')
        return redirect(url_for('index'))

    # Для GET: передаем данные для выпадающих списков
    groups = GroupNome.query.filter_by(active=True).all()
    vendors = Vendor.query.filter_by(active=True).all()

    return render_template('edit_nome.html', nome=nome, groups=groups, vendors=vendors)

@app.route('/bulk_edit_nome/<int:nome_id>', methods=['GET', 'POST'])
def bulk_edit_nome(nome_id):
    # Получаем все ТМЦ с этим nomeid
    tmc_list = Equipment.query.filter_by(nomeid=nome_id).all()
    if not tmc_list:
        flash('Нет ТМЦ с таким наименованием.', 'warning')
        return redirect(url_for('index'))
    # Получаем объект Nome для обновления фото
    nome = Nome.query.get_or_404(nome_id)
    # Получаем данные для выпадающего списка поставщиков
    suppliers = Knt.query.filter_by(active=1).all()
    if request.method == 'POST':
        try:
            # Обработка фото для группы
            if 'nome_photo' in request.files:
                file = request.files['nome_photo']
                if file and file.filename != '' and allowed_image(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    ext = filename.rsplit('.', 1)[1].lower()
                     # photo_filename = f"group_label/{timestamp}.{ext}" # <-- Удалить 'group_label/'
                    photo_filename = f"{timestamp}.{ext}" # <-- Добавить эту строку
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
                    # Удаляем старое фото из Nome, если оно больше нигде не используется
                    if nome.photo:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], nome.photo)
                        if os.path.exists(old_path):
                            # Проверяем, используется ли старое фото где-то в Equipment
                            other = Equipment.query.filter(Equipment.photo == nome.photo).first()
                            if not other:
                                os.remove(old_path)
                    # Устанавливаем новое фото для Nome
                    nome.photo = photo_filename
                    # Применяем это фото ко всем ТМЦ с пустым полем photo
                    for tmc in tmc_list:
                        if not tmc.photo:  # обрабатывает и None, и пустую строку
                            tmc.photo = photo_filename

            cost_str = request.form.get('cost', '').strip()
            currentcost_str = request.form.get('currentcost', '').strip()
            cost = Decimal(cost_str) if cost_str else Decimal('0.00')
            currentcost = Decimal(currentcost_str) if currentcost_str else Decimal('0.00')
            is_os = bool(request.form.get('os'))
            kntid = request.form.get('kntid')
            kntid = int(kntid) if kntid and kntid.isdigit() else None
            
            # === НОВЫЕ ПОЛЯ ===
            date_start_str = request.form.get('date_start')
            dtendgar_str = request.form.get('dtendgar')
            dtendlife_str = request.form.get('dtendlife')
            # Получаем комментарий из формы
            comment = request.form.get('comment', '').strip()
            apply_to_tmc = request.form.get('apply_to_tmc') is not None
            
            # Сохраняем комментарий для модели Nome
            nome.comment = comment if comment else None
            
            for tmc in tmc_list:
                tmc.cost = cost
                tmc.currentcost = currentcost
                tmc.os = is_os
                tmc.kntid = kntid
                # Устанавливаем комментарий
                if apply_to_tmc:
                    tmc.comment = comment if comment else None
                
                if date_start_str:
                    start_date = datetime.strptime(date_start_str, '%Y-%m-%d')
                    tmc.datepost = start_date
                    # Гарантия: если не задана — +1 год
                    if not dtendgar_str:
                        tmc.dtendgar = (start_date + relativedelta(years=1)).date()
                    else:
                        tmc.dtendgar = datetime.strptime(dtendgar_str, '%Y-%m-%d').date()
                    # Срок службы: если не задан — +5 лет
                    if not dtendlife_str:
                        tmc.dtendlife = (start_date + relativedelta(years=5)).date()
                    else:
                        tmc.dtendlife = datetime.strptime(dtendlife_str, '%Y-%m-%d').date()
                else:
                    # Если дата начала не указана — сохраняем только то, что вручную задано
                    if dtendgar_str:
                        tmc.dtendgar = datetime.strptime(dtendgar_str, '%Y-%m-%d').date()
                    if dtendlife_str:
                        tmc.dtendlife = datetime.strptime(dtendlife_str, '%Y-%m-%d').date()
            db.session.commit()
            flash(f'Групповое редактирование успешно выполнено для {len(tmc_list)} ТМЦ!', 'success')
            return redirect(url_for('index'))
        except (ValueError, InvalidOperation) as e:
            flash('Ошибка: Некорректный формат данных. Проверьте стоимость (например: 123.45) и даты (в формате ГГГГ-ММ-ДД).', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Произошла ошибка при сохранении: {str(e)}', 'danger')
    # Для GET-запроса: предзаполняем форму данными из первого ТМЦ
    first_tmc = tmc_list[0]
    return render_template('bulk_edit_nome.html',
                       nome=nome,
                       nome_id=nome_id,
                       nome_name=nome.name,
                       tmc_count=len(tmc_list),
                       first_tmc=first_tmc,
                       suppliers=suppliers)


@app.route('/list_by_nome/<int:nome_id>')
@login_required
def list_by_nome(nome_id):
    nome = Nome.query.get_or_404(nome_id)
    # Проверяем, является ли пользователь администратором
    is_admin = current_user.mode == 1

    # Получаем список ТМЦ, фильтруя по nomeid и, если пользователь не админ, по его id
    query = Equipment.query.filter_by(nomeid=nome_id)

    if not is_admin:
        query = query.filter_by(usersid=current_user.id)

    tmc_list = query.all()

    # Получаем шаблон комплекта для этого типа
    component_template = NomeComponents.query.filter_by(id_nome_main=nome_id).order_by(NomeComponents.sort_order).all()

    return render_template('list_by_nome.html',
                           nome=nome,
                           tmc_list=tmc_list,
                           component_template=component_template,
                           # Передаём переменную в шаблон, чтобы он знал, админ ли смотрит
                           is_admin=is_admin)

@app.route('/info_tmc/<int:tmc_id>')
@login_required
def info_tmc(tmc_id):
    tmc = Equipment.query.get_or_404(tmc_id)
    components = AppComponents.query.filter_by(id_main_asset=tmc.id).all()

    # Проверка: текущий пользователь — админ или владелец ТМЦ
    is_admin = current_user.mode == 1
    is_owner = (tmc.usersid == current_user.id)
    can_manage_temp = is_admin or is_owner

    # Получаем активную временную выдачу (если есть)
    active_usage = None
    if can_manage_temp:
        active_usage = EquipmentTempUsage.query.filter_by(
            equipment_id=tmc_id,
            returned=False
        ).first()

    # Список пользователей с ролью 2 (для формы выдачи)
    users_role_2 = []
    if can_manage_temp and not active_usage:
        users_role_2 = db.session.query(Users).join(UsersRoles, Users.id == UsersRoles.userid)\
            .filter(UsersRoles.role == 2, Users.active == True)\
            .order_by(Users.login).all()

    return render_template('info_tmc.html',
                           tmc=tmc,
                           components=components,
                           can_manage_temp=can_manage_temp,
                           active_usage=active_usage,
                           users_role_2=users_role_2)

@app.route('/add_nome', methods=['GET', 'POST'])
@login_required
def add_nome():
    """Добавление нового наименования (группы ТМЦ) с указанием количества ТМЦ."""
    if request.method == 'POST':
        name = request.form['name'].strip()
        group_id = int(request.form['groupid'])
        vendor_id = int(request.form['vendorid'])
        quantity = int(request.form.get('quantity', 1))
        date_start_str = request.form.get('date_start')
        placesid = int(request.form.get('placesid', 0))
        sernum = request.form.get('sernum', '')
        invnum = request.form.get('invnum', '')
        usersid = int(request.form['usersid'])  # ← НОВОЕ: выбранный МОЛ
        cost_str = request.form.get('cost', '').strip()  # ← НОВОЕ: стоимость
        comment = request.form.get('comment', '').strip()  # ← НОВОЕ: комментарий к наименованию

        if not name:
            flash('Наименование не может быть пустым', 'danger')
            return redirect(url_for('add_nome'))
        if not date_start_str:
            flash('Дата постановки на учет обязательна', 'danger')
            return redirect(url_for('add_nome'))
        if placesid <= 0:
            flash('Место установки обязательно', 'danger')
            return redirect(url_for('add_nome'))
        if quantity < 1:
            flash('Количество должно быть не менее 1', 'danger')
            return redirect(url_for('add_nome'))

        # Проверка дубликата наименования
        existing = Nome.query.filter_by(groupid=group_id, vendorid=vendor_id, name=name).first()
        if existing:
            flash('Такое наименование уже существует в этой группе и у этого производителя', 'warning')
            return redirect(url_for('add_nome'))

        # Обработка фото группы
        photo_filename = ''
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_image(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ext = filename.rsplit('.', 1)[1].lower()
                # photo_filename = f"group_label/{timestamp}.{ext}" # <-- Удалить 'group_label/'
                photo_filename = f"{timestamp}.{ext}" # <-- Добавить эту строку
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
            else:
                flash('Если загружаете фото, оно должно быть в допустимом формате', 'warning')

        # Парсим стоимость
        try:
            cost = Decimal(cost_str) if cost_str else Decimal('0.00')
        except (ValueError, InvalidOperation):
            cost = Decimal('0.00')

        # Создаём наименование с комментарием
        new_nome = Nome(
            groupid=group_id,
            vendorid=vendor_id,
            name=name,
            active=True,
            photo=photo_filename,
            comment=comment or None  # ← комментарий только к наименованию
        )
        db.session.add(new_nome)
        db.session.flush()  # чтобы получить new_nome.id

        # Парсим дату
        date_start = datetime.strptime(date_start_str, '%Y-%m-%d')
        dtendgar = (date_start + relativedelta(years=1)).date()
        dtendlife = (date_start + relativedelta(years=5)).date()
        orgid = current_user.orgid

        # Создаём указанное количество ТМЦ
        for i in range(quantity):
            tmc_sernum = sernum if i == 0 else ''
            tmc_invnum = invnum if i == 0 else ''
            tmc_photo = photo_filename

            new_tmc = Equipment(
                buhname=name,
                sernum=tmc_sernum,
                invnum=tmc_invnum,
                comment='',  # ← НЕ дублируем комментарий в каждый ТМЦ!
                orgid=orgid,
                placesid=placesid,
                usersid=usersid,  # ← выбранный МОЛ
                nomeid=new_nome.id,
                department_id=None,
                photo=tmc_photo,
                passport_filename='',
                kntid=None,
                datepost=date_start,
                dtendgar=dtendgar,
                dtendlife=dtendlife,
                cost=cost,
                currentcost=cost,
                os=True,
                mode=False,
                repair=False,
                active=True,
                ip='',
                mapx='',
                mapy='',
                mapmoved=0,
                mapyet=False,
                tmcgo=0,
            )
            db.session.add(new_tmc)

        try:
            db.session.commit()
            flash(f'Новое наименование и {quantity} ТМЦ успешно добавлены!', 'success')
            return redirect(url_for('list_by_nome', nome_id=new_nome.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении: {str(e)}', 'danger')
            return redirect(url_for('add_nome'))

    # GET
    groups = GroupNome.query.filter_by(active=True).all()
    vendors = Vendor.query.filter_by(active=True).all()
    places = Places.query.filter_by(active=True).all()
    # Только активные пользователи, имеющие роль 1 (МОЛ с Full доступ, не путать с Admin)
    users = db.session.query(Users).join(UsersRoles, Users.id == UsersRoles.userid)\
        .filter(Users.active == True, UsersRoles.role == 1)\
        .order_by(Users.login).all()
    return render_template('add_nome.html', groups=groups, vendors=vendors, places=places, users=users)

@app.route('/invoice_list')
@login_required
def invoice_list():
    """Список накладных: для Admin — все, для МОЛ — только связанные с ним."""
    is_admin = current_user.mode == 1

    if is_admin:
        # Админ видит всё
        invoices = Invoices.query.options(
            db.joinedload(Invoices.department),
            db.joinedload(Invoices.from_user),
            db.joinedload(Invoices.to_user),
            db.joinedload(Invoices.from_knt),
            db.joinedload(Invoices.to_knt)
        ).order_by(
            Invoices.invoice_date.desc(),
            Invoices.invoice_number.desc()
        ).all()
    else:
        # Получаем ID накладных, где пользователь — отправитель или получатель
        direct_ids = {
            id for (id,) in db.session.query(Invoices.id).filter(
                db.or_(
                    Invoices.from_user_id == current_user.id,
                    Invoices.to_user_id == current_user.id
                )
            ).all()
        }

        # Получаем ID накладных, где есть ТМЦ пользователя
        indirect_ids = {
            id for (id,) in db.session.query(Invoices.id)
            .join(InvoiceEquipment, Invoices.id == InvoiceEquipment.invoice_id)
            .join(Equipment, InvoiceEquipment.equipment_id == Equipment.id)
            .filter(Equipment.usersid == current_user.id)
            .all()
        }

        all_ids = list(direct_ids | indirect_ids)

        if all_ids:
            invoices = Invoices.query.options(
                db.joinedload(Invoices.department),
                db.joinedload(Invoices.from_user),
                db.joinedload(Invoices.to_user),
                db.joinedload(Invoices.from_knt),
                db.joinedload(Invoices.to_knt)
            ).filter(
                Invoices.id.in_(all_ids)
            ).order_by(
                Invoices.invoice_date.desc(),
                Invoices.invoice_number.desc()
            ).all()
        else:
            invoices = []

    return render_template('invoice_list.html', invoices=invoices)


@app.route('/create_invoice', methods=['GET', 'POST'])
@login_required
def create_invoice():
    # Справочники
    departments = Department.query.filter_by(active=True).all()
    users = Users.query.filter_by(active=True).all()
    warehouses = Knt.query.filter_by(supplier=0, bayer=0, active=1).all()  # ← склады

    if request.method == 'POST':
        inv_type = request.form['type']
        from_user_id = request.form.get('from_user_id')
        to_user_id = request.form.get('to_user_id')
        from_knt_id = request.form.get('from_knt_id')
        to_knt_id = request.form.get('to_knt_id')

        # Безопасное преобразование строки → int или None
        def to_int_or_none(val):
            if not val:
                return None
            try:
                return int(val)
            except ValueError:
                return None

        from_user_id = to_int_or_none(from_user_id)
        to_user_id = to_int_or_none(to_user_id)
        from_knt_id = to_int_or_none(from_knt_id)
        to_knt_id = to_int_or_none(to_knt_id)

        # Валидация по типу
        if inv_type == 'Склад-МОЛ':
            if not from_knt_id or not to_user_id:
                flash('Для типа "Склад → МОЛ" укажите склад и получателя', 'danger')
                return redirect(request.url)
        elif inv_type == 'МОЛ-Склад':
            if not from_user_id or not to_knt_id:
                flash('Для типа "МОЛ → Склад" укажите отправителя и склад', 'danger')
                return redirect(request.url)
        elif inv_type == 'МОЛ-МОЛ':
            if not from_user_id or not to_user_id:
                flash('Для типа "МОЛ → МОЛ" укажите отправителя и получателя', 'danger')
                return redirect(request.url)
        else:
            flash('Некорректный тип накладной', 'danger')
            return redirect(request.url)

        # --- Общая логика для всех типов ---

        try:
            # Получаем данные из формы (предполагается, что они есть)
            invoice_number = request.form['invoice_number']
            invoice_date = datetime.strptime(request.form['invoice_date'], '%Y-%m-%d').date()
            department_id = request.form.get('department_id')
            equipment_ids = request.form.getlist('equipment_ids')  # список ID оборудования

            # 3. Сохраняем PDF
            pdf_path = ''
            if 'pdf_file' in request.files:
                file = request.files['pdf_file']
                if file and file.filename != '' and allowed_document(file.filename):
                    filename = secure_filename(file.filename)
                    upload_dir = os.path.join('static', 'invoices')
                    os.makedirs(upload_dir, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    pdf_filename = f"{invoice_number}_{timestamp}.pdf"
                    file_path = os.path.join(upload_dir, pdf_filename)
                    file.save(file_path)
                    pdf_path = f"invoices/{pdf_filename}"  # относительный путь для static/
                else:
                    flash('PDF обязателен и должен быть в допустимом формате', 'danger')
                    return redirect(request.url)
            else:
                flash('PDF обязателен', 'danger')
                return redirect(request.url)

            # 4. Создаём накладную
            new_invoice = Invoices(
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                department_id=department_id,
                type=inv_type,
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                from_knt_id=from_knt_id,
                to_knt_id=to_knt_id,
                pdf_path=pdf_path
            )
            db.session.add(new_invoice)
            db.session.flush()  # чтобы получить new_invoice.id

            # 5. Связываем оборудование
            for eq_id in equipment_ids:
                eq = Equipment.query.get(eq_id)
                if eq:
                    # Обновляем владельца оборудования
                    if to_user_id:
                        eq.usersid = to_user_id
                    # (место можно обновлять по логике, но пока не трогаем)

                    # Связь в invoice_equipment
                    ie = InvoiceEquipment(invoice_id=new_invoice.id, equipment_id=eq.id)
                    db.session.add(ie)

                    # 6. Запись в move (перемещение)
                    move_record = Move(
                        eqid=eq.id,
                        dt=datetime.combine(invoice_date, datetime.min.time()),
                        orgidfrom=eq.orgid,
                        orgidto=eq.orgid,  # та же организация
                        placesidfrom=eq.placesid,
                        placesidto=eq.placesid,  # пока не меняем место
                        useridfrom=from_user_id or current_user.id,
                        useridto=to_user_id or current_user.id,
                        comment=f'Передача по накладной {invoice_number}'
                    )
                    db.session.add(move_record)

            db.session.commit()
            flash(f'Накладная {invoice_number} успешно создана!', 'success')
            return redirect(url_for('invoice_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании накладной: {str(e)}', 'danger')
            return redirect(request.url)

    # GET-запрос
    from_user_id = request.args.get('from_user_id', type=int)
    if from_user_id:
        equipment_list = Equipment.query.filter_by(
            usersid=from_user_id,
            active=True
        ).join(Nome).order_by(Nome.name).all()
    else:
        equipment_list = []  # ← всегда определена!

    departments = Department.query.filter_by(active=True).all()
    users = Users.query.filter_by(active=True).all()
    return render_template('create_invoice.html',
                           departments=departments,
                           users=users,
                           warehouses=warehouses,    
                           equipment_list=equipment_list,
                           now_date=date.today())


@app.route('/api/equipment_by_user/<int:user_id>')
@login_required
def equipment_by_user(user_id):
    equipment = Equipment.query.filter_by(usersid=user_id, active=True)\
        .join(Nome).order_by(Nome.name).all()
    return {
        'equipment': [
            {
                'id': eq.id,
                'buhname': eq.buhname,
                'sernum': eq.sernum or '—',
                'invnum': eq.invnum or '—',
                'login': eq.users.login if eq.users else '—'
            }
            for eq in equipment
        ]
    }

@app.route('/invoice/<int:invoice_id>')
@login_required
def invoice_detail(invoice_id):
    """Просмотр деталей накладной."""
    invoice = Invoices.query.options(
        db.joinedload(Invoices.department),
        db.joinedload(Invoices.from_user),
        db.joinedload(Invoices.to_user),
        db.joinedload(Invoices.from_knt),
        db.joinedload(Invoices.to_knt),
        db.joinedload(Invoices.invoice_equipment).joinedload(InvoiceEquipment.equipment).joinedload(Equipment.nome)
    ).get_or_404(invoice_id)

    # Подсчёт количества и общей стоимости
    equipment_items = [ie.equipment for ie in invoice.invoice_equipment]
    tmc_count = len(equipment_items)
    total_cost = sum(eq.cost for eq in equipment_items if eq.cost is not None)

    return render_template('invoice_detail.html', invoice=invoice, tmc_count=tmc_count, total_cost=total_cost)

@app.route('/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    invoice = Invoices.query.get_or_404(invoice_id)
    departments = Department.query.filter_by(active=True).all()
    users = Users.query.filter_by(active=True).all()
    warehouses = Knt.query.filter_by(supplier=0, bayer=0, active=1).all()

    # === Обработка AJAX-запросов на добавление/удаление ТМЦ ===
    if request.method == 'POST' and request.is_json:
        data = request.get_json()
        action = data.get('action')
        eq_id = data.get('eq_id')

        if action == 'add':
            eq = Equipment.query.get(eq_id)
            if not eq:
                return {'success': False, 'error': 'ТМЦ не найден'}, 404
            # Проверяем, не добавлен ли уже
            existing = InvoiceEquipment.query.filter_by(
                invoice_id=invoice_id, equipment_id=eq_id
            ).first()
            if existing:
                return {'success': False, 'error': 'ТМЦ уже в накладной'}, 400
            # Добавляем связь
            ie = InvoiceEquipment(invoice_id=invoice_id, equipment_id=eq_id)
            db.session.add(ie)
            db.session.commit()
            return {'success': True}

        elif action == 'remove':
            ie = InvoiceEquipment.query.filter_by(
                invoice_id=invoice_id, equipment_id=eq_id
            ).first()
            if not ie:
                return {'success': False, 'error': 'ТМЦ не найден в накладной'}, 404
            db.session.delete(ie)
            db.session.commit()
            return {'success': True}

        return {'success': False, 'error': 'Недопустимое действие'}, 400

    # === Обработка обычной формы редактирования (не AJAX) ===
    if request.method == 'POST' and not request.is_json:
        # ... (оставьте текущий код обработки формы без изменений)
        inv_type = request.form['type']
        from_user_id = request.form.get('from_user_id')
        to_user_id = request.form.get('to_user_id')
        from_knt_id = request.form.get('from_knt_id')
        to_knt_id = request.form.get('to_knt_id')
        def to_int_or_none(val):
            return int(val) if val and val.isdigit() else None
        from_user_id = to_int_or_none(from_user_id)
        to_user_id = to_int_or_none(to_user_id)
        from_knt_id = to_int_or_none(from_knt_id)
        to_knt_id = to_int_or_none(to_knt_id)

        if inv_type == 'Склад-МОЛ':
            if not from_knt_id or not to_user_id:
                flash('Для типа "Склад → МОЛ" укажите склад и получателя', 'danger')
                return redirect(request.url)
        elif inv_type == 'МОЛ-Склад':
            if not from_user_id or not to_knt_id:
                flash('Для типа "МОЛ → Склад" укажите отправителя и склад', 'danger')
                return redirect(request.url)
        elif inv_type == 'МОЛ-МОЛ':
            if not from_user_id or not to_user_id:
                flash('Для типа "МОЛ → МОЛ" укажите отправителя и получателя', 'danger')
                return redirect(request.url)

        invoice.invoice_number = request.form['invoice_number']
        invoice.invoice_date = datetime.strptime(request.form['invoice_date'], '%Y-%m-%d').date()
        invoice.department_id = to_int_or_none(request.form.get('department_id'))
        invoice.type = inv_type
        invoice.from_user_id = from_user_id
        invoice.to_user_id = to_user_id
        invoice.from_knt_id = from_knt_id
        invoice.to_knt_id = to_knt_id

        if 'pdf_file' in request.files:
            file = request.files['pdf_file']
            if file and file.filename != '' and allowed_document(file.filename):
                upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'invoices')
                os.makedirs(upload_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pdf_filename = f"{invoice.invoice_number}_{timestamp}.pdf"
                file_path = os.path.join(upload_dir, pdf_filename)
                file.save(file_path)
                if invoice.pdf_path:
                    old_path = os.path.join('static', invoice.pdf_path)
                    if os.path.exists(old_path):
                        other = Invoices.query.filter(Invoices.pdf_path == invoice.pdf_path,
                                                      Invoices.id != invoice.id).first()
                        if not other:
                            os.remove(old_path)
                invoice.pdf_path = f"invoices/{pdf_filename}"

        db.session.commit()
        flash('Накладная успешно обновлена!', 'success')
        return redirect(url_for('invoice_detail', invoice_id=invoice.id))

    # === GET: предзаполняем форму ===
    # Получаем текущие ТМЦ в накладной
    current_eqs = [ie.equipment for ie in invoice.invoice_equipment]

    # Определяем доступные ТМЦ в зависимости от типа накладной
    available_eqs = []
    if invoice.type == 'МОЛ-МОЛ':
        from_user_id = invoice.from_user_id
        to_user_id = invoice.to_user_id
        department_id = invoice.department_id  # ← берём отдел из накладной

        if from_user_id or to_user_id:
            query = Equipment.query.filter(
                Equipment.active == True,
                db.or_(
                    Equipment.usersid == from_user_id,
                    Equipment.usersid == to_user_id
                )
            )
            # ← ДОБАВЛЕН ФИЛЬТР ПО ОТДЕЛУ
            if department_id:
                query = query.filter(Equipment.department_id == department_id)

            query = query.outerjoin(InvoiceEquipment, db.and_(
                InvoiceEquipment.equipment_id == Equipment.id,
                InvoiceEquipment.invoice_id == invoice_id
            )).filter(InvoiceEquipment.id.is_(None))

            available_eqs = query.all()

    elif invoice.type == 'МОЛ-Склад':
        if invoice.from_user_id:
            query = Equipment.query.filter_by(
                usersid=invoice.from_user_id, active=True
            )
            # ← ДОБАВЛЕН ФИЛЬТР ПО ОТДЕЛУ
            if invoice.department_id:
                query = query.filter(Equipment.department_id == invoice.department_id)

            available_eqs = query.outerjoin(InvoiceEquipment, db.and_(
                InvoiceEquipment.equipment_id == Equipment.id,
                InvoiceEquipment.invoice_id == invoice_id
            )).filter(InvoiceEquipment.id.is_(None)).all()

    # Для Склад-МОЛ список остаётся пустым (логично)
    elif invoice.type == 'Склад-МОЛ':
        # Для типа Склад-МОЛ добавление ТМЦ через этот интерфейс не поддерживается
        # (склад не владеет ТМЦ)
        pass  # available_eqs останется пустым

    return render_template('edit_invoice.html',
                        invoice=invoice,
                        departments=departments,
                        users=users,
                        warehouses=warehouses,
                        current_eqs=current_eqs,
                        available_eqs=available_eqs,
                        now_date=date.today())

@app.route('/delete_invoice/<int:invoice_id>', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    invoice = Invoices.query.get_or_404(invoice_id)

    # Удаляем PDF-файл, если он больше нигде не используется
    if invoice.pdf_path:
        pdf_full_path = os.path.join('static', invoice.pdf_path)
        if os.path.exists(pdf_full_path):
            other_invoice = Invoices.query.filter(
                Invoices.pdf_path == invoice.pdf_path,
                Invoices.id != invoice_id
            ).first()
            if not other_invoice:
                os.remove(pdf_full_path)

    # Удаляем связанные записи из invoice_equipment и move (опционально — можно оставить для истории)
    # В данном случае удалим только invoice_equipment
    InvoiceEquipment.query.filter_by(invoice_id=invoice_id).delete()

    # Удаляем саму накладную
    db.session.delete(invoice)
    db.session.commit()

    flash('Накладная удалена.', 'warning')
    return redirect(url_for('invoice_list'))

@app.route('/all_tmc')
@login_required
def all_tmc():
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    
    filter_user_id = request.args.get('user_id', type=int)
    filter_department_id = request.args.get('department_id', type=int)
    filter_category_id = request.args.get('category_id', type=int)
    
    # Базовый запрос для фильтрации
    base_query = Equipment.query.filter_by(active=True, os=True)
    
    # Применяем фильтры
    if filter_user_id:
        base_query = base_query.filter_by(usersid=filter_user_id)
    if filter_department_id:
        base_query = base_query.filter_by(department_id=filter_department_id)
    if filter_category_id:
        base_query = base_query.join(Nome, Equipment.nomeid == Nome.id)\
                              .join(GroupNome, Nome.groupid == GroupNome.id)\
                              .filter(GroupNome.category_id == filter_category_id)
    
    # Подсчет общего количества и стоимости
    tmc_count = base_query.count()
    total_cost = db.session.query(func.coalesce(func.sum(Equipment.cost), 0))\
                          .select_from(Equipment)\
                          .filter(Equipment.id.in_([eq.id for eq in base_query.all()]))\
                          .scalar() or 0
    
    # Запрос для группировки (используем тот же фильтр)
    grouped_query = db.session.query(
        Equipment.nomeid,
        func.coalesce(Nome.name, '⚠️ Неизвестное наименование').label('nome_name'),
        func.count(Equipment.id).label('quantity'),
        func.coalesce(Nome.photo, '').label('nome_photo')
    ).join(Nome, Equipment.nomeid == Nome.id)\
     .filter(Equipment.id.in_([eq.id for eq in base_query.all()]))\
     .group_by(Equipment.nomeid, Nome.name, Nome.photo)\
     .order_by(Nome.name)
    
    grouped_tmc = grouped_query.all()
    
    # Загрузка данных для фильтров (пользователи, отделы, категории)
    all_users = Users.query.join(Equipment, Users.id == Equipment.usersid)\
                          .filter(Equipment.active == True, Equipment.os == True)\
                          .distinct().order_by(Users.login).all()
    
    all_departments = Department.query.join(Equipment, Department.id == Equipment.department_id)\
                                      .filter(Equipment.active == True, Equipment.os == True)\
                                      .distinct().order_by(Department.name).all()
    
    all_categories = Category.query.join(GroupNome, Category.id == GroupNome.category_id)\
                                   .join(Nome, GroupNome.id == Nome.groupid)\
                                   .join(Equipment, Nome.id == Equipment.nomeid)\
                                   .filter(Equipment.active == True, Equipment.os == True)\
                                   .distinct().order_by(Category.name).all()
    
    return render_template('all_tmc.html',
                           grouped_tmc=grouped_tmc,
                           all_users=all_users,
                           all_departments=all_departments,
                           all_categories=all_categories,
                           filter_user_id=filter_user_id,
                           filter_department_id=filter_department_id,
                           filter_category_id=filter_category_id,
                           tmc_count=tmc_count,
                           total_cost=total_cost,
                           user_login=current_user.login,
                           is_admin=is_admin)


@app.route('/my_tmc', endpoint='my_tmc')
@login_required
def list_my_tmc():
    is_admin = current_user.mode == 1
    if is_admin:
        return redirect(url_for('all_tmc'))

    # Фильтрация по текущему пользователю
    filter_department_id = request.args.get('department_id', type=int)
    filter_category_id = request.args.get('category_id', type=int)

    # Базовый запрос
    base_query = Equipment.query.filter_by(
        usersid=current_user.id,
        active=True,
        os=True
    )

    # Применение фильтров
    if filter_department_id:
        base_query = base_query.filter_by(department_id=filter_department_id)
    if filter_category_id:
        base_query = base_query.join(Nome, Equipment.nomeid == Nome.id)\
                               .join(GroupNome, Nome.groupid == GroupNome.id)\
                               .filter(GroupNome.category_id == filter_category_id)

    # Подсчёт
    tmc_count = base_query.count()
    total_cost = db.session.query(func.coalesce(func.sum(Equipment.cost), 0))\
                          .select_from(Equipment)\
                          .filter(Equipment.id.in_(base_query.with_entities(Equipment.id)))\
                          .scalar() or 0

    # Группировка
    grouped_query = db.session.query(
        Equipment.nomeid,
        func.coalesce(Nome.name, '⚠️ Неизвестное наименование').label('nome_name'),
        func.count(Equipment.id).label('quantity'),
        func.coalesce(Nome.photo, '').label('nome_photo')
    ).select_from(Equipment)\
     .join(Nome, Equipment.nomeid == Nome.id)

    # Применяем те же фильтры
    if filter_department_id:
        grouped_query = grouped_query.filter(Equipment.department_id == filter_department_id)
    if filter_category_id:
        grouped_query = grouped_query.join(GroupNome, Nome.groupid == GroupNome.id)\
                                     .filter(GroupNome.category_id == filter_category_id)

    grouped_query = grouped_query.filter(
        Equipment.usersid == current_user.id,
        Equipment.active == True,
        Equipment.os == True
    ).group_by(Equipment.nomeid, Nome.name, Nome.photo)\
     .order_by(Nome.name)

    grouped_tmc = grouped_query.all()

    # Загрузка фильтров
    all_departments = Department.query.join(Equipment, Department.id == Equipment.department_id)\
                                      .filter(Equipment.usersid == current_user.id,
                                              Equipment.active == True,
                                              Equipment.os == True)\
                                      .distinct().order_by(Department.name).all()

    all_categories = Category.query.join(GroupNome, Category.id == GroupNome.category_id)\
                                   .join(Nome, GroupNome.id == Nome.groupid)\
                                   .join(Equipment, Nome.id == Equipment.nomeid)\
                                   .filter(Equipment.usersid == current_user.id,
                                           Equipment.active == True,
                                           Equipment.os == True)\
                                   .distinct().order_by(Category.name).all()

    return render_template('my_tmc.html',
                           grouped_tmc=grouped_tmc,
                           tmc_count=tmc_count,
                           total_cost=total_cost,
                           filter_department_id=filter_department_id,
                           filter_category_id=filter_category_id,
                           all_departments=all_departments,
                           all_categories=all_categories,
                           user_login=current_user.login)
# app.py (вставьте этот маршрут в соответствующее место)
@app.route('/manage_categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        action = request.form.get('action')
        group_nome_id = request.form.get('group_nome_id', type=int)
        category_id = request.form.get('category_id', type=int)

        if action == 'assign' and group_nome_id and category_id:
            # Присвоить категорию группе
            group = GroupNome.query.get_or_404(group_nome_id)
            group.category_id = category_id
            db.session.commit()
            flash(f'Группа "{group.name}" успешно привязана к категории.', 'success')
        elif action == 'remove' and group_nome_id:
            # Удалить привязку категории
            group = GroupNome.query.get_or_404(group_nome_id)
            old_category_name = group.category.name if group.category else "Неизвестная"
            group.category_id = None
            db.session.commit()
            flash(f'Категория успешно отвязана от группы "{group.name}". Была: {old_category_name}', 'info')
        else:
            flash('Некорректные данные для действия.', 'danger')

        return redirect(url_for('manage_categories'))

    # GET: отображение страницы
    all_groups = GroupNome.query.filter_by(active=True).all()
    all_categories = Category.query.filter_by(active=True).all()

    # Группы, которые не привязаны ни к одной категории
    unassigned_groups = [g for g in all_groups if g.category_id is None]
    # Группы, которые уже привязаны к категориям
    assigned_groups = [g for g in all_groups if g.category_id is not None]

    return render_template('manage_categories.html',
                           all_groups=all_groups,
                           all_categories=all_categories,
                           unassigned_groups=unassigned_groups,
                           assigned_groups=assigned_groups)

@app.route('/all_components')
@login_required
def all_components():
    # Только для администраторов
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))

    # Фильтруем только НЕ основные средства
    base_query = Equipment.query.filter_by(active=True, os=False)

    # Применяем фильтры (по пользователю, отделу, категории — по аналогии с all_tmc)
    filter_user_id = request.args.get('user_id', type=int)
    filter_department_id = request.args.get('department_id', type=int)
    filter_category_id = request.args.get('category_id', type=int)

    if filter_user_id:
        base_query = base_query.filter_by(usersid=filter_user_id)
    if filter_department_id:
        base_query = base_query.filter_by(department_id=filter_department_id)
    if filter_category_id:
        base_query = base_query.join(Nome, Equipment.nomeid == Nome.id)\
                                .join(GroupNome, Nome.groupid == GroupNome.id)\
                                .filter(GroupNome.category_id == filter_category_id)

    equipment_list = base_query.all()
    tmc_count = len(equipment_list)
    total_cost = sum(eq.cost for eq in equipment_list if eq.cost is not None)

    grouped_query = db.session.query(
        Equipment.nomeid,
        func.coalesce(Nome.name, '⚠️ Неизвестное наименование').label('nome_name'),
        func.count(Equipment.id).label('quantity'),
        func.coalesce(Nome.photo, '').label('nome_photo')
    ).join(Nome, Equipment.nomeid == Nome.id)\
     .join(GroupNome, Nome.groupid == GroupNome.id) \
     .filter(Equipment.active == True, Equipment.os == False)

    if filter_user_id:
        grouped_query = grouped_query.filter(Equipment.usersid == filter_user_id)
    if filter_department_id:
        grouped_query = grouped_query.filter(Equipment.department_id == filter_department_id)
    if filter_category_id:
        grouped_query = grouped_query.filter(GroupNome.category_id == filter_category_id)

    grouped_tmc = grouped_query.group_by(Equipment.nomeid, Nome.name, Nome.photo)\
                               .order_by(GroupNome.name, Nome.name) \
                               .all()

    # Списки для фильтров (только те, у кого есть комплектующие)
    active_users_ids = db.session.query(Equipment.usersid)\
        .filter(Equipment.active == True, Equipment.os == False)\
        .distinct().subquery()
    all_users = Users.query.filter(Users.id.in_(active_users_ids), Users.active == True).all()

    active_departments_ids = db.session.query(Equipment.department_id)\
        .filter(Equipment.active == True, Equipment.os == False)\
        .filter(Equipment.department_id.isnot(None))\
        .distinct().subquery()
    all_departments = Department.query.filter(Department.id.in_(active_departments_ids), Department.active == True).all()

    active_categories_ids = db.session.query(Category.id)\
        .join(GroupNome, Category.id == GroupNome.category_id)\
        .join(Nome, GroupNome.id == Nome.groupid)\
        .join(Equipment, Nome.id == Equipment.nomeid)\
        .filter(Equipment.active == True, Equipment.os == False, Category.active == True)\
        .distinct().subquery()
    all_categories = Category.query.filter(Category.id.in_(active_categories_ids), Category.active == True).all()

    return render_template('all_components.html',
                           grouped_tmc=grouped_tmc,
                           all_users=all_users,
                           all_departments=all_departments,
                           all_categories=all_categories,
                           filter_user_id=filter_user_id,
                           filter_department_id=filter_department_id,
                           filter_category_id=filter_category_id,
                           tmc_count=tmc_count,
                           total_cost=total_cost,
                           user_login=current_user.login,
                           is_admin=is_admin)

@app.route('/add_component', methods=['GET', 'POST'])
@login_required
def add_component():
    """Добавление нового комплектующего (не ОС)."""
    if request.method == 'POST':
        # Получаем данные формы
        nomeid = int(request.form['nomeid'])
        buhname = request.form['buhname']
        sernum = request.form.get('sernum', '')
        invnum = request.form.get('invnum', '')
        comment = request.form.get('comment', '')
        orgid = int(request.form['orgid'])
        placesid = int(request.form['placesid'])
        usersid = int(request.form['usersid'])
        department_id = request.form.get('department_id')
        department_id = int(department_id) if department_id else None

        # === Связь с основным средством ===
        main_asset_id = request.form.get('main_asset_id')
        main_asset_id = int(main_asset_id) if main_asset_id else None

        # Обработка фото (опционально)
        photo_filename = ''
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_image(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ext = filename.rsplit('.', 1)[1].lower()
                photo_filename = f"group_label/{timestamp}.{ext}"
                group_label_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'group_label')
                os.makedirs(group_label_dir, exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

        # Создаём комплектующее как Equipment с os=False
        new_component = Equipment(
            buhname=buhname,
            sernum=sernum,
            invnum=invnum,
            comment=comment,
            orgid=orgid,
            placesid=placesid,
            usersid=usersid,
            nomeid=nomeid,
            department_id=department_id,
            photo=photo_filename,
            passport_filename='',  # ← паспорт не нужен для комплектующих
            kntid=None,
            datepost=datetime.utcnow(),
            date_start=date.today(),
            cost=Decimal('0.00'),      # ← можно не указывать стоимость
            currentcost=Decimal('0.00'),
            os=False,                  # ← КЛЮЧЕВОЕ: это НЕ основное средство
            mode=False,
            repair=False,
            active=True,
            ip='',
            mapx='',
            mapy='',
            mapmoved=0,
            mapyet=False,
            tmcgo=0,
            dtendgar=date.today(),     # ← можно оставить "сегодня" или None
            dtendlife=None,
        )

        try:
            db.session.add(new_component)
            db.session.flush()  # чтобы получить new_component.id

            # Если указано основное средство — создаём связь в app_components
            if main_asset_id:
                link = AppComponents(
                    id_main_asset=main_asset_id,
                    id_nome_component=nomeid,
                    ser_num_component=sernum,
                    comment_component=comment,
                )
                db.session.add(link)

            db.session.commit()
            flash('Комплектующее успешно добавлено!', 'success')
            return redirect(url_for('all_components'))  # или index

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении: {str(e)}', 'danger')
            return redirect(url_for('add_component'))

    # GET: подготовка данных
    organizations = Org.query.all()
    places = Places.query.all()
    users = db.session.query(Users)\
        .join(UsersRoles, Users.id == UsersRoles.userid)\
        .filter(Users.active == True, UsersRoles.role == 1)\
        .order_by(Users.login)\
        .all()
    departments = Department.query.filter_by(active=True).all()

    # Только те группы, где nome.is_component = 1 ИЛИ где group_nome.category относится к "Комплектующим"
    # Но проще: фильтруем Nome по is_component=1
    component_groups = db.session.query(GroupNome)\
        .join(Nome, GroupNome.id == Nome.groupid)\
        .filter(Nome.is_component == True)\
        .distinct().all()

    # Также передадим список основных средств для привязки (опционально)
    main_assets = Equipment.query.filter_by(active=True, os=True).all()

    return render_template('add_component.html',
                        organizations=organizations,
                        places=places,
                        users=users,
                        departments=departments,
                        component_groups=component_groups,
                        main_assets=main_assets,
                        datetime=datetime,
                        vendors=[],          # ← добавлено
                        nomenclatures=[])    # ← добавлено

@app.route('/edit_component/<int:component_id>', methods=['GET', 'POST'])
@login_required
def edit_component(component_id):
    """Редактирование комплектующего (os=False)."""
    component = Equipment.query.get_or_404(component_id)

    # Проверяем, что это комплектующее (os=False)
    if component.os:
        flash('Редактирование доступно только для комплектующих (не основных средств).', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Обновляем поля
        component.buhname = request.form['buhname']
        component.sernum = request.form.get('sernum', '')
        component.invnum = request.form.get('invnum', '')
        component.comment = request.form.get('comment', '')
        component.orgid = int(request.form['orgid'])
        component.placesid = int(request.form['placesid'])
        component.usersid = int(request.form['usersid'])
        component.department_id = request.form.get('department_id')
        component.department_id = int(component.department_id) if component.department_id else None

        # Обработка фото
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_image(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ext = filename.rsplit('.', 1)[1].lower()
                new_photo_filename = f"group_label/{timestamp}.{ext}"
                group_label_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'group_label')
                os.makedirs(group_label_dir, exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_photo_filename))

                # Удаляем старое фото
                if component.photo:
                    old_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], component.photo)
                    if os.path.exists(old_photo_path):
                        os.remove(old_photo_path)

                component.photo = new_photo_filename

        # Удаление фото (если нужно)
        delete_photo = request.form.get('delete_photo')
        if delete_photo == '1' and component.photo:
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], component.photo)
            if os.path.exists(photo_path):
                os.remove(photo_path)
            component.photo = ''

        # --- НОВОЕ: Обработка привязки к основному средству ---
        selected_main_asset_id = request.form.get('main_asset_id')
        selected_main_asset_id = int(selected_main_asset_id) if selected_main_asset_id else None

        # Ищем *существующую* связь для *этого конкретного комплектующего* (через его свойства)
        # Это не идеально, но в текущей схеме, где нет прямой ссылки на equipment.id в app_components,
        # приходится искать по совпадению nomeid, sernum, comment.
        existing_link = AppComponents.query.filter_by(
            id_nome_component=component.nomeid,
            ser_num_component=component.sernum,
            comment_component=component.comment,
        ).first()

        if selected_main_asset_id:
            # Пользователь выбрал основное средство
            if existing_link:
                # Если связь уже есть, обновляем id_main_asset
                if existing_link.id_main_asset != selected_main_asset_id:
                    existing_link.id_main_asset = selected_main_asset_id
                    flash('Привязка к основному средству обновлена.', 'info')
            else:
                # Связи не было, создаём новую
                new_link = AppComponents(
                    id_main_asset=selected_main_asset_id,
                    id_nome_component=component.nomeid,
                    ser_num_component=component.sernum,
                    comment_component=component.comment,
                )
                db.session.add(new_link)
                flash('Комплектующее привязано к основному средству.', 'success')
        else:
            # Пользователь не выбрал основное средство (или выбрал "не привязывать")
            if existing_link:
                # Удаляем существующую связь
                db.session.delete(existing_link)
                flash('Привязка к основному средству удалена.', 'warning')

        # --- КОНЕЦ НОВОГО ---

        try:
            db.session.commit()
            flash('Комплектующее успешно обновлено!', 'success')
            # Возврат на страницу, откуда пришли, или на список комплектующих
            return redirect(url_for('all_components'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении: {str(e)}', 'danger')

    # GET: Подготовка данных для шаблона
    organizations = Org.query.filter_by(active=True).all()
    places = Places.query.filter_by(active=True).all()
    users = db.session.query(Users)\
        .join(UsersRoles, Users.id == UsersRoles.userid)\
        .filter(Users.active == True, UsersRoles.role == 1)\
        .order_by(Users.login)\
        .all()
    departments = Department.query.filter_by(active=True).all()

    # Для определения текущего типа и производителя комплектующего
    current_nome = Nome.query.get(component.nomeid)
    current_group = GroupNome.query.get(current_nome.groupid) if current_nome else None
    current_vendor = Vendor.query.get(current_nome.vendorid) if current_nome else None

    # Списки для выпадающих списков (только активные)
    groups = GroupNome.query.filter_by(active=True).all()
    vendors = Vendor.query.filter_by(active=True).all()

    # Загружаем все наименования для выбранного производителя (для динамического обновления)
    nomenclatures = Nome.query.filter_by(vendorid=current_vendor.id, active=True).order_by(Nome.name).all() if current_vendor else []

    # --- НОВОЕ: Список основных средств для привязки ---
    main_assets = Equipment.query.filter_by(active=True, os=True).all()

    # Проверяем, к какому основному средству привязано это комплектующее (если привязано)
    # Ищем связь в app_components по свойствам компонента
    linked_main_asset = None
    potential_link = AppComponents.query.filter_by(
        id_nome_component=component.nomeid,
        ser_num_component=component.sernum,
        comment_component=component.comment,
    ).first()
    if potential_link:
        linked_main_asset = Equipment.query.filter_by(id=potential_link.id_main_asset, active=True, os=True).first()

    # --- КОНЕЦ НОВОГО ---

    return render_template('edit_component.html',
                           tmc=component,  # используем переменную tmc для совместимости с шаблоном
                           organizations=organizations,
                           places=places,
                           users=users,
                           groups=groups,
                           departments=departments,
                           current_group=current_group,
                           current_vendor=current_vendor,
                           current_nome=current_nome,
                           vendors=vendors,
                           nomenclatures=nomenclatures,
                           # --- ПЕРЕДАЁМ НОВЫЕ ПЕРЕМЕННЫЕ ---
                           main_assets=main_assets,
                           linked_main_asset_id=linked_main_asset.id if linked_main_asset else None
                           # --- КОНЕЦ ПЕРЕДАЧИ ---
                           )

@app.route('/manage_users')
@login_required
def manage_users():
    """Страница просмотра и управления пользователями (только для администраторов)."""
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))

    # Получаем всех пользователей
    all_users = Users.query.order_by(Users.login).all()

    # Получаем профили пользователей (для фото и ФИО)
    user_profiles = {profile.usersid: profile for profile in UsersProfile.query.all()}

    # Получаем роли пользователей
    user_roles = db.session.query(UsersRoles.userid, UsersRoles.role).all()
    roles_dict = {user_id: role for user_id, role in user_roles}

    # --- НОВЫЙ ПОДХОД: Прямой SQL-запрос к post_users БЕЗ столбца name ---
    # Получаем должности из post_users (столбец "post", не "name")
    try:
        result = db.session.execute(
            db.text("SELECT `userid`, `post` FROM `post_users` WHERE `active` = 1")
        )
        post_users_info = result.fetchall()
        post_dict = {row[0]: row[1] for row in post_users_info}
    except Exception as e:
        print(f"Ошибка при загрузке должностей из post_users: {e}")
        flash(f'Ошибка при загрузке данных должностей: {str(e)}', 'warning')
        post_dict = {}

    except Exception as e:
        # Обработка ошибки, если запрос не удался по другой причине
        print(f"Ошибка при запросе к post_users: {e}")
        flash(f'Ошибка при загрузке данных должностей: {str(e)}', 'warning')
        post_dict = {}

    # --- КОНЕЦ НОВОГО ПОДХОДА ---

    return render_template('manage_users.html',
                           all_users=all_users,
                           user_profiles=user_profiles,
                           roles_dict=roles_dict,
                           post_dict=post_dict,
                           is_admin=is_admin,
                           user_login=current_user.login)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Редактирование пользователя (только для администраторов)."""
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))

    user = Users.query.get_or_404(user_id)
    # Проверяем, является ли пользователь МОЛом (имеет роль 1)
    is_mol = db.session.query(UsersRoles).filter_by(userid=user.id, role=1).first() is not None
    current_role = db.session.query(UsersRoles.role).filter_by(userid=user.id).scalar() or 0
    
    # Загружаем профиль пользователя (для фото и ФИО)
    user_profile = UsersProfile.query.filter_by(usersid=user.id).first()
    if not user_profile:
        # Создаем пустой профиль, если его нет
        user_profile = UsersProfile(usersid=user.id, fio='', jpegphoto='noimage.jpg')
        db.session.add(user_profile)
        db.session.flush()

    if request.method == 'POST':
        # Получаем данные из формы
        new_login = request.form.get('login', '').strip()
        new_orgid = request.form.get('orgid', type=int)
        new_active = request.form.get('active') == 'on'
        # Обработка прав администратора через чекбокс
        new_mode = 1 if request.form.get('is_admin') == 'on' else 0
        new_password = request.form.get('password', '').strip()

        # Валидация логина
        if not new_login:
            flash('Логин не может быть пустым.', 'danger')
            orgs = Org.query.all()
            return render_template('edit_user.html', user=user, user_profile=user_profile, 
                                 orgs=orgs, is_admin=is_admin, user_login=current_user.login)

        # Проверка уникальности логина
        existing_user = Users.query.filter(Users.login == new_login, Users.id != user_id).first()
        if existing_user:
            flash(f'Логин "{new_login}" уже занят другим пользователем.', 'danger')
            orgs = Org.query.all()
            return render_template('edit_user.html', user=user, user_profile=user_profile, 
                                 orgs=orgs, is_admin=is_admin, user_login=current_user.login)

        # Обновление основных полей пользователя
        user.login = new_login
        user.orgid = new_orgid
        user.active = new_active
        user.mode = new_mode

        # Обновление пароля при необходимости
        if new_password:
            import hashlib
            user.password = hashlib.sha1(new_password.encode()).hexdigest()
        
        # Обновление ФИО в профиле
        new_fio = request.form.get('fio', '').strip()
        if user_profile:
            user_profile.fio = new_fio

        # Обработка прав администратора через чекбокс
        new_mode = 1 if request.form.get('is_admin') == 'on' else 0

        # Обработка выбора роли через выпадающий список
        new_role = request.form.get('role', type=int)
        if new_role is not None and 0 <= new_role <= 10:  # Проверка диапазона
            # Удаляем все существующие роли пользователя
            UsersRoles.query.filter_by(userid=user.id).delete()
            # Добавляем новую роль
            db.session.add(UsersRoles(userid=user.id, role=new_role))
        else:
            flash('Некорректное значение роли. Допустимый диапазон: 0-10.', 'danger')
            orgs = Org.query.all()
            return render_template('edit_user.html', user=user, user_profile=user_profile, 
                                orgs=orgs, is_admin=is_admin, current_role=current_role,
                                user_login=current_user.login)

        # Обработка загрузки фото профиля
        new_photo = request.files.get('photo')
        if new_photo and new_photo.filename != '':
            if allowed_image(new_photo.filename):
                # Удаляем старое фото, если оно не стандартное
                if user_profile.jpegphoto and user_profile.jpegphoto != 'noimage.jpg':
                    old_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], user_profile.jpegphoto)
                    if os.path.exists(old_photo_path):
                        try:
                            os.remove(old_photo_path)
                        except OSError as e:
                            flash(f'Ошибка при удалении старого фото: {e}', 'warning')

                # Сохраняем новое фото
                filename = secure_filename(new_photo.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ext = filename.rsplit('.', 1)[1].lower()
                new_photo_filename = f"{timestamp}.{ext}"
                new_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], new_photo_filename))
                user_profile.jpegphoto = new_photo_filename
                flash('Фото успешно обновлено!', 'success')
            else:
                flash('Неверный формат файла фото. Допустимые форматы: png, jpg, jpeg, gif, bmp, webp.', 'danger')
                orgs = Org.query.all()
                return render_template('edit_user.html', user=user, user_profile=user_profile, 
                                     orgs=orgs, is_admin=is_admin, user_login=current_user.login)

        try:
            db.session.commit()
            flash(f'Пользователь "{user.login}" успешно обновлён!', 'success')
            return redirect(url_for('manage_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении: {str(e)}', 'danger')

    # GET: отображаем форму с текущими данными пользователя
    orgs = Org.query.all()
    return render_template('edit_user.html',
                        user=user,
                        user_profile=user_profile,
                        orgs=orgs,
                        is_admin=is_admin,
                        current_role=current_role,  # ← добавляем эту переменную
                        user_login=current_user.login)

@app.route('/temp_assign', methods=['POST'])
@login_required
def temp_assign():
    # Проверка: текущий пользователь — МОЛ (role=1) ИЛИ админ (mode==1)
    is_admin = current_user.mode == 1
    is_mol = current_user_has_role(1)

    if not (is_admin or is_mol):
        flash('Только МОЛ или администратор может выдавать ТМЦ временно.', 'danger')
        return redirect(url_for('index'))

    eq_id = request.form.get('eq_id', type=int)
    user_temp_id = request.form.get('user_temp_id', type=int)
    comment = request.form.get('comment', '').strip()

    if not eq_id or not user_temp_id:
        flash('Некорректные данные.', 'danger')
        return redirect(url_for('my_tmc' if not is_admin else 'all_tmc'))

    # --- ОБНОВЛЁННАЯ ЛОГИКА ПОИСКА ТМЦ ---
    if is_admin:
        # Админ может выдавать ЛЮБОЕ активное ТМЦ (active=True), независимо от os и usersid
        equipment = Equipment.query.filter_by(id=eq_id, active=True).first()
    else:
        # МОЛ может выдавать ТОЛЬКО своё активное ТМЦ с os=True
        equipment = Equipment.query.filter_by(id=eq_id, usersid=current_user.id, active=True, os=True).first()
    if not equipment:
        flash('ТМЦ не найдено или не принадлежит вам.', 'danger')
        return redirect(url_for('my_tmc' if not is_admin else 'all_tmc'))
    # --- КОНЕЦ НОВОЙ ЛОГИКИ ---

    # Проверка: получатель — пользователь с ролью 2
    if not user_has_role(user_temp_id, 2):
        flash('Получатель должен иметь роль "пользователь" (role=2).', 'danger')
        return redirect(url_for('my_tmc' if not is_admin else 'all_tmc'))

    # Проверка: ТМЦ не выдано временно в данный момент
    active_usage = EquipmentTempUsage.query.filter_by(
        equipment_id=eq_id,
        returned=False
    ).first()
    if active_usage:
        flash('ТМЦ уже выдано временно и не возвращено.', 'warning')
        return redirect(url_for('my_tmc' if not is_admin else 'all_tmc'))

    # Создаём запись о временной выдаче
    usage = EquipmentTempUsage(
        equipment_id=eq_id,
        mol_userid=current_user.id,
        user_temp_id=user_temp_id,
        comment=comment
    )
    db.session.add(usage)
    db.session.commit()

    # Логирование в таблицу move (опционально, для совместимости)
    move = Move(
        eqid=eq_id,
        dt=datetime.utcnow(),
        orgidfrom=equipment.orgid,
        orgidto=equipment.orgid,
        placesidfrom=equipment.placesid,
        placesidto=equipment.placesid,
        useridfrom=current_user.id,
        useridto=user_temp_id,
        comment=f'Временная выдача: {comment or "без комментария"}'
    )
    db.session.add(move)
    db.session.commit()

    flash('ТМЦ успешно выдано временно.', 'success')
    return redirect(url_for('my_tmc' if not is_admin else 'all_tmc'))

@app.route('/temp_return/<int:usage_id>', methods=['POST'])
@login_required
def temp_return(usage_id):
    usage = EquipmentTempUsage.query.get_or_404(usage_id)
    mol_user_id = usage.mol_userid
    is_admin = current_user.mode == 1
    is_mol = current_user.id == mol_user_id

    if not (is_admin or is_mol):
        flash('Только МОЛ или администратор может принять ТМЦ обратно.', 'danger')
        return redirect(url_for('index'))

    if usage.returned:
        flash('ТМЦ уже возвращено.', 'info')
        return redirect(url_for('index'))

    usage.returned = True
    usage.dt_end = datetime.utcnow()
    db.session.commit()
    flash('ТМЦ успешно возвращено.', 'success')
    return redirect(url_for('info_tmc', tmc_id=usage.equipment_id))

@app.route('/my_temp_tmc')
@login_required
def my_temp_tmc():
    if not current_user_has_role(2):
        abort(403)

    active_usages = EquipmentTempUsage.query.filter_by(
        user_temp_id=current_user.id,
        returned=False
    ).all()

    return render_template('my_temp_tmc.html', usages=active_usages)

# === ЗАПУСК ПРИЛОЖЕНИЯ ===

if __name__ == '__main__':
    # В продакшене используйте Gunicorn/uWSGI, а не встроенный сервер
    app.run(host='0.0.0.0', port=5000, debug=True)