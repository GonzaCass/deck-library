"""Update checks, the updates page and self-update from the GTK interface."""
import datetime,os,pathlib,subprocess,sys,threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib
from . import __version__,updates
from .installations import save_settings

class UpdatesMixin:
    def check_updates(self,force=False):
        """Run due checks off the GTK thread; `force` ignores the cache interval."""
        if getattr(self,'update_busy',False):return False
        self.update_busy=True;self.refresh_update_badges()
        preferences=dict(self.preferences);entries=list(self.entries)
        def work():
            try:state=updates.check_all(self.store,preferences,entries,force=force)
            except Exception as error:state={**updates.cached(self.store),'errors':[str(error)]}
            GLib.idle_add(self.updates_ready,state,force)
        threading.Thread(target=work,daemon=True).start();return False

    def updates_ready(self,state,manual):
        self.update_busy=False;self.update_state=state;self.refresh_update_badges()
        if state.get('app') and self.preferences.get('auto_update') and not getattr(self,'update_installed',None):self.install_app_update(automatic=True)
        if self.preferences.get('auto_update_ports') and state.get('catalog'):
            for port in state['catalog']:self.update_catalog_port(port)
        if manual and self.pages.get_visible_child_name()=='updates':self.updates_page()
        return False

    def update_catalog_port(self,data):
        from . import ports
        known=ports.merged(getattr(self,'catalog_apps',None) or ports.catalog(self.store),self.preferences)
        item=next((a for a in known if a['repository']==data['repository']),None) or {'name':data['name'],'repository':data['repository']}
        self.install_port(item,True)

    def update_wiicompiled(self):
        from . import wiiupdate
        found=wiiupdate.installations(self.preferences)
        if not found:self.message('WiiCompiled','No se encontró una instalación de WiiCompiled administrada por Quiver.');return
        item=found[0];info=wiiupdate.latest()
        if not info:self.message('WiiCompiled','No se pudo consultar la última versión.');return
        image=wiiupdate.find_image(self.entries)
        if not image:
            chooser=Gtk.FileChooserDialog(title='Elegir la imagen PAL limpia de Mario Kart Wii (RMCP01)',transient_for=self,action=Gtk.FileChooserAction.OPEN);chooser.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Elegir',Gtk.ResponseType.OK)
            if chooser.run()==Gtk.ResponseType.OK:image=chooser.get_filename()
            chooser.destroy()
            if not image:return
        if not self.confirm('Actualizar Mario Kart Wii',f'Se descarga el setup oficial {info["tag"]} (suma SHA-256 verificada) y se vuelve a compilar el juego con la imagen del disco. Necesita unos 20 GB libres y tarda varios minutos; cerrar el juego antes. Si algo falla, se restaura el setup anterior.','Actualizar'):return
        self.set_status('Actualizando Mario Kart Wii…');self.start_transfer('wiicompiled');progress=self.port_progress('wiicompiled')
        def work():
            try:tag=wiiupdate.update(item,info,image,progress,transfer=progress)
            except Exception as error:
                GLib.idle_add(self.finish_transfer,'wiicompiled',str(error));GLib.idle_add(self.failed,str(error));return
            def done():
                self.finish_transfer('wiicompiled');self.toast('Mario Kart Wii actualizado a '+tag);self.set_status('Mario Kart Wii actualizado a '+tag+'.');self.check_updates(True);return False
            GLib.idle_add(done)
        threading.Thread(target=work,daemon=True).start()

    def pending_updates(self):return updates.summary(getattr(self,'update_state',{}) or {})

    def refresh_update_badges(self):
        count=len(self.pending_updates())+(1 if getattr(self,'update_installed',None) else 0);self.banner_text.show()
        self.update_badge.set_text(str(count));self.update_badge.set_visible(count>0)
        state=getattr(self,'update_state',{}) or {}
        if getattr(self,'update_installed',None):
            self.banner_text.set_text(f'Deck Library {self.update_installed} instalada. Reiniciar para usarla.');self.banner_action.set_label('Reiniciar');self.banner_action.show();self.update_banner.show()
        elif state.get('app'):
            self.banner_text.set_text(f'Deck Library {state["app"]["version"]} disponible.');self.banner_action.set_label('Ver actualización');self.banner_action.show();self.update_banner.show()
        elif self.pending_updates():
            n=len(self.pending_updates());self.banner_text.set_text(f'{n} actualización de ports disponible.' if n==1 else f'{n} actualizaciones de ports disponibles.');self.banner_action.set_label('Ver');self.banner_action.show();self.update_banner.show()
        else:self.update_banner.hide()

    def banner_clicked(self):
        if getattr(self,'update_installed',None):self.restart_app()
        else:self.updates_page()

    def restart_app(self):
        installed=pathlib.Path.home()/'Applications/DeckLibrary/launch.sh'
        launcher=installed if installed.is_file() else pathlib.Path(__file__).resolve().parent.parent/'launch.sh'
        subprocess.Popen([str(launcher)],start_new_session=True);Gtk.main_quit()

    def install_app_update(self,automatic=False):
        info=(getattr(self,'update_state',{}) or {}).get('app')
        if not info or getattr(self,'update_installing',False):return
        if os.environ.get('SteamAppId') or os.environ.get('SteamGameId'):
            if not automatic:self.message('Actualización','Abrir Deck Library desde el modo Escritorio para instalar la actualización.')
            return
        self.update_installing=True;self.set_status(f'Instalando Deck Library {info["version"]}…')
        def work():
            try:version=updates.install_update(info,self.store,lambda text:GLib.idle_add(self.set_status,text));GLib.idle_add(self.update_installed_ok,version)
            except Exception as error:GLib.idle_add(self.update_failed,str(error))
        threading.Thread(target=work,daemon=True).start()

    def update_installed_ok(self,version):
        self.update_installing=False;self.update_installed=version;self.set_status(f'Deck Library {version} instalada.');self.refresh_update_badges()
        if self.pages.get_visible_child_name()=='updates':self.updates_page()
        return False

    def update_failed(self,text):
        self.update_installing=False;self.set_status('No se pudo instalar la actualización.');self.message('Actualización',text);return False

    def updates_page(self):
        from .gui import label,button,wrap_row,Poster
        from .artwork import find_cover,normalized
        box=self.updates_box;self.reset_page(box);state=getattr(self,'update_state',None) or updates.cached(self.store)
        head=Gtk.Box(spacing=14);head.pack_start(label('Actualizaciones','hero'),True,True,0);head.pack_end(button('Buscar actualizaciones',lambda _:self.check_updates(True),True),False,False,0);box.pack_start(head,False,False,0)
        checked=state.get('checked');box.pack_start(label('Última búsqueda: '+(datetime.datetime.fromtimestamp(checked).strftime('%d/%m/%Y %H:%M') if checked else 'sin revisar'),'meta'),False,False,0)
        from .service import pending_changes
        waiting=pending_changes(self.store)
        if waiting:
            row=Gtk.Box(spacing=12);row.get_style_context().add_class('banner');row.pack_start(label(waiting[0]['description'] if len(waiting)==1 else str(len(waiting))+' cambios de Steam pendientes'),True,True,0);row.pack_end(button('Ver detalle',lambda _:self.pending_details()),False,False,0);box.pack_start(row,False,False,0)
        info=state.get('app')
        if info:
            card=self.card(box,'Deck Library '+info['version']);card.pack_start(label(info.get('notes') or 'No hay notas disponibles para esta versión.','muted'),False,False,0)
            if info.get('archive') and info.get('checksum'):card.pack_start(button('Actualizar Deck Library',lambda _:self.install_app_update(),True),False,False,0)
        items=[item for item in self.pending_updates() if item[0] in ('port','catalog','wii')];seen=set();unique=[]
        for item in items:
            key=(item[2].get('repository') or item[2]['name']).lower()
            if key not in seen:seen.add(key);unique.append(item)
        box.pack_start(label('Ports · '+str(len(unique))+' actualizaciones','title'),False,False,0)
        if not unique:box.pack_start(label('No hay actualizaciones de ports en la última revisión.','muted'),False,False,0)
        active_keys={data.get('repository') or 'wiicompiled' for _,_,data in unique}
        for key in getattr(self,'transfers',{}):
            if key not in active_keys:
                card=self.card(box,key.rsplit('/',1)[-1]);self.transfer_row(card,key)
        for kind,text,data in unique:
            card=self.card(box);row=Gtk.Box(spacing=16);card.pack_start(row,False,False,0);entry=next((e for e in self.entries if normalized(e.name)==normalized(data['name'])),None)
            if entry:row.pack_start(Poster(entry,find_cover(entry),44,66),False,False,0)
            title=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5);title.pack_start(label(data['name'],'title'),False,False,0);title.pack_start(label(str(data['installed'])+' → '+str(data['latest']),'meta'),False,False,0);row.pack_start(title,True,True,0)
            if kind=='wii':row.pack_end(button('Actualizar',lambda _:self.update_wiicompiled(),True),False,False,0)
            elif data.get('repository') and data['repository']!=updates.PROJECT2099_REPO:row.pack_end(button('Actualizar',lambda _,d=data:self.update_catalog_port(d),True),False,False,0)
            if data.get('page'):row.pack_end(Gtk.LinkButton.new_with_label(data['page'],'Publicación original'),False,False,0)
            self.transfer_row(card,'wiicompiled' if kind=='wii' else data.get('repository') or 'wiicompiled')
            expander=Gtk.Expander(label='Novedades de '+str(data['latest']));notes=label(updates.notes_text(data.get('notes','')) or 'Abrir para consultar las notas del autor.','muted');notes.set_selectable(True);notes.set_max_width_chars(95);notes.set_margin_top(12);expander.add(notes);card.pack_start(expander,False,False,0)
            loaded=['notes' in data]
            if loaded[0] and not data.get('notes'):notes.set_text('Esta fuente no incluye notas para la versión. Podés consultar la publicación original.')
            def expanded(widget,_,data=data,target=notes,loaded=loaded):
                if not widget.get_expanded() or loaded[0]:return
                loaded[0]=True;target.set_text('Consultando las notas…')
                def work():
                    try:body=updates.notes_text(updates.release_notes(data)) or 'No se encontraron notas para esta versión. Consultá la publicación original.'
                    except Exception as error:body='No se pudieron descargar las notas: '+str(error)
                    GLib.idle_add(target.set_text,body)
                threading.Thread(target=work,daemon=True).start()
            expander.connect('notify::expanded',expanded)
        options=Gtk.Expander(label='Opciones de actualización');settings_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);options.add(settings_box);box.pack_start(options,False,False,0)
        for key,text,default in (('check_updates','Buscar al abrir',True),('auto_update','Actualizar Deck Library automáticamente',True),('catalog_auto','Mantener el catálogo de ajustes actualizado',True),('community_ratings','Consultar valoraciones comunitarias por juego',True),('auto_update_ports','Actualizar ports automáticamente',False)):
            check=Gtk.CheckButton(label=text);check.set_active(self.preferences.get(key,default))
            def changed(widget,key=key):self.preferences[key]=widget.get_active();save_settings(self.preferences,self.store)
            check.connect('toggled',changed);settings_box.pack_start(check,False,False,0)
        for error in state.get('errors') or []:box.pack_start(label('No se pudo consultar '+error,'status'),False,False,0)
        box.show_all();self.pages.set_visible_child_name('updates')
