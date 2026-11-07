"""Tools page: conversions and maintenance actions that are not game settings, and the standalone Xbox ISO extraction."""
import pathlib,re,shutil,tempfile,threading
from gi.repository import Gtk,GLib,Pango
from .inline_pages import InlineDialog
from .installations import save_settings
from . import layout
from .ui_components import ActionButton,SettingsRow,text

class ToolboxMixin:
    def tools_page(self,*_):
        """One row per tool. Rows that need the Desktop (adding to Steam) or the owner's account are left out when they do not apply."""
        from . import motion
        from .gui import label
        if not self.discard_game_edits():return
        self.reset_page(self.tools_box);heading=label('Herramientas','hero');heading.set_no_show_all(True);heading.hide();self.tools_box.pack_start(heading,False,False,0)
        tools=[('Convertir un juego de Switch','Convierte un XCI o NSP propio (y su actualización) en la carpeta exefs y romfs que piden algunos ports.','Convertir','folder',lambda _:self.switch_convert_page()),
               ('Extraer una ISO de Xbox, Xbox 360 o PS3','Extrae el contenido de una ISO a una carpeta, verificándolo. Sirve para los ports que piden la carpeta del juego.','Extraer','folder',lambda _:self.iso_extract_page()),
               ('Switch 2 (experimental)','Emulador y carpeta para juegos de Switch 2. Se usan forks de Eden que todavía no son del todo compatibles.','Ver','controller',lambda _:self.switch2_page()),
               ('ROMs y ports instalados','Gestionar la copia de consola de un juego que ya tiene un port.','Gestionar ROMs','folder',lambda _:self.originals_dialog()),
               ('Duplicados y conflictos','Posibles copias de juegos e instalaciones alternativas.','Revisar','search',lambda _:self.conflicts_page()),
               ('Juegos ocultos','Restaurar juegos quitados de la biblioteca sin borrar sus archivos.','Juegos ocultos','library',self.hidden_games_dialog)]
        if self.offer_steam_shortcut():tools.append(('Deck Library en Steam','Abrir esta biblioteca desde Steam, a pantalla completa en modo Juego.','Agregar a Steam','steam',self.add_library_to_steam))
        for title,description,caption,icon,action in tools:
            row=SettingsRow(title,description,caption,icon,action);self.tools_box.pack_start(row,False,False,0)
            if title=='Deck Library en Steam':self.steam_tools_row=row
        self.pin_page_header(self.tools_box,self.tools_box.get_children()[0])
        self.tools_box.show_all();self.pages.set_visible_child_name('tools')

    def switch2_page(self,*_):
        """Where Switch 2 games go, which emulator is in use, and the community forks that run them. Nothing is downloaded or installed."""
        import json,subprocess
        from . import i18n
        from .discovery import available_emulators
        page=InlineDialog(title='Switch 2 (experimental)',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(10)
        body.pack_start(text('Los juegos de Switch 2 se ejecutan con forks comunitarios de Eden. No son versiones del equipo de Eden, siguen siendo experimentales y Eden oficial no los ejecuta. Hace falta el juego propio, prod.keys y firmware propios: Deck Library no los incluye ni los descarga.','muted',95),False,False,0)
        games=layout.folder('roms')/'switch2'
        try:games.mkdir(parents=True,exist_ok=True)
        except OSError:pass
        card=self.card(body,'Emulador en uso');status=text('','muted',90);card.pack_start(status,False,False,0)
        def refresh():
            found=available_emulators(preferences=self.preferences).get('switch2')
            status.set_text('Detectado: '+' '.join(found['command']) if found else 'No se detectó ningún emulador de Switch 2. Elegir su programa o dejar su AppImage en ~/Applications.')
        def choose(_):
            path=self.pick_file('Elegir el emulador de Switch 2')
            if not path:return
            emulators=dict(self.preferences.get('emulators',{}));emulators['switch2']=[path];self.preferences['emulators']=emulators;save_settings(self.preferences,self.store);refresh()
        card.pack_start(ActionButton('Elegir programa','folder',choose,'steam-outline'),False,False,0)
        folder=self.card(body,'Carpeta de los juegos')
        folder.pack_start(text('Los NSP y XCI de Switch 2 van en '+str(games).replace(str(pathlib.Path.home()),'~')+' (o en una carpeta llamada switch2 o nx2 dentro de cualquier carpeta de ROMs). Después, «Actualizar biblioteca» los agrega como juegos de Switch 2.','muted',90),False,False,0)
        try:data=json.loads((pathlib.Path(__file__).resolve().parent.parent/'catalog/switch2-emulators.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):data={'emulators':[]}
        known=self.card(body,'Forks conocidos')
        known.pack_start(text('Lista de la guía comunitaria '+data.get('source','')+' (estado al '+data.get('as_of','')+'). Deck Library no los probó.','meta',90),False,False,0)
        for emulator in data.get('emulators',[]):
            note=emulator.get('note_en') if i18n.language()=='en' else emulator.get('note');known.pack_start(text(emulator['name'],'title',90),False,False,0);known.pack_start(text(', '.join(emulator.get('systems',[]))+' · '+(note or ''),'muted',90),False,False,0)
            known.pack_start(ActionButton('Abrir página','file',lambda _,u=emulator['url']:subprocess.Popen(['xdg-open',u],start_new_session=True),'quiet'),False,False,0)
        refresh();page.connect('response',lambda *_:page.destroy());page._mount();return page

    def extract_iso_for_port(self,item):
        """The ISO tool, opened from a port: when the extraction ends the game folder can go straight into the port's folder."""
        return self.iso_extract_page(on_done=lambda folder:self.place_extracted_folder(item,folder))

    def place_extracted_folder(self,item,folder):
        """Move the contents of an extracted game folder into the installed port's folder (a move, so the game does not take space twice)."""
        from . import ports
        record=ports.records(self.store).get(item['repository'])
        if not record:return
        target=ports.folder_for(record);source=pathlib.Path(folder)
        if not target.is_dir() or not source.is_dir():return
        if not self.confirm('Archivos del juego',f'La carpeta extraída está en {source}. ¿Mover su contenido a la carpeta del port ({target})? Así el juego no ocupa espacio dos veces.','Mover'):return
        clashes=[child.name for child in source.iterdir() if (target/child.name).exists()]
        if clashes:self.message('No se movió nada','La carpeta del port ya tiene: '+', '.join(clashes[:4])+'. Moverlos o cambiarles el nombre y repetir.');return
        self.toast('Moviendo los archivos del juego…')
        def work():
            try:
                for child in sorted(source.iterdir()):shutil.move(str(child),str(target/child.name))
                source.rmdir();error=None
            except OSError as failure:error=failure
            GLib.idle_add(lambda:(self.message('No se pudo mover',str(error)) if error else self.toast('Archivos del juego en la carpeta del port'),False)[1])
        threading.Thread(target=work,daemon=True).start()

    def iso_extract_page(self,*_,on_done=None):
        """Extract an Xbox, Xbox 360 or PS3 ISO into <destination>/<ISO name>. The ISO is only read; the folder appears after the extraction is verified.
        `on_done(folder)` is called with the extracted folder so a port's setup can use it right away."""
        from .iso_import import extract_folder
        from .ports import Cancelled
        page=InlineDialog(title='Extraer una ISO',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(10)
        body.pack_start(text('Extrae el contenido de una ISO de Xbox, Xbox 360 o PlayStation 3 a una carpeta, comprobando cada archivo. La ISO no se modifica. Las ISO de PS3 tienen que estar descifradas; GameCube, Wii y las demás consolas no se admiten.','muted',95),False,False,0)
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
                path=self.pick_file(title,folder=folder,patterns=() if folder else ('*.iso','*.xiso'),filter_name='' if folder else 'Imágenes de disco')
                if not path:return
                state[key]=path
                if key=='root':self.preferences['iso_root']=path;save_settings(self.preferences,self.store)
                status.set_text('');refresh()
            return choose
        row('iso','Imagen ISO','Elegir',pick('iso','Elegir la ISO de Xbox, Xbox 360 o PS3'));row('root','Carpeta de destino','Cambiar',pick('root','Elegir la carpeta de destino',True))
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
            else:status.set_text(f"{result['path']}\n{result['files']} archivos · {result['size']/1024**3:.1f} GB\nListo.");self.toast('ISO extraída');on_done and on_done(result['path'])
            refresh();return False
        def run_extract(_):
            if state['busy']:return
            source,root=pathlib.Path(state['iso']),pathlib.Path(state['root']).expanduser();cancel=threading.Event();state.update(busy=True,cancel=cancel);progress.set_no_show_all(False);progress.show();progress.set_fraction(0);status.set_text('Preparando…');refresh()
            def work():
                try:GLib.idle_add(finish,extract_folder(source,root,lambda event:GLib.idle_add(paint,event),cancel),None)
                except Exception as error:GLib.idle_add(finish,None,error)
            threading.Thread(target=work,daemon=True).start()
        actions=page.get_action_area()
        extract=ActionButton('Extraer','play',run_extract,'play');actions.pack_start(extract,False,False,0)
        cancel_button=ActionButton('Cancelar','undo',lambda _:state['cancel'].set() if state['cancel'] else None,'danger');cancel_button.set_no_show_all(True);actions.pack_start(cancel_button,False,False,0)
        def closing(*_):
            state['alive']=False
            if state['cancel']:state['cancel'].set()
        page.connect('destroy',closing);page.connect('response',lambda *_:page.destroy())
        refresh();page._mount();return page
