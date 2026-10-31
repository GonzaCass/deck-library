"""Startup recovery of missing emulated games, inside the main window."""
from gi.repository import Gtk,GLib
from . import rom_locations
from .inline_pages import InlineDialog
from .ui_components import ActionButton,text


class RomLocationsMixin:
    def check_missing_roms(self):
        if self.ui_closed or getattr(self,'missing_roms_checked',False):return False
        if (not self.preferences.get('onboarding_complete') or self.pages.get_visible_child_name()=='welcome'
                or self.inline_workflows or self.discover_busy or getattr(self,'editor_dirty',False)
                or getattr(self,'port_busy',False) or getattr(self,'profile_job',False)):
            if not getattr(self,'_missing_rom_retry',0):
                def retry():
                    self._missing_rom_retry=0;return self.check_missing_roms()
                self._missing_rom_retry=GLib.timeout_add_seconds(3,retry);self.ui_sources.append(self._missing_rom_retry)
            return False
        self.missing_roms_checked=True
        self._missing_rom_queue=rom_locations.missing(self.entries,self.preferences)
        self.next_missing_rom()
        return False

    def next_missing_rom(self):
        if self.ui_closed:return False
        current={e.id:e for e in rom_locations.missing(self.entries,self.preferences)}
        queue=getattr(self,'_missing_rom_queue',[])
        while queue:
            entry=queue.pop(0)
            if entry.id in current:self.missing_rom_page(current[entry.id]);break
        return False

    def missing_rom_page(self,entry):
        page=InlineDialog(title='No se encuentra '+entry.name,transient_for=self)
        body=page.get_content_area()
        body.pack_start(text('¿El juego cambió de ubicación o se borró?','title',70),False,False,0)
        body.pack_start(text('Si está en una microSD o un disco externo, conectarlo antes de decidir. No se borrará ningún archivo.','muted',75),False,False,0)
        path=text(entry.source,'muted',75);path.set_selectable(True);body.pack_start(path,False,False,0)
        status=text('','status',75);body.pack_start(status,False,False,0)
        def refresh():
            self.entries=self.store.load();self.checked&={e.id for e in self.entries};self.library_dirty=True;self.refresh_platforms()
            if self.selected:self.selected=next((e for e in self.entries if e.id==self.selected.id),None)
            if self.pages.get_visible_child_name()=='detail':
                if self.selected:self.show_detail(self.selected)
                else:self.pages.set_visible_child_name('library')
            elif self.pages.get_visible_child_name()=='home':self.home_page()
            else:self.render()
            self.refresh_pending()
        def complete(message):
            refresh();page.destroy();self.toast(message);GLib.idle_add(self.next_missing_rom)
        def moved(_):
            patterns=tuple('*'+suffix for suffix in sorted(rom_locations.extensions(entry)))
            chosen=self.pick_file('Elegir la nueva ubicación de '+entry.name,patterns=patterns,filter_name=entry.platform)
            if not chosen:return
            try:rom_locations.relocate(entry,chosen,self.store)
            except (OSError,ValueError,RuntimeError) as error:status.set_text(str(error));return
            complete('Ubicación del juego actualizada')
        def deleted(_):
            try:result=rom_locations.forget(entry,self.store)
            except (OSError,ValueError,RuntimeError) as error:status.set_text(str(error));return
            message='Juego quitado de la biblioteca.'
            if result.get('state')=='pending':message+=' El acceso se quitará cuando Steam se cierre.'
            complete(message)
        def recheck(_):
            if entry not in rom_locations.missing([entry],self.preferences):complete('La ROM está disponible de nuevo')
            else:status.set_text('La ROM sigue sin encontrarse en la ubicación guardada.')
        def later(*_):self._missing_rom_queue=[];page.destroy()
        actions=page.get_action_area()
        for title,icon,callback,tone in [('Se movió','folder',moved,'cyan'),('Se borró','trash',deleted,'danger'),('Volver a comprobar','refresh',recheck,'steam-outline'),('Revisar después','back',later,'quiet')]:
            actions.pack_start(ActionButton(title,icon,callback,tone),False,False,0)
        page.connect('response',later);page._mount();return page
