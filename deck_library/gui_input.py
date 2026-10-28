"""Shared keyboard and gamepad navigation, including embedded tasks."""
from gi.repository import Gtk,Gdk,GLib

class InputMixin:
    def navigation_focus(self,window):
        focus=window.get_focus()
        return (focus.get_ancestor(Gtk.ComboBox) or focus) if focus else None

    def disable_tooltips(self):
        """With a controller there is no hover: a tooltip would stay over whatever page opens under the idle pointer."""
        try:
            Gtk.Settings.get_default().set_property('gtk-enable-tooltips',False)
            display=Gdk.Display.get_default()
            if display:Gtk.Tooltip.trigger_tooltip_query(display)
        except (TypeError,AttributeError):pass
    def start_gamepad(self):
        import os,sys
        if not ('--gaming' in sys.argv or os.environ.get('SteamAppId') or os.environ.get('SteamGameId')):return
        try:
            from .gamepad import Driver
            self.gamepad_driver=Driver(self)
            self.controller_mode=True;self.disable_tooltips()
            if hasattr(self,'controller_hint'):self.controller_hint.show()
            def initial_focus():
                if self.pages.get_visible_child_name()=='library':return self.focus_library()
                return self.ensure_controller_focus(self)
            GLib.idle_add(initial_focus)
        except OSError as error:self.set_status('Mando: '+str(error))

    def bind_search_keyboard(self,entry):
        from .interactions import manual_text_input
        manual_text_input(entry);entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY,'input-keyboard-symbolic');entry.set_icon_activatable(Gtk.EntryIconPosition.PRIMARY,True);entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY,'Abrir teclado · X / □');entry.connect('icon-press',lambda widget,position,event:self.open_keyboard(widget) if position==Gtk.EntryIconPosition.PRIMARY else None)

    def open_keyboard(self,entry=None):
        import subprocess,shutil,time
        from .runtime import clean_environment
        target=entry or self.get_focus()
        if isinstance(target,Gtk.Entry):target.grab_focus()
        if time.monotonic()-getattr(self,'last_keyboard_request',0)<.6:return
        self.last_keyboard_request=time.monotonic()
        if not shutil.which('steam'):self.toast('Steam no está disponible para abrir el teclado.');return
        try:subprocess.Popen(['steam','steam://open/keyboard?XPosition=0&YPosition=0&Width=0&Height=0&Mode=0'],env=clean_environment(),start_new_session=True)
        except OSError:self.toast('No se pudo abrir el teclado de Steam.')

    def mark_controller_focus(self,window,focus):
        if focus is not None:focus=focus.get_ancestor(Gtk.ComboBox) or focus
        previous=getattr(window,'_deck_focus_widget',None)
        # SDL polls at 40 Hz. Re-scanning the widget tree for an unchanged
        # focus can keep the timeout permanently ready and starve catalog
        # completion callbacks (which run at GLib's idle priority).
        if previous is focus and getattr(window,'_deck_focus_initialized',False):return
        window._deck_focus_initialized=True
        if previous is not None and previous is not focus:previous.get_style_context().remove_class('controller-focus')
        window._deck_focus_widget=focus
        if focus is not None:
            focus.get_style_context().add_class('controller-focus')
            if isinstance(focus,Gtk.ListBoxRow):
                parent=focus.get_parent()
                if isinstance(parent,Gtk.ListBox) and parent.get_selection_mode()!=Gtk.SelectionMode.NONE and parent.get_selected_row() is not focus:parent.select_row(focus)
        if isinstance(focus,Gtk.Entry) and not focus.get_input_hints()&Gtk.InputHints.INHIBIT_OSK:focus.set_input_hints(focus.get_input_hints()|Gtk.InputHints.INHIBIT_OSK)
        self.update_controller_hints(window)

    def update_controller_hints(self,window):
        hint=getattr(window,'_deck_controller_hints',None) if window is not self else getattr(self,'controller_hint',None)
        if hint is None:return
        focus=self.navigation_focus(window);activate='Seleccionar';back='Volver'
        if window is self and getattr(self,'inline_workflows',[]):back='Volver'
        elif window is not self:back='Cerrar'
        elif self.pages.get_visible_child_name()=='detail':back={'home':'Inicio','validated':'Verificados'}.get(getattr(self,'detail_origin','library'),'Biblioteca') if self.game_tab=='profiles' else 'Volver al juego'
        elif self.pages.get_visible_child_name()!='library':back='Biblioteca'
        if self.current_popover(window) or isinstance(Gtk.grab_get_current(),Gtk.MenuShell):back='Cerrar menú'
        if window is self and focus is not None:
            if getattr(focus,'library_entry_id',None):activate='Abrir ficha'
            elif getattr(focus,'profile_id',None):activate='Ver perfil'
            elif isinstance(focus,Gtk.Entry):activate='Abrir teclado'
            elif isinstance(focus,Gtk.MenuButton):activate='Abrir menú'
            elif isinstance(focus,Gtk.Expander):activate='Cerrar' if focus.get_expanded() else 'Abrir'
            elif isinstance(focus,(Gtk.CheckButton,Gtk.Switch)):activate='Cambiar'
            elif isinstance(focus,Gtk.Button):
                caption=focus.get_label()
                if caption and len(caption)<=16:activate=caption
        hint.update(activate,back,window.get_size().width)

    def prepare_controller_window(self,window):
        if getattr(window,'_deck_focus_tracked',False):return
        window._deck_focus_tracked=True
        if window is not self:
            window.connect('set-focus',self.mark_controller_focus)
            if isinstance(window,Gtk.Dialog):
                from .controller_hints import ControllerHints
                hint=ControllerHints(compact=True);area=window.get_action_area();area.pack_start(hint,False,False,0);area.set_child_secondary(hint,True);area.set_child_non_homogeneous(hint,True);window._deck_controller_hints=hint
        self.mark_controller_focus(window,window.get_focus())

    def control_is_shown(self,widget):
        if widget is None or not widget.is_sensitive():return False
        child=widget
        while child is not None:
            if not child.get_visible():return False
            parent=child.get_parent()
            if isinstance(parent,Gtk.Stack) and parent.get_visible_child() is not child:return False
            if isinstance(parent,Gtk.Revealer) and not parent.get_reveal_child():return False
            child=parent
        return True

    def control_targets(self,root):
        if not root.get_mapped() or not root.is_sensitive():return []
        if isinstance(root,Gtk.Revealer) and not root.get_reveal_child():return []
        if isinstance(root,Gtk.ComboBox):
            # GTK delegates ComboBox focus to an internal child that is absent
            # from get_children(). Expose the actual picker to stick navigation.
            root.set_can_focus(True)
            return [root]
        if isinstance(root,Gtk.ListBoxRow):
            children=[]
            for child in root.get_children():children.extend(self.control_targets(child))
            if children:return children
        if isinstance(root,Gtk.Expander):
            # The header is a control of its own; the content is reachable only while it is open.
            result=[root] if root.get_can_focus() else []
            child=root.get_child()
            if child is not None and root.get_expanded():result.extend(self.control_targets(child))
            return result
        kinds=(Gtk.Button,Gtk.ComboBox,Gtk.Entry,Gtk.TextView,Gtk.Switch,Gtk.Scale,Gtk.TreeView,Gtk.ListBoxRow,Gtk.Socket)
        if isinstance(root,kinds) and root.get_can_focus():return [root]
        result=[]
        if isinstance(root,Gtk.Container):
            for child in root.get_children():result.extend(self.control_targets(child))
        return result

    def current_popover(self,window):
        focus=window.get_focus();popover=focus.get_ancestor(Gtk.Popover) if focus else None
        if popover and popover.get_mapped() and self.control_is_shown(popover.get_relative_to()):return popover
        def find(widget):
            if not widget.get_mapped() or not widget.is_sensitive():return None
            if isinstance(widget,Gtk.MenuButton):
                value=widget.get_popover()
                if value and value.get_mapped():return value
            if isinstance(widget,Gtk.Stack):
                child=widget.get_visible_child()
                return find(child) if child else None
            if isinstance(widget,Gtk.Revealer) and not widget.get_reveal_child():return None
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():
                    value=find(child)
                    if value:return value
            return None
        return find(window)

    def ensure_controller_focus(self,window):
        if self.ui_closed:return False
        workflow=self.inline_workflows[-1] if window is self and getattr(self,'inline_workflows',[]) else None
        focus=window.get_focus()
        if focus is not None and focus.get_mapped() and focus.is_sensitive():
            self.mark_controller_focus(window,focus);return False
        if not workflow and window is self and self.pages.get_visible_child_name()=='library':
            self.focus_library()
            if self.get_focus() is not None and self.get_focus().get_mapped():return False
        targets=self.control_targets(self.current_popover(window) or workflow or window)
        preferred=None
        if not workflow and window is self and self.pages.get_visible_child_name()=='detail':
            preferred=getattr(self,'game_play_button',None) if self.game_tab=='profiles' else getattr(self.game_pages.get_visible_child(),'back_control',None)
        target=preferred if preferred in targets else next(iter(targets),None)
        if target:target.grab_focus();self.mark_controller_focus(window,target);self.reveal_focus(target)
        return False

    def move_control_focus(self,window,direction):
        from .navigation import control_neighbour
        popover=self.current_popover(window);workflow=self.inline_workflows[-1] if window is self and getattr(self,'inline_workflows',[]) else None;targets=self.control_targets(popover or workflow or window);focus=self.navigation_focus(window);rectangles={}
        for index,widget in enumerate(targets):
            point=widget.translate_coordinates(window,0,0)
            if point:rectangles[index]=(*point,widget.get_allocated_width(),widget.get_allocated_height())
        current=targets.index(focus) if focus in targets else None
        target=control_neighbour(rectangles,current,direction)
        if target is not None:
            control=targets[target];control.grab_focus();self.mark_controller_focus(window,control);self.reveal_focus(control)
        return bool(targets)

    def control_focus_token(self):
        focus=self.get_focus()
        if focus is None:return None
        if getattr(focus,'profile_id',None):return ('profile',focus.profile_id)
        name=focus.get_accessible().get_name()
        return ('name',name) if name else None

    def restore_control_focus(self,token):
        if self.ui_closed or self.pages.get_visible_child_name()!='detail':return False
        if token:
            for widget in self.control_targets(self):
                match=getattr(widget,'profile_id',None) if token[0]=='profile' else widget.get_accessible().get_name()
                if match==token[1]:widget.grab_focus();self.mark_controller_focus(self,widget);self.reveal_focus(widget);return False
        return self.ensure_controller_focus(self)

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
        self.mark_controller_focus(window,focus)
        identifier=getattr(focus,'library_entry_id',None)
        if identifier:self.library_focus_id=identifier
        for target in getattr(self,'library_targets',{}).values():
            style=target.library_focus_visual.get_style_context()
            style.add_class('game-focused') if target is focus else style.remove_class('game-focused')

    def focus_library(self,identifier=None):
        if self.ui_closed or self.pages.get_visible_child_name()!='library':return False
        self._scroll_focus_hold=(None,0)
        targets=getattr(self,'library_targets',{})
        wanted=identifier or getattr(self,'library_focus_id',None)
        if wanted not in targets:wanted=next((pid for pid,roms in getattr(self,'rom_associations',{}).items() if any(o.id==wanted for o in roms)),wanted)
        target=targets.get(wanted) or next(iter(targets.values()),None)
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
        elif action=='up':
            control=self.platform_picker if self.platform_picker.get_mapped() else self.search
            control.set_can_focus(True);control.grab_focus();self.mark_controller_focus(self,control)
        elif action=='down' and self.selection_mode:self.select_button.grab_focus()
        return True

    def reveal_focus(self,focus):
        import time
        held,until=getattr(self,'_scroll_focus_hold',(None,0))
        if focus is held and time.monotonic()<until:return
        self.reveal_bounds(focus)
        self._pending_reveal=focus
        if getattr(self,'_reveal_scheduled',False):return
        self._reveal_scheduled=True
        def after_layout():
            self._reveal_scheduled=False
            if not self.ui_closed and self.get_focus() is self._pending_reveal:self.reveal_bounds(self._pending_reveal)
            return False
        GLib.idle_add(after_layout)

    def reveal_bounds(self,focus):
        if focus is None or not focus.get_mapped():return
        visual=getattr(focus,'library_focus_visual',focus);scroll=focus.get_ancestor(Gtk.ScrolledWindow)
        while scroll:
            child=scroll.get_child();content=child.get_child() if isinstance(child,Gtk.Viewport) else child
            point=visual.translate_coordinates(content,0,0) if content else None
            if point:
                for axis,size,adjustment in ((0,visual.get_allocated_width(),scroll.get_hadjustment()),(1,visual.get_allocated_height(),scroll.get_vadjustment())):
                    start=point[axis];value=adjustment.get_value();page=adjustment.get_page_size();padding=12
                    if start-padding<value:value=start-padding
                    elif start+size+padding>value+page:value=start+size+padding-page
                    adjustment.set_value(max(adjustment.get_lower(),min(value,adjustment.get_upper()-page)))
            parent=scroll.get_parent();scroll=parent.get_ancestor(Gtk.ScrolledWindow) if parent else None

    def keep_scroll_focus(self,scroll,focus,vertical):
        # Native text/tree views scroll their contents inside a fixed widget.
        child=scroll.get_child()
        if focus is None or not isinstance(child,Gtk.Viewport):return
        content=child.get_child();visual=getattr(focus,'library_focus_visual',focus)
        point=visual.translate_coordinates(content,0,0)
        if not point:return
        axis=1 if vertical else 0;adjustment=scroll.get_vadjustment() if vertical else scroll.get_hadjustment();value=adjustment.get_value();page=adjustment.get_page_size()
        size=visual.get_allocated_height() if vertical else visual.get_allocated_width()
        focus_point=focus.translate_coordinates(content,0,0)
        focus_size=focus.get_allocated_height() if vertical else focus.get_allocated_width()
        if focus_point and focus_point[axis]+focus_size>value and focus_point[axis]<value+page:return
        candidates=[]
        for index,widget in enumerate(self.control_targets(scroll)):
            view=getattr(widget,'library_focus_visual',widget);pos=view.translate_coordinates(content,0,0)
            length=view.get_allocated_height() if vertical else view.get_allocated_width()
            hit=widget.translate_coordinates(content,0,0);hit_length=widget.get_allocated_height() if vertical else widget.get_allocated_width()
            if pos and hit and hit[axis]+hit_length>value and hit[axis]<value+page:
                full=value<=pos[axis] and pos[axis]+length<=value+page
                candidates.append((not full,abs(pos[1-axis]-point[1-axis]),abs(pos[axis]-value),index,widget))
        if candidates:
            target=min(candidates,key=lambda row:row[:4])[4];target.grab_focus();self.mark_controller_focus(target.get_toplevel(),target)

    def scroll_controller(self,action,window):
        import time
        self._pending_reveal=None;self._scroll_focus_hold=(window.get_focus(),time.monotonic()+.4)
        focus=window.get_focus();scroll=focus.get_ancestor(Gtk.ScrolledWindow) if focus else None
        candidates=[]
        while scroll:
            candidates.append(scroll)
            parent=scroll.get_parent();scroll=parent.get_ancestor(Gtk.ScrolledWindow) if parent else None
        def find(widget):
            if not widget.get_mapped():return []
            values=[widget] if isinstance(widget,Gtk.ScrolledWindow) else []
            if isinstance(widget,Gtk.Stack):
                child=widget.get_visible_child()
                if child:values.extend(find(child))
            elif isinstance(widget,Gtk.Container):
                for child in widget.get_children():values.extend(find(child))
            return values
        # Tabs and headers can sit outside the scrolling content. Prefer the
        # focused pane, then try visible panes with actual overflow; an outer
        # viewport that fits must not hide its scrollable descendants.
        workflow=self.inline_workflows[-1] if window is self and getattr(self,'inline_workflows',[]) else None
        for pane in sorted(find(workflow or window),key=lambda w:w.get_allocated_width()*w.get_allocated_height(),reverse=True):
            if pane not in candidates:candidates.append(pane)
        vertical=action in ('scroll_up','scroll_down')
        for scroll in candidates:
            adjustment=scroll.get_vadjustment() if vertical else scroll.get_hadjustment()
            lower=adjustment.get_lower();upper=max(lower,adjustment.get_upper()-adjustment.get_page_size())
            if upper>lower:
                sign=-1 if action in ('scroll_up','scroll_left') else 1
                adjustment.set_value(max(lower,min(upper,adjustment.get_value()+sign*min(96,max(32,adjustment.get_page_size()*.16)))))
                self.keep_scroll_focus(scroll,focus,vertical)
                return True
        return True

    def controller_action(self,action,window=None):
        import time
        now=time.monotonic();previous=getattr(self,'last_controller_action',('',0))
        if previous[0]==action and now-previous[1]<.09:return True
        self.last_controller_action=(action,now)
        self.controller_mode=True;self.disable_tooltips()
        if hasattr(self,'controller_hint'):self.controller_hint.show()
        window=window or self
        self.prepare_controller_window(window)
        workflow=self.inline_workflows[-1] if window is self and getattr(self,'inline_workflows',[]) else None
        handler=getattr(workflow or window,'account_controller',None)
        if handler and handler(action):return True
        grab=Gtk.grab_get_current()
        if isinstance(grab,Gtk.Menu):
            anchor=grab.get_attach_widget()
            if anchor is not None and not self.control_is_shown(anchor):grab.cancel();grab=None
        if isinstance(grab,Gtk.MenuShell) and grab.get_mapped():
            if action=='back':grab.cancel();return True
            items=[c for c in grab.get_children() if c.get_sensitive() and c.get_visible()]
            current=grab.get_selected_item()
            if action=='activate' and current:grab.activate_item(current,True);return True
            if action in ('up','down') and items:
                index=items.index(current) if current in items else -1;grab.select_item(items[(index+(1 if action=='down' else -1))%len(items)]);return True
        if workflow and action=='search':
            focus=self.get_focus();entries=[w for w in self.control_targets(workflow) if isinstance(w,Gtk.Entry)]
            if entries or isinstance(focus,Gtk.Socket):self.open_keyboard(focus if isinstance(focus,(Gtk.Entry,Gtk.Socket)) else entries[0])
            return True
        if workflow and action in ('previous_tab','next_tab'):return True
        if action in ('previous_tab','next_tab') and window is self:
            names=list(self.nav_buttons);tab={'home':'Inicio','library':'Biblioteca','validated':'Verificados','detail':{'home':'Inicio','validated':'Verificados'}.get(getattr(self,'detail_origin','library'),'Biblioteca'),'catalog':'Catálogo de ports','updates':'Actualizaciones','settings':'Ajustes'}.get(self.pages.get_visible_child_name(),'Biblioteca');active=names.index(tab);self.nav_buttons[names[(active+(-1 if action=='previous_tab' else 1))%len(names)]].clicked();return True
        if action=='back':
            popover=self.current_popover(window)
            if popover:
                anchor=popover.get_relative_to();popover.popdown()
                if anchor:anchor.grab_focus();self.mark_controller_focus(window,anchor)
                return True
            if workflow:workflow.cancel()
            elif isinstance(window,Gtk.Dialog):window.response(Gtk.ResponseType.CANCEL)
            elif window is self:
                if self.pages.get_visible_child_name()=='detail':self.back_from_game()
                elif self.pages.get_visible_child_name()!='library':self.open_library()
                else:
                    if self.selection_mode:self.toggle_selection()
                    elif self.search.get_text():self.search.set_text('')
                    GLib.idle_add(self.focus_library)
            return True
        if action.startswith('scroll_'):return self.scroll_controller(action,window)
        if action=='search' and window is self:
            if self.pages.get_visible_child_name()=='home':self.open_library()
            entry=self.validated_search if self.pages.get_visible_child_name()=='validated' and hasattr(self,'validated_search') else self.catalog_search if self.pages.get_visible_child_name()=='catalog' and hasattr(self,'catalog_search') else self.search
            self.open_keyboard(entry);return True
        if not workflow and window is self and self.move_library_focus(action):return True
        focus=self.navigation_focus(window)
        if action=='activate':
            if not self.control_is_shown(focus):self.ensure_controller_focus(window);return True
            if isinstance(focus,Gtk.Entry):self.open_keyboard(focus)
            elif isinstance(focus,Gtk.ComboBox):focus.popup()
            elif isinstance(focus,Gtk.Switch):focus.set_active(not focus.get_active())
            elif isinstance(focus,Gtk.Expander):focus.set_expanded(not focus.get_expanded())
            elif isinstance(focus,Gtk.Button):focus.clicked()
            elif isinstance(focus,Gtk.ListBoxRow):focus.activate()
            elif not window.activate_focus():window.activate_default()
            # Rendering a game/catalog page can outlast the echo suppression
            # interval. Measure from completion so a second Steam Input event
            # cannot activate an unrelated control in the newly opened page.
            self.last_controller_action=(action,time.monotonic())
            return True
        if action in ('up','down','left','right'):
            if isinstance(focus,Gtk.SpinButton) and action in ('left','right'):
                focus.spin(Gtk.SpinType.STEP_BACKWARD if action=='left' else Gtk.SpinType.STEP_FORWARD,1);return True
            if isinstance(focus,Gtk.Scale) and action in ('left','right'):
                adjustment=focus.get_adjustment();focus.set_value(focus.get_value()+(-1 if action=='left' else 1)*adjustment.get_step_increment());return True
            return self.move_control_focus(window,action)

        return False
