from flask import render_template, request, flash, url_for, redirect, session
from flask_login import login_required, logout_user

from app import app
from models import User, Message


@app.route('/')
def index():
    print("!")
    return render_template("index.html")


@app.route('/registration')
def registration():
    return render_template("registration.html")


@app.route('/authorisation')
def authorisation():
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