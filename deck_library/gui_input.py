"""Shared keyboard and gamepad navigation, including modal tasks."""
from gi.repository import Gtk,Gdk,GLib

class InputMixin:
    def start_gamepad(self):
        import os,sys
        if not ('--gaming' in sys.argv or os.environ.get('SteamAppId') or os.environ.get('SteamGameId')):return
        try:
            from .gamepad import Driver
            self.gamepad_driver=Driver(self)
            self.controller_mode=True
            if hasattr(self,'controller_hint'):self.controller_hint.show()
            GLib.idle_add(self.focus_library)
        except OSError as error:self.set_status('Mando: '+str(error))

    def bind_library_focus(self,widget,entry,card=None):
        widget.library_entry_id=entry.id
        widget.get_accessible().set_name(entry.name)
        self.library_targets[entry.id]=widget
        visual=card if card is not None else widget;widget.library_focus_visual=visual
        def entered(*_):
            self.library_focus_id=entry.id;visual.get_style_context().add_class('game-focused')
            self.reveal_focus(widget);return False
        def left(*_):visual.get_style_context().remove_class('game-focused');return False
        widget.connect('focus-in-event',entered);widget.connect('focus-out-event',left)

    def library_focus_changed(self,window,focus):
        identifier=getattr(focus,'library_entry_id',None)
        if identifier:self.library_focus_id=identifier
        for target in getattr(self,'library_targets',{}).values():
            style=target.library_focus_visual.get_style_context()
            style.add_class('game-focused') if target is focus else style.remove_class('game-focused')

    def focus_library(self,identifier=None):
        if self.ui_closed or self.pages.get_visible_child_name()!='library':return False
        targets=getattr(self,'library_targets',{})
        target=targets.get(identifier or getattr(self,'library_focus_id',None)) or next(iter(targets.values()),None)
        if target:target.grab_focus();self.library_focus_changed(self,target);self.reveal_focus(target)
        return False

    def move_library_focus(self,action):
        from .navigation import neighbour
        if action not in ('up','down','left','right') or self.pages.get_visible_child_name()!='library':return False
        focus=self.get_focus();current=getattr(focus,'library_entry_id',None)
        if not current:
            if focus is None:self.focus_library();return True
            return False
        rectangles={}
        for identifier,widget in getattr(self,'library_targets',{}).items():
            point=widget.translate_coordinates(self.library_stack,0,0)
            if point and widget.get_mapped():rectangles[identifier]=(*point,widget.get_allocated_width(),widget.get_allocated_height())
        target=neighbour(rectangles,current,action)
        if target:self.focus_library(target)
        elif action=='up':self.platform_picker.grab_focus()
        elif action=='down' and self.selection_mode:self.select_button.grab_focus()
        return True

    def reveal_focus(self,focus):
        scroll=focus.get_ancestor(Gtk.ScrolledWindow)
        if not scroll:return
        point=focus.translate_coordinates(scroll.get_child(),0,0)
        if not point:return
        for axis,size,adjustment in ((0,focus.get_allocated_width(),scroll.get_hadjustment()),(1,focus.get_allocated_height(),scroll.get_vadjustment())):
            start=point[axis];value=adjustment.get_value();page=adjustment.get_page_size();padding=10
            if start-padding<value:value=start-padding
            elif start+size+padding>value+page:value=start+size+padding-page
            adjustment.set_value(max(adjustment.get_lower(),min(value,adjustment.get_upper()-page)))

    def scroll_controller(self,action,window):
        focus=window.get_focus();scroll=focus.get_ancestor(Gtk.ScrolledWindow) if focus else None
        if not scroll:
            def find(widget):
                if not widget.get_mapped():return []
                values=[widget] if isinstance(widget,Gtk.ScrolledWindow) else []
                if isinstance(widget,Gtk.Container):
                    for child in widget.get_children():values.extend(find(child))
                return values
            candidates=find(window)
            if candidates:scroll=max(candidates,key=lambda w:w.get_allocated_width()*w.get_allocated_height())
        while scroll:
            vertical=action in ('scroll_up','scroll_down');adjustment=scroll.get_vadjustment() if vertical else scroll.get_hadjustment()
            lower=adjustment.get_lower();upper=max(lower,adjustment.get_upper()-adjustment.get_page_size())
            if upper>lower:
                sign=-1 if action in ('scroll_up','scroll_left') else 1
                adjustment.set_value(max(lower,min(upper,adjustment.get_value()+sign*min(96,max(32,adjustment.get_page_size()*.16)))))
                return True
            scroll=scroll.get_ancestor(Gtk.ScrolledWindow)
        return True

    def controller_action(self,action,window=None):
        import time
        now=time.monotonic();previous=getattr(self,'last_controller_action',('',0))
        if previous[0]==action and now-previous[1]<.09:return True
        self.last_controller_action=(action,now)
        self.controller_mode=True
        if hasattr(self,'controller_hint'):self.controller_hint.show()
        window=window or self
        handler=getattr(window,'account_controller',None)
        if handler and handler(action):return True
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
        if action.startswith('scroll_'):return self.scroll_controller(action,window)
        if action=='search' and window is self:
            entry=self.catalog_search if self.pages.get_visible_child_name()=='catalog' and hasattr(self,'catalog_search') else self.search
            entry.grab_focus();return True
        if window is self and self.move_library_focus(action):return True
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
            if focus:self.reveal_focus(focus)
            return True
        return False
