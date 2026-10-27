"""Community port catalog page: browse, install and update ports from GitHub releases."""
import pathlib,threading,time,datetime,json
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib,GdkPixbuf,Pango
from .inline_pages import InlineDialog
from . import ports
from .installations import save_settings
from .service import queue_removals
from .ui_components import badge,badge_row

ART_WIDTH=88
CATALOG_PAGE=30
ART_HEIGHT=132

def fit_badge(fit,long=False):
    s=fit['score']
    if long:return {'alta':f'Compatibilidad estimada: {s}% · Alta','media':f'Compatibilidad estimada: {s}% · Media','baja':f'Compatibilidad estimada: {s}% · Baja','muy baja':f'Compatibilidad estimada: {s}% · Muy baja'}[fit['level']]
    return {'alta':f'Compatibilidad {s}% · Alta','media':f'Compatibilidad {s}% · Media','baja':f'Compatibilidad {s}% · Baja','muy baja':f'Compatibilidad {s}% · Muy baja'}[fit['level']]

def compatibility_badge(fit,long=False):
    tone={'alta':'green','media':'yellow','baja':'orange','muy baja':'red'}[fit['level']]
    widget=badge(fit_badge(fit,long),tone,60 if long else 32)
    widget.get_style_context().add_class('compatibility-badge')
    widget.set_tooltip_text(fit_badge(fit,True));return widget

OS_LABELS={'macos':'macOS','ios':'iOS','pc':'PC'}

def system_tags(item):
    return [('Linux / Steam Deck' if name.lower()=='linux' else OS_LABELS.get(name.lower(),name.capitalize()),{'linux':'green','windows':'blue','macos':'violet','mac':'violet','android':'yellow'}.get(name.lower(),'neutral')) for name in item.get('supported_os',[])] or [('Sistemas sin confirmar','neutral')]

class CatalogMixin:
    def catalog_page(self):
        from .gui import label,button
        if getattr(self,'catalog_ready',False):self.pages.set_visible_child_name('catalog');return
        self.catalog_ready=True
        box=self.catalog_box;self.reset_page(box)
        head=Gtk.Box(spacing=12);titles=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
        titles.pack_start(label('Catálogo de ports','hero'),False,False,0)
        intro=label('Catálogos públicos, recomendados y repositorios propios. Se instalan en ~/ports desde la última versión publicada en GitHub. La mayoría necesita los archivos del juego original.','subtitle');intro.set_tooltip_text(intro.get_text())
        if self.compact_screen():intro.set_line_wrap(False);intro.set_ellipsize(Pango.EllipsizeMode.END);intro.set_max_width_chars(60)
        titles.pack_start(intro,False,False,0)
        head.pack_start(titles,True,True,0);actions=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL if self.compact_screen() else Gtk.Orientation.VERTICAL,spacing=8);actions.set_valign(Gtk.Align.CENTER)
        actions.pack_start(button('Agregar repositorio',lambda _:self.add_repository_dialog(),True),False,False,0);actions.pack_start(button('Actualizar listas',lambda _:self.load_catalog(True)),False,False,0)
        head.pack_end(actions,False,False,0);box.pack_start(head,False,False,0)
        box.pack_start(button('Juegos validados en Steam Deck',lambda _:self.validated_page()),False,False,0)
        tools=Gtk.Box(spacing=10);self.catalog_search=Gtk.SearchEntry();self.catalog_search.set_placeholder_text('Buscar ports · X: teclado');self.bind_search_keyboard(self.catalog_search);self.catalog_search.connect('search-changed',lambda _:self.fill_catalog());tools.pack_start(self.catalog_search,True,True,0)
        self.catalog_category=Gtk.ComboBoxText();self.catalog_category.get_accessible().set_name('Categoría de ports');self.catalog_category.append('','Todas las categorías');self.catalog_category.set_active_id('');self.catalog_category.connect('changed',lambda _:self.fill_catalog());tools.pack_start(self.catalog_category,False,False,0)
        self.catalog_source=Gtk.ComboBoxText();self.catalog_source.get_accessible().set_name('Fuente de ports');self.catalog_source.append('','Todas las fuentes')
        for name in ('Recomendado','Agregado','Quiver','GithubLauncher','Lista independiente','PortIntegration'):self.catalog_source.append(name,name)
        self.catalog_source.set_active_id('');self.catalog_source.connect('changed',lambda _:self.fill_catalog());tools.pack_start(self.catalog_source,False,False,0);box.pack_start(tools,False,False,0)
        self.catalog_sort=Gtk.ComboBoxText();self.catalog_sort.get_accessible().set_name('Orden de ports')
        for key,name in [('recent','Nuevos primero'),('new','Nuevos (30 días)'),('release','Últimas versiones'),('name','Nombre'),('installed','Instalados')]:self.catalog_sort.append(key,name)
        self.catalog_sort.set_active_id(self.preferences.get('catalog_sort','recent'));self.catalog_sort.connect('changed',lambda _:self.fill_catalog());tools.pack_start(self.catalog_sort,False,False,0)
        self.catalog_search.set_width_chars(12)
        for picker in (self.catalog_category,self.catalog_source,self.catalog_sort):
            for cell in picker.get_cells():cell.set_property('ellipsize',Pango.EllipsizeMode.END);cell.set_property('max-width-chars',18)
        status_row=Gtk.Box(spacing=12);self.catalog_status=label('Cargando catálogo…','status');self.catalog_status.set_line_wrap(False);self.catalog_status.set_ellipsize(Pango.EllipsizeMode.END);self.catalog_status.set_width_chars(1);status_row.pack_start(self.catalog_status,True,True,0)
        self.catalog_guide_button=button('Guía de compatibilidad',self.compatibility_guide);status_row.pack_end(self.catalog_guide_button,False,False,0);box.pack_start(status_row,False,False,0)
        self.catalog_rows=Gtk.FlowBox();self.catalog_rows.set_selection_mode(Gtk.SelectionMode.NONE);self.catalog_rows.set_min_children_per_line(1);self.catalog_rows.set_max_children_per_line(4);self.catalog_rows.set_homogeneous(True);self.catalog_rows.set_column_spacing(14);self.catalog_rows.set_row_spacing(16);box.pack_start(self.catalog_rows,False,False,0)
        self.catalog_more_box=Gtk.Box();self.catalog_more_box.set_halign(Gtk.Align.CENTER);box.pack_start(self.catalog_more_box,False,False,0)
        box.show_all();self.pages.set_visible_child_name('catalog');self.load_catalog(False)

    def compatibility_guide(self,*_):
        from .gui import label
        page=InlineDialog(title='Guía de compatibilidad',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE);box=page.get_content_area()
        box.pack_start(label('Es un índice orientativo de 0 a 100 basado en los datos del catálogo. Se muestra como porcentaje para comparar proyectos; no es una probabilidad medida ni una tasa de éxito.','subtitle'),False,False,0)
        box.pack_start(label('No mide FPS, calidad gráfica ni resultados de pruebas de juego. «Integración revisada» indica que se revisó su instalación; no confirma que el juego funcione.','muted'),False,False,0)
        box.pack_start(label('La marca de juego verificado corresponde al repositorio y a la versión de una prueba registrada. No se hereda entre variantes ni versiones. Sin validar significa que faltan pruebas, no que sea incompatible.','muted'),False,False,0)
        box.pack_start(badge_row([('Alta · 80–100%','green'),('Media · 55–79%','yellow'),('Baja · 30–54%','orange'),('Muy baja · 0–29%','red')]),False,False,0)
        base=self.card(box,'Puntuación de partida')
        base.pack_start(label('Se usa la primera condición que corresponda, en este orden:','meta'),False,False,0)
        for caption,value in [('Solo código fuente o herramienta de compilación','8 · fijo'),('Constructor del juego a partir de archivos propios','25'),('Integración revisada por Deck Library','88'),('Versión declarada para Linux','72'),('Versión para Windows, con Proton sin comprobar','50'),('Otros sistemas, sin Linux ni Windows','8'),('Sistemas sin declarar','40')]:
            row=Gtk.Box(spacing=12);row.pack_start(label(caption),True,True,0);row.pack_end(badge(value),False,False,0);base.pack_start(row,False,False,0)
        modifiers=self.card(box,'Ajustes sobre esa puntuación')
        for caption,value,tone in [('La fuente declara totalmente jugable o nativo','+8','green'),('La fuente declara jugable','+3','green'),('La fuente declara en desarrollo','−8','orange'),('Sin versión ni fecha conocidas, si no está revisado','−15','red'),('Última versión de hace más de dos años','−8','orange'),('Versión publicada en los últimos 180 días','+3','green'),('Requiere originales, BIOS o preparación según el catálogo','−5','orange')]:
            row=Gtk.Box(spacing=12);row.pack_start(label(caption),True,True,0);row.pack_end(badge(value,tone),False,False,0);modifiers.pack_start(row,False,False,0)
        modifiers.pack_start(label('El estado de la fuente y la antigüedad aplican una sola variante cada uno. El resultado se limita a 0–100. Las entradas de solo código fuente quedan en 8 y no reciben ajustes.','meta'),False,False,0)
        box.pack_start(label('Los pesos son criterios de Deck Library; no se calibraron contra pruebas de instalación o rendimiento de todo el catálogo. Por ejemplo, Windows con versión publicada (50) y estado jugable (+3), sin otros ajustes, dan 53%, nivel bajo.','muted'),False,False,0)
        page.show_all();page.run();page.destroy()

    def catalog_more(self):
        self.catalog_limit=getattr(self,'catalog_limit',CATALOG_PAGE)+CATALOG_PAGE;self.fill_catalog()

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
        from .port_requirements import original_requirement
        if not hasattr(self,'catalog_apps'):return
        everything=self.catalog_entries();variant_index=self.port_variant_index(everything);categories=sorted({a['list'] for a in everything if a['list']},key=str.casefold);current=self.catalog_category.get_active_id() or ''
        known={row[0] for row in self.catalog_category.get_model()}
        for name in categories:
            if name not in known:self.catalog_category.append(name,name)
        self.reset_page(self.catalog_rows);self.reset_page(self.catalog_more_box);text=self.catalog_search.get_text().casefold().strip();category=self.catalog_category.get_active_id() or '';source=self.catalog_source.get_active_id() or ''
        installed=ports.records(self.store);updates={u['repository'] for u in (getattr(self,'update_state',None) or {}).get('catalog') or []}
        matches=[a for a in everything if text in (' '.join((a['name'],a.get('game_title',''),a['repository'],original_requirement(a)['label']))).casefold() and (not category or a['list']==category) and (not source or source in a['source'])]
        order=self.catalog_sort.get_active_id() or 'recent'
        if self.preferences.get('catalog_sort')!=order:self.preferences['catalog_sort']=order;save_settings(self.preferences,self.store)
        if order=='installed':matches=[a for a in matches if self.catalog_installation(a,installed)]
        if order=='new':matches=[a for a in matches if 0<time.time()-(a.get('added_at') or a.get('first_seen') or 0)<30*86400]
        matches.sort(key=lambda a:(-(a.get('added_at') or a.get('first_seen') or 0) if order in ('recent','new') else -(a.get('release_at') or 0) if order=='release' else 0,(a.get('game_title') or a['name']).casefold(),a['name'].casefold()))
        key=(text,category,source,order)
        if getattr(self,'catalog_filter_key',None)!=key:self.catalog_filter_key=key;self.catalog_limit=CATALOG_PAGE
        limit=getattr(self,'catalog_limit',CATALOG_PAGE)
        self.catalog_status.set_text(f'{len(matches)} de {len(everything)} ports'+(f' · se muestran los primeros {limit}' if len(matches)>limit else ''))
        try:
            snapshot=json.loads((self.store.root/'catalog-ports.json').read_text());stamp=snapshot.get('time',0)
            self.catalog_status.set_text(self.catalog_status.get_text()+' · '+('copia guardada' if snapshot.get('offline') else 'Actualizado '+datetime.datetime.fromtimestamp(stamp).strftime('%d/%m %H:%M')))
        except (OSError,ValueError):pass
        self.catalog_generation=getattr(self,'catalog_generation',0)+1;generation=self.catalog_generation;images=[];kits=[]
        from .ui_components import PortImage
        compact=self.compact_screen()
        for item in matches[:limit]:
            card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0);card.set_size_request(270,-1);card.get_style_context().add_class('port-card');open_=button('',lambda _,i=item:self.port_details(i));open_.get_style_context().add_class('catalog-open');body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0);open_.remove(open_.get_child());open_.add(body);card.pack_start(open_,False,False,0)
            image=PortImage();body.pack_start(image,False,False,0);images.append((item,image))
            title=item.get('game_title') or item['name'];image.get_accessible().set_name('Carátula de '+title)
            open_.get_accessible().set_name('Ver detalles de '+title)
            texts=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);texts.get_style_context().add_class('port-card-content');heading=label(title,'title');heading.set_lines(2);heading.set_max_width_chars(23);heading.set_ellipsize(Pango.EllipsizeMode.END);texts.pack_start(heading,False,False,0);record=installed.get(item['repository']) or self.catalog_installation(item,installed)
            if title.casefold()!=item['name'].casefold():
                project=label(item['name'],'meta');project.set_lines(1);project.set_ellipsize(Pango.EllipsizeMode.END);project.set_max_width_chars(26);texts.pack_start(project,False,False,0)
            if item.get('description'):
                description=label(item['description'],'status');description.set_lines(1 if compact else 2);description.set_max_width_chars(30);description.set_ellipsize(Pango.EllipsizeMode.END);texts.pack_start(description,False,False,0)
            original=original_requirement(item);requirement=badge(('ROM · '+original['label']) if original['known'] else original['label'],'yellow' if original['known'] else 'neutral');requirement.set_tooltip_text(original['details']);texts.pack_start(requirement,False,False,0)
            fit=ports.compatibility(item);reviewed=ports.is_reviewed(item);tags=([(item['list'],'violet')] if item['list'] else [])+[('Integración revisada','blue') if reviewed else ('Integración sin revisar','neutral')]
            role=item.get('package_role')
            if role=='builder':tags.append(('Constructor','yellow'))
            elif role in ('source-only','build-tool'):tags.append(('Solo código fuente','orange'))
            texts.pack_start(badge_row(system_tags(item)),False,False,0)
            proof=variant_index.assess(item);texts.pack_start(self.variant_badge(proof),False,False,0)
            alternatives=variant_index.alternatives(item)
            if alternatives:tags.append((str(len(alternatives)+1)+' variantes','blue'))
            if record:
                other=record.get('alternative',False);tone='yellow' if other else variant_index.assess(item,record.get('tag',''))['tone']
                texts.pack_start(badge('Variante instalada sin identificar' if record.get('unidentified') else 'Otra variante instalada' if other else 'Instalado · '+record['tag'],tone),False,False,0)
            when=item.get('added_at') or item.get('first_seen') or 0
            if when:
                recent=time.time()-when<30*86400;tags.append((('Nuevo · ' if recent else 'Agregado ')+datetime.datetime.fromtimestamp(when).strftime('%d/%m/%Y'),'blue' if recent else 'neutral'))
            texts.pack_start(badge_row(tags),False,False,0)
            texts.pack_start(compatibility_badge(fit),False,False,0)
            if item['note']:
                note=label(item['note'],'status');note.set_lines(2);note.set_max_width_chars(30);note.set_ellipsize(Pango.EllipsizeMode.END);texts.pack_start(note,False,False,0)
            if item.get('bios') or item.get('disc'):
                checks=label('Comprobando requisitos…','status');texts.pack_start(checks,False,False,0);kits.append((item,checks))
            body.pack_start(texts,False,False,0);side=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);side.get_style_context().add_class('port-card-actions');card.pack_end(side,False,False,0)
            if proof.get('report') and proof['report']['repository'].casefold()!=item['repository'].casefold():
                target=variant_index.items.get(proof['report']['repository'].casefold())
                if target:side.pack_start(button('Ver variante probada',lambda _,i=target:self.port_details(i)),False,False,0)
            if item.get('package_role') in ('source-only','build-tool'):side.pack_start(button('Ver requisitos',lambda _,i=item:self.port_details(i)),False,False,0)
            elif record and record.get('external'):
                side.pack_start(label('Variante instalada sin identificar' if record.get('unidentified') else 'Otra variante instalada' if record.get('alternative') else 'Port ya instalado','meta'),False,False,0)
                side.pack_start(button('Ver en biblioteca',lambda _,r=record:self.select_game(r['entry'])),False,False,0)
                if record.get('alternative'):side.pack_start(button('Instalar alternativa',lambda _,i=item:self.install_port(i,False)),False,False,0)
            elif record and item['repository'] in updates:side.pack_start(button('Actualizar',lambda _,i=item:self.install_port(i,True),True),False,False,0)
            elif record and item.get('multi_appimage') and installed.get(item['repository']) and not installed[item['repository']].get('games'):side.pack_start(button('Instalar todos los juegos',lambda _,i=item:self.install_port(i,True),True),False,False,0)
            elif record and record.get('setup') and not record.get('configured'):side.pack_start(button('Configurar',lambda _,i=item:self.configure_port(i),True),False,False,0)
            elif record and record.get('setup'):
                side.pack_start(label('Configurado','good'),False,False,0)
                if record.get('setup')=='kit' and record.get('patch_level',0)<ports.PATCH_LEVEL:side.pack_start(button('Mejorar rendimiento',lambda _,i=item:self.configure_port(i),True),False,False,0)
                else:side.pack_start(button('Volver a configurar',lambda _,i=item:self.configure_port(i)),False,False,0)
                if record.get('setup')=='wwhd':side.pack_start(button('Preparar shaders',lambda _:self.prepare_shaders()),False,False,0)
            elif record:
                side.pack_start(label('Instalado','good'),False,False,0)
                if item.get('preparation')=='launcher':
                    side.pack_start(label('Asistente del port','meta'),False,False,0);side.pack_start(button('Abrir port',lambda _,r=record:self.open_installed_port(r)),False,False,0)
                elif item.get('preparation')=='manual':side.pack_start(button('Ver preparación',lambda _,i=item:self.port_details(i)),False,False,0)
            else:side.pack_start(button('Instalar',lambda _,i=item:self.install_port(i,False)),False,False,0)
            if installed.get(item['repository']) and item['repository']!='GenryTheFox0/Project-2099':side.pack_start(button('Desinstalar',lambda _,i=item:self.uninstall_port(i),tone='danger'),False,False,0)
            if 'Agregado' in item['source']:side.pack_start(button('Quitar de la lista',lambda _,i=item:self.remove_repository(i),tone='danger'),False,False,0)
            card.catalog_open=open_;card.catalog_image=image;self.catalog_rows.add(card);wrapper=card.get_parent();wrapper.set_can_focus(False);wrapper.catalog_open=open_;wrapper.catalog_image=image
            self.transfer_row(card,item['repository'])
        if len(matches)>limit:
            more=button(f'Mostrar {min(CATALOG_PAGE,len(matches)-limit)} más',lambda _:self.catalog_more());self.catalog_more_box.pack_start(more,False,False,6)
        self.catalog_rows.show_all();self.catalog_more_box.show_all();self.load_icons(images,generation);self.check_kits(kits,generation)
        self.queue_resize();GLib.idle_add(self.check_resize)

    def port_details(self,item):
        from .gui import label,button
        import subprocess
        item=ports.clean(item)
        title=item.get('game_title') or item['name'];page=InlineDialog(title=title,transient_for=self);page.port_repository=item['repository'];page.add_button('Volver al catálogo',Gtk.ResponseType.CLOSE)
        box=page.get_content_area();hero=Gtk.Box(spacing=20);detail_art=(96,144) if self.compact_screen() else (132,198);image=Gtk.Image.new_from_icon_name('applications-games-symbolic',Gtk.IconSize.DIALOG);image.set_size_request(*detail_art);image.set_valign(Gtk.Align.START);hero.pack_start(image,False,False,0)
        text=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        tool='utilit' in item.get('list','').casefold()
        heading=item.get('game_title') or ('Herramienta para ports' if tool else item['name']);text.pack_start(label(heading,'game-title'),False,False,0)
        if heading.casefold()!=item['name'].casefold():text.pack_start(label('Port: '+item['name'],'subtitle'),False,False,0)
        facts=[(item['list'] or 'Plataforma sin especificar','violet'),*system_tags(item)]
        if item['source']:facts.append((item['source'],'neutral'))
        text.pack_start(badge_row(facts),False,False,0)
        fit=ports.compatibility(item);text.pack_start(compatibility_badge(fit,True),False,False,0)
        text.pack_start(label(' '.join(fit['reasons'])+' Estimación a partir de los datos del catálogo; no es una prueba de juego.','muted'),False,False,0)
        text.pack_start(button('Cómo se calcula',self.compatibility_guide),False,False,0)
        if item.get('release_version'):text.pack_start(label('Versión disponible: '+item['release_version'],'muted'),False,False,0)
        if item.get('release_at'):text.pack_start(label('Publicada el '+datetime.datetime.fromtimestamp(item['release_at']).strftime('%d/%m/%Y'),'muted'),False,False,0)
        hero.pack_start(text,True,True,0);box.pack_start(hero,False,False,0)
        evidence=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);box.pack_start(evidence,False,False,0);variant_index=self.port_variant_index()
        def refresh_evidence(tag=None):
            if page._closed:return False
            self.reset_page(evidence);candidate={**item,**({'release_version':tag} if tag else {})};self.build_port_evidence(evidence,candidate,page,variant_index);evidence.show_all();self.refresh_layout();return False
        refresh_evidence()
        if item.get('description'):box.pack_start(label(item['description'],'subtitle'),False,False,0)
        if item.get('note'):box.pack_start(label(item['note'],'muted'),False,False,0)
        from .port_requirements import original_requirement
        requirement=original_requirement(item);originals=self.card(box,'ROM y versión necesarias');originals.pack_start(label(requirement['label'],'title'),False,False,0);originals.pack_start(label(requirement['details'],'muted'),False,False,0)
        if requirement['source']:originals.pack_start(Gtk.LinkButton.new_with_label(requirement['source'],'Requisitos del proyecto'),False,False,0)
        status=label('Cargando imagen…','meta');box.pack_start(status,False,False,0)
        def artwork(force=False):
            status.set_text('Cargando imagen…');retry.hide()
            def done(path,error):
                if page._closed:return False
                try:
                    if path:image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(path,detail_art[0],detail_art[1],True));status.set_text('');retry.hide()
                    else:status.set_text(error or 'La fuente no tiene una imagen disponible.');retry.show()
                except GLib.Error:status.set_text('No se pudo mostrar la imagen.');retry.show()
                return False
            def work():
                try:GLib.idle_add(done,ports.icon_path(self.store,item,force=force),'')
                except Exception:GLib.idle_add(done,'','No se pudo descargar la imagen. Se puede volver a intentar.')
            threading.Thread(target=work,daemon=True).start()
        retry=button('Reintentar imagen',lambda _:artwork(True));retry.get_style_context().add_class('quiet');retry.set_halign(Gtk.Align.START);retry.set_no_show_all(True);retry.hide();box.pack_start(retry,False,False,0)
        checks=label('Comprobando requisitos…','status');box.pack_start(checks,False,False,0)
        package=label('Comprobando el paquete de instalación…','meta');box.pack_start(package,False,False,0)
        from .port_recipes import preparation
        _,preparation_text=preparation(item);box.pack_start(label(preparation_text,'muted'),False,False,0)
        if item.get('source_note'):box.pack_start(label(item['source_note'],'muted'),False,False,0)
        primary_action=[None]
        def proton_install(_):
            page.response(Gtk.ResponseType.CLOSE);GLib.idle_add(lambda:(self.install_port(item,bool(ports.records(self.store).get(item['repository'])),runtime='proton'),False)[1])
        proton_button=button('Instalar con Proton',proton_install,True);proton_button.set_no_show_all(True);proton_button.hide();page.get_action_area().pack_start(proton_button,False,False,0)
        games=[(e.name,e.source) for e in self.entries if e.source]
        def requirements():
            try:lines=ports.requirements(item,games)
            except Exception:lines=[]
            def show():
                if not page._closed:checks.set_text('\n'.join(('✓ ' if ok is True else '✗ ' if ok is False else '')+message for ok,message in lines) or ('Herramienta independiente.' if tool else 'Puede necesitar archivos del juego original. Consultar los requisitos del proyecto.'))
                return False
            GLib.idle_add(show)
        threading.Thread(target=requirements,daemon=True).start()
        def package_info():
            from . import port_packages
            try:
                if item['repository']=='GenryTheFox0/Project-2099':info='Instalador integrado · Xbox 360 → Project 2099 · respaldo completo al actualizar.'
                elif item.get('package_role') in ('source-only','build-tool'):
                    info=item.get('source_note','Solo código fuente. Requiere compilación.')
                    def unavailable():
                        if not page._closed and primary_action[0]:primary_action[0].set_label('Requiere compilación' if item.get('package_role')=='build-tool' else 'Sin paquete publicado');primary_action[0].set_sensitive(False)
                        return False
                    GLib.idle_add(unavailable)
                elif item.get('web'):info='Instalador integrado · '+item['web']['kind']
                else:
                    release=ports.release_for(item['repository']);plan=ports.package_plan(item,release.get('assets',[]));proton_plan=ports.package_plan(item,release.get('assets',[]),runtime='proton');info=port_packages.summary(plan)
                    if plan:info+='\n'+plan['asset']['name']+' · '+release.get('tag_name','')
                    def offer():
                        if page._closed:return False
                        refresh_evidence(release.get('tag_name',''))
                        if proton_plan and (not plan or plan['runtime']!='proton'):proton_button.set_no_show_all(False);proton_button.show_all();proton_button.set_no_show_all(True)
                        if primary_action[0] and plan and plan['runtime']=='proton':primary_action[0].set_label('Instalar con Proton')
                        if primary_action[0] and not plan:primary_action[0].set_sensitive(False)
                        return False
                    GLib.idle_add(offer)
            except Exception:info='No se pudo comprobar el paquete. Se volverá a consultar al instalar.'
            def show():
                if not page._closed:package.set_text(info)
                return False
            GLib.idle_add(show)
        threading.Thread(target=package_info,daemon=True).start()
        repository=label(item['repository'],'muted');repository.set_selectable(True);box.pack_start(repository,False,False,0)
        if ports.valid_repository(item['repository']) and not item.get('web'):
            box.pack_start(button('Abrir proyecto en GitHub',lambda _:subprocess.Popen(['xdg-open','https://github.com/'+item['repository']],start_new_session=True)),False,False,0)
        installed=ports.records(self.store);record=installed.get(item['repository']) or self.catalog_installation(item,installed)
        updates={u['repository'] for u in (getattr(self,'update_state',None) or {}).get('catalog') or []}
        if record and record.get('external'):
            def library(_):page.response(Gtk.ResponseType.CLOSE);GLib.idle_add(lambda:(self.select_game(record['entry']),False)[1])
            page.get_action_area().pack_start(button('Ver en biblioteca',library,True),False,False,0)
        elif record and item['repository'] in updates:
            def update(_):page.response(Gtk.ResponseType.CLOSE);GLib.idle_add(lambda:(self.install_port(item,True),False)[1])
            page.get_action_area().pack_start(button('Actualizar',update,True),False,False,0)
        elif record and record.get('setup') and not record.get('configured'):
            page.get_action_area().pack_start(button('Configurar',lambda _:(page.response(Gtk.ResponseType.CLOSE),GLib.idle_add(lambda:(self.configure_port(item),False)[1])),True),False,False,0)
        elif record:
            box.pack_start(label('Instalado · '+record.get('tag',''),'good'),False,False,0)
            self.iso_cleanup_button(box,item,record)
            if installed.get(item['repository']) and item['repository']!='GenryTheFox0/Project-2099':page.get_action_area().pack_start(button('Desinstalar',lambda _:(page.response(Gtk.ResponseType.CLOSE),GLib.idle_add(lambda:(self.uninstall_port(item),False)[1])),tone='danger'),False,False,0)
            if item.get('preparation')=='launcher':page.get_action_area().pack_start(button('Abrir port',lambda _:(page.response(Gtk.ResponseType.CLOSE),GLib.idle_add(lambda:(self.open_installed_port(record),False)[1]))),False,False,0)
        else:
            def install(_):page.response(Gtk.ResponseType.CLOSE);GLib.idle_add(lambda:(self.install_port(item,False),False)[1])
            primary_action[0]=button('Instalar',install,True);page.get_action_area().pack_start(primary_action[0],False,False,0)
        if installed.get(item['repository']) and item['repository'].casefold()!='genrythefox0/project-2099':
            def delete_port(_):
                page.response(Gtk.ResponseType.CLOSE)
                GLib.idle_add(lambda:(self.delete_port_permanently(item),False)[1])
            box.pack_start(button('Eliminar completamente',delete_port,tone='danger'),False,False,0)
        self.transfer_row(box,item['repository']);page.show_all();artwork();page.run();page.destroy()

    def prepare_shaders(self):
        from . import ports
        self.set_status('Preparando los shaders de Wind Waker HD…')
        def work():
            result=ports.prepare_wwhd_shaders(progress=lambda t:GLib.idle_add(self.set_status,'Shaders: '+t[-120:]))
            def done():
                self.set_status(result['message']);self.message('Wind Waker HD · shaders',result['message']);return False
            GLib.idle_add(done)
        threading.Thread(target=work,daemon=True).start()

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
        try:
            from .ui_components import PortImage
            width,height=image.get_size_request();image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(path,900 if isinstance(image,PortImage) else width if width>0 else ART_WIDTH,600 if isinstance(image,PortImage) else height if height>0 else ART_HEIGHT,True))
        except GLib.Error:pass
        return False

    def add_repository_dialog(self):
        from .gui import label
        dialog=InlineDialog(title='Agregar repositorio',transient_for=self,modal=True);dialog.set_default_size(640,360);dialog.add_button('Cancelar',Gtk.ResponseType.CANCEL);save=dialog.add_button('Agregar',Gtk.ResponseType.OK);save.get_style_context().add_class('primary')
        box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(10)
        box.pack_start(label('Proyectos de GitHub con paquetes para Linux o Windows portable: dirección completa o «usuario/repositorio».','muted'),False,False,0)
        repo=Gtk.Entry();repo.set_placeholder_text('https://github.com/usuario/proyecto');box.pack_start(repo,False,False,0)
        name=Gtk.Entry();name.set_placeholder_text('Nombre (opcional)');box.pack_start(name,False,False,0)
        category=Gtk.ComboBoxText.new_with_entry()
        for value in ('PlayStation','PlayStation 2','Nintendo 64','GameCube','Wii','Xbox 360','Otros'):category.append_text(value)
        category.get_child().set_placeholder_text('Plataforma o categoría');box.pack_start(category,False,False,0)
        note=Gtk.Entry();note.set_placeholder_text('Nota (opcional), por ejemplo: necesita el disco original');box.pack_start(note,False,False,0)
        status=label('','status');box.pack_start(status,False,False,0);self.fit_dialog(dialog);dialog.show_all()
        while dialog.run()==Gtk.ResponseType.OK:
            parsed=ports.parse_repository(repo.get_text())
            if not parsed:status.set_text('Dirección no válida. Usar https://github.com/usuario/proyecto o usuario/repositorio.');continue
            status.set_text('Consultando GitHub…')
            while Gtk.events_pending():Gtk.main_iteration()
            try:
                from .port_packages import select
                release=ports.release_for(parsed);asset=select(release.get('assets',[]))
            except Exception as error:
                status.set_text('No se pudo consultar el repositorio: '+str(error));continue
            if asset is None and not self.confirm('Sin paquete compatible','La última versión de '+parsed+' no incluye un paquete de Linux x86_64 ni Windows portable reconocible. Se puede agregar al catálogo, pero necesita una integración específica para instalarlo.','Agregar igual'):continue
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

    def catalog_installation(self,item,installed=None):
        from .originals import key
        direct=(installed if installed is not None else ports.records(self.store)).get(item['repository'])
        if direct:return direct
        for e in self.entries:
            if e.kind not in ('port','wiicompiled'):continue
            same=e.metadata.get('port_repository','').lower()==item['repository'].lower()
            if same or key(e.name)==key(item.get('game_title') or item['name']):return {'external':True,'alternative':not same,'unidentified':not bool(e.metadata.get('port_repository')),'entry':e,'tag':e.metadata.get('port_tag') or e.metadata.get('build') or '?'}
        return None

    def open_installed_port(self,record):
        entry=ports.entry_for(ports.ports_root()/record['folder'])
        if entry:self.play(entry)
        else:self.message('Port no disponible','No se encontró el ejecutable instalado. Volver a detectar o reinstalar el port.')

    def install_port(self,item,replace,runtime='auto'):
        from . import buildenv
        item=ports.clean(item)
        if getattr(self,'port_busy',False):self.set_status('Ya hay una instalación en curso.');return
        if item['repository']=='GenryTheFox0/Project-2099':
            if any(e.metadata.get('adapter')=='project2099' for e in self.entries):self.update_project2099()
            else:self.project2099_dialog()
            return
        if item.get('package_role') in ('source-only','build-tool'):self.message('Requiere compilación',item.get('source_note','El proyecto solo publica código fuente.'));return
        proof=self.port_variant_index().assess(item)
        if proof['state']=='issue' and not self.confirm('Problema conocido en esta versión',proof['issue'],'Instalar igualmente'):return
        if not ports.is_reviewed(item) and not self.preferences.get('unreviewed_acknowledged'):
            if not self.confirm('Port sin revisar','Este port viene de una lista externa y Deck Library no lo revisó. Se descarga la versión publicada en GitHub y se verifica el tamaño y, cuando el autor la publica, la suma SHA-256; el programa se ejecuta con los permisos del usuario. Esta advertencia se muestra una sola vez.','Instalar'):return
            self.preferences['unreviewed_acknowledged']=True;save_settings(self.preferences,self.store)
        existing=self.catalog_installation(item)
        if existing and existing.get('external') and not replace and not self.confirm('Ya hay un port instalado',existing['entry'].name+' ya está en la biblioteca. ¿Instalar también '+item['name']+' como alternativa?','Instalar alternativa'):return
        needs_sdk=item.get('kit') and not buildenv.installed()
        if needs_sdk and not self.confirm('Entorno de compilación','Este port compila el juego en la Deck a partir del disco propio. Para eso hace falta el SDK de KDE '+buildenv.BRANCH+' de Flatpak (descarga de Flathub, varios cientos de MB hasta unos GB). Se instala una sola vez para este usuario y no modifica SteamOS.','Instalar y continuar'):return
        self.port_busy=True;self.set_status('Instalando '+item['name']+'…')
        if not hasattr(self,'port_jobs'):self.port_jobs={}
        cancel=threading.Event();self.port_jobs[item['repository']]=cancel
        self.start_transfer(item['repository']);progress=self.port_progress(item['repository'])
        def work():
            try:
                if needs_sdk:buildenv.install(lambda text:GLib.idle_add(self.set_status,'SDK de KDE: '+text))
                record=ports.install(item,self.store,progress=progress,transfer=progress,replace=replace,cancel=cancel,runtime=runtime);GLib.idle_add(self.port_installed,item,record)
            except Exception as error:GLib.idle_add(self.port_failed,item,str(error))
        threading.Thread(target=work,daemon=True).start()

    def delete_port_permanently(self,item):
        from . import port_removal
        if getattr(self,'port_busy',False):self.message('Instalación en curso','Esperar a que termine la instalación antes de eliminar un port.');return
        try:value=port_removal.plan(item['repository'],self.store)
        except (OSError,ValueError) as error:self.message('No se pudo preparar la eliminación',str(error));return
        description='Se borran definitivamente el port y los datos de las rutas indicadas: partidas, configuración, entorno de Proton y copias anteriores administradas por Deck Library. Esta acción no se puede deshacer.\n\nLos originales y otros datos guardados fuera de estas rutas se conservan.\n\nArchivos y carpetas que se eliminarán:\n'+'\n'.join(str(path) for path in value['paths'])
        if any(e.metadata.get('steam_appid') for e in value['entries']):description+='\n\nTambién se quita el acceso directo de Steam. Si Steam está abierto, ese cambio se guarda al cerrarlo.'
        if not self.confirm('Eliminar completamente '+value['name'],description,'Eliminar definitivamente',danger=True):return
        self.port_busy=True;self.set_status('Eliminando el port y sus datos…')
        progress=InlineDialog(title='Eliminando el port y sus datos…',transient_for=self);progress.set_deletable(False)
        spinner=Gtk.Spinner();spinner.start();progress.get_content_area().pack_start(spinner,False,False,12);progress._mount()
        def done(result,error):
            self.port_busy=False
            if self.ui_closed:return False
            progress.destroy()
            if error:self.message('No se pudo completar la eliminación',error);return False
            from . import updates
            self.entries=self.store.load();self.checked-=set(result['ids']);self.library_dirty=True;self.update_state=updates.cached(self.store)
            self.refresh_platforms();self.refresh_pending();self.refresh_update_badges()
            removed_selection=self.selected and self.selected.id in result['ids']
            if removed_selection:self.selected=None;self.detail_game_id=None;self.open_library()
            elif self.pages.get_visible_child_name()=='catalog':self.fill_catalog()
            elif self.pages.get_visible_child_name()=='library':self.render()
            self.set_status(result['name']+' eliminado completamente.')
            return False
        def work():
            try:result=port_removal.execute(item['repository'],self.store,expected=value);GLib.idle_add(done,result,None)
            except Exception as error:GLib.idle_add(done,None,str(error))
        threading.Thread(target=work,daemon=True).start()

    def uninstall_port(self,item):
        item=ports.clean(item);record=ports.records(self.store).get(item['repository'])
        if not record:self.message('Sin instalación','Deck Library no instaló este port.');return
        linked=[e for e in self.entries if e.metadata.get('port_repository')==item['repository']];in_steam=[e for e in linked if self.in_steam(e)]
        steam='\n\nTambién se quita su acceso directo de Steam, con su carátula y su configuración de mando.' if in_steam else ''
        if not self.confirm('Desinstalar '+record.get('name',item['name']),'La carpeta ~/ports/'+record['folder']+' se mueve a ~/ports/'+ports.REMOVED+' y el juego sale de la biblioteca. Las partidas guardadas dentro de esa carpeta se van con ella y pueden recuperarse de ahí; nada se borra.'+steam,'Desinstalar',danger=True):return
        try:result=ports.uninstall(item['repository'],self.store)
        except (OSError,ValueError) as error:self.message('No se pudo desinstalar',str(error));return
        accounts={e.metadata['steam_account'] for e in in_steam if e.metadata.get('steam_account')}
        if in_steam and len(accounts)==1:
            account=pathlib.Path(accounts.pop());ids=[e.metadata['steam_appid'] for e in in_steam if e.metadata.get('steam_appid')]
            if ids:self.run_queue(lambda:queue_removals(ids,account,self.store),'Preparando la eliminación del acceso directo…')
        self.entries=self.store.load();self.library_dirty=True;self.checked-={e.id for e in linked};self.refresh_platforms()
        if self.selected and self.selected.id in result['ids']:self.selected=None
        self.set_status(result['name']+' desinstalado. Carpeta guardada en ~/ports/'+ports.REMOVED+'.')
        if self.pages.get_visible_child_name()=='catalog':self.fill_catalog()
        elif self.pages.get_visible_child_name()=='library':self.render()

    def port_installed(self,item,record):
        from . import updates
        self.port_busy=False
        getattr(self,'port_jobs',{}).pop(item['repository'],None)
        updates.port_completed(self.store,item['repository'],record.get('tag',''))
        self.transfer_event(item['repository'],'Descarga verificada; configuración pendiente.' if record.get('setup') else 'Instalación completada.')
        if not record.get('setup'):self.finish_transfer(item['repository'])
        if record.get('setup'):
            self.set_status(item['name']+' instalado. Preparando la configuración…');self.configure_port(item,automatic=True)
        elif record.get('sandbox'):self.message(item['name']+' instalado','Abrirlo desde la biblioteca inicia el asistente: pide el disco y la BIOS propios y compila el juego dentro del SDK de KDE (la primera vez tarda varios minutos). Después se agrega a Steam como cualquier otro juego.')
        elif record['executable']:self.set_status(f'{item["name"]} {record["tag"]} instalado.'+(' Abrir el port para elegir los archivos originales.' if item.get('preparation')=='launcher' else ' Revisar la preparación manual en su ficha.' if item.get('preparation')=='manual' else ''))
        else:self.message('Ejecutable no identificado',f'{item["name"]} se instaló en ~/ports/{record["folder"]}, pero hay varios ejecutables posibles. Elegir el correcto con «Agregar juegos → Elegir un juego o una app».')
        if getattr(self,'update_state',None):self.update_state['catalog']=[u for u in self.update_state.get('catalog') or [] if u['repository']!=item['repository']];self.refresh_update_badges()
        self.discover()
        if not record.get('setup'):self.port_setup_finished(item)
        if self.pages.get_visible_child_name()=='catalog':self.fill_catalog()
        return False

    def port_inputs(self,item):
        from .gui import label,button
        page=InlineDialog(title='Preparar '+item['name'],transient_for=self);page.add_button('Más tarde',Gtk.ResponseType.CANCEL);ready=page.add_button('Preparar',Gtk.ResponseType.OK)
        body=page.get_content_area();summary=label('','muted');body.pack_start(summary,False,False,0)
        error=label('','status');body.pack_start(error,False,False,0)
        record=ports.records(self.store).get(item['repository'],{})
        if item.get('source_note'):body.pack_start(label(item['source_note'],'muted'),False,False,0)
        def refresh():
            record=ports.records(self.store).get(item['repository'],{})
            lines=ports.requirements(record,[(e.name,e.source) for e in self.entries if e.source])
            summary.set_text('\n'.join(('✓ ' if ok else '• ')+value for ok,value in lines))
            ready.set_sensitive(all(ok is True for ok,_ in lines))
        def select(_,key):
            path=self.pick_file({'rom':'Elegir ROM','disc':'Elegir disco CUE, BIN o ISO','bios':'Elegir BIOS','wiiu':'Elegir imagen de Wii U'}[key])
            if not path:return
            try:ports.set_input(item['repository'],key,path,self.store);error.set_text('');refresh()
            except (ValueError,OSError) as exc:error.set_text(str(exc))
        if record.get('original_data'):
            def original_data(_,folder=False):
                xbox='Xbox 360' if record['original_data'].get('kind') in ('xbox360-dante','xbox360') else 'Xbox'
                path=self.pick_file(('Elegir carpeta con exefs y romfs' if record['original_data'].get('kind')=='switch-dump' else 'Elegir carpeta extraída de '+xbox) if folder else 'Elegir ISO de '+xbox,folder=folder,patterns=() if folder else ('*.iso',),filter_name='ISO (*.iso)')
                if not path:return
                try:ports.set_input(item['repository'],'original_data',path,self.store);error.set_text('');refresh()
                except (ValueError,OSError) as exc:error.set_text(str(exc))
            if not record['original_data'].get('iso_only'):body.pack_start(button('Elegir carpeta extraída',lambda w:original_data(w,True)),False,False,0)
            if record['original_data'].get('iso'):body.pack_start(button('Elegir ISO de Xbox 360' if record['original_data'].get('kind') in ('xbox360-dante','xbox360') else 'Elegir ISO de Xbox',original_data),False,False,0)
        for key,caption in (('rom','Elegir ROM'),('disc','Elegir disco'),('bios','Elegir BIOS'),('wiiu','Elegir imagen de Wii U')):
            if record.get(key):body.pack_start(button(caption,lambda w,k=key:select(w,k)),False,False,0)
        body.pack_start(button('Volver a detectar',lambda _:refresh()),False,False,0)
        refresh();page.show_all();accepted=page.run()==Gtk.ResponseType.OK;page.destroy();return accepted

    def configure_port(self,item,automatic=False):
        """Configure an installed port with the library's disc and the BIOS found by hash, then add it to the library."""
        from . import buildenv
        record=ports.records(self.store).get(item['repository'])
        if not record or not record.get('setup'):return
        if getattr(self,'port_busy',False):self.set_status('Ya hay una tarea en curso.');return
        games=[(e.name,e.source) for e in self.entries if e.source]
        lines=ports.requirements(record,games)
        missing=[text for ok,text in lines if ok is not True]
        if missing:
            self.transfer_event(item['repository'],{'phase':'awaiting_input','text':'Archivos originales pendientes.','fraction':None,'eta':None})
            if self.port_inputs(item):return self.configure_port(item,automatic=True)
            self.set_status(item['name']+': archivos originales pendientes.');self.port_setup_finished(item);return
        needs_sdk=record['setup'] in ('kit','openpete') and not buildenv.installed()
        used=next((text for ok,text in lines if ok and text.startswith('Disco')),'')
        question='Se va a configurar '+item['name']+' con lo que ya está en la Deck.\n\n'+'\n'.join(text for ok,text in lines)+'\n\n'+('Compila el juego dentro del SDK de KDE; el kit de Spider-Man tarda unos minutos. ' if record['setup'] in ('kit','openpete') else '')+('Antes se instalará el SDK de KDE de Flatpak (una sola vez). ' if needs_sdk else '')+'Los discos originales no se modifican.'
        if not automatic and not self.confirm('Configurar '+item['name'],question,'Configurar'):return
        self.port_busy=True;self.set_status('Configurando '+item['name']+'…')
        cancel=threading.Event() if record['setup'] in ('b2recomp','dante','original_data') else None
        if cancel is not None:
            if not hasattr(self,'port_jobs'):self.port_jobs={}
            self.port_jobs[item['repository']]=cancel
        self.start_transfer(item['repository']);progress=self.port_progress(item['repository'])
        def work():
            try:
                if needs_sdk:buildenv.install(lambda text:GLib.idle_add(self.set_status,'SDK de KDE: '+text))
                done=ports.configure(item['repository'],self.store,games,progress,**({'cancel':cancel} if cancel is not None else {}))
                GLib.idle_add(self.port_configured,item,done)
            except Exception as error:GLib.idle_add(self.port_failed,item,str(error))
        threading.Thread(target=work,daemon=True).start()

    def port_configured(self,item,record):
        getattr(self,'port_jobs',{}).pop(item['repository'],None)
        self.transfer_event(item['repository'],{'phase':'done','fraction':1,'text':'Juego preparado','eta':None})
        self.port_busy=False;self.set_status(item['name']+' configurado con «'+record.get('configured_with','')+'».');self.discover()
        notes={'ctr':'La primera vez, CTR pregunta por una fuente opcional (elegir «Use Luckiest Guy») y por un preset de gráficos.','openpete':'El juego ya está compilado. Se abre en pantalla completa.','kit':'El juego ya está compilado y listo para jugar.'}
        if notes.get(record.get('setup')):self.message(item['name']+' listo',notes[record['setup']]+' Se puede agregar a Steam desde la biblioteca.')
        if self.pages.get_visible_child_name()=='catalog':self.fill_catalog()
        from .iso_import import details
        if record.get('configured') and details(ports.ports_root()/record['folder']):
            self.iso_cleanup_active=item['repository'];GLib.idle_add(lambda:(self.iso_cleanup_page(item),False)[1])
        else:self.port_setup_finished(item)
        return False

    def port_setup_finished(self,item):
        """Complete setup in the library, with no leftover workflow blocking navigation."""
        self.iso_cleanup_active=None
        for workflow in list(self.inline_workflows)[::-1]:
            if getattr(workflow,'port_repository',None)==item['repository']:
                workflow.response(Gtk.ResponseType.CLOSE);workflow.destroy()
        record=ports.records(self.store).get(item['repository'])
        if record:
            self.store.merge(ports.entries_for(ports.ports_root()/record['folder']),overwrite=False)
            self.entries=self.store.load();self.library_dirty=True;self.refresh_platforms()
        self.open_library()
        GLib.idle_add(lambda:(self.focus_library(ports.port_id(item['repository'])),False)[1])
        GLib.idle_add(self.run_next_auto_port)

    def iso_cleanup_button(self,body,item,record):
        from .iso_import import details
        from .gui import button
        if record.get('configured') and details(ports.ports_root()/record['folder']):body.pack_start(button('Liberar espacio de la ISO',lambda _:self.iso_cleanup_page(item)),False,False,0)

    def iso_cleanup_page(self,item):
        from .iso_import import details,remove_source
        from .gui import label,button
        record=ports.records(self.store).get(item['repository']);folder=ports.ports_root()/record['folder'] if record else None
        info=details(folder) if folder else None
        if not info:self.port_setup_finished(item);return
        self.iso_cleanup_active=item['repository']
        page=InlineDialog(title='Liberar espacio',transient_for=self);page.port_repository=item['repository'];keep=page.add_button('Conservar ISO',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.pack_start(label('¿Eliminar la ISO original?','title'),False,False,0)
        body.pack_start(label('La extracción terminó. Los archivos del port se conservarán. La ISO se puede conservar para otros usos o eliminar para liberar espacio.','subtitle'),False,False,0)
        path=label(info['source'],'muted');path.set_selectable(True);body.pack_start(path,False,False,0)
        body.pack_start(label(f'ISO original · {info["size"]/1e9:.2f} GB','meta'),False,False,0)
        status=label('Antes de borrar se volverán a verificar los archivos extraídos.','muted');body.pack_start(status,False,False,0)
        cancel=threading.Event();alive=[True];removing=[False]
        def close(*_):
            if removing[0]:return
            alive[0]=False;cancel.set();page.destroy();self.port_setup_finished(item)
        page.connect('response',close)
        def done(error):
            getattr(self,'port_jobs',{}).pop(item['repository'],None);self.port_busy=False;removing[0]=False
            if self.ui_closed:return False
            text=('No se pudo eliminar la ISO: '+error) if error else 'ISO eliminada. Los datos del port, las partidas y los ajustes se conservaron.'
            self.transfer_event(item['repository'],{'phase':'error' if error else 'done','fraction':0 if error else 1,'text':text,'eta':None});self.set_status(text)
            if alive[0]:status.set_text(text);remove.set_sensitive(bool(error));keep.set_sensitive(True);page.set_deletable(True)
            if not error:
                self.toast(text)
                if alive[0]:close()
            return False
        def remove_iso(_):
            if getattr(self,'port_busy',False):status.set_text('Ya hay una instalación en curso.');return
            if not self.confirm('Eliminar ISO original',info['source']+'\n\nSe eliminará de forma permanente. El port conservará los archivos extraídos; otros programas ya no podrán usar esta ISO.','Eliminar ISO',danger=True):return
            remove.set_sensitive(False);keep.set_sensitive(False);page.set_deletable(False);self.port_busy=True;removing[0]=True;cancel.clear()
            if not hasattr(self,'port_jobs'):self.port_jobs={}
            self.port_jobs[item['repository']]=cancel;self.start_transfer(item['repository']);progress=self.port_progress(item['repository'])
            def work():
                try:remove_source(folder,ports.records(self.store)[item['repository']],progress,cancel);error=''
                except Exception as failure:error=str(failure)
                GLib.idle_add(done,error)
            threading.Thread(target=work,daemon=True).start()
        remove=button('Eliminar ISO',remove_iso,tone='danger');body.pack_start(remove,False,False,0)
        page.connect('destroy',lambda *_:(alive.__setitem__(0,False),cancel.set()))
        self.transfer_row(body,item['repository']).hide();page._mount()

    def port_failed(self,item,text):
        getattr(self,'port_jobs',{}).pop(item['repository'],None)
        if 'cancelad' in text.lower():self.transfer_event(item['repository'],{'phase':'cancelled','fraction':0,'text':text,'eta':None})
        else:self.finish_transfer(item['repository'],text)
        self.port_busy=False;self.set_status(text if 'cancelad' in text.lower() else 'No se pudo instalar '+item['name']+': '+text);GLib.idle_add(self.run_next_auto_port);return False
