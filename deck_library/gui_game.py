"""Game workspace: a visual overview, explicit profile selection and secondary task pages."""
import json
from gi.repository import Gtk, GLib, Pango
from . import presets, motion, profile_display as display
from .artwork import find_cover
from .ui_components import ActionButton, TaskButton, Icon, Reveal, GameBackdrop, styled, text


class GameMixin:
    def discard_game_edits(self):
        if not getattr(self,'editor_dirty',False):return True
        if not self.confirm('Cambios sin guardar','Hay opciones editadas en este juego. ¿Querés salir sin guardarlas?','Salir sin guardar'):return False
        self.editor_dirty=False
        old=self.game_pages.get_child_by_name('options')
        if old:self.game_pages.remove(old)
        return True

    def navigate_from_game(self, callback, widget=None):
        if self.discard_game_edits():callback(widget)

    def show_detail(self, entry):
        opening = self.detail_game_id != entry.id
        if opening:
            self.game_tab = 'profiles'
            self.detail_game_id = entry.id
        # Artwork/discovery must not replace a manual form while it has unsaved changes.
        if not opening and getattr(self, 'editor_dirty', False):
            self.selected = entry
            return
        self.editor_dirty = False
        self.selected = entry
        self.reset_page(self.detail)
        self.profile_dock = None
        self.profile_selection = None
        self.profile_card_box = None
        self.detail.set_spacing(12)
        self.detail.set_border_width(20)
        self.detail.get_style_context().add_class('game-workspace')
        breadcrumb = Gtk.Box(spacing=10)
        self.game_back = ActionButton('Biblioteca', 'back', lambda _: self.back_from_game())
        styled(self.game_back, 'breadcrumb')
        breadcrumb.pack_start(self.game_back, False, False, 0)
        breadcrumb.pack_start(text('/', 'meta'), False, False, 0)
        self.game_location = text('Juego', 'meta')
        breadcrumb.pack_start(self.game_location, True, True, 0)
        breadcrumb.pack_end(self.game_menu(entry), False, False, 0)
        self.detail.pack_start(breadcrumb, False, False, 0)
        self.detail.pack_start(self.game_hero(entry), False, False, 0)
        self.game_pages = Gtk.Stack()
        self.game_pages.set_homogeneous(False)
        self.game_pages.set_vexpand(True)
        self.game_pages.set_transition_duration(140 if motion.enabled() else 0)
        self.detail.pack_start(self.game_pages, True, True, 0)
        home = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.game_pages.add_named(home, 'profiles')
        self.build_game_overview(entry, home)
        tab = self.game_tab
        self.game_tab = 'profiles'
        if tab != 'profiles':
            self.open_game_section(tab, animate=False)
        self.detail.show_all()
        self.game_compact = None
        self.update_game_size()
        if opening:
            motion.fade_in(self.game_header, duration=320)
            motion.stagger(getattr(self, 'profile_cards', []), step=50, duration=260, rise=0)

    def back_from_game(self):
        if self.game_tab != 'profiles':
            self.open_game_section('profiles')
        else:
            self.open_library()

    def game_menu(self, entry):
        menu = Gtk.MenuButton()
        styled(menu, 'quiet', 'game-menu')
        body = Gtk.Box(spacing=8)
        body.pack_start(Icon('more'), False, False, 0)
        body.pack_start(text('Más opciones'), False, False, 0)
        menu.add(body)
        menu.get_accessible().set_name('Más opciones del juego')
        popover = Gtk.Popover.new(menu)
        options = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        options.set_border_width(10)
        popover.add(options)
        rows = []
        adapter = presets.adapter_for(entry)
        if adapter in ('duckstation', 'dolphin', 'eden', 'prism'):
            rows.append(('Editar ajustes manualmente', 'sliders', lambda: self.open_game_section('options')))
        if adapter in presets.REGISTRY:
            rows.extend([
                ('Importar ajustes de un archivo', 'download', lambda: self.import_game_profile(entry)),
                ('Exportar mis ajustes', 'upload', lambda: self.export_game_profile(entry)),
            ])
        from .originals import pairs
        if any(entry.id==o.id or any(entry.id==p.id for p in ports) for o,ports in pairs(self.entries)):
            rows.append(('Administrar original y port','folder',lambda:self.originals_dialog(entry)))
        rows.extend([
            ('Cambiar carátula', 'image', lambda: self.artwork_dialog(entry)),
            ('Archivos y acceso de Steam', 'folder', lambda: self.open_game_section('files')),
            ('Diagnosticar un problema', 'search', lambda: self.check(entry)),
        ])
        for caption, icon, callback in rows:
            def activate(_, action=callback):
                popover.popdown()
                action()
            action = ActionButton(caption, icon, activate)
            action.body.set_halign(Gtk.Align.START)
            options.pack_start(action, False, False, 0)
        options.show_all()
        menu.set_popover(popover)
        return menu

    def game_hero(self, entry):
        from .gui import Poster
        cover = find_cover(entry)
        backdrop = GameBackdrop(cover)
        hero = Gtk.Box(spacing=24)
        hero.set_border_width(18)
        hero.connect('draw',backdrop.draw_backdrop)
        cover_button = Gtk.Button()
        styled(cover_button, 'hero-cover')
        cover_button.add(Poster(entry, cover, 96, 144))
        cover_button.set_valign(Gtk.Align.CENTER)
        cover_button.set_tooltip_text('Cambiar carátula')
        cover_button.get_accessible().set_name('Cambiar carátula de '+entry.name)
        cover_button.connect('clicked', lambda _: self.artwork_dialog(entry))
        hero.pack_start(cover_button, False, False, 0)
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        info.set_valign(Gtk.Align.CENTER)
        platform = Gtk.Box(spacing=8)
        platform.pack_start(styled(text(entry.platform), 'platform-chip'), False, False, 0)
        origin = {'eden': 'Eden', 'wiicompiled': 'WiiCompiled', 'prism': 'Prism Launcher', 'duckstation': 'DuckStation', 'dolphin': 'Dolphin', 'project2099': 'Project-2099'}.get(presets.adapter_for(entry), 'Port' if entry.kind == 'port' else 'Aplicación')
        platform.pack_start(text(origin, 'meta'), False, False, 0)
        info.pack_start(platform, False, False, 0)
        name = text(entry.name, 'game-title', 44)
        name.set_lines(2)
        name.set_ellipsize(Pango.EllipsizeMode.END)
        name.set_tooltip_text(entry.name)
        info.pack_start(name, False, False, 0)
        actions = Gtk.Box(spacing=10)
        self.game_play_button = ActionButton('Jugar', 'play', lambda b: self.launch_from_game(entry, b), 'play')
        self.game_play_button.set_size_request(140, -1)
        actions.pack_start(self.game_play_button, False, False, 0)
        steam = ActionButton('Agregar a Steam','steam',lambda _:self.activate_game_steam(entry),'steam')
        self.game_steam_button=steam
        self.game_steam_entry=entry
        self.refresh_game_steam()
        actions.pack_start(steam, False, False, 0)
        artwork = ActionButton('Carátula', 'image', lambda _: self.artwork_dialog(entry))
        actions.pack_start(artwork, False, False, 0)
        info.pack_start(actions, False, False, 0)
        hero.pack_start(info, True, True, 0)
        self.game_header = hero
        self.game_hero_parts = (cover_button,platform,info,name,actions)
        return hero

    def update_game_size(self,*_):
        if not hasattr(self,'game_hero_parts'):return
        compact = self.get_size().height < 680
        narrow = self.get_size().width < 1050
        if getattr(self,'game_compact',None) == (compact,narrow):return
        self.game_compact = (compact,narrow)
        if self.profile_card_box:
            self.profile_card_box.set_orientation(Gtk.Orientation.VERTICAL if narrow else Gtk.Orientation.HORIZONTAL)
            self.profile_card_box.set_homogeneous(not narrow)
        cover,platform,info,name,actions = self.game_hero_parts
        for widget in (cover,platform):
            widget.set_no_show_all(compact)
            widget.set_visible(not compact)
        info.set_orientation(Gtk.Orientation.HORIZONTAL if compact else Gtk.Orientation.VERTICAL)
        info.set_child_packing(name,compact,True,0,Gtk.PackType.START)
        info.set_spacing(16 if compact else 12)
        self.game_header.set_border_width(12 if compact else 18)
        self.detail.set_border_width(12 if compact else 20)
        style=self.game_header.get_style_context()
        style.add_class('compact') if compact else style.remove_class('compact')
        self.game_header.queue_resize();self.detail.queue_resize()
        GLib.idle_add(self.reflow_game)

    def reflow_game(self):
        if not self.ui_closed:self.detail.check_resize()
        return False

    def game_steam_pending(self, entry):
        try:
            pending = json.loads((self.store.root/'pending.json').read_text())
            return entry.id in pending.get('ids', [])
        except (OSError, ValueError):
            return False

    def activate_game_steam(self, entry):
        if self.in_steam(entry) or entry.metadata.get('steam_store'):self.open_game_section('files')
        elif self.game_steam_pending(entry):self.pending_details()
        else:self.single_steam(entry)

    def refresh_game_steam(self):
        if not hasattr(self,'game_steam_button'):return
        entry=self.game_steam_entry
        control=self.game_steam_button
        registered=self.in_steam(entry) or entry.metadata.get('steam_store')
        pending=self.game_steam_pending(entry)
        control.set_label('En Steam' if registered else 'Acceso pendiente' if pending else 'Agregar a Steam')
        control.set_icon('check' if registered else 'steam')
        style=control.get_style_context()
        style.remove_class('steam');style.remove_class('steam-outline')
        style.add_class('steam-outline' if registered or pending else 'steam')
        control.set_tooltip_text('Administrar el acceso de Steam' if registered else 'Ver el cambio preparado para Steam' if pending else 'Crear un acceso directo en Steam')

    def launch_from_game(self, entry, control):
        control.set_sensitive(False)
        control.set_label('Abriendo…')
        try:
            self.play(entry)
        except Exception as error:
            control.set_label('Jugar')
            control.set_sensitive(True)
            self.message('No se pudo abrir el juego', str(error))
            return
        self.toast('Se solicitó abrir '+entry.name)
        def ready():
            if not control.in_destruction():
                control.set_label('Jugar')
                control.set_sensitive(True)
            return False
        GLib.timeout_add(1800, ready)

    def build_game_overview(self, entry, parent):
        workspace = Gtk.Box(spacing=20)
        parent.pack_start(workspace, True, True, 0)
        scroll = self.new_scroll()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_end(12)
        content.set_margin_bottom(0)
        scroll.add(content)
        workspace.pack_start(scroll, True, True, 0)
        self.profile_cards = []
        adapter = presets.adapter_for(entry)
        if entry.metadata.get('gtaiv_root'):
            content.pack_start(TaskButton('Mejoras para GTA IV', 'FusionFix y DXVK', 'sliders', lambda _: self.gtaiv_dialog(entry)), False, False, 0)
        elif adapter in presets.REGISTRY:
            self.build_profile_picker(entry, content, parent)
        else:
            panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            styled(panel, 'surface-panel')
            panel.pack_start(text('Ajustes del juego', 'section-title'), False, False, 0)
            panel.pack_start(text('Este juego se configura desde sus propias opciones.', 'muted'), False, False, 0)
            content.pack_start(panel, False, False, 0)
        task_scroll = self.new_scroll()
        task_scroll.set_size_request(248,-1)
        tasks = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        tasks.set_margin_end(12)
        tasks.pack_start(text('Administrar','rail-heading'),False,False,8)
        tasks.pack_start(TaskButton('Controles', 'Mando e idioma', 'controller', lambda _: self.open_game_section('controls'), 'amber'),False,False,0)
        if entry.platform == 'Switch':
            tasks.pack_start(TaskButton('Contenido', 'Updates, DLC y mods', 'folder', lambda _: self.open_game_section('content'), 'cyan'),False,False,0)
        else:
            tasks.pack_start(TaskButton('Archivos y acceso', 'Ruta y acceso de Steam', 'folder', lambda _: self.open_game_section('files'), 'cyan'),False,False,0)
        if adapter in ('eden','duckstation','dolphin','prism'):
            tasks.pack_start(TaskButton('Ajustes manuales','Resolución, gráficos y más','sliders',lambda _:self.open_game_section('options'),'violet-outline'),False,False,0)
        task_scroll.add(tasks)
        workspace.pack_end(task_scroll,False,False,0)

    def profile_card(self, profile, choose, favourite=False):
        card = Gtk.Button()
        styled(card, 'profile-card')
        card.profile_id = profile['id']
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        top = Gtk.Box(spacing=8)
        icon_name, description = display.intent(profile)
        top.pack_start(styled(Icon(icon_name,22),'violet-icon'), False, False, 0)
        title = text(display.title(profile), 'profile-title', 26)
        title.set_lines(2)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        top.pack_start(title, True, True, 0)
        card.selection_icon = Icon('radio',18)
        top.pack_end(card.selection_icon, False, False, 0)
        body.pack_start(top, False, False, 0)
        subtitle = text(description,'muted',40)
        subtitle.set_lines(2)
        subtitle.set_ellipsize(Pango.EllipsizeMode.END)
        body.pack_start(subtitle, True, True, 0)
        values = display.highlights(profile)
        summary = ' · '.join(value for _,value in values)
        body.pack_start(text(summary or profile['author'], 'profile-spec', 40), False, False, 0)
        state = display.TEST_STATES[profile['tested']['status']]+(' · Favorito' if favourite else '')
        body.pack_start(text(state, 'good' if profile['tested']['status']!='proposal' else 'meta', 40), False, False, 0)
        card.rating_label=text('★ Sin valoraciones','rating',40)
        body.pack_start(card.rating_label,False,False,0)
        card.add(body)
        card.get_accessible().set_name(display.title(profile)+' · '+description+' · '+state)
        card.set_tooltip_text(profile['name']+'\n'+profile['objective'])
        card.connect('clicked',lambda _:choose(profile))
        self.profile_cards.append(card)
        return card

    def build_profile_picker(self, entry, content, parent):
        profiles = presets.recommended(entry, self.store)
        best = presets.best_for(entry, self.store)
        heading = Gtk.Box(spacing=12)
        heading.pack_start(text('Ajustes del juego','section-title'), True, True, 0)
        heading.pack_end(ActionButton('Comunidad','community',lambda _:self.community_dialog(entry),'violet-outline'), False, False, 0)
        heading.pack_end(ActionButton('Compartir mis ajustes','upload',lambda _:self.community_dialog(entry,mode='publish')),False,False,0)
        content.pack_start(heading, False, False, 0)
        self.profile_selection = None
        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        details.set_border_width(12)
        styled(details,'change-details')
        provenance = text('', 'meta', 100)
        details.pack_start(provenance,False,False,0)
        notes = text('', 'muted',100)
        details.pack_start(notes,False,False,0)
        changes = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        details.pack_start(changes,False,False,0)
        self.profile_disclosure = Reveal('Ver cambios', details)
        self.profile_feedback = styled(Gtk.Box(spacing=10),'profile-feedback')
        self.profile_feedback_icon = Icon('sliders',18)
        self.profile_feedback.pack_start(self.profile_feedback_icon,False,False,0)
        self.profile_status = text('','muted',90)
        self.profile_feedback.pack_start(self.profile_status,True,True,0)
        # Dock stays on screen even when the list of profiles or changes is long.
        dock = styled(Gtk.Box(spacing=12),'apply-dock')
        dock_words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3)
        self.profile_dock_title = text('Elegí un perfil','dock-title')
        self.profile_dock_note = text('La configuración actual se conserva hasta aplicar.','meta',60)
        dock_words.pack_start(self.profile_dock_title,False,False,0)
        dock_words.pack_start(self.profile_dock_note,False,False,0)
        dock.pack_start(dock_words,True,True,0)
        self.profile_restore = ActionButton('Deshacer','undo',lambda _:self.restore_game_profile(entry))
        self.profile_restore.set_tooltip_text('Restaurar la configuración anterior al último ajuste')
        self.profile_restore.set_sensitive((self.store.root/'applied-presets'/(entry.id+'.json')).exists())
        self.profile_apply = ActionButton('Aplicar ajustes','sliders',lambda _:self.apply_game_profile(entry),'violet')
        self.profile_apply.set_sensitive(False)
        dock.pack_end(self.profile_apply,False,False,0)
        dock.pack_end(self.profile_restore,False,False,0)
        parent.pack_end(dock,False,False,0)
        self.profile_dock = dock
        self.fetch_game_ratings(entry)

        def choose(profile):
            self.profile_selection = profile
            self.profile_choice[entry.id] = profile['id']
            for card in self.profile_cards:
                active = card.profile_id == profile['id']
                style = card.get_style_context()
                style.add_class('chosen') if active else style.remove_class('chosen')
                card.selection_icon.name = 'check' if active else 'radio'
                card.selection_icon.queue_draw()
                card.get_accessible().set_description('Seleccionado' if active else 'Seleccionar perfil')
            self.profile_dock_title.set_text(display.title(profile))
            provenance.set_text(profile['author']+' · '+display.TEST_STATES[profile['tested']['status']]+' · '+', '.join(profile['adapter']['versions']))
            notes.set_text(profile.get('notes',''))
            notes.set_visible(bool(profile.get('notes')))
            self.reset_page(changes)
            self.profile_apply.get_style_context().remove_class('applied')
            try:
                _, differences = display.differences(entry,profile,self.preferences.get('eden_config') or None)
                from .gui_tools import SETTING_LABELS
                adapter = presets.adapter_for(entry)
                for key,old,new in differences:
                    option = key.split('.',1)[1]
                    name = SETTING_LABELS.get(adapter,{}).get(option,(key,''))[0]
                    row = Gtk.Box(spacing=12)
                    left = text(name,limit=42)
                    row.pack_start(left,True,True,0)
                    row.pack_end(text(display.value_text(adapter,option,old)+' → '+display.value_text(adapter,option,new),'meta',46),False,False,0)
                    changes.pack_start(row,False,False,0)
                count = len(differences)
                self.profile_status.set_text(f'{count} ajustes por cambiar. Se usan al volver a abrir el juego.' if count else 'Este perfil coincide con los ajustes guardados.')
                self.profile_dock_note.set_text('Se guarda un respaldo antes de aplicar.' if count else 'No hay cambios por aplicar.')
                self.profile_apply.set_label('Aplicar ajustes' if count else 'Aplicado')
                self.profile_apply.set_icon('sliders' if count else 'check')
                self.profile_apply.set_sensitive(bool(count) and not getattr(self,'profile_job',False))
                self.profile_feedback_icon.name = 'sliders' if count else 'check'
                self.profile_feedback_icon.queue_draw()
                self.profile_disclosure.control.set_label(f'Ver los {count} cambios' if count else 'Ver detalles del perfil')
                if not count:self.profile_apply.get_style_context().add_class('applied')
            except Exception as error:
                self.profile_status.set_text('Falta completar la configuración: '+str(error))
                self.profile_dock_note.set_text('Completá los datos del acceso para aplicar ajustes.')
                self.profile_apply.set_sensitive(False)
                changes.pack_start(ActionButton('Completar datos del juego','file',lambda _:self.manual(entry),'steam-outline'),False,False,0)
            changes.show_all()
        self.refresh_profile_preview = lambda: choose(self.profile_selection) if self.profile_selection else None
        if profiles:
            cards = Gtk.Box(spacing=12)
            self.profile_card_box = cards
            cards.set_homogeneous(True)
            for profile in profiles[:3]:
                cards.pack_start(self.profile_card(profile,choose,profile['id']==best),True,True,0)
            content.pack_start(cards,False,False,0)
            if len(profiles)>3:
                extra = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10)
                for profile in profiles[3:]:extra.pack_start(self.profile_card(profile,choose,profile['id']==best),False,False,0)
                content.pack_start(Reveal('Personalizados y otras opciones ('+str(len(profiles)-3)+')',extra),False,False,0)
            content.pack_start(self.profile_feedback,False,False,0)
            content.pack_start(self.profile_disclosure,False,False,0)
            selected = self.profile_choice.get(entry.id,best)
            choose(next((value for value in profiles if value['id']==selected),profiles[0]))
        else:
            empty = styled(Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10),'surface-panel')
            empty.pack_start(text('Todavía no hay un perfil para este juego.','title'),False,False,0)
            row = Gtk.Box(spacing=10)
            row.pack_start(ActionButton('Buscar en la comunidad','community',lambda _:self.community_dialog(entry),'violet-outline'),False,False,0)
            row.pack_start(ActionButton('Importar archivo','download',lambda _:self.import_game_profile(entry)),False,False,0)
            empty.pack_start(row,False,False,0)
            if presets.adapter_for(entry) in ('eden','duckstation','dolphin','prism'):
                empty.pack_start(ActionButton('Editar ajustes manualmente','sliders',lambda _:self.open_game_section('options')),False,False,0)
            content.pack_start(empty,False,False,0)
            self.profile_dock_title.set_text('Sin perfil seleccionado')
            self.profile_dock_note.set_text('Podés importar uno o editar las opciones disponibles.')

    def fetch_game_ratings(self,entry):
        import threading,time
        from .community import Client
        from .gui_community import rating_caption
        if not hasattr(self,'community_rating_cache'):self.community_rating_cache={};self.community_rating_fetching=set()
        def paint(values):
            if self.ui_closed or not self.selected or self.selected.id!=entry.id:return False
            for card in self.profile_cards:
                value=next((v for v in values if v['preset']['id']==card.profile_id or 'community-'+v['id']==card.profile_id),None)
                if value:card.rating_label.set_text(rating_caption(value))
            return False
        cached=self.community_rating_cache.get(entry.id)
        if cached and time.monotonic()-cached[0]<300:
            GLib.idle_add(paint,cached[1]);return
        if entry.id in self.community_rating_fetching or self.preferences.get('community_ratings',True) is False:return
        self.community_rating_fetching.add(entry.id)
        def work():
            try:values=Client(self.store,self.preferences.get('community_url','https://presets.jokerlan.xyz')).search(entry)
            except Exception:values=[]
            self.community_rating_cache[entry.id]=(time.monotonic(),values);self.community_rating_fetching.discard(entry.id);GLib.idle_add(paint,values)
        threading.Thread(target=work,daemon=True).start()

    def apply_game_profile(self, entry):
        value = self.profile_selection
        if not value or not self.profile_apply.get_sensitive() or getattr(self,'profile_job',False):return
        self.profile_job = True
        owner = self.profile_dock
        cards = list(self.profile_cards)
        for card in cards:card.set_sensitive(False)
        self.profile_apply.set_sensitive(False)
        self.profile_apply.set_label('Aplicando…')
        self.profile_restore.set_sensitive(False)
        self.profile_status.set_text('Guardando respaldo y ajustes…')
        # The next GTK frame paints the busy state before the local atomic write.
        def apply_():
            error = None
            try:
                presets.apply(entry,value,self.store,self.preferences.get('eden_config') or None)
            except Exception as exc:
                error = str(exc)
            self.profile_job = False
            if self.ui_closed:return False
            if getattr(self,'profile_dock',None) is not owner:
                if getattr(self,'profile_selection',None):
                    self.refresh_profile_preview()
                    self.profile_restore.set_sensitive((self.store.root/'applied-presets'/(self.selected.id+'.json')).exists())
                if not error:self.toast('Ajustes aplicados a '+entry.name)
                else:self.set_status('No se pudieron aplicar los ajustes de '+entry.name+': '+error)
                return False
            for card in cards:card.set_sensitive(True)
            if error:
                self.profile_status.set_text('No se pudo aplicar: '+error)
                self.profile_apply.set_label('Reintentar')
                self.profile_apply.set_sensitive(True)
                self.profile_restore.set_sensitive((self.store.root/'applied-presets'/(entry.id+'.json')).exists())
            else:
                self.refresh_profile_preview()
                self.profile_status.set_text('Ajustes guardados. Se usan al volver a abrir el juego.')
                self.profile_restore.set_sensitive(True)
                self.toast('Ajustes aplicados · respaldo guardado')
                motion.fade_in(self.profile_feedback,duration=240)
            return False
        GLib.timeout_add(40,apply_)

    def restore_game_profile(self, entry):
        if getattr(self,'profile_job',False):return
        try:
            presets.restore(entry,self.store)
            self.profile_restore.set_sensitive(False)
            self.refresh_profile_preview()
            self.profile_status.set_text('Se restauró la configuración anterior.')
            self.toast('Configuración anterior restaurada')
        except Exception as error:
            self.profile_status.set_text('No se pudo restaurar: '+str(error))

    def open_game_section(self, section, animate=True):
        entry = self.selected
        if section != 'options' and not self.discard_game_edits():return
        if not self.game_pages.get_child_by_name(section):
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
            self.game_pages.add_named(page,section)
            titles = {'options':'Editar ajustes','controls':'Controles e idioma','files':'Archivos y acceso','content':'Contenido del juego'}
            heading = Gtk.Box(spacing=12)
            page.back_control = ActionButton('Volver al juego','back',lambda _:self.open_game_section('profiles'))
            heading.pack_start(page.back_control,False,False,0)
            heading.pack_start(text(titles.get(section,'Juego'),'section-title'),True,True,0)
            page.pack_start(heading,False,False,0)
            if section == 'options':self.build_options(entry,page)
            else:
                scroll = self.new_scroll()
                body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
                body.set_margin_end(12)
                scroll.add(body)
                page.pack_start(scroll,True,True,0)
                {'controls':self.build_game_controls,'files':self.build_game_files,'content':self.build_game_content}.get(section,self.build_game_files)(entry,body)
            page.show_all()
        self.game_pages.set_transition_type(Gtk.StackTransitionType.NONE if not motion.enabled() or not animate else Gtk.StackTransitionType.SLIDE_RIGHT if section=='profiles' else Gtk.StackTransitionType.SLIDE_LEFT)
        self.game_pages.set_visible_child_name(section)
        self.game_tab = section
        self.game_location.set_text({'profiles':'Juego','options':'Ajustes manuales','controls':'Controles e idioma','files':'Archivos y acceso','content':'Contenido del juego'}.get(section,'Juego'))
        self.game_back.set_label('Biblioteca' if section=='profiles' else 'Juego')
        if animate:
            page=self.game_pages.get_child_by_name(section)
            if section=='profiles':self.game_play_button.grab_focus()
            elif hasattr(page,'back_control'):page.back_control.grab_focus()

    def build_game_controls(self, entry, body):
        steam = self.in_steam(entry)
        panel = self.card(body,'Mando de Steam')
        if entry.metadata.get('steam_store'):
            panel.pack_start(text('Configurá el mando desde la ficha del juego en Steam.','muted'),False,False,0)
            return
        panel.pack_start(text(self.controller_summary(entry) if steam else 'Agregá este juego a Steam para asignarle un perfil de mando.','muted',85),False,False,0)
        panel.pack_start(ActionButton('Asignar perfil de mando' if steam else 'Agregar a Steam','controller' if steam else 'steam',lambda _:self.fix_controllers(entry) if steam else self.single_steam(entry),'amber'),False,False,0)
        if entry.kind == 'emulated':
            panel=self.card(body,'Emulador')
            panel.pack_start(text('Idioma del juego y configuración de botones.','muted'),False,False,0)
            panel.pack_start(ActionButton('Configurar emulador','sliders',lambda _:self.emulator_dialog(entry),'violet-outline'),False,False,0)
        if entry.platform == 'Minecraft':
            body.pack_start(TaskButton('Controles de Minecraft','Ver teclas y layouts guardados','controller',lambda _:self.layout_dialog(entry),'amber'),False,False,0)

    def build_game_files(self, entry, body):
        for caption,value in [('Archivo del juego',entry.source or entry.command[0]),('Comando de inicio',' '.join(entry.command))]:
            panel=self.card(body,caption)
            value=text(value,'muted',100)
            value.set_selectable(True)
            panel.pack_start(value,False,False,0)
        actions=Gtk.Box(spacing=10)
        actions.pack_start(ActionButton('Editar acceso','file',lambda _:self.manual(entry)),False,False,0)
        actions.pack_start(ActionButton('Diagnóstico','search',lambda _:self.check(entry)),False,False,0)
        body.pack_start(actions,False,False,0)
        if self.in_steam(entry):
            row=Gtk.Box(spacing=10)
            row.pack_start(ActionButton('Carátulas de Steam','image',lambda _:self.steam_art_dialog(entry),'steam-outline'),False,False,0)
            row.pack_start(ActionButton('Quitar acceso de Steam','undo',lambda _:self.remove_from_steam([entry]),'danger'),False,False,0)
            body.pack_start(row,False,False,0)

    def build_game_content(self, entry, body):
        body.pack_start(TaskButton('Administrar contenido','Juego base, actualizaciones, DLC y mods','folder',lambda _:self.content_dialog(entry),'cyan'),False,False,0)
        panel=self.card(body,'Mods')
        row=Gtk.Box(spacing=14)
        row.pack_start(text('Usar los mods instalados'),True,True,0)
        toggle=Gtk.Switch()
        toggle.set_active(entry.mods)
        toggle.connect('notify::active',lambda w,_:self.set_mods(w,entry))
        row.pack_end(toggle,False,False,0)
        panel.pack_start(row,False,False,0)
