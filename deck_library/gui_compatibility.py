"""Game-scoped dependency status, Proton recommendations and community fix resources."""
import pathlib,subprocess,threading
from gi.repository import Gtk,GLib
from . import runtime_components as components,proton_selection,proton_tools,game_fixes
from .inline_pages import InlineDialog
from .ui_components import ActionButton,Reveal,text,badge


class CompatibilityMixin:
    def compatibility_chips(self,entry,parent):
        if not proton_selection.mode(entry):return
        label=proton_selection.choice(entry)
        if not label:
            try:label=components.tool_for(entry).parent.name
            except ValueError:label='Proton por revisar'
        parent.pack_start(badge(label,'blue',20),False,False,0)
        chip=ActionButton('Componentes: revisar','sliders',lambda _:self.compatibility_page(entry),'quiet')
        chip.set_tooltip_text('Revisar componentes de Windows, Proton y fixes de este juego.');parent.pack_start(chip,False,False,0)
        def work():
            try:value=components.inspect(entry,self.store)
            except Exception:value={'state':'unknown'}
            def show():
                if chip.in_destruction() or self.ui_closed:return False
                chip.set_label({'present':'Componentes presentes','missing':'Faltan componentes'}.get(value['state'],'Componentes sin revisar'))
                chip.get_style_context().add_class({'present':'steam-outline','missing':'amber'}.get(value['state'],'quiet'));return False
            GLib.idle_add(show)
        threading.Thread(target=work,daemon=True).start()

    def build_compatibility_action(self,entry,body):
        if proton_selection.mode(entry) or game_fixes.for_entry(entry):
            body.pack_start(ActionButton('Compatibilidad y fixes','sliders',lambda _:self.compatibility_page(entry),'cyan'),False,False,0)

    def compatibility_page(self,entry):
        page=InlineDialog(title='Compatibilidad y fixes · '+entry.name,transient_for=self);page.add_button('Volver al juego',Gtk.ResponseType.CLOSE)
        body=page.get_content_area();actions=page.get_action_area();status=text('Revisando componentes…','status',85)
        page.pack_start(status,False,False,0);page.reorder_child(status,2)
        progress=Gtk.ProgressBar();progress.set_no_show_all(True);page.pack_start(progress,False,False,0);page.reorder_child(progress,3)
        details=self.card(body,'Componentes de Windows')
        details.pack_start(text('Componentes requeridos por este ejecutable.','muted',85),False,False,0)
        scope=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        scope.pack_start(text('Se revisan las DLL importadas por el ejecutable. No detecta todos los requisitos cargados durante el juego ni comprueba el gameplay. DirectX 9/11/12 base lo gestiona Proton; aquí se preparan componentes adicionales.','muted',85),False,False,0)
        prefix_label=text('','meta',85);prefix_label.set_selectable(True);scope.pack_start(prefix_label,False,False,0)
        found=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);details.pack_start(found,False,False,0)
        details.pack_start(Reveal('Detalles de la revisión',scope),False,False,0)
        state={'busy':False,'checks':[],'value':None,'pending':'','phase':'Preparando componentes…','timer':0,'cancel':None}
        log=Gtk.TextView();log.set_editable(False);log.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);log.set_size_request(-1,120)
        log_reveal=Reveal('Registro de preparación',log);body.pack_start(log_reveal,False,False,0);lines=[]
        def display(value):
            if page._closed:return False
            state['value']=value
            for child in found.get_children():child.destroy()
            state['checks']=[]
            for row in value.get('components',[]):
                present=row['state']=='present';check=Gtk.CheckButton(label=row['name']+' · '+('Presente' if present else 'Falta'))
                check.set_active(not present);check.set_sensitive(not present);found.pack_start(check,False,False,0);state['checks'].append((check,row['verb']))
            if not value.get('components'):found.pack_start(text(value.get('reason') or 'No se identificaron componentes adicionales. Esto no confirma que estén todos los requisitos del juego.','muted',85),False,False,0)
            if value.get('prefix'):prefix_label.set_text('Prefijo del juego: '+value['prefix'])
            if value.get('reason') and value.get('components'):found.pack_start(text(value['reason'],'meta',85),False,False,0)
            install.set_sensitive(any(c.get_active() for c,_ in state['checks']));found.show_all()
            for check,_ in state['checks']:check.connect('toggled',lambda *_:install.set_sensitive(not state['busy'] and any(c.get_active() for c,_ in state['checks'])))
            return False
        def report(line):
            state['pending']=str(line)
            if str(line).startswith(('Descargando','Instalando','Creando','Verificando')):state['phase']=str(line)[:220]
        def tick():
            if page._closed or not state['busy']:state['timer']=0;return False
            progress.pulse()
            if state['cancel'] and state['cancel'].is_set():status.set_text('Cancelando la preparación…')
            if state['pending']:

                if not state['cancel'].is_set():status.set_text(state['phase'])
                lines.append(state['pending']);del lines[:-80];log.get_buffer().set_text('\n'.join(lines));state['pending']=''
            return True
        def finish(result,error):
            state['busy']=False;self.profile_job=False
            if state['timer']:GLib.source_remove(state['timer']);state['timer']=0
            if page._closed:return False
            body.set_sensitive(True);progress.hide();cancel_button.hide();cancel_button.set_no_show_all(True);page.set_deletable(True);page.back_button.set_sensitive(True)
            for check,_ in state['checks']:check.set_sensitive(True)
            from .ports import Cancelled
            status.set_text('Preparación cancelada. Revisar los componentes para volver a intentar.' if isinstance(error,Cancelled) else ('No se pudieron preparar los componentes: '+str(error)) if error else 'Componentes preparados. Abrir el juego para comprobar su funcionamiento.')
            if result:
                lines.append('Respaldo del registro: '+result['backup']);log.get_buffer().set_text('\n'.join(lines));self.toast('Componentes preparados')
            try:display(components.inspect(entry,self.store))
            except Exception:pass
            return False
        def prepare(_):
            if state['busy'] or getattr(self,'profile_job',False) or getattr(self,'port_busy',False):return
            verbs=[verb for check,verb in state['checks'] if check.get_active()]
            if not verbs:return
            if not self.confirm('Preparar componentes de Windows','Se instalarán los componentes elegidos en el prefijo de este juego. Se respalda el registro; no es una copia completa del prefijo. Puede necesitar descargar Protontricks.','Preparar'):return
            state['busy']=True;state['cancel']=threading.Event();self.profile_job=True;body.set_sensitive(False);install.set_sensitive(False);page.set_deletable(False);page.back_button.set_sensitive(False)
            for check,_ in state['checks']:check.set_sensitive(False)
            progress.set_no_show_all(False);progress.show();cancel_button.set_no_show_all(False);cancel_button.show_all();status.set_text('Preparando componentes…');state['timer']=GLib.timeout_add(150,tick)
            def work():
                try:GLib.idle_add(finish,components.prepare(entry,verbs,self.store,progress=report,cancel=state['cancel']),None)
                except Exception as error:GLib.idle_add(finish,None,error)
            threading.Thread(target=work,daemon=True).start()
        def choose_executable(_):
            if state['busy']:return
            path=self.pick_file('Elegir el ejecutable Windows de este juego',patterns=('*.exe',),filter_name='Ejecutables Windows')
            if not path:return
            try:components.pe_imports.inspect(path)
            except (OSError,ValueError,UnicodeError) as error:status.set_text(str(error));return
            entry.metadata['dependency_executable']=path
            entries=self.store.load();saved=next((e for e in entries if e.id==entry.id),None)
            if saved:saved.metadata['dependency_executable']=path;self.store.save(entries)
            display(components.inspect(entry,self.store));status.set_text('Ejecutable seleccionado para revisar sus componentes.')
        actions.pack_start(ActionButton('Elegir ejecutable','file',choose_executable,'steam-outline'),False,False,0)
        install=ActionButton('Preparar componentes','download',prepare,'play');install.set_sensitive(False);actions.pack_start(install,False,False,0)
        def play_anyway(_):
            if state['busy']:return
            self._dependency_bypass=getattr(self,'_dependency_bypass',set());self._dependency_bypass.add(entry.id)
            page.destroy();GLib.idle_add(lambda:(self.play(entry),False)[1])
        actions.pack_start(ActionButton('Probar el juego','play',play_anyway,'steam-outline'),False,False,0)
        recommendation=game_fixes.recommendation(entry,self.store)
        cancel_button=ActionButton('Cancelar','undo',lambda _:state['cancel'].set() if state['cancel'] else None,'danger');cancel_button.set_no_show_all(True);actions.pack_start(cancel_button,False,False,0)
        if recommendation:
            panel=self.card(body,'Proton recomendado');panel.pack_start(text(recommendation['version']+' · '+recommendation['evidence'],'muted',85),False,False,0)
            def apply_recommended(_):
                try:proton_selection.save(entry,recommendation['version'],self.store);self.toast('Versión de Proton guardada');page.destroy();self.show_detail(entry)
                except (OSError,ValueError,RuntimeError) as error:status.set_text(str(error))
            if proton_selection.mode(entry)!='steam':panel.pack_start(ActionButton('Usar Proton recomendado','check',apply_recommended,'steam'),False,False,0)
        resources=game_fixes.for_entry(entry)
        if resources:
            panel=self.card(body,'Fixes y guías de la comunidad')
            for group in resources:
                for row in group['resources']:
                    panel.pack_start(ActionButton(row['name'],'file',lambda _,url=row['url']:subprocess.Popen(['xdg-open',url],start_new_session=True),'violet-outline'),False,False,0)
                    panel.pack_start(text(row['notes'],'muted',85),False,False,0)
        if proton_selection.mode(entry):self.build_proton_selector(entry,body,compact=True)
        body.reorder_child(log_reveal,-1)
        def refresh():
            try:value=components.inspect(entry,self.store);error=None
            except Exception as e:value={'state':'unknown','components':[],'reason':str(e)};error=e
            def show():
                display(value)
                if not page._closed:status.set_text('Revisión completada.' if not error else str(error))
                return False
            GLib.idle_add(show)
        def closing(*_):
            if state['timer']:GLib.source_remove(state['timer']);state['timer']=0
        def back(*_):
            page.destroy()
            if not self.ui_closed and self.selected and self.selected.id==entry.id:self.show_detail(entry)
        page.connect('destroy',closing);page.connect('response',back);page._mount();threading.Thread(target=refresh,daemon=True).start();return page
