"""Tools page: conversions and maintenance actions that are not game settings, and the standalone Xbox ISO extraction."""
import pathlib,re,shutil,tempfile,threading
from gi.repository import Gtk,GLib,Pango
from .inline_pages import InlineDialog
from .installations import save_settings
from . import layout
from .ui_components import ActionButton,text

class ToolboxMixin:
    def tools_page(self,*_):
        """One row per tool. Rows that need the Desktop (adding to Steam) or the owner's account are left out when they do not apply."""
        from . import motion
        from .gui import label
        if not self.discard_game_edits():return
        self.reset_page(self.tools_box);self.tools_box.pack_start(label('Herramientas','hero'),False,False,0)
        tools=[('Convertir un juego de Switch','Convierte un XCI o NSP propio (y su actualización) en la carpeta exefs y romfs que piden algunos ports.','Convertir','folder',lambda _:self.switch_convert_page()),
               ('Extraer una ISO de Xbox o Xbox 360','Extrae el contenido de una ISO de Xbox o Xbox 360 a una carpeta, verificándolo.','Extraer','folder',lambda _:self.iso_extract_page()),
               ('ROMs y ports instalados','Gestionar la copia de consola de un juego que ya tiene un port.','Gestionar ROMs','folder',lambda _:self.originals_dialog()),
               ('Duplicados y conflictos','Posibles copias de juegos e instalaciones alternativas.','Revisar','search',lambda _:self.conflicts_page())]
        if not motion.gaming_mode():tools.append(('Deck Library en Steam','Abrir esta biblioteca desde Steam, a pantalla completa en modo Juego.','Agregar a Steam','steam',self.add_library_to_steam))
        tools.append(('Reportar un problema o hacer una solicitud','Diagnósticos, pedidos de soporte y respuestas del equipo.','Abrir','file',lambda _:self.support_page()))
        tools.append(('Mis solicitudes y respuestas','Consultar los pedidos enviados con esta cuenta.','Ver respuestas','community',lambda _:self.my_requests_page()))
        if self.preferences.get('owner_mode'):tools.append(('Solicitudes recibidas','Los pedidos de juegos que llegaron al servicio. Solo se ven con la cuenta del propietario.','Ver','community',lambda _:self.owner_requests_page()))
        for title,description,caption,icon,action in tools:
            row=Gtk.Box(spacing=16);row.get_style_context().add_class('settings-row');words=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);words.pack_start(label(title,'title'),False,False,0);words.pack_start(label(description,'muted'),False,False,0)
            row.pack_start(words,True,True,0);row.pack_end(ActionButton(caption,icon,action,'steam' if icon=='steam' else 'violet' if icon=='community' else 'cyan'),False,False,0);self.tools_box.pack_start(row,False,False,0)
        self.tools_box.show_all();self.pages.set_visible_child_name('tools')

    def iso_extract_page(self,*_):
        """Extract an Xbox/Xbox 360 XISO into <destination>/<ISO name>. The ISO is only read; the folder appears after the extraction is verified."""
        from .iso_import import extract_folder
        from .ports import Cancelled
        page=InlineDialog(title='Extraer una ISO de Xbox',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(10)
        body.pack_start(text('Extrae el contenido de una ISO de Xbox o Xbox 360 a una carpeta, comprobando cada archivo. La ISO no se modifica. Solo sirve para ese formato (XISO); no para PlayStation, GameCube ni otras.','muted',95),False,False,0)
        state={'iso':'','root':self.preferences.get('iso_root') or str(layout.folder('iso')),'busy':False,'alive':True,'cancel':None}
        values={}
        def row(key,title,caption,choose):
            line=Gtk.Box(spacing=12);words=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2);words.pack_start(text(title,'title'),False,False,0)
            value=text('','muted',60);value.set_ellipsize(Pango.EllipsizeMode.END);value.set_line_wrap(False);words.pack_start(value,False,False,0);line.pack_start(words,True,True,0)
            line.pack_end(ActionButton(caption,'folder',choose,'neutral'),False,False,0);body.pack_start(line,False,False,0);values[key]=value
        def refresh():
            values['iso'].set_text(pathlib.Path(state['iso']).name if state['iso'] else 'Ninguna ISO elegida');values['root'].set_text(state['root']+'/<nombre de la ISO>')
            extract.set_sensitive(bool(state['iso']) and not state['busy']);cancel_button.set_visible(state['busy'])
        def pick(key,title,folder=False):
            def choose(_):
                if state['busy']:return
                path=self.pick_file(title,folder=folder,patterns=() if folder else ('*.iso','*.xiso'),filter_name='' if folder else 'Imágenes de Xbox')
                if not path:return
                state[key]=path
                if key=='root':self.preferences['iso_root']=path;save_settings(self.preferences,self.store)
                status.set_text('');refresh()
            return choose
        row('iso','Imagen ISO','Elegir',pick('iso','Elegir la ISO de Xbox o Xbox 360'));row('root','Carpeta de destino','Cambiar',pick('root','Elegir la carpeta de destino',True))
        progress=Gtk.ProgressBar();progress.set_no_show_all(True);body.pack_start(progress,False,False,0)
        status=text('','status',95);status.set_selectable(True);body.pack_start(status,False,False,0)
        def paint(event):
            if state['alive'] and isinstance(event,dict) and event.get('total'):
                progress.set_fraction(min(1,event['done']/event['total']));status.set_text(f"Extrayendo… {100*event['done']//event['total']}%")
            return False
        def finish(result,error):
            state['busy']=False;progress.hide()
            if not state['alive']:return False
            if isinstance(error,Cancelled):status.set_text('Cancelado. No se modificó nada.')
            elif error:status.set_text(str(error))
            else:status.set_text(f"{result['path']}\n{result['files']} archivos · {result['size']/1024**3:.1f} GB\nListo.");self.toast('ISO extraída')
            refresh();return False
        def run_extract(_):
            if state['busy']:return
            source,root=pathlib.Path(state['iso']),pathlib.Path(state['root']).expanduser();cancel=threading.Event();state.update(busy=True,cancel=cancel);progress.set_no_show_all(False);progress.show();progress.set_fraction(0);status.set_text('Preparando…');refresh()
            def work():
                try:GLib.idle_add(finish,extract_folder(source,root,lambda event:GLib.idle_add(paint,event),cancel),None)
                except Exception as error:GLib.idle_add(finish,None,error)
            threading.Thread(target=work,daemon=True).start()
        actions=Gtk.Box(spacing=10);body.pack_start(actions,False,False,0)
        extract=ActionButton('Extraer','play',run_extract,'play');actions.pack_start(extract,False,False,0)
        cancel_button=ActionButton('Cancelar','undo',lambda _:state['cancel'].set() if state['cancel'] else None,'danger');cancel_button.set_no_show_all(True);actions.pack_start(cancel_button,False,False,0)
        def closing(*_):
            state['alive']=False
            if state['cancel']:state['cancel'].set()
        page.connect('destroy',closing);page.connect('response',lambda *_:page.destroy())
        refresh();page._mount();return page
