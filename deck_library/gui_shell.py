"""Library-first shell: top navigation and persistent game tabs, without a sidebar."""
import json,os,pathlib,threading
from gi.repository import Gtk,Gdk,GLib,Pango,GdkPixbuf
from .inline_pages import InlineDialog
from .models import Store
from .installations import settings,save_settings
from .steam import find_accounts,active_account
from .library_view import TYPES,entry_type,visible_entries
from .ui_components import tooltip_when_cut
from .artwork import find_cover
from . import motion,__version__,presets

class ShellMixin:
    def init_shell(self):
        from .gui import label,button,PageStack
        self.set_wmclass('deck-library','deck-library');self.set_icon_from_file(str(self.asset('icon.png')));self.set_default_size(1240,760);self.set_size_request(840,520)
        if self.compact_screen() and not os.environ.get('DECK_LIBRARY_UI_TESTS'):self.maximize()
        from . import layout
        layout.ensure();self.store=Store();self.preferences=settings(self.store);self.view=self.preferences.get('view','covers');self.checked=set();self.selected=None;self.selection_mode=False;self.platform_filter='all';self.type_filter='all';self.artwork_attempted=set();self.artwork_busy=False;self.discover_busy=False;self.wizard_step=0;self.game_tab='profiles';self.detail_game_id=None;self.profile_choice={}
        self.ui_closed=False;self.ui_sources=[];self.library_focus_id=None;self.library_targets={};self.controller_mode=False
        self.connect('size-allocate',self.update_density);self.connect('destroy',Gtk.main_quit);self.connect('destroy',self.close_ui_sources);self.connect('delete-event',lambda *_:not self.discard_game_edits());self.connect('key-press-event',self.library_key);self.connect('set-focus',self.library_focus_changed);self.connect('map',self.fit_window);self.connect('size-allocate',self.update_game_size);self.connect('size-allocate',lambda *_:self.update_controller_hints(self))
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);self.add(root);self.build_navigation(root)
        overlay=Gtk.Overlay();root.pack_start(overlay,True,True,0);self.pages=PageStack();self.pages.set_hexpand(True);self.pages.set_vexpand(True);self.pages.connect('notify::visible-child-name',self.page_changed);self.inline_workflows=[];self.workflow_stack=Gtk.Stack();self.workflow_stack.set_homogeneous(False);self.workflow_stack.connect('notify::visible-child',self.refresh_layout);self.workflow_stack.add_named(self.pages,'main');overlay.add(self.workflow_stack);self.toast_widget=motion.Toast();overlay.add_overlay(self.toast_widget)
        self.build_library_page();self.home_box=self.scrolled_page('home');self.validated_box=self.scrolled_page('validated');self.detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);self.detail.set_border_width(20);self.pages.add_named(self.detail,'detail');self.settings_box=self.scrolled_page('settings');self.updates_box=self.scrolled_page('updates');self.catalog_box=self.scrolled_page('catalog');self.add_box=self.scrolled_page('add');self.pending_box=self.scrolled_page('pending');self.tools_box=self.scrolled_page('tools');self.help_box=self.scrolled_page('help')
        self.wizard_box=Gtk.Stack();self.wizard_box.set_homogeneous(False);self.wizard_box.connect('notify::visible-child',self.refresh_layout);wizard_scroll=self.new_scroll();wizard_scroll.add(self.wizard_box);self.pages.add_named(wizard_scroll,'welcome')
        footer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);footer.set_margin_start(24);footer.set_margin_end(24);footer.set_margin_bottom(8);root.pack_end(footer,False,False,0)
        self.build_pending_banner(footer)
        self.artwork_bar=Gtk.Box(spacing=8);self.artwork_bar.set_no_show_all(True);self.artwork_spinner=Gtk.Spinner();self.artwork_label=label('','meta');self.artwork_bar.pack_start(self.artwork_spinner,False,False,0);self.artwork_bar.pack_start(self.artwork_label,True,True,0);footer.pack_start(self.artwork_bar,False,False,0)
        from .controller_hints import ControllerHints
        self.controller_hint=ControllerHints();self.controller_hint.hide();self.controller_hint.set_no_show_all(True);footer.pack_start(self.controller_hint,False,False,0)
        status_row=Gtk.Box(spacing=12);footer.pack_start(status_row,False,False,0)
        self.status=label('','status');self.status.set_line_wrap(False);self.status.set_ellipsize(Pango.EllipsizeMode.END);self.status.set_no_show_all(True);self.status.hide();status_row.pack_start(self.status,True,True,0)
        self.version_label=label('v'+__version__);self.version_label.set_line_wrap(False);self.version_label.set_max_width_chars(48);self.version_label.set_ellipsize(Pango.EllipsizeMode.END);self.version_label.set_halign(Gtk.Align.START);self.version_label.set_tooltip_text('Instalación en uso: '+str(pathlib.Path(__file__).resolve().parent.parent))
        try:self.entries=self.store.load()
        except Exception as error:self.entries=[];self.set_status('No se pudo leer la biblioteca: '+str(error))
        self.apply_motion();self.refresh_platforms();self.animate_next=True;self.render();self.pages.set_visible_child_name('library')
        from . import updates
        self.update_state=updates.cached(self.store);self.refresh_update_badges()
        if self.preferences.get('onboarding_complete') and self.preferences.get('start_page')=='home':self.home_page()
        if not self.preferences.get('onboarding_complete'):self.start_wizard()
        else:GLib.idle_add(self.discover)
        if self.preferences.get('check_updates',True):self.ui_sources.append(GLib.timeout_add_seconds(5,self.check_updates))
        path=self.store.root/'last-sync.json';self.last_sync_seen=path.stat().st_mtime if path.exists() else 0;self.ui_sources.append(GLib.timeout_add_seconds(3,self.poll_sync));self.refresh_pending()
        self.start_gamepad();GLib.timeout_add_seconds(12,self.top_up_library_art)
    def compact_screen(self):
        screen=Gdk.Screen.get_default()
        return bool(screen) and screen.get_height()<=900 and screen.get_width()<=1400
    def top_up_library_art(self):
        """Desktop Mode: fill empty self-art slots or refresh previous bundled defaults, preserving custom images."""
        if motion.gaming_mode() or self.ui_closed:return False
        try:
            from .library_app import art_items
            from .service import queue_art
            account=self.current_account()
            if account:
                items=art_items(account,self.store)
                if items:queue_art(items,account,self.store,preserve_pending=True)
        except (OSError,ValueError,KeyError):pass
        return False
    def community_login(self):
        from .community import Client
        try:return Client(self.store,self.preferences.get('community_url','https://presets.jokerlan.xyz')).session().get('login') or ''
        except ValueError:return ''
    def signed_in(self):return bool(self.community_login())
    def refresh_account_button(self):
        """Signed out: a visible Register / Sign in button. Signed in: the account name. The session itself lives in community-session.json."""
        button=getattr(self,'account_button',None)
        if button is None:return
        login=self.community_login();style=button.get_style_context()
        caption=login or 'Cuenta'
        button.caption.set_text(caption);button.caption.set_no_show_all(False);button.caption.show()
        button.set_tooltip_text(('Cuenta · '+login) if login else 'Registrarse o iniciar sesión');button.get_accessible().set_name(caption)
        for name in ('steam','quiet'):style.remove_class(name)
        style.add_class('quiet');GLib.idle_add(self.check_owner_mode)
    def update_density(self,_,allocation):
        compact=allocation.height<=900 and allocation.width<=1400
        show_brand=motion.gaming_mode() and allocation.width>=1100
        if getattr(self,'brand_visible',None)!=show_brand and hasattr(self,'brand_label'):
            self.brand_visible=show_brand;self.brand_label.set_no_show_all(not show_brand);self.brand_label.set_visible(show_brand)
        if getattr(self,'deck_density',None)==compact:return
        self.deck_density=compact;style=self.get_style_context()
        for icon in getattr(self,'nav_icons',[]):
            icon.set_no_show_all(compact);icon.set_visible(not compact)
        style.add_class('deck-density') if compact else style.remove_class('deck-density')

    def close_ui_sources(self,*_):
        self.ui_closed=True
        if hasattr(self,'gamepad_driver'):self.gamepad_driver.close()
        for ident in self.ui_sources:
            if GLib.MainContext.default().find_source_by_id(ident):GLib.source_remove(ident)
        self.ui_sources.clear()
    def refresh_layout(self,*_):
        # Fullscreen X11 hosts may map a stack's new child without running its
        # queued allocation. Coalesce changes and flush at the window root.
        if self.ui_closed or getattr(self,'layout_pending',False):return
        self.layout_pending=True
        def flush():
            self.layout_pending=False
            if not self.ui_closed and self.get_mapped():self.queue_resize();self.check_resize()
            return False
        GLib.idle_add(flush)
    def asset(self,name):return pathlib.Path(__file__).resolve().parent.parent/'assets'/name
    def build_navigation(self,root):
        from .gui import label,button
        from .ui_components import Icon
        bar=Gtk.Box(spacing=8);bar.get_style_context().add_class('app-header');bar.set_border_width(6);root.pack_start(bar,False,False,0)
        from . import ui_theme;self.brand_icon=Gtk.Image.new_from_pixbuf(ui_theme.brand_pixbuf(self.asset('brand.png'),28,self.preferences.get('theme','dark')));bar.pack_start(self.brand_icon,False,False,4);brand=label('Deck Library','brand');brand.set_margin_end(12);self.brand_label=brand;bar.pack_start(brand,False,False,0)
        self.nav_buttons={};self.nav_icons=[];self.update_badge=label('','badge');self.update_badge.set_no_show_all(True);self.update_badge.set_valign(Gtk.Align.CENTER);self.update_badge.set_halign(Gtk.Align.CENTER)
        for name,callback in [('Inicio',lambda _:self.home_page()),('Biblioteca',lambda _:self.open_library()),('Verificados',lambda _:self.validated_page()),('Ports',lambda _:self.catalog_page()),('Actualizaciones',lambda _:self.updates_page()),('Herramientas',lambda _:self.tools_page()),('Ajustes',lambda _:self.settings_page())]:
            control=button(name,lambda w,action=callback:self.navigate_from_game(action,w));control.get_style_context().add_class('nav');control.set_valign(Gtk.Align.CENTER);bar.pack_start(control,False,False,0);self.nav_buttons[name]=control
            caption=control.get_child();control.remove(caption);content=Gtk.Box(spacing=7);icon=Icon({'Inicio':'grid','Biblioteca':'library','Verificados':'check','Ports':'controller','Actualizaciones':'download','Herramientas':'folder','Ajustes':'sliders'}[name],18);self.nav_icons.append(icon);content.pack_start(icon,False,False,0);content.pack_start(caption,False,False,0);control.add(content);control.get_accessible().set_name(name)
            if name=='Actualizaciones':
                content.pack_start(self.update_badge,False,False,0)
        self.steam_library_button=button('Agregar a Steam',self.add_library_to_steam);self.steam_library_button.set_valign(Gtk.Align.CENTER);self.steam_library_button.set_tooltip_text('Agregar Deck Library a Steam');self.steam_library_button.get_accessible().set_name('Agregar Deck Library a Steam');self.steam_library_button.get_style_context().add_class('steam-add');bar.pack_start(self.steam_library_button,False,False,0)
        gaming=motion.gaming_mode()
        self.steam_library_button.set_no_show_all(gaming)
        self.steam_library_button.set_visible(not gaming)
        from .gui_account import account_dialog
        from .ui_components import ActionButton
        help_button=ActionButton('Ayuda','file',self.help_page,'quiet');self.help_button=help_button;bar.pack_end(help_button,False,False,0)
        account_button=ActionButton('Cuenta','community',lambda _:account_dialog(self),'quiet');account_button.set_valign(Gtk.Align.CENTER);self.account_button=account_button;bar.pack_end(account_button,False,False,0);self.refresh_account_button()
        self.navigation_controls=[*self.nav_buttons.values(),self.steam_library_button,account_button,help_button]
        # Keep all tabs and the Steam action reachable at compact widths.
        header_scroll=self.new_scroll();header_scroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.NEVER);header_scroll.set_overlay_scrolling(False);root.remove(bar);header_scroll.add(bar);root.pack_start(header_scroll,False,False,0);root.reorder_child(header_scroll,0)
        self.update_banner=Gtk.Box(spacing=12);self.update_banner.set_no_show_all(True);self.update_banner.get_style_context().add_class('banner');self.banner_text=label('');self.banner_action=button('Ver',lambda _:self.banner_clicked());self.update_banner.pack_start(self.banner_text,True,True,0);self.banner_close=Gtk.Button();self.banner_close.add(Icon('close',18));self.banner_close.get_style_context().add_class('quiet');self.banner_close.set_tooltip_text('Cerrar el aviso');self.banner_close.get_accessible().set_name('Cerrar el aviso');self.banner_close.connect('clicked',lambda _:self.dismiss_banner());self.banner_close.show_all();self.update_banner.pack_end(self.banner_close,False,False,0);self.update_banner.pack_end(self.banner_action,False,False,0);root.pack_start(self.update_banner,False,False,0)
        self.build_launch_notice(root)
    def dismiss_banner(self):
        """Hide the notice until its text changes (another update, or a different state)."""
        self.banner_dismissed=self.banner_text.get_text();self.update_banner.hide()
    def scrolled_page(self,name):
        scroll=self.new_scroll();box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);box.set_border_width(14);box.set_margin_end(4);scroll.add(box);self.pages.add_named(scroll,name);return box
    def card(self,parent,title=None):
        from .gui import label
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);box.get_style_context().add_class('card')
        if title:box.pack_start(label(title,'title'),False,False,0)
        parent.pack_start(box,False,False,0);return box
    def page_changed(self,*_):
        page=self.pages.get_visible_child_name();active={'home':'Inicio','library':'Biblioteca','validated':'Verificados','detail':{'home':'Inicio','validated':'Verificados'}.get(getattr(self,'detail_origin','library'),'Biblioteca'),'add':'Ports','catalog':'Ports','updates':'Actualizaciones','tools':'Herramientas','settings':'Ajustes','pending':'Actualizaciones'}.get(page)
        style=self.help_button.get_style_context();style.add_class('active') if page=='help' else style.remove_class('active')
        for name,control in self.nav_buttons.items():
            style=control.get_style_context();style.add_class('active') if name==active else style.remove_class('active')
    def build_library_page(self):
        from .gui import label,button
        page=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);page.set_border_width(14);self.pages.add_named(page,'library')
        head=Gtk.Box(spacing=12);head.pack_start(label('Biblioteca','hero'),False,False,0);self.library_count=label('','meta');self.library_count.get_style_context().add_class('library-count');head.pack_start(self.library_count,True,True,0);self.rescan_button=button('Actualizar biblioteca',self.rescan_library);self.rescan_button.set_valign(Gtk.Align.CENTER);head.pack_end(self.rescan_button,False,False,0);page.pack_start(head,False,False,0)
        toolbar=Gtk.Box(spacing=10);toolbar.get_style_context().add_class('page-toolbar');self.search=Gtk.SearchEntry();self.search.set_placeholder_text('Buscar juegos · X: teclado');self.bind_search_keyboard(self.search);self.search.set_width_chars(16);self.search.set_hexpand(True);self.search.connect('search-changed',lambda _:self.render());toolbar.pack_start(self.search,True,True,0);self.filter_toggle=button('Vista y filtros',self.toggle_library_filters);toolbar.pack_end(self.filter_toggle,False,False,0);page.pack_start(toolbar,False,False,0)
        filters=Gtk.Box(spacing=8);self.platform_picker=Gtk.ComboBoxText();self.platform_picker.get_accessible().set_name('Plataforma');self.platform_picker.append('all','Todas las plataformas');self.platform_picker.set_active_id('all');self.platform_picker.connect('changed',self.filter_changed);filters.pack_start(self.platform_picker,False,False,0)
        self.type_picker=Gtk.ComboBoxText();self.type_picker.get_accessible().set_name('Tipo de juego');self.type_picker.append('all','Todos los tipos')
        for key,title in TYPES:self.type_picker.append(key,title)
        self.type_picker.set_active_id('all');self.type_picker.connect('changed',lambda w:self.type_changed(w.get_active_id() or 'all'));filters.pack_start(self.type_picker,False,False,0)
        self.sort_picker=Gtk.ComboBoxText();self.sort_picker.get_accessible().set_name('Orden de la biblioteca')
        for key,title in [('name','Nombre'),('recent','Jugados hace poco'),('favorites','Favoritos primero')]:self.sort_picker.append(key,title)
        self.library_sort=self.preferences.get('library_sort','name');self.sort_picker.set_active_id(self.library_sort);self.sort_picker.connect('changed',self.change_sort);filters.pack_start(self.sort_picker,False,False,0)
        self.view_picker=Gtk.ComboBoxText();self.view_picker.get_accessible().set_name('Vista de biblioteca')
        for key,title in [('covers','Carátulas'),('list','Lista'),('platforms','Por plataforma')]:self.view_picker.append(key,title)
        self.view_picker.set_active_id(self.view);self.view_picker.connect('changed',self.change_view);filters.pack_end(self.view_picker,False,False,0);self.select_button=button('Seleccionar',lambda _:self.toggle_selection());filters.pack_end(self.select_button,False,False,0);filter_scroll=self.new_scroll();filter_scroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.NEVER);filter_scroll.add(filters);self.filter_scroll=filter_scroll;filter_scroll.set_no_show_all(True);filter_scroll.hide();page.pack_start(filter_scroll,False,False,0)
        self.originals_bar=Gtk.Box(spacing=10);self.originals_bar.set_no_show_all(True);self.originals_label=label('','muted');self.originals_button=button('ROMs asociadas',lambda _:self.originals_dialog());self.originals_bar.pack_end(self.originals_button,False,False,0);filters.pack_end(self.originals_bar,False,False,0)
        self.library_stack=Gtk.Stack();self.library_stack.set_vexpand(True);self.library_stack.connect('notify::visible-child',self.refresh_layout);page.pack_start(self.library_stack,True,True,0)
        self.list=Gtk.ListBox();self.list.set_selection_mode(Gtk.SelectionMode.NONE);self.list.connect('row-activated',lambda _,row:self.select_game(row.entry) if hasattr(row,'entry') else None)
        self.covers=self.poster_grid();self.platform_groups=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20)
        for name,child in [('list',self.list),('covers',self.covers),('platforms',self.platform_groups)]:
            scroll=self.new_scroll();child.set_margin_end(12);child.set_margin_bottom(12);scroll.add(child);self.library_stack.add_named(scroll,name)
        self.empty_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);self.empty_box.set_halign(Gtk.Align.CENTER);self.empty_box.set_valign(Gtk.Align.CENTER);self.empty_box.pack_start(label('Todavía no hay juegos','hero'),False,False,0)
        intro=label('Deck Library junta en un solo lugar los juegos de emuladores y los ports: versiones para PC de juegos de consola, que se instalan desde el catálogo.','muted');intro.set_max_width_chars(60);intro.set_justify(Gtk.Justification.CENTER);self.empty_box.pack_start(intro,False,False,0)
        from .ui_components import ActionButton
        for caption,icon,action,tone in (('Buscar juegos instalados','refresh',lambda _:self.discover(),'play'),('Instalar un port del catálogo','controller',lambda _:self.catalog_page(),'neutral'),('Elegir carpetas de juegos','folder',lambda _:self.installation_dialog(),'neutral')):
            row=ActionButton(caption,icon,action,tone);row.set_halign(Gtk.Align.CENTER);self.empty_box.pack_start(row,False,False,0)
        empty_scroll=self.new_scroll();empty_scroll.add(self.empty_box);self.library_stack.add_named(empty_scroll,'empty')
        self.selection_bar=Gtk.Box(spacing=8);self.selection_bar.get_style_context().add_class('selection-bar');self.selection_bar.set_no_show_all(True);self.selection_label=label('');self.selection_bar.pack_start(self.selection_label,True,True,0);self.selection_bar.pack_start(button('Seleccionar visibles',lambda _:self.select_visible()),False,False,0)
        self.account=Gtk.ComboBoxText();self.accounts=find_accounts();current=active_account()
        if current in self.accounts:self.accounts.remove(current);self.accounts.insert(0,current)
        for i,path in enumerate(self.accounts):self.account.append_text('Cuenta actual' if path==current else 'Cuenta Steam '+str(i+1))
        if not self.accounts:self.account.append_text('Steam sin sesión')
        self.account.set_active(0);self.selection_bar.pack_start(self.account,False,False,0);self.add_button=button('Agregar a Steam',lambda _:self.add_to_steam(),True);self.remove_button=button('Quitar de Steam',lambda _:self.remove_from_steam(),tone='danger');self.selection_bar.pack_end(self.add_button,False,False,0);self.selection_bar.pack_end(self.remove_button,False,False,0);page.pack_end(self.selection_bar,False,False,0)
    def poster_grid(self):
        grid=Gtk.FlowBox();grid.get_style_context().add_class('game-grid');grid.set_selection_mode(Gtk.SelectionMode.NONE);grid.set_min_children_per_line(1);grid.set_max_children_per_line(9);grid.set_column_spacing(16);grid.set_row_spacing(20);grid.set_homogeneous(True);grid.set_valign(Gtk.Align.START);return grid
    def apply_motion(self):
        enabled=self.preferences.get('animations',True);Gtk.Settings.get_default().set_property('gtk-enable-animations',enabled)
        for stack in (self.library_stack,self.wizard_box):stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE if enabled and motion.page_transitions() else Gtk.StackTransitionType.NONE);stack.set_transition_duration(150 if enabled and motion.page_transitions() else 0)
    def shown_entries(self):return visible_entries([e for e in self.entries if e.id not in self.preferences.get('hidden_originals',[])],association_exclusions=self.preferences.get('unlinked_originals',[]))
    def visible(self):
        text=self.search.get_text().casefold();entries,_=self.shown_entries()
        if self.type_filter=='emulator':entries=visible_entries([e for e in self.entries if e.id not in self.preferences.get('hidden_originals',[])],prefer_ports=False)[0]
        from .originals import associations
        linked=associations(self.entries,self.preferences.get('unlinked_originals',[]))
        return sorted([e for e in entries if text in (e.name+' '+e.platform).casefold() and (self.platform_filter=='all' or self.platform_filter==e.platform or any(o.platform==self.platform_filter for o in linked.get(e.id,[]))) and (self.type_filter=='all' or self.type_filter==entry_type(e))],key=self.sort_key())
    def render(self):
        previous_focus=getattr(self.get_focus(),'library_entry_id',None)
        self.library_targets={}
        self.library_dirty=False
        from .originals import pairs,associations,rom_caption
        self.rom_associations=associations(self.entries,self.preferences.get('unlinked_originals',[]))
        if self.type_filter!='emulator':self.checked-={o.id for roms in self.rom_associations.values() for o in roms}
        if previous_focus:previous_focus=next((pid for pid,roms in self.rom_associations.items() if any(o.id==previous_focus for o in roms)),previous_focus)
        originals=[(o,p) for o,p in pairs(self.entries) if o.id not in self.preferences.get('hidden_originals',[])]
        if originals:
            self.originals_label.set_text(str(len(originals))+' originales con un port instalado.');self.originals_button.set_tooltip_text(self.originals_label.get_text());self.originals_bar.set_no_show_all(False);self.originals_bar.show_all();self.originals_bar.set_no_show_all(True)
        else:self.originals_bar.hide()
        from .gui import label,Poster
        self.steam_pending_ids=self.pending_game_ids();self.reset_page(self.list);self.reset_page(self.covers);self.reset_page(self.platform_groups);self.new_tiles=[];entries=self.visible();total=len(self.shown_entries()[0]);self.library_count.set_text(str(total)+' juegos'+(' · '+str(len(entries))+' visibles' if len(entries)!=total else ''))
        groups={}
        for e in entries:
            row=Gtk.ListBoxRow();row.entry=e
            if self.view=='list':self.bind_library_focus(row,e)
            compact=self.compact_screen();body=Gtk.Box(spacing=12 if compact else 16);body.set_border_width(3 if compact else 8);row.add(body)
            if self.selection_mode:
                check=Gtk.CheckButton();check.set_active(e.id in self.checked);check.connect('toggled',self.toggle,e.id);body.pack_start(check,False,False,0)
            body.pack_start(Poster(e,find_cover(e),*((36,54) if compact else (48,72))),False,False,0);texts=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=1 if compact else 6);texts.pack_start(label(e.name,'title'),False,False,0);texts.pack_start(label(e.platform+(' · En Steam' if self.in_steam(e) else ''),'meta'),False,False,0);body.pack_start(texts,True,True,0);self.list.add(row)
            linked=self.rom_associations.get(e.id,[])
            if linked:texts.pack_start(label(rom_caption(linked),'meta'),False,False,0)
            if self.view=='covers':self.add_cover_card(e)
            if self.view=='platforms':
                if e.platform not in groups:groups[e.platform]=[]
                groups[e.platform].append(e)
        for platform,values in sorted(groups.items()):
            self.platform_groups.pack_start(label(platform+' · '+str(len(values)),'title'),False,False,0);grid=self.poster_grid();self.platform_groups.pack_start(grid,False,False,0)
            for e in values:self.add_cover_card(e,grid)
        if not entries and total:
            for container in (self.covers,self.list,self.platform_groups):container.add(label('No hay juegos con esos filtros.','muted'))
        count=int(self.platform_filter!='all')+int(self.type_filter!='all');self.filter_toggle.set_label('Vista y filtros'+(' · '+str(count) if count else ''))
        self.library_stack.show_all();self.library_stack.set_visible_child_name(self.view if total else 'empty');self.update_selection()
        self.refresh_layout()
        if previous_focus:GLib.idle_add(self.focus_library,previous_focus)
        if getattr(self,'animate_next',False):self.animate_next=False;motion.stagger(self.new_tiles,rise=0)
    def rescan_library(self,*_):
        if self.discover_busy:self.toast('La búsqueda sigue en curso');return
        self.explicit_rescan=True;self.rescan_button.set_label('Buscando…');self.rescan_button.set_sensitive(False);self.toast('Buscando juegos instalados');self.discover()

    def toggle_library_filters(self,*_):
        opening=not self.filter_scroll.get_visible()
        if opening:self.filter_scroll.set_no_show_all(False);self.filter_scroll.show_all();self.filter_scroll.set_no_show_all(True)
        else:self.filter_scroll.hide();self.filter_toggle.grab_focus()
        self.refresh_layout()

    def add_cover_card(self,e,target=None):
        from .gui import label,Poster
        tile=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0);tile.get_style_context().add_class('library-game');tile.set_size_request(148,-1);tile.set_halign(Gtk.Align.CENTER);action=Gtk.Button();action.get_style_context().add_class('poster');action.add(Poster(e,find_cover(e),148,222));action.connect('clicked',lambda _:self.select_game(e));action.set_tooltip_text(e.name);self.bind_library_focus(action,e,tile)
        if e.id in self.checked:action.get_style_context().add_class('selected')
        tile.pack_start(action,False,False,0);info=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);info.get_style_context().add_class('game-card-info');tile.pack_start(info,False,False,0);info.pack_start(label(e.platform,'platform-caption'),False,False,0);name=label(e.name,'cover-title');name.set_line_wrap(True);name.set_lines(2);name.set_ellipsize(Pango.EllipsizeMode.END);name.set_max_width_chars(17);name.set_size_request(-1,42);tooltip_when_cut(name,e.name);info.pack_start(name,False,False,0)
        if self.is_favorite(e):info.pack_start(label('★ Favorito','card-state'),False,False,0)
        if e.metadata.get('configured') is False:info.pack_start(label('Necesita preparación','card-state'),False,False,0)
        elif self.in_steam(e):info.pack_start(label('En Steam','card-state'),False,False,0)
        elif e.id in getattr(self,'steam_pending_ids',()):info.pack_start(label('Pendiente en Steam','card-state'),False,False,0)
        (target if target is not None else self.covers).add(tile);tile.get_parent().set_can_focus(False);self.new_tiles.append(tile)
        linked=getattr(self,'rom_associations',{}).get(e.id,[])
        if linked:
            from .originals import rom_caption
            badge=label(rom_caption(linked),'meta');badge.set_tooltip_text('\n'.join(o.source for o in linked));tile.pack_start(badge,False,False,0)
    def open_library(self):
        if not self.discard_game_edits():return
        if getattr(self,'library_dirty',False):self.render()
        self.pages.set_visible_child_name('library');GLib.idle_add(self.focus_library)
    def type_changed(self,key):self.type_filter=key;self.render()
    def sort_key(self):
        from . import history
        favorites=set(self.preferences.get('favorites',[]))
        if self.library_sort=='recent':
            played=history.load(self.store);return lambda e:(-played.get(e.id,0),e.name.casefold())
        if self.library_sort=='favorites':return lambda e:(e.id not in favorites,e.name.casefold())
        return lambda e:e.name.casefold()
    def change_sort(self,picker):
        self.library_sort=picker.get_active_id() or 'name';self.preferences['library_sort']=self.library_sort;save_settings(self.preferences,self.store);self.render()
    def is_favorite(self,entry):return entry.id in self.preferences.get('favorites',[])
    def toggle_favorite(self,entry):
        favorites=[i for i in self.preferences.get('favorites',[]) if i!=entry.id]
        added=not self.is_favorite(entry)
        if added:favorites.append(entry.id)
        self.preferences['favorites']=favorites;save_settings(self.preferences,self.store)
        button=getattr(self,'game_favorite_button',None)
        if button is not None and getattr(self,'selected',None) is not None and self.selected.id==entry.id:button.set_label('Favorito' if added else 'Marcar favorito');button.set_icon('star-fill' if added else 'star')
        self.library_dirty=True;self.toast('Agregado a favoritos' if added else 'Quitado de favoritos')
    def change_view(self,picker):self.view=picker.get_active_id() or 'covers';self.preferences['view']=self.view;save_settings(self.preferences,self.store);self.render()
    def toggle_selection(self):
        self.selection_mode=not self.selection_mode
        if not self.selection_mode:self.checked.clear()
        self.render()
    def update_selection(self):
        self.select_button.set_label('Terminar' if self.selection_mode else 'Seleccionar');self.selection_label.set_text(str(len(self.checked))+' seleccionados');self.add_button.set_sensitive(bool(self.checked) and bool(self.accounts));self.remove_button.set_sensitive(any(self.in_steam(e) for e in self.entries if e.id in self.checked))
        if self.selection_mode:self.selection_bar.set_no_show_all(False);self.selection_bar.show_all();self.selection_bar.set_no_show_all(True)
        else:self.selection_bar.hide()
    def select_game(self,e):
        if self.selection_mode:
            if e.id in self.checked:self.checked.remove(e.id)
            else:self.checked.add(e.id)
            self.render();return
        if not self.discard_game_edits():return
        self.detail_origin=self.pages.get_visible_child_name() if self.pages.get_visible_child_name() in ('home','validated') else 'library';self.library_focus_id=e.id
        if self.detail_origin=='home':self.home_focus_id=e.id
        self.detail_game_id=None;self.selected=e;self.show_detail(e);self.pages.set_visible_child_name('detail');self.game_play_button.grab_focus()
    def add_hub(self):self.catalog_page()
    def settings_page(self):
        from .gui import label,button
        self.reset_page(self.settings_box);self.settings_box.pack_start(label('Ajustes','hero'),False,False,0)
        from . import hardware
        device=hardware.describe()
        if device:self.settings_box.pack_start(label(device,'muted'),False,False,0);self.settings_box.pack_start(label('Con una TV o un monitor externo se pueden usar otras frecuencias: Deck Library no limita la pantalla.','meta'),False,False,0)
        from .ui_components import ActionButton
        groups=[('General',[('Carátulas y apariencia','Proveedor de imágenes, tema, tamaño de la interfaz, idioma y animaciones.','Configurar','image',lambda _:self.appearance_dialog())]),
                ('Biblioteca',[('Instalaciones y carpetas','Emuladores y carpetas de juegos.','Elegir carpetas','folder',lambda _:self.installation_dialog())]),
                ('Mantenimiento',[('Configuración inicial','Volver a detectar instalaciones.','Iniciar asistente','plus',lambda _:self.start_wizard())])]
        for heading,rows in groups:
            self.settings_box.pack_start(label(heading,'section-title'),False,False,0)
            for title,description,caption,icon,action in rows:
                row=Gtk.Box(spacing=16);row.get_style_context().add_class('settings-row');texts=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);texts.pack_start(label(title,'title'),False,False,0);texts.pack_start(label(description,'muted'),False,False,0);row.pack_start(texts,True,True,0);row.pack_end(ActionButton(caption,icon,action,'quiet'),False,False,0);self.settings_box.pack_start(row,False,False,0)
        self.settings_box.pack_start(label('Convertir juegos de Switch, extraer ISO, agregar Deck Library a Steam y revisar duplicados está en Herramientas.','meta'),False,False,0)
        if self.version_label.get_parent() is not None:self.version_label.get_parent().remove(self.version_label)
        self.settings_box.pack_start(self.version_label,False,False,0)
        self.settings_box.show_all();self.pages.set_visible_child_name('settings')
    def appearance_dialog(self):
        from .gui import label,button
        dialog=InlineDialog(title='Carátulas y apariencia',transient_for=self,modal=True);dialog.set_default_size(760,600);dialog.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Guardar',Gtk.ResponseType.OK);box=dialog.get_content_area();box.set_border_width(16);box.set_spacing(12);combo,key=self.provider_fields(box);animations=Gtk.CheckButton(label='Animaciones');animations.set_active(self.preferences.get('animations',True));box.pack_start(animations,False,False,0)
        language=Gtk.ComboBoxText();language.get_accessible().set_name('Idioma · Language')
        for key_,title_ in (('auto','Automático'),('es','Español'),('en','English')):language.append(key_,title_)
        current_language=self.preferences.get('language') or ('es' if self.preferences.get('onboarding_complete') else 'auto');language.set_active_id(current_language)
        first_page=Gtk.ComboBoxText();first_page.get_accessible().set_name('Al abrir Deck Library');first_page.append('library','Biblioteca');first_page.append('home','Inicio');first_page.set_active_id(self.preferences.get('start_page') or 'library');first_row=Gtk.Box(spacing=12);first_row.pack_start(label('Al abrir Deck Library'),True,True,0);first_row.pack_end(first_page,False,False,0);box.pack_start(first_row,False,False,0)
        theme=Gtk.ComboBoxText();theme.get_accessible().set_name('Tema')
        for key_,title_ in (('dark','Negro'),('light','Claro')):theme.append(key_,title_)
        theme.set_active_id(self.preferences.get('theme') or 'dark');theme_row=Gtk.Box(spacing=12);theme_row.pack_start(label('Tema'),True,True,0);theme_row.pack_end(theme,False,False,0);box.pack_start(theme_row,False,False,0)
        scale=Gtk.ComboBoxText();scale.get_accessible().set_name('Tamaño de la interfaz')
        for key_,title_ in (('normal','Normal'),('large','Grande'),('xlarge','Muy grande')):scale.append(key_,title_)
        scale.set_active_id(self.preferences.get('ui_scale') or 'normal');scale_row=Gtk.Box(spacing=12);scale_row.pack_start(label('Tamaño de la interfaz'),True,True,0);scale_row.pack_end(scale,False,False,0);box.pack_start(scale_row,False,False,0)
        language_row=Gtk.Box(spacing=12);language_row.pack_start(label('Idioma · Language'),True,True,0);language_row.pack_end(language,False,False,0);box.pack_start(language_row,False,False,0);self.fit_dialog(dialog);dialog.show_all()
        if dialog.run()==Gtk.ResponseType.OK:
            self.preferences.update(artwork_provider=combo.get_active_id(),steamgriddb_key=key.get_text().strip(),animations=animations.get_active(),start_page=first_page.get_active_id() or 'library',ui_scale=scale.get_active_id() or 'normal',theme=theme.get_active_id() or 'dark')
            from . import gui,ui_theme
            ui_theme.set_theme(self.preferences['theme']);self.brand_icon.set_from_pixbuf(ui_theme.brand_pixbuf(self.asset('brand.png'),28,self.preferences['theme']));Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',self.preferences['theme']!='light')
            if gui.PROVIDER is not None:gui.PROVIDER.load_from_data(ui_theme.css(self.preferences['ui_scale'],self.preferences['theme']))
            self.queue_draw()
            chosen_language=language.get_active_id() or current_language;changed_language=chosen_language!=current_language
            if changed_language:self.preferences['language']=chosen_language
            save_settings(self.preferences,self.store);self.apply_motion();self.toast('Idioma guardado · Language saved. Reabrir Deck Library para aplicarlo · Reopen Deck Library to apply it.' if changed_language else 'Apariencia guardada');self.fetch_covers()
        dialog.destroy()
    def refresh_pending(self):
        from .service import pending_changes,reconcile_pending
        try:reconcile_pending(self.store);rows=pending_changes(self.store)
        except (OSError,ValueError):rows=[]
        if rows:
            self.pending_label.set_text(('Pendiente en Steam · '+rows[0]['description']) if len(rows)==1 else f'{len(rows)} cambios de biblioteca pendientes en Steam');self.pending_bar.set_no_show_all(False);self.pending_bar.show_all();self.pending_bar.set_no_show_all(True)
        else:self.pending_bar.hide()
        self.refresh_game_steam()
        return False
    def after_apply_closing(self,done):
        self.refresh_pending();self.pending_details()
        self.toast('Cambios aplicados' if done else 'Steam se reabrió; los cambios siguen pendientes')
        return False
    def pending_details(self):
        from .gui import label,button
        from .service import pending_changes,cancel_pending
        self.reset_page(self.pending_box);self.pending_box.pack_start(button('← Biblioteca',lambda _:self.open_library()),False,False,0);self.pending_box.pack_start(label('Cambios de Steam','hero'),False,False,0);rows=pending_changes(self.store)
        for row in rows:
            card=self.card(self.pending_box,row['description']);card.pack_start(label(row['detail'],'muted'),False,False,0)
        try:
            state=json.loads((self.store.root/'last-sync.json').read_text())
            if rows and state.get('state')=='failed':self.pending_box.pack_start(label('No se pudieron aplicar: '+state.get('error',''),'muted'),False,False,0)
        except (OSError,ValueError):pass
        if not rows:self.pending_box.pack_start(label('No hay cambios pendientes.','muted'),False,False,0)
        else:
            self.pending_box.pack_start(label('Steam guarda estos cambios cuando se cierra.','title'),False,False,0)
            self.pending_box.pack_start(label('Para verlos en el modo Juego: cerrar Deck Library y reiniciar Steam desde su menú de encendido.' if motion.gaming_mode() else 'Se aplican solos al cerrar Steam, o ahora con el botón de abajo.','muted'),False,False,0)
            if not motion.gaming_mode():
                def apply_now(_):
                    from .service import apply_closing_steam
                    if not self.confirm('Cerrar Steam','Se cierra Steam (y cualquier juego abierto desde Steam), se aplican los cambios y Steam vuelve a abrirse.','Cerrar y aplicar'):return
                    def work():
                        try:done=apply_closing_steam(self.store,lambda text:GLib.idle_add(self.set_status,text))
                        except Exception as error:GLib.idle_add(self.message,'No se pudieron aplicar',str(error));return
                        GLib.idle_add(self.after_apply_closing,done)
                    threading.Thread(target=work,daemon=True).start()
                self.pending_box.pack_start(button('Cerrar Steam y aplicar ahora',apply_now,True),False,False,0)
            def cancel(_):
                if not self.confirm('Descartar cambios pendientes','Se cancelan las operaciones listadas. Los juegos y los accesos directos que ya existen se conservan.','Descartar'):return
                try:cancel_pending(self.store);self.refresh_pending();self.pending_details();self.toast('Cambios descartados')
                except Exception as error:self.message('No se pudo descartar',str(error))
            self.pending_box.pack_start(button('Descartar estos cambios',cancel,tone='danger'),False,False,0)
        self.pending_box.show_all();self.pages.set_visible_child_name('pending')
