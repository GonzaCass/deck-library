"""Library-first shell: top navigation and persistent game tabs, without a sidebar."""
import json,os,pathlib,threading
from gi.repository import Gtk,Gdk,GLib,Pango,GdkPixbuf
from .models import Store
from .installations import settings,save_settings
from .steam import find_accounts,active_account
from .library_view import TYPES,entry_type,visible_entries
from .artwork import find_cover
from . import motion,__version__,presets

class ShellMixin:
    def init_shell(self):
        from .gui import label,button,PageStack
        self.set_wmclass('deck-library','deck-library');self.set_icon_from_file(str(self.asset('icon.png')));self.set_default_size(1240,760);self.set_size_request(840,520)
        self.store=Store();self.preferences=settings(self.store);self.view=self.preferences.get('view','covers');self.checked=set();self.selected=None;self.selection_mode=False;self.platform_filter='all';self.type_filter='all';self.artwork_attempted=set();self.artwork_busy=False;self.discover_busy=False;self.wizard_step=0;self.game_tab='profiles';self.detail_game_id=None;self.profile_choice={}
        self.ui_closed=False;self.ui_sources=[]
        self.connect('destroy',Gtk.main_quit);self.connect('destroy',self.close_ui_sources);self.connect('delete-event',lambda *_:not self.discard_game_edits());self.connect('key-press-event',self.library_key);self.connect('map',self.fit_window);self.connect('size-allocate',self.update_game_size)
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);self.add(root);self.build_navigation(root)
        overlay=Gtk.Overlay();root.pack_start(overlay,True,True,0);self.pages=PageStack();self.pages.set_hexpand(True);self.pages.set_vexpand(True);self.pages.connect('notify::visible-child-name',self.page_changed);overlay.add(self.pages);self.toast_widget=motion.Toast();overlay.add_overlay(self.toast_widget)
        self.build_library_page();self.detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);self.detail.set_border_width(20);self.pages.add_named(self.detail,'detail');self.settings_box=self.scrolled_page('settings');self.updates_box=self.scrolled_page('updates');self.catalog_box=self.scrolled_page('catalog');self.add_box=self.scrolled_page('add');self.pending_box=self.scrolled_page('pending')
        self.wizard_box=Gtk.Stack();self.wizard_box.set_homogeneous(False);wizard_scroll=self.new_scroll();wizard_scroll.add(self.wizard_box);self.pages.add_named(wizard_scroll,'welcome')
        footer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);footer.set_margin_start(24);footer.set_margin_end(24);footer.set_margin_bottom(8);root.pack_end(footer,False,False,0)
        self.build_pending_banner(footer)
        self.artwork_bar=Gtk.Box(spacing=8);self.artwork_bar.set_no_show_all(True);self.artwork_spinner=Gtk.Spinner();self.artwork_label=label('','meta');self.artwork_bar.pack_start(self.artwork_spinner,False,False,0);self.artwork_bar.pack_start(self.artwork_label,True,True,0);footer.pack_start(self.artwork_bar,False,False,0)
        self.status=label('','status');self.status.set_line_wrap(False);self.status.set_ellipsize(Pango.EllipsizeMode.END);footer.pack_start(self.status,False,False,0)
        try:self.entries=self.store.load()
        except Exception as error:self.entries=[];self.set_status('No se pudo leer la biblioteca: '+str(error))
        self.apply_motion();self.refresh_platforms();self.animate_next=True;self.render();self.pages.set_visible_child_name('library')
        from . import updates
        self.update_state=updates.cached(self.store);self.refresh_update_badges()
        if not self.preferences.get('onboarding_complete'):self.start_wizard()
        else:GLib.idle_add(self.discover)
        if self.preferences.get('check_updates',True):self.ui_sources.append(GLib.timeout_add_seconds(5,self.check_updates))
        path=self.store.root/'last-sync.json';self.last_sync_seen=path.stat().st_mtime if path.exists() else 0;self.ui_sources.append(GLib.timeout_add_seconds(3,self.poll_sync));self.refresh_pending()
        self.start_gamepad()
    def close_ui_sources(self,*_):
        self.ui_closed=True
        if hasattr(self,'gamepad_driver'):self.gamepad_driver.close()
        for ident in self.ui_sources:
            if GLib.MainContext.default().find_source_by_id(ident):GLib.source_remove(ident)
        self.ui_sources.clear()
    def asset(self,name):return pathlib.Path(__file__).resolve().parent.parent/'assets'/name
    def build_navigation(self,root):
        from .gui import label,button
        from .ui_components import Icon
        bar=Gtk.Box(spacing=8);bar.get_style_context().add_class('app-header');bar.set_border_width(12);root.pack_start(bar,False,False,0)
        icon=Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(self.asset('icon.png')),32,32,True));bar.pack_start(icon,False,False,8);brand=label('Deck Library','brand');brand.set_margin_end(8);bar.pack_start(brand,False,False,0)
        self.nav_buttons={};self.update_badge=label('','badge');self.update_badge.set_no_show_all(True)
        for name,callback in [('Biblioteca',lambda _:self.open_library()),('Catálogo de ports',lambda _:self.catalog_page()),('Actualizaciones',lambda _:self.updates_page()),('Ajustes',lambda _:self.settings_page())]:
            control=button(name,lambda w,action=callback:self.navigate_from_game(action,w));control.get_style_context().add_class('nav');bar.pack_start(control,False,False,0);self.nav_buttons[name]=control
            caption=control.get_child();control.remove(caption);content=Gtk.Box(spacing=7);content.pack_start(Icon({'Biblioteca':'library','Catálogo de ports':'plus','Actualizaciones':'download','Ajustes':'sliders'}[name],18),False,False,0);content.pack_start(caption,False,False,0);control.add(content);control.get_accessible().set_name(name)
            if name=='Actualizaciones':
                content.pack_start(self.update_badge,False,False,0)
        from .gui_account import account_dialog
        from .ui_components import ActionButton
        account_button=ActionButton('Cuenta','community',lambda _:account_dialog(self),'quiet');account_button.caption.set_no_show_all(True);account_button.caption.hide();account_button.get_accessible().set_name('Cuenta');account_button.set_tooltip_text('Cuenta');bar.pack_end(account_button,False,False,0)
        self.update_banner=Gtk.Box(spacing=12);self.update_banner.set_no_show_all(True);self.update_banner.get_style_context().add_class('banner');self.banner_text=label('');self.banner_action=button('Ver',lambda _:self.banner_clicked());self.update_banner.pack_start(self.banner_text,True,True,0);self.update_banner.pack_end(self.banner_action,False,False,0);root.pack_start(self.update_banner,False,False,0)
    def scrolled_page(self,name):
        scroll=self.new_scroll();box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);box.set_border_width(24);box.set_margin_end(8);scroll.add(box);self.pages.add_named(scroll,name);return box
    def card(self,parent,title=None):
        from .gui import label
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);box.get_style_context().add_class('card')
        if title:box.pack_start(label(title,'title'),False,False,0)
        parent.pack_start(box,False,False,0);return box
    def page_changed(self,*_):
        page=self.pages.get_visible_child_name();active={'library':'Biblioteca','detail':'Biblioteca','add':'Catálogo de ports','catalog':'Catálogo de ports','updates':'Actualizaciones','settings':'Ajustes','pending':'Actualizaciones'}.get(page)
        for name,control in self.nav_buttons.items():
            style=control.get_style_context();style.add_class('active') if name==active else style.remove_class('active')
    def build_library_page(self):
        from .gui import label,button
        page=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14);page.set_border_width(24);self.pages.add_named(page,'library')
        head=Gtk.Box(spacing=12);title=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3);title.pack_start(label('Biblioteca','hero'),False,False,0);self.library_count=label('','meta');title.pack_start(self.library_count,False,False,0);head.pack_start(title,False,False,0)
        self.search=Gtk.SearchEntry();self.search.set_placeholder_text('Buscar en tu biblioteca');self.search.set_width_chars(16);self.search.set_hexpand(True);self.search.connect('search-changed',lambda _:self.render());head.pack_start(self.search,True,True,12);head.pack_end(button('Agregar juegos',lambda _:self.add_hub(),True),False,False,0);page.pack_start(head,False,False,0)
        filters=Gtk.Box(spacing=8);self.platform_picker=Gtk.ComboBoxText();self.platform_picker.append('all','Todas las plataformas');self.platform_picker.set_active_id('all');self.platform_picker.connect('changed',self.filter_changed);filters.pack_start(self.platform_picker,False,False,0)
        self.type_picker=Gtk.ComboBoxText();self.type_picker.append('all','Todos los tipos')
        for key,title in TYPES:self.type_picker.append(key,title)
        self.type_picker.set_active_id('all');self.type_picker.connect('changed',lambda w:self.type_changed(w.get_active_id() or 'all'));filters.pack_start(self.type_picker,False,False,0)
        self.view_picker=Gtk.ComboBoxText()
        for key,title in [('covers','Carátulas'),('list','Lista'),('platforms','Por plataforma')]:self.view_picker.append(key,title)
        self.view_picker.set_active_id(self.view);self.view_picker.connect('changed',self.change_view);filters.pack_end(self.view_picker,False,False,0);self.select_button=button('Seleccionar',lambda _:self.toggle_selection());filters.pack_end(self.select_button,False,False,0);page.pack_start(filters,False,False,0)
        self.originals_bar=Gtk.Box(spacing=10);self.originals_bar.set_no_show_all(True);self.originals_label=label('','muted');self.originals_bar.pack_start(self.originals_label,True,True,0);self.originals_bar.pack_end(button('Revisar originales',lambda _:self.originals_dialog()),False,False,0);page.pack_start(self.originals_bar,False,False,0)
        self.library_stack=Gtk.Stack();self.library_stack.set_vexpand(True);page.pack_start(self.library_stack,True,True,0)
        self.list=Gtk.ListBox();self.list.set_selection_mode(Gtk.SelectionMode.NONE);self.list.connect('row-activated',lambda _,row:self.select_game(row.entry) if hasattr(row,'entry') else None)
        self.covers=self.poster_grid();self.platform_groups=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20)
        for name,child in [('list',self.list),('covers',self.covers),('platforms',self.platform_groups)]:
            scroll=self.new_scroll();child.set_margin_end(12);child.set_margin_bottom(12);scroll.add(child);self.library_stack.add_named(scroll,name)
        self.empty_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);self.empty_box.set_halign(Gtk.Align.CENTER);self.empty_box.set_valign(Gtk.Align.CENTER);self.empty_box.pack_start(label('No hay juegos en la biblioteca','title'),False,False,0);self.empty_box.pack_start(button('Buscar juegos instalados',lambda _:self.discover(),True),False,False,0);self.library_stack.add_named(self.empty_box,'empty')
        self.selection_bar=Gtk.Box(spacing=8);self.selection_bar.get_style_context().add_class('selection-bar');self.selection_bar.set_no_show_all(True);self.selection_label=label('');self.selection_bar.pack_start(self.selection_label,True,True,0);self.selection_bar.pack_start(button('Seleccionar visibles',lambda _:self.select_visible()),False,False,0)
        self.account=Gtk.ComboBoxText();self.accounts=find_accounts();current=active_account()
        if current in self.accounts:self.accounts.remove(current);self.accounts.insert(0,current)
        for i,path in enumerate(self.accounts):self.account.append_text('Cuenta actual' if path==current else 'Cuenta Steam '+str(i+1))
        if not self.accounts:self.account.append_text('Steam sin sesión')
        self.account.set_active(0);self.selection_bar.pack_start(self.account,False,False,0);self.add_button=button('Agregar a Steam',lambda _:self.add_to_steam(),True);self.remove_button=button('Quitar de Steam',lambda _:self.remove_from_steam(),tone='danger');self.selection_bar.pack_end(self.add_button,False,False,0);self.selection_bar.pack_end(self.remove_button,False,False,0);page.pack_end(self.selection_bar,False,False,0)
    def poster_grid(self):
        grid=Gtk.FlowBox();grid.set_selection_mode(Gtk.SelectionMode.NONE);grid.set_min_children_per_line(1);grid.set_max_children_per_line(9);grid.set_column_spacing(16);grid.set_row_spacing(20);grid.set_homogeneous(True);grid.set_valign(Gtk.Align.START);return grid
    def apply_motion(self):
        enabled=self.preferences.get('animations',True);Gtk.Settings.get_default().set_property('gtk-enable-animations',enabled)
        for stack in (self.library_stack,self.wizard_box):stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE if enabled else Gtk.StackTransitionType.NONE);stack.set_transition_duration(150 if enabled else 0)
    def shown_entries(self):return visible_entries([e for e in self.entries if e.id not in self.preferences.get('hidden_originals',[])],prefer_ports=False)
    def visible(self):
        text=self.search.get_text().casefold();entries,_=self.shown_entries()
        return sorted([e for e in entries if text in (e.name+' '+e.platform).casefold() and (self.platform_filter=='all' or self.platform_filter==e.platform) and (self.type_filter=='all' or self.type_filter==entry_type(e))],key=lambda e:e.name.casefold())
    def render(self):
        self.library_dirty=False
        from .originals import pairs
        originals=[(o,p) for o,p in pairs(self.entries) if o.id not in self.preferences.get('hidden_originals',[])]
        if originals:
            self.originals_label.set_text(str(len(originals))+' originales con un port instalado.');self.originals_bar.set_no_show_all(False);self.originals_bar.show_all();self.originals_bar.set_no_show_all(True)
        else:self.originals_bar.hide()
        from .gui import label,Poster
        self.reset_page(self.list);self.reset_page(self.covers);self.reset_page(self.platform_groups);self.new_tiles=[];entries=self.visible();total=len(self.shown_entries()[0]);self.library_count.set_text(str(total)+' juegos'+(' · '+str(len(entries))+' visibles' if len(entries)!=total else ''))
        groups={}
        for e in entries:
            row=Gtk.ListBoxRow();row.entry=e;body=Gtk.Box(spacing=16);body.set_border_width(8);row.add(body)
            if self.selection_mode:
                check=Gtk.CheckButton();check.set_active(e.id in self.checked);check.connect('toggled',self.toggle,e.id);body.pack_start(check,False,False,0)
            body.pack_start(Poster(e,find_cover(e),48,72),False,False,0);texts=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);texts.pack_start(label(e.name,'title'),False,False,0);texts.pack_start(label(e.platform+(' · En Steam' if self.in_steam(e) else ''),'meta'),False,False,0);body.pack_start(texts,True,True,0);self.list.add(row)
            if self.view=='covers':self.add_cover_card(e)
            if self.view=='platforms':
                if e.platform not in groups:groups[e.platform]=[]
                groups[e.platform].append(e)
        for platform,values in sorted(groups.items()):
            self.platform_groups.pack_start(label(platform+' · '+str(len(values)),'title'),False,False,0);grid=self.poster_grid();self.platform_groups.pack_start(grid,False,False,0)
            for e in values:self.add_cover_card(e,grid)
        if not entries and total:
            for container in (self.covers,self.list,self.platform_groups):container.add(label('No hay juegos con esos filtros.','muted'))
        self.library_stack.set_visible_child_name(self.view if total else 'empty');self.library_stack.show_all();self.update_selection()
        if getattr(self,'animate_next',False):self.animate_next=False;motion.stagger(self.new_tiles,rise=0)
    def add_cover_card(self,e,target=None):
        from .gui import label,Poster
        tile=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);tile.set_size_request(164,-1);action=Gtk.Button();action.get_style_context().add_class('poster');action.add(Poster(e,find_cover(e),164,246));action.connect('clicked',lambda _:self.select_game(e));action.set_tooltip_text(e.name)
        if e.id in self.checked:action.get_style_context().add_class('selected')
        tile.pack_start(action,False,False,0);name=label(e.name,'cover-title');name.set_line_wrap(False);name.set_ellipsize(Pango.EllipsizeMode.END);name.set_max_width_chars(19);name.set_tooltip_text(e.name);tile.pack_start(name,False,False,0);tile.pack_start(label(e.platform+(' · Steam' if self.in_steam(e) else ''),'meta'),False,False,0);(target if target is not None else self.covers).add(tile);self.new_tiles.append(tile)
    def open_library(self):
        if not self.discard_game_edits():return
        if getattr(self,'library_dirty',False):self.render()
        self.pages.set_visible_child_name('library')
    def type_changed(self,key):self.type_filter=key;self.render()
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
        self.detail_game_id=None;self.selected=e;self.show_detail(e);self.pages.set_visible_child_name('detail');self.game_play_button.grab_focus()
    def add_hub(self):self.catalog_page()
    def settings_page(self):
        from .gui import label,button
        self.reset_page(self.settings_box);self.settings_box.pack_start(label('Ajustes','hero'),False,False,0)
        from .ui_components import ActionButton
        for title,description,caption,icon,action in [('Instalaciones y carpetas','Emuladores y carpetas de juegos.','Elegir carpetas','folder',lambda _:self.installation_dialog()),('Carátulas y apariencia','Proveedor de imágenes y animaciones.','Configurar','image',lambda _:self.appearance_dialog()),('Originales y ports','Ocultar o quitar originales que ya tienen un port instalado.','Administrar originales','folder',lambda _:self.originals_dialog()),('Revisar biblioteca','Posibles copias de juegos e instalaciones alternativas.','Revisar','search',lambda _:self.conflicts_page()),('Deck Library en Steam','Abrir esta biblioteca desde Steam, a pantalla completa en modo Juego.','Agregar a Steam','steam',self.add_library_to_steam),('Configuración inicial','Volver a detectar instalaciones.','Iniciar asistente','plus',lambda _:self.start_wizard())]:
            row=Gtk.Box(spacing=16);row.get_style_context().add_class('settings-row');texts=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);texts.pack_start(label(title,'title'),False,False,0);texts.pack_start(label(description,'muted'),False,False,0);row.pack_start(texts,True,True,0);row.pack_end(ActionButton(caption,icon,action,'steam' if icon=='steam' else 'quiet'),False,False,0);self.settings_box.pack_start(row,False,False,0)
            if icon=='steam':self.settings_box.pack_start(label('Si Steam está abierto, el acceso se guarda al cerrarlo. Después buscá «Deck Library» en su biblioteca y pulsá Jugar.','meta'),False,False,0)
        self.settings_box.show_all();self.pages.set_visible_child_name('settings')
    def appearance_dialog(self):
        from .gui import label,button
        dialog=Gtk.Dialog(title='Carátulas y apariencia',transient_for=self,modal=True);dialog.set_default_size(760,600);dialog.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Guardar',Gtk.ResponseType.OK);box=dialog.get_content_area();box.set_border_width(16);box.set_spacing(12);combo,key=self.provider_fields(box);animations=Gtk.CheckButton(label='Animaciones');animations.set_active(self.preferences.get('animations',True));box.pack_start(animations,False,False,0);self.fit_dialog(dialog);dialog.show_all()
        if dialog.run()==Gtk.ResponseType.OK:
            self.preferences.update(artwork_provider=combo.get_active_id(),steamgriddb_key=key.get_text().strip(),animations=animations.get_active());save_settings(self.preferences,self.store);self.apply_motion();self.fetch_covers()
        dialog.destroy()
    def refresh_update_badges(self):
        count=len(self.pending_updates());self.update_badge.set_text(str(count));self.update_badge.set_visible(count>0)
        state=getattr(self,'update_state',{}) or {}
        if getattr(self,'update_installed',None):self.banner_text.set_text('Deck Library actualizada. Volvé a abrirla para usar la nueva versión.');self.banner_action.set_label('Volver a abrir');self.update_banner.show_all()
        elif state.get('app'):self.banner_text.set_text('Hay una nueva versión de Deck Library.');self.banner_action.set_label('Ver actualización');self.update_banner.show_all()
        else:self.update_banner.hide()
    def refresh_pending(self):
        from .service import pending_changes
        try:rows=pending_changes(self.store)
        except (OSError,ValueError):rows=[]
        if rows:
            self.pending_label.set_text(('Pendiente en Steam · '+rows[0]['description']) if len(rows)==1 else f'{len(rows)} cambios pendientes en Steam');self.pending_bar.set_no_show_all(False);self.pending_bar.show_all();self.pending_bar.set_no_show_all(True)
        else:self.pending_bar.hide()
        self.refresh_game_steam()
        return False
    def pending_details(self):
        from .gui import label,button
        from .service import pending_changes,cancel_pending
        self.reset_page(self.pending_box);self.pending_box.pack_start(button('← Biblioteca',lambda _:self.open_library()),False,False,0);self.pending_box.pack_start(label('Cambios de Steam','hero'),False,False,0);rows=pending_changes(self.store)
        for row in rows:
            card=self.card(self.pending_box,row['description']);card.pack_start(label(row['detail'],'muted'),False,False,0)
        if not rows:self.pending_box.pack_start(label('No hay cambios pendientes.','muted'),False,False,0)
        else:
            self.pending_box.pack_start(label('Se guardan al cerrar Steam.','muted'),False,False,0)
            def cancel(_):
                if not self.confirm('Descartar cambios pendientes','Se cancelan las operaciones listadas. Los juegos y los accesos que ya existen se conservan.','Descartar'):return
                try:cancel_pending(self.store);self.refresh_pending();self.pending_details();self.toast('Cambios descartados')
                except Exception as error:self.message('No se pudo descartar',str(error))
            self.pending_box.pack_start(button('Descartar estos cambios',cancel,tone='danger'),False,False,0)
        self.pending_box.show_all();self.pages.set_visible_child_name('pending')
