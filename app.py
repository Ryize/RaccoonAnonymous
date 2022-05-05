import uuid
from flask import Flask
from flask import Flask, flash, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_toastr import Toastr
from flask_socketio import SocketIO
from flask_moment import Moment
from flask_sessionstore import Session
from flask_session_captcha import FlaskSessionCaptcha
from flask_migrate import Migrate

app = Flask(__name__)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
toastr = Toastr(app)  # Для современного отображения flash сообщений
moment = Moment(app)
migrate_bd = Migrate(app, db)

UPLOAD_FOLDER = 'static/uploads/avatar/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app.config['SECRET_KEY']: str = str(uuid.uuid4())
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Макс размер 16мбайт
app.config['SQLALCHEMY_DATABASE_URI']: str = 'sqlite:///bd.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']: bool = True
app.config['CAPTCHA_ENABLE'] = True
app.config['CAPTCHA_LENGTH'] = 1
app.config['CAPTCHA_WIDTH'] = 160
app.config['CAPTCHA_HEIGHT'] = 60
app.config['CAPTCHA_SESSION_KEY'] = 'captcha_image'
app.config['SESSION_TYPE'] = 'sqlalchemy'

socketio = SocketIO(app, manage_session=False)
Session(app)
captcha = FlaskSessionCaptcha(app)

# Все комнаты
all_room = {
    'IT': 2,
    'Спорт': 2,
    'Наука': 2,
    'Иностранные языки': 2,
    'Работа с фото/монтаж': 2,
    'Игры': 3,
    'Творчество': 2,
    'Книги': 2,
    'Кулинария': 2,
    'Вождение': 2,
    'Ремонт техники': 1,
    'Хобби': 2,
}

if __name__ == '__main__':
    from models import *
    from admin import admin
    from controller import app

    socketio.run(app, debug=True, port=5000)
