"""Deck Library: guided setup, portrait library and focused game pages."""
import json,os,pathlib,shlex,subprocess,sys,threading,math
import gi
gi.require_version('Gtk','3.0')
gi.require_version('PangoCairo','1.0')
from gi.repository import Gtk,Gdk,GLib,Pango,GdkPixbuf
from .models import Store,Entry
from .discovery import scan,available_emulators,nice_name,SYSTEMS
from .runtime import diagnostics,clean_environment
from .service import queue_entries,restart_steam
from .steam import find_accounts,active_account
from .installations import settings,save_settings,report
from .gui_tools import ToolsMixin
from .experience import ExperienceMixin
from .artwork import find_cover

CSS=b'''
window, dialog { background:#11141d; color:#f2f4fa; font-family:Sans; font-size:14px; }
dialog label, dialog list row label { color:#f2f4fa; }
dialog label.muted, dialog list row label.muted { color:#abb5cd; }
dialog .subtitle { color:#abb5cd; }
dialog viewport, dialog scrolledwindow, dialog list { background:#11141d; }
.preset-detail { background:#1b2030; padding:18px; border-radius:12px; }
.sidebar { background:#0b0e16; padding:24px 14px; border-right:1px solid #232838; }
.brand { font-size:21px; font-weight:900; color:#fff; }
.muted { color:#9aa4ba; }
.hero { font-size:32px; font-weight:800; letter-spacing:-1px; }
.welcome-title { font-size:38px; font-weight:900; letter-spacing:-1px; }
.subtitle { color:#abb5cd; font-size:16px; }
button { background:#242a3b; color:#f2f4fa; border:1px solid #343c52; border-radius:10px; padding:10px 15px; box-shadow:none; text-shadow:none; transition:180ms ease; }
button:hover { background:#343e59; border-color:#8e83ff; }
button:active { background:#4c427d; }
button.primary { background:#ae9bff; color:#17102c; border-color:#ae9bff; font-weight:bold; }
button.primary:hover { background:#cbbfff; }
button.action-play { background:#72dbad; color:#102c20; border-color:#72dbad; font-weight:bold; }
button.action-play:hover { background:#95eac4; border-color:#95eac4; }
button.action-steam { background:#79b9fa; color:#10273f; border-color:#79b9fa; font-weight:bold; }
button.action-steam:hover { background:#a0d0ff; border-color:#a0d0ff; }
button.action-presets { background:#b69cfa; color:#271642; border-color:#b69cfa; font-weight:bold; }
button.action-presets:hover { background:#d0bbff; border-color:#d0bbff; }
button.action-content { background:#f1bd70; color:#39270f; border-color:#f1bd70; font-weight:bold; }
button.action-content:hover { background:#ffda9e; border-color:#ffda9e; }
button.action-controls { background:#75d5db; color:#102e32; border-color:#75d5db; font-weight:bold; }
button.action-controls:hover { background:#a0ebee; border-color:#a0ebee; }
button.action-diagnostic { background:#efa8c6; color:#3c1830; border-color:#efa8c6; font-weight:bold; }
button.action-diagnostic:hover { background:#ffc8de; border-color:#ffc8de; }
button.action-artwork { background:#75d5db; color:#102e32; border-color:#75d5db; font-weight:bold; }
button.action-artwork:hover { background:#a0ebee; border-color:#a0ebee; }
button.action-edit { background:#f1bd70; color:#39270f; border-color:#f1bd70; font-weight:bold; }
button.action-edit:hover { background:#ffda9e; border-color:#ffda9e; }
button.action-play label { color:#102c20; }
button.action-steam label { color:#10273f; }
button.action-presets label { color:#271642; }
button.action-content label { color:#39270f; }
button.action-controls label { color:#102e32; }
button.action-diagnostic label { color:#3c1830; }
button.action-artwork label { color:#102e32; }
button.action-edit label { color:#39270f; }
button.primary label { color:#17102c; }
button:disabled { opacity:0.45; }
button.nav { background:transparent; border-color:transparent; padding:12px; }
button.nav:hover { background:#252337; }
button.nav.active { background:#302943; color:#d6caff; border-color:#4a3e65; }
button.flat { background:transparent; border-color:transparent; }
entry, combobox button { background:#1b2030; color:#edf2f8; border:1px solid #343c52; border-radius:10px; padding:9px; }
list, list row { background:transparent; }
list row { border-bottom:1px solid #292f42; padding:10px 8px; }
list row:selected { background:#302b49; }
checkbutton { padding:5px; }
check { min-width:22px; min-height:22px; border:1px solid #737c97; border-radius:6px; background:#242a3b; }
check:checked { background:#ae9bff; color:#17102c; }
.card { background:#1b2030; border:1px solid #30374a; border-radius:14px; padding:18px; }
.title { font-size:18px; font-weight:bold; }
.pill { color:#c1b0ff; font-size:12px; font-weight:bold; }
.status { color:#9aa4ba; font-size:13px; }
.cover-card { padding:2px; }
button.poster { background:#22283a; border:2px solid #30374a; border-radius:12px; padding:0; }
button.poster:hover { border-color:#c4adff; box-shadow:0 6px 18px alpha(#000,0.6); }
button.poster.selected { border-color:#c4adff; }
.cover-title { font-size:14px; font-weight:bold; }
.selection-bar { background:#302943; border:1px solid #6a598f; padding:10px; border-radius:12px; }
.banner { background:linear-gradient(115deg,#30264e,#1d293a); border:1px solid #4c4264; border-radius:14px; padding:18px; }
progressbar trough { background:#232a3c; border:0; border-radius:4px; min-height:5px; }
progressbar progress { background:#ae9bff; border:0; border-radius:4px; }
textview text { background:#11141d; color:#d8e4f1; font-family:monospace; font-size:13px; }
'''

def label(text,style=None):
    widget=Gtk.Label(label=text,xalign=0);widget.set_line_wrap(True);widget.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    if style:widget.get_style_context().add_class(style)
    return widget

def button(text,callback,primary=False,tone=None):
    widget=Gtk.Button(label=text);widget.connect('clicked',callback)
    if primary:widget.get_style_context().add_class('primary')
    if tone:widget.get_style_context().add_class('action-'+tone)
    return widget

class Poster(Gtk.DrawingArea):
    """Fixed 2:3 canvas; contain artwork without cropping game titles."""
    def __init__(self,entry,path,width=160,height=240):
        super().__init__();self.entry=entry;self.set_size_request(width,height);self.pixbuf=None
        if path:
            try:self.pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(path,600,900,True)
            except (GLib.Error,OSError):pass
        self.connect('draw',self.draw_poster)
    def draw_poster(self,widget,cr):
        w=widget.get_allocated_width();h=widget.get_allocated_height()
        palettes={'Switch':(.22,.13,.27),'WiiCompiled':(.10,.28,.34),'Wii':(.10,.28,.34),'Minecraft':(.14,.26,.19)}
        color=palettes.get(self.entry.platform,(.17,.19,.30));cr.set_source_rgb(*color);cr.paint()
        if self.pixbuf:
            pw=self.pixbuf.get_width();ph=self.pixbuf.get_height();scale=min(w/pw,h/ph);cr.save();cr.translate((w-pw*scale)/2,(h-ph*scale)/2);cr.scale(scale,scale);Gdk.cairo_set_source_pixbuf(cr,self.pixbuf,0,0);cr.paint();cr.restore()
        else:
            cr.set_source_rgba(1,1,1,.07)
            for offset in range(-int(h),int(w),38):cr.move_to(offset,0);cr.line_to(offset+h,h)
            cr.set_line_width(14);cr.stroke()
            layout=self.create_pango_layout(self.entry.name);layout.set_width(int((w-30)*Pango.SCALE));layout.set_wrap(Pango.WrapMode.WORD_CHAR);layout.set_alignment(Pango.Alignment.CENTER);layout.set_font_description(Pango.FontDescription('Sans Bold 19'));_,th=layout.get_pixel_size();cr.set_source_rgb(.95,.95,1);cr.move_to(15,(h-th)/2);from gi.repository import PangoCairo;PangoCairo.show_layout(cr,layout)
            cr.set_source_rgba(0,0,0,.3);cr.rectangle(0,h-30,w,30);cr.fill();layout=self.create_pango_layout(self.entry.platform.upper());layout.set_font_description(Pango.FontDescription('Sans Bold 9'));tw,_=layout.get_pixel_size();cr.set_source_rgb(.85,.83,1);cr.move_to((w-tw)/2,h-23);PangoCairo.show_layout(cr,layout)
        return False

class Window(ExperienceMixin,ToolsMixin,Gtk.Window):
    def __init__(self):
        super().__init__(title='Deck Library');self.set_wmclass('deck-library','deck-library');self.set_icon_from_file(str(pathlib.Path(__file__).resolve().parent.parent/'assets/icon.svg'));self.set_default_size(1200,740);self.set_size_request(960,620)
        self.store=Store();self.preferences=settings(self.store);self.view=self.preferences.get('view','covers');self.entries=[];self.checked=set();self.selected=None;self.selection_mode=False;self.platform_filter='all';self.artwork_attempted=set();self.artwork_busy=False;self.discover_busy=False;self.wizard_step=0
        self.connect('destroy',Gtk.main_quit)
        layout=Gtk.Box();self.add(layout)
        side=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);side.set_size_request(175,-1);side.get_style_context().add_class('sidebar');layout.pack_start(side,False,False,0)
        side.pack_start(label('DECK\nLIBRARY','brand'),False,False,6)
        self.nav_buttons={}
        for text,callback in [('Biblioteca',lambda _:self.open_library()),('Agregar juegos',lambda _:self.add_hub()),('Ajustes',lambda _:self.settings_page())]:
            widget=button(text,callback);widget.get_style_context().add_class('nav');side.pack_start(widget,False,False,0);self.nav_buttons[text]=widget
        side.pack_end(label('STEAM DECK\n0.3 · Biblioteca local','muted'),False,False,0)
        main=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);main.set_border_width(22);layout.pack_start(main,True,True,0)
        self.pages=Gtk.Stack();self.pages.set_hexpand(True);self.pages.set_vexpand(True);self.pages.connect('notify::visible-child-name',self.page_changed);main.pack_start(self.pages,True,True,0)
        library=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16);self.pages.add_named(library,'library')
        heading=Gtk.Box(spacing=12);titles=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5);titles.pack_start(label('Biblioteca','hero'),False,False,0);self.library_count=label('','subtitle');titles.pack_start(self.library_count,False,False,0);heading.pack_start(titles,True,True,0);heading.pack_end(button('Actualizar',lambda _:self.discover()),False,False,0);heading.pack_end(button('+ Agregar juegos',lambda _:self.add_hub(),True),False,False,0);library.pack_start(heading,False,False,0)
        toolbar=Gtk.Box(spacing=10);self.search=Gtk.SearchEntry();self.search.set_placeholder_text('Buscar un juego…');self.search.connect('search-changed',lambda _:self.render());toolbar.pack_start(self.search,True,True,0)
        self.platform_picker=Gtk.ComboBoxText();self.platform_picker.append('all','Todas las plataformas');self.platform_picker.set_active_id('all');self.platform_picker.connect('changed',self.filter_changed);toolbar.pack_start(self.platform_picker,False,False,0)
        self.view_picker=Gtk.ComboBoxText();self.view_picker.append('covers','Carátulas');self.view_picker.append('list','Lista');self.view_picker.set_active_id(self.view);self.view_picker.connect('changed',self.change_view);toolbar.pack_start(self.view_picker,False,False,0)
        self.select_button=button('Seleccionar',lambda _:self.toggle_selection());toolbar.pack_start(self.select_button,False,False,0);library.pack_start(toolbar,False,False,0)
        self.library_stack=Gtk.Stack();self.library_stack.set_vexpand(True);library.pack_start(self.library_stack,True,True,0)
        scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);self.list=Gtk.ListBox();self.list.connect('row-selected',self.on_select);scroll.add(self.list);self.library_stack.add_named(scroll,'list')
        covers_scroll=Gtk.ScrolledWindow();covers_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);self.covers=Gtk.FlowBox();self.covers.set_selection_mode(Gtk.SelectionMode.NONE);self.covers.set_max_children_per_line(8);self.covers.set_min_children_per_line(1);self.covers.set_column_spacing(16);self.covers.set_row_spacing(20);self.covers.set_homogeneous(True);self.covers.set_valign(Gtk.Align.START);covers_scroll.add(self.covers);self.library_stack.add_named(covers_scroll,'covers')
        self.empty_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);self.empty_box.set_valign(Gtk.Align.CENTER);self.empty_box.set_halign(Gtk.Align.CENTER);self.empty_box.pack_start(label('Biblioteca vacía','hero'),False,False,0);self.empty_box.pack_start(label('Buscar juegos instalados o agregar un juego manualmente.','subtitle'),False,False,0);self.empty_box.pack_start(button('Buscar juegos',lambda _:self.start_wizard(),True),False,False,0);self.library_stack.add_named(self.empty_box,'empty')
        self.selection_bar=Gtk.Box(spacing=10);self.selection_bar.get_style_context().add_class('selection-bar');self.selection_bar.set_no_show_all(True);library.pack_start(self.selection_bar,False,False,0);self.selection_label=label('0 seleccionados','title');self.selection_bar.pack_start(self.selection_label,False,False,0);self.selection_bar.pack_start(button('Todos los visibles',lambda _:self.select_visible()),False,False,0)
        self.account=Gtk.ComboBoxText();self.accounts=find_accounts();active=active_account()
        if active in self.accounts:self.accounts.remove(active);self.accounts.insert(0,active)
        for index,path in enumerate(self.accounts):self.account.append_text('Cuenta actual' if path==active else 'Cuenta Steam '+str(index+1))
        if not self.accounts:self.account.append_text('Abrí Steam e iniciá sesión')
        self.account.set_active(0);self.selection_bar.pack_start(self.account,True,True,0)
        self.add_button=button('Agregar a Steam',lambda _:self.add_to_steam(),True);self.selection_bar.pack_end(self.add_button,False,False,0)
        detail_scroll=Gtk.ScrolledWindow();detail_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);self.detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);detail_scroll.add(self.detail);self.pages.add_named(detail_scroll,'detail')
        self.settings_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20);settings_scroll=Gtk.ScrolledWindow();settings_scroll.add(self.settings_box);self.pages.add_named(settings_scroll,'settings')
        self.add_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);self.pages.add_named(self.add_box,'add')
        self.wizard_box=Gtk.Stack();self.wizard_box.set_homogeneous(False);self.pages.add_named(self.wizard_box,'welcome')
        self.artwork_bar=Gtk.Box(spacing=10);self.artwork_bar.set_no_show_all(True);self.artwork_spinner=Gtk.Spinner();self.artwork_label=label('','muted');self.artwork_bar.pack_start(self.artwork_spinner,False,False,0);self.artwork_bar.pack_start(self.artwork_label,True,True,0);main.pack_start(self.artwork_bar,False,False,0)
        self.status=label('','status');main.pack_start(self.status,False,False,0)
        try:self.entries=self.store.load()
        except Exception as error:self.message('No se pudo leer la biblioteca',str(error))
        self.apply_motion();self.refresh_platforms();self.render();self.pages.set_visible_child_name('library')
        if not self.preferences.get('onboarding_complete'):self.start_wizard()
        else:GLib.idle_add(self.discover)
        sync_path=self.store.root/'last-sync.json';self.last_sync_seen=sync_path.stat().st_mtime if sync_path.exists() else 0;GLib.timeout_add_seconds(3,self.poll_sync)
    def apply_motion(self):
        enabled=self.preferences.get('animations',True);Gtk.Settings.get_default().set_property('gtk-enable-animations',enabled)
        for stack in (self.pages,self.library_stack,self.wizard_box):stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT if enabled else Gtk.StackTransitionType.NONE);stack.set_transition_duration(220 if enabled else 0)
    def page_changed(self,stack,*args):
        page=stack.get_visible_child_name();active={'library':'Biblioteca','detail':'Biblioteca','add':'Agregar juegos','welcome':'Agregar juegos','settings':'Ajustes'}.get(page)
        for text,widget in self.nav_buttons.items():
            context=widget.get_style_context()
            if text==active:context.add_class('active')
            else:context.remove_class('active')
    def reset_page(self,box):
        for child in box.get_children():box.remove(child)
    def open_library(self):self.pages.set_visible_child_name('library');self.render()
    def add_hub(self):
        self.reset_page(self.add_box);self.add_box.pack_start(label('Agregar juegos','hero'),False,False,0);self.add_box.pack_start(label('Detectar instalaciones, elegir un archivo o preparar Mario Kart Wii.','subtitle'),False,False,0)
        for title,text,action in [('Buscar lo instalado','Detectar EmuDeck, ports y las instancias de Minecraft.',lambda _:self.start_wizard()),('Elegir un juego o una app','Seleccionar una ROM, un programa o un launcher.',lambda _:self.manual()),('Preparar Mario Kart Wii','Recompilar tu imagen PAL y dejarla lista para la Deck.',lambda _:self.setup_wii_dialog())]:
            card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);card.get_style_context().add_class('card');card.pack_start(label(title,'title'),False,False,0);card.pack_start(label(text,'muted'),False,False,0);card.pack_start(button('Continuar →',action),False,False,0);self.add_box.pack_start(card,False,False,0)
        self.add_box.show_all();self.pages.set_visible_child_name('add')
    def poll_sync(self):
        path=self.store.root/'last-sync.json'
        try:
            if path.exists() and path.stat().st_mtime>self.last_sync_seen:
                value=json.loads(path.read_text());self.last_sync_seen=path.stat().st_mtime;self.set_status(f'{value["count"]} accesos guardados. Abrí Steam para verlos.')
        except (OSError,ValueError):pass
        return True
    def set_status(self,text):self.status.set_text(text)
    def message(self,title,text):
        dialog=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.INFO,buttons=Gtk.ButtonsType.OK,text=title);dialog.format_secondary_text(text);dialog.run();dialog.destroy()
    def discover(self):
        if self.discover_busy:return False
        self.discover_busy=True;self.set_status('Buscando tus juegos e instalaciones…');preferences=dict(self.preferences)
        def work():
            try:
                found=report(preferences=preferences);from .steam_inventory import merge_steam
                entries=self.store.merge(merge_steam(self.store.merge(scan(preferences=preferences),overwrite=False)),overwrite=False);GLib.idle_add(self.discovered,entries,found)
            except Exception as error:GLib.idle_add(self.discovery_failed,str(error))
        threading.Thread(target=work,daemon=True).start();return False
    def discovery_failed(self,text):
        self.discover_busy=False;self.set_status('No pudimos completar la búsqueda: '+text)
        if self.pages.get_visible_child_name()=='welcome' and self.wizard_step==1:self.wizard_report_label.set_text('La búsqueda falló. Revisá las rutas y volvé a buscar.');self.wizard_continue.set_sensitive(True)
        return False
    def discovered(self,entries,found=None):
        self.discover_busy=False;self.entries=entries
        if self.selected:self.selected=next((e for e in entries if e.id==self.selected.id),None)
        self.refresh_platforms();self.render();self.set_status(f'{len(entries)} juegos encontrados.');self.wizard_detection_ready(found or report(preferences=self.preferences))
        if self.pages.get_visible_child_name()!='welcome':self.fetch_covers()
        return False
    def refresh_platforms(self):
        self.platform_picker.handler_block_by_func(self.filter_changed);self.platform_picker.remove_all();self.platform_picker.append('all','Todas las plataformas')
        for platform in sorted({e.platform for e in self.entries}):self.platform_picker.append(platform,platform)
        self.platform_picker.set_active_id(self.platform_filter)
        if self.platform_picker.get_active_id() is None:self.platform_filter='all';self.platform_picker.set_active_id('all')
        self.platform_picker.handler_unblock_by_func(self.filter_changed)
    def filter_changed(self,picker):self.platform_filter=picker.get_active_id() or 'all';self.render()
    def visible(self):
        text=self.search.get_text().casefold();return sorted([e for e in self.entries if text in (e.name+' '+e.platform).casefold() and (self.platform_filter=='all' or e.platform==self.platform_filter)],key=lambda e:e.name.casefold())
    def render(self):
        self.reset_page(self.list);self.reset_page(self.covers);visible=self.visible()
        self.library_count.set_text(f'{len(self.entries)} juegos · {len({e.platform for e in self.entries})} plataformas')
        for entry in visible:
            row=Gtk.ListBoxRow();row.entry=entry;box=Gtk.Box(spacing=14);row.add(box)
            if self.selection_mode:
                check=Gtk.CheckButton();check.set_active(entry.id in self.checked);check.connect('toggled',self.toggle,entry.id);box.pack_start(check,False,False,0)
            texts=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);texts.pack_start(label(entry.name,'title'),False,False,0);texts.pack_start(label(entry.platform,'muted'),False,False,0);box.pack_start(texts,True,True,0);box.pack_end(label('Ver juego →','pill'),False,False,0);self.list.add(row);self.add_cover_card(entry)
        if not visible and self.entries:
            self.covers.add(label('No hay juegos con ese filtro. Probá otro nombre o plataforma.','muted'));self.list.add(label('No hay resultados.','muted'))
        self.library_stack.set_visible_child_name(self.view if self.entries else 'empty');self.library_stack.show_all();self.update_selection()
    def change_view(self,picker):self.view=picker.get_active_id() or 'covers';self.preferences['view']=self.view;save_settings(self.preferences,self.store);self.render()
    def toggle_selection(self):
        self.selection_mode=not self.selection_mode
        if not self.selection_mode:self.checked.clear()
        self.render()
    def update_selection(self):
        self.select_button.set_label('Terminar selección' if self.selection_mode else 'Seleccionar');self.selection_label.set_text(f'{len(self.checked)} seleccionados');self.add_button.set_sensitive(bool(self.checked) and bool(self.accounts))
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
        tile=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);tile.set_size_request(165,-1);tile.get_style_context().add_class('cover-card')
        poster=Gtk.Button();poster.set_relief(Gtk.ReliefStyle.NONE);poster.get_style_context().add_class('poster');poster.set_tooltip_text('Seleccionar '+e.name if self.selection_mode else 'Abrir ficha de '+e.name);poster.connect('clicked',lambda _:self.select_game(e));poster.add(Poster(e,find_cover(e)))
        if e.id in self.checked:poster.get_style_context().add_class('selected')
        tile.pack_start(poster,False,False,0)
        name=label(e.name,'cover-title');name.set_line_wrap(False);name.set_ellipsize(Pango.EllipsizeMode.END);name.set_max_width_chars(19);name.set_tooltip_text(e.name)
        if self.selection_mode:
            check=Gtk.CheckButton();check.add(name);check.set_active(e.id in self.checked);check.connect('toggled',self.toggle,e.id);tile.pack_start(check,False,False,0)
        else:tile.pack_start(name,False,False,0)
        tile.pack_start(label(e.platform,'pill'),False,False,0);self.covers.add(tile)
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
            self.message('Juego de Steam','GTA IV ya forma parte de tu biblioteca de Steam.');return
        if not self.accounts:self.message('Abrí Steam primero','Iniciá sesión en Steam para preparar el acceso.');return
        self.add_to_steam([e])
    def show_detail(self,e):
        self.clear_detail();back=button('← Biblioteca',lambda _:self.open_library());back.get_style_context().add_class('flat');back.set_halign(Gtk.Align.START);self.detail.pack_start(back,False,False,0)
        hero=Gtk.Box(spacing=28);art=Poster(e,find_cover(e),200,300);hero.pack_start(art,False,False,0);info=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16);info.set_hexpand(True);info.pack_start(label(e.platform.upper(),'pill'),False,False,0);info.pack_start(label(e.name,'hero'),False,False,0)
        actions=Gtk.Box(spacing=10);actions.pack_start(button('▶ Jugar',lambda _:self.play(e),tone='play'),False,False,0);actions.pack_start(button('+ Agregar a Steam',lambda _:self.single_steam(e),tone='steam'),False,False,0);info.pack_start(actions,False,False,0)
        artrow=Gtk.Box(spacing=8);artrow.pack_start(button('Cambiar carátula',lambda _:self.artwork_dialog(e),tone='artwork'),False,False,0)
        info.pack_start(artrow,False,False,0)
        origin=e.metadata.get('artwork',{})
        if origin.get('page'):info.pack_start(Gtk.LinkButton.new_with_label(origin['page'],'Carátula de '+origin.get('provider','proveedor')),False,False,0)
        hero.pack_start(info,True,True,0);self.detail.pack_start(hero,False,False,0)
        options=Gtk.FlowBox();options.set_selection_mode(Gtk.SelectionMode.NONE);options.set_min_children_per_line(1);options.set_max_children_per_line(3);options.set_homogeneous(True);options.set_column_spacing(12)
        choices=[('Arreglo de GTA IV' if e.metadata.get('gtaiv_root') else 'Ajustes recomendados','FusionFix 4.0.5 y ajustes de DXVK · confirmado por usuario.' if e.metadata.get('gtaiv_root') else 'Aplicar o restaurar presets y exportar comentarios.',lambda _:self.preset_dialog(e),'presets','Ver arreglo' if e.metadata.get('gtaiv_root') else 'Ver ajustes')]
        if e.platform=='Switch':choices.append(('Contenido del juego','Juego base, actualizaciones, DLC y mods instalados.',lambda _:self.content_dialog(e),'content','Ver contenido'))
        if e.platform=='Minecraft':choices.append(('Controles','Distribución recomendada para Minecraft.',lambda _:self.layout_dialog(e),'controls','Ver controles'))
        choices.append(('Diagnóstico','Rutas y registro de ejecución del juego.',lambda _:self.check(e),'diagnostic','Ver diagnóstico'))
        for title,text,callback,tone,action in choices:
            card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);card.get_style_context().add_class('card');card.pack_start(label(title,'title'),False,False,0);description=label(text,'muted');description.set_max_width_chars(30);card.pack_start(description,True,True,0);card.pack_end(button(action,callback,tone=tone),False,False,0);options.add(card)
        self.detail.pack_start(options,False,False,0)
        if e.metadata.get('steam_appid'):
            info.pack_start(label('Acceso existente en Steam','pill'),False,False,0)
            if not e.metadata.get('steam_store'):info.pack_start(button('Editar acceso de Steam',lambda _:self.steam_edit_dialog(e),tone='steam'),False,False,0)
        advanced=Gtk.Expander(label='Opciones avanzadas');box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);box.set_border_width(14);advanced.add(box)
        if e.platform=='Switch':
            toggle=Gtk.CheckButton(label='Usar mods instalados en Eden');toggle.set_active(e.mods);toggle.connect('toggled',self.set_mods,e);box.pack_start(toggle,False,False,0)
        path=label(e.source or e.command[0],'muted');path.set_selectable(True);path.set_max_width_chars(80);box.pack_start(path,False,False,0);box.pack_start(button('Editar ruta o comando',lambda _:self.manual(e),tone='edit'),False,False,0);self.detail.pack_start(advanced,False,False,0);self.detail.show_all()
    def set_mods(self,toggle,e):
        e.mods=toggle.get_active();self.store.save(self.entries);self.set_status('Perfil guardado. Se usará la próxima vez que abras el juego.')
    def play(self,e):
        if e.kind=='steam' or e.metadata.get('steam_override'):
            from .steam_inventory import game_uri
            uri='steam://run/'+str(e.metadata['steam_appid']) if e.metadata.get('steam_store') else game_uri(e.metadata['steam_appid'])
            subprocess.Popen(['steam',uri],env=clean_environment());self.set_status('Abriendo '+e.name+' desde Steam…');return
        self.store.save(self.entries);subprocess.Popen([sys.executable,str(pathlib.Path(__file__).resolve().parent.parent/'app.py'),'launch',e.id,'--data-dir',str(self.store.root)],env=clean_environment(),start_new_session=True)
        self.set_status('Abriendo '+e.name+'… Si falla, el diagnóstico mostrará el motivo.')
    def check(self,e):
        self.set_status('Revisando '+e.name+'…')
        def work():
            issues,log=diagnostics(e,self.store);GLib.idle_add(self.show_diagnostic,e,issues,log)
        threading.Thread(target=work,daemon=True).start()
    def show_diagnostic(self,e,issues,log):
        dialog=Gtk.Dialog(title='Diagnóstico · '+e.name,transient_for=self,modal=True);dialog.set_default_size(850,530);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(20);box.pack_start(label('\n'.join(issues) if issues else 'Las rutas y el programa están disponibles. Esto no garantiza compatibilidad del juego.','subtitle'),False,False,12)
        scroll=Gtk.ScrolledWindow();view=Gtk.TextView();view.set_editable(False);view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);view.get_buffer().set_text(log or 'Todavía no hay un registro. Usá “Probar juego” y volvé a revisar.');scroll.add(view);box.pack_start(scroll,True,True,0)
        dialog.show_all();dialog.run();dialog.destroy();self.set_status('Diagnóstico revisado.');return False
    def add_to_steam(self,selected_entries=None):
        entries=selected_entries if selected_entries is not None else [e for e in self.entries if e.id in self.checked]
        if not entries or not self.accounts:return
        account=self.accounts[self.account.get_active()]
        self.add_button.set_sensitive(False);self.set_status('Preparando los accesos de Steam…')
        def work():
            try:
                for entry in entries:
                    if entry.kind=='steam' or entry.metadata.get('steam_override'):continue
                    issues,_=diagnostics(entry,self.store)
                    blocking=[i for i in issues if i.startswith(('No se encuentra','El programa no tiene','Un ejecutable Windows','Falta el entorno'))]
                    if blocking:raise ValueError(entry.name+': '+ '\n'.join(blocking))
                result=queue_entries(entries,account,self.store);GLib.idle_add(self.saved,result)
            except Exception as error:GLib.idle_add(self.failed,str(error))
        threading.Thread(target=work,daemon=True).start()
    def saved(self,result):
        self.add_button.set_sensitive(True)
        if result['state']=='pending':
            self.set_status('Accesos preparados. Reiniciá Steam para verlos.')
            dialog=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.INFO,buttons=Gtk.ButtonsType.NONE,text='Accesos preparados')
            dialog.format_secondary_text(f'{result["count"]} juegos listos. Steam necesita reiniciarse para guardar los accesos. Cerrá cualquier juego abierto antes de continuar.')
            dialog.add_button('Más tarde',Gtk.ResponseType.CANCEL)
            if not (os.environ.get('SteamAppId') or os.environ.get('SteamGameId')):dialog.add_button('Reiniciar Steam y guardar',Gtk.ResponseType.OK)
            response=dialog.run();dialog.destroy()
            if response==Gtk.ResponseType.OK:
                self.set_status('Reiniciando Steam y guardando accesos…')
                def work():
                    try:restart_steam(self.store);GLib.idle_add(self.set_status,'Accesos guardados. Ya podés encontrarlos en Steam.')
                    except Exception as error:GLib.idle_add(self.failed,str(error))
                threading.Thread(target=work,daemon=True).start()
        else:self.set_status(f'{result["count"]} accesos guardados. Abrí Steam para verlos.');self.message('Listo',f'{result["count"]} juegos agregados a Steam. Se guardó un backup de tu biblioteca.')
        return False
    def failed(self,text):self.add_button.set_sensitive(True);self.message('No se pudo guardar',text);self.set_status('La biblioteca de Steam se conservó.');return False
    def manual(self,existing=None):
        if existing and existing.kind=='steam':self.steam_edit_dialog(existing);return
        dialog=Gtk.Dialog(title='Editar juego' if existing else 'Agregar un juego',transient_for=self,modal=True);dialog.set_default_size(650,510);dialog.add_button('Cancelar',Gtk.ResponseType.CANCEL);dialog.add_button('Guardar juego',Gtk.ResponseType.OK)
        box=dialog.get_content_area();box.set_border_width(22);box.set_spacing(12)
        kind=Gtk.ComboBoxText();kinds=['Port / app Linux','Juego emulado','Comando personalizado']
        for k in kinds:kind.append_text(k)
        kind.set_active(1 if existing and existing.kind=='emulated' else 2 if existing else 0);box.pack_start(label('Agregar juegos','title'),False,False,0);box.pack_start(kind,False,False,0)
        name=Gtk.Entry();name.set_placeholder_text('Nombre que aparecerá en Steam');name.set_text(existing.name if existing else '');box.pack_start(name,False,False,0)
        file_=Gtk.FileChooserButton(title='Elegir juego o programa',action=Gtk.FileChooserAction.OPEN);file_.set_hexpand(True)
        if existing and existing.source:file_.set_filename(existing.source)
        def chosen(widget):
            path=widget.get_filename()
            if path and not name.get_text():name.set_text(nice_name(pathlib.Path(path)))
        file_.connect('file-set',chosen);box.pack_start(file_,False,False,0)
        emulator=Gtk.ComboBoxText();emus=available_emulators(preferences=self.preferences);keys=list(emus)
        for key in keys:emulator.append_text(emus[key]['name'])
        if keys:emulator.set_active(0)
        emulator_label=label('¿Con qué emulador lo abrís?','muted');box.pack_start(emulator_label,False,False,0);box.pack_start(emulator,False,False,0)
        custom=Gtk.Entry();custom.set_placeholder_text('Ejemplo: /ruta/launcher --opcion "ruta del juego"')
        if existing:custom.set_text(shlex.join(existing.command))
        public_id=Gtk.Entry();public_id.set_placeholder_text('ID público del juego (Title ID / ID Wii / identificador del port)');public_id.set_text(existing.game_id if existing else '');
        advanced=Gtk.Expander(label='Identificador del juego (opcional)');advanced.add(public_id);box.pack_start(advanced,False,False,0)
        custom_label=label('Comando del launcher','muted');box.pack_start(custom_label,False,False,0);box.pack_start(custom,False,False,0)
        def update_fields(*args):
            file_.set_visible(kind.get_active()!=2)
            emulator.set_visible(kind.get_active()==1);emulator_label.set_visible(kind.get_active()==1)
            custom.set_visible(kind.get_active()==2);custom_label.set_visible(kind.get_active()==2)
        kind.connect('changed',update_fields);update_fields()
        box.pack_start(label('Podés agregar cualquier emulador mediante un comando personalizado. Los archivos Windows necesitan un launcher de Wine/Proton.','muted'),False,False,0)
        dialog.show_all();update_fields()
        while dialog.run()==Gtk.ResponseType.OK:
            try:
                filename=file_.get_filename();type_=kind.get_active();platform='Linux'
                if type_==0:
                    if not filename:raise ValueError('Elegí el programa que querés abrir.')
                    command=[filename];entry_kind='port'
                elif type_==1:
                    if not filename or not keys:raise ValueError('Elegí el juego y un emulador instalado.')
                    key=keys[emulator.get_active()];command=emus[key]['command']+emus[key]['flags']+[filename];entry_kind='emulated'
                    platform=next(v[0] for v in SYSTEMS.values() if v[1]==key)
                else:
                    command=shlex.split(custom.get_text());entry_kind='custom';filename=filename or '';platform=existing.platform if existing else 'Personalizado'
                e=Entry(name.get_text().strip(),command,entry_kind,platform,filename or '',mods=existing.mods if existing else True,id=existing.id if existing else '',game_id=public_id.get_text().strip(),cover=existing.cover if existing else '',metadata={**(existing.metadata if existing else {}),'manual_command':True})
                if existing:self.entries=[e if item.id==existing.id else item for item in self.entries];self.store.save(self.entries)
                else:self.entries=self.store.merge([e])
                self.selected=e;self.refresh_platforms();self.render();self.show_detail(e);self.pages.set_visible_child_name('detail');self.fetch_covers();self.set_status('Juego guardado. Ya podés agregarlo a Steam.');break
            except Exception as error:self.message('Revisá los datos',str(error))
        dialog.destroy()

def run():
    GLib.set_prgname('deck-library');GLib.set_application_name('Deck Library')
    Gtk.Window.set_default_icon_from_file(str(pathlib.Path(__file__).resolve().parent.parent/'assets/icon.svg'))
    provider=Gtk.CssProvider();provider.load_from_data(CSS);Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    window=Window();window.show_all();Gtk.main()
