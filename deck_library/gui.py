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

CSS=b'''
@define-color bg #161616;
@define-color surface #262626;
@define-color raised #393939;
@define-color text #f4f4f4;
@define-color dim #c6c6c6;
@define-color accent #78a9ff;
@define-color line #393939;
window, dialog { background:@bg; color:@text; font-family:"Noto Sans",Sans; font-size:14px; }
label { color:@text; }
label.muted,label.meta,label.status { color:@dim; }
label.meta,label.status { font-size:12px; }
label.hero,label.welcome-title { font-size:28px; font-weight:700; }
label.title { font-size:16px; font-weight:600; }
label.brand { font-size:17px; font-weight:700; }
label.eyebrow,label.pill { color:@accent; font-size:12px; font-weight:600; }
.app-header { background:@surface; border-bottom:1px solid @line; }
button { background:@raised; color:@text; border:1px solid transparent; border-radius:6px; padding:8px 16px; min-height:28px; background-image:none; box-shadow:none; text-shadow:none; }
button label { color:@text; font-weight:600; }
button:hover { background:#4c4c4c; border-color:#74798e; }
button:active { background:#525252; }
button:focus { outline:2px solid @accent; outline-offset:2px; }
button:disabled { opacity:0.42; }
button.primary { background:#0f62fe; border-color:transparent; }
button.primary label { color:white; font-weight:700; }
button.primary:hover { background:#0353e9; }
button.danger { background:transparent; border-color:#935b68; }
button.danger label { color:#ffb3bd; }
button.flat,button.nav { background:transparent; border-color:transparent; }
button.nav label { color:@dim; }
button.nav.active { background:@raised; }
button.nav.active label { color:@text; }
button.poster { padding:0; border:2px solid transparent; border-radius:6px; background:@surface; }
button.poster:hover,button.poster.selected { border-color:@accent; box-shadow:none; }
button.poster:focus { border-color:#ffffff; outline:0; box-shadow:none; }
.library-game { border:1px solid transparent; border-radius:6px; padding:4px; transition:background 120ms ease-out,border-color 120ms ease-out; }
.library-game.game-focused { background:#24344d; border-color:#78a9ff; }
.library-game.game-focused .cover-title { color:#d0e2ff; }
list row:focus,list row.game-focused { background:#24344d; border:2px solid #78a9ff; outline:0; }
.cover-title { font-size:14px; font-weight:600; }
entry,combobox button { background:@surface; color:@text; border:0; border-bottom:1px solid #8d8d8d; border-radius:6px; padding:8px 12px; min-height:32px; }
entry:focus { border-color:@accent; }
.card,.selection-bar,.preset-detail { background:@surface; border:0; border-radius:6px; padding:16px; }
.settings-row { padding:14px 4px; border-bottom:1px solid @line; }
.banner { background:#262626; border:0; border-left:3px solid #4589ff; border-radius:6px; padding:9px 14px; }
button.nav label.badge,button.nav.active label.badge { background:#0f62fe; color:#ffffff; border-radius:4px; padding:2px 6px; min-width:14px; min-height:16px; font-size:12px; font-weight:700; }
list,viewport,scrolledwindow { background:transparent; }
list row { padding:6px; border-radius:6px; border:1px solid transparent; }
list row:hover { background:@surface; }
list row:selected { background:#24344d; border-color:#4589ff; }
check { min-width:20px; min-height:20px; border:1px solid #70849e; border-radius:6px; background:@surface; }
check:checked { background:@accent; color:#10233e; }
switch { background:@line; border-radius:6px; }
switch:checked { background:@accent; }
scrollbar { background:transparent; min-width:12px; min-height:12px; }
scrollbar slider { background:#6f6f6f; border:3px solid @bg; border-radius:6px; }
scrollbar.vertical slider { min-width:7px; min-height:36px; }
scrollbar.horizontal slider { min-width:36px; min-height:7px; }
textview text { background:@bg; color:@text; }
progressbar trough { background:@raised; min-height:5px; border-radius:6px; }
progressbar progress { background:@accent; }
.toast { background:@raised; border:0; border-left:3px solid #4589ff; border-radius:6px; padding:12px 20px; }
label.toast-text { color:@text; font-size:16px; font-weight:600; }
.toast.error { border-left-color:#ff8389; }
button,entry { transition:background 160ms ease-out,border-color 160ms ease-out,box-shadow 160ms ease-out; }
.app-header { background:@bg; padding:0 6px; border-bottom:1px solid #393939; }
button.nav { border-radius:6px; padding:6px 12px; }
button.nav.active { background:#262626; border-bottom:2px solid #4589ff; border-radius:0; }
button.nav.active label,button.nav.active image { color:#f4f4f4; }
label.rating { color:#f1d18e; font-size:13px; }
label.game-title { font-size:29px; font-weight:800; letter-spacing:-0.5px; }
.compact label.game-title { font-size:20px; }
label.section-title { font-size:19px; font-weight:700; }
label.rail-heading { font-size:12px; color:@dim; font-weight:600; }
label.platform-chip { font-size:11px; font-weight:700; color:#c6c6c6; background:#393939; border-radius:6px; padding:3px 9px; }
button.hero-cover { padding:0; border-radius:6px; border:2px solid transparent; box-shadow:none; }
button.hero-cover:hover { border-color:@accent; box-shadow:none; }
button.action { min-height:28px; padding:8px 14px; }
button.quiet,button.game-menu { background:transparent; border-color:transparent; }
button.quiet:hover,button.game-menu:hover { background:@raised; border-color:@line; }
button.game-menu { min-height:22px; padding:4px 8px; }
button.breadcrumb { padding:2px 4px; min-height:24px; }
button.breadcrumb label { color:@dim; font-size:13px; }
button.play { color:#10251c; background:#7de1b1; border-color:#7de1b1; }
button.play label { color:#10251c; font-weight:800; }
button.play:hover { background:#a4efcd; border-color:#c3ffe3; box-shadow:none; }
button.play:active { background:#5ccf98; }
button.steam { color:white; background:#316de0; border-color:transparent; }
button.steam label { color:white; }
button.steam:hover { background:#4480f2; border-color:#83abff; }
button.steam-outline { color:#9cc5ff; background:#1b2b42; border-color:transparent; }
button.steam-outline label { color:#b0d1ff; }
button.steam-outline:hover { background:#243b5d; border-color:#729bd0; }
button.violet { color:#211737; background:#78a9ff; border-color:transparent; }
button.violet label { color:#211737; font-weight:700; }
button.violet:hover { background:#d0c5ff; border-color:#e5ddff; box-shadow:none; }
button.violet-outline { color:#c4b5ff; background:#2a243b; border-color:transparent; }
button.violet-outline label { color:#d1c5ff; }
button.violet-outline:hover { background:#39304c; border-color:#8b79b6; }
button.amber { color:#ffd49e; background:#3b2e22; border-color:transparent; }
button.amber label { color:#ffd49e; }
button.amber:hover { background:#4a3826; border-color:#ad8150; }
button.cyan { color:#8dd9e6; background:#1c3036; border-color:transparent; }
button.cyan label { color:#a0e0eb; }
button.cyan:hover { background:#25414a; border-color:#609ba6; }
button.profile-card { background:#262626; border:1px solid transparent; border-radius:6px; padding:15px; }
button.profile-card:hover { background:#333333; border-color:#4589ff; box-shadow:none; }
button.profile-card.chosen { background:#24344d; border-color:#78a9ff; box-shadow:none; }
button.profile-card:active { background:#334966; }
button.profile-card label { font-weight:400; }
button.profile-card label.profile-title { color:@text; font-size:17px; font-weight:700; }
button.profile-card label.muted { color:#c6c6c6; font-size:13px; }
button.profile-card label.meta { color:#c6c6c6; font-size:11px; }
button.profile-card label.profile-spec { color:#a6c8ff; font-size:12px; font-weight:600; }
.violet-icon { color:#a6c8ff; }
.profile-feedback { padding:1px 2px; color:#a6c8ff; }
.profile-feedback label { font-size:13px; }
.change-details { background:#262626; border:1px solid transparent; border-radius:6px; }
button.disclosure { padding:6px; min-height:32px; background:transparent; border-color:transparent; }
button.disclosure label { color:#e0d8ff; font-weight:600; font-size:15px; }
button.disclosure:hover { background:#26222f; }
.apply-dock { background:#262626; border:0; border-top:1px solid #525252; border-radius:6px; padding:13px 16px; }
label.dock-title { font-weight:700; font-size:15px; }
button.applied { background:#203d31; color:#a4e9c5; border-color:#365f4c; }
button.applied label { color:#a4e9c5; }
button.applied:disabled { opacity:1; }
button.task { padding:14px 16px; border-radius:6px; }
button.task label.task-title { color:@text; font-size:14px; font-weight:600; }
button.task label.meta { color:@dim; font-size:12px; font-weight:400; }
button.task.amber { background:#25201c; border-color:transparent; }
button.task.amber:hover { background:#352a20; border-color:#94714a; }
button.task.cyan { background:#1b2429; border-color:transparent; }
button.task.cyan:hover { background:#22343c; border-color:#5a8896; }
.surface-panel { padding:20px; background:@surface; border:0; border-radius:6px; }
popover { background:#262626; color:@text; border:1px solid @line; border-radius:6px; }
popover button { padding:8px; }
menu { background:@surface; color:@text; border:1px solid @line; padding:4px; }
menuitem { background:transparent; color:@text; padding:6px 10px; }
menuitem:hover { background:@raised; }
button.catalog-open { background:transparent; border:0; padding:0; box-shadow:none; }
button.catalog-open:hover { background:#333333; }
/* Logical focus stays visible on every control, including coloured actions. */
.controller-focus, button.controller-focus, button.action.controller-focus,
button.action.play.controller-focus, button.task.controller-focus,
button.profile-card.controller-focus, button.poster.controller-focus,
entry.controller-focus, switch.controller-focus, scale.controller-focus {
  outline:3px solid #ffffff; outline-offset:2px;
  box-shadow:inset 0 0 0 1px #4589ff;
}
menuitem:selected, menuitem:selected label { background:#24344d; color:#ffffff; }
label.control-glyph { background:#393939; border:1px solid #6f6f6f; border-radius:6px; padding:3px 7px; color:#ffffff; font-size:12px; font-weight:700; }
label.control-stick { border-radius:14px; min-width:16px; padding:3px 5px; }
label.control-caption { color:#c6c6c6; font-size:12px; }
'''

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

class Window(OriginalsMixin,InputMixin,ProgressMixin,GameMixin,ShellMixin,EditorMixin,CommunityMixin,LibraryToolsMixin,ActionsMixin,CatalogMixin,UpdatesMixin,ExperienceMixin,ToolsMixin,Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self,title='Deck Library');self.init_shell()


def run():
    GLib.set_prgname('deck-library');GLib.set_application_name('Deck Library')
    Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',True)
    Gtk.Window.set_default_icon_from_file(str(pathlib.Path(__file__).resolve().parent.parent/'assets/icon.png'))
    provider=Gtk.CssProvider();provider.load_from_data(CSS);Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    window=Window();window.show_all();Gtk.main()
