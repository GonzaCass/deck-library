"""Switch XCI/NSP to exefs/romfs conversion page, for ports that ask for an extracted dump."""
import pathlib,shutil,threading
from gi.repository import Gtk,GLib,Pango
from .inline_pages import InlineDialog
from .installations import save_settings
from .ui_components import ActionButton,text
from . import switch_extract as sx

SWITCH_PORTS={'revivedx/savagewindrecomp','k0nl/b2recomp'}
# Ports that need the game updated to at least this version (the content-meta number and how people name it).
SWITCH_MINIMUM={'revivedx/savagewindrecomp':{'label':'1.9.0','version':1114112}}

def minimum_for(repository):return SWITCH_MINIMUM.get(str(repository).lower())

class SwitchMixin:
    def switch_convert_page(self,*_,on_done=None,minimum=None):
        """The conversion page. `on_done(folder)` is called with the converted folder, so a port's setup can use it right away.
        `minimum` ({'label','version'}) is the update the port needs: it asks for the base game and the update when they are separate files."""
        from .ports import Cancelled
        page=InlineDialog(title='Archivos del juego de Switch',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(10)
        body.pack_start(text('Convierte un XCI o NSP propio en la carpeta con exefs y romfs que piden algunos ports, como Breath of the Wild (Savage Wind) o Bayonetta 2.','muted',95),False,False,0)
        def choose_folder(_):
            if state['busy']:return
            path=self.pick_file('Elegir carpeta con exefs y romfs',folder=True)
            if not path:return
            try:folder=sx.extracted_folder(path)
            except ValueError as error:status.set_text(str(error));return
            if on_done:
                try:on_done(str(folder))
                except (OSError,ValueError) as error:status.set_text(str(error));return
                page.destroy()
            else:status.set_text('Carpeta lista: '+str(folder));self.toast('Carpeta de juego seleccionada')
        body.pack_start(ActionButton('Usar carpeta ya extraída','folder',choose_folder,'cyan'),False,False,0)
        body.pack_start(text('O convertir un archivo XCI/NSP','section-title'),False,False,0)
        if minimum:body.pack_start(text(f"Este port necesita el juego con la actualización {minimum['label']} o posterior. Si el archivo del juego no la incluye, elegir también el archivo de la actualización: se combinan al convertir.",'title',95),False,False,0)
        body.pack_start(text('Hace falta el prod.keys de la consola propia. Solo se lee en este equipo: no se copia ni se envía a ningún sitio.','meta',95),False,False,0)
        state={'game':'','update':'','keys':'','root':self.preferences.get('switch_root') or str(sx.default_root()),'busy':False,'alive':True,'cancel':None,'tool':sx.tool_path(self.store,self.preferences)}
        found=sx.find_keys(extra=[self.preferences.get('switch_keys') or ''])
        if found:state['keys']=found[0]
        values={}
        def row(key,title,caption,choose,optional=False):
            line=Gtk.Box(spacing=12);words=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2);words.pack_start(text(title,'title'),False,False,0)
            value=text('','muted',60);value.set_ellipsize(Pango.EllipsizeMode.END);value.set_line_wrap(False);words.pack_start(value,False,False,0);line.pack_start(words,True,True,0)
            control=ActionButton(caption,'folder',choose,'steam-outline');line.pack_end(control,False,False,0);body.pack_start(line,False,False,0);values[key]=value;return control
        def shown(path,empty):return pathlib.Path(path).name if path else empty
        def refresh():
            values['game'].set_text(shown(state['game'],'Ningún archivo elegido'));values['update'].set_text(shown(state['update'],'Sin actualización'))
            values['keys'].set_text(state['keys'] and ('Detectado: '+state['keys'] if state['keys'] in found else state['keys']) or 'No se encontró prod.keys: elegirlo')
            values['root'].set_text(state['root']+'/<ID del juego>')
            tool_state.set_text('Conversor incluido en Deck Library' if state['tool'] else 'El conversor se descargará automáticamente al convertir.')
            ready=bool(state['game'] and state['keys']) and not state['busy'];convert.set_sensitive(ready);cancel_button.set_visible(state['busy'])
        def pick(key,title,patterns,filter_name,folder=False):
            def choose(_):
                if state['busy']:return
                path=self.pick_file(title,folder=folder,patterns=patterns,filter_name=filter_name)
                if not path:return
                if key=='keys':
                    try:sx.check_keys(path)
                    except ValueError as error:status.set_text(str(error));return
                    self.preferences['switch_keys']=path;save_settings(self.preferences,self.store)
                if key=='root':self.preferences['switch_root']=path;save_settings(self.preferences,self.store)
                state[key]=path;status.set_text('');refresh()
            return choose
        row('game','Juego (XCI o NSP)','Elegir',pick('game','Elegir el XCI o NSP del juego',('*.xci','*.nsp'),'Juegos de Switch'))
        row('update','Actualización (si está en otro archivo)' if minimum else 'Actualización (opcional)','Elegir',pick('update','Elegir la actualización (NSP o XCI)',('*.nsp','*.xci'),'Actualizaciones de Switch'))
        row('keys','Claves (prod.keys)','Elegir',pick('keys','Elegir el archivo prod.keys',('*.keys',),'Claves'))
        row('root','Carpeta de destino','Cambiar',pick('root','Elegir la carpeta de destino',(),'',folder=True))
        tool_state=text('','muted',95);body.pack_start(tool_state,False,False,0)
        progress=Gtk.ProgressBar();progress.set_no_show_all(True);body.pack_start(progress,False,False,0)
        status=text('','status',95);status.set_selectable(True);body.pack_start(status,False,False,0)
        def set_status(message):
            if state['alive']:status.set_text(message);progress.pulse()
            return False
        def finish(result,error):
            state['busy']=False;progress.hide()
            if not state['alive']:return False
            if isinstance(error,Cancelled):status.set_text('Cancelado. No se modificó nada.')
            elif isinstance(error,sx.NeedsUpdate):status.set_text(str(error));self.toast('Falta la actualización')
            elif error:status.set_text(str(error))
            else:
                facts=[f"{result['files']} archivos",f"{result['size']/1024**3:.1f} GB"]+(['Incluye la actualización'] if result['update'] else [])
                status.set_text(result['path']+'\n'+' · '.join(facts)+('\nArchivos preparados para el port.' if on_done else '\nCarpeta extraída lista para usar.'));self.toast('Juego convertido')
                offer_cleanup(state['root'])
                if on_done:
                    folder=result['path']
                    try:on_done(folder)
                    except (OSError,ValueError) as error:status.set_text(str(error));refresh();return False
                    page.destroy();return False
            refresh();return False
        def offer_cleanup(root):
            """Conversions delete their own working files; this offers what a cancelled or replaced one left behind."""
            found=sx.leftovers(root)
            if not found:status.set_text(status.get_text()+'\nLos archivos temporales de la conversión ya se borraron.');return
            total=sum(size for _,size in found)
            if self.confirm('Recuperar espacio',f"Hay archivos temporales y copias de conversiones anteriores en {root} que ocupan {total/1024**3:.1f} GB. ¿Borrarlos? El juego convertido y los archivos originales no se tocan.",'Borrar'):
                freed=sx.clean(root);status.set_text(status.get_text()+f'\nSe liberaron {freed/1024**3:.1f} GB.')
        def run_convert(_):
            if state['busy']:return
            cancel=threading.Event();state.update(busy=True,cancel=cancel);progress.set_no_show_all(False);progress.show();status.set_text('Preparando…');refresh()
            game,update,keys,root,tool=state['game'],state['update'],state['keys'],state['root'],state['tool']
            if minimum and not update:status.set_text('Comprobando la versión del juego…')
            def work():
                try:
                    converter=tool or sx.fetch_nstool(self.store,progress=lambda line:GLib.idle_add(set_status,line),cancel=cancel)
                    state['tool']=converter
                    result=sx.Job(converter,keys,progress=lambda line:GLib.idle_add(set_status,line),cancel=cancel).convert(game,root,update or None,minimum);GLib.idle_add(finish,result,None)
                except Exception as error:GLib.idle_add(finish,None,error)
            threading.Thread(target=work,daemon=True).start()
        actions=Gtk.Box(spacing=10);body.pack_start(actions,False,False,0)
        convert=ActionButton('Convertir','play',run_convert,'play');actions.pack_start(convert,False,False,0)
        cancel_button=ActionButton('Cancelar','undo',lambda _:state['cancel'].set() if state['cancel'] else None,'danger');cancel_button.set_no_show_all(True);actions.pack_start(cancel_button,False,False,0)
        def closing(*_):
            state['alive']=False
            if state['cancel']:state['cancel'].set()
        page.connect('destroy',closing);page.connect('response',lambda *_:page.destroy())
        refresh();page._mount()
        return page
