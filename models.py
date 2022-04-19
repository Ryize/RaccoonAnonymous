from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(96), nullable=False)
    email = db.Column(db.String(96), unique=True, nullable=True)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(32), unique=True, nullable=False)
    text = db.Column(db.String(2500), nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)