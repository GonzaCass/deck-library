"""Native console artwork: a quiet backdrop, with no network or animation loop."""
from gi.repository import Gtk,Gdk,GdkPixbuf,GLib
from . import ui_theme


class ConsoleBackdrop(Gtk.DrawingArea):
    def __init__(self):
        super().__init__();self.pixbuf=None;self.path=None
        self.connect('draw',self.paint)

    def set_cover(self,path):
        if path==self.path:return
        self.path=path;self.pixbuf=None
        if path:
            try:self.pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(path,1280,800,True)
            except (OSError,GLib.Error):pass
        self.queue_draw()

    def paint(self,widget,cr):
        import cairo
        w,h=widget.get_allocated_width(),widget.get_allocated_height()
        light=ui_theme.ACTIVE=='light';base=ui_theme.drawn('console')
        cr.set_source_rgb(*ui_theme.drawn('canvas'));cr.paint()
        glow=cairo.RadialGradient(w*.72,h*.25,0,w*.72,h*.25,w*.8)
        glow.add_color_stop_rgba(0,*base,.85);glow.add_color_stop_rgba(1,*base,0)
        cr.set_source(glow);cr.paint()
        if self.pixbuf:
            cr.save();cr.rectangle(w*.35,0,w*.65,h);cr.clip()
            scale=max(w*.65/self.pixbuf.get_width(),h/self.pixbuf.get_height())
            cr.translate(w*.67-self.pixbuf.get_width()*scale/2,(h-self.pixbuf.get_height()*scale)/2)
            cr.scale(scale,scale);Gdk.cairo_set_source_pixbuf(cr,self.pixbuf,0,0);cr.paint_with_alpha(.3 if light else .48);cr.restore()
        else:
            cr.set_source_rgba(1,1,1,.025 if not light else .18)
            for x in range(0,w+int(h),64):
                cr.move_to(x,0);cr.line_to(x+25,0);cr.line_to(x-h*.55+25,h);cr.line_to(x-h*.55,h);cr.close_path()
            cr.fill()
        canvas=ui_theme.drawn('canvas');scrim=cairo.LinearGradient(0,0,w,0)
        scrim.add_color_stop_rgba(0,*canvas,1);scrim.add_color_stop_rgba(.40,*canvas,.93);scrim.add_color_stop_rgba(1,*canvas,0)
        cr.set_source(scrim);cr.paint()
        fade=cairo.LinearGradient(0,h*.55,0,h);fade.add_color_stop_rgba(0,*canvas,0);fade.add_color_stop_rgba(1,*canvas,1)
        cr.set_source(fade);cr.paint();return False
