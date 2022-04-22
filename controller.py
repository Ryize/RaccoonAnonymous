from flask import render_template, request, flash, url_for, redirect, session
from flask_login import login_required, logout_user

from app import app
from models import User, Message


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/registration', methods=['POST', 'GET'])
def registration():
    if request.method == 'POST':
        rec = request.form
        if not 3 < len(rec.get('name')) < 33 or not 3 < len(rec.get('password')) < 33:
            flash('Ваш логин должен быть не менее 3-х символов и не более 33', 'error')
        else:
            flash('Вы успешно зарегистрировались!', 'success')
            User.register(rec.get('name'), rec.get('password'), rec.get('email'))
            return render_template('user_page.html')
    return render_template("registration.html")


@app.route('/authorisation', methods=['POST', 'GET'])
def authorisation():
    if request.method == 'POST':
        rec = request.form
        print(rec.get('name'), rec.get('password'))
        if not 3 < len(rec.get('name')) < 33 or not 3 < len(rec.get('password')) < 33:
            flash('Ваш логин должен быть не менее 3-х символов и не более 33', 'error')
        if not User.login_user(rec.get('name'), rec.get('password')):
            flash('Неверный логин или пароль.', 'error')
        else:
            return render_template('user_page.html')
    return render_template("authorisation.html")


@app.route('/user_page')
def user_page():
    return render_template("user_page.html")


@app.route('/contacts')
def contacts():
    return render_template("contacts.html")


@app.route('/chat')
def chat():
    return render_template("chat.html")


@app.route('/dialog_list')
def dialog_list():
    return render_template("dialog_list.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('authorisation'))


@app.after_request
def redirect_to_sign(response):
    """
    Если пользователь не авторизован и пытается зайти на страницу для авторизованных(@login_required),
    то функция перенаправит на страницу авторизации
    """
    if response.status_code == 401:
        return redirect(url_for('authorisation'))

    return response