"""Small native components shared by the game workspace; no theme icon dependency."""
import math
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango
from . import motion


def styled(widget, *classes):
    for name in classes:
        widget.get_style_context().add_class(name)
    return widget


def text(value, style=None, limit=None):
    widget = Gtk.Label(label=value, xalign=0)
    widget.set_line_wrap(True)
    widget.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    if style:
        styled(widget, style)
    if limit:
        widget.set_max_width_chars(limit)
    return widget


class Icon(Gtk.DrawingArea):
    """Own line icons, drawn at the current text colour. Hover motion has a finite lifetime."""
    def __init__(self, name, size=20):
        super().__init__()
        self.name = name
        self.size = size
        self.progress = 0
        self.target = 0
        self.tick = None
        self.set_size_request(size, size)
        self.set_valign(Gtk.Align.CENTER)
        self.connect('draw', self.draw_icon)

    def hover(self, active):
        self.target = 1 if active else 0
        if not motion.enabled():
            self.progress = 0
            self.queue_draw()
            return
        if self.tick is None:
            def animate(widget, clock):
                delta = self.target - self.progress
                self.progress += delta * .24
                self.queue_draw()
                if abs(delta) < .01:
                    self.progress = self.target
                    self.tick = None
                    return False
                return True
            self.tick = self.add_tick_callback(animate)

    def draw_icon(self, widget, cr):
        width, height = self.get_allocated_width(), self.get_allocated_height()
        cr.translate((width-self.size)/2, (height-self.size)/2)
        cr.scale(self.size/24, self.size/24)
        color = self.get_style_context().get_color(self.get_state_flags())
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        cr.set_line_width(1.7)
        cr.set_line_cap(1)
        cr.set_line_join(1)
        name = self.name
        def line(*points):
            cr.move_to(*points[0])
            for point in points[1:]:
                cr.line_to(*point)
            cr.stroke()
        def circle(x,y,r):
            cr.arc(x,y,r,0,math.tau);cr.stroke()
        if name == 'play':
            cr.translate(self.progress*1.5, 0)
            cr.move_to(7,4);cr.line_to(20,12);cr.line_to(7,20);cr.close_path();cr.fill()
        elif name == 'check':
            circle(12,12,9);line((7,12),(10.5,15.5),(17,8.5))
        elif name == 'radio':
            circle(12,12,8)
        elif name == 'back':
            cr.translate(-self.progress*2,0);line((14,5),(7,12),(14,19));line((7,12),(21,12))
        elif name == 'chevron':
            cr.translate(self.progress*2,0);line((9,5),(16,12),(9,19))
        elif name == 'down':
            line((6,9),(12,15),(18,9))
        elif name == 'steam':
            circle(16,7,5);circle(16,7,2.4);circle(7,17,3);line((1,14),(7,17),(12.5,10.5));line((9.5,19),(19,11))
        elif name == 'controller':
            cr.move_to(6,6);cr.curve_to(0,6,-1,21,5,19);cr.line_to(9,16);cr.line_to(15,16);cr.line_to(19,19);cr.curve_to(25,21,24,6,18,6);cr.close_path();cr.stroke()
            line((5,11),(10,11));line((7.5,8.5),(7.5,13.5));circle(17,10,0.8);circle(19,13,0.8)
        elif name == 'sliders':
            for y,x in [(5,8),(12,16),(19,8)]:
                line((3,y),(x-3,y));line((x+3,y),(21,y));circle(x,y,2.8)
        elif name == 'monitor':
            cr.rectangle(3,4,18,13);cr.stroke();line((12,17),(12,21));line((7,21),(17,21))
        elif name == 'shield':
            line((12,2),(21,6),(20,14),(17,19),(12,22),(7,19),(4,14),(3,6),(12,2));line((8,11),(11,14),(16,8))
        elif name == 'speed':
            cr.arc(12,13,9,math.pi,math.tau);cr.stroke();line((3,13),(3,18),(21,18),(21,13));line((12,14),(16+self.progress,7));circle(12,14,1.4)
        elif name == 'image':
            cr.rectangle(3,3,18,18);cr.stroke();circle(8,8,2);line((3,18),(10,11),(15,16),(18,13),(21,16))
        elif name == 'folder':
            line((2,7),(2,20),(22,20),(22,6),(11,6),(9,3),(2,3),(2,7),(22,7))
        elif name == 'community':
            circle(9,7,3);cr.arc(8,20,6,math.pi,math.tau);cr.stroke();cr.arc(17,7,3,-1.6,1.6);cr.stroke();cr.arc(17,20,5,-1.6,0);cr.stroke()
        elif name in ('download','upload'):
            if name == 'upload':cr.translate(0,24);cr.scale(1,-1)
            line((12,3),(12,16));line((7,11),(12,16),(17,11));line((3,17),(3,21),(21,21),(21,17))
        elif name == 'undo':
            line((8,4),(3,9),(8,14));line((3,9),(14,9));cr.arc(14,14,5,-math.pi/2,math.pi/2);cr.stroke();line((14,19),(10,19))
        elif name == 'more':
            for x in (5,12,19):cr.arc(x,12,1.6,0,math.tau);cr.fill()
        elif name == 'library':
            for x,h in [(3,16),(10,19),(17,14)]:cr.rectangle(x,22-h,4,h);cr.stroke()
        elif name == 'plus':
            line((4,12),(20,12));line((12,4),(12,20))
        elif name == 'refresh':
            cr.arc(12,12,8,-math.pi/2,math.pi);cr.stroke();line((4,5),(4,12),(11,12))
        elif name == 'search':
            circle(10,10,6);line((15,15),(21,21))
        elif name == 'file':
            line((5,2),(14,2),(20,8),(20,22),(5,22),(5,2));line((14,2),(14,8),(20,8));line((8,13),(16,13));line((8,17),(14,17))
        else:
            circle(12,12,9);line((12,7),(12,13));circle(12,17,.6)
        return False


class ActionButton(Gtk.Button):
    def __init__(self, caption, icon, callback=None, tone='quiet'):
        super().__init__()
        styled(self, 'action', tone)
        self.set_halign(Gtk.Align.START)
        self.body = Gtk.Box(spacing=8)
        self.body.set_halign(Gtk.Align.CENTER)
        self.icon = Icon(icon)
        self.caption = text(caption)
        self.body.pack_start(self.icon, False, False, 0)
        self.body.pack_start(self.caption, False, False, 0)
        self.add(self.body)
        self.get_accessible().set_name(caption)
        self.connect('enter-notify-event', lambda *_: self.icon.hover(True))
        self.connect('leave-notify-event', lambda *_: self.icon.hover(False))
        self.connect('focus-in-event', lambda *_: self.icon.hover(True))
        self.connect('focus-out-event', lambda *_: self.icon.hover(False))
        if callback:
            self.connect('clicked', callback)

    def get_label(self):
        return self.caption.get_text()

    def set_label(self, value):
        self.caption.set_text(value)
        self.get_accessible().set_name(value)

    def set_icon(self, name):
        self.icon.name = name
        self.icon.queue_draw()


class TaskButton(Gtk.Button):
    def __init__(self, title, subtitle, icon, callback, tone='violet'):
        super().__init__()
        styled(self, 'task', tone)
        box = Gtk.Box(spacing=12)
        self.icon = styled(Icon(icon,26), 'task-icon')
        box.pack_start(self.icon,False,False,0)
        words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        words.pack_start(text(title,'task-title'),False,False,0)
        words.pack_start(text(subtitle,'meta',24),False,False,0)
        box.pack_start(words,True,True,0)
        box.pack_end(styled(Icon('chevron',16),'muted'),False,False,0)
        self.add(box)
        self.get_accessible().set_name(title+' · '+subtitle)
        self.connect('clicked',callback)
        self.connect('enter-notify-event',lambda *_:self.icon.hover(True))
        self.connect('leave-notify-event',lambda *_:self.icon.hover(False))


class Reveal(Gtk.Box):
    """A labelled disclosure that can be focused and used with keyboard or Steam Input."""
    def __init__(self, caption, child):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.control = ActionButton(caption,'chevron')
        styled(self.control,'disclosure')
        self.control.body.set_halign(Gtk.Align.START)
        self.revealer = Gtk.Revealer()
        self.revealer.add(child)
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.pack_start(self.control,False,False,0)
        self.pack_start(self.revealer,False,False,0)
        def toggle(_):
            opening = not self.revealer.get_reveal_child()
            self.revealer.set_transition_duration(220 if motion.enabled() else 0)
            self.revealer.set_reveal_child(opening)
            self.control.set_icon('down' if opening else 'chevron')
            self.control.get_accessible().set_description('Expandido' if opening else 'Contraído')
        self.control.connect('clicked',toggle)


class GameBackdrop(Gtk.DrawingArea):
    """Flat workspace surface, independent of the cover artwork."""
    def __init__(self, path):
        super().__init__()
        self.connect('draw',self.draw_backdrop)

    def draw_backdrop(self,widget,cr):
        # Keep the workspace on the same flat charcoal surface as its controls.
        w,h=widget.get_allocated_width(),widget.get_allocated_height();radius=6
        cr.save();cr.new_path()
        for x,y,a,b in [(w-radius,radius,-math.pi/2,0),(w-radius,h-radius,0,math.pi/2),(radius,h-radius,math.pi/2,math.pi),(radius,radius,math.pi,math.pi*1.5)]:cr.arc(x,y,radius,a,b)
        cr.close_path();cr.clip();cr.set_source_rgb(0.149,0.149,0.149);cr.paint();cr.restore()
        return False
