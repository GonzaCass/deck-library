"""Manual options inside the game page, with a fixed save action."""
from gi.repository import Gtk
from . import presets
from .gui_tools import SETTING_LABELS,SECTION_LABELS

class EditorMixin:
    def build_options(self,e,box):
        from .gui import label,button
        adapter=presets.adapter_for(e)
        try:current=presets.current_values(e,self.preferences.get('eden_config') or None)
        except Exception as error:box.pack_start(label(str(error),'muted'),False,False,0);return
        scroll=self.new_scroll();page=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16);page.set_margin_end(12);scroll.add(page);box.pack_start(scroll,True,True,0);controls={};touched=set()
        def changed(ident):
            touched.add(ident);self.editor_dirty=any(read(widget)!=initial for key,(widget,read,initial) in controls.items() if key in touched)
            status.set_text('Cambios sin guardar.' if self.editor_dirty else 'Sin cambios por guardar.');save_button.set_sensitive(self.editor_dirty)
        for section,options in presets.REGISTRY[adapter].items():
            card=self.card(page,SECTION_LABELS.get(adapter,{}).get(section,section))
            for key,rule in options.items():
                title,hint=SETTING_LABELS.get(adapter,{}).get(key,(key,''));initial=current.get(section,{}).get(key);row=Gtk.Box(spacing=16);texts=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);texts.pack_start(label(title),False,False,0)
                if hint:texts.pack_start(label(hint,'meta'),False,False,0)
                row.pack_start(texts,True,True,0);ident=(section,key)
                if rule is bool:
                    widget=Gtk.Switch();widget.set_active(bool(initial));widget.set_valign(Gtk.Align.CENTER);widget.connect('notify::active',lambda w,_,i=ident:changed(i));read=lambda w:w.get_active()
                elif isinstance(rule[0],str):
                    widget=Gtk.ComboBoxText()
                    for choice in rule:widget.append(choice,choice)
                    widget.set_active_id(initial if initial in rule else rule[0]);widget.connect('changed',lambda w,i=ident:changed(i));read=lambda w:w.get_active_id()
                else:
                    is_float=type(rule[0]) is float;widget=Gtk.SpinButton.new_with_range(rule[0],rule[1],0.5 if is_float else 1);widget.set_digits(1 if is_float else 0);widget.set_value(initial if initial is not None else rule[0]);widget.connect('value-changed',lambda w,i=ident:changed(i));read=(lambda w:float(w.get_value())) if is_float else (lambda w:int(w.get_value()))
                row.pack_end(widget,False,False,0);card.pack_start(row,False,False,0);controls[ident]=(widget,read,initial)
        status=label('Solo se guardan las opciones que cambies.','status');box.pack_start(status,False,False,0);actions=Gtk.Box(spacing=10);actions.get_style_context().add_class('apply-dock');box.pack_start(actions,False,False,0)
        def save(_):
            changes={}
            for (section,key),(widget,read,initial) in controls.items():
                value=read(widget)
                if (section,key) in touched and value!=initial:changes.setdefault(section,{})[key]=value
            if not changes:self.editor_dirty=False;status.set_text('No hay cambios para guardar.');return
            try:
                result=presets.apply(e,presets.manual_profile(e,changes),self.store,self.preferences.get('eden_config') or None)
                for ident,(widget,read,initial) in list(controls.items()):controls[ident]=(widget,read,read(widget))
                touched.clear();self.editor_dirty=False;status.set_text(str(result['changes'])+' opciones guardadas con respaldo.');self.toast('Opciones guardadas');self.show_detail(e)
            except Exception as error:self.message('No se pudo guardar',str(error))
        from .ui_components import ActionButton
        save_button=ActionButton('Guardar cambios','check',save,'violet');save_button.set_sensitive(False);actions.pack_end(save_button,False,False,0)
    def import_game_profile(self,e):
        from .models import atomic_json
        path=self.pick_file('Importar perfil JSON')
        if not path:return
        try:
            import pathlib,json
            p=pathlib.Path(path)
            if p.stat().st_size>128*1024:raise ValueError('El perfil supera 128 KiB.')
            value=presets.validate(json.loads(p.read_text()))
            if not presets.compatible(e,value):raise ValueError('El perfil corresponde a otro juego o emulador.')
            presets.import_preset(path,self.store);self.game_tab='profiles';self.show_detail(e);self.toast('Perfil importado')
        except Exception as error:self.message('No se pudo importar',str(error))
    def export_game_profile(self,e):
        from .gui import label
        from .models import atomic_json
        dialog=Gtk.Dialog(title='Exportar ajustes',transient_for=self,modal=True);dialog.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Exportar',Gtk.ResponseType.OK);box=dialog.get_content_area();box.set_border_width(16);box.set_spacing(10);name=Gtk.Entry();name.set_text(e.name+' — mis ajustes');author=Gtk.Entry();author.set_placeholder_text('Alias público');box.pack_start(label('Nombre del perfil'),False,False,0);box.pack_start(name,False,False,0);box.pack_start(label('Autor'),False,False,0);box.pack_start(author,False,False,0);self.fit_dialog(dialog);dialog.show_all();response=dialog.run();title=name.get_text().strip();alias=author.get_text().strip();dialog.destroy()
        if response!=Gtk.ResponseType.OK:return
        try:
            value=presets.export_current(e,title,alias,self.store,self.preferences.get('eden_config') or None);path=self.pick_file('Guardar perfil JSON',save=True)
            if path:atomic_json(path,value);self.toast('Perfil exportado')
        except Exception as error:self.message('No se pudo exportar',str(error))
