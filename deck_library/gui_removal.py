"""Removal choices inside the application, including reversible library-only hiding."""
import threading
from gi.repository import Gtk,GLib
from . import game_removal
from .inline_pages import InlineDialog
from .ui_components import ActionButton,TaskButton,text


class RemovalMixin:
    def remove_game_dialog(self,entry):
        if not self.discard_game_edits():return
        page=InlineDialog(title='Eliminar · '+entry.name,transient_for=self)
        body=page.get_content_area();body.set_spacing(16)
        body.pack_start(text('Elegir qué eliminar.','subtitle'),False,False,0)
        def hide(_):
            try:self.preferences['hidden_entries']=game_removal.set_hidden(entry.id,True,self.store)
            except (OSError,ValueError) as error:self.message('No se pudo quitar de la biblioteca',str(error));return
            page.destroy();self.checked.discard(entry.id);self.selected=None;self.detail_game_id=None
            self.library_dirty=True;self.refresh_platforms();self.open_library();self.toast('Juego quitado de la biblioteca')
        body.pack_start(TaskButton('Solo de la biblioteca','Conserva el juego, las partidas y el acceso de Steam. Se puede restaurar desde Herramientas → Juegos ocultos.','library',hide,'steam'),False,False,0)
        def delete(_):
            page.destroy();self.delete_game_data(entry)
        body.pack_start(TaskButton('Juego y datos','Borra los archivos y los datos de las rutas que se mostrarán para confirmar. También quita el acceso directo de Steam.','undo',delete,'danger'),False,False,0)
        page.add_button('Cancelar',Gtk.ResponseType.CANCEL);page.connect('response',lambda *_:page.destroy());page._mount()
        return page

    def delete_game_data(self,entry):
        if getattr(self,'port_busy',False):self.message('Instalación en curso','Esperar a que termine la instalación antes de eliminar un port.');return
        try:value=game_removal.plan(entry,self.store)
        except (OSError,ValueError) as error:self.message('No se pudo preparar la eliminación',str(error));return
        description='Se borran definitivamente los archivos de estas rutas, incluidas las partidas y la configuración que contengan. Esta acción no se puede deshacer.\n\nLos datos fuera de estas rutas se conservan, incluidos los datos compartidos del emulador y las ROMs externas.\n\nArchivos y carpetas que se eliminarán:\n'+'\n'.join(str(p) for p in value['paths'])
        if any(self.in_steam(e) for e in value['entries']):description+='\n\nTambién se quita el acceso directo de Steam. Si Steam está abierto, ese cambio se guarda al cerrarlo.'
        if not self.confirm('Eliminar juego y datos · '+entry.name,description,'Eliminar definitivamente',danger=True):return
        self.port_busy=True;progress=InlineDialog(title='Eliminando el juego y sus datos…',transient_for=self);progress.set_deletable(False)
        spinner=Gtk.Spinner();spinner.start();progress.get_content_area().pack_start(spinner,False,False,12);progress._mount()
        def done(result,error):
            self.port_busy=False
            if self.ui_closed:return False
            progress.destroy()
            if error:self.message('No se pudo completar la eliminación',error);return False
            from . import updates
            self.entries=self.store.load();self.checked-=set(result['ids']);self.library_dirty=True;self.update_state=updates.cached(self.store)
            self.selected=None;self.detail_game_id=None;self.refresh_platforms();self.refresh_pending();self.refresh_update_badges();self.open_library()
            self.toast('Juego y datos eliminados');return False
        def work():
            try:result=game_removal.execute(entry,self.store,expected=value);GLib.idle_add(done,result,None)
            except Exception as error:GLib.idle_add(done,None,str(error))
        threading.Thread(target=work,daemon=True).start()

    def hidden_games_dialog(self,*_):
        page=InlineDialog(title='Juegos ocultos',transient_for=self);body=page.get_content_area()
        body.pack_start(text('Restaurar un juego lo vuelve a mostrar en la biblioteca. Sus archivos no se modifican.','muted'),False,False,0)
        entries=[e for e in self.entries if e.id in self.preferences.get('hidden_entries',[])]
        if not entries:body.pack_start(text('No hay juegos ocultos.','subtitle'),False,False,0)
        for entry in entries:
            row=Gtk.Box(spacing=12);row.pack_start(text(entry.name,'title'),True,True,0)
            def restore(button,e=entry,line=row):
                try:self.preferences['hidden_entries']=game_removal.set_hidden(e.id,False,self.store)
                except (OSError,ValueError) as error:self.message('No se pudo restaurar el juego',str(error));return
                line.destroy();self.library_dirty=True;self.refresh_platforms();self.toast('Juego restaurado en la biblioteca')
            row.pack_end(ActionButton('Restaurar','undo',restore,'steam'),False,False,0);body.pack_start(row,False,False,0)
        page.add_button('Volver',Gtk.ResponseType.CLOSE);page.connect('response',lambda *_:page.destroy());page._mount();return page
