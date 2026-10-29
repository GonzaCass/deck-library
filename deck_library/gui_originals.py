"""Explicit management of source images after a port is installed."""
from gi.repository import Gtk,GLib
from .inline_pages import InlineDialog
from . import originals
from .installations import save_settings
from .ui_components import ActionButton,text
class OriginalsMixin:
    def originals_dialog(self,entry=None):
        dialog=InlineDialog(title='ROMs y ports instalados',transient_for=self,modal=True);dialog.set_default_size(820,600);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(16);box.set_spacing(12)
        box.pack_start(text('Juegos con una ROM y un port instalado','section-title'),False,False,0)
        box.pack_start(text('La ROM es la copia del juego de consola (ISO u otro archivo). Se agrupa con el port para no mostrar el juego dos veces. Se puede mostrar por separado o quitar esa copia; las partidas del port se conservan.','muted',85),False,False,0)
        rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);box.pack_start(rows,True,True,0)
        def render():
            self.reset_page(rows);separate=set(self.preferences.get('unlinked_originals',[]));matches=originals.pairs(self.entries)
            if entry:matches=[(o,p) for o,p in matches if o.id==entry.id or any(v.id==entry.id for v in p)]
            if not matches:rows.pack_start(text('No se encontraron ROMs asociadas a ports instalados.','muted'),False,False,0)
            for original,ports in matches:
                panel=self.card(rows,original.name);panel.pack_start(text('Port: '+', '.join(p.name for p in ports),'meta'),False,False,0);path=text(original.source,'muted',80);path.set_selectable(True);panel.pack_start(path,False,False,0);panel.pack_start(text('Se muestra por separado en la biblioteca.' if original.id in separate else 'Agrupada con el port; no aparece como juego duplicado.','meta'),False,False,0)
                actions=Gtk.FlowBox();actions.set_selection_mode(Gtk.SelectionMode.NONE);actions.set_min_children_per_line(1);actions.set_max_children_per_line(3);actions.set_column_spacing(8);actions.set_row_spacing(8);panel.pack_start(actions,False,False,0);panel.reorder_child(actions,1)
                def hide(_,o=original):
                    selected=set(self.preferences.get('unlinked_originals',[]))
                    selected.remove(o.id) if o.id in selected else selected.add(o.id)
                    self.preferences['unlinked_originals']=sorted(selected)
                    self.preferences['hidden_originals']=[i for i in self.preferences.get('hidden_originals',[]) if i!=o.id]
                    save_settings(self.preferences,self.store);self.render();render()
                def inspect(_,o=original):
                    dialog.response(Gtk.ResponseType.CLOSE);GLib.idle_add(lambda:(self.select_game(o),False)[1])
                def remove(_,o=original):
                    try:
                        files=originals.files_for(o,self.entries)
                        if not self.confirm('Enviar ROM a la papelera',o.name+'\n\n'+'\n'.join(str(p) for p in files)+'\n\nPuede hacer falta para reconstruir el port en futuras actualizaciones.','Enviar a la papelera',danger=True):return
                        originals.trash(o,self.entries);self.preferences['hidden_originals']=sorted(set(self.preferences.get('hidden_originals',[]))|{o.id});save_settings(self.preferences,self.store);self.render();render()
                    except Exception as error:self.message('No se pudo quitar la ROM',str(error))
                actions.add(ActionButton('Abrir ficha de la ROM','file',inspect,'steam-outline'))
                actions.add(ActionButton('Ocultar ROM duplicada' if original.id in separate else 'Mostrar ROM en la biblioteca','folder',hide,'violet-outline'))
                actions.add(ActionButton('Enviar a la papelera','folder',remove,'danger'))
                for child in actions.get_children():child.set_can_focus(False)
            rows.show_all()
        render();self.fit_dialog(dialog);dialog.show_all();dialog.run();dialog.destroy()
        if self.pages.get_visible_child_name()=='detail' and self.selected:self.show_detail(self.selected)
