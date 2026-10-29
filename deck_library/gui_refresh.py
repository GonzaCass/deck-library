"""Background refreshes that do not replace forms or reset unchanged views."""
import time
from gi.repository import GLib


class RefreshMixin:
    def start_live_refresh(self):
        self.live_catalog_checked=time.monotonic()
        self.ui_sources.append(GLib.timeout_add_seconds(45,self.live_refresh))

    def live_refresh(self):
        if self.ui_closed:return False
        if not self.preferences.get('onboarding_complete'):return True
        editing=bool(getattr(self,'inline_workflows',[]) or getattr(self,'editor_dirty',False) or getattr(self,'port_busy',False) or getattr(self,'profile_job',False))
        if not editing:
            self.discover(quiet=True)
            if self.pages.get_visible_child_name()=='detail' and self.selected:self.fetch_game_ratings(self.selected)
            if getattr(self,'catalog_ready',False) and time.monotonic()-self.live_catalog_checked>=900:
                self.live_catalog_checked=time.monotonic();self.load_catalog(False)
        if self.preferences.get('check_updates',True):self.check_updates()
        return True

    def watch_page(self,page,callback,interval=20,ready=None):
        """Only refresh the visible page, stopping its timer when it is closed."""
        def tick():
            if self.ui_closed or page._closed:return False
            if page.get_mapped() and (ready is None or ready()):callback()
            return True
        identifier=GLib.timeout_add_seconds(interval,tick);self.ui_sources.append(identifier)
        def stop(*_):
            if GLib.MainContext.default().find_source_by_id(identifier):GLib.source_remove(identifier)
            if identifier in self.ui_sources:self.ui_sources.remove(identifier)
        page.connect('destroy',stop)
        return identifier
