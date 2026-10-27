"""Screen-sized library workflows and non-modal pending Steam changes."""
import os,pathlib,sys,threading
from gi.repository import Gtk,Gdk,GLib
from .inline_pages import InlineDialog
from .models import Entry

class LibraryToolsMixin:
    def new_scroll(self):
        from .interactions import configure_scroll
        scroll=Gtk.ScrolledWindow();scroll.set_overlay_scrolling(False);scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);return configure_scroll(scroll)
    def fit_window(self,*_):
        if os.environ.get('SteamAppId') or '--gaming' in sys.argv:self.fullscreen()
        return False
    def fit_dialog(self,dialog):
        if isinstance(dialog,InlineDialog):return
        if getattr(dialog,'_deck_fitted',False):return
        dialog._deck_fitted=True
        display=Gdk.Display.get_default();monitor=display.get_monitor_at_window(self.get_window()) if self.get_window() else display.get_primary_monitor()
        area=monitor.get_workarea() if monitor else Gdk.Rectangle(x=0,y=0,width=1280,height=800)
        width,height=dialog.get_default_size();dialog.set_default_size(min(max(width,480),area.width-48),min(max(height,380),area.height-64))
        content=dialog.get_content_area();children=content.get_children()
        scroll=self.new_scroll();scroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC);scroll.set_hexpand(True);scroll.set_vexpand(True)
        body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=content.get_spacing());body.set_margin_end(12);body.set_margin_bottom(12)
        for child in children:content.remove(child);body.pack_start(child,True,True,0)
        scroll.add(body);content.pack_start(scroll,True,True,0)
    def build_pending_banner(self,parent):
        from .gui import label,button
        self.pending_bar=Gtk.Box(spacing=10);self.pending_bar.get_style_context().add_class('banner');self.pending_bar.set_no_show_all(True)
        self.pending_label=label('Reinicio de Steam pendiente para aplicar los cambios.');self.pending_label.set_hexpand(True);self.pending_bar.pack_start(self.pending_label,True,True,0)
        self.pending_bar.pack_end(button('Ver cambios',lambda _:self.pending_details()),False,False,0);parent.pack_start(self.pending_bar,False,False,0)
    def library_key(self,widget,event):
        if event.keyval in (Gdk.KEY_Return,Gdk.KEY_KP_Enter) and isinstance(self.get_focus(),Gtk.Button):return self.controller_action('activate')
        keys={Gdk.KEY_Up:'up',Gdk.KEY_Down:'down',Gdk.KEY_Left:'left',Gdk.KEY_Right:'right',Gdk.KEY_Page_Up:'previous_tab',Gdk.KEY_Page_Down:'next_tab'}
        focus=self.get_focus()
        if event.keyval in keys and not isinstance(focus,(Gtk.Entry,Gtk.TextView,Gtk.SpinButton,Gtk.ComboBox)):
            return self.controller_action(keys[event.keyval])
        if event.keyval==Gdk.KEY_Escape:return self.controller_action('back')
        return False
    def conflicts_page(self):
        from .gui import label,button
        from .conflicts import analyze
        dialog=InlineDialog(title='Duplicados y conflictos',transient_for=self,modal=True);dialog.set_default_size(760,580);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE);box=dialog.get_content_area();box.set_border_width(16)
        status=label('Revisando rutas e instalaciones…','muted');box.pack_start(status,False,False,8);results=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);box.pack_start(results,True,True,0);alive=[True]
        def show(rows,error):
            if not alive[0]:return False
            status.set_text(error or (f'{len(rows)} elementos para revisar.' if rows else 'No se detectaron duplicados ni conflictos en las rutas revisadas.'))
            for row in rows:
                card=self.card(results,row['title']);card.pack_start(label(row['note'],'muted'),False,False,0)
                for path in row['paths']:
                    text=label(path);text.set_selectable(True);text.set_max_width_chars(65);card.pack_start(text,False,False,0)
            results.show_all();return False
        entries=list(self.entries);preferences=dict(self.preferences)
        def work():
            try:GLib.idle_add(show,analyze(entries,preferences=preferences),None)
            except Exception as exc:GLib.idle_add(show,[],str(exc))
        threading.Thread(target=work,daemon=True).start()
        self.fit_dialog(dialog);dialog.show_all();dialog.run();alive[0]=False;dialog.destroy()

    def add_library_to_steam(self,*_):
        from .service import queue_entries
        account=self.current_account()
        if not account:self.message('Steam','Iniciar sesión en Steam para preparar el acceso directo.');return
        app=pathlib.Path(__file__).resolve().parent.parent/'app.py'
        from .library_app import entry as self_entry
        entry=self_entry(app)
        from .library_app import art_items
        from .service import queue_art
        def job():
            result=queue_entries([entry],account,self.store)
            items=art_items(account,self.store,app)
            if items:queue_art(items,account,self.store,preserve_pending=True)
            return result
        self.run_queue(job,'Preparando Deck Library para Steam…')
    def emulator_dialog(self,e):
        from .gui import label,button
        from .emulator_settings import inspect_emulator,set_language
        from .discovery import available_emulators
        dialog=InlineDialog(title='Emulador · '+e.platform,transient_for=self,modal=True);dialog.set_default_size(700,500);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE);box=dialog.get_content_area();box.set_border_width(16);box.set_spacing(12)
        state=inspect_emulator(e,self.preferences);text=label(state['summary']);text.set_selectable(True);text.set_max_width_chars(65);box.pack_start(text,False,False,0)
        if state['languages']:
            combo=Gtk.ComboBoxText()
            for key,title in state['languages'].items():combo.append(key,title)
            combo.set_active_id(state.get('language'));box.pack_start(combo,False,False,0)
            def save(_):
                try:set_language(e,combo.get_active_id(),self.store,self.preferences);self.toast('Idioma guardado para la próxima ejecución');dialog.response(Gtk.ResponseType.CLOSE)
                except Exception as exc:self.message('No se pudo guardar',str(exc))
            box.pack_start(button('Guardar idioma',save,True),False,False,0)
        box.pack_start(label('El mapeo de botones depende del emulador y del dispositivo. Abrir su editor para cambiarlo; el perfil de Steam se administra desde la ficha del juego.','muted'),False,False,0)
        slug=state['slug'];program=available_emulators(preferences=self.preferences).get(slug)
        if program:
            def open_(_):
                import subprocess
                from .runtime import clean_environment
                subprocess.Popen(program['command'],env=clean_environment(),start_new_session=True);dialog.response(Gtk.ResponseType.CLOSE)
            box.pack_start(button('Abrir configuración del emulador',open_),False,False,0)
        self.fit_dialog(dialog);dialog.show_all();dialog.run();dialog.destroy()
