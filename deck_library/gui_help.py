"""First-use guide, curated Deck reports and opt-in bug diagnostics inside the app."""
import json,pathlib,threading,subprocess
from gi.repository import Gtk,GLib,Gdk
from .inline_pages import InlineDialog
from .ui_components import ActionButton,text,badge,badge_row,Reveal
from . import bug_report,validated_games

GUIDE=[
 ('1. Encontrar juegos','Biblioteca muestra lo que hay en la Deck. Si falta algo, Actualizar biblioteca vuelve a buscar.'),
 ('2. Instalar un port','Ports → elegir un juego → Instalar. La tarjeta indica si hace falta una ROM o un disco.'),
 ('3. Preparar los originales','Algunos ports piden archivos propios. En Herramientas se convierte un XCI o NSP de Switch y se extrae una ISO de Xbox.'),
 ('4. Elegir un perfil','Abrir un juego → Perfiles. Elegir uno no cambia nada hasta Aplicar; Deshacer vuelve atrás. Aplicar y jugar hace las dos cosas.'),
 ('5. Jugar desde Steam','Agregar a Steam crea el acceso con su carátula. Aparece cuando Steam se cierra y se vuelve a abrir.'),
 ('6. Ver qué está probado','Verificados muestra los juegos comprobados en una Steam Deck y el arreglo de cada uno. No es una certificación de Valve.'),
 ('7. Consultas y soporte','Ayuda → Reportar un problema o hacer una solicitud. Con una cuenta se reciben avisos de respuesta dentro de la app.'),
 ('8. Usar el mando','A selecciona, B vuelve, LB y RB cambian de pestaña, X abre el teclado, Y abre las opciones del juego, Menú abre los filtros y la palanca derecha desplaza.'),
]

class HelpMixin:
    def help_page(self,*_):
        """Help is a page of the window, not a window: an arrow at the top left leads back to where the person was."""
        from .ui_components import Icon
        if not self.discard_game_edits():return
        current=self.pages.get_visible_child_name()
        if current!='help':self.help_return=current
        box=self.help_box;self.reset_page(box);box.set_spacing(12)
        head=Gtk.Box(spacing=10);back=Gtk.Button();back.add(Icon('back',20));back.get_style_context().add_class('quiet');back.set_tooltip_text('Volver');back.get_accessible().set_name('Volver');back.connect('clicked',lambda _:self.leave_help());back.set_valign(Gtk.Align.CENTER)
        head.pack_start(back,False,False,0);head.pack_start(text('Ayuda','hero'),True,True,0);box.pack_start(head,False,False,0)
        box.pack_start(text('La biblioteca y los ajustes locales se pueden usar sin cuenta.','muted',90),False,False,0)
        for title,description in GUIDE:
            panel=self.card(box,title);panel.pack_start(text(description,'muted',95),False,False,0)
        actions=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);box.pack_start(actions,False,False,0)
        actions.pack_start(ActionButton('Reportar un problema o hacer una solicitud','file',lambda _:self.support_page(),'violet'),False,False,0)
        if (self.store.root/'last-launch-error.json').is_file():actions.pack_start(ActionButton('Último error de un juego','file',lambda _:self.launch_error_page(),'quiet'),False,False,0)
        self.pin_page_header(box,head,actions)
        box.show_all();self.pages.set_visible_child_name('help');self.refresh_layout()
        GLib.idle_add(lambda:(box.get_ancestor(Gtk.ScrolledWindow).get_vadjustment().set_value(0),False)[1])

    def resolve_verified_covers(self,items):
        """Covers for the verified list: the installed game's own art first, then the catalog's (cached or searched off the GTK thread). Without one the poster keeps its name."""
        from . import ports
        from .artwork import find_cover
        catalog=self.catalog_entries();offline=self.preferences.get('artwork_provider')=='off'
        lists={'eden':'Nintendo Switch','wiicompiled':'Wii'}
        local=[(game,find_cover(installed) if installed else '',cover) for game,installed,cover in items]
        for game,path,cover in local:
            if path:cover.set_path(path)
        def work():
            for game,path,cover in local:
                if path or offline:continue
                item=next((v for v in catalog if game['repository'] and v['repository'].casefold()==game['repository'].casefold()),None) or {'name':game['name'],'game_title':game['name'],'list':lists.get(game['adapter'],''),'repository':'verified/'+game['id']}
                try:found=ports.icon_path(self.store,item)
                except Exception:found=''
                if found and not self.ui_closed:GLib.idle_add(cover.set_path,found)
        threading.Thread(target=work,daemon=True).start()

    def leave_help(self,*_):
        """Back from Help to the page it was opened from."""
        target={'home':self.home_page,'validated':self.validated_page,'catalog':self.catalog_page,'updates':self.updates_page,'tools':self.tools_page,'settings':self.settings_page}.get(getattr(self,'help_return','library'),self.open_library)
        target()

    def validated_page(self,*_):
        if not self.discard_game_edits():return
        body=self.validated_box;self.reset_page(body);body.set_spacing(12)
        body.pack_start(text('Verificados por Deck Library','hero'),False,False,0)
        body.pack_start(text('Juegos comprobados en una Steam Deck y el arreglo que necesitó cada uno. Revisar la versión y las limitaciones antes de instalar.','muted',90),False,False,0)
        body.pack_start(ActionButton('Reportar un problema o hacer una solicitud','plus',lambda _:self.support_page(),'violet'),False,False,0)
        search=Gtk.SearchEntry();search.set_placeholder_text('Buscar juegos validados · X: teclado');self.bind_search_keyboard(search);self.validated_search=search;body.pack_start(search,False,False,0)
        results=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);body.pack_start(results,False,False,0);self.validated_targets={};panels=[]
        from .gui import Poster
        from .models import Entry
        shown_as={'eden':'Switch','wiicompiled':'Wii','narutorise':'Windows'};covers=[]
        for game in validated_games.catalog():
            card=self.card(results,None);panels.append((game,card));installed=validated_games.matching(game,self.entries)
            row=Gtk.Box(spacing=16);card.pack_start(row,False,False,0)
            cover=Poster(Entry(game['name'],['x'],platform=shown_as.get(game['adapter'],'PC')),'',112,168);cover.set_valign(Gtk.Align.START);row.pack_start(cover,False,False,0);covers.append((game,installed,cover))
            panel=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);row.pack_start(panel,True,True,0);panel.pack_start(text(game['name'],'title'),False,False,0)
            how={'automatic':('Lo aplica Deck Library','green'),'profile':('Perfil incluido','blue'),'manual':('Guía manual','yellow')}[game['fix_how']]
            panel.pack_start(badge_row([('Gameplay confirmado','green'),how]),False,False,0)
            panel.pack_start(text(game['program']+' · '+game['version'],'meta',85),False,False,0)
            panel.pack_start(text('Steam Deck OLED' if game['hardware']=='steam-deck-oled' else 'Steam Deck LCD','meta'),False,False,0)
            panel.pack_start(text(game['result'],'muted',95),False,False,0)
            panel.pack_start(text('Arreglo','title'),False,False,0);panel.pack_start(text(game['fix'],'muted',95),False,False,0)
            details=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);details.pack_start(text('Limitaciones','title'),False,False,0);details.pack_start(text(game['limitations'],'muted',95),False,False,0);details.pack_start(text('Evidencia','title'),False,False,0);details.pack_start(text(game['fix_evidence'],'muted',95),False,False,0);details.pack_start(text('Fecha del registro: '+game['date'],'meta'),False,False,0)
            panel.pack_start(Reveal('Ver condiciones de la prueba',details),False,False,0)
            def open_game(_,entry=installed):
                self.select_game(entry)
            if installed:
                control=ActionButton('Abrir juego en mi biblioteca','library',open_game,'steam-outline');panel.pack_start(control,False,False,0);panel.reorder_child(control,1);self.validated_targets[installed.id]=control
            elif game['repository']:
                from . import ports
                item=next((v for v in self.catalog_entries() if v['repository'].casefold()==game['repository'].casefold()),None)
                if item:
                    action=ActionButton('Ver port y requisitos','controller',lambda _,item=item:self.port_details(item),'steam-outline');panel.pack_start(action,False,False,0);panel.reorder_child(action,1)
            if game['profile_id']:
                from . import presets
                profile=next((p for p in presets.catalog(self.store) if p['id']==game['profile_id']),None)
                if profile:details.pack_start(text(profile['objective'],'meta',95),False,False,0)
        empty=text('No hay juegos validados con ese nombre.','muted');results.pack_start(empty,False,False,0);empty.set_no_show_all(True)
        self.resolve_verified_covers(covers)
        def filter_games(_):
            query=search.get_text().strip().casefold();count=0
            for game,panel in panels:
                shown=query in (game['name']+' '+game['program']+' '+game['fix']).casefold();panel.set_visible(shown);count+=shown
            empty.set_visible(not count)
        search.connect('search-changed',filter_games);body.show_all();filter_games(None)
        self.pin_page_header(body,*body.get_children()[:3])
        body.get_ancestor(Gtk.ScrolledWindow).show();self.pages.set_visible_child_name('validated');self.refresh_layout()
        attempts=[0]
        def focus():
            if self.ui_closed or self.pages.get_visible_child_name()!='validated' or self.validated_search is not search:return False
            attempts[0]+=1
            target=self.validated_targets.get(getattr(self,'library_focus_id',None),search)
            if not target.get_mapped():return attempts[0]<5
            target.grab_focus();self.mark_controller_focus(self,target);self.reveal_focus(target)
            return self.get_focus() is not target and attempts[0]<5
        # Stack mapping/layout can restore the old focus after an idle callback.
        GLib.timeout_add(30,focus)

    def bug_report_page(self,entry=None):
        if entry is not None and not hasattr(entry,'metadata'):entry=None
        page=InlineDialog(title='Reportar un problema',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(10)
        title=Gtk.Entry();title.set_placeholder_text('Qué falló, por ejemplo: no instala un port');body.pack_start(text('Título'),False,False,0);body.pack_start(title,False,False,0)
        body.pack_start(text('Pasos para reproducirlo, qué se esperaba y qué ocurrió','meta'),False,False,0)
        description=Gtk.TextView();description.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);scroll=self.new_scroll();scroll.set_size_request(-1,110);scroll.add(description);body.pack_start(scroll,False,False,0)
        include=Gtk.CheckButton(label='Incluir los últimos registros del programa y del juego');include.set_active(True);body.pack_start(include,False,False,0)
        body.pack_start(text('El reporte oculta rutas personales, correos y credenciales conocidas. Revisar el contenido antes de compartirlo. No se envían ROMs, partidas ni archivos de configuración.','muted',95),False,False,0)
        preview=Gtk.TextView();preview.set_editable(False);preview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);preview_scroll=self.new_scroll();preview_scroll.set_size_request(-1,170);preview_scroll.add(preview);preview_reveal=Reveal('Revisar los datos del reporte',preview_scroll);body.pack_start(preview_reveal,False,False,0)
        status=text('','status',95);body.pack_start(status,False,False,0);state={'report':None,'reference':'','alive':True}
        def report():
            value=bug_report.collect(self.store,entry,include.get_active())
            value['title']=title.get_text().strip();value['description']=description.get_buffer().get_text(description.get_buffer().get_start_iter(),description.get_buffer().get_end_iter(),True)
            value=bug_report.sanitize(value);bug_report.validate_report(value);state['report']=value;preview.get_buffer().set_text(json.dumps(value,ensure_ascii=False,indent=2));return value
        def review(_):
            try:
                report();send_button.set_sensitive(True);preview_reveal.revealer.set_reveal_child(True);status.set_text('Reporte preparado. Revisar los datos y elegir cómo compartirlos.')
            except Exception as error:status.set_text(str(error))
        def export(_):
            try:
                value=report();path=self.pick_file('Guardar reporte ZIP',save=True,suggested_name='deck-library-report.zip')
                if path:bug_report.export(value,path);status.set_text('Reporte guardado. Se puede adjuntar al crear el issue de GitHub.');self.toast('Reporte exportado')
            except Exception as error:status.set_text(str(error))
        def github(_):
            try:
                url=bug_report.issue_url(report(),state['reference']) if title.get_text().strip() and description.get_buffer().get_char_count() else bug_report.ISSUES
                subprocess.Popen(['xdg-open',url],start_new_session=True)
            except Exception as error:status.set_text(str(error))
        def send(_):
            value=state['report']
            if not value:status.set_text('Preparar y revisar el reporte antes de enviarlo.');return
            if not self.confirm('Enviar diagnóstico','Se enviará el reporte que figura en la vista previa al servicio de Deck Library. No se publica en GitHub. Si hay una sesión iniciada, se vincula a esa cuenta para consultar respuestas.','Enviar reporte'):return
            send_button.set_sensitive(False);status.set_text('Enviando reporte…')
            def done(result,error):
                if not state['alive']:return False
                send_button.set_sensitive(True)
                if error:status.set_text(error)
                else:send_button.set_sensitive(False);state['reference']=result['id'];status.set_text('Reporte recibido: '+result['id']);self.toast('Reporte recibido');page.get_action_area().pack_start(ActionButton('Ver mis reportes','community',lambda _:(page.destroy(),self.support_page()),'cyan'),False,False,0)
                return False
            def work():
                from .community import Client
                try:result=self.community_client().request('/v1/bug-reports',value);GLib.idle_add(done,result,None)
                except Exception as error:GLib.idle_add(done,None,str(error))
            threading.Thread(target=work,daemon=True).start()
        from .gui import wrap_row
        actions=page.get_action_area()
        for caption,icon,callback in [('Preparar reporte','search',review),('Guardar ZIP','download',export),('Reportar en GitHub','file',github)]:actions.pack_start(ActionButton(caption,icon,callback,'steam-outline'),False,False,0)
        send_button=ActionButton('Enviar diagnóstico','upload',send,'violet');send_button.set_sensitive(False);actions.pack_start(send_button,False,False,0)
        def changed(*_):state['report']=None;send_button.set_sensitive(False)
        title.connect('changed',changed);description.get_buffer().connect('changed',changed);include.connect('toggled',changed)
        page.connect('destroy',lambda *_:state.update(alive=False));page.connect('response',lambda *_:page.destroy());page._mount()
