"""Isolated, ephemeral WebKit account view embedded through GTK XEmbed.

The parent only sends navigation actions; credentials stay in Keycloak's page.
No page content, password, cookie or provider token is read or returned.
"""
import json,sys,os
import gi
gi.require_version('Gtk','3.0');gi.require_version('WebKit2','4.1')
from gi.repository import Gtk,GLib,WebKit2,Gdk
from auth_policy import origin,allowed_navigation

def emit(event,**fields):print(json.dumps({'event':event,**fields}),flush=True)

def main():
    initial=bytearray()
    while len(initial)<16384:
        byte=os.read(sys.stdin.fileno(),1)
        if byte in (b'\n',b''):break
        initial.extend(byte)
    config=json.loads(initial);uri=config['uri'];expected=origin(uri);register=config.get('mode')=='register'
    plug=Gtk.Plug.new(int(sys.argv[1]));context=WebKit2.WebContext.new_ephemeral();view=WebKit2.WebView.new_with_context(context)
    settings=view.get_settings();settings.set_enable_developer_extras(False);settings.set_javascript_can_open_windows_automatically(False)
    view.set_background_color(Gdk.RGBA(red=.067,green=.071,blue=.086,alpha=1));plug.add(view)
    def policy(_,decision,kind):
        if kind in (WebKit2.PolicyDecisionType.NAVIGATION_ACTION,WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION):
            target=decision.get_navigation_action().get_request().get_uri()
            if kind==WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION or not allowed_navigation(target,expected):decision.ignore();emit('blocked');return True
        return False
    view.connect('decide-policy',policy);view.connect('permission-request',lambda _,request:(request.deny(),True)[1])
    view.connect('load-failed-with-tls-errors',lambda *_:(emit('tls_error'),True)[1])
    view.connect('load-failed',lambda _,event,uri,error:(emit('load_error'),False)[1])
    view.connect('web-process-terminated',lambda *_:emit('load_error'))
    registration_requested=[False]
    def loaded(_,event):
        if event!=WebKit2.LoadEvent.FINISHED:return
        emit('ready')
        if register and not registration_requested[0]:
            def registered(web,result,*_):
                try:registration_requested[0]=web.evaluate_javascript_finish(result).to_boolean()
                except GLib.Error:pass
            view.evaluate_javascript("(()=>{const a=document.querySelector('a[href*=\"login-actions/registration\"]');if(a){a.click();return true;}return false;})()",-1,None,None,None,registered,None)
    view.connect('load-changed',loaded)
    def action(value):
        name=value.get('action')
        if name=='close':Gtk.main_quit();return
        if name=='reload':view.reload();return
        if name not in ('up','down','left','right','activate'):return
        view.grab_focus()
        if name=='activate':script="(()=>{const a=document.activeElement;if(a&&a.matches('button,a,input[type=submit]'))a.click();else if(a&&a.form)a.form.requestSubmit();})()"
        else:
            delta=-1 if name in ('up','left') else 1
            first='a.length-1' if delta<0 else '0'
            script="(()=>{const a=[...document.querySelectorAll('input:not([type=hidden]):not([disabled]),button:not([disabled]),a[href],select,textarea,[tabindex=\"0\"]')].filter(e=>e.getClientRects().length);if(!a.length)return;const i=a.indexOf(document.activeElement);a[i<0?"+first+":(i+"+str(delta)+"+a.length)%a.length].focus();})()"
        view.evaluate_javascript(script,-1,None,None,None,None,None)
    incoming=bytearray()
    def receive(_,condition):
        if condition & (GLib.IOCondition.HUP|GLib.IOCondition.ERR):Gtk.main_quit();return False
        chunk=os.read(sys.stdin.fileno(),4096)
        if not chunk:Gtk.main_quit();return False
        incoming.extend(chunk)
        if len(incoming)>16384:Gtk.main_quit();return False
        while b'\n' in incoming:
            line,_,rest=incoming.partition(b'\n');incoming[:]=rest
            try:action(json.loads(line))
            except (ValueError,TypeError):pass
        return True
    GLib.io_add_watch(sys.stdin,GLib.IOCondition.IN|GLib.IOCondition.HUP|GLib.IOCondition.ERR,receive)
    plug.connect('destroy',lambda *_:Gtk.main_quit());plug.show_all();view.load_uri(uri);Gtk.main()
if __name__=='__main__':main()
