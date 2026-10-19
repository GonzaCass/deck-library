"""Community actions, explicit publication, and GitHub device sign-in."""
import threading,subprocess
from gi.repository import Gtk,GLib
from .community import Client
from .installations import save_settings
from . import presets

class CommunityMixin:
    def community_dialog(self,e):
        from .gui import label,button,wrap_row
        dialog=Gtk.Dialog(title='Comunidad · '+e.name,transient_for=self,modal=True);dialog.set_default_size(760,600);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE);box=dialog.get_content_area();box.set_border_width(16);box.set_spacing(10)
        box.pack_start(label('Ajustes comunitarios','title'),False,False,0);url=Gtk.Entry();url.set_text(self.preferences.get('community_url','https://presets.jokerlan.xyz'));url.set_placeholder_text('https://presets.jokerlan.xyz');box.pack_start(url,False,False,0)
        status=label('La consulta es pública. Publicar y comentar requiere iniciar sesión con GitHub.','muted');box.pack_start(status,False,False,0)
        rows=Gtk.ListBox();scroll=self.new_scroll();scroll.set_min_content_height(150);scroll.add(rows);box.pack_start(scroll,True,True,0);selected=[None];pending=[None];alive=[True];busy=[False];server=[url.get_text().strip()];actions=wrap_row();box.pack_start(actions,False,False,0)
        def client():return Client(self.store,server[0])
        try:
            login=client().session().get('login')
            if login:status.set_text('Sesión: '+login+'. Podés consultar, publicar o comentar perfiles.')
        except ValueError:pass
        def chosen(_,row):selected[0]=getattr(row,'value',None)
        rows.connect('row-selected',chosen)
        def run(job,done):
            if busy[0]:return
            server[0]=url.get_text().strip();busy[0]=True;status.set_text('Conectando…');actions.set_sensitive(False);url.set_sensitive(False)
            def finish(value,error):
                busy[0]=False
                if not alive[0]:return False
                actions.set_sensitive(True);url.set_sensitive(True)
                if error:status.set_text(error)
                else:done(value)
                return False
            def work():
                try:value=job();GLib.idle_add(finish,value,None)
                except Exception as exc:GLib.idle_add(finish,None,str(exc))
            threading.Thread(target=work,daemon=True).start()
        def found(values):
            selected[0]=None
            for row in rows.get_children():rows.remove(row)
            for value in values:
                row=Gtk.ListBoxRow();row.value=value;body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5);body.set_border_width(8);body.pack_start(label(value['preset']['name'],'title'),False,False,0);body.pack_start(label(value['author']+' · '+value['preset']['objective']+f" · {value.get('works',0)} funcionó / {value.get('issues',0)} problemas"+(' · '+{'pending':'pendiente de revisión','approved':'publicado','rejected':'rechazado'}.get(value.get('status'),value.get('status','')) if value.get('status') else ''),'muted'),False,False,0);row.add(body);rows.add(row)
            rows.show_all();status.set_text(f'{len(values)} perfiles publicados. Descargá uno para revisar sus cambios antes de aplicarlo.')
        def search(_,mine=False):
            try:server[0]=url.get_text().strip();c=client();self.preferences['community_url']=c.url;save_settings(self.preferences,self.store)
            except Exception as exc:status.set_text(str(exc));return
            run(lambda:c.search(e,mine=mine),found)
        def signin(_):
            def started(value):
                pending[0]=value['wait_key'];status.set_text('Ingresá el código '+value['user_code']+' en github.com/login/device. Después pulsá «Confirmar acceso».');subprocess.Popen(['xdg-open','https://github.com/login/device'])
            run(lambda:client().start(),started)
        def poll(_):
            if not pending[0]:status.set_text('Primero pulsá «Iniciar sesión».');return
            run(lambda:client().poll(pending[0]),lambda value:status.set_text('Conectado como '+value['login'] if value.get('state')=='connected' else 'GitHub todavía espera la autorización.'))
        def download(_):
            if not selected[0]:status.set_text('Seleccioná un perfil.');return
            try:client().download(selected[0]);self.game_tab='profiles';dialog.response(Gtk.ResponseType.CLOSE);GLib.idle_add(lambda:(self.show_detail(e),False)[1])
            except Exception as exc:status.set_text(str(exc))
        def publish(_):
            try:
                server[0]=url.get_text().strip();c=client();login=c.session().get('login')
                if not login:raise ValueError('Iniciá sesión antes de publicar.')
                value=presets.export_current(e,e.name+' — '+login,login,self.store,self.preferences.get('eden_config') or None)
                if not self.confirm('Publicar mis ajustes',value['name']+'\n\nSe publican las opciones permitidas del JSON, tu alias de GitHub y la identidad del juego bajo licencia MIT. El aporte queda pendiente de revisión. No se envía el archivo completo del emulador.','Publicar'):return
                run(lambda:c.publish(value),lambda result:status.set_text('Aporte recibido, pendiente de revisión.'))
            except Exception as exc:status.set_text(str(exc))
        def feedback(_,result):
            if not selected[0]:status.set_text('Seleccioná un perfil.');return
            row=selected[0];run(lambda:client().feedback(row,result),lambda result:status.set_text('Comentario guardado.'))
        for title,action in [('Buscar perfiles',search),('Mis aportes',lambda w:search(w,True)),('Iniciar sesión',signin),('Confirmar acceso',poll),('Descargar y revisar',download),('Publicar mis ajustes',publish),('Me funcionó',lambda w:feedback(w,'works')),('Tuve problemas',lambda w:feedback(w,'issues')),('Cerrar sesión',lambda _:run(lambda:client().logout(),lambda _:status.set_text('Sesión cerrada.')))]:actions.pack_start(button(title,action,primary=title=='Descargar y revisar'),False,False,0)
        self.fit_dialog(dialog);dialog.show_all();dialog.run();alive[0]=False;dialog.destroy()
