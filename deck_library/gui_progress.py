"""Progress belongs to each port's row in both catalog and updates."""
import time
from gi.repository import Gtk,GLib
from .transfer import Progress,caption

class ProgressMixin:
    def transfer_row(self,parent,key):
        from .gui import label
        if not hasattr(self,'transfer_views'):self.transfer_views={};self.transfers={}
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);bar=Gtk.ProgressBar();bar.set_show_text(True);status=label('','status');box.pack_start(bar,False,False,0);box.pack_start(status,False,False,0);parent.pack_start(box,False,False,0)
        control=Gtk.Button(label='Cancelar');control.connect('clicked',lambda _:self.cancel_transfer(key));box.pack_start(control,False,False,0);box.transfer_control=control
        self.transfer_views.setdefault(key,[]).append((box,bar,status));box.set_no_show_all(True)
        if key in self.transfers:self.paint_transfer(key)
        else:box.hide()
        return box

    def start_transfer(self,key):
        if not hasattr(self,'transfers'):self.transfers={};self.transfer_views={}
        self.transfers[key]=Progress();self.paint_transfer(key)

    def transfer_event(self,key,event):
        if self.ui_closed:return False
        if key not in getattr(self,'transfers',{}):self.start_transfer(key)
        state=self.transfers[key].update(event);self.paint_transfer(key);self.set_status(caption(state));return False

    def paint_transfer(self,key):
        state=self.transfers[key].state
        live=[]
        for box,bar,status in self.transfer_views.get(key,[]):
            if box.get_parent() is None:continue
            live.append((box,bar,status));box.set_no_show_all(False);box.show_all();box.set_no_show_all(True)
            fraction=state.get('fraction')
            if fraction is None:bar.pulse();bar.set_text(state.get('text','Trabajando…'))
            else:bar.set_fraction(fraction);bar.set_text(f'{fraction*100:.0f}%')
            status.set_text(caption(state))
            control=box.transfer_control;active=key in getattr(self,'port_jobs',{})
            control.set_label('Cancelar' if active else 'Descartar');control.set_visible(active or state.get('phase') in ('done','error','cancelled'))
        self.transfer_views[key]=live

    def finish_transfer(self,key,error=None):
        self.transfer_event(key,{'phase':'error' if error else 'done','fraction':0 if error else 1,'text':('Error: '+error) if error else 'Actualización completada','eta':None})

    def port_progress(self,key):
        last=[0]
        def update(event):
            now=time.monotonic()
            if isinstance(event,str) or now-last[0]>=.12 or event.get('done')==event.get('total'):
                last[0]=now;GLib.idle_add(self.transfer_event,key,event)
        return update

    def cancel_transfer(self,key):
        event=getattr(self,'port_jobs',{}).get(key)
        if event:
            event.set();self.transfer_event(key,'Cancelando…')
        else:
            self.transfers.pop(key,None)
            for box,_,_ in self.transfer_views.get(key,[]):box.hide()
            self.set_status('')
