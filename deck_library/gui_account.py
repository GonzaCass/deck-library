"""Native account panel, with isolated provider forms inside the app."""
import json,pathlib,subprocess,threading,time
from gi.repository import Gtk,GLib,GdkX11
from .inline_pages import InlineDialog
from . import auth_runtime,motion
from .auth_policy import account_uri
from .community import Client
from .ui_components import ActionButton,text

class AccountSocket(Gtk.Socket):
    # A remote plug can advertise its previous allocation as its minimum.
    # Keep the containing dialog within the Deck screen; WebKit scrolls its page.
    def do_get_preferred_width(self):return (1,600)
    def do_get_preferred_height(self):return (180,420)

class AccountPane(Gtk.Box):
    def refresh_layout(self,*_):
        window=self.get_toplevel()
        if window is not self and hasattr(window,'refresh_layout'):window.refresh_layout()

    def __init__(self,client,on_change=lambda:None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        self.client=client;self.on_change=on_change;self.alive=True;self.generation=0;self.process=None;self.timer=None;self.wait=None;self.uri=None;self.deadline=0;self.install_cancel=threading.Event()
        self.pack_start(text('Cuenta','section-title'),False,False,0)
        self.summary=text('','title');self.pack_start(self.summary,False,False,0)
        self.actions=Gtk.Box(spacing=10);self.pack_start(self.actions,False,False,0)
        self.login=ActionButton('Iniciar sesión','community',lambda _:self.start('login'),'steam');self.register=ActionButton('Crear cuenta','plus',lambda _:self.start('register'),'violet-outline');self.logout=ActionButton('Cerrar sesión','undo',lambda _:self.signout(),'quiet')
        for button in (self.login,self.register,self.logout):
            button.show_all();button.set_no_show_all(True);self.actions.pack_start(button,False,False,0)
        self.stack=Gtk.Stack();self.stack.set_homogeneous(False);self.stack.set_vexpand(True);self.stack.connect('notify::visible-child',self.refresh_layout);self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE if motion.page_transitions() else Gtk.StackTransitionType.NONE);self.stack.set_transition_duration(120 if motion.page_transitions() else 0);self.pack_start(self.stack,True,True,0)
        intro=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);intro.set_valign(Gtk.Align.CENTER);intro.pack_start(text('Permite publicar ajustes, valorar perfiles y compartir resultados.','muted',64),False,False,0);intro.pack_start(text('Los perfiles se pueden consultar sin una cuenta.','meta',64),False,False,0);intro.pack_start(text('Para crear una cuenta es necesario verificar el correo.','meta',64),False,False,0);self.stack.add_named(intro,'intro')
        self.browser_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);self.stack.add_named(self.browser_box,'browser');self.socket=None
        self.fallback=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);self.stack.add_named(self.fallback,'fallback');self.reason=text('','muted',70);self.fallback.pack_start(self.reason,False,False,0)
        self.retry=ActionButton('Reintentar','refresh',lambda _:self.embed(),'violet-outline');self.fallback.pack_start(self.retry,False,False,0)
        self.install_button=ActionButton('Instalar componente de acceso','download',lambda _:self.install_runtime(),'violet');self.fallback.pack_start(self.install_button,False,False,0)
        self.external=ActionButton('Continuar en el navegador','community',lambda _:self.open_external(),'quiet');self.fallback.pack_start(self.external,False,False,0)
        self.code=text('','meta',70);self.code.set_selectable(True);self.fallback.pack_start(self.code,False,False,0)
        self.status=text('','status',85);self.pack_start(self.status,False,False,0)
        self.cancel_button=ActionButton('Cancelar acceso','back',lambda _:self.cancel(),'quiet');self.cancel_button.show_all();self.cancel_button.set_no_show_all(True);self.pack_start(self.cancel_button,False,False,0)
        self.connect('destroy',lambda *_:self.close());self.show_all();self.refresh();self.stack.set_visible_child_name('intro');self.cancel_button.hide()
        if self.client.session().get('token'):self.validate()

    def task(self,job,done,fail=None):
        generation=self.generation
        def finish(value,error):
            if not self.alive or generation!=self.generation:
                if isinstance(value,dict) and value.get('state')=='connected':
                    threading.Thread(target=lambda:self.revoke(value['token']),daemon=True).start()
                return False
            if error:
                self.status.set_text(error)
                if fail:fail()
            else:done(value)
            return False
        def work():
            try:GLib.idle_add(finish,job(),None)
            except Exception as error:GLib.idle_add(finish,None,str(error))
        threading.Thread(target=work,daemon=True).start()

    def revoke(self,token):
        try:self.client.request('/v1/logout',{},token=token)
        except Exception:pass

    def refresh(self):
        login=self.client.session().get('login');self.summary.set_text(login or 'Sin sesión')
        self.login.set_visible(not login);self.register.set_visible(not login);self.logout.set_visible(bool(login))
        self.on_change()

    def validate(self):
        self.status.set_text('Comprobando sesión…')
        def done(_):self.status.set_text('');self.refresh()
        self.task(self.client.me,done,self.refresh)

    def start(self,mode):
        self.cancel();self.mode=mode;self.status.set_text('Conectando…');self.login.set_sensitive(False);self.register.set_sensitive(False);self.cancel_button.show();self.actions.hide();self.summary.hide()
        def started(value):
            self.wait=value['wait_key'];self.uri=account_uri(value.get('verification_uri_complete') or value['verification_uri']);self.deadline=time.monotonic()+900
            self.code.set_text('Código: '+value['user_code']);self.embed();self.schedule(value.get('interval',5))
        def failed():self.login.set_sensitive(True);self.register.set_sensitive(True);self.cancel_button.hide();self.actions.show();self.summary.show()
        self.task(lambda:self.client.start('keycloak'),started,failed)

    def embed(self):
        self.stop_browser()
        display=self.get_display()
        if not isinstance(display,GdkX11.X11Display):self.unavailable('El acceso integrado necesita X11. Reiniciar la app con su lanzador o continuar en el navegador.',False);return
        for child in self.browser_box.get_children():child.destroy()
        self.socket=AccountSocket();self.socket.set_can_focus(True);self.socket.set_hexpand(True);self.socket.set_vexpand(True);self.socket.set_size_request(-1,240);self.browser_box.pack_start(self.socket,True,True,0);self.browser_box.show_all();self.stack.set_visible_child_name('browser');self.socket.realize()
        socket=self.socket;generation=self.generation
        def ready(args):
            self.status.set_text('Cargando acceso…')
            try:
                self.process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1)
                process=self.process;self.send({'uri':self.uri,'mode':self.mode});socket.connect('plug-removed',lambda *_:True)
                def events():
                    try:
                        for line in process.stdout:
                            try:value=json.loads(line)
                            except ValueError:continue
                            GLib.idle_add(self.browser_event,value,generation)
                    except (ValueError,OSError):pass
                    GLib.idle_add(self.browser_event,{'event':'exited'},generation,process)
                threading.Thread(target=events,daemon=True).start()
            except OSError:self.unavailable('No se pudo abrir el acceso integrado.',False)
        def missing():self.unavailable('El acceso integrado necesita WebKit de GNOME. Se descargará desde Flathub una sola vez.',True)
        self.task(lambda:auth_runtime.command(pathlib.Path(__file__).with_name('auth_browser.py'),socket.get_id()),ready,missing)

    def browser_event(self,value,generation,process=None):
        if not self.alive or generation!=self.generation:return False
        event=value.get('event')
        if event=='ready':
            self.status.set_text('Steam + X: abrir teclado · B: cancelar')
            if self.socket:self.socket.grab_focus()
        elif event in ('tls_error','load_error'):self.status.set_text('No se pudo cargar el acceso. Revisar la conexión o continuar en el navegador.');self.external.show();self.stack.set_visible_child_name('fallback');self.install_button.hide();self.reason.set_text('No se pudo cargar el acceso de forma segura.')
        elif event=='exited' and process is self.process and self.wait:self.unavailable('El componente de acceso se cerró. Se puede reintentar o continuar en el navegador.',False)
        return False

    def unavailable(self,reason,install):
        self.stack.set_visible_child_name('fallback');self.reason.set_text(reason);self.install_button.set_visible(install);self.retry.set_visible(not install);self.external.show();self.status.set_text('')

    def send(self,value):
        try:
            if self.process and self.process.poll() is None:self.process.stdin.write(json.dumps(value)+'\n');self.process.stdin.flush()
        except (OSError,ValueError):pass

    def handle_controller(self,action,window):
        if not self.wait:return False
        if action=='back':self.cancel();return True
        if self.stack.get_visible_child_name()!='browser' or not self.socket:return False
        focus=window.get_focus()
        if focus is self.socket or focus is None:
            if action in ('up','down','left','right','activate'):self.send({'action':action});return True
        return False

    def open_external(self):
        if self.uri:subprocess.Popen(['xdg-open',self.uri],start_new_session=True)

    def install_runtime(self):
        self.install_button.set_sensitive(False);self.status.set_text('Instalando componente desde Flathub…');self.install_cancel=threading.Event();cancel=self.install_cancel
        def done(_):self.install_button.set_sensitive(True);self.embed()
        self.task(lambda:auth_runtime.install(lambda *_:None,cancel),done,lambda:self.install_button.set_sensitive(True))

    def schedule(self,interval):self.timer=GLib.timeout_add_seconds(min(60,max(5,int(interval))),self.poll)
    def poll(self):
        self.timer=None
        if not self.alive or not self.wait:return False
        if time.monotonic()>self.deadline:self.cancel();self.status.set_text('El acceso venció. Volver a intentarlo.');return False
        def done(value):
            if value.get('state')=='connected':
                self.client.remember(value);self.cancel();self.refresh();self.status.set_text('Sesión iniciada.')
            else:self.schedule(value.get('interval',5))
        self.task(lambda:self.client.poll(self.wait,persist=False),done,self.failed_poll);return False
    def failed_poll(self):
        message=self.status.get_text();self.cancel();self.status.set_text(message)
    def signout(self):
        self.cancel();self.logout.set_sensitive(False)
        def done(_):self.logout.set_sensitive(True);self.refresh();self.status.set_text('Sesión cerrada.')
        self.task(self.client.logout,done,lambda:(self.logout.set_sensitive(True),self.refresh()))
    def stop_browser(self):
        process=self.process;self.process=None
        if process:
            self.send_close(process)
            def reap():
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:process.wait(timeout=2)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
                for stream in (process.stdin,process.stdout):
                    if stream:stream.close()
            threading.Thread(target=reap,daemon=True).start()
    @staticmethod
    def send_close(process):
        try:process.stdin.write('{"action":"close"}\n');process.stdin.flush()
        except (OSError,ValueError):pass
    def cancel(self):
        self.generation+=1;self.wait=None;self.install_cancel.set()
        if self.timer:
            if GLib.MainContext.default().find_source_by_id(self.timer):GLib.source_remove(self.timer)
            self.timer=None
        self.stop_browser();self.stack.set_visible_child_name('intro');self.login.set_sensitive(True);self.register.set_sensitive(True);self.cancel_button.hide();self.status.set_text('');self.actions.show();self.summary.show()
    def close(self):
        if self.alive:self.cancel();self.alive=False

def account_dialog(window):
    dialog=InlineDialog(title='Cuenta · Deck Library',transient_for=window,modal=True)
    width,height=window.get_size();dialog.set_default_size(min(900,width-32),min(720,height-48));dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
    content=dialog.get_content_area();content.set_border_width(18)
    pane=AccountPane(Client(window.store,window.preferences.get('community_url','https://presets.jokerlan.xyz')));scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);scroll.add(pane);content.pack_start(scroll,True,True,0)
    dialog.account_controller=lambda action:pane.handle_controller(action,dialog)
    dialog.show();pane.show();dialog.run();pane.close();dialog.destroy()
