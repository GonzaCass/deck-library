"""Inline recovery and reuse of portable game installations."""
import pathlib
from gi.repository import Gtk,GLib
from .inline_pages import InlineDialog
from .ui_components import ActionButton,text
from . import ports,port_locations,switch_port


class PortLocationsMixin:
    def port_install_choice(self,item,runtime='auto'):
        page=InlineDialog(title='Instalar '+item['name'],transient_for=self)
        page.add_button('Volver',Gtk.ResponseType.CLOSE)
        body=page.get_content_area()
        body.pack_start(text('Descargar el port o vincular una instalación que ya esté en este equipo. Los archivos del juego se eligen en el siguiente paso si hacen falta.','muted',85),False,False,0)
        def download(_):
            page.destroy();GLib.idle_add(lambda:(self.install_port(item,False,runtime=runtime,location_chosen=True),False)[1])
        def existing(_):
            page.destroy();self.port_location_page(item)
        page.get_action_area().pack_start(ActionButton('Descargar port','download',download,'play'),False,False,0)
        page.get_action_area().pack_start(ActionButton('Usar instalación existente','folder',existing,'cyan'),False,False,0)
        page.connect('response',lambda *_:page.destroy());page._mount()
        return page

    def port_location_page(self,item=None,entry=None):
        repository=(entry.metadata.get('port_repository','') if entry else '') or (item or {}).get('repository','')
        record=ports.records(self.store).get(repository,{})
        item=ports.clean(item or record or {'repository':repository}) if repository else None
        page=InlineDialog(title='Carpetas del juego',transient_for=self)
        page.add_button('Volver',Gtk.ResponseType.CLOSE)
        if repository:page.port_repository=repository
        body=page.get_content_area();body.set_spacing(12)
        status=text('','status',85);status.set_selectable(True)
        path_label=text('','muted',85);path_label.set_selectable(True)
        body.pack_start(text('Port: la carpeta del ejecutable. Archivos del juego: los originales extraídos o los datos compilados que necesita ese port.','muted',85),False,False,0)
        body.pack_start(path_label,False,False,0);body.pack_start(status,False,False,0)
        current=[entry];changed=[False]
        def refresh():
            value=ports.records(self.store).get(repository,{})
            folder=ports.folder_for(value) if value else pathlib.Path(current[0].source).parent if current[0] and current[0].source else None
            lines=['Carpeta del port: '+str(folder)] if folder else ['Elegir la carpeta donde está instalado el port.']
            if value.get('game_data_dir'):lines.append('Datos compilados: '+value['game_data_dir'])
            if (value.get('inputs') or {}).get('original_data'):lines.append('Archivos extraídos: '+value['inputs']['original_data'])
            path_label.set_text('\n'.join(lines))
            missing=port_locations.problem(current[0],self.store) if current[0] else ''
            if missing:status.set_text(missing)
        def apply_folder(path,executable=None):
            try:
                fresh=port_locations.link_entry(current[0],path,self.store,executable) if current[0] else port_locations.link(repository,path,self.store,item=item,executable=executable)
            except (OSError,ValueError) as error:status.set_text(str(error));return False
            current[0]=fresh;changed[0]=True;status.set_text('Ubicación guardada. El acceso de Steam se conserva.');refresh();return True
        def choose(_):
            path=self.pick_file('Elegir carpeta del port',folder=True)
            if path:apply_folder(path)
        actions=page.get_action_area()
        actions.pack_start(ActionButton('Elegir carpeta del port','folder',choose,'cyan'),False,False,0)
        def choose_executable(_):
            path=self.pick_file('Elegir ejecutable del port')
            if path:apply_folder(str(pathlib.Path(path).parent),path)
        # Explicit executable selection resolves multi-program packages without guessing.
        advanced=self.card(body,'Ejecutable del port')
        advanced.pack_start(text('Si la carpeta tiene varios programas, elegir cuál inicia el juego.','muted',85),False,False,0)
        advanced.pack_start(ActionButton('Elegir ejecutable si hay varios','file',choose_executable,'steam-outline'),False,False,0)
        found=port_locations.candidates(repository,self.store) if repository else port_locations.manual_candidates(entry,self.store) if entry else []
        if found:
            found_box=self.card(body,'Instalaciones encontradas')
            for folder in found:
                found_box.pack_start(ActionButton(folder.name,'folder',lambda _,p=folder:apply_folder(p),'steam-outline'),False,False,0)
                found_box.pack_start(text(str(folder),'muted',85),False,False,0)
        if repository:
            def reinstall(_):
                if not self.confirm('Reinstalar el port','Se descargará el port y se repetirán los pasos que falten. Si la instalación está en una microSD, conectarla antes. Una carpeta vinculada de otro lanzador se conserva.','Reinstalar'):return
                page.destroy();GLib.idle_add(lambda:(self.install_port(item,bool(ports.records(self.store).get(repository)),location_chosen=True,reinstall_missing=True),False)[1])
            actions.pack_start(ActionButton('Reinstalar port','download',reinstall,'amber'),False,False,0)
            def data_selected(folder):
                value=ports.records(self.store).get(repository)
                if not value:raise ValueError('Elegir primero la carpeta del port.')
                ports.set_input(repository,'original_data',folder,self.store);changed[0]=True;status.set_text('Carpeta de archivos guardada.');refresh()
            def compiled_selected(folder):
                switch_port.set_data(repository,folder,self.store);changed[0]=True;status.set_text('Juego compilado vinculado.');refresh()
            def originals(_):
                value=ports.records(self.store).get(repository)
                if not value:status.set_text('Elegir primero la carpeta del port.');return
                if (value.get('original_data') or {}).get('kind')=='switch-dump':
                    from .gui_switch import minimum_for
                    self.switch_convert_page(on_done=data_selected,minimum=minimum_for(repository),on_prepared=compiled_selected if repository.casefold()==switch_port.REPOSITORY else None)
                elif value.get('setup'):
                    # The shared wizard also handles ISO, ROM, BIOS and disc requirements.
                    page.destroy()
                    if self.port_inputs(ports.clean(value)):self.configure_port(ports.clean(value),automatic=True)
            if record.get('setup') or (item or {}).get('setup'):
                actions.pack_start(ActionButton('Elegir archivos del juego','file',originals,'violet-outline'),False,False,0)
        else:body.pack_start(text('Este port se agregó manualmente. Para reinstalarlo hace falta su proyecto de origen.','meta',85),False,False,0)
        def closed(*_):
            if not changed[0]:return
            self.entries=self.store.load();self.library_dirty=True;self.refresh_platforms()
            fresh=next((e for e in self.entries if current[0] and e.id==current[0].id),None)
            if fresh:GLib.idle_add(lambda:(self.select_game(fresh),False)[1])
        page.connect('destroy',closed);page.connect('response',lambda *_:page.destroy());refresh();page._mount()
        return page

    def recover_port_location(self,entry):
        try:fresh=port_locations.recover(entry,self.store)
        except (OSError,ValueError) as error:
            self.message('No se pudo recuperar la ubicación',str(error));return False
        if fresh is not entry:
            self.entries=self.store.load();self.library_dirty=True;self.selected=fresh
        if port_locations.problem(fresh,self.store):
            self.port_location_page(entry=fresh);return False
        return fresh
