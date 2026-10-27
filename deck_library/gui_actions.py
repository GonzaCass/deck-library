"""Library actions and background work, independent of the window layout."""
import json,os,pathlib,shlex,subprocess,sys,threading,re
from gi.repository import Gtk,GLib,Pango
from .inline_pages import InlineDialog,InlineFileButton
from .models import Store,Entry
from .discovery import scan,available_emulators,nice_name,SYSTEMS
from .runtime import diagnostics,clean_environment
from .service import queue_entries,queue_removals,queue_controllers
from .installations import settings,save_settings,report
from .gui import label,button,Banner

class ActionsMixin:
    def reset_page(self,box):
        for child in box.get_children():box.remove(child)
    def toast(self,text):self.toast_widget.show_text(text)
    def poll_sync(self):
        notice=self.store.root/'launch-notice.json'
        if notice.is_file():
            reading=notice.with_name('launch-notice-reading.json')
            try:
                notice.replace(reading);value=json.loads(reading.read_text());reading.unlink()
                if isinstance(value,dict) and isinstance(value.get('message'),str):self.message('No se pudo iniciar el juego',value['message'])
            except (OSError,ValueError):pass
        path=self.store.root/'last-sync.json'
        try:
            if path.exists() and path.stat().st_mtime>self.last_sync_seen:
                value=json.loads(path.read_text());self.last_sync_seen=path.stat().st_mtime;self.set_status(self.sync_summary(value));self.toast(self.sync_summary(value));self.discover()
        except (OSError,ValueError):pass
        self.refresh_pending();return True
    def sync_summary(self,value):
        if value.get('state')=='failed':return 'No se pudieron aplicar los cambios de Steam: '+value.get('error','')
        parts=[]
        if value.get('shortcuts'):parts.append(f'{len(value["shortcuts"])} accesos guardados')
        if value.get('removed'):parts.append(f'{len(value["removed"])} accesos quitados')
        if value.get('layouts'):parts.append(f'layout de mando asignado a {len(value["layouts"])}')
        return (', '.join(parts) or 'Cambios guardados').capitalize()+'. Abrir Steam para verlos.'
    def set_status(self,text):
        self.status.set_text(text);self.status.set_visible(bool(text))
        ident=getattr(self,'status_timer',0)
        if ident:GLib.source_remove(ident);self.status_timer=0
        if text and not getattr(self,'ui_closed',False):self.status_timer=GLib.timeout_add_seconds(7,self.clear_status)
        if hasattr(self,'toast_widget') and re.search(r'guardad|aplicad|actualizad|instalad|configurad|restaurad|exportad|importad|cancelad|descartad|no se pudo|no se pudieron|falló|error',text,re.I):self.toast(text)
    def clear_status(self):
        self.status_timer=0;self.status.set_text('');self.status.set_visible(False);return False
    def message(self,title,text):
        page=InlineDialog(title=title,transient_for=self);page.get_content_area().pack_start(label(text,'subtitle'),False,False,0);page.add_button('Volver',Gtk.ResponseType.CLOSE);page.connect('response',lambda *_:page.destroy());page._mount()
    def confirm(self,title,text,accept='Continuar',danger=False):
        dialog=InlineDialog(title=title,transient_for=self);dialog.get_content_area().pack_start(label(text,'subtitle'),False,False,0);dialog.add_button('Cancelar',Gtk.ResponseType.CANCEL)
        action=dialog.add_button(accept,Gtk.ResponseType.OK)
        if danger:action.get_style_context().add_class('danger')
        else:action.get_style_context().add_class('primary')
        self.fit_dialog(dialog);dialog.show_all();response=dialog.run();dialog.destroy();return response==Gtk.ResponseType.OK
    def offer_deck_controls(self,entry):
        """After a setting is applied to a Switch game, offer to map Eden's player 1 to the Deck when it is not."""
        from . import eden_controls,presets
        from .installations import save_settings
        try:
            if presets.adapter_for(entry)!='eden':return
            state=eden_controls.status(self.preferences.get('eden_config') or None)
        except (OSError,ValueError):return
        if state=='ok' or self.preferences.get('eden_controls_declined')==state:return
        text=('Eden no tiene mapeados los controles de la Steam Deck.' if state=='missing' else 'Eden usa otro dispositivo para el jugador 1, no los controles de la Steam Deck.')+'\nActualizar el mando del jugador 1 con los controles de la Deck (se guarda una copia de qt-config.ini)?'
        if self.confirm('Mando de la Steam Deck en Eden',text,'Actualizar mando'):
            try:backup=eden_controls.apply(self.preferences.get('eden_config') or None);self.toast('Mando de la Deck actualizado en Eden')
            except Exception as error:self.message('No se pudo actualizar el mando',str(error))
        else:self.preferences['eden_controls_declined']=state;save_settings(self.preferences,self.store)
    def discover(self):
        if self.discover_busy:return False
        self.discover_busy=True;self.set_status('Buscando juegos e instalaciones…');preferences=dict(self.preferences)
        def work():
            try:
                found=report(preferences=preferences);from .steam_inventory import merge_steam
                from . import ports
                ports.maintain(self.store)
                merged=self.store.merge(scan(preferences=preferences),overwrite=False);entries=merge_steam(merged);self.store.save(entries);GLib.idle_add(self.discovered,entries,found)
            except Exception as error:GLib.idle_add(self.discovery_failed,str(error))
        threading.Thread(target=work,daemon=True).start();return False
    def discovery_failed(self,text):
        if getattr(self,'explicit_rescan',False):self.explicit_rescan=False;self.rescan_button.set_sensitive(True);self.rescan_button.set_label('Buscar instalados')
        self.discover_busy=False;self.set_status('La búsqueda no se completó: '+text)
        if self.pages.get_visible_child_name()=='welcome' and self.wizard_step==1:self.wizard_report_label.set_text('La búsqueda falló. Revisar las rutas y repetirla.');self.wizard_continue.set_sensitive(True)
        return False
    def discovered(self,entries,found=None):
        if getattr(self,'explicit_rescan',False):self.explicit_rescan=False;self.rescan_button.set_sensitive(True);self.rescan_button.set_label('Buscar instalados');self.toast('Biblioteca actualizada')
        self.discover_busy=False;self.entries=entries
        if self.selected:self.selected=next((e for e in entries if e.id==self.selected.id),None)
        self.checked&={e.id for e in entries}
        self.refresh_platforms();self.library_dirty=True
        if self.pages.get_visible_child_name()=='library':self.render()
        elif self.pages.get_visible_child_name()=='home':self.home_page()
        self.set_status(f'{len(entries)} juegos encontrados.');self.wizard_detection_ready(found or report(preferences=self.preferences))
        if self.pages.get_visible_child_name()=='detail':
            if self.selected:self.show_detail(self.selected)
            else:self.pages.set_visible_child_name('library')
        if self.pages.get_visible_child_name()!='welcome':self.fetch_covers()
        return False
    def refresh_platforms(self):
        self.platform_picker.handler_block_by_func(self.filter_changed);self.platform_picker.remove_all();self.platform_picker.append('all','Todas las plataformas')
        for platform in sorted({e.platform for e in self.shown_entries()[0]}):self.platform_picker.append(platform,platform)
        self.platform_picker.set_active_id(self.platform_filter)
        if self.platform_picker.get_active_id() is None:self.platform_filter='all';self.platform_picker.set_active_id('all')
        self.platform_picker.handler_unblock_by_func(self.filter_changed)
    def filter_changed(self,picker):self.platform_filter=picker.get_active_id() or 'all';self.animate_next=True;self.render()
    def in_steam(self,e):return e.metadata.get('steam_appid') is not None and not e.metadata.get('steam_store')
    def toggle(self,check,id_):
        if check.get_active():self.checked.add(id_)
        else:self.checked.discard(id_)
        self.update_selection()
    def select_visible(self):
        ids={e.id for e in self.visible()}
        if ids and ids.issubset(self.checked):self.checked-=ids
        else:self.checked|=ids
        self.selection_mode=True;self.render()
    def on_select(self,list_,row):
        if row and hasattr(row,'entry'):self.select_game(row.entry)
    def clear_detail(self):self.reset_page(self.detail)
    def show_empty_detail(self):self.clear_detail()
    def single_steam(self,e):
        if e.metadata.get('steam_store'):
            self.message('Juego de Steam','Este juego ya forma parte de la biblioteca de Steam.');return
        if not self.accounts:self.message('Steam sin sesión','Iniciar sesión en Steam para preparar el acceso.');return
        self.add_to_steam([e])
    def controller_summary(self,e):
        """Short text about the saved gamepad layouts for this shortcut."""
        from . import controllers
        try:state=controllers.status(pathlib.Path(e.metadata['steam_account']),e.metadata['steam_appid'])
        except (OSError,ValueError,KeyError):return 'No se pudo leer la configuración de mandos de Steam.'
        if not state:return 'Steam no tiene plantillas de mando disponibles para este acceso.'
        missing=[controllers.FAMILY_NAMES[f] for f,value in state.items() if value is None]
        return 'Layout de gamepad asignado a todos los tipos de mando.' if not missing else 'Sin layout para: '+', '.join(missing)+'. Esos mandos no se detectan en el juego.'
    def steam_banner(self,e):
        """The shortcut's hero (and logo) from Steam's grid folder, or None."""
        from . import steamart
        if not self.in_steam(e) or not e.metadata.get('steam_account'):return None
        try:art=steamart.existing(pathlib.Path(e.metadata['steam_account']),e.metadata['steam_appid'])
        except (OSError,ValueError,TypeError):return None
        if not art.get('hero'):return None
        return Banner(str(art['hero']),str(art['logo']) if art.get('logo') else None)
    def set_mods(self,toggle,e):
        e.mods=toggle.get_active();self.store.save(self.entries);self.set_status('Perfil guardado. Se aplica en la próxima ejecución del juego.')
    def play(self,e):
        if e.kind=='steam' or e.metadata.get('steam_override') or self.in_steam(e):
            from .steam_inventory import game_uri
            uri='steam://run/'+str(e.metadata['steam_appid']) if e.metadata.get('steam_store') else game_uri(e.metadata['steam_appid'])
            subprocess.Popen(['steam',uri],env=clean_environment());self.set_status('Abriendo '+e.name+' desde Steam…');return
        self.store.save(self.entries);subprocess.Popen([sys.executable,str(pathlib.Path(__file__).resolve().parent.parent/'app.py'),'launch',e.id,'--data-dir',str(self.store.root)],env=clean_environment(),start_new_session=True)
        self.set_status('Abriendo '+e.name+'. Si falla, el diagnóstico muestra el motivo.')
    def check(self,e):
        self.set_status('Revisando '+e.name+'…')
        def work():
            issues,log=diagnostics(e,self.store);GLib.idle_add(self.show_diagnostic,e,issues,log)
        threading.Thread(target=work,daemon=True).start()
    def show_diagnostic(self,e,issues,log):
        dialog=InlineDialog(title='Diagnóstico · '+e.name,transient_for=self,modal=True);dialog.set_default_size(850,530);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(20);box.pack_start(label('\n'.join(issues) if issues else 'Rutas y programa disponibles. Esto no garantiza la compatibilidad del juego.','subtitle'),False,False,12)
        scroll=self.new_scroll();view=Gtk.TextView();view.set_editable(False);view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);view.get_buffer().set_text(log or 'Sin registro todavía. Ejecutar el juego y volver a revisar.');scroll.add(view);box.pack_start(scroll,True,True,0)
        self.fit_dialog(dialog);dialog.show_all();dialog.run();dialog.destroy();self.set_status('Diagnóstico revisado.');return False
    def current_account(self):return self.accounts[self.account.get_active()] if self.accounts else None
    def run_queue(self,job,busy_text):
        """Run a queue operation off the GTK thread and report through `queue_done`."""
        self.add_button.set_sensitive(False);self.set_status(busy_text)
        def work():
            try:result=job();GLib.idle_add(self.queue_done,result)
            except Exception as error:GLib.idle_add(self.failed,str(error))
        threading.Thread(target=work,daemon=True).start()
    def add_to_steam(self,selected_entries=None):
        entries=selected_entries if selected_entries is not None else [e for e in self.entries if e.id in self.checked]
        if not entries or not self.accounts:return
        account=self.accounts[self.account.get_active()]
        def job():
            for entry in entries:
                if entry.kind=='steam' or entry.metadata.get('steam_override'):continue
                issues,_=diagnostics(entry,self.store)
                blocking=[i for i in issues if i.startswith(('No se encuentra','El programa no tiene','Un ejecutable Windows','Falta el entorno'))]
                if blocking:raise ValueError(entry.name+': '+'\n'.join(blocking))
            return queue_entries(entries,account,self.store)
        self.run_queue(job,'Preparando los accesos de Steam…')
    def remove_from_steam(self,entries=None):
        entries=entries if entries is not None else [e for e in self.entries if e.id in self.checked]
        targets=[e for e in entries if self.in_steam(e)]
        if not targets:self.message('Sin accesos','Ningún juego seleccionado tiene acceso guardado en Steam.');return
        accounts={e.metadata['steam_account'] for e in targets}
        if len(accounts)>1:self.message('Varias cuentas','Los accesos pertenecen a cuentas de Steam distintas. Quitarlos por separado.');return
        names=', '.join(e.name for e in targets[:4])+(f' y {len(targets)-4} más' if len(targets)>4 else '')
        if not self.confirm('Quitar de Steam',f'{names}\n\nSe elimina el acceso de la biblioteca de Steam, junto con su carátula y su layout de mando. El juego, sus archivos y sus partidas no se modifican. Antes de guardar se crea un respaldo de la lista de accesos.','Quitar',danger=True):return
        account=pathlib.Path(accounts.pop());ids=[e.metadata['steam_appid'] for e in targets]
        self.run_queue(lambda:queue_removals(ids,account,self.store),'Preparando la eliminación de accesos…')
    def fix_controllers(self,e):
        if not self.in_steam(e):self.message('Mando','Agregar primero el juego a Steam.');return
        if not self.confirm('Asignar layout de mando','Se asigna el layout de gamepad de Steam a este acceso para DualSense, DualShock, Xbox, Switch Pro y mandos genéricos, reemplazando el layout que tuviera cada tipo. Los cambios se guardan con Steam cerrado.','Asignar'):return
        account=pathlib.Path(e.metadata['steam_account']);self.run_queue(lambda:queue_controllers([e.metadata['steam_appid']],account,self.store),'Preparando el layout de mando…')
    def queue_done(self,result):
        self.add_button.set_sensitive(True);self.update_selection()
        if result['state']=='idle':self.set_status('Sin cambios.');return False
        if result['state']=='pending':
            self.refresh_pending();self.set_status('Cambio en espera: se guardará cuando Steam se cierre.');self.toast('Se aplicará al cerrar Steam o al iniciar la próxima sesión.')
        else:
            self.set_status('Cambios guardados. Abrir Steam para verlos.');self.toast('Cambios guardados en Steam');self.discover()
        return False
    def failed(self,text):self.add_button.set_sensitive(True);self.message('No se pudo guardar',text);self.set_status('La biblioteca de Steam no se modificó.');return False
    def manual(self,existing=None):
        if existing and existing.kind=='steam':self.steam_edit_dialog(existing);return
        dialog=InlineDialog(title='Editar juego' if existing else 'Agregar un juego',transient_for=self,modal=True);dialog.set_default_size(650,510);dialog.add_button('Cancelar',Gtk.ResponseType.CANCEL);dialog.add_button('Guardar',Gtk.ResponseType.OK)
        box=dialog.get_content_area();box.set_border_width(22);box.set_spacing(12)
        kind=Gtk.ComboBoxText();kinds=['Port o app de Linux','Juego emulado','Comando personalizado']
        for k in kinds:kind.append_text(k)
        kind.set_active(1 if existing and existing.kind=='emulated' else 2 if existing else 0);box.pack_start(label('Tipo','muted'),False,False,0);box.pack_start(kind,False,False,0)
        name=Gtk.Entry();name.set_placeholder_text('Nombre en Steam');name.set_text(existing.name if existing else '');box.pack_start(name,False,False,0)
        file_=InlineFileButton(title='Elegir juego o programa',action=Gtk.FileChooserAction.OPEN);file_.set_hexpand(True)
        if existing and existing.source:file_.set_filename(existing.source)
        def chosen(widget):
            path=widget.get_filename()
            if path and not name.get_text():name.set_text(nice_name(pathlib.Path(path)))
        file_.connect('file-set',chosen);box.pack_start(file_,False,False,0)
        emulator=Gtk.ComboBoxText();emus=available_emulators(preferences=self.preferences);keys=list(emus)
        for key in keys:emulator.append_text(emus[key]['name'])
        if keys:emulator.set_active(0)
        emulator_label=label('Emulador','muted');box.pack_start(emulator_label,False,False,0);box.pack_start(emulator,False,False,0)
        custom=Gtk.Entry();custom.set_placeholder_text('/ruta/launcher --opcion "ruta del juego"')
        if existing:custom.set_text(shlex.join(existing.command))
        public_id=Gtk.Entry();public_id.set_placeholder_text('Title ID, ID de Wii o identificador del port');public_id.set_text(existing.game_id if existing else '')
        advanced=Gtk.Expander(label='Identificador del juego (opcional)');advanced.add(public_id);box.pack_start(advanced,False,False,0)
        custom_label=label('Comando del launcher','muted');box.pack_start(custom_label,False,False,0);box.pack_start(custom,False,False,0)
        def update_fields(*args):
            file_.set_visible(kind.get_active()!=2)
            emulator.set_visible(kind.get_active()==1);emulator_label.set_visible(kind.get_active()==1)
            custom.set_visible(kind.get_active()==2);custom_label.set_visible(kind.get_active()==2)
        kind.connect('changed',update_fields);update_fields()
        box.pack_start(label('Cualquier emulador se agrega con un comando personalizado. Los archivos de Windows necesitan un launcher de Wine o Proton.','muted'),False,False,0)
        self.fit_dialog(dialog);dialog.show_all();update_fields()
        while dialog.run()==Gtk.ResponseType.OK:
            try:
                filename=file_.get_filename();type_=kind.get_active();platform='Linux'
                if type_==0:
                    if not filename:raise ValueError('Elegir el programa que se va a abrir.')
                    command=[filename];entry_kind='port'
                elif type_==1:
                    if not filename or not keys:raise ValueError('Elegir el juego y un emulador instalado.')
                    key=keys[emulator.get_active()];command=emus[key]['command']+emus[key]['flags']+[filename];entry_kind='emulated'
                    platform=next(v[0] for v in SYSTEMS.values() if v[1]==key)
                else:
                    command=shlex.split(custom.get_text());entry_kind='custom';filename=filename or '';platform=existing.platform if existing else 'Personalizado'
                e=Entry(name.get_text().strip(),command,entry_kind,platform,filename or '',mods=existing.mods if existing else True,id=existing.id if existing else '',game_id=public_id.get_text().strip(),cover=existing.cover if existing else '',metadata={**(existing.metadata if existing else {}),'manual_command':True})
                if existing:self.entries=[e if item.id==existing.id else item for item in self.entries];self.store.save(self.entries)
                else:self.entries=self.store.merge([e])
                self.selected=e;self.refresh_platforms();self.render();self.show_detail(e);self.pages.set_visible_child_name('detail');self.fetch_covers();self.set_status('Juego guardado.');break
            except Exception as error:self.message('Datos incorrectos',str(error))
        dialog.destroy()
