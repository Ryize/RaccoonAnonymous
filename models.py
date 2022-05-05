from random import randint


from datetime import datetime
from typing import Union, Optional

from flask import Flask
from flask_login import UserMixin, login_user, current_user
from flask_sqlalchemy import SQLAlchemy

from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


NOT_SPECIFIED = 'Не указанна!'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True, default='Здесь рассказ о себе (но мне лень его менять)!')
    warn = db.Column(db.Integer, default=0)
    admin_status = db.Column(db.Boolean, default=False)
    banned = db.relationship('BanUser', backref='user')
    muted = db.relationship('MuteUser', backref='user')
    email = db.Column(db.Text, unique=True, nullable=True)
    avatar = db.Column(db.Text, nullable=True, default='racoon_standart.jpg')

    @staticmethod
    def login_user(name: str, password: str) -> Union[bool, ValueError]:
        """
        Метод для авторизации пользователя.
        :param: login(str, логин пользователя, 3 < login < 33)
        :param: password(str, пароль пользователя, 3 < password < 33)
        :return: bool(True - при успешной авторизации, False - при неудаче)
                 или ValueError(Если переданные данные не str, недостаточной или слишком большой длинны).
        """
        # Проверка на корректность переданных значений
        if not isinstance(name, str) or not isinstance(password, str) or not 3 < len(name) < 33 or not 3 < len(
                password) < 97:
            raise ValueError('Логин или пароль недостаточной длинны. Либо не верный тип данных')
        email = generate_password_hash(name, method='sha512')  # Если такого логина не существует, мы можем ожидать, что передали email
        user = User.query.filter_by(name=name).first() or User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return True
        return False

    @staticmethod
    def register(name: str, password: str, email: Optional[str] = None,
                 auto_login: bool = True) -> Union[ValueError, RuntimeError]:
        """
        Метод для регистрации пользователя.
        :param: login(str, логин пользователя, 3 < login < 33)
        :param: password(str, пароль пользователя, 3 < password < 33)
        :param: email(str, email пользователя, 3 < email < 97)
        :param: auto_login(bool, авторизация пользователя)
        :return: new_user(При успешной регистрации)
                 или RuntimeError(Если пользователь уже существует)
                 или ValueError(Если переданные данные не str, недостаточной или слишком большой длинны).
        """

        user = User.query.filter_by(name=name).first() or User.query.filter_by(email=email).first()
        if user: raise RuntimeError('Такой пользователь уже существует!')

        # Проверка на корректность переданных значений
        if not isinstance(name, str) or not isinstance(password, str) or not isinstance(auto_login ,bool) or not 3 < len(name) < 33 or not 3 < len(password) < 97 or (len(email) > 0 and not 3 < len(email) < 97):
            raise ValueError('Логин или пароль недостаточной длинны. Либо не верный тип данных')
        email = email or None

        new_user = User(email=email, name=name,
                        password=generate_password_hash(password, method='sha512'))  # Создание нового пользователя

        db.session.add(new_user)
        db.session.commit()
        if auto_login: login_user(new_user)  # Авторизовать пользователя
        return new_user

    def __repr__(self):
        status = 'Пользователь'
        if self.admin_status: status = 'Администратор'
        return f'{self.name} ({status})'



class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(32), nullable=False)
    text = db.Column(db.String(2500), nullable=False)
    room = db.Column(db.String(32), nullable=False)
    complaint = db.relationship('Complaint', backref='message')
    created_on = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'{self.login}: {self.text}'


class BanUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(32), nullable=False)
    who_banned = db.Column(db.Integer, db.ForeignKey('user.id'))
    ban_time = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.String(64), default=NOT_SPECIFIED)

    def __repr__(self):
        return f'{self.login}({self.ban_time}): {self.reason}'


class MuteUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(32), nullable=False)
    who_muted = db.Column(db.Integer, db.ForeignKey('user.id'))
    mute_time = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.String(64), default=NOT_SPECIFIED)

    def __repr__(self):
        return f'{self.login}({self.mute_time}): {self.reason}'


class RoomBan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(32), nullable=False)
    room = db.Column(db.String(32), nullable=False)
    reason = db.Column(db.String(64), default=NOT_SPECIFIED)
    ban_end_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'{self.login}({self.room}): {self.reason}'


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(32), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    text = db.Column(db.String(256), default=NOT_SPECIFIED)
    agreed_status = db.Column(db.Boolean, default=False)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)


db.create_all()  # Создаёт таблицы, если ещё не созданы


def save_message(login: str, text: str, room: str) -> Message:
    """
    Сохраняет в БД новое сообщение.
    :param login: str (Логин пользователя, написавшего сообщение)
    :param text: str (Текст сообщения)
    :param room: str (Название комнаты)
    :return: Message (Объект класса Message, он уже закомичен в БД)
    """
    new_message = Message(login=login, text=text, room=room)
    db.session.add(new_message)
    db.session.commit()
    return new_message


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
