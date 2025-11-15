# migrate_group_photos.py
import os
import shutil
from app import app, db
from models import Nome

UPLOAD_FOLDER = 'static/uploads'
GROUP_LABEL_SUBDIR = 'group_label'
FULL_PATH = os.path.join(UPLOAD_FOLDER, GROUP_LABEL_SUBDIR)

# Создаём папку, если её нет
os.makedirs(FULL_PATH, exist_ok=True)

def migrate_photos():
    with app.app_context():
        # Выбираем все записи из nome, где photo не пустой и НЕ начинается с 'group_label/'
        nomes = Nome.query.filter(
            Nome.photo != '',
            ~Nome.photo.startswith(GROUP_LABEL_SUBDIR + '/')
        ).all()

        updated = 0
        for nome in nomes:
            old_path = os.path.join(UPLOAD_FOLDER, nome.photo)
            if os.path.exists(old_path):
                # Формируем новый путь
                new_filename = f"group_label/{os.path.basename(nome.photo)}"
                new_full_path = os.path.join(UPLOAD_FOLDER, new_filename)

                # Перемещаем файл
                shutil.move(old_path, new_full_path)

                # Обновляем путь в БД
                nome.photo = new_filename
                updated += 1
                print(f"✅ Перемещено: {old_path} → {new_full_path}")
            else:
                print(f"⚠️  Файл не найден: {old_path}")

        db.session.commit()
        print(f"\n✅ Обновлено {updated} записей в таблице `nome`.")

if __name__ == '__main__':
    migrate_photos()
