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
from .gui_updates import UpdatesMixin
from .gui_catalog import CatalogMixin
from .library_view import TYPES,entry_type,visible_entries
from .experience import ExperienceMixin
from .artwork import find_cover

CSS=b'''
@define-color bg #0a0d14;
@define-color surface #111620;
@define-color raised #1a2131;
@define-color line #243049;
@define-color text #eef2fa;
@define-color dim #98a4bb;
@define-color accent #4f9dff;
@define-color accent2 #4f9dff;
@define-color on_accent #0a1226;
@define-color good #5fcf9a;
@define-color bad #ff7b7b;

window, dialog { background:@bg; color:@text; font-family:Sans; font-size:15px; }
label { color:@text; }
label.muted, label.status { color:@dim; }
label.status { font-size:13px; }
label.subtitle { color:@dim; font-size:16px; }
label.hero { font-size:26px; font-weight:800; }
label.welcome-title { font-size:38px; font-weight:800; }
label.title { font-size:17px; font-weight:700; }
label.pill { color:@accent; font-size:12px; font-weight:700; }
label.badge { background:@accent; color:@on_accent; border-radius:10px; padding:0 8px; font-size:12px; font-weight:800; }
button.nav label.badge { color:@on_accent; }
label.sidebar-version { color:@dim; font-size:12px; }
label.good { color:@good; }
dialog viewport, dialog scrolledwindow, dialog list { background:@bg; }

.sidebar { background-image:linear-gradient(180deg,#121826,#0a0d14); border-right:1px solid @line; padding:22px 14px; }
.brand { font-size:18px; font-weight:800; }
button.nav { background:transparent; border:0; border-left:3px solid transparent; border-radius:6px; padding:11px 14px; min-height:44px; box-shadow:none; }
button.nav label { color:@dim; font-weight:700; font-size:15px; }
button.nav image { color:@dim; }
button.nav:hover { background:alpha(@accent,0.08); }
button.nav:hover label, button.nav:hover image { color:@text; }
button.nav.active { background:alpha(@accent,0.15); border-left-color:@accent; }
button.nav.active label, button.nav.active image { color:@text; }
button.nav:focus { outline:2px solid @accent; outline-offset:-2px; }
button.chip { background:@surface; border:1px solid @line; border-radius:6px; padding:5px 18px; min-height:24px; }
button.chip:hover { border-color:@accent; }
button.chip label { color:@dim; font-weight:600; }
button.chip.active { background:@accent; border-color:transparent; }
button.chip.active label { color:@on_accent; }
label.tag { background:@raised; border-radius:4px; padding:2px 11px; font-size:12px; font-weight:600; color:@dim; }
label.tag.accent { background:alpha(@accent,0.18); color:@accent; }
label.tag.warn { background:alpha(#f0a35c,0.18); color:#f0a35c; }
.divider { background:@line; min-height:1px; }
.card { background:@surface; border:1px solid @line; border-radius:10px; padding:18px; }
.preset-detail { background:@surface; padding:16px; border-radius:8px; }
.banner { background:alpha(@accent,0.12); border:1px solid alpha(@accent,0.6); border-radius:8px; padding:10px 14px; }
.selection-bar { background:@raised; border:1px solid @line; padding:10px; border-radius:8px; }

button { background:@raised; color:@text; border:1px solid @line; border-radius:6px; padding:8px 16px; min-height:30px; box-shadow:none; text-shadow:none; background-image:none; }
button label { color:@text; }
button:hover { border-color:@accent; }
button:active { background:@line; }
button:focus { outline:2px solid @accent; outline-offset:2px; }
button:disabled { opacity:0.45; }
button.primary { background:@accent; border-color:transparent; }
button.primary label { color:@on_accent; font-weight:700; }
button.primary:hover { background:#78b4ff; }
button.danger { background:transparent; border-color:@bad; }
button.danger label { color:@bad; }
button.danger:hover { background:alpha(@bad,0.15); }
button.flat { background:transparent; border-color:transparent; }
button.poster { background:@raised; border:2px solid transparent; border-radius:8px; padding:0; }
button.poster:hover, button.poster.selected { border-color:@accent; }
button.poster.selected { box-shadow:0 0 0 3px alpha(@accent,0.35); }

entry, combobox button { background:@surface; color:@text; border:1px solid @line; border-radius:6px; padding:8px; min-height:30px; }
entry:focus { border-color:@accent; }
list, list row { background:transparent; }
list row { border-bottom:1px solid @line; padding:10px 8px; }
list row:selected { background:@raised; }
check { min-width:22px; min-height:22px; border:1px solid @dim; border-radius:6px; background:@raised; }
check:checked { background:@accent; color:@on_accent; border-color:@accent; }
switch { background:@line; border-radius:14px; }
switch:checked { background:@accent; }
progressbar trough { background:@raised; border:0; border-radius:4px; min-height:5px; }
progressbar progress { background:@accent; border:0; border-radius:4px; }
textview text { background:@bg; color:@text; font-family:monospace; font-size:13px; }
.cover-title { font-size:14px; font-weight:700; }

/* Motion: 150-300 ms, ease-out. Hover and focus must be visible for mouse, touch and gamepad (Steam Input sends keys). */
button, entry, .card, .banner { transition:background 180ms ease-out, border-color 180ms ease-out, box-shadow 220ms ease-out, opacity 180ms ease-out; }
button.poster { transition:border-color 200ms ease-out, box-shadow 240ms ease-out; }
button.poster:hover { box-shadow:0 10px 24px alpha(black,0.5); }
button.poster:focus { border-color:@accent; box-shadow:0 0 0 3px alpha(@accent,0.4), 0 10px 24px alpha(black,0.5); outline:none; }
button.tab, button.chip { transition:background 180ms ease-out, border-color 200ms ease-out; }
button.tab:focus, button.chip:focus { outline:2px solid @accent; outline-offset:-3px; }
button { min-height:36px; }
entry { min-height:36px; }
button.chip { min-height:32px; }
switch { transition:background 200ms ease-out; }
.toast { background:@raised; border:1px solid @accent; border-radius:8px; padding:10px 18px; box-shadow:0 8px 24px alpha(black,0.55); }
label.toast-text { color:@text; font-weight:600; }
'''

TONES={'play':'primary','danger':'danger'}

def label(text,style=None):
    widget=Gtk.Label(label=text,xalign=0);widget.set_line_wrap(True);widget.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    if style:widget.get_style_context().add_class(style)
    return widget

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
        if not motion.enabled():self.set_transition_type(Gtk.StackTransitionType.NONE);self.set_transition_duration(0)
        else:
            self.set_transition_duration(260)
            self.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT if new>old else Gtk.StackTransitionType.SLIDE_RIGHT if new<old else Gtk.StackTransitionType.CROSSFADE)
        super().set_visible_child_name(name)

class Poster(Gtk.DrawingArea):
    """Fixed 2:3 canvas; contain artwork without cropping game titles."""
    def __init__(self,entry,path,width=160,height=240,overlay=False,steam=False):
        super().__init__();self.entry=entry;self.overlay=overlay;self.steam=steam;self.set_size_request(width,height);self.pixbuf=None
        if path:
            try:self.pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(path,600,900,True)
            except (GLib.Error,OSError):pass
        self.connect('draw',self.draw_poster)
    def draw_poster(self,widget,cr):
        w=widget.get_allocated_width();h=widget.get_allocated_height()
        palettes={'Switch':(.20,.14,.24),'WiiCompiled':(.11,.24,.30),'Wii':(.11,.24,.30),'Minecraft':(.14,.24,.18)}
        color=palettes.get(self.entry.platform,(.15,.18,.25));cr.set_source_rgb(*color);cr.paint()
        if self.pixbuf:
            pw=self.pixbuf.get_width();ph=self.pixbuf.get_height();scale=min(w/pw,h/ph);cr.save();cr.translate((w-pw*scale)/2,(h-ph*scale)/2);cr.scale(scale,scale);Gdk.cairo_set_source_pixbuf(cr,self.pixbuf,0,0);cr.paint();cr.restore()
        else:
            from gi.repository import PangoCairo
            cr.set_source_rgba(1,1,1,.06)
            for offset in range(-int(h),int(w),38):cr.move_to(offset,0);cr.line_to(offset+h,h)
            cr.set_line_width(14);cr.stroke()
            layout=self.create_pango_layout(self.entry.name);layout.set_width(int((w-30)*Pango.SCALE));layout.set_wrap(Pango.WrapMode.WORD_CHAR);layout.set_alignment(Pango.Alignment.CENTER);layout.set_font_description(Pango.FontDescription('Sans Bold 19'));_,th=layout.get_pixel_size();cr.set_source_rgb(.93,.95,.98);cr.move_to(15,(h-th)/2);PangoCairo.show_layout(cr,layout)
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

class Window(CatalogMixin,UpdatesMixin,ExperienceMixin,ToolsMixin,Gtk.Window):
    def __init__(self):
        super().__init__(title='Deck Library');self.set_wmclass('deck-library','deck-library');self.set_icon_from_file(str(pathlib.Path(__file__).resolve().parent.parent/'assets/icon.svg'));self.set_default_size(1200,740);self.set_size_request(960,620)
        self.store=Store();self.preferences=settings(self.store);self.view=self.preferences.get('view','covers');self.entries=[];self.checked=set();self.selected=None;self.selection_mode=False;self.platform_filter='all';self.type_filter='all';self.artwork_attempted=set();self.artwork_busy=False;self.discover_busy=False;self.wizard_step=0
        self.connect('destroy',Gtk.main_quit)
        layout=Gtk.Box();self.add(layout)
        self.build_sidebar(layout)
        main=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);main.set_border_width(20);overlay=Gtk.Overlay();overlay.add(main);self.toast_widget=motion.Toast();overlay.add_overlay(self.toast_widget);layout.pack_start(overlay,True,True,0)
        self.pages=PageStack();self.pages.set_hexpand(True);self.pages.set_vexpand(True);self.pages.connect('notify::visible-child-name',self.page_changed);main.pack_start(self.pages,True,True,0)
        self.build_library()
        detail_scroll=Gtk.ScrolledWindow();detail_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);self.detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);detail_scroll.add(self.detail);self.pages.add_named(detail_scroll,'detail')
        self.settings_box=self.scrolled_page('settings');self.updates_box=self.scrolled_page('updates');self.catalog_box=self.scrolled_page('catalog')
        self.add_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);self.pages.add_named(self.add_box,'add')
        self.wizard_box=Gtk.Stack();self.wizard_box.set_homogeneous(False);self.pages.add_named(self.wizard_box,'welcome')
        self.artwork_bar=Gtk.Box(spacing=10);self.artwork_bar.set_no_show_all(True);self.artwork_spinner=Gtk.Spinner();self.artwork_label=label('','muted');self.artwork_bar.pack_start(self.artwork_spinner,False,False,0);self.artwork_bar.pack_start(self.artwork_label,True,True,0);main.pack_start(self.artwork_bar,False,False,0)
        self.status=label('','status');main.pack_start(self.status,False,False,0)
        try:self.entries=self.store.load()
        except Exception as error:self.message('No se pudo leer la biblioteca',str(error))
        self.apply_motion();self.refresh_platforms();self.animate_next=True;self.render();self.pages.set_visible_child_name('library')
        if not self.preferences.get('onboarding_complete'):self.start_wizard()
        else:GLib.idle_add(self.discover)
        self.update_state=None
        from . import updates
        self.update_state=updates.cached(self.store);self.refresh_update_badges()
        if self.preferences.get('check_updates',True):GLib.timeout_add_seconds(5,self.check_updates)
        sync_path=self.store.root/'last-sync.json';self.last_sync_seen=sync_path.stat().st_mtime if sync_path.exists() else 0;GLib.timeout_add_seconds(3,self.poll_sync)

    def scrolled_page(self,name):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);box.set_margin_end(8);scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);scroll.add(box);self.pages.add_named(scroll,name);return box

    def card(self,parent,title=None):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);box.get_style_context().add_class('card')
        if title:box.pack_start(label(title,'title'),False,False,0)
        parent.pack_start(box,False,False,0);return box

    def build_sidebar(self,layout):
        side=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);side.set_size_request(262,-1);side.get_style_context().add_class('sidebar');layout.pack_start(side,False,False,0)
        brand=Gtk.Box(spacing=12)
        try:brand.pack_start(Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(pathlib.Path(__file__).resolve().parent.parent/'assets/icon.svg'),40,40,True)),False,False,0)
        except GLib.Error:pass
        brand.pack_start(label('Deck Library','brand'),False,False,0);side.pack_start(brand,False,False,6)
        add=button('Agregar juegos',lambda _:self.add_hub(),True);side.pack_start(add,False,False,10)
        self.nav_buttons={};theme=Gtk.IconTheme.get_default()
        for text,icon,callback in [('Biblioteca',('view-grid-symbolic',),lambda _:self.open_library()),('Catálogo',('folder-download-symbolic','system-software-install-symbolic'),lambda _:self.catalog_page()),('Actualizaciones',('view-refresh-symbolic','software-update-available-symbolic'),lambda _:self.updates_page()),('Ajustes',('emblem-system-symbolic','preferences-system-symbolic'),lambda _:self.settings_page())]:
            widget=Gtk.Button();widget.set_relief(Gtk.ReliefStyle.NONE);widget.connect('clicked',callback);widget.get_style_context().add_class('nav');row=Gtk.Box(spacing=12)
            icon=next((i for i in icon if theme.has_icon(i)),None)
            if icon:row.pack_start(Gtk.Image.new_from_icon_name(icon,Gtk.IconSize.LARGE_TOOLBAR),False,False,0)
            row.pack_start(label(text),True,True,0)
            if text=='Actualizaciones':
                self.update_badge=label('0','badge');self.update_badge.set_no_show_all(True);self.update_badge.set_yalign(0.5);row.pack_end(self.update_badge,False,False,0)
            widget.add(row);side.pack_start(widget,False,False,0);self.nav_buttons[text]=widget
        side.pack_end(label('Versión '+__version__,'sidebar-version'),False,False,4)

    def build_library(self):
        library=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14);self.pages.add_named(library,'library')
        self.update_banner=Gtk.Box(spacing=12);self.update_banner.get_style_context().add_class('banner');self.update_banner.set_no_show_all(True)
        self.banner_text=label('');self.banner_text.set_line_wrap(False);self.banner_text.set_hexpand(True);self.update_banner.pack_start(self.banner_text,True,True,0);self.banner_action=button('Ver',lambda _:self.banner_clicked(),True);self.update_banner.pack_end(self.banner_action,False,False,0);library.pack_start(self.update_banner,False,False,0)
        toolbar=Gtk.Box(spacing=10);self.search=Gtk.SearchEntry();self.search.set_placeholder_text('Buscar juego');self.search.connect('search-changed',lambda _:self.render());toolbar.pack_start(self.search,True,True,0)
        self.view_picker=Gtk.ComboBoxText();self.view_picker.append('covers','Carátulas');self.view_picker.append('list','Lista');self.view_picker.set_active_id(self.view);self.view_picker.connect('changed',self.change_view);toolbar.pack_start(self.view_picker,False,False,0)
        self.select_button=button('Seleccionar',lambda _:self.toggle_selection());toolbar.pack_start(self.select_button,False,False,0);toolbar.pack_start(button('Buscar juegos',lambda _:self.discover()),False,False,0);library.pack_start(toolbar,False,False,0)
        filters=Gtk.Box(spacing=8);library.pack_start(filters,False,False,0);self.chip_buttons={}
        for key,title in [('all','Todos'),*TYPES]:
            chip=Gtk.Button(label=title);chip.get_style_context().add_class('chip');chip.connect('clicked',lambda _,k=key:self.type_changed(k));filters.pack_start(chip,False,False,0);self.chip_buttons[key]=chip
        self.chip_buttons['all'].get_style_context().add_class('active')
        self.platform_picker=Gtk.ComboBoxText();self.platform_picker.append('all','Todas las plataformas');self.platform_picker.set_active_id('all');self.platform_picker.connect('changed',self.filter_changed);filters.pack_start(self.platform_picker,False,False,6)
        self.prefer_ports=Gtk.CheckButton(label='Preferir ports');self.prefer_ports.set_tooltip_text('Oculta la versión por emulador de un juego que ya tiene port.');self.prefer_ports.set_active(self.preferences.get('prefer_ports',True));self.prefer_ports.connect('toggled',self.prefer_changed);filters.pack_start(self.prefer_ports,False,False,0)
        self.library_count=label('','status');self.library_count.set_line_wrap(False);self.library_count.set_ellipsize(3);self.library_count.set_halign(Gtk.Align.END);filters.pack_end(self.library_count,False,False,0)
        self.library_stack=Gtk.Stack();self.library_stack.set_vexpand(True);library.pack_start(self.library_stack,True,True,0)
        scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);self.list=Gtk.ListBox();self.list.connect('row-selected',self.on_select);scroll.add(self.list);self.library_stack.add_named(scroll,'list')
        covers_scroll=Gtk.ScrolledWindow();covers_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);self.covers=Gtk.FlowBox();self.covers.set_selection_mode(Gtk.SelectionMode.NONE);self.covers.set_max_children_per_line(8);self.covers.set_min_children_per_line(1);self.covers.set_column_spacing(16);self.covers.set_row_spacing(20);self.covers.set_homogeneous(True);self.covers.set_valign(Gtk.Align.START);covers_scroll.add(self.covers);self.library_stack.add_named(covers_scroll,'covers')
        self.empty_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16);self.empty_box.set_valign(Gtk.Align.CENTER);self.empty_box.set_halign(Gtk.Align.CENTER);self.empty_box.pack_start(label('Biblioteca vacía','hero'),False,False,0);self.empty_box.pack_start(label('Buscar juegos instalados o agregar uno manualmente.','subtitle'),False,False,0);self.empty_box.pack_start(button('Buscar juegos',lambda _:self.start_wizard(),True),False,False,0);self.library_stack.add_named(self.empty_box,'empty')
        self.selection_bar=Gtk.Box(spacing=10);self.selection_bar.get_style_context().add_class('selection-bar');self.selection_bar.set_no_show_all(True);library.pack_start(self.selection_bar,False,False,0);self.selection_label=label('0 seleccionados','title');self.selection_bar.pack_start(self.selection_label,False,False,0);self.selection_bar.pack_start(button('Todos los visibles',lambda _:self.select_visible()),False,False,0)
        self.account=Gtk.ComboBoxText();self.accounts=find_accounts();active=active_account()
        if active in self.accounts:self.accounts.remove(active);self.accounts.insert(0,active)
        for index,path in enumerate(self.accounts):self.account.append_text('Cuenta actual' if path==active else 'Cuenta Steam '+str(index+1))
        if not self.accounts:self.account.append_text('Steam sin sesión iniciada')
        self.account.set_active(0);self.selection_bar.pack_start(self.account,True,True,0)
        self.remove_button=button('Quitar de Steam',lambda _:self.remove_from_steam(),tone='danger');self.selection_bar.pack_end(self.remove_button,False,False,0)
        self.add_button=button('Agregar a Steam',lambda _:self.add_to_steam(),True);self.selection_bar.pack_end(self.add_button,False,False,0)

    def apply_motion(self):
        enabled=self.preferences.get('animations',True);Gtk.Settings.get_default().set_property('gtk-enable-animations',enabled)
        for stack in (self.library_stack,self.wizard_box):stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE if enabled else Gtk.StackTransitionType.NONE);stack.set_transition_duration(160 if enabled else 0)
    def page_changed(self,stack,*args):
        page=stack.get_visible_child_name();active={'library':'Biblioteca','detail':'Biblioteca','catalog':'Catálogo','updates':'Actualizaciones','settings':'Ajustes'}.get(page)
        for text,widget in self.nav_buttons.items():
            context=widget.get_style_context()
            if text==active:context.add_class('active')
            else:context.remove_class('active')
    def reset_page(self,box):
        for child in box.get_children():box.remove(child)
    def open_library(self):self.animate_next=True;self.pages.set_visible_child_name('library');self.render()
    def toast(self,text):self.toast_widget.show_text(text)
    def add_hub(self):
        self.reset_page(self.add_box);self.add_box.pack_start(label('Agregar juegos','hero'),False,False,0);self.add_box.pack_start(label('Detectar instalaciones, elegir un archivo o preparar un port.','subtitle'),False,False,0)
        for title,text,action in [('Buscar lo instalado','EmuDeck, ports y las instancias de Minecraft.',lambda _:self.start_wizard()),('Catálogo de ports','Recompilaciones y ports de la comunidad, instalados desde GitHub.',lambda _:self.catalog_page()),('Elegir un juego o una app','ROM, programa o launcher.',lambda _:self.manual()),('Mario Kart Wii','Recompilar una imagen PAL y dejarla lista para la Deck.',lambda _:self.setup_wii_dialog()),('Spider-Man: Edge of Time','Project-2099 desde una ISO de Xbox 360, con Proton y ajustes para la Deck.',lambda _:self.project2099_dialog())]:
            card=self.card(self.add_box,title);card.pack_start(label(text,'muted'),False,False,0);row=Gtk.Box();row.pack_start(button('Continuar',action),False,False,0);card.pack_start(row,False,False,0)
        self.add_box.show_all();self.pages.set_visible_child_name('add')
    def poll_sync(self):
        path=self.store.root/'last-sync.json'
        try:
            if path.exists() and path.stat().st_mtime>self.last_sync_seen:
                value=json.loads(path.read_text());self.last_sync_seen=path.stat().st_mtime;self.set_status(self.sync_summary(value));self.toast(self.sync_summary(value));self.discover()
        except (OSError,ValueError):pass
        return True
    def sync_summary(self,value):
        parts=[]
        if value.get('shortcuts'):parts.append(f'{len(value["shortcuts"])} accesos guardados')
        if value.get('removed'):parts.append(f'{len(value["removed"])} accesos quitados')
        if value.get('layouts'):parts.append(f'layout de mando asignado a {len(value["layouts"])}')
        return (', '.join(parts) or 'Cambios guardados').capitalize()+'. Abrir Steam para verlos.'
    def set_status(self,text):self.status.set_text(text)
    def message(self,title,text):
        dialog=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.INFO,buttons=Gtk.ButtonsType.OK,text=title);dialog.format_secondary_text(text);dialog.run();dialog.destroy()
    def confirm(self,title,text,accept='Continuar',danger=False):
        dialog=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.QUESTION,buttons=Gtk.ButtonsType.NONE,text=title);dialog.format_secondary_text(text);dialog.add_button('Cancelar',Gtk.ResponseType.CANCEL)
        action=dialog.add_button(accept,Gtk.ResponseType.OK)
        if danger:action.get_style_context().add_class('danger')
        else:action.get_style_context().add_class('primary')
        response=dialog.run();dialog.destroy();return response==Gtk.ResponseType.OK
    def discover(self):
        if self.discover_busy:return False
        self.discover_busy=True;self.set_status('Buscando juegos e instalaciones…');preferences=dict(self.preferences)
        def work():
            try:
                found=report(preferences=preferences);from .steam_inventory import merge_steam
                from . import ports
                ports.maintain(self.store)
                merged=self.store.merge(scan(preferences=preferences),overwrite=False);entries=merge_steam(merged);self.store.save(entries);GLib.idle_add(self.discovered,entries,found)
            except Exception as error:GLib.idle_add(self.discovery_failed,str(error))
        threading.Thread(target=work,daemon=True).start();return False
    def discovery_failed(self,text):
        self.discover_busy=False;self.set_status('La búsqueda no se completó: '+text)
        if self.pages.get_visible_child_name()=='welcome' and self.wizard_step==1:self.wizard_report_label.set_text('La búsqueda falló. Revisar las rutas y repetirla.');self.wizard_continue.set_sensitive(True)
        return False
    def discovered(self,entries,found=None):
        self.discover_busy=False;self.entries=entries
        if self.selected:self.selected=next((e for e in entries if e.id==self.selected.id),None)
        self.checked&={e.id for e in entries}
        self.refresh_platforms();self.render();self.set_status(f'{len(entries)} juegos encontrados.');self.wizard_detection_ready(found or report(preferences=self.preferences))
        if self.pages.get_visible_child_name()=='detail':
            if self.selected:self.show_detail(self.selected)
            else:self.pages.set_visible_child_name('library')
        if self.pages.get_visible_child_name()!='welcome':self.fetch_covers()
        return False
    def refresh_platforms(self):
        self.platform_picker.handler_block_by_func(self.filter_changed);self.platform_picker.remove_all();self.platform_picker.append('all','Todas las plataformas')
        for platform in sorted({e.platform for e in self.shown_entries()[0]}):self.platform_picker.append(platform,platform)
        self.platform_picker.set_active_id(self.platform_filter)
        if self.platform_picker.get_active_id() is None:self.platform_filter='all';self.platform_picker.set_active_id('all')
        self.platform_picker.handler_unblock_by_func(self.filter_changed)
    def filter_changed(self,picker):self.platform_filter=picker.get_active_id() or 'all';self.animate_next=True;self.render()
    def type_changed(self,key):
        self.type_filter=key;self.animate_next=True
        for name,chip in self.chip_buttons.items():
            style=chip.get_style_context()
            if name==key:style.add_class('active')
            else:style.remove_class('active')
        self.render()
    def prefer_changed(self,check):self.preferences['prefer_ports']=check.get_active();save_settings(self.preferences,self.store);self.render()
    def shown_entries(self):
        """Library entries after the duplicate rule; also returns how many emulator versions were left out."""
        return visible_entries(self.entries,self.preferences.get('prefer_ports',True))
    def visible(self):
        text=self.search.get_text().casefold();entries,_=self.shown_entries()
        return sorted([e for e in entries if text in (e.name+' '+e.platform).casefold() and (self.platform_filter=='all' or e.platform==self.platform_filter) and (self.type_filter=='all' or entry_type(e)==self.type_filter)],key=lambda e:e.name.casefold())
    def in_steam(self,e):return e.metadata.get('steam_appid') is not None and not e.metadata.get('steam_store')
    def render(self):
        self.reset_page(self.list);self.reset_page(self.covers);visible=self.visible();self.new_tiles=[]
        shown,hidden=self.shown_entries();platforms=len({e.platform for e in shown});games=len(shown);self.library_count.set_text(f'{games} {"juego" if games==1 else "juegos"}'+(f' · {hidden} ocultos por tener port' if hidden else ''))
        for entry in visible:
            row=Gtk.ListBoxRow();row.entry=entry;box=Gtk.Box(spacing=14);row.add(box)
            if self.selection_mode:
                check=Gtk.CheckButton();check.set_active(entry.id in self.checked);check.connect('toggled',self.toggle,entry.id);box.pack_start(check,False,False,0)
            texts=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);texts.pack_start(label(entry.name,'title'),False,False,0);texts.pack_start(label(entry.platform+(' · En Steam' if self.in_steam(entry) else ''),'muted'),False,False,0);box.pack_start(texts,True,True,0);self.list.add(row);self.add_cover_card(entry)
        if not visible and self.entries:
            self.covers.add(label('Ningún juego coincide con el filtro.','muted'));self.list.add(label('Sin resultados.','muted'))
        self.library_stack.set_visible_child_name(self.view if self.entries else 'empty');self.library_stack.show_all();self.update_selection()
        if getattr(self,'animate_next',False):self.animate_next=False;motion.stagger(self.new_tiles)
    def change_view(self,picker):self.view=picker.get_active_id() or 'covers';self.animate_next=True;self.preferences['view']=self.view;save_settings(self.preferences,self.store);self.render()
    def toggle_selection(self):
        self.selection_mode=not self.selection_mode
        if not self.selection_mode:self.checked.clear()
        self.render()
    def update_selection(self):
        self.select_button.set_label('Terminar selección' if self.selection_mode else 'Seleccionar');self.selection_label.set_text(f'{len(self.checked)} seleccionados');self.add_button.set_sensitive(bool(self.checked) and bool(self.accounts))
        self.remove_button.set_sensitive(any(self.in_steam(e) for e in self.entries if e.id in self.checked))
        if self.selection_mode:
            self.selection_bar.set_no_show_all(False);self.selection_bar.show_all();self.selection_bar.set_no_show_all(True)
        else:self.selection_bar.hide()
    def select_game(self,e):
        if self.selection_mode:
            if e.id in self.checked:self.checked.remove(e.id)
            else:self.checked.add(e.id)
            self.render();return
        self.selected=e;self.show_detail(e);self.pages.set_visible_child_name('detail')
    def add_cover_card(self,e):
        tile=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);tile.set_size_request(170,-1)
        poster=Gtk.Button();poster.set_relief(Gtk.ReliefStyle.NONE);poster.get_style_context().add_class('poster');poster.set_tooltip_text('Seleccionar '+e.name if self.selection_mode else 'Abrir '+e.name);poster.connect('clicked',lambda _:self.select_game(e));poster.add(Poster(e,find_cover(e),170,255,overlay=True,steam=self.in_steam(e)))
        if e.id in self.checked:poster.get_style_context().add_class('selected')
        tile.pack_start(poster,False,False,0)
        if self.selection_mode:
            name=label(e.name,'cover-title');name.set_line_wrap(False);name.set_ellipsize(Pango.EllipsizeMode.END);name.set_max_width_chars(19);name.set_tooltip_text(e.name)
            check=Gtk.CheckButton();check.add(name);check.set_active(e.id in self.checked);check.connect('toggled',self.toggle,e.id);tile.pack_start(check,False,False,0)
        self.covers.add(tile);self.new_tiles.append(tile)
    def toggle(self,check,id_):
        if check.get_active():self.checked.add(id_)
        else:self.checked.discard(id_)
        self.update_selection()
    def select_visible(self):
        ids={e.id for e in self.visible()}
        if ids and ids.issubset(self.checked):self.checked-=ids
        else:self.checked|=ids
        self.selection_mode=True;self.render()
    def on_select(self,list_,row):
        if row and hasattr(row,'entry'):self.select_game(row.entry)
    def clear_detail(self):self.reset_page(self.detail)
    def show_empty_detail(self):self.clear_detail()
    def single_steam(self,e):
        if e.metadata.get('steam_store'):
            self.message('Juego de Steam','Este juego ya forma parte de la biblioteca de Steam.');return
        if not self.accounts:self.message('Steam sin sesión','Iniciar sesión en Steam para preparar el acceso.');return
        self.add_to_steam([e])

    def controller_summary(self,e):
        """Short text about the saved gamepad layouts for this shortcut."""
        from . import controllers
        try:state=controllers.status(pathlib.Path(e.metadata['steam_account']),e.metadata['steam_appid'])
        except (OSError,ValueError,KeyError):return 'No se pudo leer la configuración de mandos de Steam.'
        if not state:return 'Steam no tiene plantillas de mando disponibles para este acceso.'
        missing=[controllers.FAMILY_NAMES[f] for f,value in state.items() if value is None]
        return 'Layout de gamepad asignado a todos los tipos de mando.' if not missing else 'Sin layout para: '+', '.join(missing)+'. Esos mandos no se detectan en el juego.'

    def show_detail(self,e):
        self.clear_detail();back=button('← Biblioteca',lambda _:self.open_library());back.get_style_context().add_class('flat');back.set_halign(Gtk.Align.START);self.detail.pack_start(back,False,False,0)
        hero=Gtk.Box(spacing=28);art=Poster(e,find_cover(e),200,300);hero.pack_start(art,False,False,0);info=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14);info.set_hexpand(True);info.pack_start(label(e.platform.upper(),'pill'),False,False,0);info.pack_start(label(e.name,'hero'),False,False,0)
        steam_text='En la biblioteca de Steam' if e.metadata.get('steam_store') else 'Acceso guardado en Steam' if self.in_steam(e) else 'Sin acceso en Steam'
        info.pack_start(label(steam_text,'muted'),False,False,0)
        actions=Gtk.Box(spacing=10);actions.pack_start(button('Jugar',lambda _:self.play(e),True),False,False,0)
        if self.in_steam(e):actions.pack_start(button('Quitar de Steam',lambda _:self.remove_from_steam([e]),tone='danger'),False,False,0)
        elif not e.metadata.get('steam_store'):actions.pack_start(button('Agregar a Steam',lambda _:self.single_steam(e)),False,False,0)
        actions.pack_start(button('Cambiar carátula',lambda _:self.artwork_dialog(e)),False,False,0);info.pack_start(actions,False,False,0)
        if self.in_steam(e) and e.kind!='steam':info.pack_start(button('Editar acceso de Steam',lambda _:self.steam_edit_dialog(e)),False,False,0)
        if self.in_steam(e):info.pack_start(button('Arte de Steam (portada, fondo, logotipo, ícono)',lambda _:self.steam_art_dialog(e)),False,False,0)
        origin=e.metadata.get('artwork',{})
        if origin.get('page'):info.pack_start(Gtk.LinkButton.new_with_label(origin['page'],'Carátula de '+origin.get('provider','proveedor')),False,False,0)
        hero.pack_start(info,True,True,0);self.detail.pack_start(hero,False,False,0)
        options=Gtk.FlowBox();options.set_selection_mode(Gtk.SelectionMode.NONE);options.set_min_children_per_line(1);options.set_max_children_per_line(3);options.set_homogeneous(True);options.set_column_spacing(12);options.set_row_spacing(12)
        gta=bool(e.metadata.get('gtaiv_root'))
        choices=[('Arreglo de GTA IV' if gta else 'Ajustes recomendados','FusionFix 4.0.5 y DXVK. Confirmado en una Deck OLED.' if gta else 'Perfiles de video y rendimiento, con vista previa y respaldo.',lambda _:self.preset_dialog(e),'Ver arreglo' if gta else 'Ver ajustes')]
        from . import presets
        if presets.adapter_for(e) in ('duckstation','dolphin','eden','prism'):choices.append(('Ajustes del juego','Resolución, FPS, correcciones y rendimiento de este juego.',lambda _:self.game_settings_dialog(e),'Configurar'))
        if e.platform=='Switch':choices.append(('Contenido','Juego base, actualizaciones, DLC y mods instalados.',lambda _:self.content_dialog(e),'Administrar'))
        if e.platform=='Minecraft':choices.append(('Controles','Distribución recomendada para Minecraft.',lambda _:self.layout_dialog(e),'Ver controles'))
        if self.in_steam(e):choices.append(('Mando',self.controller_summary(e),lambda _:self.fix_controllers(e),'Asignar layout'))
        choices.append(('Diagnóstico','Rutas, programa y registro de la última ejecución.',lambda _:self.check(e),'Revisar'))
        for title,text,callback,action in choices:
            card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);card.get_style_context().add_class('card');card.pack_start(label(title,'title'),False,False,0);description=label(text,'muted');description.set_max_width_chars(32);card.pack_start(description,True,True,0);card.pack_end(button(action,callback),False,False,0);options.add(card)
        self.detail.pack_start(options,False,False,0)
        advanced=Gtk.Expander(label='Opciones avanzadas');box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);box.set_border_width(14);advanced.add(box)
        if e.platform=='Switch':
            toggle=Gtk.CheckButton(label='Usar los mods instalados en Eden');toggle.set_active(e.mods);toggle.connect('toggled',self.set_mods,e);box.pack_start(toggle,False,False,0)
        path=label(e.source or e.command[0],'muted');path.set_selectable(True);path.set_max_width_chars(80);box.pack_start(path,False,False,0);box.pack_start(button('Editar ruta o comando',lambda _:self.manual(e)),False,False,0);self.detail.pack_start(advanced,False,False,0);self.detail.show_all()
    def set_mods(self,toggle,e):
        e.mods=toggle.get_active();self.store.save(self.entries);self.set_status('Perfil guardado. Se aplica en la próxima ejecución del juego.')
    def play(self,e):
        if e.kind=='steam' or e.metadata.get('steam_override'):
            from .steam_inventory import game_uri
            uri='steam://run/'+str(e.metadata['steam_appid']) if e.metadata.get('steam_store') else game_uri(e.metadata['steam_appid'])
            subprocess.Popen(['steam',uri],env=clean_environment());self.set_status('Abriendo '+e.name+' desde Steam…');return
        self.store.save(self.entries);subprocess.Popen([sys.executable,str(pathlib.Path(__file__).resolve().parent.parent/'app.py'),'launch',e.id,'--data-dir',str(self.store.root)],env=clean_environment(),start_new_session=True)
        self.set_status('Abriendo '+e.name+'. Si falla, el diagnóstico muestra el motivo.')
    def check(self,e):
        self.set_status('Revisando '+e.name+'…')
        def work():
            issues,log=diagnostics(e,self.store);GLib.idle_add(self.show_diagnostic,e,issues,log)
        threading.Thread(target=work,daemon=True).start()
    def show_diagnostic(self,e,issues,log):
        dialog=Gtk.Dialog(title='Diagnóstico · '+e.name,transient_for=self,modal=True);dialog.set_default_size(850,530);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(20);box.pack_start(label('\n'.join(issues) if issues else 'Rutas y programa disponibles. Esto no garantiza la compatibilidad del juego.','subtitle'),False,False,12)
        scroll=Gtk.ScrolledWindow();view=Gtk.TextView();view.set_editable(False);view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);view.get_buffer().set_text(log or 'Sin registro todavía. Ejecutar el juego y volver a revisar.');scroll.add(view);box.pack_start(scroll,True,True,0)
        dialog.show_all();dialog.run();dialog.destroy();self.set_status('Diagnóstico revisado.');return False

    def current_account(self):return self.accounts[self.account.get_active()] if self.accounts else None
    def run_queue(self,job,busy_text):
        """Run a queue operation off the GTK thread and report through `queue_done`."""
        self.add_button.set_sensitive(False);self.set_status(busy_text)
        def work():
            try:result=job();GLib.idle_add(self.queue_done,result)
            except Exception as error:GLib.idle_add(self.failed,str(error))
        threading.Thread(target=work,daemon=True).start()
    def add_to_steam(self,selected_entries=None):
        entries=selected_entries if selected_entries is not None else [e for e in self.entries if e.id in self.checked]
        if not entries or not self.accounts:return
        account=self.accounts[self.account.get_active()]
        def job():
            for entry in entries:
                if entry.kind=='steam' or entry.metadata.get('steam_override'):continue
                issues,_=diagnostics(entry,self.store)
                blocking=[i for i in issues if i.startswith(('No se encuentra','El programa no tiene','Un ejecutable Windows','Falta el entorno'))]
                if blocking:raise ValueError(entry.name+': '+'\n'.join(blocking))
            return queue_entries(entries,account,self.store)
        self.run_queue(job,'Preparando los accesos de Steam…')
    def remove_from_steam(self,entries=None):
        entries=entries if entries is not None else [e for e in self.entries if e.id in self.checked]
        targets=[e for e in entries if self.in_steam(e)]
        if not targets:self.message('Sin accesos','Ningún juego seleccionado tiene acceso guardado en Steam.');return
        accounts={e.metadata['steam_account'] for e in targets}
        if len(accounts)>1:self.message('Varias cuentas','Los accesos pertenecen a cuentas de Steam distintas. Quitarlos por separado.');return
        names=', '.join(e.name for e in targets[:4])+(f' y {len(targets)-4} más' if len(targets)>4 else '')
        if not self.confirm('Quitar de Steam',f'{names}\n\nSe elimina el acceso de la biblioteca de Steam, junto con su carátula y su layout de mando. El juego, sus archivos y sus partidas no se modifican. Antes de guardar se crea un respaldo de la lista de accesos.','Quitar',danger=True):return
        account=pathlib.Path(accounts.pop());ids=[e.metadata['steam_appid'] for e in targets]
        self.run_queue(lambda:queue_removals(ids,account,self.store),'Preparando la eliminación de accesos…')
    def fix_controllers(self,e):
        if not self.in_steam(e):self.message('Mando','Agregar primero el juego a Steam.');return
        if not self.confirm('Asignar layout de mando','Se asigna el layout de gamepad de Steam a este acceso para DualSense, DualShock, Xbox, Switch Pro y mandos genéricos, reemplazando el layout que tuviera cada tipo. Los cambios se guardan con Steam cerrado.','Asignar'):return
        account=pathlib.Path(e.metadata['steam_account']);self.run_queue(lambda:queue_controllers([e.metadata['steam_appid']],account,self.store),'Preparando el layout de mando…')
    def queue_done(self,result):
        self.add_button.set_sensitive(True);self.update_selection()
        if result['state']=='idle':self.set_status('Sin cambios.');return False
        if result['state']=='pending':
            self.set_status('Cambios pendientes. Steam debe cerrarse para guardarlos.')
            dialog=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.INFO,buttons=Gtk.ButtonsType.NONE,text='Cambios pendientes')
            dialog.format_secondary_text(f'{result["count"]} cambios preparados. Steam debe cerrarse para guardarlos; cerrar antes cualquier juego abierto.')
            dialog.add_button('Más tarde',Gtk.ResponseType.CANCEL)
            if not (os.environ.get('SteamAppId') or os.environ.get('SteamGameId')):dialog.add_button('Reiniciar Steam y guardar',Gtk.ResponseType.OK)
            response=dialog.run();dialog.destroy()
            if response==Gtk.ResponseType.OK:
                self.set_status('Reiniciando Steam y guardando cambios…')
                def work():
                    try:restart_steam(self.store);GLib.idle_add(self.set_status,'Cambios guardados en Steam.')
                    except Exception as error:GLib.idle_add(self.failed,str(error))
                threading.Thread(target=work,daemon=True).start()
        else:
            self.set_status('Cambios guardados. Abrir Steam para verlos.');self.toast('Cambios guardados en Steam');self.discover()
        return False
    def failed(self,text):self.add_button.set_sensitive(True);self.message('No se pudo guardar',text);self.set_status('La biblioteca de Steam no se modificó.');return False
    def manual(self,existing=None):
        if existing and existing.kind=='steam':self.steam_edit_dialog(existing);return
        dialog=Gtk.Dialog(title='Editar juego' if existing else 'Agregar un juego',transient_for=self,modal=True);dialog.set_default_size(650,510);dialog.add_button('Cancelar',Gtk.ResponseType.CANCEL);dialog.add_button('Guardar',Gtk.ResponseType.OK)
        box=dialog.get_content_area();box.set_border_width(22);box.set_spacing(12)
        kind=Gtk.ComboBoxText();kinds=['Port o app de Linux','Juego emulado','Comando personalizado']
        for k in kinds:kind.append_text(k)
        kind.set_active(1 if existing and existing.kind=='emulated' else 2 if existing else 0);box.pack_start(label('Tipo','muted'),False,False,0);box.pack_start(kind,False,False,0)
        name=Gtk.Entry();name.set_placeholder_text('Nombre en Steam');name.set_text(existing.name if existing else '');box.pack_start(name,False,False,0)
        file_=Gtk.FileChooserButton(title='Elegir juego o programa',action=Gtk.FileChooserAction.OPEN);file_.set_hexpand(True)
        if existing and existing.source:file_.set_filename(existing.source)
        def chosen(widget):
            path=widget.get_filename()
            if path and not name.get_text():name.set_text(nice_name(pathlib.Path(path)))
        file_.connect('file-set',chosen);box.pack_start(file_,False,False,0)
        emulator=Gtk.ComboBoxText();emus=available_emulators(preferences=self.preferences);keys=list(emus)
        for key in keys:emulator.append_text(emus[key]['name'])
        if keys:emulator.set_active(0)
        emulator_label=label('Emulador','muted');box.pack_start(emulator_label,False,False,0);box.pack_start(emulator,False,False,0)
        custom=Gtk.Entry();custom.set_placeholder_text('/ruta/launcher --opcion "ruta del juego"')
        if existing:custom.set_text(shlex.join(existing.command))
        public_id=Gtk.Entry();public_id.set_placeholder_text('Title ID, ID de Wii o identificador del port');public_id.set_text(existing.game_id if existing else '')
        advanced=Gtk.Expander(label='Identificador del juego (opcional)');advanced.add(public_id);box.pack_start(advanced,False,False,0)
        custom_label=label('Comando del launcher','muted');box.pack_start(custom_label,False,False,0);box.pack_start(custom,False,False,0)
        def update_fields(*args):
            file_.set_visible(kind.get_active()!=2)
            emulator.set_visible(kind.get_active()==1);emulator_label.set_visible(kind.get_active()==1)
            custom.set_visible(kind.get_active()==2);custom_label.set_visible(kind.get_active()==2)
        kind.connect('changed',update_fields);update_fields()
        box.pack_start(label('Cualquier emulador se agrega con un comando personalizado. Los archivos de Windows necesitan un launcher de Wine o Proton.','muted'),False,False,0)
        dialog.show_all();update_fields()
        while dialog.run()==Gtk.ResponseType.OK:
            try:
                filename=file_.get_filename();type_=kind.get_active();platform='Linux'
                if type_==0:
                    if not filename:raise ValueError('Elegir el programa que se va a abrir.')
                    command=[filename];entry_kind='port'
                elif type_==1:
                    if not filename or not keys:raise ValueError('Elegir el juego y un emulador instalado.')
                    key=keys[emulator.get_active()];command=emus[key]['command']+emus[key]['flags']+[filename];entry_kind='emulated'
                    platform=next(v[0] for v in SYSTEMS.values() if v[1]==key)
                else:
                    command=shlex.split(custom.get_text());entry_kind='custom';filename=filename or '';platform=existing.platform if existing else 'Personalizado'
                e=Entry(name.get_text().strip(),command,entry_kind,platform,filename or '',mods=existing.mods if existing else True,id=existing.id if existing else '',game_id=public_id.get_text().strip(),cover=existing.cover if existing else '',metadata={**(existing.metadata if existing else {}),'manual_command':True})
                if existing:self.entries=[e if item.id==existing.id else item for item in self.entries];self.store.save(self.entries)
                else:self.entries=self.store.merge([e])
                self.selected=e;self.refresh_platforms();self.render();self.show_detail(e);self.pages.set_visible_child_name('detail');self.fetch_covers();self.set_status('Juego guardado.');break
            except Exception as error:self.message('Datos incorrectos',str(error))
        dialog.destroy()

def run():
    GLib.set_prgname('deck-library');GLib.set_application_name('Deck Library')
    Gtk.Window.set_default_icon_from_file(str(pathlib.Path(__file__).resolve().parent.parent/'assets/icon.svg'))
    provider=Gtk.CssProvider();provider.load_from_data(CSS);Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    window=Window();window.show_all();Gtk.main()
