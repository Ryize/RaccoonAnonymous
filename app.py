from flask import Flask
from flask import Flask, flash, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config['SECRET_KEY']: str = 'bgcegy3yg2d3ue2uwccuby2ubwcchjsbgvcwcuwbc2whbu11'
app.config['SQLALCHEMY_DATABASE_URI']: str = 'sqlite:///bd.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']: bool = True


if __name__ == '__main__':
    from models import *
    from controller import app
    app.run(debug=True, host='0.0.0.0', port=5001)

