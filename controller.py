from flask import render_template, request, flash, url_for, redirect, session
from flask_login import login_required, logout_user, current_user
from flask_socketio import SocketIO, join_room, leave_room, emit, send, rooms

from app import app, db, socketio, all_room, captcha
from models import User, Message
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

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    room = request.args.get('room') or 'general'
    last_msg = reversed(Message.query.filter_by(room=room).order_by(Message.created_on.desc()).limit(100).all())  # Получить 100 сообщений
    return render_template('chat.html', room=room, all_msg = last_msg)

@socketio.on('join', namespace='/chat')
def join(message):
    room = message.get('room')
    join_room(room)
    text_template = f"""Вы успешно присоеденились к комнате: {room.replace('_', ' №')}.\nЖелаем вам удачи!"""
    emit('status_join', {'msg':  text_template, 'room': room}, to=room)


@socketio.on('text', namespace='/chat')
def text(message):
    room = message.get('room')
    msg = message['msg']
    if User.query.filter_by(name=current_user.name).first().admin_status:
        data = MessageControl(msg.replace('\n', '')).auto_command()
        emit('message', {'msg': data, 'user': 'Система', 'room': message.get('room')}, to=room)
        return
    if len(message['msg'].replace(' ', '').replace('\n', '')) > 0 and len(msg) < 1000:
        new_message = Message(login=current_user.name, text=msg, room=room)
        db.session.add(new_message)
        db.session.commit()
        emit('message', {'msg': msg, 'user': current_user.name, 'room': message.get('room')}, to=room)
    else:
        emit('status_error', {'msg': 'Неверные данные!', 'user': current_user.name, 'room': message.get('room')}, to=room)


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
