"""Small native components shared by the game workspace; no theme icon dependency."""
import math
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango, Atk
from . import motion

class PortImage(Gtk.Image):
    """Vertical 2:3 box-art canvas for port cards; keeps square/landscape icons uncropped over a soft backdrop."""
    def __init__(self):
        super().__init__();self.set_from_icon_name('applications-games-symbolic',Gtk.IconSize.DIALOG)
    def do_get_preferred_width(self):return (156,174)
    def do_get_preferred_height(self):return (252,252)
    def do_draw(self,cr):
        width,height=self.get_allocated_width(),self.get_allocated_height();radius=8;cr.save();cr.new_path()
        for x,y,a,b in [(width-radius,radius,-math.pi/2,0),(width-radius,height-radius,0,math.pi/2),(radius,height-radius,math.pi/2,math.pi),(radius,radius,math.pi,math.pi*1.5)]:cr.arc(x,y,radius,a,b)
        cr.close_path();cr.clip()
        from . import ui_theme
        cr.set_source_rgb(*ui_theme.drawn('image'));cr.paint()
        pix=self.get_pixbuf() if self.get_storage_type()==Gtk.ImageType.PIXBUF else None
        if pix:
            pw,ph=pix.get_width(),pix.get_height()
            if ph>=pw*1.12:
                scale=max(width/pw,height/ph);cr.save();cr.translate((width-pw*scale)/2,(height-ph*scale)/2);cr.scale(scale,scale);Gdk.cairo_set_source_pixbuf(cr,pix,0,0);cr.paint();cr.restore()
            else:
                bg=max(width/pw,height/ph);cr.save();cr.translate((width-pw*bg)/2,(height-ph*bg)/2);cr.scale(bg,bg);Gdk.cairo_set_source_pixbuf(cr,pix,0,0);cr.paint();cr.restore()
                cr.set_source_rgba(0.05,0.06,0.08,0.74);cr.paint()
                fg=min((width-14)/pw,(height-14)/ph);cr.save();cr.translate((width-pw*fg)/2,(height-ph*fg)/2);cr.scale(fg,fg);Gdk.cairo_set_source_pixbuf(cr,pix,0,0);cr.paint();cr.restore()
        else:Gtk.Image.do_draw(self,cr)
        cr.restore();return False


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


def badge(value, tone='neutral', limit=32):
    widget=styled(text(value),'tag','tag-'+tone)
    widget.set_line_wrap(False);widget.set_ellipsize(Pango.EllipsizeMode.END)
    widget.set_max_width_chars(limit);widget.set_halign(Gtk.Align.START);widget.set_valign(Gtk.Align.CENTER)
    widget.set_tooltip_text(value)
    return widget


def platform_badge(value, icon_name='controller', tone='neutral', limit=16):
    box=styled(Gtk.Box(spacing=4),'plat-tag','plat-tag-'+tone)
    box.set_halign(Gtk.Align.START);box.set_valign(Gtk.Align.CENTER)
    ic=Icon(icon_name,13);lbl=text(value);lbl.set_line_wrap(False);lbl.set_ellipsize(Pango.EllipsizeMode.END);lbl.set_max_width_chars(limit)
    box.pack_start(ic,False,False,0);box.pack_start(lbl,False,False,0);box.set_tooltip_text(value)
    return box


def badge_row(values,per_line=12,compact=False):
    if compact:
        row=styled(Gtk.Box(spacing=6),'game-metadata');row.set_valign(Gtk.Align.CENTER)
        for value,tone in values:row.pack_start(badge(value,tone),False,False,0)
        return row
    row=styled(Gtk.FlowBox(),'tag-row');row.set_selection_mode(Gtk.SelectionMode.NONE);row.set_can_focus(False)
    row.set_min_children_per_line(1);row.set_max_children_per_line(per_line)
    row.set_column_spacing(6);row.set_row_spacing(5)
    row.set_valign(Gtk.Align.CENTER);row.set_homogeneous(False)
    for value,tone in values:
        row.add(badge(value,tone));row.get_children()[-1].set_can_focus(False)
    return row

def metadata_line(values):
    """Short facts read as one line rather than competing status badges."""
    line=text(' · '.join(dict.fromkeys(value for value in values if value)),'metadata-line')
    line.set_line_wrap(False);line.set_width_chars(1);line.set_ellipsize(Pango.EllipsizeMode.END)
    return line

def section_tab(caption,callback):
    control=styled(Gtk.Button(label=caption),'section-tab')
    control.get_accessible().set_role(Atk.Role.PAGE_TAB)
    control.connect('clicked',callback)
    return control

def select_tab(control,active):
    style=control.get_style_context()
    style.add_class('active') if active else style.remove_class('active')
    control.get_accessible().set_description('Sección actual' if active else 'Abrir sección')
    control.get_accessible().notify_state_change(Atk.StateType.SELECTED,active)

class SectionTabs(Gtk.Box):
    """Fixed local navigation with an independent scroll position for each section."""
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=10)
        self.buttons={};self.scrolls={}
        self.bar=styled(Gtk.Box(spacing=12),'subtab-bar');self.bar.get_accessible().set_role(Atk.Role.PAGE_TAB_LIST)
        nav=Gtk.ScrolledWindow();nav.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.NEVER);nav.add(self.bar)
        self.pack_start(nav,False,False,0)
        self.stack=Gtk.Stack();self.stack.set_homogeneous(False);self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.pack_start(self.stack,True,True,0)
    def add_page(self,name,caption,child):
        scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);scroll.set_overlay_scrolling(True);scroll.add(child)
        scroll.show_all();self.stack.add_named(scroll,name);self.scrolls[name]=scroll
        control=section_tab(caption,lambda _:self.select(name));self.buttons[name]=control;self.bar.pack_start(control,False,False,0)
        self.select(self.stack.get_visible_child_name() or name)
    def select(self,name):
        previous=self.stack.get_visible_child_name();self.stack.set_visible_child_name(name)
        for key,control in self.buttons.items():select_tab(control,key==name)
        if previous!=name:motion.enter_page(self.stack.get_visible_child())
    def cycle(self,step):
        names=list(self.buttons);current=self.stack.get_visible_child_name();name=names[(names.index(current)+step)%len(names)]
        self.select(name);self.buttons[name].grab_focus()


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
        elif name == 'grid':
            for x,y in ((3,3),(14,3),(3,14),(14,14)):cr.rectangle(x,y,7,7)
            cr.stroke()
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
        elif name == 'close':
            line((6,6),(18,18));line((18,6),(6,18))
        elif name in ('star','star-fill'):
            for i in range(10):
                radius=10 if i%2==0 else 4.3;angle=-math.pi/2+i*math.pi/5;point=(12+radius*math.cos(angle),12.8+radius*math.sin(angle))
                cr.move_to(*point) if i==0 else cr.line_to(*point)
            cr.close_path()
            if name=='star-fill':cr.fill_preserve()
            cr.stroke()
        elif name == 'plus':
            line((4,12),(20,12));line((12,4),(12,20))
        elif name == 'refresh':
            cr.arc(12,12,8,-math.pi/2,math.pi);cr.stroke();line((4,5),(4,12),(11,12))
        elif name == 'search':
            circle(10,10,6);line((15,15),(21,21))
        elif name == 'file':
            line((5,2),(14,2),(20,8),(20,22),(5,22),(5,2));line((14,2),(14,8),(20,8));line((8,13),(16,13));line((8,17),(14,17))
        elif name == 'logout':
            line((10,4),(4,4),(4,20),(10,20));line((9,12),(21,12));line((16,7),(21,12),(16,17))
        elif name == 'plat-ps':
            line((6.8,3.6),(10.2,9.4),(3.4,9.4),(6.8,3.6));circle(17.2,6.5,2.9)
            cr.rectangle(3.8,14.4,5.8,5.8);cr.stroke();line((14.4,14.4),(20.2,20.2));line((20.2,14.4),(14.4,20.2))
        elif name == 'plat-xbox':
            circle(12,12,9);line((6.6,6.6),(17.4,17.4));line((17.4,6.6),(6.6,17.4))
        elif name == 'plat-switch':
            cr.rectangle(4,3,6.5,18);cr.stroke();cr.rectangle(13.5,3,6.5,18);cr.stroke()
            cr.arc(7.25,8.5,1.5,0,math.tau);cr.fill();cr.arc(16.75,14.5,1.5,0,math.tau);cr.fill()
        elif name == 'plat-nintendo':
            line((9,3),(15,3),(15,9),(21,9),(21,15),(15,15),(15,21),(9,21),(9,15),(3,15),(3,9),(9,9),(9,3))
        elif name == 'plat-pc':
            cr.rectangle(3,4,18,12);cr.stroke();line((12,16),(12,20));line((7,20),(17,20))
        elif name == 'plat-sega':
            circle(12,12,9);circle(12,12,4.5)
        elif name == 'plat-arcade':
            circle(12,6.5,3.2);line((12,9.7),(12,16));cr.rectangle(4,16,16,4.5);cr.stroke()
        elif name == 'disc':
            circle(12,12,9);circle(12,12,2.6);cr.arc(12,12,5.8,-math.pi*.75,-math.pi*.25);cr.stroke()
        else:
            circle(12,12,9);line((12,7),(12,13));circle(12,17,.6)
        return False


class ActionButton(Gtk.Button):
    def __init__(self, caption, icon, callback=None, tone='quiet'):
        super().__init__()
        styled(self, 'action', tone)
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.CENTER)
        self.body = Gtk.Box(spacing=8)
        self.body.set_halign(Gtk.Align.CENTER)
        self.icon = Icon(icon)
        self.caption = text(caption)
        self.caption.set_line_wrap(False)
        self.caption.set_single_line_mode(True)
        if not caption:self.caption.set_no_show_all(True);self.caption.hide()
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
        self.caption.set_no_show_all(not bool(value));self.caption.set_visible(bool(value))
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


class SettingsRow(Gtk.Button):
    """One focus target keeps a setting, its explanation and its action together."""
    def __init__(self,title,description,caption,icon,callback):
        super().__init__();styled(self,'preference-row')
        row=Gtk.Box(spacing=12);row.set_valign(Gtk.Align.CENTER)
        emblem=styled(Gtk.Box(),'preference-icon');emblem.set_valign(Gtk.Align.CENTER)
        emblem.pack_start(Icon(icon,20),False,False,0);row.pack_start(emblem,False,False,0)
        words=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2);words.set_hexpand(True)
        self.title=text(title,'preference-title');self.description=text(description,'meta')
        for widget in (self.title,self.description):widget.set_width_chars(1)
        words.pack_start(self.title,False,False,0);words.pack_start(self.description,False,False,0)
        row.pack_start(words,True,True,0)
        action=text(caption,'preference-action');action.set_valign(Gtk.Align.CENTER);action.set_max_width_chars(18)
        row.pack_start(action,False,False,0);row.pack_end(Icon('chevron',18),False,False,0)
        self.add(row);self.get_accessible().set_name(title);self.get_accessible().set_description(description)
        self.connect('clicked',callback)


class Reveal(Gtk.Box):
    """A labelled disclosure that can be focused and used with keyboard or Steam Input."""
    def __init__(self, caption, child):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=0)
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
    """Carry the home screen's quiet artwork and ambient colour into a game."""
    def __init__(self, path):
        super().__init__()
        from .gui_console import ConsoleBackdrop
        self.backdrop=ConsoleBackdrop();self.backdrop.set_cover(path)
        self.connect('draw',self.draw_backdrop)

    def draw_backdrop(self,widget,cr):
        w,h=widget.get_allocated_width(),widget.get_allocated_height();radius=10
        cr.save();cr.new_path()
        for x,y,a,b in [(w-radius,radius,-math.pi/2,0),(w-radius,h-radius,0,math.pi/2),(radius,h-radius,math.pi/2,math.pi),(radius,radius,math.pi,math.pi*1.5)]:cr.arc(x,y,radius,a,b)
        cr.close_path();cr.clip();self.backdrop.paint(widget,cr);cr.restore()
        return False

def tooltip_when_cut(widget,value):
    """Full-name tooltip only while the text is actually shortened with an ellipsis, so it never pops up over a page for no reason."""
    widget.set_has_tooltip(True)
    def query(label,x,y,keyboard,tip):
        if keyboard or getattr(label.get_toplevel(),'controller_mode',False):return False
        layout=label.get_layout()
        if layout is None or not layout.is_ellipsized():return False
        tip.set_text(value);return True
    widget.tooltip_query=query;widget.connect('query-tooltip',query)
