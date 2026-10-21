"""Guided onboarding and artwork selection for the redesigned library."""
import pathlib,threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib,GdkPixbuf
from .inline_pages import InlineDialog,InlineFileChooser
from .installations import report,save_settings
from . import cover_provider

class ExperienceMixin:
    def provider_fields(self,box):
        from .gui import label
        box.pack_start(label('Proveedor de carátulas','title'),False,False,0)
        box.pack_start(label('Automático usa SteamGridDB si hay una clave configurada; si no, busca en Libretro y Wikipedia. La imagen se puede cambiar por juego.','muted'),False,False,0)
        combo=Gtk.ComboBoxText()
        for key,name in [('automatic','Automático (recomendado)'),('libretro','Libretro · consolas clásicas'),('wikipedia','Wikipedia · sin cuenta'),('steamgriddb','SteamGridDB · carátulas 600 × 900'),('off','Solo imágenes locales')]:combo.append(key,name)
        combo.set_active_id(self.preferences.get('artwork_provider','automatic'));box.pack_start(combo,False,False,0)
        box.pack_start(label('Clave de SteamGridDB (opcional)','title'),False,False,6)
        box.pack_start(label('Con una clave, las carátulas, fondos, logotipos e íconos de Steam se buscan en SteamGridDB. Cómo conseguirla: 1) iniciar sesión en steamgriddb.com con la cuenta de Steam; 2) abrir el perfil y entrar en Preferencias → API; 3) copiar la clave y pegarla aquí. Es gratuita y personal: no compartirla.','muted'),False,False,0)
        key=Gtk.Entry();key.set_visibility(False);key.set_placeholder_text('Pegar la clave API de SteamGridDB');key.set_text(self.preferences.get('steamgriddb_key',''));key.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY,'view-reveal-symbolic');key.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY,'Mostrar u ocultar la clave')
        key.connect('icon-press',lambda entry,*a:entry.set_visibility(not entry.get_visibility()));box.pack_start(key,False,False,0)
        row=Gtk.Box(spacing=12);verdict=label('','muted')
        def test(_):
            text=key.get_text().strip()
            if not text:verdict.set_text('Pegar primero la clave.');return
            verdict.set_text('Probando…')
            def work():
                from . import steamart
                import urllib.error
                try:steamart.find_games(text,'Zelda');result='Clave válida.'
                except urllib.error.HTTPError as error:result='SteamGridDB rechazó la clave.' if error.code in (401,403) else 'SteamGridDB respondió con error '+str(error.code)+'.'
                except Exception as error:result='No se pudo probar: '+str(error)
                GLib.idle_add(verdict.set_text,result)
            threading.Thread(target=work,daemon=True).start()
        from .gui import button
        row.pack_start(button('Probar clave',test),False,False,0);row.pack_start(verdict,True,True,0);box.pack_start(row,False,False,0)
        link=Gtk.LinkButton.new_with_label('https://www.steamgriddb.com/profile/preferences/api','Abrir la página de claves de SteamGridDB');box.pack_start(link,False,False,0)
        box.pack_start(label('La clave se guarda solo en esta Deck. Al buscar se envía el nombre del juego al proveedor y las imágenes se guardan localmente.','muted'),False,False,0)
        return combo,key

    def settings_page(self):
        from .gui import label,button,wrap_row
        self.reset_page(self.settings_box)
        self.settings_box.pack_start(label('Ajustes','hero'),False,False,0)
        self.settings_box.pack_start(label('Carátulas, rutas y apariencia.','subtitle'),False,False,0)
        panel=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14);panel.get_style_context().add_class('card');self.settings_box.pack_start(panel,False,False,0)
        advanced=Gtk.Expander(label='Proveedor de carátulas y clave API');provider_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);advanced.add(provider_box);panel.pack_start(advanced,False,False,0);combo,key=self.provider_fields(provider_box)
        animations=Gtk.Switch();animations.set_active(self.preferences.get('animations',True));row=Gtk.Box(spacing=12);row.pack_start(label('Animaciones y transiciones'),True,True,0);row.pack_end(animations,False,False,0);panel.pack_start(row,False,False,0)
        def save(_):
            if combo.get_active_id()=='steamgriddb' and not key.get_text().strip():self.message('Falta la clave','Ingresar la clave o elegir Automático o Wikipedia.');return
            self.preferences.update(artwork_provider=combo.get_active_id(),steamgriddb_key=key.get_text().strip(),animations=animations.get_active());save_settings(self.preferences,self.store);self.apply_motion();self.artwork_attempted.clear();self.set_status('Ajustes guardados.');self.fetch_covers()
        panel.pack_start(button('Guardar y buscar carátulas',save,True),False,False,0)
        row=wrap_row()
        from . import motion
        if not motion.gaming_mode():row.pack_start(button('Agregar Deck Library a Steam',self.add_library_to_steam),False,False,0)
        row.pack_start(button('Instalaciones y carpetas',lambda _:self.installation_dialog()),False,False,0)
        row.pack_start(button('Repetir configuración inicial',lambda _:self.start_wizard()),False,False,0)
        row.pack_start(button('Aplicar ajustes máximos para Steam Deck',lambda _:self.apply_deck_max()),False,False,0)
        row.pack_start(button('Completar arte de todos los accesos de Steam',lambda _:self.complete_all_art()),False,False,0)
        self.settings_box.pack_start(row,False,False,0);self.settings_box.reorder_child(row,2);self.settings_box.show_all();self.pages.set_visible_child_name('settings')

    def apply_deck_max(self):
        from . import deckmax
        text={'applied':'actualizado','present':'ya estaba aplicado','busy':'abierto: cerrar y repetir','missing':'no instalado'}
        done=deckmax.apply();self.message('Ajustes máximos para Steam Deck','Resolución interna y calidad al máximo que admite la pantalla de 1280×800. Se guarda un respaldo de cada archivo modificado.\n\n'+'\n'.join(f'{name}: {text[state]}' for name,state in done))

    def start_wizard(self):
        self.wizard_step=0;self.wizard_found=None;self.wizard_checks={};self.checked.clear();self.selection_mode=False;self.draw_wizard();self.wizard_box.show();self.pages.set_visible_child_name('welcome');return False
    def draw_wizard(self):
        from .gui import label,button,wrap_row
        stack=self.wizard_box;box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);stack.add(box)
        steps=['Inicio','Detección','Carátulas','Final'];progress=Gtk.Box(spacing=12)
        for index,title in enumerate(steps):
            item=label(f'{index+1}  {title}','pill' if index==self.wizard_step else 'muted');progress.pack_start(item,True,True,0)
        box.pack_start(progress,False,False,0)
        body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16);body.set_hexpand(True);body.set_vexpand(True);box.pack_start(body,True,True,8)
        footer=Gtk.Box(spacing=12);box.pack_end(footer,False,False,0)
        if self.wizard_step==0:
            body.pack_start(label('Configuración inicial','welcome-title'),False,False,12)
            body.pack_start(label('Detectar instalaciones, configurar carátulas y preparar accesos a Steam.','subtitle'),False,False,0)
            for title,text in [('1  Detección','EmuDeck, emuladores, ports de Quiver e instancias de Prism.'),('2  Carátulas','Descarga automática y ajustes recomendados por juego.'),('3  Steam','Selección de juegos y creación de accesos.')]:
                card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);card.get_style_context().add_class('card');card.pack_start(label(title,'title'),False,False,0);card.pack_start(label(text,'muted'),False,False,0);body.pack_start(card,False,False,0)
            footer.pack_end(button('Empezar',lambda _:self.wizard_next(),True),False,False,0)
            footer.pack_start(button('Omitir',lambda _:self.leave_wizard(False)),False,False,0)
        elif self.wizard_step==1:
            body.pack_start(label('Juegos detectados','hero'),False,False,0)
            body.pack_start(label('Marcar los juegos que se agregarán a Steam. Si falta alguno, añadir su carpeta.','subtitle'),False,False,0)
            self.wizard_report_label=label('Buscando EmuDeck, emuladores, ports y Prism…','pill');body.pack_start(self.wizard_report_label,False,False,0)
            scroll=self.new_scroll();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);self.wizard_results=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);scroll.add(self.wizard_results);body.pack_start(scroll,True,True,0)
            controls=Gtk.Box(spacing=10);controls.pack_start(button('Añadir carpeta',lambda _:self.wizard_folder()),False,False,0);controls.pack_start(button('Rutas y emuladores',lambda _:self.installation_dialog()),False,False,0);body.pack_start(controls,False,False,0)
            footer.pack_start(button('Atrás',lambda _:self.wizard_back()),False,False,0)
            self.wizard_continue=button('Continuar',lambda _:self.wizard_next(),True);footer.pack_end(self.wizard_continue,False,False,0);self.wizard_continue.set_sensitive(self.wizard_found is not None)
            if self.wizard_found is not None:self.wizard_detection_ready(self.wizard_found)
            else:self.discover()
        elif self.wizard_step==2:
            body.pack_start(label('Carátulas','hero'),False,False,0)
            self.wizard_provider,self.wizard_key=self.provider_fields(body)
            body.pack_start(label('Las carátulas se descargan al terminar. La biblioteca se puede usar mientras tanto.','muted'),False,False,0)
            footer.pack_start(button('Atrás',lambda _:self.wizard_back()),False,False,0);footer.pack_end(button('Continuar',lambda _:self.wizard_next(),True),False,False,0)
        else:
            body.pack_start(label('Configuración completada','welcome-title'),False,False,12)
            body.pack_start(label(f'{len(self.entries)} juegos encontrados · {len(self.checked)} seleccionados para Steam','subtitle'),False,False,0)
            body.pack_start(label('Cada carátula abre la ficha del juego: jugar, aplicar ajustes o agregarlo a Steam.','title'),False,False,16)
            body.pack_start(label('Para agregar varios a la vez, activar «Seleccionar». Si Steam está abierto, debe reiniciarse para guardar los accesos.','muted'),False,False,0)
            footer.pack_start(button('Atrás',lambda _:self.wizard_back()),False,False,0);footer.pack_end(button('Abrir biblioteca',lambda _:self.leave_wizard(True),True),False,False,0)
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
            if provider=='steamgriddb' and not key:self.message('Falta la clave','Ingresar la clave de SteamGridDB o usar el proveedor Automático, que no la necesita.');return
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
        deck='EmuDeck detectado' if found['emudeck']['installed'] else 'EmuDeck no detectado'
        self.wizard_report_label.set_text(f'{deck}  ·  {len(found["emulators"])} emuladores  ·  {len(found["prism"])} instalaciones de Prism  ·  {len(self.entries)} juegos')
        self.reset_page(self.wizard_results);self.wizard_checks={}
        for entry in sorted(self.entries,key=lambda e:(e.platform,e.name.casefold())):
            row=Gtk.CheckButton(label=entry.name+'  ·  '+entry.platform);row.set_active(entry.id in self.checked);self.wizard_checks[entry.id]=row;self.wizard_results.pack_start(row,False,False,0)
        if not self.entries:
            from .gui import label
            self.wizard_results.pack_start(label('No se encontraron juegos. Añadir una carpeta o configurar el emulador.','muted'),False,False,0)
        self.wizard_results.show_all()
    def wizard_folder(self):
        dialog=InlineFileChooser(title='Carpeta de juegos',transient_for=self,action=Gtk.FileChooserAction.SELECT_FOLDER);dialog.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Buscar en esta carpeta',Gtk.ResponseType.OK)
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
                GLib.idle_add(self.artwork_label.set_text,f'Carátulas {index} de {len(candidates)}: {entry.name}')
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
            entry.cover=path;entry.metadata['artwork']={'provider':row['provider'],'page':row.get('page','')};self.store.save(self.entries);self.library_dirty=True
            if self.pages.get_visible_child_name()=='library':self.render()
            if self.selected and self.selected.id==id_ and self.pages.get_visible_child_name()=='detail':self.show_detail(entry)
        return False
    def covers_finished(self,count,total):
        self.artwork_busy=False;self.artwork_spinner.stop();self.artwork_bar.hide();self.set_status(f'{count} carátulas encontradas.'+(' Las faltantes se pueden buscar desde la ficha de cada juego.' if count<total else ''));return False
    def artwork_dialog(self,e):
        from .gui import label,button,wrap_row
        dialog=InlineDialog(title='Carátula · '+e.name,transient_for=self,modal=True);dialog.set_default_size(820,600);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(12)
        query=Gtk.Entry();query.set_text(cover_provider.title_for(e));row=Gtk.Box(spacing=10);row.pack_start(query,True,True,0);box.pack_start(row,False,False,0)
        status=label('Buscar una carátula en línea o elegir una imagen local.','muted');box.pack_start(status,False,False,0)
        scroll=self.new_scroll();results=Gtk.FlowBox();results.set_selection_mode(Gtk.SelectionMode.NONE);results.set_max_children_per_line(4);scroll.add(results);box.pack_start(scroll,True,True,0)
        alive={'value':True}
        def begin():
            search_button.set_sensitive(False);self.reset_page(results);status.set_text('Buscando…');return False
        def add_tile(data,path):
            if not alive['value']:return False
            tile=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);pick=Gtk.Button()
            try:pick.add(Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(path,140,210,True)))
            except GLib.Error:return False
            def selected(_,data=data,path=path):
                e.cover=path;e.metadata['artwork']={'provider':data['provider'],'page':data.get('page','')};self.store.save(self.entries);self.render();self.show_detail(e);self.toast('Carátula actualizada');dialog.response(Gtk.ResponseType.CLOSE)
            pick.connect('clicked',selected);tile.pack_start(pick,False,False,0);name=label(data['title'],'muted');name.set_max_width_chars(16);tile.pack_start(name,False,False,0);tile.pack_start(Gtk.LinkButton.new_with_label(data['page'],data['provider']),False,False,0);results.add(tile);results.show_all();return False
        def finished(count,error):
            if not alive['value']:return False
            search_button.set_sensitive(True);status.set_text(error or ((f'{count} imágenes. Elegir una para usarla.' if count!=1 else '1 imagen. Elegir para usarla.') if count else 'Sin resultados. Probar otro nombre o cambiar el proveedor en Ajustes.'));return False
        def lookup(_):
            text=query.get_text().strip();prefs={**self.preferences,'_artwork_platform':e.platform}
            if not text:return
            begin()
            def work():
                from concurrent.futures import ThreadPoolExecutor,as_completed
                try:rows=cover_provider.search(text,prefs,merge=True)[:18]
                except Exception as error:GLib.idle_add(finished,0,'No se pudo consultar el proveedor: '+str(error));return
                GLib.idle_add(status.set_text,f'{len(rows)} resultados. Descargando vistas previas…');count=0
                with ThreadPoolExecutor(6) as pool:
                    jobs={pool.submit(cover_provider.download,row,self.store):row for row in rows}
                    for job in as_completed(jobs):
                        try:path=job.result()
                        except Exception:continue
                        count+=1;GLib.idle_add(add_tile,jobs[job],path)
                GLib.idle_add(finished,count,'')
            threading.Thread(target=work,daemon=True).start()
        search_button=button('Buscar en línea',lookup,True);row.pack_start(search_button,False,False,0);query.connect('activate',lookup)
        def local(_):self.choose_cover(e);self.show_detail(e);dialog.response(Gtk.ResponseType.CLOSE)
        box.pack_start(button('Elegir imagen local',local),False,False,0)
        if e.metadata.get('artwork',{}).get('page'):box.pack_start(Gtk.LinkButton.new_with_label(e.metadata['artwork']['page'],'Ver origen de la carátula actual'),False,False,0)
        self.fit_dialog(dialog);dialog.show_all();lookup(None);dialog.run();alive['value']=False;dialog.destroy()
    def steam_art_dialog(self,e):
        """Choose the five Steam artwork slots of a shortcut from SteamGridDB; chosen images are written when Steam is closed."""
        from .gui import label,button,wrap_row
        from . import steamart
        from .service import queue_art
        key=self.preferences.get('steamgriddb_key','')
        if not key:
            self.message('Falta la clave de SteamGridDB','Agregar la clave API en Ajustes. Es la misma cuenta que usa el plugin de Decky.');return
        account=pathlib.Path(e.metadata['steam_account']);appid=e.metadata['steam_appid']
        dialog=InlineDialog(title='Arte de Steam · '+e.name,transient_for=self,modal=True);dialog.set_default_size(900,660);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(18);box.set_spacing(10)
        top=Gtk.Box(spacing=10);query=Gtk.Entry();query.set_text(cover_provider.title_for(e));top.pack_start(query,True,True,0);games=Gtk.ComboBoxText();top.pack_start(games,False,False,0);find=button('Buscar juego',lambda _:look(),True);top.pack_start(find,False,False,0);box.pack_start(top,False,False,0)
        status=label('','muted');box.pack_start(status,False,False,0)
        present=steamart.existing(account,appid);chosen={};notebook=Gtk.Notebook();box.pack_start(notebook,True,True,0);lists={};state={'alive':True,'game':None}
        summary=label('','muted');box.pack_start(summary,False,False,0)
        def refresh_summary():
            parts=[f'{steamart.SLOTS[s][1]}: '+('elegido' if s in chosen else 'ya en Steam' if present[s] else 'falta') for s in steamart.SLOTS];summary.set_text(' · '.join(parts));save.set_sensitive(bool(chosen))
        for slot,(_,title,_,_) in steamart.SLOTS.items():
            scroll=self.new_scroll();flow=Gtk.FlowBox();flow.set_selection_mode(Gtk.SelectionMode.NONE);flow.set_max_children_per_line(6 if slot in ('portrait','icon','logo') else 3);scroll.add(flow);lists[slot]=flow;notebook.append_page(scroll,Gtk.Label(label=title+(' ✓' if present[slot] else '')))
        def add_tile(slot,row,path):
            if not state['alive']:return False
            width,height={'portrait':(120,180),'banner':(220,103),'hero':(300,97),'logo':(160,90),'icon':(96,96)}[slot]
            try:pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(path,width,height,True)
            except GLib.Error:return False
            pick=Gtk.Button();pick.add(Gtk.Image.new_from_pixbuf(pixbuf));pick.set_tooltip_text((row.get('author') or '')+' · '+f'{row["width"]}×{row["height"]}')
            def chose(_,slot=slot,row=row):pick_image(slot,row)
            pick.connect('clicked',chose);lists[slot].add(pick);pick.show_all();return False
        def pick_image(slot,row):
            status.set_text('Descargando la imagen elegida…')
            def work():
                try:data,ext=steamart.fetch_image(row['url']);path=steamart.stage(self.store,appid,slot,data,ext)
                except Exception as error:GLib.idle_add(status.set_text,'No se pudo descargar: '+str(error));return
                def done():chosen[slot]=path;status.set_text(steamart.SLOTS[slot][1]+' elegido. Guardar para aplicarlo.');refresh_summary();return False
                GLib.idle_add(done)
            threading.Thread(target=work,daemon=True).start()
        def load_slot(slot,game_id,autopick=False):
            def work():
                try:rows=steamart.candidates(key,game_id,slot)
                except Exception as error:GLib.idle_add(status.set_text,'SteamGridDB: '+str(error));return
                if autopick and rows and not present[slot] and slot not in chosen:GLib.idle_add(pick_image,slot,rows[0])
                from concurrent.futures import ThreadPoolExecutor,as_completed
                with ThreadPoolExecutor(5) as pool:
                    jobs={pool.submit(cover_provider.download,{'url':r['thumb'],'title':e.name,'provider':'SteamGridDB','page':r['page']},self.store):r for r in rows}
                    for job in as_completed(jobs):
                        try:path=job.result()
                        except Exception:continue
                        GLib.idle_add(add_tile,slot,jobs[job],path)
            threading.Thread(target=work,daemon=True).start()
        def load_all(game_id,autopick=False):
            e.metadata['sgdb_id']=game_id
            for slot in steamart.SLOTS:
                self.reset_page(lists[slot]);load_slot(slot,game_id,autopick)
        def look():
            text=query.get_text().strip()
            if not text:return
            status.set_text('Buscando el juego en SteamGridDB…')
            def work():
                try:found=steamart.find_games(key,text)
                except Exception as error:GLib.idle_add(status.set_text,'SteamGridDB: '+str(error));return
                def show():
                    games.remove_all()
                    for g in found:games.append(str(g['id']),g['name'])
                    if not found:status.set_text('Sin resultados. Probar otro nombre.');return False
                    games.set_active_id(str(e.metadata.get('sgdb_id')) if str(e.metadata.get('sgdb_id')) in {str(g['id']) for g in found} else str(found[0]['id']));status.set_text('Elegir una imagen por pestaña.');return False
                GLib.idle_add(show)
            threading.Thread(target=work,daemon=True).start()
        games.connect('changed',lambda c:load_all(int(c.get_active_id())) if c.get_active_id() else None)
        bottom=Gtk.Box(spacing=10)
        def complete(_):
            gid=games.get_active_id()
            if not gid:return
            for slot in steamart.SLOTS:
                if not present[slot] and slot not in chosen:load_slot(slot,int(gid),True)
            status.set_text('Eligiendo automáticamente lo que falta…')
        bottom.pack_start(button('Completar lo que falta',complete),False,False,0)
        save=button('Guardar en Steam',lambda _:commit(),True);bottom.pack_end(save,False,False,0);box.pack_start(bottom,False,False,0)
        def commit():
            items=[{'appid':appid,'slot':s,'file':f} for s,f in chosen.items()]
            self.store.save(self.entries);dialog.response(Gtk.ResponseType.CLOSE)
            self.run_queue(lambda:queue_art(items,account,self.store),'Preparando el arte de Steam…')
        refresh_summary();self.fit_dialog(dialog);dialog.show_all();look();dialog.run();state['alive']=False;dialog.destroy()
    def complete_all_art(self):
        """Fill every empty Steam artwork slot of every shortcut from SteamGridDB, keeping what exists."""
        from . import steamart
        from .service import queue_art
        key=self.preferences.get('steamgriddb_key','')
        if not key:self.message('Falta la clave de SteamGridDB','Agregar la clave API en Ajustes. La del plugin de Decky es exclusiva de ese plugin y no se puede reutilizar.');return
        targets=[e for e in self.entries if self.in_steam(e) and e.metadata.get('steam_account')]
        if not targets:self.message('Sin accesos','Ningún juego de la biblioteca tiene acceso guardado en Steam.');return
        if not self.confirm('Completar arte de Steam',f'Se buscan en SteamGridDB las imágenes que faltan (portada vertical y horizontal, fondo, logotipo e ícono) de {len(targets)} accesos. Lo que ya existe no se reemplaza. Las imágenes se guardan cuando Steam está cerrado.'):return
        self.set_status('Buscando arte de Steam…')
        def work():
            try:
                items,report=steamart.complete_missing(key,targets,self.store,lambda t:GLib.idle_add(self.set_status,t))
                done=[r for r in report if r[1].startswith('se agregó')]
                by_account={}
                for item in items:by_account.setdefault(item.pop('account'),[]).append(item)
                result={'state':'idle','count':0}
                for account,rows in by_account.items():result=queue_art(rows,pathlib.Path(account),self.store)
            except Exception as error:GLib.idle_add(self.failed,str(error));return
            lines='\n'.join(f'{name}: {text}' for name,text in report)
            GLib.idle_add(self.message,'Arte de Steam',f'{len(items)} imágenes para {len(done)} juegos. Se aplican cuando Steam está cerrado.\n\n'+lines)
            GLib.idle_add(self.queue_done,{'state':result['state'],'count':len(items)})
        threading.Thread(target=work,daemon=True).start()
    def steam_edit_dialog(self,e):
        from .gui import label
        from .steam_inventory import shortcuts,launch_command
        from .models import atomic_json
        account=e.metadata.get('steam_account')
        try:item=next(s for s in shortcuts(account) if s['appid']==e.metadata.get('steam_appid'))
        except (OSError,ValueError,StopIteration,TypeError):self.message('Acceso no disponible','Buscar juegos de nuevo para detectar los accesos de Steam.');return
        dialog=InlineDialog(title='Editar acceso de Steam',transient_for=self,modal=True);dialog.set_default_size(700,460);dialog.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Guardar',Gtk.ResponseType.OK);box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(10)
        fields={}
        for key,title in [('name','Nombre'),('exe','Ejecutable'),('startdir','Carpeta de inicio'),('options','Opciones de lanzamiento')]:
            box.pack_start(label(title,'muted'),False,False,0);field=Gtk.Entry();field.set_text(item[key]);fields[key]=field;box.pack_start(field,False,False,0)
        box.pack_start(label('Se conservan el identificador del acceso, Steam Input y Proton. La carátula elegida también se guarda en Steam.','muted'),False,False,0);self.fit_dialog(dialog);dialog.show_all()
        if dialog.run()==Gtk.ResponseType.OK:
            updated={**item,**{key:field.get_text().strip() for key,field in fields.items()}}
            if not updated['name'] or not updated['exe']:self.message('Datos incompletos','Nombre y ejecutable son obligatorios.')
            else:
                e.name=updated['name']
                if e.kind=='steam':e.command=launch_command(updated);e.source=e.command[0] if e.command[0].startswith('/') else '';e.metadata['steam_original']=updated
                else:
                    # Editing native Steam fields adopts that launch definition explicitly.
                    e.metadata['steam_override']=updated
                self.store.save(self.entries);self.render();self.show_detail(e);self.single_steam(e)
        dialog.destroy()
