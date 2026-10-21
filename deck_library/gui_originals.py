"""Explicit management of source images after a port is installed."""
from gi.repository import Gtk,GLib
from .inline_pages import InlineDialog
from . import originals
from .installations import save_settings
from .ui_components import ActionButton,text
class OriginalsMixin:
    def originals_dialog(self,entry=None):
        dialog=InlineDialog(title='Originales y ports',transient_for=self,modal=True);dialog.set_default_size(820,600);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(16);box.set_spacing(12)
        box.pack_start(text('Originales con un port instalado','section-title'),False,False,0)
        box.pack_start(text('El port y su ROM comparten una ficha. Se puede abrir el original, mostrarlo por separado o conservarlo para futuras actualizaciones.','muted',85),False,False,0)
        rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);box.pack_start(rows,True,True,0)
        def render():
            self.reset_page(rows);separate=set(self.preferences.get('unlinked_originals',[]));matches=originals.pairs(self.entries)
            if entry:matches=[(o,p) for o,p in matches if o.id==entry.id or any(v.id==entry.id for v in p)]
            if not matches:rows.pack_start(text('No hay originales asociados a ports instalados.','muted'),False,False,0)
            for original,ports in matches:
                panel=self.card(rows,original.name);panel.pack_start(text('Port: '+', '.join(p.name for p in ports),'meta'),False,False,0);path=text(original.source,'muted',80);path.set_selectable(True);panel.pack_start(path,False,False,0)
                actions=Gtk.Box(spacing=8);panel.pack_start(actions,False,False,0)
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
                        if not self.confirm('Enviar original a la papelera',o.name+'\n\n'+'\n'.join(str(p) for p in files)+'\n\nPuede hacer falta para reconstruir el port en futuras actualizaciones.','Enviar a la papelera',danger=True):return
                        originals.trash(o,self.entries);self.preferences['hidden_originals']=sorted(set(self.preferences.get('hidden_originals',[]))|{o.id});save_settings(self.preferences,self.store);self.render();render()
                    except Exception as error:self.message('No se pudo quitar el original',str(error))
                actions.pack_start(ActionButton('Ver original','file',inspect,'steam-outline'),False,False,0)
                actions.pack_start(ActionButton('Asociar al port' if original.id in separate else 'Mostrar separado','folder',hide,'violet-outline'),False,False,0)
                actions.pack_start(ActionButton('Enviar a la papelera','folder',remove,'danger'),False,False,0)
            rows.show_all()
        render();self.fit_dialog(dialog);dialog.show_all();dialog.run();dialog.destroy()
        if self.pages.get_visible_child_name()=='detail' and self.selected:self.show_detail(self.selected)
