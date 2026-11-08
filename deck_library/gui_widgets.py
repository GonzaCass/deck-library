"""Small widgets shared by every page: labels, buttons, the page stack, Steam banners and cover posters."""
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GLib,Pango,GdkPixbuf
from . import motion

TONES={'play':'play','danger':'danger','presets':'violet','steam':'steam','controls':'amber'}

def label(text,style=None):
    widget=Gtk.Label(label=text,xalign=0);widget.set_line_wrap(True);widget.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    if style:widget.get_style_context().add_class(style)
    return widget

def wrap_row():
    return WrapRow()

class WrapRow(Gtk.FlowBox):
    def __init__(self):
        super().__init__();self.set_selection_mode(Gtk.SelectionMode.NONE);self.set_min_children_per_line(1);self.set_max_children_per_line(4);self.set_column_spacing(8);self.set_row_spacing(8)
    def pack_start(self,child,*args):self.add(child)
    def pack_end(self,child,*args):self.add(child)

def button(text,callback,primary=False,tone=None):
    widget=Gtk.Button(label=text);widget.connect('clicked',callback)
    style=widget.get_style_context()
    if primary:style.add_class('primary')
    if tone in TONES:style.add_class(TONES[tone])
    return widget

class PageStack(Gtk.Stack):
    """Fade allocated pages without snapshotting a changing GTK layout."""
    def set_visible_child_name(self,name):
        current=self.get_visible_child_name()
        child=self.get_child_by_name(name)
        if child is not None:child.show()
        self.set_transition_type(Gtk.StackTransitionType.NONE);self.set_transition_duration(0)
        super().set_visible_child_name(name)
        GLib.idle_add(self.allocate_visible_page)
        if current!=name and child is not None:motion.enter_page(child)

    def allocate_visible_page(self):
        child=self.get_visible_child()
        if child is None or not self.get_mapped():return False
        window=self.get_toplevel()
        window.queue_resize();window.check_resize()
        return False

class Banner(Gtk.DrawingArea):
    """Steam's own background (and logo) for a shortcut, cropped to the page width with a fade into the page colour."""
    def __init__(self,hero,logo=None,height=210):
        super().__init__();self.set_size_request(-1,height);self.hero=self.logo=None
        try:self.hero=GdkPixbuf.Pixbuf.new_from_file_at_scale(hero,1600,-1,True)
        except (GLib.Error,OSError):pass
        if logo:
            try:self.logo=GdkPixbuf.Pixbuf.new_from_file_at_scale(logo,-1,96,True)
            except (GLib.Error,OSError):pass
        self.connect('draw',self.draw_banner)
    def draw_banner(self,widget,cr):
        import cairo
        w=widget.get_allocated_width();h=widget.get_allocated_height();cr.set_source_rgb(0.075,0.071,0.063);cr.paint()
        if self.hero:
            scale=max(w/self.hero.get_width(),h/self.hero.get_height());cr.save();cr.rectangle(0,0,w,h);cr.clip()
            cr.translate((w-self.hero.get_width()*scale)/2,(h-self.hero.get_height()*scale)/2);cr.scale(scale,scale);Gdk.cairo_set_source_pixbuf(cr,self.hero,0,0);cr.paint();cr.restore()
        shade=cairo.LinearGradient(0,h*0.35,0,h);shade.add_color_stop_rgba(0,0.075,0.071,0.063,0);shade.add_color_stop_rgba(1,0.075,0.071,0.063,1);cr.set_source(shade);cr.rectangle(0,0,w,h);cr.fill()
        if self.logo:
            scale=min(1,(w*0.4)/self.logo.get_width());cr.save();cr.translate(24,h-24-self.logo.get_height()*scale);cr.scale(scale,scale);Gdk.cairo_set_source_pixbuf(cr,self.logo,0,0);cr.paint();cr.restore()
        return False

class Poster(Gtk.DrawingArea):
    """Fixed 2:3 canvas; fill the cover without side bands."""
    def __init__(self,entry,path,width=160,height=240,overlay=False,steam=False,favorite=False):
        super().__init__();self.entry=entry;self.overlay=overlay;self.steam=steam;self.favorite=favorite;self.set_size_request(width,height);self.pixbuf=None
        if path:
            try:self.pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(path,600,900,True)
            except (GLib.Error,OSError):pass
        self.connect('draw',self.draw_poster)
    def set_path(self,path):
        """Show a cover that arrived after the widget was built."""
        try:self.pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(path,600,900,True) if path else None
        except (GLib.Error,OSError):self.pixbuf=None
        self.queue_draw()
    def draw_poster(self,widget,cr):
        import cairo,math
        w=widget.get_allocated_width();h=widget.get_allocated_height()
        radius=8;cr.new_path()
        for x,y,a,b in [(w-radius,radius,-1.5708,0),(w-radius,h-radius,0,1.5708),(radius,h-radius,1.5708,3.1416),(radius,radius,3.1416,4.7124)]:cr.arc(x,y,radius,a,b)
        cr.close_path();cr.clip()
        palettes={'Switch':(.11,.46,.41),'Switch 2':(.13,.40,.50),'WiiCompiled':(.09,.52,.50),'Wii':(.09,.52,.50),'PlayStation 2':(.20,.31,.58),'PS2':(.20,.31,.58),'PlayStation':(.24,.28,.54),'Xbox 360':(.14,.45,.26),'Minecraft':(.20,.45,.27),'Linux':(.24,.35,.56),'Windows':(.26,.34,.48)}
        color=palettes.get(self.entry.platform,(.26,.31,.49));cr.set_source_rgb(*color);cr.paint()
        if self.pixbuf:
            pw=self.pixbuf.get_width();ph=self.pixbuf.get_height();scale=max(w/pw,h/ph);cr.save();cr.rectangle(0,0,w,h);cr.clip();cr.translate((w-pw*scale)/2,(h-ph*scale)/2);cr.scale(scale,scale);Gdk.cairo_set_source_pixbuf(cr,self.pixbuf,0,0);cr.get_source().set_extend(cairo.EXTEND_PAD);cr.paint();cr.restore()
        else:
            from gi.repository import PangoCairo
            from .port_patterns import entry_display_title
            shown_name=entry_display_title(self.entry)
            bg=cairo.LinearGradient(0,0,0,h)
            bg.add_color_stop_rgb(0,min(1,color[0]*1.18),min(1,color[1]*1.18),min(1,color[2]*1.18))
            bg.add_color_stop_rgb(1,color[0]*.36,color[1]*.36,color[2]*.42)
            cr.set_source(bg);cr.paint()
            glow=cairo.RadialGradient(w*.78,h*.18,2,w*.78,h*.18,max(w,h)*.75)
            glow.add_color_stop_rgba(0,1,1,1,.14);glow.add_color_stop_rgba(1,1,1,1,0)
            cr.set_source(glow);cr.paint()
            if w<100:
                layout=self.create_pango_layout(shown_name.strip()[:1].upper() or '?');layout.set_font_description(Pango.FontDescription('Sans Bold '+str(max(10,int(w/2.4)))));tw,th=layout.get_pixel_size();cr.set_source_rgb(.95,.97,1);cr.move_to((w-tw)/2,(h-th)/2);PangoCairo.show_layout(cr,layout);return False
            words=[part[0].upper() for part in shown_name.replace(':',' ').split() if part and part[0].isalnum()][:2]
            monogram=''.join(words) or (shown_name.strip()[:1].upper() or '?')
            emblem=self.create_pango_layout(monogram);emblem.set_font_description(Pango.FontDescription('Sans Bold '+str(max(24,int(w*.34)))))
            ew,eh=emblem.get_pixel_size();cr.set_source_rgba(1,1,1,.10);cr.move_to((w-ew)/2,max(18,(h-eh)*.36));PangoCairo.show_layout(cr,emblem)
            if not self.overlay:
                layout=self.create_pango_layout(shown_name);layout.set_width(int((w-28)*Pango.SCALE));layout.set_wrap(Pango.WrapMode.WORD_CHAR);layout.set_ellipsize(Pango.EllipsizeMode.END);layout.set_height(-2);layout.set_alignment(Pango.Alignment.CENTER);layout.set_font_description(Pango.FontDescription('Sans Bold '+str(max(9,min(14,int(w/9.5))))));_,th=layout.get_pixel_size();cr.set_source_rgb(.95,.97,1);cr.move_to(14,h-th-36);PangoCairo.show_layout(cr,layout)
                cr.set_source_rgba(0,0,0,.28);cr.rectangle(0,h-28,w,28);cr.fill();layout=self.create_pango_layout((self.entry.platform or 'Juego').upper());layout.set_font_description(Pango.FontDescription('Sans Bold 8'));tw,_=layout.get_pixel_size();cr.set_source_rgb(.84,.90,.98);cr.move_to((w-tw)/2,h-21);PangoCairo.show_layout(cr,layout)
        if self.overlay:self.draw_overlay(widget,cr,w,h)
        return False
    def draw_overlay(self,widget,cr,w,h):
        """Bottom gradient with the game's name and platform, and a small badge for shortcuts already in Steam."""
        import cairo,re
        from gi.repository import PangoCairo
        from .port_patterns import entry_display_title
        shown_name=entry_display_title(self.entry)
        shade=cairo.LinearGradient(0,0,0,h);shade.add_color_stop_rgba(0,0.02,0.03,0.04,.02);shade.add_color_stop_rgba(.52,0.02,0.03,0.04,.18);shade.add_color_stop_rgba(1,0.02,0.03,0.04,.94);cr.set_source(shade);cr.paint()
        clean_title=re.sub(r'\s*\((?:Europe|USA|Japan|World|[E]n[A-Za-z, ]*|Rev\s*\w+|v\d[\d\.]*|Disc\s*\d+)[^\)]*\)','',shown_name,flags=re.I).strip() or shown_name
        layout=self.create_pango_layout(clean_title);layout.set_font_description(Pango.FontDescription('Sans Bold 9.5'));layout.set_width(int((w-16)*Pango.SCALE));layout.set_wrap(Pango.WrapMode.WORD_CHAR);layout.set_ellipsize(Pango.EllipsizeMode.END);layout.set_height(-3)
        _,th=layout.get_pixel_size();cr.set_source_rgba(1,1,1,.98);cr.move_to(8,h-th-10);PangoCairo.show_layout(cr,layout)
        sub=self.create_pango_layout((self.entry.platform or 'Juego').upper());sub.set_font_description(Pango.FontDescription('Sans Bold 7.5'));tw,th=sub.get_pixel_size()
        px,py,pw,ph,pr=8,8,tw+12,th+5,5
        cr.new_path()
        for x,y,a,b in [(px+pw-pr,py+pr,-1.5708,0),(px+pw-pr,py+ph-pr,0,1.5708),(px+pr,py+ph-pr,1.5708,3.1416),(px+pr,py+pr,3.1416,4.7124)]:cr.arc(x,y,pr,a,b)
        cr.close_path();cr.set_source_rgba(.04,.06,.09,.78);cr.fill()
        cr.set_source_rgba(.92,.95,1,.95);cr.move_to(px+6,py+2.5);PangoCairo.show_layout(cr,sub)
        if self.steam:
            cr.set_source_rgba(0.04,0.05,0.09,.82);cr.arc(w-18,18,10,0,6.2832);cr.fill();cr.set_source_rgba(.68,.82,1,1);cr.set_line_width(2.0);cr.move_to(w-22.5,18);cr.line_to(w-19,21.5);cr.line_to(w-13,14);cr.stroke()
        if self.favorite:
            fx=w-38 if self.steam else w-18
            cr.set_source_rgba(0.04,0.05,0.09,.82);cr.arc(fx,18,10,0,6.2832);cr.fill()
            star=self.create_pango_layout('★');star.set_font_description(Pango.FontDescription('Sans Bold 9'));sw,sh=star.get_pixel_size();cr.set_source_rgba(1,.82,.28,1);cr.move_to(fx-sw/2,18-sh/2);PangoCairo.show_layout(cr,star)
