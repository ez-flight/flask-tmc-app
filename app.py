# -*- coding: utf-8 -*-
import os
import hashlib
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from models import Equipment, Nome, Org, Places, Users, db, GroupNome, Vendor, Department

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализируем Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# Инициализируем базу данных
db.init_app(app)

# Настройки загрузки фото
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Создание таблиц при первом запросе
@app.before_request
def create_tables_once():
    if not hasattr(app, 'tables_created'):
        db.create_all()
        app.tables_created = True

# === Маршруты ===

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        user = Users.query.filter_by(login=login, active=True).first()

        if user:
            # Правильный алгоритм: SHA1(password + salt)
            candidate = hashlib.sha1((password + user.salt).encode()).hexdigest()
            if user.password == candidate:
                login_user(user)
                flash('Вы успешно вошли!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))

        flash('Неверный логин или пароль', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    dept_id = request.args.get('dept_id', type='int')
    if dept_id:
        tmc_list = Equipment.query.filter_by(department_id=dept_id).all()
    else:
        tmc_list = Equipment.query.all()
    departments = Department.query.filter_by(active=True).all()
    return render_template('index.html', tmc_list=tmc_list, departments=departments)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_tmc():
    if request.method == 'POST':
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

        photo_filename = ''
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ext = filename.rsplit('.', 1)[1].lower()
                photo_filename = f"{timestamp}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

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
        )
        db.session.add(new_tmc)
        db.session.commit()
        flash('ТМЦ успешно добавлен!', 'success')
        return redirect(url_for('index'))

    organizations = Org.query.all()
    places = Places.query.all()
    users = Users.query.all()
    groups = GroupNome.query.filter_by(active=True).all()
    departments = Department.query.filter_by(active=True).all()
    return render_template('add_tmc.html',
                           organizations=organizations,
                           places=places,
                           users=users,
                           groups=groups,
                           departments=departments)

@app.route('/edit/<int:tmc_id>', methods=['GET', 'POST'])
@login_required
def edit_tmc(tmc_id):
    tmc = Equipment.query.get_or_404(tmc_id)
    if request.method == 'POST':
        tmc.buhname = request.form['buhname']
        tmc.sernum = request.form.get('sernum', '')
        tmc.invnum = request.form.get('invnum', '')
        tmc.comment = request.form.get('comment', '')
        groupid = int(request.form['groupid'])
        vendorid = int(request.form['vendorid'])
        nomeid = int(request.form['nomeid'])
        tmc.orgid = int(request.form['orgid'])
        tmc.placesid = int(request.form['placesid'])
        tmc.usersid = int(request.form['usersid'])
        department_id = request.form.get('department_id')
        tmc.department_id = int(department_id) if department_id else None

        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                if tmc.photo:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], tmc.photo)
                    if os.path.exists(old_path):
                        other = Equipment.query.filter(Equipment.photo == tmc.photo, Equipment.id != tmc_id).first()
                        if not other:
                            os.remove(old_path)
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                photo_filename = f"{timestamp}.{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
                tmc.photo = photo_filename

        tmc.nomeid = nomeid
        db.session.commit()
        flash('ТМЦ успешно обновлен!', 'success')
        return redirect(url_for('index'))

    organizations = Org.query.all()
    places = Places.query.all()
    users = Users.query.all()
    groups = GroupNome.query.filter_by(active=True).all()
    departments = Department.query.filter_by(active=True).all()

    current_nome = Nome.query.get(tmc.nomeid)
    current_vendor = Vendor.query.get(current_nome.vendorid) if current_nome else None
    current_group = GroupNome.query.get(current_nome.groupid) if current_nome else None

    vendors = []
    if current_group:
        vendors = db.session.query(Vendor).join(Nome, Vendor.id == Nome.vendorid)\
            .filter(Nome.groupid == current_group.id).distinct().all()
    nomenclatures = []
    if current_group and current_vendor:
        nomenclatures = Nome.query.filter_by(groupid=current_group.id, vendorid=current_vendor.id, active=True).all()

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
    if tmc.photo:
        path = os.path.join(app.config['UPLOAD_FOLDER'], tmc.photo)
        if os.path.exists(path):
            other = Equipment.query.filter(Equipment.photo == tmc.photo, Equipment.id != tmc_id).first()
            if not other:
                os.remove(path)
    db.session.delete(tmc)
    db.session.commit()
    flash('ТМЦ успешно удален!', 'danger')
    return redirect(url_for('index'))

@app.route('/get_vendors_by_group/<int:group_id>')
def get_vendors_by_group(group_id):
    vendors = Vendor.query.filter_by(active=True).order_by(Vendor.name).all()
    return {'vendors': [{'id': v.id, 'name': v.name} for v in vendors]}

@app.route('/get_nomenclatures_by_group_and_vendor/<int:group_id>/<int:vendor_id>')
def get_nomenclatures_by_group_and_vendor(group_id, vendor_id):
    noms = Nome.query.filter_by(groupid=group_id, vendorid=vendor_id, active=True).all()
    return {'nomenclatures': [{'id': n.id, 'name': n.name} for n in noms]}

@app.route('/add_nomenclature', methods=['POST'])
@login_required
def add_nomenclature():
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)