"""Controller-friendly home: one featured game and a horizontal collection."""
import pathlib,shutil
from gi.repository import Gtk,GLib,Pango
from .ui_components import ActionButton,text,styled,badge
from .library_view import entry_type
from .artwork import find_cover
from .gui_console import ConsoleBackdrop

HOME_LIMIT=16

class HomeMixin:
    def home_page(self):
        if not self.discard_game_edits():return
        from .gui_widgets import Poster
        from . import history
        box=self.home_box;scroll=box.get_ancestor(Gtk.ScrolledWindow)
        refreshing=self.pages.get_visible_child_name()=='home'
        position=scroll.get_vadjustment().get_value() if refreshing else 0
        horizontal=getattr(self,'home_rail',None)
        rail_position=horizontal.get_hadjustment().get_value() if refreshing and horizontal else 0
        focus=self.get_focus();focused_id=getattr(focus,'home_game_id',None)
        focus_role=getattr(focus,'home_role',None) if refreshing else None
        returning=self.pages.get_visible_child_name()=='detail' and getattr(self,'detail_origin','library')=='home'
        restore_id=getattr(self,'home_focus_id',None) if returning else focused_id
        selected_id=restore_id or (getattr(getattr(self,'home_entry',None),'id',None) if refreshing else None)
        self.reset_page(box);box.set_border_width(0);box.set_margin_end(0);box.set_spacing(0);box.set_vexpand(True)
        styled(box,'console-home');entries=self.shown_entries()[0];played=history.load(self.store)
        entries=sorted(entries,key=lambda e:(-played.get(e.id,0),e.name.casefold()))
        self.home_entries={e.id:e for e in entries};self.home_targets={};self.home_entry=None
        hero=Gtk.Overlay();self.home_hero=hero;self.home_backdrop=ConsoleBackdrop();hero.add(self.home_backdrop)
        content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);self.home_hero_content=content
        content.set_margin_start(30);content.set_margin_end(30);content.set_margin_top(20);content.set_margin_bottom(18)
        content.set_valign(Gtk.Align.CENTER);hero.add_overlay(content)
        self.home_eyebrow=text('Próxima partida','console-eyebrow');content.pack_start(self.home_eyebrow,False,False,0)
        self.home_title=text('Todo listo para empezar','console-title',34)
        self.home_title.set_width_chars(1);self.home_title.set_lines(2);self.home_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.home_title.set_halign(Gtk.Align.START);content.pack_start(self.home_title,False,False,0)
        self.home_badges=Gtk.Box(spacing=8);content.pack_start(self.home_badges,False,False,0)
        self.home_actions=Gtk.Box(spacing=10);content.pack_start(self.home_actions,False,False,2)
        self.home_play=styled(ActionButton('Jugar','play',lambda _:self.play_home_game()),'console-play')
        self.home_play.home_role='play';self.home_actions.pack_start(self.home_play,False,False,0)
        self.home_details=styled(ActionButton('Ficha del juego','sliders',lambda _:self.select_game(self.home_entry) if self.home_entry else None),'console-secondary')
        self.home_details.home_role='details';self.home_details.set_tooltip_text('Abrir ficha del juego');self.home_details.get_accessible().set_name('Abrir ficha del juego')
        self.home_actions.pack_start(self.home_details,False,False,0)
        self.home_favorite=styled(ActionButton('','star',lambda _:self.favorite_home_game()),'console-round')
        self.home_favorite.home_role='favorite';self.home_actions.pack_start(self.home_favorite,False,False,0)
        box.pack_start(hero,False,False,0)
        section=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);section.set_margin_start(28);section.set_margin_end(28);section.set_margin_top(6)
        heading=Gtk.Box(spacing=14);heading.pack_start(text('Mis juegos','section-title'),False,False,0)
        heading.pack_start(text(f'{len(entries)} juegos · por último jugado','meta'),True,True,0);section.pack_start(heading,False,False,0)
        self.home_rail=self.new_scroll();self.home_rail.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.NEVER)
        self.home_rail.set_overlay_scrolling(True);self.home_rail.set_min_content_height(232)
        rail=Gtk.Box(spacing=14);rail.set_border_width(4);self.home_rail.add(rail)
        from .port_patterns import entry_display_title
        for entry in entries[:HOME_LIMIT]:
            shown=entry_display_title(entry)
            control=styled(Gtk.Button(),'console-card');control.home_game_id=entry.id
            control.set_tooltip_text(shown);control.get_accessible().set_name(shown)
            body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            body.pack_start(Poster(entry,find_cover(entry),148,222,overlay=True,steam=self.in_steam(entry),favorite=self.is_favorite(entry)),False,False,0)
            control.add(body);control.connect('clicked',lambda _,e=entry:self.select_game(e))
            control.connect('focus-in-event',lambda _,event,e=entry:self.focus_home_game(e))
            rail.pack_start(control,False,False,0);self.home_targets[entry.id]=control
        all_games=styled(ActionButton('Ver toda la biblioteca','library',lambda _:self.open_library()),'console-all')
        all_games.set_size_request(148,222);all_games.caption.set_line_wrap(True);all_games.caption.set_max_width_chars(12)
        all_games.body.set_orientation(Gtk.Orientation.VERTICAL);all_games.body.set_spacing(14);rail.pack_start(all_games,False,False,0)
        section.pack_start(self.home_rail,False,False,0);box.pack_start(section,True,True,0)
        utility=styled(Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8),'console-utility')
        utility.set_margin_start(28);utility.set_margin_end(28);utility.set_margin_top(12);utility.set_margin_bottom(12)
        bar=Gtk.Box(spacing=10);counts=Gtk.Box(spacing=8);self.home_counts={}
        ports=[e for e in entries if entry_type(e)=='port']
        for caption,value in [('Juegos',len(entries)),('Ports instalados',len(ports)),('Plataformas',len({e.platform for e in entries if e.platform})),('Actualizaciones',len(self.pending_updates()))]:
            card=styled(Gtk.Box(spacing=6),'summary-card')
            amount=text(str(value),'summary-count');card.pack_start(amount,False,False,0);card.pack_start(text(caption,'meta'),False,False,0)
            counts.pack_start(card,False,False,0);self.home_counts[caption]=amount
        bar.pack_start(counts,False,False,0)
        actions=Gtk.Box(spacing=10)
        try:actions.pack_start(text(f'{shutil.disk_usage(pathlib.Path.home()).free/(1024**3):.1f} GiB libres','meta'),False,False,0)
        except OSError:pass
        bar.pack_end(actions,False,False,0);utility.pack_start(bar,False,False,0);box.pack_end(utility,False,False,0)
        chosen=self.home_entries.get(selected_id) or next(iter(entries),None)
        if chosen:self.feature_home_game(chosen)
        else:
            self.home_play.set_label('Conseguir juegos');self.home_play.set_icon('plus')
            self.home_favorite.set_no_show_all(True);self.home_favorite.hide();self.home_details.set_no_show_all(True);self.home_details.hide()
            self.home_badges.pack_start(text('Instalar un port o elegir carpetas de juegos.','meta'),False,False,0)
        box.show_all();scroll.show_all();self.resize_console_home()
        self.pages.set_visible_child_name('home');self.refresh_layout()
        def restore():
            if self.ui_closed or self.pages.get_visible_child_name()!='home':return False
            target=self.home_targets.get(restore_id)
            if target is None and focus_role:target={'play':self.home_play,'favorite':self.home_favorite,'details':self.home_details}.get(focus_role)
            if target is None and not refreshing:target=self.home_play
            if target:
                target.grab_focus();self.mark_controller_focus(self,target)
                if returning:self.reveal_focus(target)
            if not returning:
                scroll.get_vadjustment().set_value(position);self.home_rail.get_hadjustment().set_value(rail_position)
            return False
        GLib.idle_add(restore)

    def resize_console_home(self):
        if not hasattr(self,'home_hero'):return
        width,height=self.get_size().width,self.get_size().height
        compact=width<1050 or height<680
        chars=26 if compact else 34
        if self.home_title.get_max_width_chars()!=chars:self.home_title.set_max_width_chars(chars)
        natural=self.home_hero_content.get_preferred_height_for_width(max(300,width-60))[1]+38
        hero_height=max(290 if height<=820 else 330,natural)
        if self.home_hero.get_size_request().height!=hero_height:self.home_hero.set_size_request(-1,hero_height)

    def feature_home_game(self,entry):
        from . import history
        from .port_patterns import entry_display_title,entry_port_project
        shown=entry_display_title(entry);port_project=entry_port_project(entry)
        self.home_entry=entry;self.home_title.set_text(shown);self.home_title.set_tooltip_text(shown)
        self.home_eyebrow.set_text('Continuar jugando' if entry.id in history.load(self.store) else 'Próxima partida')
        self.home_backdrop.platform=entry.platform or ''
        self.home_backdrop.set_cover(find_cover(entry));self.reset_page(self.home_badges)
        kind_label={'port':'Port · '+port_project if port_project else 'Port','emulator':'Emulador','minecraft':'Minecraft','steam':'Steam'}.get(entry_type(entry),'Juego')
        if entry.platform and entry.platform.casefold()!=kind_label.casefold() and not (entry_type(entry)=='port' and entry.platform.casefold()=='linux'):
            self.home_badges.pack_start(badge(entry.platform,'violet'),False,False,0)
        self.home_badges.pack_start(badge(kind_label,'blue'),False,False,0)
        pending=entry.metadata.get('configured') is False
        self.home_badges.pack_start(badge('Preparación pendiente' if pending else 'En la biblioteca','yellow' if pending else 'green'),False,False,0)
        self.home_play.set_label('Preparar' if pending else 'Jugar');self.home_play.set_icon('sliders' if pending else 'play')
        favorite=self.is_favorite(entry);self.home_favorite.set_icon('star-fill' if favorite else 'star')
        self.home_favorite.set_tooltip_text('Quitar de favoritos' if favorite else 'Marcar como favorito')
        self.home_favorite.get_accessible().set_name('Quitar de favoritos' if favorite else 'Marcar como favorito')
        self.home_favorite.get_accessible().set_description(entry.name)
        for identifier,control in self.home_targets.items():
            context=control.get_style_context();context.add_class('featured') if identifier==entry.id else context.remove_class('featured')
        self.home_badges.show_all()

    def focus_home_game(self,entry):
        if self.home_entry is None or self.home_entry.id!=entry.id:self.feature_home_game(entry)
        self.home_focus_id=entry.id;return False

    def favorite_home_game(self):
        if self.home_entry:self.toggle_favorite(self.home_entry);self.feature_home_game(self.home_entry)

    def play_home_game(self):
        entry=self.home_entry
        if not entry:self.catalog_page();return
        if entry.metadata.get('configured') is False:self.select_game(entry);return
        self.play(entry)
