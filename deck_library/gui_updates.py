"""Update checks, the updates page and self-update from the GTK interface."""
import datetime,os,pathlib,subprocess,sys,threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib
from .inline_pages import InlineFileChooser,InlineDialog
from . import __version__,motion,updates
from .installations import save_settings

def notes_preview(text,lines=3,width=110):
    """The first lines of the release notes, so the change summary is visible without opening anything."""
    rows=[]
    for row in str(text).splitlines():
        row=row.strip().lstrip('-*#• ').strip()
        if row:rows.append(row if len(row)<=width else row[:width-1].rstrip()+'…')
        if len(rows)>=lines:break
    return '\n'.join(rows)

class UpdatesMixin:
    def check_updates(self,force=False):
        """Run due checks off the GTK thread; `force` ignores the cache interval."""
        if getattr(self,'update_busy',False):return False
        self.update_busy=True;self.app_check_busy=True;self.refresh_update_badges()
        preferences=dict(self.preferences);entries=list(self.entries)
        def work():
            try:state=updates.check_all(self.store,preferences,entries,force=force,on_app=lambda state:GLib.idle_add(self.app_update_ready,state))
            except Exception as error:state={**updates.cached(self.store),'errors':[str(error)],'app_error':str(error)}
            GLib.idle_add(self.updates_ready,state,force)
        threading.Thread(target=work,daemon=True).start();return False

    def updates_ready(self,state,manual):
        if self.ui_closed:return False
        self.update_busy=False;self.app_update_ready(state)
        if self.preferences.get('auto_update_ports') and os.environ.get('DECK_LIBRARY_UI_PREVIEW')!='1':
            self.auto_port_queue=[('catalog',p) for p in state.get('catalog') or []]+([('project2099',state['project2099'])] if state.get('project2099') else [])
            self.run_next_auto_port()
        return False

    def app_update_ready(self,state):
        if self.ui_closed:return False
        state=updates.reconcile_ports(state,self.store)
        changed=state!=getattr(self,'update_state',None)
        self.app_check_busy=False;self.update_state=state;self.refresh_update_badges()
        if changed and self.pages.get_visible_child_name()=='updates' and not self.inline_workflows:self.updates_page()
        if state.get('app') and self.preferences.get('auto_update') and not getattr(self,'update_installed',None) and os.environ.get('DECK_LIBRARY_UI_PREVIEW')!='1':self.install_app_update(automatic=True)
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
            chooser=InlineFileChooser(title='Elegir la imagen PAL limpia de Mario Kart Wii (RMCP01)',transient_for=self,action=Gtk.FileChooserAction.OPEN);chooser.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Elegir',Gtk.ResponseType.OK)
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
        if hasattr(self,'shell_update_badge'):
            self.shell_update_badge.set_text(str(count));self.shell_update_badge.set_visible(False)
        state=getattr(self,'update_state',{}) or {}
        version='v'+__version__
        if getattr(self,'update_installed',None):version+=f' · Reabrir para {self.update_installed}'
        elif state.get('app'):version+=f' → {state["app"]["version"]} · Actualización disponible'
        elif getattr(self,'app_check_busy',False):version+=' · Buscando actualización'
        elif state.get('app_error'):version+=' · No se pudo comprobar'
        elif not self.preferences.get('check_updates',True):version+=' · Búsqueda automática desactivada'
        elif state.get('app_checked'):version+=' · Última versión'
        if hasattr(self,'version_label'):self.version_label.set_text(version)
        if getattr(self,'update_installed',None):
            self.banner_text.set_text(f'Deck Library {self.update_installed} instalada. Volver a abrirla para usarla.');self.banner_action.set_label('Cerrar y abrir de nuevo desde Steam' if motion.gaming_mode() else 'Volver a abrir');self.banner_action.show();self.update_banner.show()
        elif state.get('app'):
            self.banner_text.set_text(f'Deck Library {state["app"]["version"]} disponible.');self.banner_action.set_label('Ver actualización');self.banner_action.show();self.update_banner.show()
        elif self.pending_updates():
            n=len(self.pending_updates());self.banner_text.set_text(f'{n} actualización de ports disponible.' if n==1 else f'{n} actualizaciones de ports disponibles.');self.banner_action.set_label('Ver');self.banner_action.show();self.update_banner.show()
        elif state.get('app_error'):
            self.banner_text.set_text('No se pudo comprobar la actualización de Deck Library.');self.banner_action.set_label('Reintentar');self.banner_action.show();self.update_banner.show()
        else:self.update_banner.hide()
        if self.update_banner.get_visible() and getattr(self,'banner_dismissed','')==self.banner_text.get_text():self.update_banner.hide()
        if self.update_banner.get_visible() and not os.environ.get('DECK_LIBRARY_UI_TESTS'):
            if getattr(self,'_update_banner_timer',0):GLib.source_remove(self._update_banner_timer)
            self._update_banner_timer=GLib.timeout_add_seconds(5,lambda:(setattr(self,'_update_banner_timer',0),self.dismiss_banner(),False)[2])

    def banner_clicked(self):
        if getattr(self,'update_installed',None):self.restart_app()
        else:
            if (getattr(self,'update_state',{}) or {}).get('app_error'):self.check_updates(True)
            self.updates_page()

    def restart_app(self):
        if motion.gaming_mode():Gtk.main_quit();return  # a copy started from here would live outside Steam's session and stay without a window
        installed=pathlib.Path.home()/'Applications/DeckLibrary/launch.sh'
        launcher=installed if installed.is_file() else pathlib.Path(__file__).resolve().parent.parent/'launch.sh'
        subprocess.Popen([str(launcher)],start_new_session=True);Gtk.main_quit()

    def install_app_update(self,automatic=False):
        info=(getattr(self,'update_state',{}) or {}).get('app')
        if not info or getattr(self,'update_installing',False) or getattr(self,'update_installed',None)==info.get('version'):return
        if getattr(self,'port_busy',False) or getattr(self,'inline_workflows',[]):
            if automatic and not getattr(self,'app_update_retry',0):
                def retry():
                    if self.ui_closed:return False
                    if getattr(self,'port_busy',False) or getattr(self,'inline_workflows',[]):return True
                    self.app_update_retry=0;self.install_app_update(automatic=True);return False
                self.app_update_retry=GLib.timeout_add_seconds(2,retry);self.ui_sources.append(self.app_update_retry)
            elif not automatic:self.set_status('Finalizar la tarea actual antes de actualizar Deck Library.')
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
        from .ui_components import Reveal
        if not os.environ.get('DECK_LIBRARY_UI_TESTS'):self.dismiss_banner()
        box=self.updates_box;self.reset_page(box);state=getattr(self,'update_state',None) or updates.cached(self.store)
        head=Gtk.Box(spacing=14);head.pack_start(label('Actualizaciones','hero'),True,True,0);box.pack_start(head,False,False,0)
        checked=state.get('checked');meta_row=Gtk.Box(spacing=16);meta_row.pack_start(label('Última búsqueda: '+(datetime.datetime.fromtimestamp(checked).strftime('%d/%m/%Y %H:%M') if checked else 'sin revisar'),'meta'),False,False,0)
        meta_row.pack_start(label('Versión en uso: '+__version__,'meta'),False,False,0);box.pack_start(meta_row,False,False,0)
        info=state.get('app')
        if info:
            card=self.card(box,'Deck Library '+info['version']);card.pack_start(label(info.get('notes') or 'No hay notas disponibles para esta versión.','muted'),False,False,0)
            if getattr(self,'update_installed',None):head.pack_end(button('Cerrar y abrir de nuevo desde Steam' if motion.gaming_mode() else 'Volver a abrir para usar la versión instalada',lambda _:self.restart_app(),True),False,False,0)
            elif info.get('archive') and info.get('checksum'):head.pack_end(button('Actualizar Deck Library',lambda _:self.install_app_update(),True),False,False,0)
        else:
            head.set_no_show_all(True);head.hide()
        items=[item for item in self.pending_updates() if item[0] in ('port','catalog','wii')];seen=set();unique=[]
        for item in items:
            key=(item[2].get('repository') or item[2]['name']).lower()
            if key not in seen:seen.add(key);unique.append(item)
        box.pack_start(label('Ports · '+str(len(unique))+' actualizaciones','title'),False,False,0)
        if not unique:box.pack_start(label('No hay actualizaciones de ports en la última revisión.','muted'),False,False,0)
        active_keys={data.get('repository') or 'wiicompiled' for _,_,data in unique}
        for key,transfer in getattr(self,'transfers',{}).items():
            if key not in active_keys and transfer.state.get('phase') not in ('done','cancelled'):
                card=self.card(box,key.rsplit('/',1)[-1]);self.transfer_row(card,key)
        prefetched=[0]
        opened=getattr(self,'update_notes_open',set());self.update_notes_open=opened
        cache=getattr(self,'update_notes_cache',{});self.update_notes_cache=cache
        for kind,text,data in unique:
            card=self.card(box);row=Gtk.Box(spacing=16);card.pack_start(row,False,False,0);content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);row.pack_start(content,True,True,0);heading=Gtk.Box(spacing=12);content.pack_start(heading,False,False,0);actions=Gtk.Box(spacing=10);actions.set_valign(Gtk.Align.CENTER);actions.set_halign(Gtk.Align.END);row.pack_end(actions,False,False,0);entry=next((e for e in self.entries if normalized(e.name)==normalized(data['name'])),None)
            if entry:heading.pack_start(Poster(entry,find_cover(entry),44,66),False,False,0)
            title=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5);name=label(data['name'],'title');name.set_width_chars(1);title.pack_start(name,False,False,0);title.pack_start(label(str(data['installed'])+' → '+str(data['latest']),'meta'),False,False,0);heading.pack_start(title,True,True,0)
            if kind=='wii':actions.pack_end(button('Actualizar',lambda _:self.update_wiicompiled(),True),False,False,0)
            elif data.get('repository')==updates.PROJECT2099_REPO:actions.pack_end(button('Actualizar',lambda _:self.update_project2099(),True),False,False,0)
            elif data.get('repository'):actions.pack_end(button('Actualizar',lambda _,d=data:self.update_catalog_port(d),True),False,False,0)
            if data.get('page'):actions.pack_start(Gtk.LinkButton.new_with_label(data['page'],'Publicación original'),False,False,0)
            if data.get('repository')==updates.PROJECT2099_REPO:content.pack_start(label('Actualización con respaldo completo. Conserva partidas; el cambio de motor deja los mods y ajustes anteriores en la copia de seguridad.','muted'),False,False,0)
            self.transfer_row(content,'wiicompiled' if kind=='wii' else data.get('repository') or 'wiicompiled')
            note_key=(data.get('repository') or kind,str(data['latest']))
            initial=cache.get(note_key,updates.notes_text(data.get('notes','')))
            notes=label(initial or 'Abrir para consultar las notas del autor.','muted');notes.set_selectable(True);notes.set_width_chars(1);notes.set_max_width_chars(95);notes.set_margin_top(8)
            # A bounded notes area keeps the disclosure header within reach on
            # the Deck, even when a release has many pages of changes.
            notes_scroll=self.new_scroll();notes_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
            notes_scroll.set_propagate_natural_height(True);notes_scroll.set_min_content_height(110);notes_scroll.set_max_content_height(220);notes_scroll.add(notes)
            disclosure=Reveal('Novedades de '+str(data['latest']),notes_scroll)
            disclosure.get_style_context().add_class('update-expander');content.pack_start(disclosure,False,False,0)
            disclosure.revealer.set_transition_type(Gtk.RevealerTransitionType.NONE)
            loaded=[bool(initial)];alive=[True]
            disclosure.connect('destroy',lambda *_,alive=alive:alive.__setitem__(0,False))
            def load_notes(data=data,target=notes,loaded=loaded,alive=alive,key=note_key):
                if loaded[0]:return
                loaded[0]=True;target.set_text('Consultando las notas…')
                def work():
                    try:body=updates.notes_text(updates.release_notes(data)) or 'Esta versión no incluye novedades escritas por el autor. Consultar la publicación original.'
                    except Exception as error:body='No se pudieron descargar las notas: '+str(error)
                    def show():
                        if not self.ui_closed:
                            cache[key]=body
                            if alive[0]:target.set_text(body);self.refresh_layout()
                        return False
                    GLib.idle_add(show)
                threading.Thread(target=work,daemon=True).start()
            def expanded(widget,_,key=note_key,load=load_notes):
                if widget.get_reveal_child():opened.add(key);load()
                else:opened.discard(key)
                self.refresh_layout()
            disclosure.revealer.connect('notify::reveal-child',expanded)
            if note_key in opened:disclosure.control.clicked()
            if not loaded[0] and prefetched[0]<6:prefetched[0]+=1;load_notes()
        for error in state.get('errors') or []:box.pack_start(label('No se pudo consultar '+error,'status'),False,False,0)
        self.pin_page_header(box,head)
        box.show_all();self.pages.set_visible_child_name('updates')

    def update_settings_page(self,*_):
        from .ui_components import text
        page=InlineDialog(title='Actualizaciones automáticas',transient_for=self)
        page.add_button('Volver',Gtk.ResponseType.CLOSE)
        for key,caption,default in (('check_updates','Buscar al abrir',True),('auto_update','Actualizar Deck Library automáticamente',True),('auto_update_ports','Actualizar ports automáticamente',False),('catalog_auto','Mantener el catálogo de ajustes actualizado',True),('community_ratings','Consultar valoraciones comunitarias por juego',True)):
            row=Gtk.Box(spacing=16);row.set_margin_top(8);row.set_margin_bottom(8)
            name=text(caption);name.set_width_chars(1);row.pack_start(name,True,True,0)
            control=Gtk.Switch();control.set_valign(Gtk.Align.CENTER);control.set_active(self.preferences.get(key,default));control.get_accessible().set_name(caption)
            def changed(widget,_,key=key):
                self.preferences[key]=widget.get_active();save_settings(self.preferences,self.store)
                if key=='check_updates' and widget.get_active():self.check_updates()
            control.connect('notify::active',changed);row.pack_end(control,False,False,0);page.content.pack_start(row,False,False,0)
        page.connect('response',lambda *_:page.destroy());page._mount();return page

    def run_next_auto_port(self):
        if getattr(self,'port_busy',False) or getattr(self,'iso_cleanup_active',None) or not getattr(self,'auto_port_queue',[]):return False
        kind,data=self.auto_port_queue.pop(0)
        if kind=='project2099':self.update_project2099(automatic=True)
        else:self.update_catalog_port(data)
        if not getattr(self,'port_busy',False):GLib.idle_add(self.run_next_auto_port)
        return False

    def update_project2099(self,automatic=False):
        from . import project2099_update,ports
        if getattr(self,'port_busy',False):self.set_status('Ya hay una instalación en curso.');return
        entry=next((e for e in self.entries if e.metadata.get('adapter')=='project2099'),None)
        if not entry:return
        source=project2099_update.source_for(entry,self.entries)
        if not source and automatic:self.set_status('Project-2099 necesita indicar la copia original para actualizarse.');return
        if not source:
            chooser=InlineFileChooser(title='Elegir la copia Xbox 360 de Edge of Time',transient_for=self,action=Gtk.FileChooserAction.OPEN,patterns=('*.iso','*.zip','*.7z'),filter_name='ISO, ZIP o 7z');chooser.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Elegir',Gtk.ResponseType.OK)
            if chooser.run()==Gtk.ResponseType.OK:source=chooser.get_filename()
            chooser.destroy()
            if not source:return
        key=updates.PROJECT2099_REPO
        if not hasattr(self,'port_jobs'):self.port_jobs={}
        cancel=threading.Event();self.port_jobs[key]=cancel;self.port_busy=True;self.start_transfer(key);progress=self.port_progress(key)
        def finished(result,error):
            self.port_jobs.pop(key,None);self.port_busy=False;self.finish_transfer(key,error)
            GLib.idle_add(self.run_next_auto_port)
            if result:
                from .models import atomic_json
                cached=updates.cached(self.store);cached['project2099']=None;atomic_json(updates.cache_path(self.store),cached)
                self.update_state['project2099']=None;self.refresh_update_badges();self.discover();self.set_status('Project-2099 actualizado a '+result['version']+'. Copia anterior conservada en '+result['backup'])
            return False
        def work():
            try:
                release=ports.release_for(key);result=project2099_update.update(entry,source,release,self.store,progress,cancel);GLib.idle_add(finished,result,None)
            except Exception as error:GLib.idle_add(finished,None,str(error))
        threading.Thread(target=work,daemon=True).start()
