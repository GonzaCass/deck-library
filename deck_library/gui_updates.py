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
        self.set_status('Actualizando Mario Kart Wii…')
        def work():
            try:tag=wiiupdate.update(item,info,image,lambda t:GLib.idle_add(self.set_status,t[-160:]))
            except Exception as error:GLib.idle_add(self.failed,str(error));return
            def done():
                self.toast('Mario Kart Wii actualizado a '+tag);self.set_status('Mario Kart Wii actualizado a '+tag+'.');self.check_updates(True);return False
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
        from .gui import label,button
        box=self.updates_box;self.reset_page(box)
        state=getattr(self,'update_state',None) or updates.cached(self.store)
        if not hasattr(self,'update_state'):self.update_state=state
        head=Gtk.Box(spacing=12);titles=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        titles.pack_start(label('Actualizaciones','hero'),False,False,0)
        checked=state.get('checked');titles.pack_start(label('Última búsqueda: '+(datetime.datetime.fromtimestamp(checked).strftime('%d/%m/%Y %H:%M') if checked else 'nunca'),'subtitle'),False,False,0)
        head.pack_start(titles,True,True,0);head.pack_end(button('Buscar ahora',lambda _:self.check_updates(True),True),False,False,0);box.pack_start(head,False,False,0)
        card=self.card(box,'Deck Library')
        installed=getattr(self,'update_installed',None);info=state.get('app')
        if installed:
            card.pack_start(label(f'Versión {installed} instalada. Reiniciar para usarla.'),False,False,0);card.pack_start(button('Reiniciar',lambda _:self.restart_app(),True),False,False,0)
        elif info:
            card.pack_start(label(f'Versión instalada {__version__} · disponible {info["version"]}'),False,False,0)
            if info['notes']:
                notes=label(info['notes'],'muted');notes.set_selectable(True);card.pack_start(notes,False,False,0)
            row=Gtk.Box(spacing=10)
            if info.get('archive') and info.get('checksum'):row.pack_start(button('Instalar actualización',lambda _:self.install_app_update(),True),False,False,0)
            else:card.pack_start(label('La publicación no incluye un paquete verificable; instalar manualmente.','muted'),False,False,0)
            if info.get('page'):row.pack_start(Gtk.LinkButton.new_with_label(info['page'],'Ver novedades'),False,False,0)
            card.pack_start(row,False,False,0)
        else:card.pack_start(label(f'Versión {__version__}. Sin actualizaciones pendientes.','muted'),False,False,0)
        card=self.card(box,'Ajustes recomendados')
        presets=state.get('presets')
        card.pack_start(label(f'{presets["count"]} perfiles en el catálogo · {presets["new"]} nuevos · {presets["changed"]} modificados en la última revisión' if presets else 'Catálogo sin revisar.','muted'),False,False,0)
        card=self.card(box,'Ports')
        ports=[item for item in self.pending_updates() if item[0] in ('port','catalog','wii')]
        if ports:
            for kind,text,data in ports:
                row=Gtk.Box(spacing=10);row.pack_start(label(text),True,True,0)
                if data.get('page'):row.pack_end(Gtk.LinkButton.new_with_label(data['page'],'Ver versión'),False,False,0)
                if kind=='catalog':row.pack_end(button('Actualizar',lambda _,d=data:self.update_catalog_port(d),True),False,False,0)
                if kind=='wii':row.pack_end(button('Actualizar aquí',lambda _:self.update_wiicompiled(),True),False,False,0)
                if kind=='port' and data.get('repository'):row.pack_end(button('Instalar la nueva versión aquí',lambda _,d=data:self.update_catalog_port(d),True),False,False,0)
                card.pack_start(row,False,False,0)
        else:card.pack_start(label('Los ports instalados están al día.','muted'),False,False,0)
        for error in state.get('errors') or []:card.pack_start(label('No se pudo consultar '+error,'status'),False,False,0)
        card=self.card(box,'Opciones')
        for key,text,default in (('check_updates','Buscar actualizaciones al abrir',True),('auto_update','Instalar automáticamente las actualizaciones de Deck Library',True),('catalog_auto','Actualizar los ajustes recomendados desde el catálogo',True),('auto_update_ports','Actualizar automáticamente los ports instalados desde el catálogo',False)):
            row=Gtk.Box(spacing=12);switch=Gtk.Switch();switch.set_active(self.preferences.get(key,default));switch.set_valign(Gtk.Align.CENTER)
            def changed(widget,_,key=key):self.preferences[key]=widget.get_active();save_settings(self.preferences,self.store)
            switch.connect('notify::active',changed);row.pack_start(label(text),True,True,0);row.pack_end(switch,False,False,0);card.pack_start(row,False,False,0)
        box.show_all();self.pages.set_visible_child_name('updates')
