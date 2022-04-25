import time
from datetime import datetime
from typing import Optional
from app import db
from models import User


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
        user.ban_time = dt_object
        db.session.add(user)
        db.session.commit()
        return f'<label style="color: #CD5C5C; font-size: 125%;">Пользователь {login} был заблокирован на {_time}</label>'

    def command_rban(self, login: str, time: str, room: str, *args, **kwargs):
        pass

    def command_mute(self, login: str, _time: str, *args, **kwargs):
        dt_object = self.__convert_time(_time)

        user = User.query.filter_by(name=login).first()
        user.mute_time = dt_object
        db.session.add(user)
        db.session.commit()
        return f'<label style="color: #87CEEB; font-size: 125%;">Пользователь {login} был замучен на {_time}</label>'

    def command_warn(self, login: str, *args, **kwargs):
        user = User.query.filter_by(name=login).first()
        user.warn += 1
        msg = f'<label style="color: #B8860B; font-size: 125%;">Пользователь {login} получил {user.warn} предупреждение! '
        if user.warn > 2:
            self.command_ban(login=login, _time='45m')
            user.warn = 0
            msg += 'И был заблокирован на 45 минут!'
        db.session.add(user)
        db.session.commit()
        return f'{msg}</label>'

    def __convert_time(self, _time):
        if not _time:
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
