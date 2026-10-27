"""Deck Library: biblioteca, fichas de juego y asistente inicial."""
import json,os,pathlib,shlex,subprocess,sys,threading
import gi
gi.require_version('Gtk','3.0')
gi.require_version('PangoCairo','1.0')
from gi.repository import Gtk,Gdk,GLib,Pango,GdkPixbuf
from . import motion
from . import __version__
from .models import Store,Entry
from .discovery import scan,available_emulators,nice_name,SYSTEMS
from .runtime import diagnostics,clean_environment
from .service import queue_entries,queue_removals,queue_controllers,restart_steam
from .steam import find_accounts,active_account
from .installations import settings,save_settings,report
from .gui_tools import ToolsMixin
from .gui_library import LibraryToolsMixin
from .gui_community import CommunityMixin
from .gui_updates import UpdatesMixin
from .gui_catalog import CatalogMixin
from .library_view import TYPES,entry_type,visible_entries
from .experience import ExperienceMixin
from .artwork import find_cover

from .ui_theme import CSS,load_fonts
load_fonts()

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
    """Stack that slides between the library and a game's page and cross-fades between the other pages."""
    ORDER={'library':0,'detail':1}
    def set_visible_child_name(self,name):
        current=self.get_visible_child_name();old=self.ORDER.get(current,0);new=self.ORDER.get(name,0)
        if not motion.page_transitions():self.set_transition_type(Gtk.StackTransitionType.NONE);self.set_transition_duration(0)
        else:
            self.set_transition_duration(140)
            self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        super().set_visible_child_name(name)
        if self.get_transition_type()==Gtk.StackTransitionType.NONE:
            GLib.idle_add(self.allocate_visible_page)

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
    def __init__(self,entry,path,width=160,height=240,overlay=False,steam=False):
        super().__init__();self.entry=entry;self.overlay=overlay;self.steam=steam;self.set_size_request(width,height);self.pixbuf=None
        if path:
            try:self.pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(path,600,900,True)
            except (GLib.Error,OSError):pass
        self.connect('draw',self.draw_poster)
    def draw_poster(self,widget,cr):
        import cairo
        w=widget.get_allocated_width();h=widget.get_allocated_height()
        palettes={'Switch':(.20,.14,.24),'WiiCompiled':(.11,.24,.30),'Wii':(.11,.24,.30),'Minecraft':(.14,.24,.18)}
        color=palettes.get(self.entry.platform,(.15,.18,.25));cr.set_source_rgb(*color);cr.paint()
        if self.pixbuf:
            pw=self.pixbuf.get_width();ph=self.pixbuf.get_height();scale=max(w/pw,h/ph);cr.save();cr.rectangle(0,0,w,h);cr.clip();cr.translate((w-pw*scale)/2,(h-ph*scale)/2);cr.scale(scale,scale);Gdk.cairo_set_source_pixbuf(cr,self.pixbuf,0,0);cr.get_source().set_extend(cairo.EXTEND_PAD);cr.paint();cr.restore()
        else:
            from gi.repository import PangoCairo
            cr.set_source_rgba(1,1,1,.06)
            for offset in range(-int(h),int(w),38):cr.move_to(offset,0);cr.line_to(offset+h,h)
            cr.set_line_width(14);cr.stroke()
            layout=self.create_pango_layout(self.entry.name);layout.set_width(int((w-30)*Pango.SCALE));layout.set_wrap(Pango.WrapMode.WORD_CHAR);layout.set_alignment(Pango.Alignment.CENTER);layout.set_font_description(Pango.FontDescription('Sans Bold '+str(max(7,min(19,int(w/8))))));_,th=layout.get_pixel_size();cr.set_source_rgb(.93,.95,.98);cr.move_to(15,(h-th)/2);PangoCairo.show_layout(cr,layout)
            cr.set_source_rgba(0,0,0,.3);cr.rectangle(0,h-30,w,30);cr.fill();layout=self.create_pango_layout(self.entry.platform.upper());layout.set_font_description(Pango.FontDescription('Sans Bold 9'));tw,_=layout.get_pixel_size();cr.set_source_rgb(.8,.86,.95);cr.move_to((w-tw)/2,h-23);PangoCairo.show_layout(cr,layout)
        if self.overlay:self.draw_overlay(widget,cr,w,h)
        return False
    def draw_overlay(self,widget,cr,w,h):
        """Bottom gradient with the game's name and platform, and a small badge for shortcuts already in Steam."""
        import cairo
        from gi.repository import PangoCairo
        shade=cairo.LinearGradient(0,h*0.58,0,h);shade.add_color_stop_rgba(0,0.04,0.05,0.09,0);shade.add_color_stop_rgba(1,0.04,0.05,0.09,0.94);cr.set_source(shade);cr.rectangle(0,h*0.58,w,h*0.42);cr.fill()
        layout=self.create_pango_layout(self.entry.name);layout.set_font_description(Pango.FontDescription('Sans Bold 11'));layout.set_width(int((w-24)*Pango.SCALE));layout.set_ellipsize(Pango.EllipsizeMode.END);layout.set_height(-2)
        cr.set_source_rgba(1,1,1,.97);cr.move_to(12,h-70);PangoCairo.show_layout(cr,layout)
        sub=self.create_pango_layout(self.entry.platform.upper());sub.set_font_description(Pango.FontDescription('Sans Bold 8'));cr.set_source_rgba(.62,.72,1,.95);cr.move_to(12,h-24);PangoCairo.show_layout(cr,sub)
        if self.steam:
            cr.set_source_rgba(0.04,0.05,0.09,.78);cr.arc(w-22,22,13,0,6.2832);cr.fill();cr.set_source_rgba(.62,.72,1,1);cr.set_line_width(2.4);cr.move_to(w-28,22);cr.line_to(w-23,27);cr.line_to(w-15,17);cr.stroke()

from .gui_actions import ActionsMixin
from .gui_shell import ShellMixin
from .gui_game import GameMixin
from .gui_progress import ProgressMixin
from .gui_input import InputMixin
from .gui_editor import EditorMixin

from .gui_originals import OriginalsMixin
from .gui_home import HomeMixin
from .gui_help import HelpMixin

class Window(HelpMixin,HomeMixin,OriginalsMixin,InputMixin,ProgressMixin,GameMixin,ShellMixin,EditorMixin,CommunityMixin,LibraryToolsMixin,ActionsMixin,CatalogMixin,UpdatesMixin,ExperienceMixin,ToolsMixin,Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self,title='Deck Library');self.init_shell()


def run():
    GLib.set_prgname('deck-library');GLib.set_application_name('Deck Library')
    Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',True)
    Gtk.Window.set_default_icon_from_file(str(pathlib.Path(__file__).resolve().parent.parent/'assets/icon.png'))
    provider=Gtk.CssProvider();provider.load_from_data(CSS);Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    from . import i18n
    i18n.setup(settings(Store()))
    window=Window();window.show_all();Gtk.main();i18n.dump_missed()
