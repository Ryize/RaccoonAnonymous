from datetime import datetime
import time
from flask import render_template, request, flash, url_for, redirect, session
from flask_login import login_required, logout_user, current_user
from flask_socketio import SocketIO, join_room, leave_room, emit, send, rooms

from app import app, db, socketio, all_room, captcha
from models import User, Message, RoomBan
from buisness_logic import MessageControl


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
            if captcha.validate():
                flash('Вы успешно зарегистрировались!', 'success')
                User.register(rec.get('name'), rec.get('password'), rec.get('email'))
                return render_template('user_page.html')
            else:
                flash('Вы неверно ввели капчу!', 'error')
    return render_template("registration.html")


@app.route('/authorisation', methods=['POST', 'GET'])
def authorisation():
    if request.method == 'POST':
        rec = request.form
        if captcha.validate():
            if not 3 < len(rec.get('name')) < 33 or not 3 < len(rec.get('password')) < 33:
                flash('Ваш логин должен быть не менее 3-х символов и не более 33', 'error')
            if not User.login_user(rec.get('name'), rec.get('password')):
                flash('Неверный логин или пароль.', 'error')
            else:
                return render_template('user_page.html')
        else:
            flash('Вы неверно ввели капчу!', 'error')
    return render_template("authorisation.html")


@app.route('/user_page')
def user_page():
    return render_template("user_page.html")


@app.route('/contacts')
def contacts():
    return render_template("contacts.html")


@app.route('/rooms')
def roomss():
    return render_template("all_room.html", all_room=all_room)


def td_format(td_object):
    seconds = int(td_object.total_seconds())
    periods = [
        ('лет', 60 * 60 * 24 * 365),
        ('месяца(ев)', 60 * 60 * 24 * 30),
        ('день(дня-дней)', 60 * 60 * 24),
        ('час(а-ов)', 60 * 60),
        ('минут(а)', 60),
        ('секунд', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            strings.append("%s %s" % (period_value, period_name))

    return ", ".join(strings)


@app.route('/chat', methods=['GET', 'POST'])
def chat():
    room = request.args.get('room') or 'general'
    time_now = datetime.fromtimestamp(int(time.time()))
    try:
        room_ban_time = td_format(
            RoomBan.query.filter_by(login=current_user.name, room=room).first().ban_end_date - time_now)
    except: room_ban_time = None
    last_msg = reversed(Message.query.filter_by(room=room).order_by(Message.created_on.desc()).limit(
        100).all())  # Получить 100 сообщений
    ban_time, mute_time = td_format(current_user.ban_time - time_now), td_format(current_user.mute_time - time_now)
    return render_template('chat.html', room=room, all_msg=last_msg, ban_time=ban_time, room_ban_time=room_ban_time, time_now=time_now, mute_time=mute_time)


@socketio.on('join', namespace='/chat')
@login_required
def join(message):
    room = message.get('room')
    room_ban = RoomBan.query.filter_by(login=current_user.name, room=room).first()
    if current_user.ban_time > datetime.fromtimestamp(int(time.time())) or (
            room_ban and room_ban.ban_end_date > datetime.fromtimestamp(int(time.time()))): return
    join_room(room)
    text_template = f"""Вы успешно присоеденились к комнате: {room.replace('_', ' №')}.\nЖелаем вам удачи!"""
    emit('status_join', {'msg': text_template, 'room': room}, to=room)


@socketio.on('text', namespace='/chat')
@login_required
def text(message):
    room = message.get('room')
    msg = message['msg']
    new_message = Message(login=current_user.name, text=msg, room=room)
    db.session.add(new_message)
    db.session.commit()

    _time =  datetime.fromtimestamp(int(time.time()))

    room_ban = RoomBan.query.filter_by(login=current_user.name, room=room).first()
    if current_user.ban_time > _time or (room_ban and room_ban.ban_end_date > _time) or current_user.mute_time > _time: return
    if User.query.filter_by(name=current_user.name).first().admin_status:
        if len(msg.split()) == 4:
            msg = msg.split()
            if msg[3].lower() == 'this': msg[3] = room
            msg = ' '.join(msg)
        try:
            data = MessageControl(msg.replace('\n', '')).auto_command()
            emit('message', {'msg': msg, 'user': current_user.name, 'room': message.get('room')}, to=room)
            if msg.split()[0][1:].lower() in ('ban', 'rban', 'mute', ):
                emit('message', {'msg': data, 'user': 'Система', 'room': message.get('room'), 'ban': msg.split()[1]},
                     to=room)
            else:
                emit('message', {'msg': data, 'user': 'Система', 'room': message.get('room')}, to=room)
            return
        except:
            pass
    if len(message['msg'].replace(' ', '').replace('\n', '')) > 0 and len(msg) < 1000:
        emit('message', {'msg': msg, 'user': current_user.name, 'room': message.get('room')}, to=room)
    else:
        emit('status_error', {'msg': 'Неверные данные!', 'user': current_user.name, 'room': message.get('room')},
             to=room)


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
    то функция перенаправит на страницу авторизации.
    """
    if response.status_code == 401:
        return redirect(url_for('authorisation'))

    return response
