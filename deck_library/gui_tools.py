"""Installation, content and portable preset dialogs for the GTK library."""
import json,pathlib,shlex,subprocess,sys,threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib
from .installations import settings,save_settings,report
from .models import atomic_json
from . import presets
from .content import switch_inventory,install_nsp,install_mod_zip,nsp_identity,switch_id

class ToolsMixin:
    def gtaiv_dialog(self,e):
        from .gui import label,button
        from . import gtaiv
        dialog=Gtk.Dialog(title='Arreglo de GTA IV',transient_for=self,modal=True)
        dialog.set_default_size(760,520);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(22);box.set_spacing(14)
        box.pack_start(label('GTA IV · FusionFix 4.0.5','title'),False,False,0)
        box.pack_start(label('Confirmado por un usuario en Steam Deck OLED el 01/10/2026: el juego funcionó bien después de estos cambios. No hay una medición de FPS sostenidos.','subtitle'),False,False,0)
        box.pack_start(label('• Instala FusionFix 4.0.5 oficial con respaldo completo.\n• Usa DXVK 2.6.2 y latencia máxima de un cuadro.\n• Activa VSync de DXVK y apaga el del juego.\n• Conserva tus gráficos y límite de FPS (60 en una instalación nueva).\n• Muestra botones de PlayStation.\n\nCerrá el juego antes de aplicar. Descarga aproximadamente 172 MB la primera vez. El juego queda cerrado.','muted'),False,False,0)
        doc=pathlib.Path(__file__).resolve().parent.parent/'docs/GTAIV.md'
        box.pack_start(button('Leer instructivo',lambda _:subprocess.Popen(['xdg-open',str(doc)],start_new_session=True)),False,False,0)
        status=label('Listo para aplicar.','muted');box.pack_start(status,False,False,0)
        row=Gtk.Box(spacing=12);box.pack_start(row,False,False,0)
        active=[False];buttons=[]
        def finish(result,error):
            active[0]=False
            for control in buttons:control.set_sensitive(True)
            dialog.set_deletable(True);dialog.set_response_sensitive(Gtk.ResponseType.CLOSE,True)
            status.set_text(('No se pudo completar: '+error) if error else 'Listo. Respaldo: '+result)
            return False
        def run(action):
            if active[0]:return
            config=e.metadata.get('gtaiv_settings')
            if action=='apply' and not config:
                config=self.pick_file('Elegir SETTINGS.CFG de GTA IV')
                if not config:return
                e.metadata['gtaiv_settings']=config;self.store.save(self.entries)
            active[0]=True
            for control in buttons:control.set_sensitive(False)
            dialog.set_deletable(False);dialog.set_response_sensitive(Gtk.ResponseType.CLOSE,False)
            status.set_text('Descargando, respaldando y aplicando…' if action=='apply' else 'Restaurando respaldo…')
            def work():
                try:
                    result=gtaiv.apply(e.metadata['gtaiv_root'],config,self.store) if action=='apply' else gtaiv.restore(e.metadata['gtaiv_root'],self.store)
                    GLib.idle_add(finish,result,None)
                except Exception as exc:GLib.idle_add(finish,None,str(exc))
            threading.Thread(target=work,daemon=True).start()
        for title,action in [('Aplicar arreglo de GTA IV','apply'),('Restaurar respaldo','restore')]:
            control=button(title,lambda _,a=action:run(a),tone='presets');buttons.append(control);row.pack_start(control,True,True,0)
        dialog.show_all()
        while True:
            dialog.run()
            if not active[0]:break
        dialog.destroy()

    def pick_file(self,title,save=False):
        dialog=Gtk.FileChooserDialog(title=title,transient_for=self,action=Gtk.FileChooserAction.SAVE if save else Gtk.FileChooserAction.OPEN)
        dialog.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Guardar' if save else 'Elegir',Gtk.ResponseType.OK)
        if save:dialog.set_do_overwrite_confirmation(True);dialog.set_current_name('preset.json')
        result=dialog.get_filename() if dialog.run()==Gtk.ResponseType.OK else None;dialog.destroy();return result
    def choose_cover(self,e):
        path=self.pick_file('Elegir carátula local')
        if path:
            try:
                from gi.repository import GdkPixbuf
                GdkPixbuf.Pixbuf.new_from_file_at_scale(path,150,185,True)
                e.cover=path;e.metadata.pop('artwork',None);self.store.save(self.entries);self.render();self.set_status('Carátula guardada para '+e.name+'.')
            except GLib.Error:self.message('Carátula','Elegí un archivo de imagen compatible.')
    def installation_dialog(self):
        from .gui import label,button
        dialog=Gtk.Dialog(title='Instalaciones y rutas',transient_for=self,modal=True);dialog.set_default_size(850,650);dialog.add_button('Cancelar',Gtk.ResponseType.CANCEL);dialog.add_button('Guardar y buscar',Gtk.ResponseType.OK)
        scroll=Gtk.ScrolledWindow();box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);box.set_border_width(20);scroll.add(box);dialog.get_content_area().pack_start(scroll,True,True,0)
        found=report(preferences=self.preferences);deck=found['emudeck']
        box.pack_start(label(('EmuDeck detectado' if deck['installed'] else 'No se detectó EmuDeck. Elegí carpetas y emuladores instalados.')+'\nBiblioteca: '+deck['roms'],'title'),False,False,0)
        box.pack_start(label('Agregá rutas si usás una microSD, otra carpeta de Quiver o una instalación portátil. Una carpeta por línea.','muted'),False,False,0)
        buffers={}
        for key,title in [('rom_roots','Bibliotecas de ROMs (carpeta que contiene switch, wii, ps2…)'),('port_roots','Carpetas de ports'),('quiver_roots','Instalaciones de Quiver (carpeta con Apps)'),('prism_roots','Datos de Prism Launcher (carpeta con prismlauncher.cfg)'),('wiicompiled_roots','Datos de WiiCompiled (carpeta con Config.toml / Install)')]:
            row=Gtk.Box(spacing=8);row.pack_start(label(title),True,True,0)
            view=Gtk.TextView();view.set_size_request(-1,60);view.get_buffer().set_text('\n'.join(self.preferences.get(key,[])));buffers[key]=view.get_buffer()
            def choose(_,buffer=buffers[key]):
                picker=Gtk.FileChooserDialog(title='Elegir carpeta',transient_for=dialog,action=Gtk.FileChooserAction.SELECT_FOLDER);picker.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Agregar carpeta',Gtk.ResponseType.OK)
                if picker.run()==Gtk.ResponseType.OK:
                    current=buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True).strip();buffer.set_text(current+('\n' if current else '')+picker.get_filename())
                picker.destroy()
            row.pack_end(button('Agregar carpeta',choose),False,False,0);box.pack_start(row,False,False,0);box.pack_start(view,False,False,0)
        config=Gtk.Entry();config.set_text(self.preferences.get('eden_config',''));config.set_placeholder_text(str(pathlib.Path.home()/'.config/eden'));box.pack_start(label('Configuración de Eden (qt-config.ini)'),False,False,0);box.pack_start(config,False,False,0)
        row=Gtk.Box(spacing=8);row.pack_start(label('Emuladores instalados','title'),True,True,0);box.pack_start(row,False,False,0)
        emulator_commands=dict(self.preferences.get('emulators',{}));from .discovery import SYSTEMS
        used=set()
        for name,slug,flags,extensions in SYSTEMS.values():
            if slug in used:continue
            used.add(slug);row=Gtk.Box(spacing=10);program=found['emulators'].get(slug);text=Gtk.Label(label=name+' — '+(shlex.join(program['command']) if program else 'No detectado'),xalign=0);text.set_line_wrap(True);row.pack_start(text,True,True,0)
            def choose(_,key=slug,title=name,widget=text):
                path=self.pick_file('Elegir programa de '+title)
                if path:emulator_commands[key]=[path];widget.set_text(title+' — '+path)
            row.pack_end(button('Elegir programa',choose),False,False,0);box.pack_start(row,False,False,0)
        dialog.show_all()
        if dialog.run()==Gtk.ResponseType.OK:
            for key,buffer in buffers.items():self.preferences[key]=list(dict.fromkeys(str(pathlib.Path(p.strip()).expanduser()) for p in buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True).splitlines() if p.strip()))
            self.preferences['emulators']=emulator_commands;self.preferences['eden_config']=config.get_text().strip();save_settings(self.preferences,self.store);self.discover()
        dialog.destroy()
    def preset_dialog(self,e):
        if e.metadata.get('gtaiv_root'):return self.gtaiv_dialog(e)
        from .gui import label,button
        dialog=Gtk.Dialog(title='Ajustes recomendados · '+e.name,transient_for=self,modal=True);dialog.set_default_size(880,640);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(18);box.set_spacing(12)
        box.pack_start(label(e.name,'title'),False,False,0)
        box.pack_start(label('Los cambios se muestran antes de aplicar. Se guarda una copia de seguridad. Cada perfil indica su estado de validación.','muted'),False,False,0)
        toolbar=Gtk.Box(spacing=8);box.pack_start(toolbar,False,False,0)
        panes=Gtk.Box(spacing=16);box.pack_start(panes,True,True,0)
        list_=Gtk.ListBox();scroll=Gtk.ScrolledWindow();scroll.set_size_request(300,-1);scroll.add(list_);panes.pack_start(scroll,False,False,0)
        detail_scroll=Gtk.ScrolledWindow();detail_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);detail_scroll.get_style_context().add_class('preset-detail');detail=label('Seleccionar un preset','subtitle');detail.set_valign(Gtk.Align.START);detail.set_max_width_chars(43);detail_scroll.add(detail);panes.pack_start(detail_scroll,True,True,0)
        selected=[None];items=[p for p in presets.catalog(self.store) if presets.compatible(e,p)]
        def fill():
            for row in list_.get_children():list_.remove(row)
            for value in items:
                row=Gtk.ListBoxRow();row.value=value;card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5);card.set_border_width(12);name=label(value['name'],'title');name.set_max_width_chars(25);card.pack_start(name,False,False,0)
                status={'proposal':'Para probar','boot-tested':'Arranque comprobado','user-confirmed':'Confirmado por usuario'}[value['tested']['status']]
                meta=label(value['author']+' · '+status+' · '+', '.join(value['adapter']['versions']),'muted');meta.set_max_width_chars(30);card.pack_start(meta,False,False,0);row.add(card);list_.add(row)
            if not items:list_.add(label('Todavía no hay un preset compatible. Importá uno o exportá tus ajustes actuales.','muted'))
            list_.show_all()
            if items:list_.select_row(list_.get_row_at_index(0))
        def chosen(_,row):
            selected[0]=getattr(row,'value',None)
            value=selected[0]
            detail.set_text((value['objective']+'\n'+value.get('notes','')) if value else '')
        list_.connect('row-selected',chosen)
        def import_(_):
            path=self.pick_file('Importar preset JSON')
            if path:
                try:
                    value=presets.import_preset(path,self.store)
                    if not presets.compatible(e,value):raise ValueError('Se importó, pero corresponde a otro juego/programa.')
                    items[:]=[p for p in presets.catalog(self.store) if presets.compatible(e,p)];fill()
                except Exception as error:self.message('Preset',str(error))
        def export_(_):
            form=Gtk.Dialog(title='Exportar mis ajustes',transient_for=dialog,modal=True);form.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Exportar',Gtk.ResponseType.OK);body=form.get_content_area();body.set_border_width(18);body.set_spacing(10)
            name=Gtk.Entry();name.set_text(e.name+' — mis ajustes');author=Gtk.Entry();author.set_placeholder_text('Alias público (sin cuenta ni correo)');body.pack_start(name,False,False,0);body.pack_start(author,False,False,0);body.pack_start(label('Solo opciones permitidas. Se exporta como propuesta con licencia MIT; revisá el contenido antes de compartirlo.','muted'),False,False,0);form.show_all()
            if form.run()==Gtk.ResponseType.OK:
                try:
                    value=presets.export_current(e,name.get_text().strip(),author.get_text().strip(),self.store,self.preferences.get('eden_config') or None);path=self.pick_file('Guardar preset portable',save=True)
                    if path:atomic_json(path,value);presets.import_preset(path,self.store);items[:]=[p for p in presets.catalog(self.store) if presets.compatible(e,p)];fill();detail.set_text('JSON exportado. Compartilo o agregalo al catálogo del repositorio.')
                except Exception as error:self.message('No se pudo exportar',str(error))
            form.destroy()
        def refresh(_):
            form=Gtk.Dialog(title='Catálogo de GitHub',transient_for=dialog,modal=True);form.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Descargar catálogo',Gtk.ResponseType.OK);entry=Gtk.Entry();entry.set_placeholder_text('https://raw.githubusercontent.com/usuario/repo/main/presets/catalog.json');entry.set_text(self.preferences.get('catalog_url',''));form.get_content_area().pack_start(entry,False,False,15);form.set_default_size(700,130);form.show_all()
            response=form.run();url=entry.get_text().strip();form.destroy()
            if response==Gtk.ResponseType.OK:
                self.preferences['catalog_url']=url;save_settings(self.preferences,self.store);detail.set_text('Descargando catálogo…')
                def work():
                    try:
                        count=presets.refresh_catalog(url,self.store)
                        def done():items[:]=[p for p in presets.catalog(self.store) if presets.compatible(e,p)];fill();detail.set_text(str(count)+' presets descargados y validados.');return False
                        GLib.idle_add(done)
                    except Exception as error:GLib.idle_add(self.message,'No se pudo descargar',str(error))
                threading.Thread(target=work,daemon=True).start()
        toolbar.pack_start(button('Importar JSON',import_),False,False,0);toolbar.pack_start(button('Exportar mis ajustes',export_),False,False,0);toolbar.pack_start(button('Catálogo GitHub',refresh),False,False,0)
        actions=Gtk.Box(spacing=8);box.pack_start(actions,False,False,0)
        def apply_(_):
            value=selected[0]
            if not value:self.message('Elegí un preset','Seleccioná un perfil de la lista.');return
            try:
                path,changes=presets.preview(e,value,self.preferences.get('eden_config') or None)
                confirm=Gtk.MessageDialog(transient_for=dialog,modal=True,buttons=Gtk.ButtonsType.OK_CANCEL,text='¿Aplicar '+value['name']+'?');confirm.format_secondary_text('\n'.join(f'{key}: {old} → {new}' for key,old,new in changes)+'\n\nPrograma: '+value['adapter']['id']+' · versiones declaradas: '+', '.join(value['adapter']['versions'])+'\nSe guarda una copia de seguridad. No instala actualizaciones ni mods.');response=confirm.run();confirm.destroy()
                if response==Gtk.ResponseType.OK:
                    result=presets.apply(e,value,self.store,self.preferences.get('eden_config') or None);detail.set_text(str(result['changes'])+' ajustes aplicados.')
            except Exception as error:self.message('No se pudo aplicar',str(error))
        def restore_(_):
            try:presets.restore(e,self.store);detail.set_text('Se restauró el ajuste anterior.')
            except Exception as error:self.message('Restaurar ajuste',str(error))
        def feedback_(_):
            value=selected[0]
            if not value:return
            form=Gtk.Dialog(title='Comentarios locales',transient_for=dialog,modal=True);form.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Guardar comentarios',Gtk.ResponseType.OK);body=form.get_content_area();body.set_border_width(18);body.set_spacing(10);choice=Gtk.ComboBoxText()
            for key,title in [('works','Me funcionó'),('issues','Tuve problemas'),('not-tested','Todavía no lo probé')]:choice.append(key,title)
            choice.set_active(0);notes=Gtk.Entry();notes.set_placeholder_text('Qué juego probaste y qué notaste (sin datos privados)');body.pack_start(choice,False,False,0);body.pack_start(notes,False,False,0);form.set_default_size(650,180);form.show_all()
            if form.run()==Gtk.ResponseType.OK:
                report=presets.feedback(e,value,choice.get_active_id(),notes.get_text(),self.store);destination=self.pick_file('Exportar comentarios',save=True)
                if destination:atomic_json(destination,report)
                detail.set_text('Comentarios guardados localmente.')
            form.destroy()
        actions.pack_start(button('Aplicar preset',apply_,tone='play'),False,False,0);actions.pack_start(button('Restaurar anterior',restore_,tone='content'),False,False,0);actions.pack_start(button('Exportar comentarios',feedback_,tone='controls'),False,False,0)
        fill();dialog.show_all();dialog.run();dialog.destroy()
    def content_dialog(self,e):
        from .gui import label,button
        dialog=Gtk.Dialog(title='Contenido de Switch · '+e.name,transient_for=self,modal=True);dialog.set_default_size(870,620);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(12);status=label('Leyendo contenido…','muted');box.pack_start(status,False,False,0);scroll=Gtk.ScrolledWindow();rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);scroll.add(rows);box.pack_start(scroll,True,True,0)
        def fill():
            inventory=switch_inventory(e,config_dir=self.preferences.get('eden_config') or None)
            for child in rows.get_children():rows.remove(child)
            rows.pack_start(label('Base: '+('disponible' if inventory['base']['available'] else 'falta el archivo')+' · Title ID: '+(inventory['title_id'] or 'No identificado'),'title'),False,False,0)
            rows.pack_start(label('Versión base: '+inventory['base']['version'],'muted'),False,False,0)
            cached=pathlib.Path.home()/'.cache/eden/game_list'/((inventory['title_id'] or 'unknown')+'.pv.txt')
            if cached.exists():rows.pack_start(label('Último contenido detectado por Eden:\n'+cached.read_text()[:1000],'muted'),False,False,0)
            for kind,title in [('updates','Actualizaciones'),('dlc','DLC')]:
                rows.pack_start(label(title+' ('+str(len(inventory[kind]))+')','title'),False,False,0)
                for item in inventory[kind]:
                    row=Gtk.Box(spacing=8);text=label(item['name']+'\n'+('Instalado en NAND' if item['installed'] else 'Archivo disponible; no registrado por Deck Library'));text.set_max_width_chars(65);row.pack_start(text,True,True,0)
                    if not item['installed']:
                        def install_(_,path=item['path']):self.install_content_job([path],status,fill,e)
                        row.pack_end(button('Instalar en Eden',install_),False,False,0)
                    rows.pack_start(row,False,False,0)
            rows.pack_start(label('Mods ('+str(len(inventory['mods']))+') · '+('activados para este acceso' if e.mods else 'desactivados para comparar'),'title'),False,False,0)
            for item in inventory['mods']:rows.pack_start(label(item['name']),False,False,0)
            rows.show_all();status.set_text('Los archivos originales y las partidas se conservan. Cerrá Eden antes de instalar.')
        controls=Gtk.FlowBox();controls.set_selection_mode(Gtk.SelectionMode.NONE);controls.set_max_children_per_line(2);controls.set_min_children_per_line(1);box.pack_start(controls,False,False,0)
        def choose_nsp(_):
            path=self.pick_file('Elegir actualización o DLC (NSP)')
            if path:self.install_content_job([path],status,fill,e)
        def all_(_):
            inventory=switch_inventory(e,config_dir=self.preferences.get('eden_config') or None);paths=[p['path'] for kind in ('updates','dlc') for p in inventory[kind] if not p['installed']]
            self.install_content_job(paths,status,fill,e)
        controls.add(button('Elegir actualización / DLC',choose_nsp));controls.add(button('Instalar los pendientes',all_))
        def base_(_):
            path=self.pick_file('Elegir juego base NSP / XCI')
            if path:
                if pathlib.Path(path).suffix.lower() not in ('.nsp','.xci'):self.message('Archivo base','Elegí un NSP o XCI.');return
                e.source=path;e.cwd=str(pathlib.Path(path).parent)
                if '-g' in e.command:e.command[e.command.index('-g')+1]=path
                else:e.command[-1]=path
                self.store.save(self.entries);fill();self.render()
        controls.add(button('Elegir juego base',base_))
        def mod_(_):
            path=self.pick_file('Elegir mod LayeredFS ZIP')
            if path:
                status.set_text('Preparando mod…')
                def work():
                    try:install_mod_zip(path,e,self.store,self.preferences.get('eden_config') or None);GLib.idle_add(fill)
                    except Exception as error:GLib.idle_add(self.message,'No se pudo instalar el mod',str(error))
                threading.Thread(target=work,daemon=True).start()
        controls.add(button('Elegir mod ZIP',mod_))
        fill();dialog.show_all();dialog.run();dialog.destroy()
    def install_content_job(self,paths,status,done,entry=None):
        if not paths:status.set_text('No hay contenido pendiente.');return
        status.set_text('Preparando instalación…')
        def work():
            try:
                for path in paths:
                    identity=nsp_identity(path)
                    if entry and identity['base_id'] and identity['base_id']!=switch_id(entry):raise ValueError('Este NSP corresponde a otro juego; no se instaló.')
                    if identity['kind']=='base':raise ValueError('Seleccioná una actualización o un DLC; para la base usá Elegir juego base.')
                    install_nsp(path,self.preferences.get('eden_config') or None,lambda text:GLib.idle_add(status.set_text,text))
                GLib.idle_add(done)
            except Exception as error:GLib.idle_add(self.message,'Contenido de Eden',str(error));GLib.idle_add(status.set_text,'No se completó la instalación. Revisá el mensaje.')
        threading.Thread(target=work,daemon=True).start()
    def layout_dialog(self,e):
        from .gui import label,button
        dialog=Gtk.Dialog(title='Controles recomendados · Minecraft',transient_for=self,modal=True);dialog.set_default_size(700,570);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE);box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(12)
        from .steam_input import local_profiles
        profiles=local_profiles(e)
        if profiles:
            profile=profiles[0];box.pack_start(label('Perfil guardado: '+profile['title'],'title'),False,False,0)
            summary=Gtk.ScrolledWindow();summary.set_size_request(-1,210);text=Gtk.TextView();text.set_editable(False);text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);text.get_buffer().set_text('\n'.join(control+' → '+action for control,action in profile['bindings'])+'\nModos: '+', '.join(profile['modes']));summary.add(text);box.pack_start(summary,True,True,0)
            box.pack_start(label('Steam conserva este perfil. El botón inferior abre sus controles; los cambios se hacen allí.','muted'),False,False,0)
        layout=next((p['layout'] for p in presets.catalog(self.store) if presets.compatible(e,p) and p.get('layout')),None)
        if layout and not profiles:
            box.pack_start(label('Steam Input · Teclado (WASD) y ratón','title'),False,False,0);box.pack_start(label('\n'.join(k+' → '+v for k,v in layout['bindings'].items())),True,True,0);box.pack_start(label(layout.get('notes',''),'muted'),False,False,0)
        elif not profiles:box.pack_start(label('No se encontró un perfil local. Agregá un preset con controles para esta instancia.'),False,False,0)
        def open_(_):
            from .steam import read_kv,get
            if not self.accounts:return
            try:
                shortcuts=read_kv((self.accounts[self.account.get_active()]/'shortcuts.vdf').read_bytes())['shortcuts'][1]
                item=next(v[1] for v in shortcuts.values() if get(v[1],'appid')==e.metadata.get('steam_appid') or get(v[1],'appname')==e.name);appid=get(item,'appid');subprocess.Popen(['steam','steam://controllerconfig/'+str(appid)])
                self.set_status('Controles abiertos en Steam.')
            except (OSError,ValueError,StopIteration):self.message('Agregá primero la instancia','Guardá su acceso en Steam para abrir la configuración de controles.')
        box.pack_start(button('Abrir controles en Steam',open_,True),False,False,0);dialog.show_all();dialog.run();dialog.destroy()
    def setup_wii_dialog(self):
        from .gui import label,button
        from .setup_wii import install,check_image
        dialog=Gtk.Dialog(title='Preparar Mario Kart WiiCompiled',transient_for=self,modal=True);dialog.set_default_size(780,590);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE);box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(15)
        box.pack_start(label('Tu imagen → recompilar → optimizar → Steam','title'),False,False,0)
        box.pack_start(label('Elegí Mario Kart Wii PAL limpio RMCP01. Se descarga el setup oficial 0.2.33 y el SDK si falta. Requiere unos 20 GB temporales y puede tardar bastante. No sobrescribe la instalación que ya funciona.','muted'),False,False,0)
        image=Gtk.FileChooserButton(title='Elegir imagen de Mario Kart Wii',action=Gtk.FileChooserAction.OPEN);box.pack_start(image,False,False,0)
        setup=Gtk.FileChooserButton(title='Setup oficial existente (opcional)',action=Gtk.FileChooserAction.OPEN);box.pack_start(label('Opcional: elegir el setup oficial ya descargado','muted'),False,False,0);box.pack_start(setup,False,False,0)
        status=label('Elegí la imagen y comenzá.','status');box.pack_start(status,True,True,0);cancel=threading.Event();busy=[False]
        def start(_):
            try:check_image(image.get_filename() or '')
            except Exception as error:self.message('Imagen de Wii',str(error));return
            if busy[0]:return
            cancel.clear();chosen_image=image.get_filename();chosen_setup=setup.get_filename()
            busy[0]=True;start_button.set_sensitive(False);stop.set_sensitive(True)
            def work():
                try:
                    install(chosen_image,self.store,chosen_setup,lambda text:GLib.idle_add(status.set_text,text),cancel)
                    GLib.idle_add(self.finish_wii_setup,status)
                except Exception as error:GLib.idle_add(status.set_text,str(error)+'\nRegistro local: '+str(self.store.root/'wii-setup/install.log'))
                finally:busy[0]=False;GLib.idle_add(start_button.set_sensitive,True);GLib.idle_add(stop.set_sensitive,False)
            threading.Thread(target=work,daemon=True).start()
        actions=Gtk.Box(spacing=10);start_button=button('Preparar y optimizar',start,True);stop=button('Cancelar proceso',lambda _:cancel.set());stop.set_sensitive(False);actions.pack_start(start_button,False,False,0);actions.pack_start(stop,False,False,0);box.pack_start(actions,False,False,0)
        dialog.show_all();dialog.run()
        if busy[0]:cancel.set()
        dialog.destroy()
    def finish_wii_setup(self,status):
        self.preferences=settings(self.store);self.entries=self.store.load();self.refresh_platforms();self.render();status.set_text('Listo. Mario Kart Wii está en tu biblioteca: seleccionalo y agregalo a Steam.');return False
