"""First-use guide, curated Deck reports and opt-in bug diagnostics inside the app."""
import json,pathlib,threading,subprocess
from gi.repository import Gtk,GLib,Gdk
from .inline_pages import InlineDialog
from .ui_components import ActionButton,text,badge,Reveal
from . import bug_report,validated_games

GUIDE=[
 ('1. Encontrar o instalar juegos','Biblioteca muestra los juegos encontrados en la Deck. Catálogo de ports descarga el programa del port; después puede pedir la ROM, ISO o carpeta original para prepararlo.'),
 ('2. Preparar y jugar','Preparar indica que faltan archivos o una compilación. Jugar abre el juego listo. Si no encuentra los originales, elegir su ubicación desde la ficha del port.'),
 ('3. Elegir ajustes','Abrir una carátula y elegir un perfil. Ver detalles muestra sus cambios. Aplicar guarda un respaldo; Deshacer recupera los valores anteriores. Cerrar el juego antes de cambiarlos.'),
 ('4. Usar Steam','Agregar a Steam crea el acceso directo y copia su carátula. Si Steam está abierto, el cambio espera hasta que se cierre; se recupera al iniciar la siguiente sesión. No hace falta recrear el acceso directo al cambiar Proton.'),
 ('5. Compartir con la comunidad','No hace falta una cuenta para jugar o usar perfiles locales. Para publicar o comentar: Cuenta → Crear cuenta, verificar el correo e iniciar sesión. Dentro del juego, Comunidad → Compartir mis ajustes permite capturar la configuración, revisarla y publicarla.'),
 ('6. Entender las pruebas','Instalado significa que hay archivos en la Deck. Sin verificar es una propuesta. Verificado por usuario corresponde a una prueba concreta. Juegos validados muestra equipo, versión, resultado y limitaciones; no es una certificación de Valve.')
]

class HelpMixin:
    def help_page(self,*_):
        page=InlineDialog(title='Guía de Deck Library',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(12)
        body.pack_start(text('Primeros pasos','hero'),False,False,0)
        body.pack_start(text('La biblioteca y los ajustes locales se pueden usar sin cuenta.','muted',90),False,False,0)
        for title,description in GUIDE:
            panel=self.card(body,title);panel.pack_start(text(description,'muted',95),False,False,0)
        actions=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);body.pack_start(actions,False,False,0)
        actions.pack_start(ActionButton('Juegos validados','check',lambda _:self.validated_page(),'steam'),False,False,0)
        actions.pack_start(ActionButton('Reportar un problema','file',lambda _:self.bug_report_page(),'violet-outline'),False,False,0)
        page.connect('response',lambda *_:page.destroy());page._mount()

    def validated_page(self,*_):
        page=InlineDialog(title='Juegos validados en Steam Deck',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(12)
        body.pack_start(text('Esta lista reúne pruebas de juego reportadas en una Steam Deck. Conviene revisar la versión, el equipo y las limitaciones: instalar un port o tener una puntuación alta de compatibilidad no equivale a haberlo probado.','muted',95),False,False,0)
        for game in validated_games.catalog():
            panel=self.card(body,game['name']);panel.pack_start(badge('Gameplay confirmado','green'),False,False,0)
            panel.pack_start(text(game['program']+' · '+game['version'],'meta',85),False,False,0)
            panel.pack_start(text('Steam Deck OLED' if game['hardware']=='steam-deck-oled' else 'Steam Deck LCD','meta'),False,False,0)
            panel.pack_start(text(game['result'],'muted',95),False,False,0)
            details=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);details.pack_start(text(game['limitations'],'muted',95),False,False,0);details.pack_start(text('Fecha del registro: '+game['date'],'meta'),False,False,0)
            panel.pack_start(Reveal('Ver condiciones de la prueba',details),False,False,0)
            installed=validated_games.matching(game,self.entries)
            def open_game(_,entry=installed):
                page.response(Gtk.ResponseType.CLOSE);GLib.idle_add(lambda:(self.select_game(entry),False)[1])
            if installed:panel.pack_start(ActionButton('Abrir juego en mi biblioteca','library',open_game,'steam-outline'),False,False,0)
            elif game['repository']:
                from . import ports
                item=next((v for v in self.catalog_entries() if v['repository'].casefold()==game['repository'].casefold()),None)
                if item:panel.pack_start(ActionButton('Ver port y requisitos','controller',lambda _,item=item:self.port_details(item),'steam-outline'),False,False,0)
            if game['profile_id']:
                from . import presets
                profile=next((p for p in presets.catalog(self.store) if p['id']==game['profile_id']),None)
                if profile:details.pack_start(text(profile['objective'],'meta',95),False,False,0)
        page.connect('response',lambda *_:page.destroy());page._mount()

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
            if not self.confirm('Enviar diagnóstico','Se enviará el reporte que figura en la vista previa al servicio de Deck Library. No se publica en GitHub ni incluye una cuenta personal.','Enviar reporte'):return
            send_button.set_sensitive(False);status.set_text('Enviando reporte…')
            def done(result,error):
                if not state['alive']:return False
                send_button.set_sensitive(True)
                if error:status.set_text(error)
                else:state['reference']=result['id'];status.set_text('Reporte recibido: '+result['id']);self.toast('Reporte recibido')
                return False
            def work():
                from .community import Client
                try:result=Client(self.store,self.preferences.get('community_url','https://presets.jokerlan.xyz')).request('/v1/bug-reports',value,token='');GLib.idle_add(done,result,None)
                except Exception as error:GLib.idle_add(done,None,str(error))
            threading.Thread(target=work,daemon=True).start()
        from .gui import wrap_row
        actions=wrap_row();body.pack_start(actions,False,False,0)
        for caption,icon,callback in [('Preparar reporte','search',review),('Guardar ZIP','download',export),('Reportar en GitHub','file',github)]:actions.pack_start(ActionButton(caption,icon,callback,'steam-outline'),False,False,0)
        send_button=ActionButton('Enviar diagnóstico','upload',send,'violet');send_button.set_sensitive(False);actions.pack_start(send_button,False,False,0)
        def changed(*_):state['report']=None;send_button.set_sensitive(False)
        title.connect('changed',changed);description.get_buffer().connect('changed',changed);include.connect('toggled',changed)
        page.connect('destroy',lambda *_:state.update(alive=False));page.connect('response',lambda *_:page.destroy());page._mount()
