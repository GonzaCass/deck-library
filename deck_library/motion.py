"""Small, optional UI motion: fades, staggered entrances and toasts. Every helper does nothing when animations are off.

Durations follow common UI guidance: micro-interactions 150-300 ms, list entrances 250-350 ms with a short stagger,
ease-out curves, and no continuous motion outside loaders.
"""
import gi
import os,sys
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib

def enabled():
    """False when the user turned animations off (Ajustes) or the desktop asks for reduced motion."""
    settings=Gtk.Settings.get_default()
    return bool(settings is None or settings.get_property('gtk-enable-animations'))

def gaming_mode():
    return bool('--gaming' in sys.argv or os.environ.get('SteamAppId') or os.environ.get('SteamGameId'))

def page_transitions():
    # Gamescope can snapshot a GTK Stack while its new scrolled child still needs
    # allocation. Switch directly there, then fade the already allocated page.
    return enabled() and not gaming_mode()

def ease_out(t):return 1-(1-t)**3

def smooth_scroll(adjustment,target,duration=95):
    """Glide a Gtk.Adjustment to `target` smoothly instead of jumping in one frame."""
    lower=adjustment.get_lower();upper=max(lower,adjustment.get_upper()-adjustment.get_page_size())
    target=max(lower,min(upper,float(target)))
    if os.environ.get('DECK_LIBRARY_UI_TESTS') or os.environ.get('DECK_LIBRARY_UI_PREVIEW')=='1' or not enabled():
        adjustment.set_value(target);return
    start=adjustment.get_value()
    if abs(target-start)<1.5:
        adjustment.set_value(target);return
    previous=getattr(adjustment,'_deck_scroll_source',None)
    if previous and GLib.MainContext.default().find_source_by_id(previous):
        if abs(target-getattr(adjustment,'_deck_scroll_target',-99999))<1.5:return
        GLib.source_remove(previous)
    adjustment._deck_scroll_target=target
    import time
    t0=time.monotonic()
    def step():
        elapsed=(time.monotonic()-t0)*1000.0
        t=min(1.0,elapsed/max(1.0,duration))
        adjustment.set_value(start+(target-start)*ease_out(t))
        if t>=1.0:
            adjustment._deck_scroll_source=None
            return False
        return True
    adjustment._deck_scroll_source=GLib.timeout_add(16,step)

def enter_page(widget, duration=150):
    """Fade an allocated page smoothly without flashing or taking a Gtk.Stack snapshot."""
    if not enabled() or os.environ.get('DECK_LIBRARY_UI_PREVIEW')=='1':
        widget.set_opacity(1);return
    widget.set_opacity(0.35)
    def enter():
        if not widget.get_mapped():widget.set_opacity(1);return False
        root=widget.get_toplevel()
        root.queue_resize();root.check_resize()
        fade_in(widget,duration=duration,start_opacity=0.35)
        return False
    GLib.idle_add(enter)

def fade_in(widget,duration=180,delay=0,rise=0,start_opacity=0):
    """Animate opacity smoothly on the widget's frame clock without mutating margins (which causes layout jitter)."""
    previous=getattr(widget,'_deck_fade_tick',None)
    if previous:widget.remove_tick_callback(previous);widget._deck_fade_tick=None
    if not enabled() or os.environ.get('DECK_LIBRARY_UI_PREVIEW')=='1':
        widget.set_opacity(1);return
    widget.set_opacity(start_opacity);state={'start':None}
    def tick(w,clock):
        if not enabled():w.set_opacity(1);w._deck_fade_tick=None;return False
        now=clock.get_frame_time()/1000
        if state['start'] is None:state['start']=now+delay
        t=(now-state['start'])/duration
        if t<=0:return True
        t=min(1,t);eased=ease_out(t);w.set_opacity(start_opacity+(1-start_opacity)*eased)
        if t>=1:w._deck_fade_tick=None
        return t<1
    widget._deck_fade_tick=widget.add_tick_callback(tick)

def stagger(widgets,step=20,limit=12,duration=180,rise=0):
    """Subtle opacity entrance without margin reflows."""
    for index,widget in enumerate(widgets):
        if index<limit:fade_in(widget,duration,delay=index*step,rise=0,start_opacity=0.45)

class Toast(Gtk.Revealer):
    """A readable, dismissible floating notice that disappears automatically."""
    def __init__(self):
        super().__init__();self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN);self.set_halign(Gtk.Align.CENTER);self.set_valign(Gtk.Align.START);self.set_margin_top(18);self.set_margin_start(24);self.set_margin_end(24)
        self.text=Gtk.Label(xalign=0);self.text.set_line_wrap(True);self.text.set_max_width_chars(54);self.text.get_style_context().add_class('toast-text')
        self.box=Gtk.Box(spacing=16);self.box.get_style_context().add_class('toast');self.icon=Gtk.Image.new_from_icon_name('emblem-ok-symbolic',Gtk.IconSize.LARGE_TOOLBAR);self.box.pack_start(self.icon,False,False,0);self.box.pack_start(self.text,True,True,0)
        close=Gtk.Button(label='×');close.set_can_focus(False);close.set_tooltip_text('Cerrar aviso');close.get_accessible().set_name('Cerrar aviso');close.connect('clicked',lambda _:self.hide_text());self.box.pack_end(close,False,False,0)
        self.add(self.box);self.timer=None;self.last_text=''
    def show_text(self,text,seconds=5):
        self.last_text=text;self.text.set_text(text);error=any(word in text.casefold() for word in ('no se pudo','error','falló','no se pudieron'))
        style=self.box.get_style_context();style.add_class('error') if error else style.remove_class('error');self.icon.set_from_icon_name('dialog-error-symbolic' if error else 'emblem-ok-symbolic',Gtk.IconSize.LARGE_TOOLBAR)
        self.set_transition_duration(180 if enabled() else 0);self.show_all();self.set_reveal_child(True)
        if self.timer:GLib.source_remove(self.timer)
        self.timer=GLib.timeout_add(int(seconds*1000),self.hide_text)
    def hide_text(self):
        if self.timer and GLib.MainContext.default().find_source_by_id(self.timer):GLib.source_remove(self.timer)
        self.timer=None;self.set_reveal_child(False);return False
    def do_destroy(self):
        self.hide_text();Gtk.Revealer.do_destroy(self)
