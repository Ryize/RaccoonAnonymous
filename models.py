from random import randint


from datetime import datetime
from typing import Union, Optional

from flask import Flask
from flask_login import UserMixin, login_user
from flask_sqlalchemy import SQLAlchemy

from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=True)

    @staticmethod
    def login_user(login: str, password: str) -> Union[bool, ValueError]:
        """
        Метод для авторизаии пользователя.
        :param: login(str, логин пользователя, 3 < login < 33)
        :param: password(str, пароль пользователя, 3 < password < 33)
        :return: bool(True - при успешной авторизации, False - при неудаче)
                 или ValueError(Если переданные данные не str, недостаточной или слишком большой длинны).
        """
        # Проверка на кооректность переданных значений
        if not isinstance(login, str) or not isinstance(password, str) or not 3 < len(login) < 33 or not 3 < len(
                password) < 97:
            raise ValueError('Логин или пароль недостаточной длинны. Либо не верный тип данных')
        email = generate_password_hash(login, method='sha512')  # Если такого логина не существует, мы можем ожидать, что передали email
        user = User.query.filter_by(login=login).first() or User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return True
        return False

    @staticmethod
    def register(login: str, password: str, email: Optional[str] = None,
                 auto_login: bool = True) -> Union[ValueError, RuntimeError]:
        """
        Метод для регистрации пользователя.
        :param: login(str, логин пользователя, 3 < login < 33)
        :param: password(str, пароль пользователя, 3 < password < 33)
        :param: email(str, email пользователя, 3 < email < 97)
        :param: auto_login(bool, авторизаия пользователя)
        :return: new_user(При успешной регистрации)
                 или RuntimeError(Если пользователь уже существует)
                 или ValueError(Если переданные данные не str, недостаточной или слишком большой длинны).
        """

        user = User.query.filter_by(login=login).first() or User.query.filter_by(email=email).first()
        if user: raise RuntimeError('Такой пользователь уже существует!')

        # Проверка на кооректность переданных значений
        if not isinstance(login, str) or not isinstance(password, str) or not isinstance(auto_login ,bool) or not 3 < len(login) < 33 or not 3 < len(password) < 97 or (len(email) > 0 and not 3 < len(email) < 97):
            raise ValueError('Логин или пароль недостаточной длинны. Либо не верный тип данных')
        email = email or None

        new_user = User(email=email, login=login,
                        password=generate_password_hash(password, method='sha512'))  # Создание нового пользователя

        db.session.add(new_user)
        db.session.commit()
        if auto_login: login_user(user)  # Авторизовать пользователя
        return new_user

    def login(self):
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
