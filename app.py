from flask import Flask, flash, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config['SECRET_KEY']: str = 'bgcegy3yg2d3ue2uwccuby2ubwcchjsbgvcwcuwbc2whbu11'
app.config['SQLALCHEMY_DATABASE_URI']: str = 'sqlite:///bd.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']: bool = True

db = SQLAlchemy(app)

@app.route('/')
def index():
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


if __name__ == '__main__':
    from models import *
    app.run(debug=True, host='0.0.0.0', port=5001)

