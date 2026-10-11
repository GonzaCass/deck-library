"""Small, optional UI motion: fades, staggered entrances and toasts. Every helper does nothing when animations are off.

Durations follow common UI guidance: micro-interactions 150-300 ms, list entrances 250-350 ms with a short stagger,
ease-out curves, and no continuous motion outside loaders.
"""
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib

def enabled():
    """False when the user turned animations off (Ajustes) or the desktop asks for reduced motion."""
    settings=Gtk.Settings.get_default()
    return bool(settings is None or settings.get_property('gtk-enable-animations'))

def ease_out(t):return 1-(1-t)**3

def fade_in(widget,duration=260,delay=0,rise=0):
    """Animate opacity 0 -> 1 (and an optional upward slide through the top margin) on the widget's frame clock."""
    if not enabled():widget.set_opacity(1);return
    widget.set_opacity(0);base=widget.get_margin_top();state={'start':None}
    if rise:widget.set_margin_top(base+rise)
    def tick(w,clock):
        now=clock.get_frame_time()/1000
        if state['start'] is None:state['start']=now+delay
        t=(now-state['start'])/duration
        if t<=0:return True
        t=min(1,t);eased=ease_out(t);w.set_opacity(eased)
        if rise:w.set_margin_top(int(base+rise*(1-eased)))
        return t<1
    widget.add_tick_callback(tick)

def stagger(widgets,step=35,limit=16,duration=280,rise=10):
    """Fade a list of widgets in one after another; only the first `limit` animate, the rest appear at once."""
    for index,widget in enumerate(widgets):
        if index<limit:fade_in(widget,duration,delay=index*step,rise=rise)

class Toast(Gtk.Revealer):
    """A short confirmation that slides up, waits and slides away."""
    def __init__(self):
        super().__init__();self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP);self.set_halign(Gtk.Align.CENTER);self.set_valign(Gtk.Align.END);self.set_margin_bottom(28)
        self.text=Gtk.Label();self.text.get_style_context().add_class('toast-text');box=Gtk.Box();box.get_style_context().add_class('toast');box.add(self.text);self.add(box);self.timer=None
    def show_text(self,text,seconds=3.2):
        self.text.set_text(text);self.set_transition_duration(220 if enabled() else 0);self.show_all();self.set_reveal_child(True)
        if self.timer:GLib.source_remove(self.timer)
        self.timer=GLib.timeout_add(int(seconds*1000),self.hide_text)
    def hide_text(self):
        self.timer=None;self.set_reveal_child(False);return False
