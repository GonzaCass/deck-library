"""Shared keyboard and gamepad navigation, including modal tasks."""
from gi.repository import Gtk,Gdk

class InputMixin:
    def start_gamepad(self):
        import os,sys
        if not ('--gaming' in sys.argv or os.environ.get('SteamAppId')):return
        try:
            from .gamepad import Driver
            self.gamepad_driver=Driver(self)
        except OSError as error:self.set_status('Mando: '+str(error))

    def controller_action(self,action,window=None):
        import time
        now=time.monotonic();previous=getattr(self,'last_controller_action',('',0))
        if previous[0]==action and now-previous[1]<.09:return True
        self.last_controller_action=(action,now)
        window=window or self
        grab=Gtk.grab_get_current()
        if isinstance(grab,Gtk.MenuShell):
            if action=='back':grab.cancel();return True
            items=[c for c in grab.get_children() if c.get_sensitive() and c.get_visible()]
            current=grab.get_selected_item()
            if action=='activate' and current:grab.activate_item(current,True);return True
            if action in ('up','down') and items:
                index=items.index(current) if current in items else -1;grab.select_item(items[(index+(1 if action=='down' else -1))%len(items)]);return True
        if action in ('previous_tab','next_tab') and window is self:
            names=list(self.nav_buttons);active={'library':0,'detail':0,'catalog':1,'updates':2,'settings':3}.get(self.pages.get_visible_child_name(),0);self.nav_buttons[names[(active+(-1 if action=='previous_tab' else 1))%len(names)]].clicked();return True
        if action=='back':
            if isinstance(window,Gtk.Dialog):window.response(Gtk.ResponseType.CANCEL)
            elif window is self:
                if self.pages.get_visible_child_name()=='detail':self.back_from_game()
                elif self.pages.get_visible_child_name()!='library':self.open_library()
            return True
        if action=='search' and window is self:
            entry=self.catalog_search if self.pages.get_visible_child_name()=='catalog' and hasattr(self,'catalog_search') else self.search
            entry.grab_focus();return True
        focus=window.get_focus()
        if action=='activate':
            if isinstance(focus,Gtk.ComboBox):focus.popup()
            elif isinstance(focus,Gtk.Switch):focus.set_active(not focus.get_active())
            elif isinstance(focus,Gtk.Button):focus.clicked()
            elif isinstance(focus,Gtk.ListBoxRow):focus.activate()
            elif not window.activate_focus():window.activate_default()
            return True
        directions={'up':Gtk.DirectionType.UP,'down':Gtk.DirectionType.DOWN,'left':Gtk.DirectionType.LEFT,'right':Gtk.DirectionType.RIGHT}
        if action in directions:
            if not window.child_focus(directions[action]):window.child_focus(Gtk.DirectionType.TAB_BACKWARD if action in ('up','left') else Gtk.DirectionType.TAB_FORWARD)
            focus=window.get_focus()
            if focus:
                scroll=focus.get_ancestor(Gtk.ScrolledWindow)
                if scroll:
                    position=focus.translate_coordinates(scroll.get_child(),0,0)
                    if position:
                        adj=scroll.get_vadjustment();y=position[1];height=focus.get_allocated_height();value=adj.get_value()
                        if y<value:adj.set_value(max(adj.get_lower(),y))
                        elif y+height>value+adj.get_page_size():adj.set_value(min(adj.get_upper()-adj.get_page_size(),y+height-adj.get_page_size()))
            return True
        return False
