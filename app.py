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


app = Flask(__name__)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
toastr = Toastr(app)
moment = Moment(app)

app.config['SECRET_KEY']: str = str(uuid.uuid4())
app.config['SQLALCHEMY_DATABASE_URI']: str = 'sqlite:///bd.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']: bool = True
app.config['CAPTCHA_ENABLE'] = True
app.config['CAPTCHA_LENGTH'] = 5
app.config['CAPTCHA_WIDTH'] = 160
app.config['CAPTCHA_HEIGHT'] = 60
app.config['CAPTCHA_SESSION_KEY'] = 'captcha_image'
app.config['SESSION_TYPE'] = 'sqlalchemy'

socketio = SocketIO(app, manage_session=False)
Session(app)
captcha = FlaskSessionCaptcha(app)

# Все комнаты
all_room = {
    'Спорт': 3,
    'IT': 5,
    'Наука': 3,
    'Долгая разработка': 10,
}

if __name__ == '__main__':
    from models import *
    from admin import admin
    from controller import app
    socketio.run(app, debug=True, port=5011)
