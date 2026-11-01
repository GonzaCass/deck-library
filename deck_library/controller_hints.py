"""Compact, non-interactive controller legends for PlayStation, Steam Deck, Xbox and Switch buttons."""
import math
import gi
gi.require_version('Gtk','3.0')
gi.require_version('PangoCairo','1.0')
from gi.repository import Gtk,Pango,PangoCairo

LAYOUTS={
    'ps':{'activate':'✕','options':'△','search':'□','move':'L','tabs':'L1/R1','back':'○'},
    'deck':{'activate':'A','options':'Y','search':'X','move':'L','tabs':'L1/R1','back':'B'},
    'xbox':{'activate':'A','options':'Y','search':'X','move':'L','tabs':'LB/RB','back':'B'},
    'switch':{'activate':'A','options':'X','search':'Y','move':'L','tabs':'L/R','back':'B'},
}


def _round_rect(cr,x,y,w,h,r):
    cr.new_path()
    for cx,cy,a,b in [(x+w-r,y+r,-math.pi/2,0),(x+w-r,y+h-r,0,math.pi/2),(x+r,y+h-r,math.pi/2,math.pi),(x+r,y+r,math.pi,math.pi*1.5)]:cr.arc(cx,cy,r,a,b)
    cr.close_path()


class ControllerGlyph(Gtk.DrawingArea):
    """Authentic vector DualSense/DualShock caps for PlayStation and clean console caps for Deck/Xbox/Switch."""
    def __init__(self,role,layout='ps'):
        super().__init__()
        self.role=role;self.layout=layout
        self.set_valign(Gtk.Align.CENTER)
        self._sync_size()
        self.connect('draw',self.draw_glyph)

    def _sync_size(self):
        if self.role=='tabs':self.set_size_request(52,22)
        else:self.set_size_request(24,24)

    def set_layout(self,layout):
        self.layout=layout if layout in LAYOUTS else 'ps'
        self._sync_size();self.queue_draw()

    def _draw_text(self,cr,value,cx,cy,font,rgb):
        layout=self.create_pango_layout(value);layout.set_font_description(Pango.FontDescription(font))
        tw,th=layout.get_pixel_size();cr.set_source_rgb(*rgb);cr.move_to(cx-tw/2,cy-th/2);PangoCairo.show_layout(cr,layout)

    def draw_glyph(self,widget,cr):
        w,h=self.get_allocated_width(),self.get_allocated_height()
        cx,cy=w/2,h/2
        if self.role=='tabs':
            caption=LAYOUTS[self.layout]['tabs']
            _round_rect(cr,1,2,w-2,h-4,6);cr.set_source_rgb(.12,.14,.18);cr.fill_preserve()
            cr.set_line_width(1.2);cr.set_source_rgb(.32,.37,.45);cr.stroke()
            self._draw_text(cr,caption,cx,cy,'Sans Bold 8.5',(.92,.95,.98));return False
        if self.role in ('move','scroll'):
            cr.arc(cx,cy,10.5,0,math.tau);cr.set_source_rgb(.10,.12,.15);cr.fill_preserve()
            cr.set_line_width(1.2);cr.set_source_rgb(.30,.35,.42);cr.stroke()
            cr.arc(cx,cy,7.8,0,math.tau);cr.set_source_rgb(.17,.20,.25);cr.fill_preserve()
            cr.set_line_width(1.0);cr.set_source_rgb(.42,.48,.56);cr.stroke()
            self._draw_text(cr,'L' if self.role=='move' else 'R',cx,cy,'Sans Bold 8.5',(.94,.96,.99));return False
        if self.layout=='ps':
            cr.arc(cx,cy,10.5,0,math.tau);cr.set_source_rgb(.10,.12,.15);cr.fill_preserve()
            cr.set_line_width(1.3);cr.set_source_rgb(.27,.32,.40);cr.stroke()
            cr.set_line_cap(1);cr.set_line_join(1)
            if self.role=='activate':  # Authentic PlayStation Cross (Blue)
                cr.set_source_rgb(.38,.66,1.0);cr.set_line_width(2.3)
                d=4.4;cr.move_to(cx-d,cy-d);cr.line_to(cx+d,cy+d);cr.stroke()
                cr.move_to(cx+d,cy-d);cr.line_to(cx-d,cy+d);cr.stroke()
            elif self.role=='back':  # Authentic PlayStation Circle (Coral Red)
                cr.set_source_rgb(1.0,.42,.42);cr.set_line_width(2.2)
                cr.arc(cx,cy,5.1,0,math.tau);cr.stroke()
            elif self.role=='options':  # Authentic PlayStation Triangle (Mint Teal)
                cr.set_source_rgb(.24,.88,.64);cr.set_line_width(2.1)
                cr.move_to(cx,cy-5.2);cr.line_to(cx+5.1,cy+4.0);cr.line_to(cx-5.1,cy+4.0);cr.close_path();cr.stroke()
            elif self.role=='search':  # Authentic PlayStation Square (Pink Lavender)
                cr.set_source_rgb(.94,.56,.88);cr.set_line_width(2.1)
                cr.rectangle(cx-4.5,cy-4.5,9.0,9.0);cr.stroke()
            return False
        letter=LAYOUTS[self.layout][self.role]
        fills={
            'xbox':{'activate':(.22,.68,.36),'back':(.86,.28,.28),'search':(.24,.56,.92),'options':(.88,.68,.18)},
            'deck':{'activate':(.88,.91,.95),'back':(.24,.28,.34),'search':(.24,.28,.34),'options':(.24,.28,.34)},
            'switch':{'activate':(.88,.26,.28),'back':(.88,.68,.18),'options':(.24,.56,.92),'search':(.22,.68,.36)},
        }[self.layout]
        fill=fills[self.role]
        ink=(.06,.07,.09) if (self.layout=='deck' and self.role=='activate') or (self.layout in ('xbox','switch') and self.role=='options' and fill[1]>.6) else (.96,.98,1.0)
        cr.arc(cx,cy,10.2,0,math.tau);cr.set_source_rgb(*fill);cr.fill_preserve()
        cr.set_line_width(1.1);cr.set_source_rgba(1,1,1,.22);cr.stroke()
        self._draw_text(cr,letter,cx,cy,'Sans Bold 9.5',ink)
        return False


class ControllerHints(Gtk.Box):
    def __init__(self,compact=False,layout='ps'):
        super().__init__(spacing=14)
        self.set_valign(Gtk.Align.CENTER);self.items={};self.badges={};self.icons={};self.compact=compact;self._state=None;self.layout='ps'
        glyphs=LAYOUTS.get(layout,LAYOUTS['ps'])
        groups=[('activate',glyphs['activate'],'Seleccionar'),('back',glyphs['back'],'Volver')] if compact else [('activate',glyphs['activate'],'Seleccionar'),('options',glyphs['options'],'Opciones'),('search',glyphs['search'],'Buscar'),('move',glyphs['move'],'Mover'),('tabs',glyphs['tabs'],'Pestañas'),('back',glyphs['back'],'Volver')]
        for name,glyph,caption in groups:
            item=Gtk.Box(spacing=6);item.get_style_context().add_class('hint-'+name)
            icon=ControllerGlyph(name,layout)
            badge=Gtk.Label(label=glyph);badge.get_style_context().add_class('control-glyph');badge.set_no_show_all(True);badge.hide()
            if name in ('move','scroll'):icon.set_tooltip_text('Stick izquierdo / cruceta' if name=='move' else 'Stick derecho')
            label=Gtk.Label(label=caption);label.get_style_context().add_class('control-caption')
            item.pack_start(icon,False,False,0);item.pack_start(badge,False,False,0);item.pack_start(label,False,False,0)
            if name=='back':self.pack_end(item,False,False,0)
            else:self.pack_start(item,False,False,0)
            self.items[name]=(item,label);self.badges[name]=badge;self.icons[name]=icon
        self.set_layout(layout)
        self.show_all()
    def set_layout(self,layout='ps'):
        self.layout=layout if layout in LAYOUTS else 'ps'
        glyphs=LAYOUTS[self.layout]
        style=self.get_style_context()
        for key in LAYOUTS:style.remove_class('layout-'+key)
        style.add_class('layout-'+self.layout)
        for name,badge in self.badges.items():
            if name in glyphs:badge.set_text(glyphs[name])
        for icon in self.icons.values():icon.set_layout(self.layout)
    def update(self,activate='Seleccionar',back='Volver',width=1280,home=False):
        state=(activate,back,width>=1100,width>=920,width>=1200,home,self.layout)
        if state==self._state:return
        self._state=state
        self.items['activate'][1].set_text(activate);self.items['back'][1].set_text(back)
        if not self.compact:
            self.items['search'][0].set_visible(width>=840)
            self.items['tabs'][0].set_visible(width>=920)
            self.items['options'][0].set_visible(width>=840)
            self.items['options'][1].set_text('Favorito' if home else 'Opciones')
