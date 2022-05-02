from datetime import datetime
import time
from flask import render_template, request, flash, url_for, redirect, session
from flask_login import login_required, logout_user, current_user
from flask_socketio import SocketIO, join_room, leave_room, emit, send, rooms

from app import app, db, socketio, all_room, captcha
from models import User, Message, RoomBan, BanUser, MuteUser, Complaint
from buisness_logic import *


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
def rooms():
    return render_template("all_room.html", all_room=all_room)


@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    room = request.args.get('room') or 'general'
    if room != 'general':
        room_text, room_number = room.split('_')
        for title, number in all_room.items():
            if room_text == title:
                if int(room_number) < 1 or int(room_number) > number:
                    flash('Такой комнаты не существует!', 'error')
                    return redirect(url_for('rooms'))
                break
        else:
            flash('Такой комнаты не существует!', 'error')
            return redirect(url_for('rooms'))
    time_now = datetime.fromtimestamp(int(time.time()))
    reason = 'Не указанна!'
    room_ban_time = None
    room_ban_user = RoomBan.query.filter_by(login=current_user.name, room=room).first()
    if room_ban_user:
        room_ban_time = td_format(room_ban_user.ban_end_date - time_now)
        reason = room_ban_user.reason
    last_msg = reversed(Message.query.filter_by(room=room).order_by(Message.created_on.desc()).limit(100).all())

    user_ban = BanUser.query.filter_by(login=current_user.name).first()
    user_mute = MuteUser.query.filter_by(login=current_user.name).first()

    ban_time, reason = get_ban_data(user_ban, time_now, reason)
    mute_time, reason = get_mute_data(user_mute, time_now, reason)
    return render_template('chat.html', room=room, all_msg=last_msg, ban_time=ban_time, room_ban_time=room_ban_time,
                           time_now=time_now, mute_time=mute_time, reason=reason)


@socketio.on('join', namespace='/chat')
@login_required
def join(message):
    room = message.get('room')
    room_ban = RoomBan.query.filter_by(login=current_user.name, room=room).first()
    user_ban = BanUser.query.filter_by(login=current_user.name).first()
    ban_time = datetime.fromtimestamp(int(time.time()) - 1)
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
    if not check_message_can_processed(message, room, _time): return
    msg_controller.msg_dict[current_user.id] = int(time.time())
    if complaint_on_message(msg): emit('message', {'msg': 'Ваша жалоба зарегестрированна!', 'user': current_user.name,
                                                   'room': message.get('room'), 'special': True}, to=room); return
    new_message = save_message(current_user.name, msg, room)
    if MessageControl(msg).execute_admin_commands(new_message.id, room): return

    emit('message', {'id': new_message.id, 'msg': msg, 'user': current_user.name + ': ', 'room': message.get('room')},
         to=room)


def check_message_can_processed(message: dict, room: str, _time: datetime) -> bool:
    """
    Выполняет проверки: Все ли данные введены корректно (Сообщение не может быть из одних пробелов/табов и тд),
    не заблокирован/замучен пользователь, прошла ли хотя бы секунда с прошлого сообщения (Чтобы не было спама).
    :param message: dict (Словарь сообщения, его передаёт socketio)
    :param room: str (Название комнаты)
    :param _time: datetime (Объект времени с библиотеки datetime)
    :return: bool (True - можно обработать сообщение, False - сообщения нельзя обрабатывать,
                    одна или несколько проверок не пройдены)
    """
    if not check_time_send_msg() or not check_correct_data(message) or not checking_possibility_sending_message(room,
                                                                                                                _time):
        return False
    return True


def check_time_send_msg() -> bool:
    """
    Проверяет сколько времени прошло с прошлого сообщения. Должно быть не менее 1 секунды.
    :return: bool (True - прошло более (или ровно) 1 секунды, False - меньше 1 секунды)
    """
    if msg_controller.msg_dict.get(current_user.id):
        if int(msg_controller.msg_dict.get(current_user.id)) + 1 > int(time.time()):
            return False
    return True


def save_message(login: str, text: str, room: str) -> Message:
    """
    Сохраняет в БД новое сообщение.
    :param login: str (Логин пользователя, написавшего сообщение)
    :param text: str (Текст сообщения)
    :param room: str (Название комнаты)
    :return: Message (Объект класса Message, он уже закомичен в БД)
    """
    new_message = Message(login=login, text=text, room=room)
    db.session.add(new_message)
    db.session.commit()
    return new_message


@app.route('/dialog_list')
def dialog_list():
    return render_template("dialog_list.html")


@app.route('/rules')
def rules():
    return render_template("rules.html")


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
