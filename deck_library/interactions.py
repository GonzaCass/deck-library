"""Explicit text input and touch/mouse-emulated drag scrolling for the Deck."""
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk


def manual_text_input(widget):
    if isinstance(widget,Gtk.Entry) and not widget.get_input_hints()&Gtk.InputHints.INHIBIT_OSK:
        widget.set_input_hints(widget.get_input_hints()|Gtk.InputHints.INHIBIT_OSK)
    if isinstance(widget,Gtk.Container):
        for child in widget.get_children():manual_text_input(child)


def configure_scroll(scroll):
    if getattr(scroll,'_deck_drag',None):return scroll
    from gi.repository import GLib
    import time,os
    scroll.set_kinetic_scrolling(True);scroll.set_capture_button_press(True)
    drag=Gtk.GestureDrag.new(scroll);drag.set_button(1);drag.set_touch_only(False);drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
    state={'active':False,'claimed':False,'vx':0.0,'vy':0.0,'last_x':0.0,'last_y':0.0,'last_t':0.0,'momentum':None}
    def stop_momentum():
        if state['momentum'] and GLib.MainContext.default().find_source_by_id(state['momentum']):
            GLib.source_remove(state['momentum'])
        state['momentum']=None
    def begin(gesture,x,y):
        stop_momentum()
        state.update(active=False,claimed=False,vx=0.0,vy=0.0,last_x=0.0,last_y=0.0,last_t=time.monotonic())
        event=Gtk.get_current_event();device=event.get_source_device() if event else None
        # Real touch events already have GTK's kinetic scrolling. Steam may instead
        # expose touch as mouse events; only that path needs the drag fallback.
        if device and device.get_source()==Gdk.InputSource.TOUCHSCREEN:return
        widget=Gtk.get_event_widget(event) if event else None
        while widget is not None and widget is not scroll:
            if isinstance(widget,(Gtk.Entry,Gtk.TextView,Gtk.Range,Gtk.Switch)):return
            widget=widget.get_parent()
        state.update(active=True,x=scroll.get_hadjustment().get_value(),y=scroll.get_vadjustment().get_value())
    def update(gesture,x,y):
        if not state['active']:return
        horizontal=scroll.get_hadjustment();vertical=scroll.get_vadjustment()
        dx=horizontal.get_upper()-horizontal.get_page_size()-horizontal.get_lower()
        dy=vertical.get_upper()-vertical.get_page_size()-vertical.get_lower()
        if not state['claimed']:
            if max(abs(x),abs(y))<10:return
            if not ((dy>0 and abs(y)>=abs(x)) or (dx>0 and abs(x)>abs(y))):return
            state['claimed']=True;gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        now=time.monotonic();dt=max(0.004,now-state['last_t'])
        state['vx']=0.65*state['vx']+0.35*((x-state['last_x'])/dt)
        state['vy']=0.65*state['vy']+0.35*((y-state['last_y'])/dt)
        state['last_x']=x;state['last_y']=y;state['last_t']=now
        for adjustment,origin,offset in ((horizontal,state['x'],x),(vertical,state['y'],y)):
            adjustment.set_value(max(adjustment.get_lower(),min(adjustment.get_upper()-adjustment.get_page_size(),origin-offset)))
    def end(*_):
        was_claimed=state['claimed']
        state['active']=False
        if not was_claimed or os.environ.get('DECK_LIBRARY_UI_TESTS'):return
        vx,vy=state['vx'],state['vy']
        if max(abs(vx),abs(vy))<60:return
        def tick():
            nonlocal vx,vy
            vx*=0.88;vy*=0.88
            if max(abs(vx),abs(vy))<12:
                state['momentum']=None;return False
            for adjustment,vel in ((scroll.get_hadjustment(),vx),(scroll.get_vadjustment(),vy)):
                upper=max(adjustment.get_lower(),adjustment.get_upper()-adjustment.get_page_size())
                if upper>adjustment.get_lower() and abs(vel)>=12:
                    adjustment.set_value(max(adjustment.get_lower(),min(upper,adjustment.get_value()-vel*0.016)))
            return True
        state['momentum']=GLib.timeout_add(16,tick)
    drag.connect('drag-begin',begin);drag.connect('drag-update',update);drag.connect('drag-end',end)
    scroll._deck_drag=drag;scroll._deck_drag_begin=begin;scroll._deck_drag_update=update
    return scroll
