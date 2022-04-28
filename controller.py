from datetime import datetime
import time
from flask import render_template, request, flash, url_for, redirect, session
from flask_login import login_required, logout_user, current_user
from flask_socketio import SocketIO, join_room, leave_room, emit, send, rooms

from app import app, db, socketio, all_room, captcha
from models import User, Message, RoomBan, BanUser, MuteUser, Complaint
from buisness_logic import MessageControl, check_correct_data, checking_possibility_sending_message


class MessageController:
    msg_dict = {}

msg_controller = MessageController()


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


def complaint_on_message(msg: str) -> bool:
    msg_split = msg.split()
    if msg_split[0][1:].lower() != 'vote': return False
    login = current_user.name
    message_id = msg_split[1]
    text = ' '.join(msg_split[2:])
    complaint = Complaint(login=login, message_id=message_id, text=text)
    db.session.add(complaint)
    db.session.commit()
    return True


@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    room = request.args.get('room') or 'general'
    time_now = datetime.fromtimestamp(int(time.time()))
    reason = 'Не указанна!'
    try:
        room_ban_user = RoomBan.query.filter_by(login=current_user.name, room=room).first()
        room_ban_time = td_format(room_ban_user.ban_end_date - time_now)
        reason = room_ban_user.reason
    except:
        room_ban_time = None
    last_msg = reversed(Message.query.filter_by(room=room).order_by(Message.created_on.desc()).limit(100).all())
    user_ban = BanUser.query.filter_by(login=current_user.name).first()
    user_mute = MuteUser.query.filter_by(login=current_user.name).first()
    ban_time, mute_time = None, None
    if user_ban:
        ban_time = td_format(user_ban.ban_time - time_now)
        if not ban_time: ban_time = None
        else: reason = user_ban.reason
    if user_mute:
        mute_time = td_format(user_mute.mute_time - time_now)
        if mute_time:
            if user_mute.mute_time < time_now: mute_time = None
            else: reason = user_mute.reason
        else: mute_time = None
    return render_template('chat.html', room=room, all_msg=last_msg, ban_time=ban_time, room_ban_time=room_ban_time,
                           time_now=time_now, mute_time=mute_time, reason=reason)


@socketio.on('join', namespace='/chat')
@login_required
def join(message):
    room = message.get('room')
    room_ban = RoomBan.query.filter_by(login=current_user.name, room=room).first()
    user_ban = BanUser.query.filter_by(login=current_user.name).first()
    ban_time = datetime.fromtimestamp(int(time.time())-1)
    if user_ban: ban_time = user_ban.ban_time
    if ban_time > datetime.fromtimestamp(int(time.time())) or (
            room_ban and room_ban.ban_end_date > datetime.fromtimestamp(int(time.time()))): return
    join_room(room)
    text_template = f"""Вы успешно присоеденились к комнате: {room.replace('_', ' №')}.\nЖелаем вам удачи!"""
    emit('status_join', {'msg': text_template, 'room': room}, to=room)


@socketio.on('text', namespace='/chat')
@login_required
def text(message):
    room = message.get('room')
    msg = message['msg'].replace('\n', ' ')
    _time = datetime.fromtimestamp(int(time.time()))
    if msg_controller.msg_dict.get(current_user.id):
        if int(msg_controller.msg_dict.get(current_user.id)) + 1 > int(time.time()):
            return
    msg_controller.msg_dict[current_user.id] = int(time.time())
    if not check_correct_data(message): return
    if not checking_possibility_sending_message(room, _time): return
    if complaint_on_message(msg): emit('message', {'msg': 'Ваша жалоба зарегестрированна!', 'user': current_user.name, 'room': message.get('room'), 'special': True}, to=room); return
    new_message = Message(login=current_user.name, text=msg, room=room)
    db.session.add(new_message)
    db.session.commit()
    if MessageControl(msg).execute_admin_commands(new_message.id, room): return

    emit('message', {'id': new_message.id, 'msg': msg, 'user': current_user.name+': ', 'room': message.get('room')}, to=room)

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
