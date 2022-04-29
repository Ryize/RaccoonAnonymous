import time
from datetime import datetime
from typing import Tuple, Optional
from app import db
from models import *

from flask_login import current_user
from flask_admin import Admin
from flask_socketio import SocketIO, join_room, leave_room, emit, send, rooms


class MessageControl:
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

    def auto_command(self):
        msg_split = self.msg.split()
        if len(msg_split) < 2:
            raise ValueError('Недостаточно аргументов у команды')
        command = msg_split[0][1:]
        login = msg_split[1]
        _time, room, reason = '*', None, 'Не указанна!'
        if len(msg_split) > 2:
            _time = msg_split[2]
            if len(msg_split) > 3 and msg_split[0][1:] == 'rban':
                room = msg_split[3]
                reason = ' '.join(msg_split[4:])
            elif len(msg_split) > 3 and msg_split[0][1:] not in ['broadcast', 'bc']:
                reason = ' '.join(msg_split[3:])
        return self._commands[msg_split[0][1:]](command=command, login=login, _time=_time, room=room, reason=reason)

    def command_ban(self, login: str, _time: Optional[str] = None, reason: str = 'Не указанна!', *args, **kwargs):
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

    def command_rban(self, login: str, room: str, _time: Optional[str] = None, reason: str = 'Не указанна!', *args,
                     **kwargs):
        dt_object = self.__convert_time(_time)
        user = RoomBan.query.filter_by(login=login, room=room).first()
        if not user: user = RoomBan(login=login, room=room, reason=reason, ban_end_date=dt_object)
        user.ban_end_date, user.reason = dt_object, reason
        db.session.add(user)
        db.session.commit()
        time_rban = f'на {_time}'
        if _time == '*': time_rban = f'навсегда'
        return f'<p style="color: #87CEEB; font-size: 125%;">Пользователь {login} был заблокирован в данной комнате {time_rban} Администратором {current_user.name}. <br>Причина: <em>{reason}</em></p>'

    def command_mute(self, login: str, _time: str = None, reason: str = 'Не указанна!', *args, **kwargs):
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

    def command_warn(self, login: str, *args, **kwargs):
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

    def command_unban(self, login: str, *args, **kwargs):
        user = BanUser.query.filter_by(login=login).first()
        if user:
            user.ban_time = self.__convert_time('1')
        else:
            return
        db.session.add(user)
        db.session.commit()
        msg = f'<label style="color: #B8860B; font-size: 125%;">Администратор {current_user.name} разбанил пользователя {login} '
        return f'{msg}</label>'

    def command_unmute(self, login: str, *args, **kwargs):
        user = MuteUser.query.filter_by(login=login).first()
        if user:
            user.mute_time = self.__convert_time('1')
        else:
            return
        db.session.add(user)
        db.session.commit()
        msg = f'<label style="color: #B8860B; font-size: 125%;">Администратор {current_user.name} размутил пользователя {login} '
        return f'{msg}</label>'

    def command_unwarn(self, login: str, *args, **kwargs):
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

    def execute_admin_commands(self, message_id: int, room: str):
        if User.query.filter_by(name=current_user.name).first().admin_status:
            if self._broadcast_command(message_id, room): return True
            try:
                msg = self._preparation_for_rban_command(room)
                cmd_answer = self._get_cmd_answer(message_id, msg, room)
                emit('message', cmd_answer, to=room)
                return True
            except:
                return False

    def _broadcast_command(self, message_id: int, room: str) -> bool:
        if self.msg.split()[0][1:].lower() in ['broadcast', 'bc']:
            msg = self.msg.split()
            del msg[0]
            emit('message',
                 {'id': message_id, 'msg': '<strong>' + ' '.join(msg) + '</strong>',
                  'user': 'Предводитель Енотов', 'room': room, 'system': True},
                 broadcast=True)
            return True
        return False

    def _get_cmd_answer(self, message_id: int, msg: str, room: str):
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
        msg = self.msg
        if len(msg.split()) > 3 and msg.split()[0][1:].lower() == 'rban':
            msg = msg.split()
            if msg[3].lower() == 'this': msg[3] = room
            msg = ' '.join(msg)
        return msg

    def __convert_time(self, _time):
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
    msg = message['msg']
    if len(msg.replace(' ', '').replace('\n', '')) > 0 and len(msg) < 1000:
        return True
    else:
        emit('status_error',
             {'id': message_id, 'msg': 'Неверные данные!', 'user': current_user.name, 'room': message.get('room')},
             to=room)


def checking_possibility_sending_message(room: str, _time: datetime) -> bool:
    room_ban = RoomBan.query.filter_by(login=current_user.name, room=room).first() or None
    user_ban = BanUser.query.filter_by(login=current_user.name).first() or None
    user_mute = MuteUser.query.filter_by(login=current_user.name).first() or None
    if user_ban:
        if user_ban.ban_time > _time: return False
    if room_ban:
        if room_ban.ban_end_date > _time: return False
    if user_mute:
        if user_mute.mute_time > _time: return False
    return True


def get_ban_data(user_ban: BanUser, time_now: datetime, reason: str) -> Tuple[Optional[str], str]:
    ban_time = None
    if user_ban:
        ban_time = td_format(user_ban.ban_time - time_now)
        if ban_time:
            reason = user_ban.reason
    return ban_time, reason


def get_mute_data(user_mute: MuteUser, time_now: datetime, reason: str) -> Tuple[Optional[str], str]:
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
