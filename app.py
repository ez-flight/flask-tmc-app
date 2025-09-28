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
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal, InvalidOperation


from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Модели базы данных (должны быть определены в models.py)
from flask_migrate import Migrate
from models import Equipment, Nome, Org, Places, Users, db, GroupNome, Vendor, Department, Knt

# Загружаем переменные окружения из .env
load_dotenv()

# Создаём Flask-приложение
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-for-dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)  # ← ЭТА СТРОКА ОБЯЗАТЕЛЬНА!


# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # маршрут для перенаправления неавторизованных пользователей


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


# === ЗАГРУЗКА ПОЛЬЗОВАТЕЛЯ ДЛЯ Flask-Login ===

@login_manager.user_loader
def load_user(user_id):
    """Загружает пользователя по ID для Flask-Login."""
    return Users.query.get(int(user_id))


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
    # Группируем по nomeid и подсчитываем количество
    query = db.session.query(
        Equipment.nomeid,
        Nome.name.label('nome_name'),
        func.count(Equipment.id).label('quantity'),
        Nome.photo.label('nome_photo')  # Берем фото из таблицы nome
    ).join(Nome, Equipment.nomeid == Nome.id)\
     .filter(Equipment.active == True) \
     .group_by(Equipment.nomeid, Nome.name, Nome.photo)\
     .order_by(Nome.name)

    grouped_tmc = query.all()

    return render_template('index.html', grouped_tmc=grouped_tmc)


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
                photo_filename = f"{timestamp}.{ext}"
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
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], passport_filename))

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
            os=False,
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
    users = Users.query.all()
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
                photo_filename = f"{timestamp}.{ext}"  # Исправлено
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
                tmc.photo = photo_filename

        # Обработка паспорта при редактировании
        if 'passport' in request.files:
            file = request.files['passport']
            if file and file.filename != '':
                if not allowed_document(file.filename):
                    flash('Файл паспорта должен быть в формате PDF (с расширением .pdf)', 'danger')
                    return redirect(request.url)
        
                # Удаляем старый паспорт, если он есть и нигде больше не используется
                if tmc.passport_filename:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], tmc.passport_filename)
                    if os.path.exists(old_path):
                        other = Equipment.query.filter(
                            Equipment.passport_filename == tmc.passport_filename,
                            Equipment.id != tmc.id
                        ).first()
                        if not other:
                            os.remove(old_path)

                # Генерируем новое имя и сохраняем ТОЛЬКО если файл загружен
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                passport_filename = f"passport_{timestamp}.pdf"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], passport_filename))
                tmc.passport_filename = passport_filename

        # else: файл не выбран — ничего не делаем, оставляем старое значение

         # Исправлено: убрано дублирующее присваивание tmc.nomeid
        tmc.nomeid = int(request.form['nomeid'])

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
        return redirect(url_for('index'))

    # GET: подготовка данных для формы
    organizations = Org.query.all()
    places = Places.query.all()
    users = Users.query.all()
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
    """Удаление ТМЦ."""
    tmc = Equipment.query.get_or_404(tmc_id)
    if tmc.photo:
        path = os.path.join(app.config['UPLOAD_FOLDER'], tmc.photo)
        if os.path.exists(path):
            other = Equipment.query.filter(
                Equipment.photo == tmc.photo,
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
                photo_filename = f"{timestamp}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
                nome.photo = photo_filename

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
                    photo_filename = f"{timestamp}.{ext}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
                    
                    # Удаляем старое фото, если оно больше нигде не используется
                    if nome.photo:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], nome.photo)
                        if os.path.exists(old_path):
                            # Проверяем, используется ли фото где-то еще
                            other = Equipment.query.filter(
                                Equipment.photo == nome.photo
                            ).first()
                            if not other:
                                os.remove(old_path)
                    
                    nome.photo = photo_filename
            
            cost_str = request.form.get('cost', '').strip()
            currentcost_str = request.form.get('currentcost', '').strip()
            
            cost = Decimal(cost_str) if cost_str else Decimal('0')
            currentcost = Decimal(currentcost_str) if currentcost_str else Decimal('0')
            
            is_os = bool(request.form.get('os'))
            kntid = request.form.get('kntid')
            kntid = int(kntid) if kntid and kntid.isdigit() else None
            
            date_start_str = request.form.get('date_start')
            dtendgar_str = request.form.get('dtendgar')
            
            for tmc in tmc_list:
                tmc.cost = cost
                tmc.currentcost = currentcost
                tmc.os = is_os
                tmc.kntid = kntid
                
                if date_start_str:
                    tmc.datepost = datetime.strptime(date_start_str, '%Y-%m-%d')
                
                if dtendgar_str:
                    tmc.dtendgar = datetime.strptime(dtendgar_str, '%Y-%m-%d').date()
                elif date_start_str:
                    start_date = datetime.strptime(date_start_str, '%Y-%m-%d')
                    tmc.dtendgar = (start_date + relativedelta(years=5)).date()
            
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
                    nome_id=nome_id,
                    nome_name=tmc_list[0].nome.name if tmc_list[0].nome else "Неизвестно",
                    tmc_count=len(tmc_list),
                    first_tmc=first_tmc,
                    suppliers=suppliers)


@app.route('/list_by_nome/<int:nome_id>')
def list_by_nome(nome_id):
    # Получаем наименование
    nome = Nome.query.get_or_404(nome_id)
    # Получаем все ТМЦ этого типа
    tmc_list = Equipment.query.filter_by(nomeid=nome_id).all()
    
    # Для отображения связанных данных (организация, место и т.д.)
    # Мы просто передаем список, а связанные объекты будем получать через отношения в шаблоне
    # (или через отдельные запросы, если связи не настроены)
    
    return render_template('list_by_nome.html', 
                           nome=nome, 
                           tmc_list=tmc_list,
                           now_date=date.today())  # ← добавлено

@app.route('/info_tmc/<int:tmc_id>')
@login_required
def info_tmc(tmc_id):
    tmc = Equipment.query.get_or_404(tmc_id)
    return render_template('info_tmc.html', tmc=tmc)

@app.route('/add_nome', methods=['GET', 'POST'])
@login_required
def add_nome():
    """Добавление нового наименования (группы ТМЦ)."""
    if request.method == 'POST':
        name = request.form['name'].strip()
        group_id = int(request.form['groupid'])
        vendor_id = int(request.form['vendorid'])

        if not name:
            flash('Наименование не может быть пустым', 'danger')
            return redirect(url_for('add_nome'))

        # Проверка на дубликат
        existing = Nome.query.filter_by(groupid=group_id, vendorid=vendor_id, name=name).first()
        if existing:
            flash('Такое наименование уже существует в этой группе и у этого производителя', 'warning')
            return redirect(url_for('add_nome'))

        new_nome = Nome(
            groupid=group_id,
            vendorid=vendor_id,
            name=name,
            active=True,
            photo=''
        )

        # Обработка фото (опционально)
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_image(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ext = filename.rsplit('.', 1)[1].lower()
                photo_filename = f"{timestamp}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
                new_nome.photo = photo_filename

        db.session.add(new_nome)
        db.session.commit()
        flash('Новое наименование успешно добавлено!', 'success')
        return redirect(url_for('index'))

    # GET: отображаем форму
    groups = GroupNome.query.filter_by(active=True).all()
    vendors = Vendor.query.filter_by(active=True).all()
    return render_template('add_nome.html', groups=groups, vendors=vendors)

# === ЗАПУСК ПРИЛОЖЕНИЯ ===

if __name__ == '__main__':
    # В продакшене используйте Gunicorn/uWSGI, а не встроенный сервер
    app.run(host='0.0.0.0', port=5000, debug=True)