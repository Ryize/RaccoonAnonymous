import time
from datetime import datetime
from typing import Tuple, Optional
from app import db
from models import *

from flask_login import current_user
from flask_admin import Admin
from flask_socketio import SocketIO, join_room, leave_room, emit, send, rooms

NOT_SPECIFIED: str = 'Не указанна!'
NOT_ID: str = 'id неопределенно'


class MessageControl:
    """
    Класс, отвечающий за работу команд.
    """

    def __init__(self, msg: str):
        self.msg = msg
        self._commands = {
            'ban': self.command_ban,
            'unban': self.command_unban,
            'rban': self.command_rban,
            'mute': self.command_mute,
            'unmute': self.command_unmute,
            'warn': self.command_warn,
            'unwarn': self.command_unwarn,
        }

    def auto_command(self, new_message_id: int, room: str) -> bool:
        """
        Автоматически определяет и вызывает нужную команду. Команды записаны в self._commands.
        :return: str (Текст, после выполнения команды)
        """
        msg_split = self.msg.split()
        if len(msg_split) < 1:
            raise ValueError('Недостаточно аргументов у команды')
        try:
            command = msg_split[0][1:]

            if self.execute_admin_commands(new_message_id, room): return True
            _time, room, reason = '*', None, NOT_SPECIFIED
            login = msg_split[1]
            if len(msg_split) > 2:
                _time = msg_split[2]
                if len(msg_split) > 3 and msg_split[0][1:] == 'rban':
                    room = msg_split[3]
                    reason = ' '.join(msg_split[4:])
                elif len(msg_split) > 3 and msg_split[0][1:] not in ['broadcast', 'bc']:
                    reason = ' '.join(msg_split[3:])
            msg = self._commands[msg_split[0][1:]](command=command, login=login, _time=_time, room=room, reason=reason)
            emit('message', {'id': new_message_id, 'user': '', 'msg': msg, 'room': room, 'system': True},to=room)
            return True
        except IndexError:
            return False

    def command_ban(self, login: str, _time: Optional[str] = None, reason: str = NOT_SPECIFIED, *args,
                    **kwargs) -> str:
        """
        Реализует логику команды блокировки (бана).
        :param login: str (Логин пользователя, которого блокируют)
        :param _time: str (Время блокировки)
        :param reason: str (Причина блокировки)
        :return: str (Информация - кто, кого, за что и на сколько заблокировал)
        """
        dt_object = self.__convert_time(_time)
        user_ban = BanUser.query.filter_by(login=login, who_banned=current_user.id).first()
        if not user_ban:
            user_ban = BanUser(login=login, ban_time=dt_object, reason=reason, who_banned=current_user.id)
        user_ban.ban_time, user_ban.reason = dt_object, reason
        db.session.add(user_ban)
        db.session.commit()
        time_ban = f'на {_time}'
        if _time == '*': time_ban = f'навсегда'
        return f'<p style="color: #CD5C5C; font-size: 125%;">Пользователь {login} был заблокирован {time_ban} Администратором {current_user.name}. <br>Причина: <em>{reason}</em></p>'

    def command_rban(self, login: str, room: str, _time: Optional[str] = None, reason: str = NOT_SPECIFIED, *args,
                     **kwargs) -> str:
        """
        Реализуется логика блокировки пользователя в конкретной комнате.
        :param login: str (Логин пользователя, которого блокируют)
        :param room: str(Название комнаты)
        :param _time: str (Время блокировки)
        :param reason: str (Причина блокировки)
        :return: str (Информация - кто, кого, за что и на сколько заблокировал)
        """
        dt_object = self.__convert_time(_time)
        user = RoomBan.query.filter_by(login=login, room=room).first()
        if not user: user = RoomBan(login=login, room=room, reason=reason, ban_end_date=dt_object)
        user.ban_end_date, user.reason = dt_object, reason
        db.session.add(user)
        db.session.commit()
        time_rban = f'на {_time}'
        if _time == '*': time_rban = f'навсегда'
        return f'<p style="color: #87CEEB; font-size: 125%;">Пользователь {login} был заблокирован в данной комнате {time_rban} Администратором {current_user.name}. <br>Причина: <em>{reason}</em></p>'

    def command_mute(self, login: str, _time: str = None, reason: str = NOT_SPECIFIED, *args, **kwargs) -> str:
        """
        Реализует логику команды затыкания пользователя (мута, читать сообщения можно, писать нельзя).
        :param login: str (Логин пользователя, которого блокируют)
        :param _time: str (Время мута)
        :param reason: str (Причина мута)
        :return: str (Информация - кто, кого, за что и на сколько замутил)
        """
        dt_object = self.__convert_time(_time)

        user_mute = MuteUser.query.filter_by(login=login, who_muted=current_user.id).first()
        if not user_mute:
            user_mute = MuteUser(login=login, mute_time=dt_object, reason=reason, who_muted=current_user.id)
        user_mute.mute_time, user_mute.reason = dt_object, reason
        db.session.add(user_mute)
        db.session.commit()
        time_mute = f'на {_time}'
        if not _time: time_mute = f'навсегда'
        return f'<p style="color: #87CEEB; font-size: 115%;">Пользователь {login} был замучен {time_mute} Администратором {current_user.name}. <br>Причина: <em>{reason}</em></p>'

    def command_warn(self, login: str, *args, **kwargs) -> str:
        """
        Реализует логику команды предупреждения (варна, после трёх предупреждения, пользователь блокируется на 45 минут).
        :param login: str (Логин пользователя)
        :return: str (Информация по предупреждению)
        """
        user = User.query.filter_by(name=login).first()
        user.warn += 1
        msg = f'<label style="color: #B8860B; font-size: 125%;">Администратор {current_user.name} выдал {user.warn} предупреждение пользователю {login} '
        if user.warn > 2:
            self.command_ban(login=login, _time='45m')
            user.warn = 0
            msg += 'И был заблокирован на 45 минут!'
        db.session.add(user)
        db.session.commit()
        return f'{msg}</label>'

    def command_unban(self, login: str, *args, **kwargs) -> Optional[str]:
        """
        Реализует логику команды снятия блокировки (бана).
        :param login: str (Логин пользователя, с которого снимают блокировку)
        :return: str (Информация по разбану)
        """
        user = BanUser.query.filter_by(login=login).first()
        if user:
            user.ban_time = self.__convert_time('1')
        else:
            return
        db.session.add(user)
        db.session.commit()
        msg = f'<label style="color: #B8860B; font-size: 125%;">Администратор {current_user.name} разбанил пользователя {login} '
        return f'{msg}</label>'

    def command_unmute(self, login: str, *args, **kwargs) -> Optional[str]:
        """
        Реализует логику команды снятия затыкания (мута).
        :param login: str (Логин пользователя, с которого снимают мут)
        :return: str (Информация по муту)
        """
        user = MuteUser.query.filter_by(login=login).first()
        if user:
            user.mute_time = self.__convert_time('1')
        else:
            return
        db.session.add(user)
        db.session.commit()
        msg = f'<label style="color: #B8860B; font-size: 125%;">Администратор {current_user.name} размутил пользователя {login} '
        return f'{msg}</label>'

    def command_unwarn(self, login: str, *args, **kwargs) -> Optional[str]:
        """
        Реализует логику команды снятия предупреждения (варна, предупреждения не уходят ниже 0).
        :param login: str (Логин пользователя, с которого снимают варн)
        :return: str (Информация по варну)
        """
        user = User.query.filter_by(name=login).first()
        if user:
            if user.warn > 0:
                user.warn -= 1
        else:
            return
        db.session.add(user)
        db.session.commit()
        msg = f'<label style="color: #B8860B; font-size: 125%;">Администратор {current_user.name} снял одно предупреждение с пользователя {login}. Осталось {user.warn} предупреждений '
        return f'{msg}</label>'

    def execute_admin_commands(self, message_id: int, room: str) -> Optional[bool]:
        """
        Выполняет команду, если пользователь - администратор.
        :return: Optional[bool] (None - пользователь не Администратор, True - команда успешно выполнена,
                                False - что-то пошло не так, команда не выполнена)
        """
        if User.query.filter_by(name=current_user.name).first().admin_status:
            if self._broadcast_command(message_id, room): return True
            if self._clearchat_command(message_id, room): return True
            if self._delmsg_command(message_id, room): return True
            try:
                msg = self._preparation_for_rban_command(room)
                cmd_answer = self._get_cmd_answer(message_id, msg, room)
                emit('message', cmd_answer, to=room)
                return True
            except Exception:
                return False

    def _broadcast_command(self, message_id: int, room: str) -> bool:
        """
        Логика команды broadcast - отправляет сообщение во все комнаты.
        :param message_id: int (id Сообщения)
        :param room: str (Название комнаты)
        :return: bool (True - сообщение успешно отправлено, False - введённая команда не broadcast или bc)
        """
        if self.msg.split()[0][1:].lower() in ['broadcast', 'bc']:
            msg = self.msg.split()
            del msg[0]
            emit('message',
                 {'id': message_id, 'msg': '<strong>' + ' '.join(msg) + '</strong>',
                  'user': 'Предводитель Енотов', 'room': room, 'system': True},
                 broadcast=True)
            return True
        return False

    def _clearchat_command(self, message_id: int, room: str) -> bool:
        """
        Удаляет все сообщения из комнаты.
        :param message_id: int (id Сообщения)
        :param room: str (Название комнаты)
        :return: bool (True - сообщения успешно удалены, False - введённая команда не clearchat или cc)
        """
        if self.msg.split()[0][1:].lower() in ['clearchat', 'cc']:
            msg = self.msg.split()
            if len(msg) == 2:
                room = msg[1]
            Message.query.filter_by(room=room).delete()
            db.session.commit()
            emit('message',
                 {'id': message_id,
                  'msg': f'<strong>Сообщения в этой комнате были очищены Администратором {current_user.name}</strong>',
                  'user': '[<label style="color: #FFA07A">Система</label>]', 'room': room, 'system': True},
                 to=room)
            emit('message',
                 {'id': message_id,
                  'msg': f'[<label style="color: #FFA07A">Система</label>]&nbsp;&nbsp;&nbsp; Чат {room} успешно очищен!',
                  'user': current_user.name, 'room': room, 'special': True},
                 broadcast=True)
            return True
        return False

    def _delmsg_command(self, message_id: int, room: str) -> bool:
        """
        Удаляет сообщение по id.
        :param message_id: int (id Сообщения)
        :param room: str (Название комнаты)
        :return: bool (True - сообщение успешно удалено, False - введённая команда не delmsg/dmsg/dm)
        """
        if self.msg.split()[0][1:].lower() in ['delmsg', 'dmsg', 'dm']:
            msg = self.msg.split()
            removed_message_id = msg[1]
            Message.query.filter_by(id=removed_message_id).delete()
            db.session.commit()
            emit('message',
                 {'id': message_id,
                  'msg': f'[<label style="color: #FFA07A">Система</label>]&nbsp;&nbsp;&nbsp; Сообщение {removed_message_id} успешно удалено!',
                  'user': current_user.name, 'room': room, 'special': True},
                 broadcast=True)
            return True
        return False

    def msg_command(self) -> bool:
        """
        Логика команды msg - отправляет сообщение только определённому человеку.
        :return: bool (True - сообщение успешно отправлено, False - введённая команда не msg или m)
        """
        if self.msg.split()[0][1:].lower() in ['msg', 'm']:
            msg = self.msg.split()
            user_login = msg[1]
            del msg[0], msg[1]
            if user_login not in current_user.connected_users:
                emit('message', {'id': NOT_ID,
                                 'msg': f'[<label style="color: #FFA07A">Система</label>]&nbsp;  Пользователь не в сети!',
                                 'user': current_user.name, 'special': True, })
                return True
            emit('message',
                 {'id': NOT_ID,
                  'msg': f'[<label style="color: #FF8C00">{current_user.name}&nbsp;&nbsp;&nbsp;--->&nbsp;&nbsp;&nbsp;Я</label>]&nbsp;  {" ".join(msg)}',
                  'user': User.query.filter_by(name=user_login).first().name, 'special': True, },
                 broadcast=True)
            emit('message', {'id': NOT_ID,
                             'msg': f'[<label style="color: #FF8C00">Я&nbsp;&nbsp;&nbsp;--->&nbsp;&nbsp;&nbsp;{user_login}</label>]&nbsp;  {" ".join(msg)}',
                             'user': current_user.name, 'special': True, })
            return True
        return False

    def _get_cmd_answer(self, message_id: int, msg: str, room: str) -> dict:
        """
        Реализует стандартный генератор ответа сервера.
        :param message_id: int (id Сообщения)
        :param msg: str (Текст сообщения)
        :param room: str (Название комнаты)
        :return: dict (Словарь со всем содержимым ответа(Например для: socketio.emit))
        """
        data = MessageControl(msg.replace('\n', '')).auto_command()
        dict_template = {'id': message_id,
                         'msg': msg,
                         'user': current_user.name,
                         'room': room,
                         'system': True}
        if msg.split()[0][1:].lower() in ('ban', 'rban', 'mute',):
            dict_template['msg'], dict_template['user'], dict_template['ban'] = data, '', msg.split()[1]
        else:
            dict_template['msg'], dict_template['user'] = data, ''
        return dict_template

    def _preparation_for_rban_command(self, room) -> str:
        """
        Приводит сообщение, к формату который поддерживает команда rban. Заменяет номер текущей комнаты (через this),
        на название комнаты.
        :param room: str (Название комнаты)
        :return: str (Новый текст сообщения)
        """
        msg = self.msg
        if len(msg.split()) > 3 and msg.split()[0][1:].lower() == 'rban':
            msg = msg.split()
            if msg[3].lower() == 'this': msg[3] = room
            msg = ' '.join(msg)
        return msg

    def __convert_time(self, _time: str) -> datetime:
        """
        Метод, для конвертации времени указанного в сообщении.
        Просто число (Пример: 27) - секунды;
        Добавляется m (Пример: 13m) - минуты (13 * 60);
        Добавляется h (Пример: 18h) - часы (19 * 60 * 60);
        Добавляется d (Пример: 34d) - дни (34 * 60 * 60 * 24);
        Добавляется y (Пример: 2y) - года (2 * 60 * 60 * 24 * 365);
        (Пустое значение или * - преобразуется в 700 лет)
        :param _time: str (Текст с временем)
        :return: datetime
        """
        if not _time or _time == '*':
            _time = 60 * 60 * 24 * 365 * 700 + time.time()
        elif _time.find('m') != -1 or _time.find('M') != -1:
            _time = int(_time[:-1]) * 60 + time.time()
        elif _time.find('h') != -1 or _time.find('H') != -1:
            _time = int(_time[:-1]) * 60 * 60 + time.time()
        elif _time.find('d') != -1 or _time.find('D') != -1:
            _time = int(_time[:-1]) * 60 * 60 * 24 + time.time()
        elif _time.find('y') != -1 or _time.find('Y') != -1:
            _time = int(_time[:-1]) * 60 * 60 * 24 * 365 + time.time()
        else:
            _time = int(_time) + time.time()
        dt_object = datetime.fromtimestamp(int(_time))
        return dt_object


def check_correct_data(message: dict) -> Optional[bool]:
    """
    Проверка корректности введённых данных. Не менее 1 и не более 1000 символов.
    :param message: dict (Список, который нам предоставляет socketio)
    :return: Optional[bool] (None - неверные данные, True - всё хорошо)
    """
    msg = message['msg']
    if len(msg.replace(' ', '').replace('\n', '')) > 0 and len(msg) < 1000:
        return True
    else:
        emit('status_error',
             {'id': message_id, 'msg': 'Неверные данные!', 'user': current_user.name, 'room': message.get('room')},
             to=room)


def checking_possibility_sending_message(room: str, _time: datetime) -> bool:
    """
    Проверка, не заблокирован/замучен/заблокирован в данной комнате пользователь.
    :param room: str (Название комнаты)
    :param _time: datetime (Текущее время)
    :return: bool (True - пользователь может отправлять сообщения, False - проверка/проверки не пройдены)
    """
    room_ban = RoomBan.query.filter_by(login=current_user.name, room=room).first()
    user_ban = BanUser.query.filter_by(login=current_user.name).first()
    user_mute = MuteUser.query.filter_by(login=current_user.name).first()
    if (user_ban and user_ban.ban_time > _time) or (room_ban and room_ban.ban_end_date > _time) or (
            user_mute and user_mute.mute_time > _time):
        return False
    return True


def get_ban_data(user_ban: BanUser, time_now: datetime, reason: str) -> Tuple[Optional[str], str]:
    """
    Получить время и причину блокировки.
    :param user_ban: BanUser (Забаненный пользователь)
    :param time_now: datetime (Текущее время)
    :param reason: str (Причина)
    :return: Tuple[Optional[str], str]
    """
    ban_time = None
    if user_ban:
        ban_time = td_format(user_ban.ban_time - time_now)
        if ban_time:
            reason = user_ban.reason
    return ban_time, reason


def get_mute_data(user_mute: MuteUser, time_now: datetime, reason: str) -> Tuple[Optional[str], str]:
    """
    Получить время и причину мута.
    :param user_mute: MuteUser (заткнутый пользователь)
    :param time_now: datetime (Текущее время)
    :param reason: str (Причина)
    :return: Tuple[Optional[str], str]
    """
    mute_time = None
    if user_mute:
        mute_time = td_format(user_mute.mute_time - time_now)
        if mute_time:
            if user_mute.mute_time < time_now:
                mute_time = None
            else:
                reason = user_mute.reason
        else:
            mute_time = None
    return mute_time, reason


def td_format(td_object) -> str:
    """
    Привести от объекта datetime, к формату понятному человеку (Например: 5 лет 4 месяца 13 часов).
    :param td_object: datetime (Объект который преобразовывается)
    :return: str (Преобразованная дата)
    """
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
    """
    Команда жалобы на сообщение.
    :param msg: str (Сообщение на которое пожаловались)
    :return: bool (True - жалоба записана в БД)
    """
    msg_split = msg.split()
    if msg_split[0][1:].lower() != 'vote': return False
    login = current_user.name
    message_id = msg_split[1]
    text = ' '.join(msg_split[2:])
    complaint = Complaint(login=login, message_id=message_id, text=text)
    db.session.add(complaint)
    db.session.commit()
    return True
