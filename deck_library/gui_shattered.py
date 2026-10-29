"""One action for the existing Shattered Dimensions Steam installation."""
import threading
from gi.repository import Gtk,GLib
from . import shattered
from .inline_pages import InlineDialog
from .ui_components import ActionButton,Reveal,text,badge


class ShatteredMixin:
    def build_shattered_fix(self,entry,body):
        if not shattered.matches(entry):return
        panel=self.card(body,'Arreglo de audio y voces')
        panel.pack_start(text('Instala d3dx9_43 y XACT en el prefijo de este juego. Guarda un respaldo del registro y conserva el acceso de Steam y las partidas. El idioma solo cambia si se elige esa opción.','muted',95),False,False,0)
        try:
            value=shattered.inspect(entry)
            if value['detected']:panel.pack_start(badge('Componentes detectados','green'),False,False,0)
        except (OSError,ValueError) as error:panel.pack_start(text(str(error),'meta',95),False,False,0)
        options=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);row=Gtk.Box(spacing=10)
        row.pack_start(text('Idioma del juego'),True,True,0);language=Gtk.ComboBoxText()
        for key,caption in [('ESN','Español'),('keep','Conservar idioma actual')]:language.append(key,caption)
        language.set_active_id('keep');row.pack_end(language,False,False,0);options.pack_start(row,False,False,0)
        options.pack_start(text('Requiere el acceso de Steam con Proton 10.0 y un primer inicio completado. Protontricks se instala si falta. Las voces necesitan los archivos del idioma elegido. El respaldo cubre el registro y los archivos locales modificados; no es una copia completa del prefijo.','meta',95),False,False,0)
        panel.pack_start(Reveal('Opciones y requisitos del arreglo',options),False,False,0)
        action=ActionButton('Aplicar arreglo','sliders',lambda _:self.apply_shattered_fix(entry,language.get_active_id()),'violet');action.set_halign(Gtk.Align.START)
        panel.pack_start(action,False,False,0);panel.reorder_child(action,1)

    def apply_shattered_fix(self,entry,language='keep'):
        if getattr(self,'profile_job',False) or getattr(self,'port_busy',False):return
        self.profile_job=True;page=InlineDialog(title='Preparando Shattered Dimensions',transient_for=self);page.set_deletable(False)
        status=text('Preparando el arreglo…','title',95);page.get_content_area().pack_start(status,False,False,0)
        spinner=Gtk.Spinner();spinner.start();page.get_content_area().pack_start(spinner,False,False,0)
        log=Gtk.TextView();log.set_editable(False);log.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);scroll=self.new_scroll();scroll.set_min_content_height(150);scroll.add(log)
        page.get_content_area().pack_start(Reveal('Detalles de la preparación',scroll),True,True,0);page._mount()
        lines=[]
        def progress(line):
            def paint():
                if page._closed:return False
                lines.append(line);del lines[:-100];log.get_buffer().set_text('\n'.join(lines));return False
            GLib.idle_add(paint)
        def done(result,error):
            self.profile_job=False
            if self.ui_closed:return False
            spinner.stop();spinner.hide();page.set_deletable(True)
            status.set_text(str(error) if error else 'Arreglo aplicado. Iniciar el juego desde Steam para comprobar audio, voces y controles.')
            if result:progress('Respaldo: '+result['backup']);self.toast('Arreglo de Shattered Dimensions aplicado')
            def back(*_):
                page.destroy()
                if self.selected and self.selected.id==entry.id:self.show_detail(entry)
            page.add_button('Volver al juego',Gtk.ResponseType.CLOSE);page.connect('response',back)
            return False
        def work():
            try:GLib.idle_add(done,shattered.apply(entry,self.store,language,progress),None)
            except Exception as error:GLib.idle_add(done,None,str(error))
        threading.Thread(target=work,daemon=True).start()
        return page
