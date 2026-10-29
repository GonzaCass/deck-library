"""Administrator recognition after an account change."""
import threading
from gi.repository import GLib
from .gui_support import SupportMixin

class RequestsMixin(SupportMixin):
    def owner_verified(self):
        try:token=self.community_client().session().get('token')
        except ValueError:return False
        return bool(token and token==getattr(self,'owner_session',None) and self.preferences.get('owner_mode'))

    def check_owner_mode(self):
        """Refresh administrator actions only for the account that completed this check."""
        from .installations import save_settings
        try:client=self.community_client();session=client.session().get('token')
        except ValueError:self.owner_session=None;return
        def apply(admin):
            if self.ui_closed or self.community_client().session().get('token')!=session:return False
            previous=(self.preferences.get('owner_mode'),getattr(self,'owner_session',None))
            if self.preferences.get('owner_mode')!=admin:
                self.preferences['owner_mode']=admin;save_settings(self.preferences,self.store)
            self.owner_session=session if admin else None
            if previous!=(admin,self.owner_session) and not self.inline_workflows:
                page=self.pages.get_visible_child_name()
                if page=='tools':self.tools_page()
                elif page=='home':self.home_page()
            return False
        if not self.signed_in():apply(False);return
        def work():
            try:admin=bool(client.me().get('admin'))
            except Exception:return
            GLib.idle_add(apply,admin)
        threading.Thread(target=work,daemon=True).start()
