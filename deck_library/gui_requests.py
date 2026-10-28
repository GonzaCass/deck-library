"""Game requests: anyone can ask for a game to be made to work; only the owner's account sees what arrives."""
import threading
from gi.repository import Gtk,GLib
from .inline_pages import InlineDialog
from .ui_components import ActionButton,badge,text

PLATFORMS=('Switch','PlayStation','Xbox','Wii / Wii U','PC (Windows)','Otra')
STATES={'new':('Recibida','neutral'),'investigating':('En estudio','blue'),'fixed':('Resuelta','green'),'declined':('No se pudo','orange')}

class RequestsMixin:
    def community_client(self):
        from .community import Client
        return Client(self.store,self.preferences.get('community_url','https://presets.jokerlan.xyz'))

    def request_game_page(self,*_):
        page=InlineDialog(title='Pedir un juego',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(10)
        body.pack_start(text('No hace falta enviar el juego ni sus archivos, y no se aceptan. La solicitud se revisa y se intenta hacer que el juego funcione en la Steam Deck. Si se logra, el arreglo se publica en Deck Library, sin incluir el juego.','muted',95),False,False,0)
        body.pack_start(text('Nombre del juego','title'),False,False,0)
        title=Gtk.Entry();title.set_max_length(120);title.set_placeholder_text('Por ejemplo: Nombre del juego');body.pack_start(title,False,False,0)
        body.pack_start(text('Plataforma','title'),False,False,0)
        platform=Gtk.ComboBoxText();platform.get_accessible().set_name('Plataforma del juego')
        for name in PLATFORMS:platform.append(name,name)
        platform.set_active(0);body.pack_start(platform,False,False,0)
        body.pack_start(text('Qué falla o qué se necesita (opcional)','title'),False,False,0)
        details=Gtk.TextView();details.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);scroll=self.new_scroll();scroll.set_size_request(-1,110);scroll.add(details);body.pack_start(scroll,False,False,0)
        body.pack_start(text('Sin enlaces ni archivos. Con una cuenta se puede ver después cómo va la solicitud.','meta',95),False,False,0)
        status=text('','status',95);status.set_selectable(True);state={'alive':True,'busy':False}
        def send(_):
            if state['busy']:return
            buffer=details.get_buffer();value={'title':title.get_text().strip(),'platform':platform.get_active_id() or 'Otra','details':buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True).strip()}
            if len(value['title'])<2:status.set_text('Indicar el nombre del juego.');return
            state['busy']=True;send_button.set_sensitive(False);status.set_text('Enviando…')
            def done(result,error):
                state['busy']=False
                if not state['alive']:return False
                send_button.set_sensitive(True)
                if error:status.set_text(str(error))
                else:
                    status.set_text(f"Solicitud recibida. Número: {result['id']}");title.set_text('');details.get_buffer().set_text('');self.toast('Solicitud enviada')
                    self.refresh_my_requests(mine)
                return False
            def work():
                try:result=self.community_client().request('/v1/requests',value);GLib.idle_add(done,result,None)
                except Exception as error:GLib.idle_add(done,None,error)
            threading.Thread(target=work,daemon=True).start()
        send_button=ActionButton('Enviar solicitud','upload',send,'play');body.pack_start(send_button,False,False,0);body.pack_start(status,False,False,0)
        mine=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);body.pack_start(mine,False,False,0)
        page.connect('destroy',lambda *_:state.update(alive=False));page.connect('response',lambda *_:page.destroy());page._mount()
        self.refresh_my_requests(mine)
        return page

    def refresh_my_requests(self,box):
        """The signed-in person's own requests and what became of them. Nothing is shown without a session."""
        if not self.signed_in():return
        def paint(rows):
            if self.ui_closed or box.get_parent() is None:return False
            self.reset_page(box)
            if rows:
                box.pack_start(text('Mis solicitudes','title'),False,False,0)
                for row in rows:
                    label,tone=STATES.get(row['state'],STATES['new']);line=Gtk.Box(spacing=8);line.pack_start(badge(label,tone,14),False,False,0);line.pack_start(text(f"{row['title']} · {row['platform']}"),True,True,0);box.pack_start(line,False,False,0)
                    if row.get('note'):box.pack_start(text(row['note'],'meta',90),False,False,0)
            box.show_all();return False
        def work():
            try:rows=self.community_client().request('/v1/me/requests').get('requests',[])
            except Exception:return
            GLib.idle_add(paint,rows)
        threading.Thread(target=work,daemon=True).start()

    def check_owner_mode(self):
        """Ask the service once whether this account is an administrator; only then does the received-requests page appear in Settings."""
        if not self.signed_in():
            if self.preferences.get('owner_mode'):self.preferences['owner_mode']=False
            return
        def work():
            try:admin=bool(self.community_client().me().get('admin'))
            except Exception:return
            def apply():
                if self.preferences.get('owner_mode')!=admin:
                    from .installations import save_settings
                    self.preferences['owner_mode']=admin;save_settings(self.preferences,self.store)
                return False
            GLib.idle_add(apply)
        threading.Thread(target=work,daemon=True).start()

    def owner_requests_page(self,*_):
        page=InlineDialog(title='Solicitudes recibidas',transient_for=self);page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();body.set_spacing(10)
        status=text('Cargando…','status',95);body.pack_start(status,False,False,0);listing=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);body.pack_start(listing,False,False,0);state={'alive':True}
        def paint(rows,error):
            if not state['alive']:return False
            self.reset_page(listing)
            status.set_text(str(error) if error else f'{len(rows)} solicitudes.' if rows else 'No hay solicitudes todavía.')
            for row in rows:
                card=self.card(listing,f"{row['title']} · {row['platform']}");label,tone=STATES.get(row['state'],STATES['new']);card.pack_start(badge(label,tone,14),False,False,0)
                if row['details']:card.pack_start(text(row['details'],'muted',95),False,False,0)
                card.pack_start(text('Número '+row['id']+(' · de '+row['login'] if row['login'] else ' · sin cuenta'),'meta',95),False,False,0)
                actions=Gtk.Box(spacing=8);card.pack_start(actions,False,False,0)
                for key,(caption,_) in STATES.items():
                    if key!=row['state']:actions.pack_start(ActionButton(caption,'check',lambda _,r=row,k=key:change(r,k),'neutral'),False,False,0)
            listing.show_all();return False
        def load():
            def work():
                try:rows=self.community_client().request('/v1/admin/requests').get('requests',[]);GLib.idle_add(paint,rows,None)
                except Exception as error:GLib.idle_add(paint,[],error)
            threading.Thread(target=work,daemon=True).start()
        def change(row,new_state):
            def work():
                try:self.community_client().request('/v1/admin/requests/'+row['id'],{'state':new_state,'note':''});GLib.idle_add(load)
                except Exception as error:GLib.idle_add(paint,[],error)
            threading.Thread(target=work,daemon=True).start()
        page.connect('destroy',lambda *_:state.update(alive=False));page.connect('response',lambda *_:page.destroy());page._mount();load()
        return page
