"""Community port catalog page: browse, install and update ports from GitHub releases."""
import threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib,GdkPixbuf
from . import ports
from .installations import save_settings

ICON_SIZE=56

class CatalogMixin:
    def catalog_page(self):
        from .gui import label,button
        box=self.catalog_box;self.reset_page(box)
        head=Gtk.Box(spacing=12);titles=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        titles.pack_start(label('Catálogo de ports','hero'),False,False,0)
        titles.pack_start(label('Listas públicas de Quiver y GithubLauncher, recomendados y repositorios propios. Se instalan en ~/ports desde el último release de GitHub. La mayoría necesita los archivos del juego original.','subtitle'),False,False,0)
        head.pack_start(titles,True,True,0);actions=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        actions.pack_start(button('Agregar repositorio',lambda _:self.add_repository_dialog(),True),False,False,0);actions.pack_start(button('Actualizar listas',lambda _:self.load_catalog(True)),False,False,0)
        head.pack_end(actions,False,False,0);box.pack_start(head,False,False,0)
        tools=Gtk.Box(spacing=10);self.catalog_search=Gtk.SearchEntry();self.catalog_search.set_placeholder_text('Buscar port o juego');self.catalog_search.connect('search-changed',lambda _:self.fill_catalog());tools.pack_start(self.catalog_search,True,True,0)
        self.catalog_category=Gtk.ComboBoxText();self.catalog_category.append('','Todas las categorías');self.catalog_category.set_active_id('');self.catalog_category.connect('changed',lambda _:self.fill_catalog());tools.pack_start(self.catalog_category,False,False,0)
        self.catalog_source=Gtk.ComboBoxText();self.catalog_source.append('','Todas las fuentes')
        for name in ('Recomendado','Agregado','Quiver','GithubLauncher'):self.catalog_source.append(name,name)
        self.catalog_source.set_active_id('');self.catalog_source.connect('changed',lambda _:self.fill_catalog());tools.pack_start(self.catalog_source,False,False,0);box.pack_start(tools,False,False,0)
        self.catalog_status=label('Cargando catálogo…','status');box.pack_start(self.catalog_status,False,False,0)
        self.catalog_rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);box.pack_start(self.catalog_rows,False,False,0)
        box.show_all();self.pages.set_visible_child_name('catalog');self.load_catalog(False)

    def load_catalog(self,force):
        self.catalog_status.set_text('Cargando catálogo…');extra=list(self.preferences.get('catalog_sources',[]))
        def work():
            try:apps=ports.catalog(self.store,force,extra=extra)
            except Exception as error:GLib.idle_add(self.catalog_loaded,None,str(error));return
            GLib.idle_add(self.catalog_loaded,apps,'')
        threading.Thread(target=work,daemon=True).start()

    def catalog_loaded(self,apps,error):
        if apps is None:
            # Recommended and own entries remain usable without the remote lists.
            self.catalog_apps=ports.merged([],self.preferences);self.fill_catalog();self.catalog_status.set_text('No se pudieron cargar las listas remotas: '+error);return False
        self.catalog_apps=apps;self.fill_catalog();return False

    def catalog_entries(self):return ports.merged(getattr(self,'catalog_apps',[]),self.preferences)

    def fill_catalog(self):
        from .gui import label,button
        if not hasattr(self,'catalog_apps'):return
        everything=self.catalog_entries();categories=sorted({a['list'] for a in everything if a['list']},key=str.casefold);current=self.catalog_category.get_active_id() or ''
        known={row[0] for row in self.catalog_category.get_model()}
        for name in categories:
            if name not in known:self.catalog_category.append(name,name)
        self.reset_page(self.catalog_rows);text=self.catalog_search.get_text().casefold().strip();category=self.catalog_category.get_active_id() or '';source=self.catalog_source.get_active_id() or ''
        installed=ports.records(self.store);updates={u['repository'] for u in (getattr(self,'update_state',None) or {}).get('catalog') or []}
        matches=[a for a in everything if text in (a['name']+' '+a['repository']).casefold() and (not category or a['list']==category) and (not source or source in a['source'])]
        matches.sort(key=lambda a:(not a['source'].startswith(('Recomendado','Agregado')),a['name'].casefold()))
        self.catalog_status.set_text(f'{len(matches)} de {len(everything)} ports'+(' · se muestran los primeros 60' if len(matches)>60 else ''))
        self.catalog_generation=getattr(self,'catalog_generation',0)+1;generation=self.catalog_generation;images=[];kits=[]
        for item in matches[:60]:
            row=Gtk.Box(spacing=14);row.get_style_context().add_class('card');image=Gtk.Image();image.set_size_request(ICON_SIZE,ICON_SIZE);image.set_valign(Gtk.Align.START);row.pack_start(image,False,False,0);images.append((item,image))
            texts=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);texts.pack_start(label(item['name'],'title'),False,False,0);record=installed.get(item['repository'])
            tags=[t for t in (item['list'],item['source'],'Asistido por IA' if item['ai'] else '') if t]
            texts.pack_start(label(item['repository']+(' · instalado '+record['tag'] if record else ''),'muted'),False,False,0)
            if tags:texts.pack_start(label('  ·  '.join(tags),'pill'),False,False,0)
            if item['note']:texts.pack_start(label(item['note'],'status'),False,False,0)
            if item.get('bios') or item.get('disc'):
                checks=label('Comprobando requisitos…','status');texts.pack_start(checks,False,False,0);kits.append((item,checks))
            row.pack_start(texts,True,True,0);side=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
            if record and item['repository'] in updates:side.pack_start(button('Actualizar',lambda _,i=item:self.install_port(i,True),True),False,False,0)
            elif record and record.get('setup') and not record.get('configured'):side.pack_start(button('Configurar',lambda _,i=item:self.configure_port(i),True),False,False,0)
            elif record and record.get('setup'):
                side.pack_start(label('Configurado','good'),False,False,0)
                if record.get('setup')=='kit' and record.get('patch_level',0)<ports.PATCH_LEVEL:side.pack_start(button('Mejorar rendimiento',lambda _,i=item:self.configure_port(i),True),False,False,0)
                else:side.pack_start(button('Volver a configurar',lambda _,i=item:self.configure_port(i)),False,False,0)
            elif record:side.pack_start(label('Instalado','good'),False,False,0)
            else:side.pack_start(button('Instalar',lambda _,i=item:self.install_port(i,False)),False,False,0)
            if 'Agregado' in item['source']:side.pack_start(button('Quitar de la lista',lambda _,i=item:self.remove_repository(i),tone='danger'),False,False,0)
            row.pack_end(side,False,False,0);self.catalog_rows.pack_start(row,False,False,0)
        self.catalog_rows.show_all();self.load_icons(images,generation);self.check_kits(kits,generation)

    def check_kits(self,kits,generation):
        """Compare each kit's BIOS and disc requirements with what is already on the Deck."""
        games=[(e.name,e.source) for e in self.entries if e.source]
        def work():
            for item,widget in kits:
                try:lines=ports.requirements(item,games)
                except Exception:lines=[]
                GLib.idle_add(self.show_requirements,widget,lines,generation)
        if kits:threading.Thread(target=work,daemon=True).start()

    def show_requirements(self,widget,lines,generation):
        if generation!=self.catalog_generation:return False
        marks={True:'✓ ',False:'✗ ',None:'? '}
        widget.set_text('\n'.join(marks[ok]+text for ok,text in lines) if lines else '');return False

    def load_icons(self,images,generation):
        """Icons and box art arrive in the background; rows keep their layout meanwhile."""
        def work():
            from concurrent.futures import ThreadPoolExecutor
            def one(pair):
                item,image=pair
                if generation!=self.catalog_generation:return
                try:path=ports.icon_path(self.store,item)
                except Exception:path=''
                if path:GLib.idle_add(self.show_icon,image,path,generation)
            with ThreadPoolExecutor(6) as pool:list(pool.map(one,images))
        threading.Thread(target=work,daemon=True).start()

    def show_icon(self,image,path,generation):
        if generation!=self.catalog_generation:return False
        try:image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(path,ICON_SIZE,ICON_SIZE,True))
        except GLib.Error:pass
        return False

    def add_repository_dialog(self):
        from .gui import label
        dialog=Gtk.Dialog(title='Agregar repositorio',transient_for=self,modal=True);dialog.set_default_size(640,360);dialog.add_button('Cancelar',Gtk.ResponseType.CANCEL);save=dialog.add_button('Agregar',Gtk.ResponseType.OK);save.get_style_context().add_class('primary')
        box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(10)
        box.pack_start(label('Cualquier proyecto de GitHub con releases para Linux: dirección completa o «usuario/repositorio».','muted'),False,False,0)
        repo=Gtk.Entry();repo.set_placeholder_text('https://github.com/usuario/proyecto');box.pack_start(repo,False,False,0)
        name=Gtk.Entry();name.set_placeholder_text('Nombre (opcional)');box.pack_start(name,False,False,0)
        category=Gtk.ComboBoxText.new_with_entry()
        for value in ('PlayStation','PlayStation 2','Nintendo 64','GameCube','Wii','Xbox 360','Otros'):category.append_text(value)
        category.get_child().set_placeholder_text('Plataforma o categoría');box.pack_start(category,False,False,0)
        note=Gtk.Entry();note.set_placeholder_text('Nota (opcional), por ejemplo: necesita el disco original');box.pack_start(note,False,False,0)
        status=label('','status');box.pack_start(status,False,False,0);dialog.show_all()
        while dialog.run()==Gtk.ResponseType.OK:
            parsed=ports.parse_repository(repo.get_text())
            if not parsed:status.set_text('Dirección no válida. Usar https://github.com/usuario/proyecto o usuario/repositorio.');continue
            status.set_text('Consultando GitHub…')
            while Gtk.events_pending():Gtk.main_iteration()
            try:
                release=ports.release_for(parsed);asset=ports.pick_asset(release.get('assets',[]))
            except Exception as error:
                status.set_text('No se pudo consultar el repositorio: '+str(error));continue
            if asset is None and not self.confirm('Sin archivo para Linux','La última versión de '+parsed+' no incluye un archivo para Linux x86_64 reconocible. Se puede agregar igual, pero no se podrá instalar desde aquí hasta que lo publique.','Agregar igual'):continue
            item={'repository':parsed,'name':name.get_text().strip() or parsed.split('/')[1],'category':(category.get_active_text() or '').strip(),'note':note.get_text().strip()}
            clean=ports.clean(item,'','Agregado')
            custom=[c for c in self.preferences.get('custom_ports',[]) if str(c.get('repository','')).lower()!=parsed.lower()]
            custom.append({'repository':clean['repository'],'name':clean['name'],'category':clean['list'],'note':clean['note'],'folderName':clean['folder']})
            self.preferences['custom_ports']=custom;save_settings(self.preferences,self.store);self.set_status(clean['name']+' agregado al catálogo.');break
        dialog.destroy()
        if hasattr(self,'catalog_apps'):self.fill_catalog()

    def remove_repository(self,item):
        if not self.confirm('Quitar de la lista',item['name']+' deja de aparecer en el catálogo. Lo ya instalado no se modifica.','Quitar',danger=True):return
        self.preferences['custom_ports']=[c for c in self.preferences.get('custom_ports',[]) if str(c.get('repository','')).lower()!=item['repository'].lower()];save_settings(self.preferences,self.store);self.fill_catalog()

    def install_port(self,item,replace):
        from . import buildenv
        if getattr(self,'port_busy',False):self.set_status('Ya hay una instalación en curso.');return
        needs_sdk=item.get('kit') and not buildenv.installed()
        if needs_sdk and not self.confirm('Entorno de compilación','Este port compila el juego en la Deck a partir del disco propio. Para eso hace falta el SDK de KDE '+buildenv.BRANCH+' de Flatpak (descarga de Flathub, varios cientos de MB hasta unos GB). Se instala una sola vez para este usuario y no modifica SteamOS.','Instalar y continuar'):return
        self.port_busy=True;self.set_status('Instalando '+item['name']+'…')
        def work():
            try:
                if needs_sdk:buildenv.install(lambda text:GLib.idle_add(self.set_status,'SDK de KDE: '+text))
                record=ports.install(item,self.store,progress=lambda text:GLib.idle_add(self.set_status,text),replace=replace);GLib.idle_add(self.port_installed,item,record)
            except Exception as error:GLib.idle_add(self.port_failed,item,str(error))
        threading.Thread(target=work,daemon=True).start()

    def port_installed(self,item,record):
        self.port_busy=False
        if record.get('setup'):
            self.set_status(item['name']+' instalado. Preparando la configuración…');self.configure_port(item,automatic=True)
        elif record.get('sandbox'):self.message(item['name']+' instalado','Abrirlo desde la biblioteca inicia el asistente: pide el disco y la BIOS propios y compila el juego dentro del SDK de KDE (la primera vez tarda varios minutos). Después se agrega a Steam como cualquier otro juego.')
        elif record['executable']:self.set_status(f'{item["name"]} {record["tag"]} instalado.')
        else:self.message('Ejecutable no identificado',f'{item["name"]} se instaló en ~/ports/{record["folder"]}, pero hay varios ejecutables posibles. Elegir el correcto con «Agregar juegos → Elegir un juego o una app».')
        if getattr(self,'update_state',None):self.update_state['catalog']=[u for u in self.update_state.get('catalog') or [] if u['repository']!=item['repository']];self.refresh_update_badges()
        self.discover()
        if self.pages.get_visible_child_name()=='catalog':self.fill_catalog()
        return False

    def configure_port(self,item,automatic=False):
        """Configure an installed port with the library's disc and the BIOS found by hash, then add it to the library."""
        from . import buildenv
        record=ports.records(self.store).get(item['repository'])
        if not record or not record.get('setup'):return
        if getattr(self,'port_busy',False):self.set_status('Ya hay una tarea en curso.');return
        games=[(e.name,e.source) for e in self.entries if e.source]
        lines=ports.requirements(record,games)
        missing=[text for ok,text in lines if ok is False]
        if missing:
            self.message('Falta algo para configurar '+item['name'],'\n\n'.join(missing)+'\n\nCuando esté disponible, usar «Configurar» en el catálogo.');self.set_status(item['name']+': faltan requisitos.');return
        needs_sdk=record['setup'] in ('kit','openpete') and not buildenv.installed()
        used=next((text for ok,text in lines if ok and text.startswith('Disco')),'')
        question='Se va a configurar '+item['name']+' con lo que ya está en la Deck.\n\n'+'\n'.join(text for ok,text in lines)+'\n\n'+('Compila el juego dentro del SDK de KDE; el kit de Spider-Man tarda unos minutos. ' if record['setup'] in ('kit','openpete') else '')+('Antes se instalará el SDK de KDE de Flatpak (una sola vez). ' if needs_sdk else '')+'Los discos originales no se modifican.'
        if not self.confirm('Configurar '+item['name'],question,'Configurar'):return
        self.port_busy=True;self.set_status('Configurando '+item['name']+'…')
        def work():
            try:
                if needs_sdk:buildenv.install(lambda text:GLib.idle_add(self.set_status,'SDK de KDE: '+text))
                done=ports.configure(item['repository'],self.store,games,lambda text:GLib.idle_add(self.set_status,item['name']+': '+text))
                GLib.idle_add(self.port_configured,item,done)
            except Exception as error:GLib.idle_add(self.port_failed,item,str(error))
        threading.Thread(target=work,daemon=True).start()

    def port_configured(self,item,record):
        self.port_busy=False;self.set_status(item['name']+' configurado con «'+record.get('configured_with','')+'».');self.discover()
        notes={'ctr':'La primera vez, CTR pregunta por una fuente opcional (elegir «Use Luckiest Guy») y por un preset de gráficos.','openpete':'El juego ya está compilado. Se abre en pantalla completa.','kit':'El juego ya está compilado y listo para jugar.'}
        if notes.get(record.get('setup')):self.message(item['name']+' listo',notes[record['setup']]+' Se puede agregar a Steam desde la biblioteca.')
        if self.pages.get_visible_child_name()=='catalog':self.fill_catalog()
        return False

    def port_failed(self,item,text):
        self.port_busy=False;self.set_status('No se pudo instalar '+item['name']+'.');self.message('Instalación de '+item['name'],text);return False
