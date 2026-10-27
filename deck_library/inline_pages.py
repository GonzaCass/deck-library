"""Single-window workflows. These widgets never create native windows."""
import pathlib,fnmatch
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib,GObject,Pango

class InlineDialog(Gtk.Box):
    __gsignals__={'response':(GObject.SignalFlags.RUN_LAST,None,(int,))}

    def __init__(self,title='',transient_for=None,modal=False,**kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.owner=transient_for.owner if isinstance(transient_for,InlineDialog) else transient_for
        self._loop=None;self._answer=None;self._mounted=False;self._closed=False;self._deletable=True;self._buttons={};self._default_size=(640,480)
        self.set_border_width(12);self.set_hexpand(True);self.set_vexpand(True)
        heading=Gtk.Label(label=title,xalign=0);heading.set_line_wrap(True);heading.get_style_context().add_class('inline-page-heading');self.pack_start(heading,False,False,0)
        self.content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        self.scroll=self.owner.new_scroll();self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC);self.scroll.set_overlay_scrolling(False);self.scroll.set_vexpand(True);self.scroll.add(self.content);self.pack_start(self.scroll,True,True,0)
        self.actions=Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL);self.actions.set_layout(Gtk.ButtonBoxStyle.END);self.actions.set_spacing(10);self.pack_end(self.actions,False,False,0)
        self.connect('destroy',self._destroyed)

    def get_content_area(self):return self.content
    def get_action_area(self):return self.actions
    def set_default_size(self,width,height):self._default_size=(width,height)
    def get_default_size(self):return self._default_size
    def get_size(self):return self.owner.get_size()
    def get_focus(self):return self.owner.get_focus()
    def set_deletable(self,value):self._deletable=value
    def add_button(self,text,response):
        button=Gtk.Button(label=text);button.connect('clicked',lambda _:self.response(response));self.actions.add(button);self._buttons[response]=button
        if response in (Gtk.ResponseType.OK,Gtk.ResponseType.ACCEPT):button.get_style_context().add_class('primary')
        return button
    def add_buttons(self,*pairs):
        for i in range(0,len(pairs),2):self.add_button(pairs[i],pairs[i+1])
    def set_response_sensitive(self,response,value):
        if response in self._buttons:self._buttons[response].set_sensitive(value)
    def cancel(self):
        if not self._deletable:return
        # Long-running setup tasks explicitly disable their only close action.
        if self._buttons and not any(b.get_sensitive() for b in self._buttons.values()):return
        self.response(Gtk.ResponseType.CANCEL)
    def response(self,value):
        self._answer=int(value);self.emit('response',int(value))
        if self._loop and self._loop.is_running():self._loop.quit()
    def _mount(self):
        if self._mounted:return
        self._mounted=True;owner=self.owner;self._previous_focus=owner.get_focus();self._previous=owner.workflow_stack.get_visible_child()
        owner.inline_workflows.append(self);owner.workflow_stack.add(self);owner.workflow_stack.show();owner.workflow_stack.set_visible_child(self)
        for control in owner.navigation_controls:control.set_sensitive(False)
        from .interactions import manual_text_input
        manual_text_input(self)
        Gtk.Box.show_all(self);owner.workflow_stack.set_visible_child(self)
        GLib.idle_add(self._focus_first)
    def _focus_first(self):
        if self._closed:return False
        targets=self.owner.control_targets(self)
        if targets:
            targets[0].grab_focus();self.owner.mark_controller_focus(self.owner,targets[0])
        return False
    def run(self):
        self._mount();self._answer=None;self._loop=GLib.MainLoop()
        self._loop.run();self._loop=None
        return self._answer if self._answer is not None else Gtk.ResponseType.CANCEL
    def _destroyed(self,*_):
        self._closed=True
        if self._loop and self._loop.is_running():self._loop.quit()
        if not self._mounted:return
        owner=self.owner
        visible=bool(owner.inline_workflows and owner.inline_workflows[-1] is self)
        if self in owner.inline_workflows:owner.inline_workflows.remove(self)
        if owner.ui_closed:return
        for page in owner.inline_workflows:
            if page._previous is self:page._previous=self._previous;page._previous_focus=self._previous_focus
        if self.get_parent() is owner.workflow_stack:owner.workflow_stack.remove(self)
        previous=self._previous
        if visible and previous and previous.get_parent() is owner.workflow_stack:owner.workflow_stack.set_visible_child(previous)
        for control in owner.navigation_controls:control.set_sensitive(not owner.inline_workflows)
        if not visible:return
        focus=self._previous_focus
        def restore():
            if owner.ui_closed:return False
            if focus and owner.control_is_shown(focus):focus.grab_focus();owner.mark_controller_focus(owner,focus)
            else:owner.ensure_controller_focus(owner)
            owner.update_controller_hints(owner);return False
        GLib.idle_add(restore)

class InlineFileChooser(InlineDialog):
    """Local file browser with explicit actions, without native chooser dialogs."""
    def __init__(self,title='',transient_for=None,action=Gtk.FileChooserAction.OPEN,patterns=(),filter_name='',**kwargs):
        super().__init__(title,transient_for,**kwargs);self.action=action;self.overwrite=False;self.selected=None;self.folder=pathlib.Path.home();self.patterns=tuple(patterns)
        bar=Gtk.Box(spacing=8);self.path=Gtk.Entry();self.path.set_hexpand(True);self.path.set_text(str(self.folder));self.path.connect('activate',lambda _:self.open_path());bar.pack_start(self.path,True,True,0)
        for text,callback in [('Ir',self.open_path),('Subir',lambda:self.load(self.folder.parent)),('Inicio',lambda:self.load(pathlib.Path.home())),('Descargas',lambda:self.load(pathlib.Path.home()/'Downloads'))]:
            button=Gtk.Button(label=text);button.connect('clicked',lambda _,cb=callback:cb());bar.pack_start(button,False,False,0)
        self.content.pack_start(bar,False,False,0)
        self.file_filter=None
        if self.patterns and action==Gtk.FileChooserAction.OPEN:
            self.file_filter=Gtk.ComboBoxText();self.file_filter.append('matching',filter_name or ', '.join(self.patterns));self.file_filter.append('all','Todos los archivos');self.file_filter.set_active_id('matching');self.file_filter.connect('changed',lambda *_:self.load(self.folder));self.content.pack_start(self.file_filter,False,False,0)
        self.status=Gtk.Label(xalign=0);self.status.set_line_wrap(True);self.content.pack_start(self.status,False,False,0)
        self.files=Gtk.ListBox();self.files.set_selection_mode(Gtk.SelectionMode.SINGLE);self.files.connect('row-selected',self.select);self.files.connect('row-activated',self.open_row)
        scroll=self.owner.new_scroll();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);scroll.set_min_content_height(140);scroll.set_vexpand(True);scroll.add(self.files);self.content.pack_start(scroll,True,True,0)
        self.filename=Gtk.Entry();self.filename.set_placeholder_text('Nombre del archivo');self.filename.set_no_show_all(action!=Gtk.FileChooserAction.SAVE);self.filename.set_visible(action==Gtk.FileChooserAction.SAVE);self.content.pack_start(self.filename,False,False,0)
        self.load(self.folder)
    def load(self,folder):
        try:
            folder=pathlib.Path(folder).expanduser().resolve();rows=sorted((p for p in folder.iterdir() if not p.name.startswith('.')),key=lambda p:(not p.is_dir(),p.name.casefold()))
        except OSError as error:self.status.set_text(str(error));return
        self.folder=folder;self.selected=None;self.path.set_text(str(folder));self.status.set_text('')
        for row in self.files.get_children():row.destroy()
        for p in rows:
            if self.action==Gtk.FileChooserAction.SELECT_FOLDER and not p.is_dir():continue
            if not p.is_dir() and not self.matches(p):continue
            row=Gtk.ListBoxRow();row.path=p;box=Gtk.Box(spacing=10);box.pack_start(Gtk.Image.new_from_icon_name('folder-symbolic' if p.is_dir() else 'text-x-generic-symbolic',Gtk.IconSize.BUTTON),False,False,0);label=Gtk.Label(label=p.name,xalign=0);label.set_ellipsize(Pango.EllipsizeMode.END);label.set_max_width_chars(64);label.set_width_chars(1);box.pack_start(label,True,True,0);row.add(box);self.files.add(row)
        self.files.show_all()
    def matches(self,path):
        return not self.file_filter or self.file_filter.get_active_id()=='all' or any(fnmatch.fnmatchcase(path.name.casefold(),pattern.casefold()) for pattern in self.patterns)
    def open_path(self):
        p=pathlib.Path(self.path.get_text()).expanduser()
        if p.is_dir():self.load(p)
        elif p.is_file() and self.action!=Gtk.FileChooserAction.SELECT_FOLDER:self.load(p.parent);self.selected=p;self.filename.set_text(p.name)
        else:self.status.set_text('La ruta no existe o no es una carpeta.')
    def select(self,_,row):
        if row:
            self.selected=row.path
            if row.path.is_file():self.filename.set_text(row.path.name)
    def open_row(self,_,row):
        if row.path.is_dir():self.load(row.path)
        else:self.selected=row.path;self.response(Gtk.ResponseType.OK)
    def get_filename(self):
        if self.action==Gtk.FileChooserAction.SAVE:return str(self.folder/self.filename.get_text().strip())
        return str(self.selected or self.folder)
    def set_current_name(self,name):self.filename.set_text(name)
    def set_do_overwrite_confirmation(self,value):self.overwrite=value
    def response(self,value):
        if value==Gtk.ResponseType.OK:
            path=pathlib.Path(self.get_filename())
            if self.action==Gtk.FileChooserAction.OPEN and not path.is_file():self.status.set_text('Elegir un archivo.');return
            if self.action==Gtk.FileChooserAction.OPEN and not self.matches(path):self.status.set_text('El archivo no coincide con el filtro seleccionado.');return
            if self.action==Gtk.FileChooserAction.SELECT_FOLDER and not path.is_dir():self.status.set_text('Elegir una carpeta.');return
            if self.action==Gtk.FileChooserAction.SAVE:
                name=self.filename.get_text().strip()
                if not name or pathlib.Path(name).name!=name:self.status.set_text('Escribir un nombre de archivo sin carpetas.');return
                if path.exists() and self.overwrite and not self.owner.confirm('Reemplazar archivo',str(path),'Reemplazar',danger=True):return
        super().response(value)

class InlineFileButton(Gtk.Button):
    __gsignals__={'file-set':(GObject.SignalFlags.RUN_LAST,None,())}
    def __init__(self,title='',action=Gtk.FileChooserAction.OPEN,patterns=(),filter_name=''):
        super().__init__(label=title);self.title=title;self.action=action;self.patterns=patterns;self.filter_name=filter_name;self.filename=None;self.connect('clicked',self.choose)
    def get_filename(self):return self.filename
    def set_filename(self,name):
        self.filename=str(name);self.set_label(pathlib.Path(name).name);self.set_tooltip_text(str(name));self.get_child().set_ellipsize(Pango.EllipsizeMode.MIDDLE);self.get_child().set_max_width_chars(40)
    def choose(self,*_):
        page=InlineFileChooser(title=self.title,transient_for=self.get_toplevel(),action=self.action,patterns=self.patterns,filter_name=self.filter_name);page.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Elegir',Gtk.ResponseType.OK)
        if self.filename:page.load(pathlib.Path(self.filename).parent)
        if page.run()==Gtk.ResponseType.OK:self.set_filename(page.get_filename());self.emit('file-set')
        page.destroy()
