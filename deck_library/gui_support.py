"""Support forms, administrator replies and persistent response notifications."""
import threading
from gi.repository import Gtk,GLib
from .inline_pages import InlineDialog
from .ui_components import ActionButton,badge,text

PLATFORMS=('Switch','PlayStation','Xbox','Wii / Wii U','PC (Windows)','Otra')
CATEGORIES={'report':'Reporte de problema','port':'Port','emulated':'Juego emulado','native':'Juego nativo','minecraft':'Instancia de Minecraft'}
STATES={'new':('Recibida','neutral'),'investigating':('En estudio','blue'),'fixed':('Resuelta','green'),'declined':('No se pudo','orange')}

def contents(view):
    b=view.get_buffer();return b.get_text(b.get_start_iter(),b.get_end_iter(),True).strip()

class SupportMixin:
    def community_client(self):
        from .community import Client
        return Client(self.store,self.preferences.get('community_url','https://presets.jokerlan.xyz'))

    def support_page(self,entry=None):
        if entry is not None and not hasattr(entry,'metadata'):entry=None
        page=InlineDialog(title='Solicitudes y reportes',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(10);actions=page.get_action_area()
        def choose(action):page.destroy();action()
        actions.pack_start(ActionButton('Nueva solicitud','plus',lambda _:choose(lambda:self.request_game_page(entry=entry)),'violet'),False,False,0)
        actions.pack_start(ActionButton('Reportar un problema','file',lambda _:choose(lambda:self.bug_report_page(entry)),'amber'),False,False,0)
        actions.pack_start(ActionButton('Actualizar','refresh',lambda _:self.refresh_my_requests(listing),'cyan'),False,False,0)
        if not self.signed_in():
            body.pack_start(text('Iniciar sesión para gestionar las solicitudes y los reportes enviados.','muted',85),False,False,0)
            def sign_in(_):
                self.open_request_account()
                if self.signed_in():page.destroy();self.support_page(entry)
            actions.pack_start(ActionButton('Iniciar sesión','community',sign_in,'steam'),False,False,0)
        body.pack_start(text('Mis solicitudes y reportes','section-title'),False,False,0)
        listing=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);body.pack_start(listing,False,False,0)
        page.connect('response',lambda *_:page.destroy());page._mount();self.refresh_my_requests(listing);return page

    def open_request_account(self):
        from .gui_account import account_dialog
        account_dialog(self)

    def request_game_page(self,*_,entry=None):
        page=InlineDialog(title='Hacer una solicitud',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(8)
        category=Gtk.ComboBoxText();category.get_accessible().set_name('Tipo de solicitud')
        for key,name in CATEGORIES.items():
            if key!='report':category.append(key,name)
        initial=('port' if entry.kind=='port' else 'minecraft' if entry.platform=='Minecraft' else 'emulated' if entry.kind=='emulated' else 'native') if entry else 'port'
        category.set_active_id(initial);body.pack_start(text('Tipo de solicitud','title'),False,False,0);body.pack_start(category,False,False,0)
        title=Gtk.Entry();title.set_max_length(120);title.set_placeholder_text('Nombre del juego o de la instancia');body.pack_start(text('Nombre del juego o de la instancia','title'),False,False,0);body.pack_start(title,False,False,0)
        if entry:title.set_text(entry.name)
        platform=Gtk.ComboBoxText();platform.get_accessible().set_name('Plataforma del juego')
        for name in PLATFORMS:platform.append(name,name)
        platform.set_active_id(entry.platform if entry and entry.platform in PLATFORMS else 'Otra');body.pack_start(text('Plataforma','title'),False,False,0);body.pack_start(platform,False,False,0)
        repo_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);repo_box.pack_start(text('Repositorio del port en GitHub','title'),False,False,0)
        repository=Gtk.Entry();repository.set_placeholder_text('https://github.com/autor/proyecto');repo_box.pack_start(repository,False,False,0);body.pack_start(repo_box,False,False,0)
        if entry and entry.metadata.get('port_repository'):repository.set_text('https://github.com/'+entry.metadata['port_repository'])
        def changed(*_):
            visible=category.get_active_id()=='port';repo_box.set_no_show_all(not visible);repo_box.set_visible(visible);self.refresh_layout()
        category.connect('changed',changed)
        body.pack_start(text('Explicar el problema o lo que se necesita','title'),False,False,0)
        details=Gtk.TextView();details.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);scroll=self.new_scroll();scroll.set_size_request(-1,100);scroll.add(details);body.pack_start(scroll,False,False,0)
        body.pack_start(text('No adjuntar archivos ni enlaces de descarga de juegos.','meta',85),False,False,0)
        if not self.signed_in():
            body.pack_start(text('Iniciar sesión permite recibir avisos y leer las respuestas en la app. Una solicitud sin cuenta no tiene seguimiento.','muted',85),False,False,0)
            body.pack_start(ActionButton('Iniciar sesión','community',lambda _:self.open_request_account(),'cyan'),False,False,0)
        status=text('','status',85);state={'alive':True,'busy':False}
        def send(_):
            if state['busy']:return
            value={'title':title.get_text().strip(),'category':category.get_active_id(),'platform':platform.get_active_id() or 'Otra','repository':repository.get_text().strip() if category.get_active_id()=='port' else '', 'details':contents(details)}
            try:
                from community.requests import fields
                fields(value)
                if not value['details']:raise ValueError('Explicar el problema o lo que se necesita.')
            except ValueError as error:status.set_text(str(error));return
            state['busy']=True;send_button.set_sensitive(False);status.set_text('Enviando…')
            def done(result,error):
                state['busy']=False
                if not state['alive']:return False
                send_button.set_sensitive(True)
                if error:status.set_text(str(error))
                else:
                    self.toast('Solicitud enviada');status.set_text(f"Solicitud recibida. Número: {result['id']}");send_button.set_sensitive(False)
                    page.get_action_area().pack_start(ActionButton('Ver mis solicitudes','community',lambda _:(page.destroy(),self.my_requests_page()),'cyan'),False,False,0);body.show_all();changed()
                return False
            def work():
                try:GLib.idle_add(done,self.community_client().request('/v1/requests',value),None)
                except Exception as error:GLib.idle_add(done,None,error)
            threading.Thread(target=work,daemon=True).start()
        send_button=ActionButton('Enviar solicitud','upload',send,'violet');page.get_action_area().pack_start(send_button,False,False,0);body.pack_start(status,False,False,0)
        page.connect('destroy',lambda *_:state.update(alive=False));page.connect('response',lambda *_:page.destroy());changed();page._mount();return page

    def build_request_notification(self,root):
        self.request_notice=Gtk.Box(spacing=10);self.request_notice.get_style_context().add_class('request-notice');self.request_notice.set_no_show_all(True)
        self.request_notice_label=text('','title',65);self.request_notice.pack_start(self.request_notice_label,True,True,0)
        self.request_notice.pack_end(ActionButton('Ver respuestas','community',lambda _:self.my_requests_page(),'violet'),False,False,0);root.pack_start(self.request_notice,False,False,0)

    def poll_request_replies(self):
        if self.ui_closed:return False
        if not self.signed_in():
            if hasattr(self,'request_notice'):self.request_notice.hide()
            return True
        if getattr(self,'request_poll_busy',False):return True
        self.request_poll_busy=True;client=self.community_client();session=client.session().get('token')
        def done(value):
            self.request_poll_busy=False
            if self.ui_closed or self.community_client().session().get('token')!=session:return False
            count=value.get('unread',0)
            if hasattr(self,'request_notice'):
                if count:
                    self.request_notice_label.set_text('Nueva respuesta recibida' if count==1 else f'Nuevas respuestas en {count} solicitudes');self.request_notice.set_no_show_all(False);self.request_notice.show_all();self.request_notice.set_no_show_all(True)
                    if getattr(self,'request_unread_count',0)<count:self.toast('Nueva respuesta · Ver respuestas')
                else:self.request_notice.hide()
            self.request_unread_count=count;return False
        def work():
            try:result=client.request('/v1/me/requests')
            except Exception:
                GLib.idle_add(lambda:setattr(self,'request_poll_busy',False));return
            GLib.idle_add(done,result)
        threading.Thread(target=work,daemon=True).start();return True

    def my_requests_page(self,*_):
        return self.support_page()

    def refresh_my_requests(self,box):
        if not self.signed_in():return
        client=self.community_client();session=client.session().get('token')
        def paint(rows,error):
            if self.ui_closed or box.get_parent() is None or not box.get_mapped() or self.community_client().session().get('token')!=session:return False
            self.reset_page(box)
            if error:box.pack_start(text(str(error),'status',85),False,False,0)
            elif not rows:box.pack_start(text('Todavía no hay solicitudes de esta cuenta.','muted',85),False,False,0)
            for row in rows:
                card=self.card(box,row['title']);caption,tone=STATES.get(row['state'],STATES['new']);card.pack_start(badge(caption,tone,20),False,False,0)
                card.pack_start(text(CATEGORIES.get(row.get('category'),'Juego emulado')+' · '+row['platform']+' · '+row['id'],'meta',85),False,False,0)
                for reply in row.get('replies',[]):
                    caption,_=STATES.get(reply['state'],STATES['new']);card.pack_start(text('Deck Library · '+caption,'title',85),False,False,0)
                    if reply['note']:card.pack_start(text(reply['note'],'muted',85),False,False,0)
                if not row.get('replies'):card.pack_start(text(row.get('note') or 'La solicitud está pendiente de revisión.','muted',85),False,False,0)
            box.show_all();self.refresh_layout()
            def acknowledge():
                for row in rows:
                    if row.get('unread'):
                        try:client.request('/v1/me/requests/'+row['id']+'/read',{'updated':row['updated']})
                        except Exception:continue
                GLib.idle_add(lambda:(self.poll_request_replies(),False)[1])
            if rows:threading.Thread(target=acknowledge,daemon=True).start()
            return False
        def work():
            try:GLib.idle_add(paint,client.request('/v1/me/requests').get('requests',[]),None)
            except Exception as error:GLib.idle_add(paint,[],error)
        threading.Thread(target=work,daemon=True).start()

    def owner_requests_page(self,*_):
        page=InlineDialog(title='Bandeja de entrada',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(10);status=text('Cargando…','status',85);body.pack_start(status,False,False,0)
        page.get_action_area().pack_start(ActionButton('Actualizar','refresh',lambda _:load(),'cyan'),False,False,0)
        listing=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);body.pack_start(listing,False,False,0);state={'alive':True,'busy':False}
        def paint(rows,error):
            state['busy']=False
            if not state['alive']:return False
            if error:status.set_text(str(error));return False
            self.reset_page(listing);status.set_text(f'{len(rows)} solicitudes.' if rows else 'No hay solicitudes todavía.')
            for row in rows:
                card=self.card(listing,row['title']);caption,tone=STATES.get(row['state'],STATES['new']);card.pack_start(badge(caption,tone,20),False,False,0)
                card.pack_start(text(CATEGORIES.get(row.get('category'),'Juego emulado')+' · '+row['platform'],'meta',85),False,False,0)
                if row.get('repository'):card.pack_start(Gtk.LinkButton.new_with_label(row['repository'],'Repositorio del port'),False,False,0)
                card.pack_start(text('Número '+row['id']+(' · de '+row['login'] if row['login'] else ' · sin cuenta'),'meta',85),False,False,0)
                if row.get('note'):card.pack_start(text('Última respuesta: '+row['note'],'muted',85),False,False,0)
                response=Gtk.TextView();response.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);response.get_accessible().set_name('Respuesta a '+row['title']);scroll=self.new_scroll();scroll.set_size_request(-1,85);scroll.add(response)
                card.pack_start(text('Respuesta al usuario','title'),False,False,0);card.pack_start(scroll,False,False,0);actions=Gtk.Box(spacing=8);card.pack_start(actions,False,False,0)
                actions.pack_start(ActionButton('Enviar respuesta','upload',lambda _,r=row,v=response:change(r,r['state'],contents(v)),'violet'),False,False,0)
                if row.get('report_id'):actions.pack_start(ActionButton('Ver diagnóstico','file',lambda _,r=row:self.request_diagnostic_page(r),'steam'),False,False,0)
                for key,(caption,_) in STATES.items():
                    if key!=row['state']:actions.pack_start(ActionButton(caption,'check',lambda _,r=row,k=key,v=response:change(r,k,contents(v)),{'new':'cyan','investigating':'steam','fixed':'play','declined':'amber'}[key]),False,False,0)
                card.reorder_child(actions,2)
                if row['details']:card.pack_start(text(row['details'],'muted',85),False,False,0)
            listing.show_all();self.refresh_layout();return False
        def load():
            def work():
                try:GLib.idle_add(paint,self.community_client().request('/v1/admin/requests').get('requests',[]),None)
                except Exception as error:GLib.idle_add(paint,[],error)
            threading.Thread(target=work,daemon=True).start()
        def change(row,new_state,note):
            if state['busy']:return
            if new_state==row['state'] and not note:status.set_text('Escribir una respuesta o cambiar el estado.');return
            state['busy']=True;status.set_text('Enviando respuesta…')
            def work():
                try:self.community_client().request('/v1/admin/requests/'+row['id'],{'state':new_state,'note':note});GLib.idle_add(lambda:(self.toast('Respuesta enviada'),load(),False)[-1])
                except Exception as error:GLib.idle_add(paint,[],error)
            threading.Thread(target=work,daemon=True).start()
        page.connect('destroy',lambda *_:state.update(alive=False));page.connect('response',lambda *_:page.destroy());page._mount();load();return page

    def request_diagnostic_page(self,row):
        import json
        page=InlineDialog(title='Diagnóstico · '+row['title'],transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        status=text('Cargando diagnóstico…','status',85);body=page.get_content_area();body.pack_start(status,False,False,0)
        view=Gtk.TextView();view.set_editable(False);view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);body.pack_start(view,True,True,0)
        def done(value,error):
            if page._closed:return False
            status.set_text(str(error) if error else 'Diagnóstico enviado con este reporte.')
            if value:view.get_buffer().set_text(json.dumps(value['report'],ensure_ascii=False,indent=2))
            return False
        def work():
            try:GLib.idle_add(done,self.community_client().request('/v1/admin/requests/'+row['id']+'/diagnostic'),None)
            except Exception as error:GLib.idle_add(done,None,error)
        page.connect('response',lambda *_:page.destroy());page._mount();threading.Thread(target=work,daemon=True).start();return page
