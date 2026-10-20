"""Compact, non-interactive controller legends for Deck and PlayStation buttons."""
from gi.repository import Gtk

class ControllerHints(Gtk.Box):
    def __init__(self,compact=False):
        super().__init__(spacing=14)
        self.set_valign(Gtk.Align.CENTER);self.items={};self.compact=compact;self._state=None
        groups=[('activate','A / ✕','Seleccionar'),('back','B / ○','Volver')]
        if not compact:groups += [('move','L','Mover'),('scroll','R','Desplazar'),('tabs','LB/RB · L1/R1','Pestañas'),('search','X / □','Teclado')]
        for name,glyph,caption in groups:
            item=Gtk.Box(spacing=6);badge=Gtk.Label(label=glyph);badge.get_style_context().add_class('control-glyph')
            if name in ('move','scroll'):badge.get_style_context().add_class('control-stick');badge.set_tooltip_text('Palanca izquierda / cruceta' if name=='move' else 'Palanca derecha')
            label=Gtk.Label(label=caption);label.get_style_context().add_class('control-caption')
            item.pack_start(badge,False,False,0);item.pack_start(label,False,False,0);self.pack_start(item,False,False,0);self.items[name]=(item,label)
        self.show_all()
    def update(self,activate='Seleccionar',back='Volver',width=1280):
        state=(activate,back,width>=1100,width>=920)
        if state==self._state:return
        self._state=state
        self.items['activate'][1].set_text(activate);self.items['back'][1].set_text(back)
        if not self.compact:
            self.items['search'][0].set_visible(width>=1100)
            self.items['tabs'][0].set_visible(width>=920)
