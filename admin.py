from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin, AdminIndexView, expose
from flask_login import current_user
from flask import redirect, url_for
from app import app
from models import db, User, RoomBan, Message, Complaint, BanUser, MuteUser


class RacoonAnonymousModelView(ModelView):
    def is_accessible(self):
        if not current_user.is_anonymous and current_user.is_authenticated:
            return current_user.admin_status

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('authorisation'))


class UserView(RacoonAnonymousModelView):
    column_exclude_list = ['password', 'email', ]
    column_editable_list = ['warn']
    column_filters = ("id", 'name', 'admin_status',)
    form_excluded_columns = ['password', 'email', 'name']


class RoomBanView(RacoonAnonymousModelView):
    column_filters = ("id", 'login', 'room',)
    column_editable_list = ['reason']


class UserBanView(RacoonAnonymousModelView):
    column_filters = ("id", 'login', 'who_banned', 'reason', 'ban_time',)
    column_editable_list = ['reason']
    form_excluded_columns = ['ban_time', 'who_banned']


class UserMuteView(RacoonAnonymousModelView):
    column_filters = ("id", 'login', 'who_muted', 'reason', 'mute_time',)
    column_editable_list = ['reason']
    form_excluded_columns = ['mute_time', 'who_muted']


class MessageView(RacoonAnonymousModelView):
    column_filters = ("id", 'login', 'text', 'room', 'created_on',)
    can_edit = False


class ComplaintView(RacoonAnonymousModelView):
    column_filters = ("id", 'login', 'message_id', 'text', 'created_on',)
    column_editable_list = ['agreed_status']
    form_excluded_columns = ['login', 'message_id', 'text', 'created_on', ]


class IndexView(AdminIndexView):
    @expose('/')
    def admin_index(self):
        admins = User.query.filter_by(admin_status=True).all()
        return self.render('admin/index.html', admins=admins)

    def is_accessible(self):
        if not current_user.is_anonymous and current_user.is_authenticated:
            return current_user.admin_status


admin = Admin(app, name='Анонимные еноты', template_mode='bootstrap4', index_view=IndexView())
admin.add_view(UserView(User, db.session, name='Пользователи'))
admin.add_view(UserBanView(BanUser, db.session, name='Забаненные'))
admin.add_view(UserMuteView(MuteUser, db.session, name='Заткнутые'))
admin.add_view(RoomBanView(RoomBan, db.session, name='Забаненные в комнатах'))
admin.add_view(MessageView(Message, db.session, name='Сообщения'))
admin.add_view(ComplaintView(Complaint, db.session, name='Жалобы'))
