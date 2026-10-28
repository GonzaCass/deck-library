"""Administrator recognition after an account change."""
import threading
from gi.repository import GLib
from .gui_support import SupportMixin

class RequestsMixin(SupportMixin):
    def check_owner_mode(self):
        """Ask the service once whether this account is an administrator; only then does the received-requests page appear in Settings."""
        from .installations import save_settings
        def apply(admin):
            if self.ui_closed:return False
            if self.preferences.get('owner_mode')!=admin:
                self.preferences['owner_mode']=admin;save_settings(self.preferences,self.store)
                if self.pages.get_visible_child_name()=='tools':self.tools_page()
            return False
        if not self.signed_in():
            apply(False)
            return
        def work():
            try:admin=bool(self.community_client().me().get('admin'))
            except Exception:return
            GLib.idle_add(apply,admin)
        threading.Thread(target=work,daemon=True).start()
