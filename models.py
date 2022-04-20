from datetime import datetime
from typing import Union

from flask import Flask
from flask_login import UserMixin, login_user
from flask_sqlalchemy import SQLAlchemy

from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(96), nullable=False)
    email = db.Column(db.String(96), unique=True, nullable=True)

    @staticmethod
    def login(login: str, password: str) -> Union[bool, ValueError]:
        """
        Метод для авторизаии пользователя.
        :param: login(str, логин пользователя, 3 < login < 33)
        :param: password(str, пароль пользователя, 3 < password < 33)
        :return: bool(True - при успешной авторизации, False - при неудаче)
                 или ValueError(Если переданные данные не str, недостаточной или слишком большой длинны).
        """
        # Проверка на кооректность переданных значений
        if not isinstance(login, str) or not isinstance(password, str) or not 3 < len(login) < 33 or not 3 < len(password) < 97:
            raise ValueError('Логин или пароль недостаточной длинны. Либо не верный тип данных')
        email = generate_password_hash(login)  # Если такого логина не существует, мы можем ожидать, что передали email
        user = User.query.filter_by(login=login).first() or User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return True
        return False

    def signup(self):
        pass

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(32), unique=True, nullable=False)
    text = db.Column(db.String(2500), nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)


db.create_all()  # Создаёт таблицы, если ещё не созданы


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)