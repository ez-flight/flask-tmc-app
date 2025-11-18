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
from sqlalchemy import func, case, and_
from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal, InvalidOperation
from sqlalchemy.exc import IntegrityError

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for, abort, send_file, Response
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user


from models import Equipment, Nome, Org, Places, Users, db, GroupNome, Vendor, Department, Knt, Invoices, InvoiceEquipment, UsersRoles, UsersProfile, Category, Move, AppComponents, NomeComponents, PostUsers, News, EquipmentTempUsage

# Загружаем переменные окружения из .env
load_dotenv()

# Проверяем тестовый режим
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'

# Создаём Flask-приложение
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-for-dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEST_MODE'] = TEST_MODE
db.init_app(app)


# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # маршрут для перенаправления неавторизованных пользователей

app.jinja_env.globals['date'] = date

# === КОНТЕКСТНЫЙ ПРОЦЕССОР ===
@app.context_processor
def inject_user_data():
    """Добавляет данные пользователя во все шаблоны."""
    if current_user.is_authenticated:
        is_admin = current_user.mode == 1
        is_mol = current_user_has_role(1)
        
        # В тестовом режиме используем мок-данные
        if TEST_MODE:
            return {
                'user_login': current_user.login,
                'user_photo': url_for('static', filename='uploads/noimage.jpg'),
                'tmc_count': 0,  # Тестовые данные
                'total_cost': 0,  # Тестовые данные
                'is_admin': is_admin,
                'is_mol': is_mol,
                'user_org_name': 'Тестовая организация',
                'user_org_id': current_user.orgid if hasattr(current_user, 'orgid') else 1,
                'test_mode': True
            }
        
        # Реальный режим: запрос ТМЦ для пользователя или всех (если админ)
        if is_admin:
            tmc_query = Equipment.query.filter_by(active=True, os=True)
        else:
            tmc_query = Equipment.query.filter_by(usersid=current_user.id, active=True, os=True)
        
        tmc_count = tmc_query.count()
        total_cost = db.session.query(func.coalesce(func.sum(Equipment.cost), 0)).filter(
            Equipment.id.in_([eq.id for eq in tmc_query.all()])
        ).scalar() or 0
        
        # Фото пользователя
        from models import UsersProfile
        profile = UsersProfile.query.filter_by(usersid=current_user.id).first()
        if profile and profile.jpegphoto and profile.jpegphoto != 'noimage.jpg':
            user_photo = url_for('static', filename=f'uploads/{profile.jpegphoto}')
        else:
            user_photo = url_for('static', filename='uploads/noimage.jpg')
        
        # Название организации пользователя
        user_org_name = None
        if hasattr(current_user, 'orgid') and current_user.orgid:
            org = Org.query.get(current_user.orgid)
            if org:
                user_org_name = org.name
        
        return {
            'user_login': current_user.login,
            'user_photo': user_photo,
            'tmc_count': tmc_count,
            'total_cost': total_cost,
            'is_admin': is_admin,
            'is_mol': is_mol,
            'user_org_name': user_org_name,
            'user_org_id': current_user.orgid if hasattr(current_user, 'orgid') else None,
            'test_mode': False
        }
    return {
        'user_login': '',
        'user_photo': url_for('static', filename='uploads/noimage.jpg'),
        'tmc_count': 0,
        'total_cost': 0,
        'is_admin': False,
        'is_mol': False,
        'test_mode': TEST_MODE
    }

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
    if TEST_MODE and hasattr(current_user, '_roles'):
        # В тестовом режиме проверяем роли из мок-объекта
        return role_id in current_user._roles
    
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
    if TEST_MODE:
        # В тестовом режиме возвращаем мок-пользователя
        from test_mode import TEST_USERS
        for user in TEST_USERS.values():
            if str(user.id) == str(user_id):
                return user
        return None
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
        login_name = request.form['login']
        password = request.form['password']

        # Тестовый режим: используем мок-данные
        if TEST_MODE:
            from test_mode import get_test_user, check_test_password
            # Нормализуем логин (приводим к нижнему регистру)
            login_normalized = login_name.strip().lower() if login_name else ''
            password_normalized = password.strip() if password else ''
            
            # Отладочная информация (можно убрать в продакшене)
            if not login_normalized:
                flash('Логин не может быть пустым', 'danger')
            elif not password_normalized:
                flash('Пароль не может быть пустым', 'danger')
            elif check_test_password(login_normalized, password_normalized):
                user = get_test_user(login_normalized)
                if user:
                    login_user(user)
                    response = redirect(url_for('index'))
                    response.set_cookie('user_randomid_w3', user.randomid, max_age=60*60*24*30)
                    flash(f'Тестовый режим: вход выполнен как {user.login}', 'info')
                    return response
                else:
                    flash('Пользователь не найден в тестовой базе', 'danger')
            else:
                flash(f'Неверный логин или пароль. Логин: "{login_normalized}", пароль проверен: {password_normalized == "test123"}', 'danger')
        else:
            # Реальный режим: используем БД
            user = Users.query.filter_by(login=login_name, active=1).first()
            if user and check_password(password, user.salt, user.password):
                login_user(user)
                response = redirect(url_for('index'))
                # Устанавливаем куку, как в оригинальной системе
                response.set_cookie('user_randomid_w3', user.randomid, max_age=60*60*24*30)  # 30 дней
                return response
            else:
                flash('Неверный логин или пароль', 'danger')

    return render_template('auth/login.html', test_mode=TEST_MODE)


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
    is_mol = current_user_has_role(1)

    # В тестовом режиме не делаем запросы к БД
    if TEST_MODE:
        news_list = []
        return render_template('tmc/index.html', news_list=news_list)
    
    # Реальный режим: запрос ТМЦ для пользователя или всех (если админ)
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

    # Фото пользователя (только в реальном режиме)
    if not TEST_MODE:
        from models import UsersProfile
        profile = UsersProfile.query.filter_by(usersid=current_user.id).first()
        if profile and profile.jpegphoto and profile.jpegphoto != 'noimage.jpg':
            user_photo = url_for('static', filename=f'uploads/{profile.jpegphoto}')
        else:
            user_photo = url_for('static', filename='uploads/noimage.jpg')

    # Новости: закрепленные сверху, затем остальные, максимум 5 (только в реальном режиме)
    if not TEST_MODE:
        pinned_news = News.query.filter_by(stiker=True, pinned=True).order_by(News.dt.desc()).all()
        unpinned_news = News.query.filter_by(stiker=True, pinned=False).order_by(News.dt.desc()).all()
        
        # Объединяем: сначала закрепленные, затем остальные, максимум 5
        news_list = []
        if pinned_news:
            # Берем последнюю закрепленную новость
            news_list.append(pinned_news[0])
            # Добавляем остальные новости до лимита 5
            remaining_slots = 4
            for news in unpinned_news:
                if remaining_slots <= 0:
                    break
                news_list.append(news)
                remaining_slots -= 1
        else:
            # Если нет закрепленных, берем просто 5 последних
            news_list = unpinned_news[:5]
    else:
        news_list = []

    return render_template('tmc/index.html',
                           news_list=news_list)


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_tmc():
    """Добавление нового ТМЦ. Доступно только админу и МОЛ (role=1)."""
    # Проверка доступа: только админ или МОЛ
    is_admin = current_user.mode == 1
    is_mol = current_user_has_role(1)
    
    if not (is_admin or is_mol):
        flash('Доступ запрещён. Только администратор или МОЛ могут добавлять ТМЦ.', 'danger')
        return redirect(url_for('index'))
    
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
        
        # Для МОЛ автоматически устанавливаем usersid = current_user.id
        # Для админа берем из формы
        if is_mol and not is_admin:
            usersid = current_user.id
        else:
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

        # Обработка статуса ТМЦ
        status = request.form.get('status', 'active')
        if status == 'repair':
            repair_status = True
            lost_status = False
        elif status == 'lost':
            repair_status = False
            lost_status = True
        else:  # active
            repair_status = False
            lost_status = False
        
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
            repair=repair_status,
            lost=lost_status,
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
    
    # Для админа показываем список всех МОЛ, для МОЛ - только себя
    if is_admin:
        users = db.session.query(Users)\
            .join(UsersRoles, Users.id == UsersRoles.userid)\
            .filter(Users.active == True, UsersRoles.role == 1)\
            .order_by(Users.login)\
            .all()
    else:
        # Для МОЛ показываем только себя
        users = [current_user] if is_mol else []
    
    departments = Department.query.filter_by(active=True).all()
    
    # Получаем группы для выпадающего списка
    groups = GroupNome.query.filter_by(active=True).all()

    return render_template('tmc/add_tmc.html',
                           organizations=organizations,
                           places=places,
                           users=users,
                           departments=departments,
                           groups=groups,
                           datetime=datetime,
                           is_admin=is_admin,
                           is_mol=is_mol,
                           current_user=current_user,
                           preselected_nome=preselected_nome,
                           preselected_group=preselected_group,
                           preselected_vendor=preselected_vendor)

@app.route('/edit/<int:tmc_id>', methods=['GET', 'POST'])
@login_required
def edit_tmc(tmc_id):
    """Редактирование ТМЦ."""
    from models import EquipmentComments
    
    tmc = Equipment.query.get_or_404(tmc_id)
    if request.method == 'POST':
        tmc.buhname = request.form['buhname']
        tmc.sernum = request.form.get('sernum', '')
        tmc.invnum = request.form.get('invnum', '')
        
        # Обработка комментария: сохраняем старый в архив, если он изменился
        new_comment = request.form.get('comment', '').strip()
        old_comment = tmc.comment or ''
        
        if new_comment != old_comment and old_comment:
            # Сохраняем старый комментарий в архив
            archived_comment = EquipmentComments(
                equipment_id=tmc_id,
                comment=old_comment,
                created_by=current_user.id
            )
            db.session.add(archived_comment)
        
        tmc.comment = new_comment
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

        # Обработка статуса ТМЦ
        status = request.form.get('status', 'active')
        if status == 'repair':
            tmc.repair = True
            tmc.lost = False
        elif status == 'lost':
            tmc.repair = False
            tmc.lost = True
        else:  # active
            tmc.repair = False
            tmc.lost = False

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

    return render_template('tmc/edit_tmc.html',
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

    return render_template('nomenclature/edit_nome.html', nome=nome, groups=groups, vendors=vendors)

@app.route('/bulk_edit_nome/<int:nome_id>', methods=['GET', 'POST'])
@login_required
def bulk_edit_nome(nome_id):
    # Только для администраторов
    if current_user.mode != 1:
        flash('Доступ запрещён. Групповое редактирование доступно только администраторам.', 'danger')
        return redirect(url_for('index'))
    
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
    return render_template('nomenclature/bulk_edit_nome.html',
                       nome=nome,
                       nome_id=nome_id,
                       nome_name=nome.name,
                       tmc_count=len(tmc_list),
                       first_tmc=first_tmc,
                       suppliers=suppliers)

@app.route('/edit_nome_group/<int:nome_id>', methods=['GET', 'POST'])
@login_required
def edit_nome_group(nome_id):
    """Редактирование группы ТМЦ - доступно админу и МОЛ."""
    nome = Nome.query.get_or_404(nome_id)
    
    # Проверка прав доступа: только админ или МОЛ
    is_admin = current_user.mode == 1
    is_mol = current_user_has_role(1)
    
    if not (is_admin or is_mol):
        flash('Доступ запрещён. Редактирование группы ТМЦ доступно только администраторам и МОЛ.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Обновляем флаг составного ТМЦ
            nome.is_composite = bool(request.form.get('is_composite'))
            
            # Обновляем комментарий группы
            comment = request.form.get('comment', '').strip()
            nome.comment = comment if comment else None
            
            # Обновляем категорию (сорт) - значение от 1 до 5
            category_sort_str = request.form.get('category_sort', '').strip()
            if category_sort_str:
                category_sort = int(category_sort_str)
                if 1 <= category_sort <= 5:
                    nome.category_sort = category_sort
                else:
                    flash('Категория (сорт) должна быть от 1 до 5', 'warning')
                    nome.category_sort = None
            else:
                nome.category_sort = None
            
            db.session.commit()
            flash('Группа ТМЦ успешно обновлена!', 'success')
            return redirect(url_for('list_by_nome', nome_id=nome_id))
        except ValueError:
            db.session.rollback()
            flash('Ошибка: Категория (сорт) должна быть числом от 1 до 5', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении: {str(e)}', 'danger')
    
    # GET: отображаем форму редактирования
    return render_template('nomenclature/edit_nome_group.html',
                         nome=nome,
                         is_admin=is_admin,
                         is_mol=is_mol)

@app.route('/list_by_nome/<int:nome_id>')
@login_required
def list_by_nome(nome_id):
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        from test_mode import MockUser
        # Создаем мок-объект nome для шаблона
        class MockNome:
            id = nome_id
            name = f'Тестовая группа {nome_id}'
            photo = ''
            is_composite = False
            category_sort = None
        nome = MockNome()
        return render_template('tmc/list_by_nome.html',
                             nome=nome,
                             tmc_list=[],
                             component_template=[],
                             is_admin=current_user.mode == 1,
                             is_mol=current_user_has_role(1))
    
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
    
    # Проверяем, является ли пользователь МОЛ
    is_mol = current_user_has_role(1)

    return render_template('tmc/list_by_nome.html',
                           nome=nome,
                           tmc_list=tmc_list,
                           component_template=component_template,
                           # Передаём переменные в шаблон
                           is_admin=is_admin,
                           is_mol=is_mol)

@app.route('/info_tmc/<int:tmc_id>')
@login_required
def info_tmc(tmc_id):
    tmc = Equipment.query.get_or_404(tmc_id)
    
    # Проверяем, является ли ТМЦ составным (может иметь комплектующие)
    nome = tmc.nome
    is_composite = nome.is_composite if nome else False
    
    # Получаем комплектующие только если ТМЦ составное
    components = []
    if is_composite:
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

    # Получаем историю перемещений
    # 1. Перемещения между МОЛ/Склад из таблицы Move
    moves = Move.query.filter_by(eqid=tmc_id).order_by(Move.dt.desc()).all()
    
    # 2. Временные выдачи из таблицы EquipmentTempUsage
    temp_usages = EquipmentTempUsage.query.filter_by(
        equipment_id=tmc_id
    ).order_by(EquipmentTempUsage.dt_start.desc()).all()
    
    # Объединяем в один список с унифицированной структурой
    history = []
    
    # Обрабатываем перемещения
    for move in moves:
        org_from = Org.query.get(move.orgidfrom)
        org_to = Org.query.get(move.orgidto)
        place_from = Places.query.get(move.placesidfrom)
        place_to = Places.query.get(move.placesidto)
        user_from = Users.query.get(move.useridfrom)
        user_to = Users.query.get(move.useridto)
        
        history.append({
            'type': 'move',
            'id': move.id,
            'date': move.dt,
            'org_from': org_from.name if org_from else f'ID {move.orgidfrom}',
            'org_to': org_to.name if org_to else f'ID {move.orgidto}',
            'place_from': place_from.name if place_from else f'ID {move.placesidfrom}',
            'place_to': place_to.name if place_to else f'ID {move.placesidto}',
            'user_from': user_from.login if user_from else f'ID {move.useridfrom}',
            'user_to': user_to.login if user_to else f'ID {move.useridto}',
            'comment': move.comment,
            'is_temp': 'Временная выдача' in move.comment
        })
    
    # Обрабатываем временные выдачи
    for usage in temp_usages:
        mol_user = usage.mol_user
        temp_user = usage.temp_user
        
        history.append({
            'type': 'temp_usage',
            'id': usage.id,
            'date': usage.dt_start,
            'org_from': tmc.org.name if tmc.org else '',
            'org_to': tmc.org.name if tmc.org else '',
            'place_from': tmc.places.name if tmc.places else '',
            'place_to': tmc.places.name if tmc.places else '',
            'user_from': mol_user.login if mol_user else f'ID {usage.mol_userid}',
            'user_to': temp_user.login if temp_user else f'ID {usage.user_temp_id}',
            'comment': usage.comment or '',
            'returned': usage.returned,
            'dt_end': usage.dt_end,
            'is_temp': True
        })
    
    # Сортируем по дате (от новых к старым)
    history.sort(key=lambda x: x['date'], reverse=True)
    
    # Получаем историю комментариев
    from models import EquipmentComments
    comment_history = EquipmentComments.query.filter_by(
        equipment_id=tmc_id
    ).order_by(EquipmentComments.created_at.desc()).all()

    return render_template('tmc/info_tmc.html',
                           tmc=tmc,
                           components=components,
                           is_composite=is_composite,
                           can_manage_temp=can_manage_temp,
                           active_usage=active_usage,
                           users_role_2=users_role_2,
                           history=history,
                           comment_history=comment_history)

@app.route('/add_nome', methods=['GET', 'POST'])
@login_required
def add_nome():
    """Добавление нового наименования (группы ТМЦ) с указанием количества ТМЦ. Доступно только админу."""
    # Проверка доступа: только админ
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён. Только администратор может добавлять группы ТМЦ.', 'danger')
        return redirect(url_for('index'))
    
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
                lost=False,
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
    return render_template('nomenclature/add_nome.html', groups=groups, vendors=vendors, places=places, users=users)

@app.route('/invoice_list')
@login_required
def invoice_list():
    """Список накладных: для Admin — все, для МОЛ — только связанные с ним."""
    is_admin = current_user.mode == 1
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('invoices/invoice_list.html',
                             invoices=[],
                             is_admin=is_admin)
    

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

    return render_template('invoices/invoice_list.html', invoices=invoices)


@app.route('/create_invoice', methods=['GET', 'POST'])
@login_required
def create_invoice():
    # В тестовом режиме запрещаем создание накладных
    if TEST_MODE:
        flash('Создание накладных недоступно в тестовом режиме', 'warning')
        return redirect(url_for('invoice_list'))
    
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
    return render_template('invoices/create_invoice.html',
                           departments=departments,
                           users=users,
                           warehouses=warehouses,    
                           equipment_list=equipment_list,
                           now_date=date.today())


@app.route('/api/equipment_by_user/<int:user_id>')
@login_required
def equipment_by_user(user_id):
    # В тестовом режиме возвращаем пустой список
    if TEST_MODE:
        from flask import jsonify
        return jsonify({'equipment': []})
    
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
    # В тестовом режиме запрещаем просмотр
    if TEST_MODE:
        flash('Просмотр накладных недоступен в тестовом режиме', 'warning')
        return redirect(url_for('invoice_list'))
    
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

    return render_template('invoices/invoice_detail.html', invoice=invoice, tmc_count=tmc_count, total_cost=total_cost)

@app.route('/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    # В тестовом режиме запрещаем редактирование
    if TEST_MODE:
        flash('Редактирование накладных недоступно в тестовом режиме', 'warning')
        return redirect(url_for('invoice_list'))
    
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

    return render_template('invoices/edit_invoice.html',
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
    # В тестовом режиме запрещаем удаление
    if TEST_MODE:
        flash('Удаление накладных недоступно в тестовом режиме', 'warning')
        return redirect(url_for('invoice_list'))
    
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
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('tmc/all_tmc.html',
                             grouped_tmc=[],
                             all_departments=[],
                             all_categories=[],
                             all_users=[],
                             filter_user_id=None,
                             filter_department_id=None,
                             filter_category_id=None)
    
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
    
    # Получаем все ID ТМЦ для подсчета статистики
    tmc_ids = [eq.id for eq in base_query.all()]
    
    # Запрос для группировки с подсчетом статистики по статусам
    grouped_query = db.session.query(
        Equipment.nomeid,
        func.coalesce(Nome.name, '⚠️ Неизвестное наименование').label('nome_name'),
        func.count(Equipment.id).label('quantity'),
        func.coalesce(Nome.photo, '').label('nome_photo'),
        func.sum(case((Equipment.repair == True, 1), else_=0)).label('repair_count'),
        func.sum(case((Equipment.lost == True, 1), else_=0)).label('lost_count'),
        func.sum(case((and_(Equipment.repair == False, Equipment.lost == False), 1), else_=0)).label('active_count')
    ).join(Nome, Equipment.nomeid == Nome.id)\
     .filter(Equipment.id.in_(tmc_ids))\
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
    
    return render_template('tmc/all_tmc.html',
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

    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('tmc/my_tmc.html',
                             grouped_tmc=[],
                             all_departments=[],
                             all_categories=[],
                             filter_department_id=None,
                             filter_category_id=None)

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

    # Получаем все ID ТМЦ для подсчета статистики
    tmc_ids = [eq.id for eq in base_query.with_entities(Equipment.id).all()]
    
    # Группировка с подсчетом статистики по статусам
    grouped_query = db.session.query(
        Equipment.nomeid,
        func.coalesce(Nome.name, '⚠️ Неизвестное наименование').label('nome_name'),
        func.count(Equipment.id).label('quantity'),
        func.coalesce(Nome.photo, '').label('nome_photo'),
        func.sum(case((Equipment.repair == True, 1), else_=0)).label('repair_count'),
        func.sum(case((Equipment.lost == True, 1), else_=0)).label('lost_count'),
        func.sum(case((and_(Equipment.repair == False, Equipment.lost == False), 1), else_=0)).label('active_count')
    ).select_from(Equipment)\
     .join(Nome, Equipment.nomeid == Nome.id)

    # Применяем те же фильтры
    if filter_department_id:
        grouped_query = grouped_query.filter(Equipment.department_id == filter_department_id)
    if filter_category_id:
        grouped_query = grouped_query.join(GroupNome, Nome.groupid == GroupNome.id)\
                                     .filter(GroupNome.category_id == filter_category_id)

    grouped_query = grouped_query.filter(
        Equipment.id.in_(tmc_ids)
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

    is_mol = current_user_has_role(1)
    
    return render_template('tmc/my_tmc.html',
                           grouped_tmc=grouped_tmc,
                           tmc_count=tmc_count,
                           total_cost=total_cost,
                           filter_department_id=filter_department_id,
                           filter_category_id=filter_category_id,
                           all_departments=all_departments,
                           all_categories=all_categories,
                           user_login=current_user.login,
                           is_mol=is_mol)
# app.py (вставьте этот маршрут в соответствующее место)
@app.route('/manage_categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    is_admin = current_user.mode == 1
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('categories/manage_categories.html',
                             categories=[],
                             is_admin=is_admin)
    
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

    return render_template('admin/manage_categories.html',
                           all_groups=all_groups,
                           all_categories=all_categories,
                           unassigned_groups=unassigned_groups,
                           assigned_groups=assigned_groups)

@app.route('/all_components')
@login_required
def all_components():
    # Только для администраторов
    is_admin = current_user.mode == 1
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('components/all_components.html',
                             components=[],
                             is_admin=is_admin)
    
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

    return render_template('components/all_components.html',
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
    # В тестовом режиме запрещаем добавление
    if TEST_MODE:
        flash('Добавление комплектующих недоступно в тестовом режиме', 'warning')
        return redirect(url_for('all_components'))
    
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

        # Если указано основное средство, проверяем, что оно составное,
        # и наследуем МОЛ
        if main_asset_id:
            main_asset = Equipment.query.get(main_asset_id)
            if main_asset:
                # Проверяем, что ТМЦ является составным
                nome_main = Nome.query.get(main_asset.nomeid)
                if nome_main and nome_main.is_composite:
                    # Наследуем МОЛ от основного ТМЦ
                    usersid = main_asset.usersid
                    orgid = main_asset.orgid
                    placesid = main_asset.placesid
                    department_id = main_asset.department_id
                else:
                    msg = ('К выбранному ТМЦ нельзя прикреплять комплектующие. '
                           'ТМЦ должно быть помечено как составное.')
                    flash(msg, 'warning')
                    return redirect(url_for('add_component'))

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
            passport_filename='',  # паспорт не нужен для комплектующих
            kntid=None,
            datepost=datetime.utcnow(),
            date_start=date.today(),
            cost=Decimal('0.00'),  # можно не указывать стоимость
            currentcost=Decimal('0.00'),
            os=False,  # КЛЮЧЕВОЕ: это НЕ основное средство
            mode=False,
            repair=False,
            lost=False,
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
                # Проверяем, не привязано ли уже комплектующее этого типа
                # к данному ТМЦ
                existing_component = AppComponents.query.filter_by(
                    id_main_asset=main_asset_id,
                    id_nome_component=nomeid
                ).first()

                if existing_component:
                    db.session.rollback()
                    nome_component = Nome.query.get(nomeid)
                    nome_name = (nome_component.name
                                 if nome_component else f"ID {nomeid}")
                    msg = (f'К данному ТМЦ уже привязано комплектующее типа '
                           f'"{nome_name}". К одному ТМЦ можно привязать '
                           f'только одно комплектующее каждого типа.')
                    flash(msg, 'warning')
                    return redirect(url_for('add_component'))
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

    # Также передадим список основных средств для привязки
    # (только составные ТМЦ). Получаем ID составных ТМЦ
    composite_nome_ids = (db.session.query(Nome.id)
                          .filter(Nome.is_composite == True)
                          .subquery())
    main_assets = Equipment.query.filter(
        Equipment.active == True,
        Equipment.os == True,
        Equipment.nomeid.in_(composite_nome_ids)
    ).all()

    # Получаем информацию о том, какие типы комплектующих уже привязаны
    # к каким ТМЦ. Словарь: {nome_id: [asset_ids]} - какие ТМЦ уже имеют
    # комплектующее данного типа
    blocked_assets_by_nome = {}
    existing_links = AppComponents.query.all()
    for link in existing_links:
        if link.id_nome_component not in blocked_assets_by_nome:
            blocked_assets_by_nome[link.id_nome_component] = []
        blocked_assets_by_nome[link.id_nome_component].append(link.id_main_asset)

    return render_template('components/add_component.html',
                        organizations=organizations,
                        places=places,
                        users=users,
                        departments=departments,
                        component_groups=component_groups,
                        main_assets=main_assets,
                        blocked_assets_by_nome=blocked_assets_by_nome,
                        datetime=datetime,
                        vendors=[],
                        nomenclatures=[])

@app.route('/edit_component/<int:component_id>', methods=['GET', 'POST'])
@login_required
def edit_component(component_id):
    """Редактирование комплектующего (os=False)."""
    # В тестовом режиме запрещаем редактирование
    if TEST_MODE:
        flash('Редактирование комплектующих недоступно в тестовом режиме', 'warning')
        return redirect(url_for('all_components'))
    
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
        selected_main_asset_id = (int(selected_main_asset_id)
                                   if selected_main_asset_id else None)

        # Если указано основное средство, проверяем, что оно составное,
        # и наследуем МОЛ
        if selected_main_asset_id:
            main_asset = Equipment.query.get(selected_main_asset_id)
            if main_asset:
                # Проверяем, что ТМЦ является составным
                nome_main = Nome.query.get(main_asset.nomeid)
                if nome_main and nome_main.is_composite:
                    # Наследуем МОЛ от основного ТМЦ
                    component.usersid = main_asset.usersid
                    component.orgid = main_asset.orgid
                    component.placesid = main_asset.placesid
                    component.department_id = main_asset.department_id
                else:
                    msg = ('К выбранному ТМЦ нельзя прикреплять комплектующие. '
                           'ТМЦ должно быть помечено как составное.')
                    flash(msg, 'warning')
                    return redirect(url_for('edit_component',
                                           component_id=component_id))

        # Ищем существующую связь для этого конкретного комплектующего
        # (через его свойства). Это не идеально, но в текущей схеме, где нет
        # прямой ссылки на equipment.id в app_components, приходится искать
        # по совпадению nomeid, sernum, comment.
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
                    # Проверяем, не привязано ли уже комплектующее этого типа
                    # к новому ТМЦ. Исключаем текущую связь из проверки
                    existing_component = AppComponents.query.filter(
                        AppComponents.id_main_asset == selected_main_asset_id,
                        AppComponents.id_nome_component == component.nomeid,
                        AppComponents.id != existing_link.id
                    ).first()

                    if existing_component:
                        nome_name = (component.nome.name
                                      if component.nome else "неизвестно")
                        msg = (f'К выбранному ТМЦ уже привязано комплектующее '
                               f'типа "{nome_name}". К одному ТМЦ можно привязать '
                               f'только одно комплектующее каждого типа.')
                        flash(msg, 'warning')
                        return redirect(url_for('edit_component',
                                               component_id=component_id))

                    existing_link.id_main_asset = selected_main_asset_id
                    flash('Привязка к основному средству обновлена.', 'info')
                # Если связь указывает на тот же ТМЦ - ничего не делаем
            else:
                # Связи не было, проверяем, не привязано ли уже комплектующее
                # этого типа к данному ТМЦ
                existing_component = AppComponents.query.filter_by(
                    id_main_asset=selected_main_asset_id,
                    id_nome_component=component.nomeid
                ).first()

                if existing_component:
                    nome_name = (component.nome.name
                                  if component.nome else "неизвестно")
                    msg = (f'К выбранному ТМЦ уже привязано комплектующее '
                           f'типа "{nome_name}". К одному ТМЦ можно привязать '
                           f'только одно комплектующее каждого типа.')
                    flash(msg, 'warning')
                    return redirect(url_for('edit_component',
                                           component_id=component_id))

                # Создаём новую связь
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

    # Загружаем все наименования для выбранного производителя
    # (для динамического обновления)
    nomenclatures = (Nome.query.filter_by(vendorid=current_vendor.id,
                                          active=True)
                     .order_by(Nome.name).all()
                     if current_vendor else [])

    # --- НОВОЕ: Список основных средств для привязки
    # (только составные ТМЦ). Получаем ID составных ТМЦ
    composite_nome_ids = (db.session.query(Nome.id)
                          .filter(Nome.is_composite == True)
                          .subquery())
    main_assets = Equipment.query.filter(
        Equipment.active == True,
        Equipment.os == True,
        Equipment.nomeid.in_(composite_nome_ids)
    ).all()
    # Получаем информацию о том, какие типы комплектующих уже привязаны
    # к каким ТМЦ. Словарь: {nome_id: [asset_ids]} - какие ТМЦ уже имеют
    # комплектующее данного типа
    blocked_assets_by_nome = {}
    existing_links = AppComponents.query.all()
    for link in existing_links:
        if link.id_nome_component not in blocked_assets_by_nome:
            blocked_assets_by_nome[link.id_nome_component] = []
        blocked_assets_by_nome[link.id_nome_component].append(
            link.id_main_asset)

    # Проверяем, к какому основному средству привязано это комплектующее
    # (если привязано). Ищем связь в app_components по свойствам компонента
    linked_main_asset = None
    potential_link = AppComponents.query.filter_by(
        id_nome_component=component.nomeid,
        ser_num_component=component.sernum,
        comment_component=component.comment,
    ).first()
    if potential_link:
        linked_main_asset = Equipment.query.filter_by(
            id=potential_link.id_main_asset,
            active=True,
            os=True
        ).first()

    # --- КОНЕЦ НОВОГО ---

    return render_template('components/edit_component.html',
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
                           blocked_assets_by_nome=blocked_assets_by_nome,
                           linked_main_asset_id=linked_main_asset.id if linked_main_asset else None,
                           current_component_nome_id=component.nomeid
                           # --- КОНЕЦ ПЕРЕДАЧИ ---
                           )

@app.route('/manage_users')
@login_required
def manage_users():
    """Страница просмотра и управления пользователями (только для администраторов)."""
    is_admin = current_user.mode == 1
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('users/manage_users.html',
                             users=[],
                             is_admin=is_admin)
    
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

    return render_template('users/manage_users.html',
                           all_users=all_users,
                           user_profiles=user_profiles,
                           roles_dict=roles_dict,
                           post_dict=post_dict,
                           is_admin=is_admin,
                           user_login=current_user.login)

@app.route('/edit_my_profile', methods=['GET', 'POST'])
@login_required
def edit_my_profile():
    """Редактирование своего профиля (для всех пользователей)."""
    user = current_user
    user_id = current_user.id
    
    # Загружаем профиль пользователя (для фото и ФИО)
    user_profile = UsersProfile.query.filter_by(usersid=user_id).first()
    if not user_profile:
        # Создаем пустой профиль, если его нет
        user_profile = UsersProfile(usersid=user_id, fio='', jpegphoto='noimage.jpg')
        db.session.add(user_profile)
        db.session.flush()
    
    if request.method == 'POST':
        # Получаем данные из формы
        new_password = request.form.get('password', '').strip()
        
        # Обновление пароля при необходимости
        if new_password:
            import hashlib
            user.password = hashlib.sha1(new_password.encode()).hexdigest()
        
        # Обновление ФИО в профиле
        new_fio = request.form.get('fio', '').strip()
        if user_profile:
            user_profile.fio = new_fio
        
        # Обработка загрузки фото
        if 'photo' in request.files:
            photo_file = request.files['photo']
            if photo_file and photo_file.filename and allowed_image(photo_file.filename):
                # Удаляем старое фото, если оно не стандартное
                if user_profile.jpegphoto and user_profile.jpegphoto != 'noimage.jpg':
                    old_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], user_profile.jpegphoto)
                    if os.path.exists(old_photo_path):
                        try:
                            os.remove(old_photo_path)
                        except OSError as e:
                            flash(f'Ошибка при удалении старого фото: {e}', 'warning')
                
                # Сохраняем новое фото
                filename = secure_filename(photo_file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ext = filename.rsplit('.', 1)[1].lower()
                new_photo_filename = f"{timestamp}.{ext}"
                photo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_photo_filename))
                user_profile.jpegphoto = new_photo_filename
            elif photo_file and photo_file.filename:
                flash('Неверный формат файла фото. Допустимые форматы: png, jpg, jpeg, gif, bmp, webp.', 'danger')
        
        try:
            db.session.commit()
            flash('Профиль успешно обновлён.', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении: {str(e)}', 'danger')
    
    # GET: отображаем форму с текущими данными пользователя
    return render_template('users/edit_my_profile.html',
                        user=user,
                        user_profile=user_profile,
                        user_login=current_user.login)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Редактирование пользователя (только для администраторов)."""
    is_admin = current_user.mode == 1
    
    # В тестовом режиме запрещаем редактирование
    if TEST_MODE:
        flash('Редактирование пользователей недоступно в тестовом режиме', 'warning')
        return redirect(url_for('manage_users'))
    
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
            return render_template('users/edit_user.html', user=user, user_profile=user_profile, 
                                 orgs=orgs, is_admin=is_admin, user_login=current_user.login)

        # Проверка уникальности логина
        existing_user = Users.query.filter(Users.login == new_login, Users.id != user_id).first()
        if existing_user:
            flash(f'Логин "{new_login}" уже занят другим пользователем.', 'danger')
            orgs = Org.query.all()
            return render_template('users/edit_user.html', user=user, user_profile=user_profile, 
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
            return render_template('users/edit_user.html', user=user, user_profile=user_profile, 
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
                return render_template('users/edit_user.html', user=user, user_profile=user_profile, 
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
    return render_template('users/edit_user.html',
                        user=user,
                        user_profile=user_profile,
                        orgs=orgs,
                        is_admin=is_admin,
                        current_role=current_role,  # ← добавляем эту переменную
                        user_login=current_user.login)

@app.route('/temp_assign', methods=['POST'])
@login_required
def temp_assign():
    # В тестовом режиме запрещаем выдачу
    if TEST_MODE:
        flash('Выдача ТМЦ недоступна в тестовом режиме', 'warning')
        return redirect(url_for('index'))
    
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

    # Определяем ответственного МОЛ для записи
    # Если выдачу делает админ, используем ответственного МОЛ из equipment.usersid
    # Если выдачу делает МОЛ, используем текущего пользователя
    responsible_mol_id = equipment.usersid if is_admin else current_user.id
    
    # Создаём запись о временной выдаче
    # В mol_userid записываем ответственного МОЛ (не того, кто выдал, а того, за кем числится ТМЦ)
    usage = EquipmentTempUsage(
        equipment_id=eq_id,
        mol_userid=responsible_mol_id,
        user_temp_id=user_temp_id,
        comment=comment
    )
    db.session.add(usage)
    db.session.commit()

    # Логирование в таблицу move (опционально, для совместимости)
    # В useridfrom всегда указываем ответственного МОЛ
    move = Move(
        eqid=eq_id,
        dt=datetime.utcnow(),
        orgidfrom=equipment.orgid,
        orgidto=equipment.orgid,
        placesidfrom=equipment.placesid,
        placesidto=equipment.placesid,
        useridfrom=responsible_mol_id,
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
    # В тестовом режиме запрещаем возврат
    if TEST_MODE:
        flash('Возврат ТМЦ недоступен в тестовом режиме', 'warning')
        return redirect(url_for('my_temp_tmc'))
    
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
    # Страница доступна всем авторизованным пользователям
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('temp_usage/my_temp_tmc.html',
                             active_usages=[],
                             tmc_count=0,
                             total_cost=0)
    
    # Получаем активные выдачи для текущего пользователя
    active_usages = EquipmentTempUsage.query.filter_by(
        user_temp_id=current_user.id,
        returned=False
    ).all()
    
    # Подсчитываем статистику
    tmc_count = len(active_usages)
    total_cost = 0
    
    for usage in active_usages:
        if usage.equipment and usage.equipment.cost:
            cost_value = float(usage.equipment.cost) if usage.equipment.cost else 0
            total_cost += cost_value

    return render_template('temp_usage/my_temp_tmc.html', 
                         usages=active_usages,
                         tmc_count=tmc_count,
                         total_cost=total_cost)

def calculate_stats_data(tmc_query, is_admin=False):
    """Вспомогательная функция для расчета статистики."""
    stats_data = {}
    
    # Получаем ID всех ТМЦ из запроса
    tmc_ids = [eq.id for eq in tmc_query.all()]
    
    if not tmc_ids:
        return stats_data
    
    # Статистика по категориям (количество ТМЦ)
    category_stats = db.session.query(
        Category.name.label('category_name'),
        func.count(Equipment.id).label('count')
    ).join(GroupNome, Category.id == GroupNome.category_id)\
     .join(Nome, GroupNome.id == Nome.groupid)\
     .join(Equipment, Nome.id == Equipment.nomeid)\
     .filter(Equipment.id.in_(tmc_ids))\
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
     .filter(Equipment.id.in_(tmc_ids))\
     .group_by(Category.id, Category.name)\
     .order_by(func.sum(Equipment.cost).desc())\
     .all()
    
    stats_data['category_cost_labels'] = [row.category_name for row in category_cost_stats] if category_cost_stats else []
    stats_data['category_costs'] = [float(row.total_cost) for row in category_cost_stats] if category_cost_stats else []
    
    # Статистика по отделам (только для админа)
    if is_admin:
        department_stats = db.session.query(
            Department.name.label('department_name'),
            func.count(Equipment.id).label('count')
        ).join(Equipment, Department.id == Equipment.department_id)\
         .filter(Equipment.id.in_(tmc_ids))\
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
         .filter(Equipment.id.in_(tmc_ids))\
         .group_by(Users.id, Users.login)\
         .order_by(func.count(Equipment.id).desc())\
         .limit(10)\
         .all()
        
        stats_data['user_labels'] = [row.user_login for row in user_stats] if user_stats else []
        stats_data['user_counts'] = [row.count for row in user_stats] if user_stats else []
    
    # Динамика добавления ТМЦ по месяцам (последние 12 месяцев)
    twelve_months_ago = datetime.now() - relativedelta(days=365)
    
    # Получаем все ТМЦ за последний год из нашего запроса
    all_equipment = Equipment.query.filter(
        Equipment.id.in_(tmc_ids),
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
    repair_count = Equipment.query.filter(Equipment.id.in_(tmc_ids), Equipment.repair == True).count()
    active_count = Equipment.query.filter(Equipment.id.in_(tmc_ids), Equipment.repair == False).count()
    
    stats_data['status_labels'] = ['Активные', 'В ремонте']
    stats_data['status_counts'] = [active_count, repair_count]
    
    # Общее количество комплектующих (только для админа)
    if is_admin:
        components_count = Equipment.query.filter_by(active=True, os=False).count()
        stats_data['components_count'] = components_count
    
    return stats_data

@app.route('/all_stats')
@login_required
def all_stats():
    """Страница статистики для администратора - статистика по всем ТМЦ."""
    is_admin = current_user.mode == 1
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        empty_stats = {
            'tmc_count': 0,
            'total_cost': 0,
            'active_users': 0,
            'category_labels': [],
            'category_counts': [],
            'category_cost_labels': [],
            'category_costs': [],
            'department_labels': [],
            'department_counts': [],
            'user_labels': [],
            'user_counts': [],
            'monthly_labels': [],
            'monthly_counts': [],
            'status_labels': ['В эксплуатации', 'В ремонте', 'Потеряно'],
            'status_counts': [0, 0, 0],
            'components_count': 0
        }
        return render_template('reports/stats.html', 
                             stats_data=empty_stats, 
                             tmc_count=0,
                             total_cost=0,
                             active_users=0,
                             is_admin=True,
                             page_title='Статистика системы')
    
    if not is_admin:
        flash('Доступ запрещён. Только администратор может просматривать общую статистику.', 'danger')
        return redirect(url_for('index'))
    
    # Запрос всех ТМЦ
    tmc_query = Equipment.query.filter_by(active=True, os=True)
    tmc_count = tmc_query.count()
    total_cost = db.session.query(func.coalesce(func.sum(Equipment.cost), 0)).filter(
        Equipment.id.in_([eq.id for eq in tmc_query.all()])
    ).scalar()
    
    # Подсчёт активных пользователей
    active_users = db.session.query(Equipment.usersid).filter(
        Equipment.active == True,
        Equipment.os == True
    ).distinct().count()
    
    # Рассчитываем статистику
    stats_data = calculate_stats_data(tmc_query, is_admin=True)
    stats_data['components_count'] = Equipment.query.filter_by(active=True, os=False).count()
    
    return render_template('reports/stats.html',
                         tmc_count=tmc_count,
                         total_cost=total_cost,
                         active_users=active_users,
                         stats_data=stats_data,
                         is_admin=True,
                         page_title='Статистика системы')

@app.route('/my_stats')
@login_required
def my_stats():
    """Страница статистики для МОЛ - статистика только по его ТМЦ."""
    is_mol = current_user_has_role(1)
    is_admin = current_user.mode == 1
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        empty_stats = {
            'tmc_count': 0,
            'total_cost': 0,
            'status_counts': {'active': 0, 'repair': 0, 'lost': 0},
            'status_costs': {'active': 0, 'repair': 0, 'lost': 0},
            'components_count': 0,
            'department_labels': [],
            'department_counts': []
        }
        return render_template('reports/stats.html', stats_data=empty_stats, is_admin=False)
    
    if not (is_mol or is_admin):
        flash('Доступ запрещён. Только МОЛ может просматривать свою статистику.', 'danger')
        return redirect(url_for('index'))
    
    # Запрос ТМЦ текущего МОЛ
    tmc_query = Equipment.query.filter_by(usersid=current_user.id, active=True, os=True)
    tmc_ids = [eq.id for eq in tmc_query.all()]
    tmc_count = len(tmc_ids)
    total_cost = db.session.query(func.coalesce(func.sum(Equipment.cost), 0)).filter(
        Equipment.id.in_(tmc_ids)
    ).scalar() or 0
    
    # Рассчитываем базовую статистику
    stats_data = calculate_stats_data(tmc_query, is_admin=False)
    
    # Дополнительная статистика по статусам (включая "Потерян")
    if tmc_ids:
        # Количество по статусам
        active_count = Equipment.query.filter(
            Equipment.id.in_(tmc_ids),
            Equipment.repair == False,
            Equipment.lost == False
        ).count()
        repair_count = Equipment.query.filter(
            Equipment.id.in_(tmc_ids),
            Equipment.repair == True
        ).count()
        lost_count = Equipment.query.filter(
            Equipment.id.in_(tmc_ids),
            Equipment.lost == True
        ).count()
        
        # Стоимость по статусам
        active_cost = db.session.query(func.coalesce(func.sum(Equipment.cost), 0)).filter(
            Equipment.id.in_(tmc_ids),
            Equipment.repair == False,
            Equipment.lost == False
        ).scalar() or 0
        
        repair_cost = db.session.query(func.coalesce(func.sum(Equipment.cost), 0)).filter(
            Equipment.id.in_(tmc_ids),
            Equipment.repair == True
        ).scalar() or 0
        
        lost_cost = db.session.query(func.coalesce(func.sum(Equipment.cost), 0)).filter(
            Equipment.id.in_(tmc_ids),
            Equipment.lost == True
        ).scalar() or 0
        
        stats_data['status_labels'] = ['В эксплуатации', 'В ремонте', 'Потерян']
        stats_data['status_counts'] = [active_count, repair_count, lost_count]
        stats_data['status_costs'] = [float(active_cost), float(repair_cost), float(lost_cost)]
    
    # Статистика по отделам для МОЛ
    if tmc_ids:
        department_stats = db.session.query(
            Department.name.label('department_name'),
            func.count(Equipment.id).label('count')
        ).join(Equipment, Department.id == Equipment.department_id)\
         .filter(Equipment.id.in_(tmc_ids))\
         .group_by(Department.id, Department.name)\
         .order_by(func.count(Equipment.id).desc())\
         .limit(10)\
         .all()
        
        stats_data['department_labels'] = [row.department_name for row in department_stats] if department_stats else []
        stats_data['department_counts'] = [row.count for row in department_stats] if department_stats else []
    
    # Статистика по комплектующим МОЛ
    components_count = Equipment.query.filter_by(
        usersid=current_user.id,
        active=True,
        os=False
    ).count()
    stats_data['components_count'] = components_count
    
    return render_template('reports/stats.html',
                         tmc_count=tmc_count,
                         total_cost=total_cost,
                         active_users=0,
                         stats_data=stats_data,
                         is_admin=False,
                         page_title='Моя статистика')

@app.route('/all_moves')
@login_required
def all_moves():
    """Страница всех перемещений для администратора."""
    is_admin = current_user.mode == 1
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('reports/all_moves.html', moves_data=[])
    
    
    if not is_admin:
        flash('Доступ запрещён. Только администратор может просматривать все перемещения.', 'danger')
        return redirect(url_for('index'))
    
    # Получаем все перемещения, отсортированные по дате (новые сначала)
    moves = Move.query.order_by(Move.dt.desc()).limit(100).all()
    
    # Загружаем связанные данные для отображения
    moves_data = []
    for move in moves:
        equipment = Equipment.query.get(move.eqid)
        place_from = Places.query.get(move.placesidfrom) if move.placesidfrom else None
        place_to = Places.query.get(move.placesidto) if move.placesidto else None
        user_from = Users.query.get(move.useridfrom) if move.useridfrom else None
        user_to = Users.query.get(move.useridto) if move.useridto else None
        
        moves_data.append({
            'move': move,
            'equipment': equipment,
            'place_from': place_from,
            'place_to': place_to,
            'user_from': user_from,
            'user_to': user_to
        })
    
    return render_template('reports/all_moves.html', moves_data=moves_data)

@app.route('/my_moves')
@login_required
def my_moves():
    """Страница перемещений для МОЛ - только перемещения его ТМЦ и комплектующих."""
    is_mol = current_user_has_role(1)
    is_admin = current_user.mode == 1
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('reports/my_moves.html', moves_data=[], is_mol=is_mol)
    
    
    if not (is_mol or is_admin):
        flash('Доступ запрещён. Только МОЛ может просматривать свои перемещения.', 'danger')
        return redirect(url_for('index'))
    
    # Получаем все ТМЦ, которые числятся за текущим МОЛ
    my_equipment_ids = db.session.query(Equipment.id).filter_by(
        usersid=current_user.id,
        active=True
    ).all()
    my_equipment_ids = [eq[0] for eq in my_equipment_ids]
    
    # Получаем ID основного ТМЦ для комплектующих, которые связаны с ТМЦ МОЛ
    # Перемещения комплектующих записываются через их основное ТМЦ (id_main_asset)
    my_components_main_asset_ids = db.session.query(AppComponents.id_main_asset).join(
        Equipment, AppComponents.id_main_asset == Equipment.id
    ).filter(
        Equipment.usersid == current_user.id,
        Equipment.active == True
    ).distinct().all()
    my_components_main_asset_ids = [comp[0] for comp in my_components_main_asset_ids]
    
    # Объединяем ID ТМЦ и основных ТМЦ для комплектующих
    all_equipment_ids = list(set(my_equipment_ids + my_components_main_asset_ids))
    
    # Получаем перемещения для ТМЦ МОЛ
    # Перемещения комплектующих уже включены через их основное ТМЦ
    if all_equipment_ids:
        moves = Move.query.filter(
            Move.eqid.in_(all_equipment_ids)
        ).order_by(Move.dt.desc()).limit(100).all()
    else:
        moves = []
    
    # Загружаем связанные данные для отображения
    moves_data = []
    for move in moves:
        equipment = Equipment.query.get(move.eqid)
        place_from = Places.query.get(move.placesidfrom) if move.placesidfrom else None
        place_to = Places.query.get(move.placesidto) if move.placesidto else None
        user_from = Users.query.get(move.useridfrom) if move.useridfrom else None
        user_to = Users.query.get(move.useridto) if move.useridto else None
        
        moves_data.append({
            'move': move,
            'equipment': equipment,
            'place_from': place_from,
            'place_to': place_to,
            'user_from': user_from,
            'user_to': user_to
        })
    
    return render_template('reports/my_moves.html', moves_data=moves_data, is_mol=is_mol)

@app.route('/my_friends')
@login_required
def my_friends():
    """Страница "Мои друзья" - для МОЛ показывает пользователей, которым выдавал ТМЦ, для обычных пользователей - МОЛ, которые выдавали им ТМЦ."""
    is_mol = current_user_has_role(1)
    is_admin = current_user.mode == 1
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('temp_usage/my_friends.html',
                             friends=[],
                             is_mol=is_mol,
                             is_admin=is_admin)
    
    if is_mol or is_admin:
        # Для МОЛ: показываем пользователей, которым МОЛ выдавал ТМЦ
        # Получаем всех пользователей, которым МОЛ выдавал ТМЦ (включая возвращенные)
        all_assignments = db.session.query(
            EquipmentTempUsage.user_temp_id,
            func.count(EquipmentTempUsage.id).label('total_assignments'),
            func.sum(case((EquipmentTempUsage.returned == False, 1), else_=0)).label('active_assignments')
        ).filter(
            EquipmentTempUsage.mol_userid == current_user.id
        ).group_by(EquipmentTempUsage.user_temp_id).all()
        
        # Получаем информацию о пользователях и их профилях
        friends_data = []
        for user_id, total_count, active_count in all_assignments:
            user = Users.query.get(user_id)
            if user:
                # Получаем профиль пользователя
                profile = UsersProfile.query.filter_by(usersid=user_id).first()
                user_photo = url_for('static', filename='uploads/noimage.jpg')
                if profile and profile.jpegphoto and profile.jpegphoto != 'noimage.jpg':
                    user_photo = url_for('static', filename=f'uploads/{profile.jpegphoto}')
                
                friends_data.append({
                    'user': user,
                    'profile': profile,
                    'photo': user_photo,
                    'total_assignments': total_count or 0,
                    'active_assignments': active_count or 0
                })
        
        # Сортируем по количеству активных выдач (сначала те, у кого больше активных)
        friends_data.sort(key=lambda x: x['active_assignments'], reverse=True)
        
        return render_template('temp_usage/my_friends.html', 
                             friends_data=friends_data,
                             is_mol=is_mol,
                             is_admin=is_admin,
                             is_mol_view=True)
    else:
        # Для обычных пользователей: показываем только МОЛ с активными выдачами
        # Получаем всех МОЛ, которые выдавали ТМЦ текущему пользователю (только активные выдачи)
        all_assignments = db.session.query(
            EquipmentTempUsage.mol_userid,
            func.count(EquipmentTempUsage.id).label('total_assignments'),
            func.count(EquipmentTempUsage.id).label('active_assignments')
        ).filter(
            EquipmentTempUsage.user_temp_id == current_user.id,
            EquipmentTempUsage.returned == False
        ).group_by(EquipmentTempUsage.mol_userid).all()
        
        # Получаем информацию о МОЛ и их профилях
        friends_data = []
        for mol_id, total_count, active_count in all_assignments:
            mol_user = Users.query.get(mol_id)
            if mol_user:
                # Получаем профиль МОЛ
                profile = UsersProfile.query.filter_by(usersid=mol_id).first()
                user_photo = url_for('static', filename='uploads/noimage.jpg')
                if profile and profile.jpegphoto and profile.jpegphoto != 'noimage.jpg':
                    user_photo = url_for('static', filename=f'uploads/{profile.jpegphoto}')
                
                friends_data.append({
                    'user': mol_user,
                    'profile': profile,
                    'photo': user_photo,
                    'total_assignments': total_count or 0,
                    'active_assignments': active_count or 0
                })
        
        # Сортируем по количеству активных выдач (сначала те, у кого больше активных)
        friends_data.sort(key=lambda x: x['active_assignments'], reverse=True)
        
        return render_template('temp_usage/my_friends.html', 
                             friends_data=friends_data,
                             is_mol=False,
                             is_admin=False,
                             is_mol_view=False)

@app.route('/friend_equipment/<int:friend_user_id>')
@login_required
def friend_equipment(friend_user_id):
    """Страница со списком выданного имущества конкретному пользователю (для МОЛ) или выданного конкретным МОЛ (для обычных пользователей)."""
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('temp_usage/friend_equipment.html',
                             active_usages=[],
                             active_cost=0,
                             friend_user_id=friend_user_id,
                             is_mol_view=current_user_has_role(1) or current_user.mode == 1)
    
    is_mol = current_user_has_role(1)
    is_admin = current_user.mode == 1
    
    friend_user = Users.query.get_or_404(friend_user_id)
    
    if is_mol or is_admin:
        # Для МОЛ: показываем ТМЦ, выданные конкретному пользователю
        # Проверяем, что этот пользователь действительно получал ТМЦ от текущего МОЛ
        active_usages = EquipmentTempUsage.query.filter_by(
            mol_userid=current_user.id,
            user_temp_id=friend_user_id,
            returned=False
        ).order_by(EquipmentTempUsage.dt_start.desc()).all()
    else:
        # Для обычных пользователей: показываем ТМЦ, выданные конкретным МОЛ текущему пользователю
        # Проверяем, что этот МОЛ действительно выдавал ТМЦ текущему пользователю
        active_usages = EquipmentTempUsage.query.filter_by(
            mol_userid=friend_user_id,
            user_temp_id=current_user.id,
            returned=False
        ).order_by(EquipmentTempUsage.dt_start.desc()).all()
    
    # Подсчитываем стоимость активных ТМЦ
    active_cost = 0
    
    for usage in active_usages:
        if usage.equipment and usage.equipment.cost:
            cost_value = float(usage.equipment.cost) if usage.equipment.cost else 0
            active_cost += cost_value
    
    # Получаем профиль пользователя
    profile = UsersProfile.query.filter_by(usersid=friend_user_id).first()
    user_photo = url_for('static', filename='uploads/noimage.jpg')
    if profile and profile.jpegphoto and profile.jpegphoto != 'noimage.jpg':
        user_photo = url_for('static', filename=f'uploads/{profile.jpegphoto}')
    
    return render_template('temp_usage/friend_equipment.html',
                         friend_user=friend_user,
                         friend_profile=profile,
                         friend_photo=user_photo,
                         active_usages=active_usages,
                         active_cost=active_cost,
                         is_mol=is_mol,
                         is_admin=is_admin,
                         is_mol_view=(is_mol or is_admin))

# === УПРАВЛЕНИЕ НОВОСТЯМИ (только для админа) ===

@app.route('/manage_news')
@login_required
def manage_news():
    """Список всех новостей для управления (только для администраторов)."""
    is_admin = current_user.mode == 1
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('news/manage_news.html',
                             all_news=[],
                             is_admin=is_admin)
    
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    
    all_news = News.query.order_by(News.pinned.desc(), News.dt.desc()).all()
    return render_template('news/manage_news.html', all_news=all_news, is_admin=is_admin)

@app.route('/add_news', methods=['GET', 'POST'])
@login_required
def add_news():
    """Создание новой новости (только для администраторов)."""
    # В тестовом режиме запрещаем создание
    if TEST_MODE:
        flash('Создание новостей недоступно в тестовом режиме', 'warning')
        return redirect(url_for('manage_news'))
    
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        stiker = request.form.get('stiker') == 'on'
        pinned = request.form.get('pinned') == 'on'
        
        if not title or not body:
            flash('Заголовок и текст новости обязательны', 'danger')
            return redirect(url_for('add_news'))
        
        # Если закрепляем новую новость, снимаем закрепление с остальных
        if pinned:
            News.query.filter_by(pinned=True).update({'pinned': False})
        
        new_news = News(
            title=title,
            body=body,
            stiker=stiker,
            pinned=pinned,
            dt=datetime.utcnow()
        )
        
        try:
            db.session.add(new_news)
            db.session.commit()
            flash('Новость успешно создана!', 'success')
            return redirect(url_for('manage_news'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании новости: {str(e)}', 'danger')
            return redirect(url_for('add_news'))
    
    return render_template('news/add_news.html', is_admin=is_admin)

@app.route('/edit_news/<int:news_id>', methods=['GET', 'POST'])
@login_required
def edit_news(news_id):
    """Редактирование новости (только для администраторов)."""
    # В тестовом режиме запрещаем редактирование
    if TEST_MODE:
        flash('Редактирование новостей недоступно в тестовом режиме', 'warning')
        return redirect(url_for('manage_news'))
    
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    
    news = News.query.get_or_404(news_id)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        stiker = request.form.get('stiker') == 'on'
        pinned = request.form.get('pinned') == 'on'
        
        if not title or not body:
            flash('Заголовок и текст новости обязательны', 'danger')
            return redirect(url_for('edit_news', news_id=news_id))
        
        # Если закрепляем новость, снимаем закрепление с остальных
        if pinned and not news.pinned:
            News.query.filter(News.pinned == True, News.id != news_id).update({'pinned': False})
        
        news.title = title
        news.body = body
        news.stiker = stiker
        news.pinned = pinned
        
        try:
            db.session.commit()
            flash('Новость успешно обновлена!', 'success')
            return redirect(url_for('manage_news'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении новости: {str(e)}', 'danger')
            return redirect(url_for('edit_news', news_id=news_id))
    
    return render_template('news/edit_news.html', news=news, is_admin=is_admin)

@app.route('/delete_news/<int:news_id>', methods=['POST'])
@login_required
def delete_news(news_id):
    """Удаление новости (только для администраторов)."""
    # В тестовом режиме запрещаем удаление
    if TEST_MODE:
        flash('Удаление новостей недоступно в тестовом режиме', 'warning')
        return redirect(url_for('manage_news'))
    
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    
    news = News.query.get_or_404(news_id)
    
    try:
        db.session.delete(news)
        db.session.commit()
        flash('Новость успешно удалена!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении новости: {str(e)}', 'danger')
    
    return redirect(url_for('manage_news'))

# === УПРАВЛЕНИЕ ОТДЕЛАМИ ===

@app.route('/my_departments')
@login_required
def my_departments():
    """Отображение отделов: для МОЛ - только отделы с ТМЦ, для админа - все отделы."""
    is_admin = current_user.mode == 1
    
    # В тестовом режиме возвращаем пустые данные
    if TEST_MODE:
        return render_template('departments/my_departments.html',
                             departments=[],
                             is_admin=is_admin)
    
    if is_admin:
        # Для админа - все отделы
        departments = Department.query.filter_by(active=True).order_by(Department.name).all()
    else:
        # Для МОЛ - только отделы, где у него есть ТМЦ
        departments = db.session.query(Department).join(
            Equipment, Department.id == Equipment.department_id
        ).filter(
            Equipment.usersid == current_user.id,
            Equipment.active == True,
            Equipment.os == True,
            Department.active == True
        ).distinct().order_by(Department.name).all()
    
    # Подсчёт статистики по каждому отделу
    department_stats = []
    for dept in departments:
        if is_admin:
            # Для админа - все ТМЦ в отделе
            tmc_count = Equipment.query.filter_by(
                department_id=dept.id,
                active=True,
                os=True
            ).count()
            total_cost = db.session.query(
                func.coalesce(func.sum(Equipment.cost), 0)
            ).filter_by(
                department_id=dept.id,
                active=True,
                os=True
            ).scalar()
        else:
            # Для МОЛ - только его ТМЦ в отделе
            tmc_count = Equipment.query.filter_by(
                department_id=dept.id,
                usersid=current_user.id,
                active=True,
                os=True
            ).count()
            total_cost = db.session.query(
                func.coalesce(func.sum(Equipment.cost), 0)
            ).filter_by(
                department_id=dept.id,
                usersid=current_user.id,
                active=True,
                os=True
            ).scalar()
        
        department_stats.append({
            'department': dept,
            'tmc_count': tmc_count,
            'total_cost': float(total_cost) if total_cost else 0.0
        })
    
    return render_template('departments/my_departments.html',
                          department_stats=department_stats,
                          is_admin=is_admin)

@app.route('/add_department', methods=['GET', 'POST'])
@login_required
def add_department():
    """Создание нового отдела (только для администраторов)."""
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('my_departments'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip()
        
        if not name or not code:
            flash('Все поля обязательны для заполнения', 'danger')
            return redirect(url_for('add_department'))
        
        # Проверяем уникальность кода
        existing_dept = Department.query.filter_by(code=code).first()
        if existing_dept:
            flash(f'Отдел с кодом "{code}" уже существует', 'danger')
            return redirect(url_for('add_department'))
        
        try:
            new_department = Department(
                name=name,
                code=code,
                active=True
            )
            db.session.add(new_department)
            db.session.commit()
            flash(f'Отдел "{name}" успешно создан', 'success')
            return redirect(url_for('my_departments'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании отдела: {str(e)}', 'danger')
    
    return render_template('departments/add_department.html')

@app.route('/edit_department/<int:department_id>', methods=['GET', 'POST'])
@login_required
def edit_department(department_id):
    """Редактирование отдела (только для администраторов)."""
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('my_departments'))
    
    department = Department.query.get_or_404(department_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip()
        active = request.form.get('active') == 'on'
        
        if not name or not code:
            flash('Все поля обязательны для заполнения', 'danger')
            return redirect(url_for('edit_department', department_id=department_id))
        
        # Проверяем уникальность кода (кроме текущего отдела)
        existing_dept = Department.query.filter(
            Department.code == code,
            Department.id != department_id
        ).first()
        if existing_dept:
            flash(f'Отдел с кодом "{code}" уже существует', 'danger')
            return redirect(url_for('edit_department', department_id=department_id))
        
        try:
            department.name = name
            department.code = code
            department.active = active
            db.session.commit()
            flash(f'Отдел "{name}" успешно обновлён', 'success')
            return redirect(url_for('my_departments'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении отдела: {str(e)}', 'danger')
    
    return render_template('departments/edit_department.html',
                          department=department)

@app.route('/delete_department/<int:department_id>', methods=['POST'])
@login_required
def delete_department(department_id):
    """Удаление отдела (только для администраторов)."""
    is_admin = current_user.mode == 1
    if not is_admin:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('my_departments'))
    
    department = Department.query.get_or_404(department_id)
    
    # Проверяем, есть ли ТМЦ, привязанные к этому отделу
    tmc_count = Equipment.query.filter_by(
        department_id=department_id,
        active=True
    ).count()
    
    if tmc_count > 0:
        flash(f'Невозможно удалить отдел "{department.name}": к нему привязано {tmc_count} ТМЦ. Сначала удалите или переместите ТМЦ.', 'danger')
        return redirect(url_for('my_departments'))
    
    try:
        # Помечаем отдел как неактивный вместо физического удаления
        department.active = False
        db.session.commit()
        flash(f'Отдел "{department.name}" успешно удалён', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении отдела: {str(e)}', 'danger')
    
    return redirect(url_for('my_departments'))

@app.route('/generate_form8/<int:department_id>')
@login_required
def generate_form8(department_id):
    """Генерация формы 8 (Книга учета материальных ценностей) для отдела."""
    is_admin = current_user.mode == 1
    department = Department.query.get_or_404(department_id)
    
    # Проверка доступа: МОЛ может видеть только свои отделы
    if not is_admin:
        # Проверяем, есть ли у пользователя ТМЦ в этом отделе
        user_tmc_in_dept = Equipment.query.filter_by(
            department_id=department_id,
            usersid=current_user.id,
            active=True,
            os=True
        ).first()
        if not user_tmc_in_dept:
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('my_departments'))
    
    # Получаем ТМЦ отдела
    if is_admin:
        equipment_list = Equipment.query.filter_by(
            department_id=department_id,
            active=True,
            os=True
        ).order_by(Equipment.invnum, Equipment.buhname).all()
    else:
        equipment_list = Equipment.query.filter_by(
            department_id=department_id,
            usersid=current_user.id,
            active=True,
            os=True
        ).order_by(Equipment.invnum, Equipment.buhname).all()
    
    if not equipment_list:
        flash('В отделе нет ТМЦ для формирования отчета', 'warning')
        return redirect(url_for('my_departments'))
    
    # Генерируем PDF файл формы 8
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os
    
    # Регистрируем шрифт Times New Roman (или Liberation Serif как аналог)
    # Пытаемся найти системный шрифт с кириллицей (Times New Roman или аналог)
    times_font_paths = [
        '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]
    
    # Ищем доступный шрифт (приоритет Serif, затем Sans)
    regular_font_path = None
    bold_font_path = None
    
    # Сначала ищем Serif (Times New Roman аналог)
    for path in times_font_paths:
        if os.path.exists(path) and 'Serif' in path and 'Regular' in path:
            regular_font_path = path
            break
    
    # Если не нашли Serif, ищем Sans
    if not regular_font_path:
        for path in times_font_paths:
            if os.path.exists(path) and ('Regular' in path or ('Sans.ttf' in path and 'Bold' not in path and 'Serif' not in path)):
                regular_font_path = path
                break
    
    # Ищем Bold версию
    for path in times_font_paths:
        if os.path.exists(path) and 'Bold' in path:
            # Предпочитаем Serif Bold, если есть
            if 'Serif' in path:
                bold_font_path = path
                break
            elif not bold_font_path:  # Сохраняем первый найденный Bold
                bold_font_path = path
    
    # Регистрируем шрифты, если найдены
    if regular_font_path:
        try:
            pdfmetrics.registerFont(TTFont('TimesFont', regular_font_path))
            font_name = 'TimesFont'
        except:
            font_name = 'Helvetica'
    else:
        font_name = 'Helvetica'
    
    if bold_font_path:
        try:
            pdfmetrics.registerFont(TTFont('TimesFontBold', bold_font_path))
            bold_font_name = 'TimesFontBold'
        except:
            bold_font_name = 'Helvetica-Bold'
    else:
        bold_font_name = 'Helvetica-Bold'
    
    # Создаем буфер для PDF
    buffer = BytesIO()
    
    # Создаем документ в альбомной ориентации
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                           rightMargin=10*mm, leftMargin=10*mm,
                           topMargin=10*mm, bottomMargin=10*mm)
    
    # Контейнер для элементов документа
    elements = []
    
    # Стили
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName=bold_font_name
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#000000'),
        alignment=TA_LEFT,
        fontName=font_name
    )
    
    small_style = ParagraphStyle(
        'CustomSmall',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor('#000000'),
        alignment=TA_CENTER,
        fontName=font_name,
        leading=8  # Межстрочный интервал
    )
    
    # Стиль для данных в таблице (меньший размер для лучшего масштабирования)
    table_data_style = ParagraphStyle(
        'TableData',
        parent=styles['Normal'],
        fontSize=6,
        textColor=colors.HexColor('#000000'),
        alignment=TA_CENTER,  # Центрирование
        fontName=font_name,
        leading=7
    )
    
    # Стиль для чисел в таблице
    table_number_style = ParagraphStyle(
        'TableNumber',
        parent=styles['Normal'],
        fontSize=6,
        textColor=colors.HexColor('#000000'),
        alignment=TA_CENTER,  # Центрирование для чисел
        fontName=font_name,
        leading=7
    )
    
    # Стиль для заголовков таблицы (без переноса)
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=6,
        textColor=colors.HexColor('#000000'),
        alignment=TA_CENTER,
        fontName=bold_font_name,
        leading=7
    )
    
    # Титульная страница
    # Заголовок формы
    elements.append(Spacer(1, 20*mm))
    form_title = Paragraph('Форма № 8', normal_style)
    elements.append(form_title)
    elements.append(Spacer(1, 5*mm))
    
    # Основной заголовок
    main_title = Paragraph('КНИГА № ____<br/>УЧЕТА МАТЕРИАЛЬНЫХ ЦЕННОСТЕЙ', title_style)
    elements.append(main_title)
    elements.append(Spacer(1, 10*mm))
    
    # Получаем организацию пользователя
    user_org = None
    if hasattr(current_user, 'orgid') and current_user.orgid:
        user_org = db.session.get(Org, current_user.orgid)
    org_name = user_org.name if user_org else 'Не указано'
    
    # Получаем МОЛ (берем первого из списка ТМЦ или текущего пользователя)
    mol_name = 'Не указано'
    if equipment_list and equipment_list[0].users:
        mol_name = equipment_list[0].users.login
    elif current_user:
        mol_name = current_user.login
    
    # Информация об отделе и датах
    info_data = [
        [
            Paragraph('Учреждение:', normal_style),
            Paragraph(org_name, normal_style),
            Paragraph('по ОКУД', normal_style),
            Paragraph('', normal_style)
        ],
        [
            Paragraph('Структурное подразделение:', normal_style),
            Paragraph(department.name, normal_style),
            Paragraph('Дата открытия', normal_style),
            Paragraph('', normal_style)
        ],
        [
            Paragraph('Материально ответственное лицо:', normal_style),
            Paragraph(mol_name, normal_style),
            Paragraph('Дата закрытия', normal_style),
            Paragraph('', normal_style)
        ],
        [
            Paragraph('', normal_style),
            Paragraph('', normal_style),
            Paragraph('по ОКПО', normal_style),
            Paragraph('', normal_style)
        ]
    ]
    
    info_table = Table(info_data, colWidths=[50*mm, 90*mm, 35*mm, 25*mm])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), bold_font_name),
        ('FONTNAME', (1, 0), (1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))
    
    # Даты начала и окончания
    date_text = f'Начата «____» ________ {datetime.now().year} г.<br/>Окончена «____» ________ {datetime.now().year} г.'
    date_para = Paragraph(date_text, normal_style)
    elements.append(date_para)
    elements.append(Spacer(1, 5*mm))
    elements.append(PageBreak())
    
    # Пояснения к форме
    explanations = [
        'Пояснения к форме:',
        '1. Книга используется для учета материальных ценностей, выданных в установленных случаях во временное пользование на период не более одного месяца.',
        '2. Книга ведется в подразделении, на складе, в мастерской (цехе) воинской части.',
        '3. В книге отдельные листы отводятся для каждого наименования материальных ценностей или для каждой единицы (военнослужащего), получающей их.',
    ]
    
    for exp in explanations:
        elements.append(Paragraph(exp, normal_style))
        elements.append(Spacer(1, 3*mm))
    
    elements.append(PageBreak())
    
    # Группируем ТМЦ по nomeid (группам ТМЦ)
    from collections import defaultdict
    equipment_by_nome = defaultdict(list)
    for eq in equipment_list:
        equipment_by_nome[eq.nomeid].append(eq)
    
    # Для каждой группы ТМЦ создаем отдельную страницу
    for nome_id, nome_equipment_list in equipment_by_nome.items():
        # Получаем название группы ТМЦ
        nome = Nome.query.get(nome_id)
        nome_name = nome.name if nome else f'Группа ID {nome_id}'
        
        # Создаем единую таблицу для всей страницы
        # Берем данные из первого ТМЦ группы (если есть)
        first_eq = nome_equipment_list[0] if nome_equipment_list else None
        
        # Получаем данные для верхней секции
        # Убеждаемся, что все значения являются строками (не None)
        def safe_str(value):
            """Безопасное преобразование в строку, возвращает '' если None"""
            return str(value) if value is not None else ''
        
        warehouse = safe_str(first_eq.places.name) if first_eq and first_eq.places else ''  # Склад (из places)
        rack = safe_str(getattr(first_eq, 'warehouse_rack', None)) if first_eq else ''  # Стеллаж
        cell = safe_str(getattr(first_eq, 'warehouse_cell', None)) if first_eq else ''  # Ячейка
        unit_name = safe_str(getattr(first_eq, 'unit_name', None)) if first_eq else ''  # Единица измерения (наименование)
        unit_code = safe_str(getattr(first_eq, 'unit_code', None)) if first_eq else ''  # Единица измерения (код)
        price = f"{float(first_eq.cost):,.2f}".replace(',', ' ') if first_eq and first_eq.cost else ''  # Цена
        
        # Марка (из vendor через vendorid)
        brand = ''
        if first_eq and first_eq.nome and first_eq.nome.vendorid:
            vendor = Vendor.query.get(first_eq.nome.vendorid)
            brand = safe_str(vendor.name) if vendor else ''
        
        # Категория (сорт) - значение от 1 до 5 из группы ТМЦ
        category = ''
        if first_eq and first_eq.nome and first_eq.nome.category_sort:
            category = str(first_eq.nome.category_sort)  # Категория (сорт) - значение от 1 до 5
        profile = safe_str(getattr(first_eq, 'profile', None)) if first_eq else ''  # Профиль
        size = safe_str(getattr(first_eq, 'size', None)) if first_eq else ''  # Размер
        stock_norm = safe_str(getattr(first_eq, 'stock_norm', None)) if first_eq else ''  # Норма запаса
        service_life = first_eq.dtendlife.strftime('%d.%m.%Y') if first_eq and first_eq.dtendlife else ''  # Срок службы
        
        # Создаем единую таблицу
        table_data = []
        
        # Первая строка - заголовки верхней секции
        # Только заголовки, без значений
        header_row1 = [
            Paragraph('Склад', table_header_style),
            Paragraph('Стеллаж', table_header_style),
            Paragraph('Ячейка', table_header_style),
            Paragraph('Единица измерения', table_header_style),
            Paragraph('', table_header_style),  # Пустая ячейка для объединения
            Paragraph('Цена, руб. коп.', table_header_style),
            Paragraph('Марка', table_header_style),
            Paragraph('Категория (сорт)', table_header_style),
            Paragraph('Профиль', table_header_style),
            Paragraph('Размер', table_header_style),
            Paragraph('Норма запаса', table_header_style),
            Paragraph('Срок службы', table_header_style)
        ]
        table_data.append(header_row1)
        
        # Вторая строка - подзаголовки
        # Для объединяемых столбцов (0,1,2,5,6,7,8,9,10,11) - пустые ячейки
        # Для столбцов 3,4 - подзаголовки "наименование" и "код"
        header_row2 = [
            Paragraph('', table_data_style),  # Столбец 0 - пусто (будет объединен)
            Paragraph('', table_data_style),  # Столбец 1 - пусто (будет объединен)
            Paragraph('', table_data_style),  # Столбец 2 - пусто (будет объединен)
            Paragraph('наименование', table_header_style),
            Paragraph('код', table_header_style),
            Paragraph('', table_data_style),  # Столбец 5 - пусто (будет объединен)
            Paragraph('', table_data_style),  # Столбец 6 - пусто (будет объединен)
            Paragraph('', table_data_style),  # Столбец 7 - пусто (будет объединен)
            Paragraph('', table_data_style),  # Столбец 8 - пусто (будет объединен)
            Paragraph('', table_data_style),  # Столбец 9 - пусто (будет объединен)
            Paragraph('', table_data_style),  # Столбец 10 - пусто (будет объединен)
            Paragraph('', table_data_style)  # Столбец 11 - пусто (будет объединен)
        ]
        table_data.append(header_row2)
        
        # Третья строка - все данные из базы данных
        # Для объединяемых столбцов (0,1,2,5,6,7,8,9,10,11) - значения из БД
        # Для столбцов 3,4 - значения единицы измерения из БД
        data_row3 = [
            Paragraph(warehouse, table_data_style) if warehouse else Paragraph('', table_data_style),  # Столбец 0 - значение склада
            Paragraph(rack, table_data_style) if rack else Paragraph('', table_data_style),  # Столбец 1 - значение стеллажа
            Paragraph(cell, table_data_style) if cell else Paragraph('', table_data_style),  # Столбец 2 - значение ячейки
            Paragraph(unit_name, table_data_style) if unit_name else Paragraph('', table_data_style),  # Столбец 3 - значение единицы измерения (наименование)
            Paragraph(unit_code, table_data_style) if unit_code else Paragraph('', table_data_style),  # Столбец 4 - значение единицы измерения (код)
            Paragraph(price, table_data_style) if price else Paragraph('', table_data_style),  # Столбец 5 - значение цены
            Paragraph(brand, table_data_style) if brand else Paragraph('', table_data_style),  # Столбец 6 - значение марки
            Paragraph(category, table_data_style) if category else Paragraph('', table_data_style),  # Столбец 7 - значение категории
            Paragraph(profile, table_data_style) if profile else Paragraph('', table_data_style),  # Столбец 8 - значение профиля
            Paragraph(size, table_data_style) if size else Paragraph('', table_data_style),  # Столбец 9 - значение размера
            Paragraph(stock_norm, table_data_style) if stock_norm else Paragraph('', table_data_style),  # Столбец 10 - значение нормы запаса
            Paragraph(service_life, table_data_style) if service_life else Paragraph('', table_data_style)  # Столбец 11 - значение срока службы
        ]
        table_data.append(data_row3)
        
        # Четвертая строка - "Наименование материальных ценностей" с названием группы (объединенная ячейка на всю ширину)
        nome_row = [
            Paragraph(f'Наименование материальных ценностей "{nome_name}"', table_header_style),
            Paragraph('', table_data_style),  # Пустые ячейки для объединения
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style)
        ]
        table_data.append(nome_row)
        
        # Пятая строка - заголовки основной таблицы
        main_header_row1 = [
            Paragraph('Порядковый<br/>номер<br/>записи', table_header_style),
            Paragraph('Дата<br/>записи', table_header_style),
            Paragraph('Документ', table_header_style),
            Paragraph('Документ', table_header_style),
            Paragraph('Документ', table_header_style),
            Paragraph('От кого получено<br/>(кому отпущено)', table_header_style),
            Paragraph('Заводской номер<br/>(иной номер)', table_header_style),
            Paragraph('Инвентарный<br/>номер', table_header_style),
            Paragraph('Приход', table_header_style),
            Paragraph('Расход', table_header_style),
            Paragraph('Остаток', table_header_style),
            Paragraph('Контроль<br/>(подпись и дата)', table_header_style)
        ]
        table_data.append(main_header_row1)
        
        # Шестая строка - подзаголовки для документа
        main_header_row2 = [
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('наименование', table_header_style),
            Paragraph('дата', table_header_style),
            Paragraph('номер', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style),
            Paragraph('', table_header_style)
        ]
        table_data.append(main_header_row2)
        
        # Данные для этой группы
        total_cost = 0
        for idx, eq in enumerate(nome_equipment_list, 1):
            # Дата поступления
            date_str = eq.datepost.strftime('%d.%m.%Y') if eq.datepost else ''
            
            # Документ (можно использовать накладные или другие документы)
            # Ищем связанные накладные
            doc_name = 'Поступление'
            doc_date = date_str
            doc_number = ''
            
            # Пытаемся найти первую накладную для этого ТМЦ (по дате накладной)
            # Сортируем по дате накладной, чтобы получить самую раннюю
            invoice_eq = InvoiceEquipment.query.join(Invoices).filter(
                InvoiceEquipment.equipment_id == eq.id
            ).order_by(Invoices.invoice_date.asc()).first()
            
            if invoice_eq and invoice_eq.invoice:
                doc_name = 'Накладная'
                doc_date = invoice_eq.invoice.invoice_date.strftime('%d.%m.%Y') if invoice_eq.invoice.invoice_date else date_str
                doc_number = invoice_eq.invoice.invoice_number or ''
                
                # Определяем, от кого был принят ТМЦ согласно первой накладной
                invoice = invoice_eq.invoice
                from_info = ''
                
                # Загружаем связанные данные, если они не загружены
                if invoice.type == 'Склад-МОЛ':
                    # От склада (from_knt)
                    if invoice.from_knt_id:
                        knt = Knt.query.get(invoice.from_knt_id)
                        if knt and knt.name:
                            from_info = knt.name
                        else:
                            from_info = f'Склад ID {invoice.from_knt_id}'
                    else:
                        from_info = 'Склад (не указан)'
                elif invoice.type == 'МОЛ-МОЛ':
                    # От МОЛ (from_user)
                    if invoice.from_user_id:
                        from_user = Users.query.get(invoice.from_user_id)
                        if from_user and from_user.login:
                            from_info = from_user.login
                        else:
                            from_info = f'МОЛ ID {invoice.from_user_id}'
                    else:
                        from_info = 'МОЛ (не указан)'
                elif invoice.type == 'МОЛ-Склад':
                    # От МОЛ (from_user) - при возврате на склад
                    if invoice.from_user_id:
                        from_user = Users.query.get(invoice.from_user_id)
                        if from_user and from_user.login:
                            from_info = from_user.login
                        else:
                            from_info = f'МОЛ ID {invoice.from_user_id}'
                    else:
                        from_info = 'МОЛ (не указан)'
                else:
                    from_info = 'Не указано'
                
                from_to_info = from_info
            else:
                # Если накладной нет, используем текущего МОЛ как fallback
                mol_name = eq.users.login if eq.users else 'Не указан'
                from_to_info = mol_name
            
            # Заводской номер
            factory_num = eq.sernum or ''
            
            # Инвентарный номер
            inv_num = eq.invnum or ''
            
            # Приход (стоимость при поступлении)
            cost = float(eq.cost) if eq.cost else 0.0
            total_cost += cost
            receipt = f"{cost:,.2f}".replace(',', ' ') if cost > 0 else ''
            
            # Расход (пусто, так как это книга учета)
            expense = ''
            
            # Остаток (равен приходу для учета)
            balance = receipt
            
            # Используем Paragraph для всех текстовых элементов для корректного масштабирования
            row = [
                Paragraph(str(idx), table_data_style),
                Paragraph(date_str, table_data_style) if date_str else '',
                Paragraph(doc_name, table_data_style) if doc_name else '',
                Paragraph(doc_date, table_data_style) if doc_date else '',
                Paragraph(doc_number, table_data_style) if doc_number else '',
                Paragraph(from_to_info, table_data_style) if from_to_info else '',  # Наименование ТМЦ и МОЛ
                Paragraph(factory_num, table_data_style) if factory_num else '',
                Paragraph(inv_num, table_data_style) if inv_num else '',
                Paragraph(receipt, table_number_style) if receipt else '',
                Paragraph(expense, table_number_style) if expense else '',
                Paragraph(balance, table_number_style) if balance else '',
                Paragraph('', table_data_style)  # Контроль (подпись и дата)
            ]
            table_data.append(row)
        
        # Итоговая строка для этой группы
        total_cost_str = f"{total_cost:,.2f}".replace(',', ' ')
        total_row = [
            Paragraph('ИТОГО', table_header_style),  # Используем стиль заголовка для "ИТОГО"
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph('', table_data_style),
            Paragraph(total_cost_str, table_number_style),
            Paragraph('', table_data_style),
            Paragraph(total_cost_str, table_number_style),
            Paragraph('', table_data_style)
        ]
        table_data.append(total_row)
        
        # Создаем таблицу (для альбомной ориентации увеличиваем ширину колонок)
        # Увеличиваем ширину колонок для предотвращения переноса слов
        table = Table(table_data, colWidths=[
            15*mm,  # Порядковый номер (увеличено)
            18*mm,  # Дата записи (увеличено)
            22*mm,  # Документ - наименование (увеличено)
            18*mm,  # Документ - дата (увеличено)
            18*mm,  # Документ - номер (увеличено)
            40*mm,  # От кого получено (увеличено)
            22*mm,  # Заводской номер (увеличено)
            20*mm,  # Инвентарный номер (увеличено)
            20*mm,  # Приход (увеличено)
            20*mm,  # Расход (увеличено)
            20*mm,  # Остаток (увеличено)
            28*mm   # Контроль (увеличено)
        ])
        
        # Стиль единой таблицы (белый фон)
        table.setStyle(TableStyle([
            # Общие стили для всей таблицы - белый фон
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            
            # Первая строка (индекс 0) - заголовки верхней секции
            ('FONTNAME', (0, 0), (-1, 0), bold_font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            # Объединение ячеек для "Единица измерения" в первой строке (горизонтально)
            ('SPAN', (3, 0), (4, 0)),
            
            # Вторая строка (индекс 1) - значения верхней секции
            ('FONTSIZE', (0, 1), (-1, 1), 6),
            # Подзаголовки единицы измерения (столбцы 3 и 4 не объединяем)
            ('FONTNAME', (3, 1), (4, 1), bold_font_name),
            
            # Объединение 1-й и 2-й строк для столбцов 0,1,2,5,6,7,8,9,10,11 (вертикально)
            # НЕ объединяем с третьей строкой, чтобы данные из строки 2 были видны
            # В ReportLab при SPAN отображается только содержимое первой ячейки
            # Поэтому объединяем только строки 0 и 1, а данные в строке 2 будут видны отдельно
            ('SPAN', (0, 0), (0, 1)),  # Столбец 0 (Склад) - объединяем строки 0 и 1
            ('SPAN', (1, 0), (1, 1)),  # Столбец 1 (Стеллаж) - объединяем строки 0 и 1
            ('SPAN', (2, 0), (2, 1)),  # Столбец 2 (Ячейка) - объединяем строки 0 и 1
            ('SPAN', (5, 0), (5, 1)),  # Столбец 5 (Цена) - объединяем строки 0 и 1
            ('SPAN', (6, 0), (6, 1)),  # Столбец 6 (Марка) - объединяем строки 0 и 1
            ('SPAN', (7, 0), (7, 1)),  # Столбец 7 (Категория) - объединяем строки 0 и 1
            ('SPAN', (8, 0), (8, 1)),  # Столбец 8 (Профиль) - объединяем строки 0 и 1
            ('SPAN', (9, 0), (9, 1)),  # Столбец 9 (Размер) - объединяем строки 0 и 1
            ('SPAN', (10, 0), (10, 1)),  # Столбец 10 (Норма запаса) - объединяем строки 0 и 1
            ('SPAN', (11, 0), (11, 1)),  # Столбец 11 (Срок службы) - объединяем строки 0 и 1
            
            # Третья строка (индекс 2) - все данные из базы данных
            ('FONTSIZE', (0, 2), (-1, 2), 6),
            
            # Четвертая строка (индекс 3) - "Наименование материальных ценностей" (объединенная на всю ширину)
            ('FONTNAME', (0, 3), (-1, 3), bold_font_name),
            ('FONTSIZE', (0, 3), (-1, 3), 6),
            ('SPAN', (0, 3), (-1, 3)),  # Объединяем все ячейки в строке
            
            # Пятая строка (индекс 4) - заголовки основной таблицы
            ('FONTNAME', (0, 4), (-1, 4), bold_font_name),
            ('FONTSIZE', (0, 4), (-1, 4), 6),
            # Объединение ячеек для заголовка "Документ"
            ('SPAN', (2, 4), (4, 4)),
            
            # Шестая строка (индекс 5) - подзаголовки документа
            ('FONTNAME', (0, 5), (-1, 5), font_name),
            ('FONTSIZE', (0, 5), (-1, 5), 5),
            
            # Данные (начиная с седьмой строки, индекс 6)
            ('FONTNAME', (0, 6), (-1, -2), font_name),
            ('FONTSIZE', (0, 6), (-1, -2), 6),
            ('ALIGN', (0, 6), (-1, -2), 'CENTER'),  # Все данные по центру
            
            # Общие стили для всей таблицы
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            
            # Итоговая строка
            ('FONTNAME', (0, -1), (-1, -1), bold_font_name),
            ('FONTSIZE', (0, -1), (-1, -1), 6),
        ]))
        
        elements.append(table)
        
        # Разрыв страницы перед следующей группой (кроме последней)
        nome_ids_list = list(equipment_by_nome.keys())
        if nome_id != nome_ids_list[-1]:
            elements.append(PageBreak())
    
    # Собираем PDF
    doc.build(elements)
    
    # Подготовка ответа
    buffer.seek(0)
    
    # Создаем безопасное имя файла (только ASCII символы)
    safe_dept_name = department.name.replace(' ', '_').encode('ascii', 'ignore').decode('ascii')
    if not safe_dept_name:
        safe_dept_name = 'department'
    filename_ascii = f"form8_{safe_dept_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Для кириллицы используем RFC 2231 encoding
    from urllib.parse import quote
    filename_utf8 = f"form8_{department.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filename_encoded = quote(filename_utf8.encode('utf-8'))
    
    response = Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'inline; filename="{filename_ascii}"; filename*=UTF-8\'\'{filename_encoded}'
        }
    )
    
    return response

# === ЗАПУСК ПРИЛОЖЕНИЯ ===

if __name__ == '__main__':
    # В продакшене используйте Gunicorn/uWSGI, а не встроенный сервер
    app.run(host='0.0.0.0', port=5000, debug=True)