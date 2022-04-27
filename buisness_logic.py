import time
from datetime import datetime
from typing import Optional
from app import db
from models import User, RoomBan

from flask_login import current_user
from flask_socketio import SocketIO, join_room, leave_room, emit, send, rooms


class MessageControl:
    def __init__(self, msg: str):
        self.msg = msg
        self._commands = {
            'ban': self.command_ban,
            'rban': self.command_rban,
            'mute': self.command_mute,
            'warn': self.command_warn,
        }

    def auto_command(self):
        msg_split = self.msg.split()
        if len(msg_split) < 2:
            raise ValueError('Недостаточно аргументов у команды')
        command = msg_split[0][1:]
        login = msg_split[1]
        _time, room = None, None
        if len(msg_split) > 2:
            _time = msg_split[2]
            if len(msg_split) == 4:
                room = msg_split[3]
        return self._commands[msg_split[0][1:]](command=command, login=login, _time=_time, room=room)

    def command_ban(self, login: str, _time: Optional[str] = None, *args, **kwargs):
        dt_object = self.__convert_time(_time)
        user = User.query.filter_by(name=login).first()
        if not user:
            raise RuntimeError('Пользователь не найден!')
        user.ban_time = dt_object
        db.session.add(user)
        db.session.commit()
        time_ban = f'на {_time}'
        if not _time: time_ban = f'навсегда'
        return f'<label style="color: #CD5C5C; font-size: 125%;">Пользователь {login} был заблокирован {time_ban} Администратором {current_user.name}</label>'

    def command_rban(self, login: str, room: str, _time: Optional[str] = None, *args, **kwargs):
        dt_object = self.__convert_time(_time)
        user = RoomBan.query.filter_by(login=login, room=room).first()
        if not user: user = RoomBan(login=login, room=room, ban_end_date=dt_object)
        user.ban_end_date = dt_object
        db.session.add(user)
        db.session.commit()
        time_rban = f'на {_time}'
        if _time == '*': time_rban = f'навсегда'
        return f'<label style="color: #87CEEB; font-size: 125%;">Пользователь {login} был заблокирован в данной комнате {time_rban} Администратором {current_user.name}</label>'

    def command_mute(self, login: str, _time: str = None, *args, **kwargs):
        dt_object = self.__convert_time(_time)

        user = User.query.filter_by(name=login).first()
        user.mute_time = dt_object
        db.session.add(user)
        db.session.commit()
        time_mute = f'на {_time}'
        if not _time: time_mute = f'навсегда'
        return f'<label style="color: #87CEEB; font-size: 125%;">Пользователь {login} был замучен {time_mute} Администратором {current_user.name}</label>'

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

    def execute_admin_commands(self, message_id: int, room: str):
        if User.query.filter_by(name=current_user.name).first().admin_status:
            if self._broadcast_command(message_id, room): return True
            try:
                msg = self._preparation_for_rban_command()
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
                  'user': 'Предводитель Енотов', 'room': room},
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
            dict_template['msg'], dict_template['user'], dict_template['ban'] = data, 'Система', msg.split()[1]
        else:
            dict_template['msg'], dict_template['user'] = data, 'Система'
        return dict_template

    def _preparation_for_rban_command(self) -> str:
        msg = self.msg
        if len(msg.split()) == 4:
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
    room_ban = RoomBan.query.filter_by(login=current_user.name, room=room).first()
    if current_user.ban_time > _time or (room_ban and room_ban.ban_end_date > _time) or current_user.mute_time > _time:
        return False
    return True
