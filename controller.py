from flask import render_template, request, flash, url_for, redirect, session
from app import app
from models import User, Message


@app.route('/')
def index():
    print("!")
    return render_template("index.html")


@app.route('/registration')
def registration():
    print("!")
    User.login('2ss', '2sssss')
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
