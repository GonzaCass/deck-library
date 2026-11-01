"""Native console artwork: a quiet backdrop, with no network or animation loop."""
from gi.repository import Gtk,Gdk,GdkPixbuf,GLib
from . import ui_theme


class ConsoleBackdrop(Gtk.DrawingArea):
    def __init__(self):
        super().__init__();self.pixbuf=None;self.path=None;self.tint=None;self.platform=''
        self.connect('draw',self.paint)

    def set_cover(self,path,platform=None):
        if platform is not None:self.platform=platform
        palettes={'Switch':(.11,.42,.38),'WiiCompiled':(.09,.46,.45),'Wii':(.09,.46,.45),'PlayStation 2':(.20,.29,.52),'PS2':(.20,.29,.52),'PlayStation':(.24,.27,.50),'Xbox 360':(.14,.40,.25),'Minecraft':(.18,.40,.25),'Linux':(.22,.33,.52),'Windows':(.24,.32,.46)}
        tint=palettes.get(self.platform)
        if path==self.path and tint==self.tint:return
        self.path=path;self.tint=tint;self.pixbuf=None
        if path:
            try:self.pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(path,1280,800,True)
            except (OSError,GLib.Error):pass
        self.queue_draw()

    def paint(self,widget,cr):
        import cairo,math
        w,h=widget.get_allocated_width(),widget.get_allocated_height()
        light=ui_theme.ACTIVE=='light';base=self.tint if self.tint and not light else ui_theme.drawn('console')
        cr.set_source_rgb(*ui_theme.drawn('canvas'));cr.paint()
        glow=cairo.RadialGradient(w*.74,h*.28,0,w*.74,h*.28,w*.78)
        glow.add_color_stop_rgba(0,*base,.82 if not light else .72);glow.add_color_stop_rgba(.55,*base,.28);glow.add_color_stop_rgba(1,*base,0)
        cr.set_source(glow);cr.paint()
        if self.pixbuf:
            cr.save();cr.rectangle(w*.32,0,w*.68,h);cr.clip()
            scale=max(w*.68/self.pixbuf.get_width(),h/self.pixbuf.get_height())
            cr.translate(w*.68-self.pixbuf.get_width()*scale/2,(h-self.pixbuf.get_height()*scale)/2)
            cr.scale(scale,scale);Gdk.cairo_set_source_pixbuf(cr,self.pixbuf,0,0);cr.paint_with_alpha(.32 if light else .52);cr.restore()
        else:
            aura=cairo.RadialGradient(w*.78,h*.42,10,w*.78,h*.42,h*.95)
            aura.add_color_stop_rgba(0,1,1,1,.06 if not light else .22);aura.add_color_stop_rgba(1,1,1,1,0)
            cr.set_source(aura);cr.paint()
            cr.save();cr.set_source_rgba(1,1,1,.035 if not light else .14);cr.set_line_width(1.5)
            for radius in (.28,.44,.62):
                cr.arc(w*.78,h*.46,h*radius,0,math.tau);cr.stroke()
            cr.restore()
        canvas=ui_theme.drawn('canvas');scrim=cairo.LinearGradient(0,0,w,0)
        scrim.add_color_stop_rgba(0,*canvas,1);scrim.add_color_stop_rgba(.42,*canvas,.92);scrim.add_color_stop_rgba(1,*canvas,0)
        cr.set_source(scrim);cr.paint()
        fade=cairo.LinearGradient(0,h*.58,0,h);fade.add_color_stop_rgba(0,*canvas,0);fade.add_color_stop_rgba(1,*canvas,1)
        cr.set_source(fade);cr.paint();return False
