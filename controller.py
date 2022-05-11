from datetime import datetime
import time, os
from flask import render_template, request, flash, url_for, redirect, session
from flask_login import login_required, logout_user, current_user
from flask_socketio import SocketIO, join_room, leave_room, emit, send, rooms

from werkzeug.utils import secure_filename

from app import app, db, socketio, all_room, captcha, ALLOWED_EXTENSIONS
from models import *
from buisness_logic import *


class MessageController:
    msg_dict = {}


msg_controller = MessageController()
connected_users = set()
ERROR_DATA_FORMAT: str = 'Ваш логин должен быть не менее 3-х символов и не более 33'


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/registration', methods=['POST', 'GET'])
@app.route('/register', methods=['POST', 'GET'])
def registration():
    if request.method == 'GET':
        return render_template("registration.html")
    rec = request.form
    if not 3 < len(rec.get('name')) < 33 or not 3 < len(rec.get('password')) < 33:
        flash(ERROR_DATA_FORMAT, 'error')
        return redirect((url_for('registration')))
    if captcha.validate():
        try:
            User.register(rec.get('name'), rec.get('password'), rec.get('email'))
        except RuntimeError:
            flash('Пользователь с такими данными уже зарегестрирован!', 'error')
            return redirect(url_for('registration'))
        except ValueError:
            flash(ERROR_DATA_FORMAT, 'error')
            return redirect(url_for('registration'))
        flash('Вы успешно зарегистрировались!', 'success')
        return redirect(url_for('user_page'))
    else:
        flash('Вы неверно ввели капчу!', 'error')


@app.route('/authorisation', methods=['POST', 'GET'])
@app.route('/login', methods=['POST', 'GET'])
def authorisation():
    if request.method == 'POST':
        rec = request.form
        if captcha.validate():
            if not 3 < len(rec.get('name')) < 33 or not 3 < len(rec.get('password')) < 33:
                flash(ERROR_DATA_FORMAT, 'error')
            try:
                if not User.login_user(rec.get('name'), rec.get('password')):
                    flash('Неверный логин или пароль.', 'error')
                else:
                    return redirect(url_for('user_page'))
            except ValueError:
                flash(ERROR_DATA_FORMAT, 'error')
                return redirect(url_for('authorisation'))
        else:
            flash('Вы неверно ввели капчу!', 'error')
    return render_template("authorisation.html")


@app.route('/user_page', methods=['GET', 'POST'])
@app.route('/profile', methods=['POST', 'GET'])
@login_required
def user_page():
    if request.method == 'POST':
        avatar_file = request.files.get('avatar')
        if avatar_file and allowed_file(avatar_file.filename):
            filename = secure_filename(avatar_file.filename)
            avatar_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user = User.query.get(current_user.id)
            user.avatar = filename
            db.session.add(user)
            db.session.commit()
            flash('Аватарка успешно изменена!', 'success')
            return redirect(url_for('user_page'))

        user_description = request.form.get('description')
        if not user_description:
            flash('Неверные данные!')
            return redirect(url_for('user_page'))
        user = User.query.get(current_user.id)
        user.description = user_description
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('user_page'))
    avatar = '/' + os.path.join(app.config['UPLOAD_FOLDER'], current_user.avatar)
    user = User.query.get(current_user.id)
    return render_template("user_page.html", avatar=avatar, user=user)


@app.route('/profile/<int:id>')
def profile(id):
    user = User.query.get(id)
    if not user:
        flash('Пользователь не найден!', 'error')
        return redirect(url_for('user_page'))
    avatar = '/' + os.path.join(app.config['UPLOAD_FOLDER'], current_user.avatar)
    return render_template("user_page.html", avatar=avatar, user=user)


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
    if not checking_room_exists(room): return redirect(url_for('rooms'))

    private, login = False, False
    pm = PrivateMessage.query.filter_by(room=room).first()
    if pm and (pm.login1 == current_user.name or pm.login2 == current_user.name):
        login = pm.login1
        if pm.login1 == current_user.name: login = pm.login2
        private = True

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
    if private:
        return render_template('ls.html', room=room, all_msg=last_msg, ban_time=ban_time, room_ban_time=room_ban_time,
                               time_now=time_now, mute_time=mute_time, reason=reason, User=User, private=private,
                               login=login)

    return render_template('chat.html', room=room, all_msg=last_msg, ban_time=ban_time, room_ban_time=room_ban_time,
                           time_now=time_now, mute_time=mute_time, reason=reason, User=User)


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
    text_template = f"""Вы успешно присоединились к комнате: {room.replace('_', ' №')}.\nЖелаем вам удачи!"""
    emit('status_join', {'msg': text_template, 'room': room}, to=room)
    connected_users.add(current_user.name)


@socketio.on('text', namespace='/chat')
@login_required
def text(message):
    room = message.get('room')
    msg = message['msg'].replace('\n', ' ')
    current_user.connected_users = connected_users
    _time = datetime.fromtimestamp(int(time.time()))
    if not check_message_can_processed(message, room, _time): return
    if MessageControl(msg).msg_command(): return
    msg_controller.msg_dict[current_user.id] = int(time.time())
    if complaint_on_message(msg): emit('message', {
        'msg': '[<label style="color: #FFA07A">Система</label>]&nbsp;&nbsp;&nbsp;Ваша жалоба зарегистрированна!',
        'user': current_user.name,
        'room': message.get('room'), 'special': True}, to=room); return
    new_message = save_message(current_user.name, msg, room)
    if MessageControl(msg).auto_command(new_message.id, room): return

    user_name, system = get_msg_data()
    emit('message',
         {'id': new_message.id, 'msg': msg, 'user': user_name + ': ', 'room': message.get('room'), 'system': system, },
         to=room)


@socketio.on('disconnect', namespace='/chat')
@login_required
def on_disconnect():
    connected_users.remove(current_user.name)


@app.route('/dialog_list')
def dialog_list():
    pm = PrivateMessage.query.filter_by(login1=current_user.name).all()
    if not pm:
        pm = PrivateMessage.query.filter_by(login2=current_user.name).all()
    return render_template("dialog_list.html", pm=pm)


@app.route('/rules')
def rules():
    return render_template("rules.html")


@app.route("/create_ls_room/<login>")
@login_required
def create_ls_room(login):
    room_name = f'{current_user.name}-{login}'
    pm = PrivateMessage.query.filter_by(room=room_name).first()
    if pm: return redirect(url_for('chat', room=pm.room))
    pm = PrivateMessage(login1=current_user.name, login2=login, room=room_name)
    db.session.add(pm)
    db.session.commit()
    return redirect(url_for('rooms'))


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


def check_time_send_msg() -> bool:
    """
    Проверяет сколько времени прошло с прошлого сообщения. Должно быть не менее 1 секунды.
    :return: bool (True - прошло более (или ровно) 1 секунды, False - меньше 1 секунды)
    """
    if msg_controller.msg_dict.get(current_user.id):
        if int(msg_controller.msg_dict.get(current_user.id)) + 1 > int(time.time()):
            return False
    return True


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


def get_msg_data() -> tuple:
    """
    Получить данные (Префикс, статус ответа сервера)
    :return: tuple (1 - префикс + имя пользователя, статус сервера)
    """
    user_name, system = current_user.name, False
    if current_user.admin_status:
        user_name = f'<small>[<label style="color: #CD5C5C">Админ</label>]</small> {current_user.name}'
        system = True
    return user_name, system


def checking_room_exists(room: str) -> bool:
    """
    Проверка существования комнаты.
    :param room: str (Название проверяемой комнаты)
    :return: bool (True - такая комната существует, False - такой комнаты не существует)
    """
    UNDEFINED_ROOM: str = 'Такой комнаты не существует!'
    if room == 'general':
        return True
    pm = PrivateMessage.query.filter_by(room=room).first()
    if pm and (pm.login1 == current_user.name or pm.login2 == current_user.name):
        return True
    if Message.query.filter_by(room=room).first(): return True
    try:
        room_text, room_number = room.split('_')
    except ValueError:
        flash(UNDEFINED_ROOM, 'error')
        return False
    for title, number in all_room.items():
        if room_text == title:
            if int(room_number) < 1 or int(room_number) > number:
                flash(UNDEFINED_ROOM, 'error')
                return False
            break
    else:
        flash(UNDEFINED_ROOM, 'error')
        return False
    return True


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
