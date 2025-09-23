# -*- coding: utf-8 -*-
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from models import Equipment, Nome, Org, Places, Users, db, GroupNome, Vendor, Department

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # Исправлена опечатка
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализируем базу данных с приложением
db.init_app(app)

# >>> ВЕРНУЛИ: Путь для загрузки фотографий внутрь проекта
UPLOAD_FOLDER = os.path.join('static', 'uploads')  # Папка для загрузок
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}  # Расширения

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Макс. 16MB

# Создаем папку, если её нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# <<<

# Создаем все таблицы (если они не существуют)
@app.before_request
def create_tables_once():
    if not hasattr(app, 'tables_created'):
        db.create_all()
        app.tables_created = True

# Главная страница: список всех ТМЦ
@app.route('/')
def index():
    dept_id = request.args.get('dept_id', type=int)
    if dept_id:
        tmc_list = Equipment.query.filter_by(department_id=dept_id).all()
    else:
        tmc_list = Equipment.query.all()

    departments = Department.query.filter_by(active=True).all()

    return render_template('index.html', tmc_list=tmc_list, departments=departments)

# Страница добавления нового ТМЦ
@app.route('/add', methods=['GET', 'POST'])
def add_tmc():
    if request.method == 'POST':
        buhname = request.form['buhname']
        sernum = request.form.get('sernum', '')
        invnum = request.form.get('invnum', '')
        comment = request.form.get('comment', '')

        # Получаем ID из новых полей
        groupid = int(request.form['groupid'])   # ID группы
        vendorid = int(request.form['vendorid']) # ID производителя
        nomeid = int(request.form['nomeid'])     # ID наименования

        # Остальные обязательные поля
        orgid = int(request.form['orgid'])
        placesid = int(request.form['placesid'])
        usersid = int(request.form['usersid'])

        # Новое поле: Отдел
        department_id = request.form.get('department_id')
        if department_id:
            department_id = int(department_id)
        else:
            department_id = None

        # Обработка фото (как было)
        photo_filename = ''
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ext = filename.rsplit('.', 1)[1].lower()
                photo_filename = f"{timestamp}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

        # Создаем новый объект ТМЦ
        new_tmc = Equipment(
           buhname=buhname,
           sernum=sernum,
           invnum=invnum,
           comment=comment,
           orgid=orgid,
           placesid=placesid,
           usersid=usersid,
           nomeid=nomeid,  # Используем выбранное наименование
           photo=photo_filename,
           department_id=department_id  # Привязка к отделу
        )

        db.session.add(new_tmc)
        db.session.commit()

        flash('ТМЦ успешно добавлен!', 'success')
        return redirect(url_for('index'))

    # Для GET: загружаем все данные
    organizations = Org.query.all()
    places = Places.query.all()
    users = Users.query.all()
    groups = GroupNome.query.filter_by(active=True).all()  # Передаем группы
    departments = Department.query.filter_by(active=True).all()  # Передаем отделы

    return render_template('add_tmc.html',
                           organizations=organizations,
                           places=places,
                           users=users,
                           groups=groups,
                           departments=departments)

# Маршрут для редактирования ТМЦ
@app.route('/edit/<int:tmc_id>', methods=['GET', 'POST'])
def edit_tmc(tmc_id):
    # Получаем объект ТМЦ по ID или возвращаем 404
    tmc = Equipment.query.get_or_404(tmc_id)

    if request.method == 'POST':
        # Обновляем поля из формы
        tmc.buhname = request.form['buhname']
        tmc.sernum = request.form.get('sernum', '')
        tmc.invnum = request.form.get('invnum', '')
        tmc.comment = request.form.get('comment', '')

        # Обработка загрузки нового фото (опционально)
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                # Удаляем старый файл, если он есть и не используется другими ТМЦ
                if tmc.photo:
                    old_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], tmc.photo)
                    if os.path.exists(old_photo_path):
                        other_tmc_with_same_photo = Equipment.query.filter(Equipment.photo == tmc.photo, Equipment.id != tmc_id).first()
                        if not other_tmc_with_same_photo:
                            os.remove(old_photo_path)

                # Сохраняем новый файл
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                photo_filename = f"{timestamp}.{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
                tmc.photo = photo_filename

        # Обновляем обязательные поля
        tmc.orgid = int(request.form['orgid'])
        tmc.placesid = int(request.form['placesid'])
        tmc.usersid = int(request.form['usersid'])

        # Получаем ID из новых полей
        groupid = int(request.form['groupid'])   # ID группы
        vendorid = int(request.form['vendorid']) # ID производителя
        nomeid = int(request.form['nomeid'])     # ID наименования

        tmc.nomeid = nomeid

        # Обновляем привязку к отделу
        department_id = request.form.get('department_id')
        tmc.department_id = int(department_id) if department_id else None

        # Сохраняем изменения в базе данных
        db.session.commit()

        flash('ТМЦ успешно обновлен!', 'success')
        return redirect(url_for('index'))

    # Для GET-запроса: загружаем данные для выпадающих списков и передаем текущий объект tmc в шаблон
    organizations = Org.query.all()
    places = Places.query.all()
    users = Users.query.all()
    groups = GroupNome.query.filter_by(active=True).all()  # Передаем группы
    departments = Department.query.filter_by(active=True).all()  # Передаем отделы

    # Получаем текущее наименование, производителя и группу для предзаполнения
    current_nome = Nome.query.get(tmc.nomeid)
    current_vendor = Vendor.query.get(current_nome.vendorid) if current_nome else None
    current_group = GroupNome.query.get(current_nome.groupid) if current_nome else None

    # Получаем списки для динамической подгрузки
    # Производители для текущей группы
    vendors = []
    if current_group:
        vendors = db.session.query(Vendor).join(Nome, Vendor.id == Nome.vendorid)\
            .filter(Nome.groupid == current_group.id)\
            .distinct()\
            .all()

    # Наименования для текущей группы и производителя
    nomenclatures = []
    if current_group and current_vendor:
        nomenclatures = Nome.query.filter_by(groupid=current_group.id, vendorid=current_vendor.id, active=True).all()

    return render_template('edit_tmc.html',
                           tmc=tmc,
                           organizations=organizations,
                           places=places,
                           users=users,
                           groups=groups,
                           departments=departments,  # Передаем отделы
                           current_group=current_group,
                           current_vendor=current_vendor,
                           current_nome=current_nome,
                           vendors=vendors,
                           nomenclatures=nomenclatures)

# Маршрут для удаления ТМЦ
@app.route('/delete/<int:tmc_id>', methods=['POST'])
def delete_tmc(tmc_id):
    tmc = Equipment.query.get_or_404(tmc_id)
    if tmc.photo:
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], tmc.photo)
        if os.path.exists(photo_path):
            other_tmc_with_same_photo = Equipment.query.filter(Equipment.photo == tmc.photo, Equipment.id != tmc_id).first()
            if not other_tmc_with_same_photo:
                os.remove(photo_path)
    db.session.delete(tmc)
    db.session.commit()
    flash('ТМЦ успешно удален!', 'danger')
    return redirect(url_for('index'))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/get_vendors_by_group/<int:group_id>')
def get_vendors_by_group(group_id):
    # Возвращаем ВСЕХ активных производителей, независимо от связи с группой
    vendors = Vendor.query.filter_by(active=True).order_by(Vendor.name).all()
    vendor_list = [{'id': v.id, 'name': v.name} for v in vendors]
    return {'vendors': vendor_list}

@app.route('/get_nomenclatures_by_group_and_vendor/<int:group_id>/<int:vendor_id>')
def get_nomenclatures_by_group_and_vendor(group_id, vendor_id):
    # Получаем все наименования для выбранной группы и производителя
    # Если связи нет — вернётся пустой список, и пользователь сможет создать новое наименование
    nomenclatures = Nome.query.filter_by(groupid=group_id, vendorid=vendor_id, active=True).all()
    nomenclature_list = [{'id': n.id, 'name': n.name} for n in nomenclatures]
    return {'nomenclatures': nomenclature_list}

@app.route('/add_nomenclature', methods=['POST'])
def add_nomenclature():
    group_id = request.form.get('groupid', type=int)
    vendor_id = request.form.get('vendorid', type=int)
    name = request.form.get('name', '').strip()

    if not group_id or not vendor_id or not name:
        return {'success': False, 'message': 'Все поля обязательны'}, 400

    # Проверяем, не существует ли уже такое наименование
    existing = Nome.query.filter_by(groupid=group_id, vendorid=vendor_id, name=name).first()
    if existing:
        return {'success': False, 'message': 'Такое наименование уже существует'}, 409

    # Создаем новое наименование
    new_nome = Nome(groupid=group_id, vendorid=vendor_id, name=name, active=True)
    db.session.add(new_nome)
    db.session.commit()

    return {'success': True, 'id': new_nome.id, 'name': new_nome.name}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)