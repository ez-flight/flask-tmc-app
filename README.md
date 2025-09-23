Вот готовый файл `README.md` для вашего проекта — оформлен в Markdown, содержит описание функционала, инструкции по развертыванию, настройке и использованию. Готов к загрузке в GitHub одним файлом.

---

### ✅ Скопируйте и сохраните как `README.md`

```markdown
# 🖥️ Система учета ТМЦ (Товарно-Материальных Ценностей)

**Flask-приложение для учета, добавления, редактирования и удаления ТМЦ с поддержкой фото, привязки к отделам, группам и производителям.**

---

## 📌 Основные возможности

- ✅ Добавление, редактирование, удаление ТМЦ.
- 📸 Загрузка фотографий (хранение в `/var/www/html/photos`, отображение через Nginx).
- 🏢 Привязка ТМЦ к **отделам** (Отдел связи, ОТО, ПС и др.).
- 🧩 Динамический выбор: **Группа → Производитель → Наименование**.
- ➕ Возможность создания нового наименования прямо из формы.
- 🔍 Фильтрация списка ТМЦ по отделам на главной странице.
- 🧑‍💼 Привязка к организации, месту нахождения, ответственному пользователю.
- 🔄 История перемещений (в будущем — через таблицу `move`).

---

## 🚀 Требования

- Python 3.8+
- MySQL 8.0+
- Nginx (для раздачи фото)
- Linux-сервер (рекомендуется Ubuntu 20.04+)

---

## 🛠️ Установка и настройка

### 1. Клонирование проекта

```bash
git clone https://github.com/ваш-логин/flask-tmc-app.git
cd flask-tmc-app
```

> 💡 Если репозиторий ещё не создан — инициализируйте локально:
> ```bash
> git init
> git remote add origin https://github.com/ваш-логин/flask-tmc-app.git
> ```

---

### 2. Создание виртуального окружения и установка зависимостей

```bash
python3 -m venv venv
source venv/bin/activate
pip install Flask Flask-SQLAlchemy PyMySQL python-dotenv cryptography
```

---

### 3. Настройка базы данных MySQL

#### ✅ Создайте базу и таблицы (если ещё не сделано)

```sql
CREATE DATABASE webuseorg3 CHARACTER SET utf8mb3 COLLATE utf8mb3_bin;

USE webuseorg3;

-- Таблица отделов
CREATE TABLE `department` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `code` VARCHAR(50) NOT NULL COMMENT 'Короткий код (например, ОС, ОТО)',
  `active` TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_bin;

-- Добавляем столбец department_id в equipment
ALTER TABLE `equipment`
ADD COLUMN `department_id` INT NULL DEFAULT NULL AFTER `tmcgo`,
ADD INDEX `fk_equipment_department_idx` (`department_id` ASC);

ALTER TABLE `equipment`
ADD CONSTRAINT `fk_equipment_department`
  FOREIGN KEY (`department_id`)
  REFERENCES `department` (`id`)
  ON DELETE SET NULL
  ON UPDATE CASCADE;

-- Заполняем отделы
INSERT INTO `department` (`name`, `code`, `active`) VALUES
('Отдел связи', 'ОС', 1),
('Отдел технического обеспечения', 'ОТО', 1),
('Противопожарная служба', 'ПС', 1);

-- Привязываем существующие ТМЦ
UPDATE `equipment` SET `department_id` = 1 WHERE `id` BETWEEN 400 AND 439;
UPDATE `equipment` SET `department_id` = 2 WHERE `id` BETWEEN 440 AND 445;
```

---

### 4. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
SECRET_KEY=your_secret_key_here
DATABASE_URL=mysql+pymysql://root:your_password@localhost/webuseorg3
```

> ⚠️ Замените `your_password` на реальный пароль MySQL (если он есть).

---

### 5. Настройка папки для фотографий

```bash
sudo mkdir -p /var/www/html/photos
sudo chown -R $USER:$USER /var/www/html/photos
sudo chmod -R 755 /var/www/html/photos
```

---

### 6. Настройка Nginx для раздачи фото

Создайте конфиг Nginx:

```bash
sudo nano /etc/nginx/sites-available/flask-tmc
```

Вставьте:

```nginx
server {
    listen 80;
    server_name ваш_IP_или_домен;  # Например, 192.168.100.106

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /photos/ {
        alias /var/www/html/photos/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /static/ {
        alias /home/flask_tmc_app/static/;
    }
}
```

Активируйте и перезапустите Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/flask-tmc /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

### 7. Запуск приложения

```bash
cd /home/flask_tmc_app
source venv/bin/activate
python3 app.py
```

> ✅ Приложение будет доступно по адресу: `http://192.168.100.106`

---

## 🖼️ Загрузка фотографий

Фотографии загружаются через форму добавления/редактирования ТМЦ.  
Файлы сохраняются в `/var/www/html/photos/` и доступны по URL: `http://192.168.100.106/photos/имя_файла.jpg`.

---

## 👥 Управление отделами

Отделы управляются через базу данных. Чтобы добавить новый отдел — выполните SQL:

```sql
INSERT INTO `department` (`name`, `code`, `active`) VALUES ('Новый отдел', 'НО', 1);
```

После этого он появится в выпадающем списке в формах и фильтрах.

---

## 🧩 Структура проекта

```
flask-tmc-app/
├── app.py                  # Главный файл приложения
├── models.py               # Модели базы данных
├── .env                    # Переменные окружения
├── requirements.txt        # Зависимости (опционально)
├── static/
│   └── uploads/            # Символическая ссылка на /var/www/html/photos/
├── templates/
│   ├── base.html
│   ├── index.html          # Главная страница со списком ТМЦ
│   ├── add_tmc.html        # Форма добавления ТМЦ
│   └── edit_tmc.html       # Форма редактирования ТМЦ
└── README.md               # Этот файл
```

---

## 📎 Полезные команды

| Действие | Команда |
|----------|---------|
| Активировать окружение | `source venv/bin/activate` |
| Запустить приложение | `python3 app.py` |
| Проверить статус MySQL | `sudo systemctl status mysql` |
| Перезапустить Nginx | `sudo systemctl restart nginx` |
| Просмотреть логи Flask | В терминале, где запущен `app.py` |

---

## 🛡️ Безопасность

- ❗ Не используйте встроенный сервер Flask в продакшене.
- ✅ Для продакшена используйте `gunicorn` + `nginx`.
- 🔐 Храните `.env` вне репозитория (добавьте в `.gitignore`).
- 🔒 Настройте пароли для пользователей MySQL.

---

## 📄 Лицензия

MIT License — используйте и модифицируйте свободно.

---

> 🧑‍💻 Разработано для кафедры 51.  
> 📞 Контакты: ваш_email@example.com  
> 🌐 Версия: 1.0
```

---

## ✅ Готово!

Сохраните этот текст как `README.md` в корне вашего проекта — и загрузите в GitHub. Теперь любой, кто клонирует ваш репозиторий, сможет быстро развернуть и запустить систему учета ТМЦ.

Удачи с проектом! 🚀
