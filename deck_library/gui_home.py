"""A compact collection overview backed by the same library and update state as the other tabs."""
import pathlib,shutil
from gi.repository import Gtk,GLib,Pango
from .ui_components import ActionButton,Icon,text,styled
from .library_view import entry_type

class HomeMixin:
    def home_page(self):
        if not self.discard_game_edits():return
        from .gui import Poster
        from .artwork import find_cover
        box=self.home_box;scroll=box.get_ancestor(Gtk.ScrolledWindow)
        refreshing=self.pages.get_visible_child_name()=='home';position=scroll.get_vadjustment().get_value() if refreshing else 0
        focus=self.get_focus();focused_id=getattr(focus,'home_game_id',None);focus_token=self.control_focus_token() if refreshing else None
        returning=self.pages.get_visible_child_name()=='detail' and getattr(self,'detail_origin','library')=='home'
        restore_id=getattr(self,'home_focus_id',None) if returning else focused_id
        self.reset_page(box)
        header=Gtk.Box(spacing=10);header.pack_start(text('Inicio','hero'),True,True,0)
        storage=styled(Gtk.Box(spacing=8),'home-storage')
        try:
            drive=shutil.disk_usage(pathlib.Path.home());free=drive.free/(1024**3)
            storage.pack_start(Icon('folder',18),False,False,0);storage.pack_start(text(f'{free:.1f} GiB libres','meta'),False,False,0);storage.set_tooltip_text('Espacio disponible en la unidad de la carpeta personal')
        except OSError:storage.pack_start(text('Espacio no disponible','meta'),False,False,0)
        header.pack_end(storage,False,False,0)
        actions=Gtk.Box(spacing=8)
        self.home_support_button=ActionButton('Solicitudes y reportes','community',lambda _:self.support_page(),'violet');actions.pack_start(self.home_support_button,False,False,0)
        if self.owner_verified():
            actions.pack_start(ActionButton('Bandeja de entrada','upload',lambda _:self.owner_requests_page(),'cyan'),False,False,0)
        actions.pack_start(ActionButton('Actualizar biblioteca','refresh',self.rescan_library,'steam-outline'),False,False,0)
        self.pin_page_header(box,header,actions)
        entries=self.shown_entries()[0];ports=[e for e in entries if entry_type(e)=='port' and not (pathlib.Path(e.cwd)/'deck_library/gui_shell.py').is_file()];platforms={e.platform for e in entries if e.platform};waiting=len(self.pending_updates())
        counts=Gtk.Box(spacing=12,homogeneous=True);self.home_counts={}
        for caption,value,icon in [('Juegos',len(entries),'library'),('Ports instalados',len(ports),'controller'),('Plataformas',len(platforms),'monitor'),('Actualizaciones',waiting,'download')]:
            card=styled(Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6),'summary-card');top=Gtk.Box(spacing=8);top.pack_start(text(caption,'meta'),True,True,0);top.pack_end(Icon(icon,18),False,False,0);card.pack_start(top,False,False,0);value_label=text(str(value),'summary-count');card.pack_start(value_label,False,False,0);counts.pack_start(card,True,True,0);self.home_counts[caption]=value_label
        box.pack_start(counts,False,False,0)
        self.home_targets={}
        def new_grid():
            grid=Gtk.FlowBox();grid.set_selection_mode(Gtk.SelectionMode.NONE);grid.set_min_children_per_line(1);grid.set_max_children_per_line(6);grid.set_homogeneous(True);grid.set_column_spacing(14);grid.set_row_spacing(14);return grid
        from . import history
        recent=[e for e in history.recent(entries,self.store,6)]
        if recent:
            recent_head=styled(Gtk.Box(spacing=12),'section-row');recent_head.pack_start(text('Continuar jugando','section-title'),True,True,0);box.pack_start(recent_head,False,False,0)
            recent_grid=new_grid();box.pack_start(recent_grid,False,False,0)
        heading=styled(Gtk.Box(spacing=12),'section-row');heading.pack_start(text('Ports instalados','section-title'),True,True,0);box.pack_start(heading,False,False,0)
        grid=new_grid();self.home_port_grid=grid;box.pack_start(grid,False,False,0)
        featured=ports
        def add_tile(target,entry):
            control=styled(Gtk.Button(),'summary-game');control.set_size_request(152,-1);control.set_halign(Gtk.Align.CENTER);control.get_accessible().set_name('Ver '+entry.name);control.set_tooltip_text(entry.name);control.home_game_id=entry.id
            body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);cover=Poster(entry,find_cover(entry),150,225);cover.set_halign(Gtk.Align.CENTER);body.pack_start(cover,False,False,0);info=styled(Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5),'port-card-content');name=text(entry.name,'title',14);name.set_lines(2);name.set_ellipsize(Pango.EllipsizeMode.END);info.pack_start(name,False,False,0)
            for caption in (entry.platform,'Preparación pendiente' if entry.metadata.get('configured') is False else 'Instalado'):
                meta=text(caption,'meta',16);meta.set_lines(1);meta.set_ellipsize(Pango.EllipsizeMode.END);info.pack_start(meta,False,False,0)
            body.pack_start(info,True,True,0);control.add(body);control.connect('clicked',lambda _,e=entry:self.select_game(e));target.add(control);control.get_parent().set_can_focus(False);self.home_targets.setdefault(entry.id,control)
        for entry in recent:add_tile(recent_grid,entry)
        for entry in sorted(featured,key=lambda e:e.name.casefold()):add_tile(grid,entry)
        if not featured:
            grid.add(ActionButton('Abrir catálogo de ports','plus',lambda _:self.catalog_page(),'quiet'))
        box.show_all();scroll=box.get_ancestor(Gtk.ScrolledWindow)
        if scroll:scroll.show_all()
        self.pages.set_visible_child_name('home');self.refresh_layout()
        def restore():
            if self.ui_closed or self.pages.get_visible_child_name()!='home':return False
            target=self.home_targets.get(restore_id)
            if target:
                target.grab_focus();self.mark_controller_focus(self,target)
                if returning:self.reveal_focus(target)
            elif refreshing:self.restore_control_focus(focus_token)
            if not returning:scroll.get_vadjustment().set_value(position)
            return False
        GLib.idle_add(restore)
