"""Guided onboarding and artwork selection for the redesigned library."""
import pathlib,threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib,GdkPixbuf
from .installations import report,save_settings
from . import cover_provider

class ExperienceMixin:
    def provider_fields(self,box):
        from .gui import label
        box.pack_start(label('Proveedor de carátulas','title'),False,False,0)
        box.pack_start(label('Automático usa SteamGridDB si agregás una clave; si no, busca en Libretro y Wikipedia. Podés elegir otra imagen después.','muted'),False,False,0)
        combo=Gtk.ComboBoxText()
        for key,name in [('automatic','Automático · recomendado'),('libretro','Libretro · consolas clásicas'),('wikipedia','Wikipedia · sin cuenta'),('steamgriddb','SteamGridDB · carátulas 600 × 900'),('off','Solo imágenes locales')]:combo.append(key,name)
        combo.set_active_id(self.preferences.get('artwork_provider','automatic'));box.pack_start(combo,False,False,0)
        key=Gtk.Entry();key.set_visibility(False);key.set_placeholder_text('Clave API de SteamGridDB (opcional)');key.set_text(self.preferences.get('steamgriddb_key',''));box.pack_start(key,False,False,0)
        link=Gtk.LinkButton.new_with_label('https://www.steamgriddb.com/profile/preferences/api','Obtener mi clave en SteamGridDB');box.pack_start(link,False,False,0)
        box.pack_start(label('La clave queda en esta Deck. Al buscar se envía el nombre del juego al proveedor; las imágenes se guardan localmente.','muted'),False,False,0)
        return combo,key

    def settings_page(self):
        from .gui import label,button
        self.reset_page(self.settings_box)
        self.settings_box.pack_start(label('Ajustes','hero'),False,False,0)
        self.settings_box.pack_start(label('Instalaciones, carátulas y apariencia.','subtitle'),False,False,0)
        panel=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14);panel.get_style_context().add_class('card');self.settings_box.pack_start(panel,False,False,0)
        combo,key=self.provider_fields(panel)
        animations=Gtk.Switch();animations.set_active(self.preferences.get('animations',True));row=Gtk.Box(spacing=12);row.pack_start(label('Animaciones y transiciones'),True,True,0);row.pack_end(animations,False,False,0);panel.pack_start(row,False,False,0)
        def save(_):
            if combo.get_active_id()=='steamgriddb' and not key.get_text().strip():self.message('Falta la clave','Agregá tu clave o elegí Automático / Wikipedia.');return
            self.preferences.update(artwork_provider=combo.get_active_id(),steamgriddb_key=key.get_text().strip(),animations=animations.get_active());save_settings(self.preferences,self.store);self.apply_motion();self.artwork_attempted.clear();self.set_status('Preferencias guardadas.');self.fetch_covers()
        panel.pack_start(button('Guardar y completar carátulas',save,True),False,False,0)
        row=Gtk.Box(spacing=12)
        row.pack_start(button('Instalaciones y carpetas',lambda _:self.installation_dialog()),False,False,0)
        row.pack_start(button('Repetir asistente inicial',lambda _:self.start_wizard()),False,False,0)
        self.settings_box.pack_start(row,False,False,0);self.settings_box.show_all();self.pages.set_visible_child_name('settings')

    def start_wizard(self):
        self.wizard_step=0;self.wizard_found=None;self.wizard_checks={};self.checked.clear();self.selection_mode=False;self.draw_wizard();self.wizard_box.show();self.pages.set_visible_child_name('welcome');return False
    def draw_wizard(self):
        from .gui import label,button
        stack=self.wizard_box;box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);stack.add(box)
        steps=['Bienvenida','Detectar','Carátulas','Listo para Steam'];progress=Gtk.Box(spacing=12)
        for index,title in enumerate(steps):
            item=label(f'{index+1}  {title}','pill' if index==self.wizard_step else 'muted');progress.pack_start(item,True,True,0)
        box.pack_start(progress,False,False,0)
        body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16);body.set_hexpand(True);body.set_vexpand(True);box.pack_start(body,True,True,8)
        footer=Gtk.Box(spacing=12);box.pack_end(footer,False,False,0)
        if self.wizard_step==0:
            body.pack_start(label('Configuración inicial','welcome-title'),False,False,12)
            body.pack_start(label('Detectar instalaciones, configurar carátulas y preparar accesos a Steam.','subtitle'),False,False,0)
            for title,text in [('01  Detectar juegos','EmuDeck, emuladores, ports de Quiver y instancias de Prism.'),('02  Configurar carátulas','Carátulas automáticas y ajustes recomendados por juego.'),('03  Agregar a Steam','Seleccionar juegos y preparar sus accesos.')]:
                card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);card.get_style_context().add_class('card');card.pack_start(label(title,'title'),False,False,0);card.pack_start(label(text,'muted'),False,False,0);body.pack_start(card,False,False,0)
            footer.pack_end(button('Empezar →',lambda _:self.wizard_next(),True),False,False,0)
            footer.pack_start(button('Ahora no',lambda _:self.leave_wizard(False)),False,False,0)
        elif self.wizard_step==1:
            body.pack_start(label('Juegos detectados','hero'),False,False,0)
            body.pack_start(label('Marcá los juegos que querés llevar a Steam. Si falta algo, agregá su carpeta.','subtitle'),False,False,0)
            self.wizard_report_label=label('Buscando EmuDeck, emuladores, ports y Prism…','pill');body.pack_start(self.wizard_report_label,False,False,0)
            scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);self.wizard_results=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);scroll.add(self.wizard_results);body.pack_start(scroll,True,True,0)
            controls=Gtk.Box(spacing=10);controls.pack_start(button('Falta una carpeta',lambda _:self.wizard_folder()),False,False,0);controls.pack_start(button('Rutas y emuladores',lambda _:self.installation_dialog()),False,False,0);body.pack_start(controls,False,False,0)
            footer.pack_start(button('← Atrás',lambda _:self.wizard_back()),False,False,0)
            self.wizard_continue=button('Continuar →',lambda _:self.wizard_next(),True);footer.pack_end(self.wizard_continue,False,False,0);self.wizard_continue.set_sensitive(self.wizard_found is not None)
            if self.wizard_found is not None:self.wizard_detection_ready(self.wizard_found)
            else:self.discover()
        elif self.wizard_step==2:
            body.pack_start(label('Carátulas','hero'),False,False,0)
            self.wizard_provider,self.wizard_key=self.provider_fields(body)
            body.pack_start(label('Buscaremos las carátulas al terminar. Los juegos siguen disponibles mientras se descargan.','muted'),False,False,0)
            footer.pack_start(button('← Atrás',lambda _:self.wizard_back()),False,False,0);footer.pack_end(button('Continuar →',lambda _:self.wizard_next(),True),False,False,0)
        else:
            body.pack_start(label('Configuración completada','welcome-title'),False,False,12)
            body.pack_start(label(f'{len(self.entries)} juegos encontrados · {len(self.checked)} seleccionados para Steam','subtitle'),False,False,0)
            body.pack_start(label('En la biblioteca, tocá una carátula para jugar, aplicar un preset o agregar ese juego a Steam.','title'),False,False,16)
            body.pack_start(label('Para agregar varios, activá “Seleccionar” y usá el botón de Steam que aparece abajo. Steam pedirá reiniciarse si está abierto.','muted'),False,False,0)
            footer.pack_start(button('← Atrás',lambda _:self.wizard_back()),False,False,0);footer.pack_end(button('Abrir biblioteca →',lambda _:self.leave_wizard(True),True),False,False,0)
        box.show_all();stack.set_visible_child(box)
        def remove_previous():
            for child in stack.get_children():
                if child is not stack.get_visible_child():stack.remove(child)
            return False
        GLib.timeout_add(260,remove_previous)
    def wizard_next(self):
        if self.wizard_step==1:self.checked={id_ for id_,widget in self.wizard_checks.items() if widget.get_active()}
        if self.wizard_step==2:
            provider=self.wizard_provider.get_active_id();key=self.wizard_key.get_text().strip()
            if provider=='steamgriddb' and not key:self.message('Falta la clave','Pegá tu clave de SteamGridDB o usá el proveedor Automático sin clave.');return
            self.preferences.update(artwork_provider=provider,steamgriddb_key=key);save_settings(self.preferences,self.store)
        self.wizard_step+=1;self.draw_wizard()
    def wizard_back(self):
        if self.wizard_step==1:self.checked={id_ for id_,widget in self.wizard_checks.items() if widget.get_active()}
        self.wizard_step=max(0,self.wizard_step-1);self.draw_wizard()
    def leave_wizard(self,complete):
        if complete:self.preferences['onboarding_complete']=True;save_settings(self.preferences,self.store)
        self.selection_mode=bool(self.checked);self.render();self.pages.set_visible_child_name('library');self.fetch_covers()
    def wizard_detection_ready(self,found):
        if self.pages.get_visible_child_name()!='welcome' or self.wizard_step!=1:return
        self.wizard_found=found;self.wizard_continue.set_sensitive(True)
        deck='EmuDeck ✓' if found['emudeck']['installed'] else 'EmuDeck no detectado'
        self.wizard_report_label.set_text(f'{deck}  ·  {len(found["emulators"])} emuladores  ·  {len(found["prism"])} instalaciones de Prism  ·  {len(self.entries)} juegos')
        self.reset_page(self.wizard_results);self.wizard_checks={}
        for entry in sorted(self.entries,key=lambda e:(e.platform,e.name.casefold())):
            row=Gtk.CheckButton(label=entry.name+'  ·  '+entry.platform);row.set_active(entry.id in self.checked);self.wizard_checks[entry.id]=row;self.wizard_results.pack_start(row,False,False,0)
        if not self.entries:
            from .gui import label
            self.wizard_results.pack_start(label('No encontramos juegos todavía. Elegí una carpeta o configurá el emulador.','muted'),False,False,0)
        self.wizard_results.show_all()
    def wizard_folder(self):
        dialog=Gtk.FileChooserDialog(title='¿Dónde están tus juegos?',transient_for=self,action=Gtk.FileChooserAction.SELECT_FOLDER);dialog.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Buscar aquí',Gtk.ResponseType.OK)
        if dialog.run()==Gtk.ResponseType.OK:
            path=dialog.get_filename()
            for key in ('rom_roots','port_roots'):
                self.preferences[key]=list(dict.fromkeys(self.preferences.get(key,[])+[path]))
            save_settings(self.preferences,self.store);self.wizard_found=None;self.discover()
        dialog.destroy()
    def fetch_covers(self,force=False):
        if getattr(self,'artwork_busy',False) or self.preferences.get('artwork_provider')=='off':return
        candidates=[e for e in self.entries if not e.cover or not pathlib.Path(e.cover).is_file()]
        if not force:candidates=[e for e in candidates if e.id not in self.artwork_attempted]
        if not candidates:return
        self.artwork_busy=True;preferences=dict(self.preferences);self.artwork_spinner.start();self.artwork_label.set_text('Buscando carátulas…');self.artwork_bar.show_all()
        def work():
            successes=0
            for index,entry in enumerate(candidates,1):
                GLib.idle_add(self.artwork_label.set_text,f'Carátulas · {index} de {len(candidates)} · {entry.name}')
                self.artwork_attempted.add(entry.id)
                try:
                    row=cover_provider.best_match(entry,cover_provider.search(cover_provider.title_for(entry),{**preferences,'_artwork_platform':entry.platform}))
                    if row:
                        path=cover_provider.download(row,self.store);GLib.idle_add(self.cover_received,entry.id,path,row);successes+=1
                except Exception:pass
            GLib.idle_add(self.covers_finished,successes,len(candidates))
        threading.Thread(target=work,daemon=True).start()
    def cover_received(self,id_,path,row):
        entry=next((e for e in self.entries if e.id==id_),None)
        if entry and (not entry.cover or not pathlib.Path(entry.cover).is_file()):
            entry.cover=path;entry.metadata['artwork']={'provider':row['provider'],'page':row.get('page','')};self.store.save(self.entries);self.render()
            if self.selected and self.selected.id==id_ and self.pages.get_visible_child_name()=='detail':self.show_detail(entry)
        return False
    def covers_finished(self,count,total):
        self.artwork_busy=False;self.artwork_spinner.stop();self.artwork_bar.hide();self.set_status(f'{count} carátulas encontradas.'+(f' Podés buscar otra imagen en la ficha de cada juego.' if count<total else ''));return False
    def artwork_dialog(self,e):
        from .gui import label,button
        dialog=Gtk.Dialog(title='Carátula · '+e.name,transient_for=self,modal=True);dialog.set_default_size(820,600);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(12)
        query=Gtk.Entry();query.set_text(cover_provider.title_for(e));row=Gtk.Box(spacing=10);row.pack_start(query,True,True,0);box.pack_start(row,False,False,0)
        status=label('Buscá una carátula online o elegí una imagen de tu Deck.','muted');box.pack_start(status,False,False,0)
        scroll=Gtk.ScrolledWindow();results=Gtk.FlowBox();results.set_selection_mode(Gtk.SelectionMode.NONE);results.set_max_children_per_line(4);scroll.add(results);box.pack_start(scroll,True,True,0)
        alive={'value':True}
        def loaded(items,error):
            if not alive['value']:return False
            search_button.set_sensitive(True);self.reset_page(results);status.set_text(error or f'{len(items)} imágenes. Tocá la que quieras usar.')
            for data,path in items:
                tile=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);pick=Gtk.Button()
                try:pick.add(Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(path,140,210,True)))
                except GLib.Error:continue
                def selected(_,data=data,path=path):
                    e.cover=path;e.metadata['artwork']={'provider':data['provider'],'page':data.get('page','')};self.store.save(self.entries);self.render();self.show_detail(e);dialog.response(Gtk.ResponseType.CLOSE)
                pick.connect('clicked',selected);tile.pack_start(pick,False,False,0);name=label(data['title'],'muted');name.set_max_width_chars(16);tile.pack_start(name,False,False,0);tile.pack_start(Gtk.LinkButton.new_with_label(data['page'],data['provider']),False,False,0);results.add(tile)
            results.show_all();return False
        def lookup(_):
            text=query.get_text().strip();prefs={**self.preferences,'_artwork_platform':e.platform}
            if not text:return
            search_button.set_sensitive(False);status.set_text('Buscando y descargando vistas previas…')
            def work():
                try:
                    rows=cover_provider.search(text,prefs);items=[]
                    for item in rows[:12]:
                        try:items.append((item,cover_provider.download(item,self.store)))
                        except Exception:continue
                    GLib.idle_add(loaded,items,'No encontramos imágenes. Probá otro nombre o cambiá el proveedor en Ajustes.' if not items else '')
                except Exception:GLib.idle_add(loaded,[],'No pudimos consultar el proveedor. Revisá la conexión y la clave en Ajustes.')
            threading.Thread(target=work,daemon=True).start()
        search_button=button('Buscar online',lookup,True);row.pack_start(search_button,False,False,0);query.connect('activate',lookup)
        def local(_):self.choose_cover(e);self.show_detail(e);dialog.response(Gtk.ResponseType.CLOSE)
        box.pack_start(button('Elegir imagen local',local),False,False,0)
        if e.metadata.get('artwork',{}).get('page'):box.pack_start(Gtk.LinkButton.new_with_label(e.metadata['artwork']['page'],'Ver origen de la carátula actual'),False,False,0)
        dialog.show_all();lookup(None);dialog.run();alive['value']=False;dialog.destroy()
    def steam_edit_dialog(self,e):
        from .gui import label
        from .steam_inventory import shortcuts,launch_command
        from .models import atomic_json
        account=e.metadata.get('steam_account')
        try:item=next(s for s in shortcuts(account) if s['appid']==e.metadata.get('steam_appid'))
        except (OSError,ValueError,StopIteration,TypeError):self.message('Acceso no disponible','Actualizar la biblioteca para volver a detectar los accesos de Steam.');return
        dialog=Gtk.Dialog(title='Editar acceso de Steam',transient_for=self,modal=True);dialog.set_default_size(700,460);dialog.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Guardar y actualizar Steam',Gtk.ResponseType.OK);box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(10)
        fields={}
        for key,title in [('name','Nombre'),('exe','Ejecutable'),('startdir','Carpeta de inicio'),('options','Opciones de lanzamiento')]:
            box.pack_start(label(title,'muted'),False,False,0);field=Gtk.Entry();field.set_text(item[key]);fields[key]=field;box.pack_start(field,False,False,0)
        box.pack_start(label('Se conserva el identificador del acceso y su configuración de Steam Input y Proton. La carátula seleccionada también se guarda en Steam.','muted'),False,False,0);dialog.show_all()
        if dialog.run()==Gtk.ResponseType.OK:
            updated={**item,**{key:field.get_text().strip() for key,field in fields.items()}}
            if not updated['name'] or not updated['exe']:self.message('Datos incompletos','El nombre y el ejecutable son obligatorios.')
            else:
                e.name=updated['name']
                if e.kind=='steam':e.command=launch_command(updated);e.source=e.command[0] if e.command[0].startswith('/') else '';e.metadata['steam_original']=updated
                else:
                    # Editing native Steam fields adopts that launch definition explicitly.
                    e.metadata['steam_override']=updated
                self.store.save(self.entries);self.render();self.show_detail(e);self.single_steam(e)
        dialog.destroy()
