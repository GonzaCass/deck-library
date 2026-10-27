"""Installation, content and portable preset dialogs for the GTK library."""
import datetime,json,pathlib,shlex,subprocess,sys,threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib
from .inline_pages import InlineDialog,InlineFileChooser,InlineFileButton
from .installations import settings,save_settings,report
from .models import atomic_json
from . import presets
from .content import switch_inventory,install_nsp,install_mod_zip,nsp_identity,switch_id

SECTION_LABELS={'duckstation':{'GPU':'Video','Display':'Pantalla y FPS','CPU':'Procesador','CDROM':'Disco'},'dolphin':{'Video_Settings':'Video','Video_Hacks':'Correcciones de video'},'prism':{'General':'Memoria y ventana'}}
SETTING_LABELS={
 'duckstation':{
  'ResolutionScale':('Resolución interna (×)','Multiplicador sobre la resolución original de PS1. En la Deck, 3 a 5 es lo habitual.'),
  'Multisamples':('Antialiasing (MSAA)','1 desactiva el suavizado.'),
  'TextureFilter':('Filtro de texturas','Nearest conserva el aspecto original.'),
  'TrueColor':('Color verdadero (24 bits)','Elimina el degradado por bandas del color original.'),
  'ScaledDithering':('Dithering escalado','Ajusta el patrón de puntos a la resolución interna.'),
  'WidescreenHack':('Pantalla ancha','Amplía la imagen en 3D; puede recortar o deformar algunos juegos.'),
  'DisableInterlacing':('Quitar entrelazado','Evita el parpadeo en juegos que usan modo entrelazado.'),
  'ForceNTSCTimings':('Forzar velocidad NTSC','Corrige la velocidad de juegos PAL a 60 Hz; puede afectar la música.'),
  'ChromaSmoothing24Bit':('Suavizar color en videos de 24 bits',''),
  'PGXPEnable':('PGXP (geometría precisa)','Corrige vértices que tiemblan. Es la base de las demás opciones PGXP.'),
  'PGXPCulling':('PGXP: descarte de caras','Reduce huecos en la geometría.'),
  'PGXPTextureCorrection':('PGXP: texturas en perspectiva','Quita la deformación de texturas.'),
  'PGXPColorCorrection':('PGXP: corrección de color',''),
  'PGXPDepthBuffer':('PGXP: búfer de profundidad','Mejora el orden de dibujo; algunos juegos fallan.'),
  'PGXPCPU':('PGXP: modo CPU','Más preciso y más lento. Útil si hay geometría rota.'),
  'PGXPPreserveProjFP':('PGXP: conservar proyección','Arregla ciertos juegos con cámara inestable.'),
  'PGXPVertexCache':('PGXP: caché de vértices','Puede corregir polígonos que desaparecen.'),
  'MaxFPS':('Límite de FPS','0 usa la velocidad del juego.'),
  'VSync':('Sincronización vertical',''),
  'IntegerScaling':('Escalado entero','Sin bordes borrosos; deja franjas negras.'),
  'LinearFiltering':('Filtro lineal de pantalla',''),
  'ShowFPS':('Mostrar FPS',''),
  'OverclockEnable':('Overclock del procesador','Quita ralentizaciones en juegos pesados.'),
  'OverclockNumerator':('Overclock: numerador','Porcentaje = numerador / denominador × 100.'),
  'OverclockDenominator':('Overclock: denominador',''),
  'ReadSpeedup':('Velocidad de lectura del disco (×)','Acorta las pantallas de carga; algunos juegos fallan por encima de 1.'),
  'LoadImageToRAM':('Cargar el disco en RAM','Evita tirones de lectura.'),
  'LoadImagePatches':('Aplicar parches del disco','Activa los parches de la base de datos de DuckStation.')},
 'dolphin':{'InternalResolution':('Resolución interna (×)','1 es nativa de Wii.'),'MSAA':('Antialiasing (MSAA)','0 lo desactiva.'),'SSAA':('Supermuestreo (SSAA)','Más costoso que MSAA.'),'MaxAnisotropy':('Filtrado anisotrópico','Exponente: 0 desactivado, 4 equivale a 16×.'),'EFBScaledCopy':('Copia de EFB escalada','Desactivar corrige efectos borrosos.'),'EFBAccessEnable':('Acceso a EFB desde CPU','Necesario para algunos efectos; reduce rendimiento.'),'EFBToTextureEnable':('EFB a textura','Desactivar mejora precisión y reduce velocidad.')},
}

SECTION_LABELS.update({'eden':{'Core':'Núcleo','Cpu':'Procesador','System':'Sistema','Renderer':'Gráficos'},'wiicompiled':{'video':'Video','audio':'Audio'},'prism':{'General':'Memoria y ventana'},'project2099':{'runtime':'Ejecución'}})
SETTING_LABELS.setdefault('eden',{}).update({
 'language_index':('Idioma del juego','5 español de España; 14 español latinoamericano. La ROM debe incluirlo.'),'use_multi_core':('Varios núcleos de CPU',''),'use_speed_limit':('Limitar la velocidad',''),'speed_limit':('Límite de velocidad (%)','100 es la velocidad original'),'sync_core_speed':('Sincronizar la velocidad de los núcleos',''),
 'cpu_accuracy':('Precisión de la CPU','0 automática, 1 precisa, 2 insegura'),'use_custom_cpu_ticks':('Ciclos de CPU personalizados',''),'use_docked_mode':('Modo base (TV)','Desactivado equivale al modo portátil'),
 'backend':('API gráfica','0 OpenGL, 1 Vulkan'),'resolution_setup':('Resolución interna','Escala sobre la resolución original de la consola'),'aspect_ratio':('Relación de aspecto',''),'anti_aliasing':('Suavizado de bordes','0 sin suavizado'),
 'scaling_filter':('Filtro de escalado','5 es FSR'),'gpu_accuracy':('Precisión de la GPU','0 normal, 1 alta, 2 extrema'),'dma_accuracy':('Precisión de DMA',''),'vram_usage_mode':('Uso de memoria de video',''),
 'use_disk_shader_cache':('Caché de shaders en disco',''),'use_vulkan_driver_pipeline_cache':('Caché de pipelines del controlador Vulkan',''),'use_asynchronous_gpu_emulation':('Emulación de GPU asíncrona',''),
 'use_asynchronous_shaders':('Compilar shaders en segundo plano','Evita tirones al compilar'),'async_presentation':('Presentación asíncrona',''),'use_vsync':('Sincronización vertical',''),'force_max_clock':('Forzar el reloj máximo de la GPU',''),'max_anisotropy':('Filtro anisotrópico','0 automático, 4 es 16×')})
SETTING_LABELS.setdefault('wiicompiled',{}).update({'resolution_multiplier':('Multiplicador de resolución',''),'disable_copy_filter':('Desactivar el filtro de copia',''),'frame_interpolation_fps':('Interpolación de cuadros (FPS)',''),'graphics_api':('API gráfica',''),'display_mode':('Modo de pantalla',''),'skip_unready_pipelines':('Omitir pipelines no listos',''),'show_fps':('Mostrar FPS',''),'mix_worker':('Mezcla de audio en otro hilo','')})
SETTING_LABELS.setdefault('prism',{}).update({'OverrideMemory':('Personalizar la memoria',''),'MinMemAlloc':('Memoria mínima (MiB)',''),'MaxMemAlloc':('Memoria máxima (MiB)',''),'OverrideWindow':('Personalizar la ventana',''),'MinecraftWinWidth':('Ancho de ventana',''),'MinecraftWinHeight':('Alto de ventana',''),'LaunchMaximized':('Iniciar maximizada','')})

SECTION_LABELS['narutorise']={'runtime':'Gráficos de Naruto'}
SETTING_LABELS['narutorise']={'renderer': ('Motor gráfico', 'Nativo, sin emulación de GPU.'), 'native_backend': ('API gráfica', 'Vulkan es la opción compatible con este port bajo Proton.'), 'resolution_scale': ('Resolución base (×)', '1× corresponde a 720p.'), 'internal_resolution_scale': ('Resolución interna (×)', '0 usa la resolución base; 1,5 equivale a 1080p.'), 'fullscreen': ('Pantalla completa', ''), 'frame_rate': ('Objetivo de FPS', 'Usar 30 o 60 en la Deck; no garantiza una tasa fija.'), 'vsync': ('Sincronización vertical', ''), 'd3d12_host_vsync': ('Sincronización de presentación', 'Se guarda junto con VSync.'), 'msaa_samples': ('Suavizado MSAA', '0 desactiva MSAA; aumenta el trabajo gráfico.'), 'swap_post_effect': ('Suavizado de bordes', 'FXAA suaviza la imagen; none lo desactiva.'), 'present_effect': ('Filtro de presentación', 'CAS mantiene la nitidez.'), 'anisotropic_override': ('Filtrado de texturas', '-1 automático, 0 desactivado, 1 = 1×, 2 = 2×, 3 = 4×, 4 = 8×, 5 = 16×.'), 'transparency_antialiasing': ('Suavizado de transparencias', ''), 'max_frame_latency': ('Cuadros en espera', 'Vulkan limita la presentación a un cuadro.'), 'triple_buffering': ('Triple búfer', '')}

class ToolsMixin:
    def gtaiv_dialog(self,e):
        from .gui import label,button,wrap_row
        from . import gtaiv
        dialog=InlineDialog(title='Arreglo de GTA IV',transient_for=self,modal=True)
        dialog.set_default_size(760,520);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(22);box.set_spacing(14)
        box.pack_start(label('GTA IV · FusionFix 4.0.5','title'),False,False,0)
        box.pack_start(label('Confirmado en una Steam Deck OLED el 01/10/2026: el juego funcionó bien con estos cambios. No hay medición de FPS sostenidos.','subtitle'),False,False,0)
        box.pack_start(label('• FusionFix 4.0.5 oficial, con respaldo completo.\n• DXVK 2.6.2 y latencia máxima de un cuadro.\n• VSync de DXVK activado y el del juego apagado.\n• Se conservan los gráficos y el límite de FPS (60 en una instalación nueva).\n• Botones de PlayStation.\n\nEl juego debe estar cerrado. La primera vez se descargan unos 172 MB.','muted'),False,False,0)
        doc=pathlib.Path(__file__).resolve().parent.parent/'docs/GTAIV.md'
        box.pack_start(button('Leer instrucciones',lambda _:subprocess.Popen(['xdg-open',str(doc)],start_new_session=True)),False,False,0)
        status=label('Listo para aplicar.','muted');box.pack_start(status,False,False,0)
        row=Gtk.Box(spacing=12);box.pack_start(row,False,False,0)
        active=[False];buttons=[]
        def finish(result,error):
            active[0]=False
            for control in buttons:control.set_sensitive(True)
            dialog.set_deletable(True);dialog.set_response_sensitive(Gtk.ResponseType.CLOSE,True)
            status.set_text(('No se pudo completar: '+error) if error else 'Listo. Respaldo: '+result)
            return False
        def run(action):
            if active[0]:return
            config=e.metadata.get('gtaiv_settings')
            if action=='apply' and not config:
                config=self.pick_file('Elegir SETTINGS.CFG de GTA IV')
                if not config:return
                e.metadata['gtaiv_settings']=config;self.store.save(self.entries)
            active[0]=True
            for control in buttons:control.set_sensitive(False)
            dialog.set_deletable(False);dialog.set_response_sensitive(Gtk.ResponseType.CLOSE,False)
            status.set_text('Descargando, respaldando y aplicando…' if action=='apply' else 'Restaurando respaldo…')
            def work():
                try:
                    result=gtaiv.apply(e.metadata['gtaiv_root'],config,self.store) if action=='apply' else gtaiv.restore(e.metadata['gtaiv_root'],self.store)
                    GLib.idle_add(finish,result,None)
                except Exception as exc:GLib.idle_add(finish,None,str(exc))
            threading.Thread(target=work,daemon=True).start()
        for title,action in [('Aplicar arreglo de GTA IV','apply'),('Restaurar respaldo','restore')]:
            control=button(title,lambda _,a=action:run(a),tone='presets');buttons.append(control);row.pack_start(control,True,True,0)
        self.fit_dialog(dialog);dialog.show_all()
        while True:
            dialog.run()
            if not active[0]:break
        dialog.destroy()

    def pick_file(self,title,save=False,folder=False):
        dialog=InlineFileChooser(title=title,transient_for=self,action=Gtk.FileChooserAction.SELECT_FOLDER if folder else Gtk.FileChooserAction.SAVE if save else Gtk.FileChooserAction.OPEN)
        dialog.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Guardar' if save else 'Elegir',Gtk.ResponseType.OK)
        if save:dialog.set_do_overwrite_confirmation(True);dialog.set_current_name('preset.json')
        result=dialog.get_filename() if dialog.run()==Gtk.ResponseType.OK else None;dialog.destroy();return result
    def choose_cover(self,e):
        path=self.pick_file('Elegir carátula local')
        if path:
            try:
                from gi.repository import GdkPixbuf
                GdkPixbuf.Pixbuf.new_from_file_at_scale(path,150,185,True)
                e.cover=path;e.metadata.pop('artwork',None);self.store.save(self.entries);self.render();self.set_status('Carátula guardada para '+e.name+'.')
            except GLib.Error:self.message('Carátula','Elegir un archivo de imagen compatible.')
    def installation_dialog(self):
        from .gui import label,button,wrap_row
        dialog=InlineDialog(title='Instalaciones y rutas',transient_for=self,modal=True);dialog.set_default_size(850,650);dialog.add_button('Cancelar',Gtk.ResponseType.CANCEL);dialog.add_button('Guardar y buscar',Gtk.ResponseType.OK)
        scroll=self.new_scroll();box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);box.set_border_width(20);scroll.add(box);dialog.get_content_area().pack_start(scroll,True,True,0)
        found=report(preferences=self.preferences);deck=found['emudeck']
        box.pack_start(label(('EmuDeck detectado' if deck['installed'] else 'EmuDeck no detectado. Elegir carpetas y emuladores instalados.')+'\nBiblioteca: '+deck['roms'],'title'),False,False,0)
        box.pack_start(label('Rutas adicionales para microSD, otra carpeta de Quiver o instalaciones portátiles. Una carpeta por línea.','muted'),False,False,0)
        buffers={}
        for key,title in [('rom_roots','Bibliotecas de ROMs (carpeta que contiene switch, wii, ps2…)'),('port_roots','Carpetas de ports'),('quiver_roots','Instalaciones de Quiver (carpeta con Apps)'),('prism_roots','Datos de Prism Launcher (carpeta con prismlauncher.cfg)'),('wiicompiled_roots','Datos de WiiCompiled (carpeta con Config.toml / Install)')]:
            row=Gtk.Box(spacing=8);row.pack_start(label(title),True,True,0)
            view=Gtk.TextView();view.set_size_request(-1,60);view.get_buffer().set_text('\n'.join(self.preferences.get(key,[])));buffers[key]=view.get_buffer()
            def choose(_,buffer=buffers[key]):
                picker=InlineFileChooser(title='Elegir carpeta',transient_for=dialog,action=Gtk.FileChooserAction.SELECT_FOLDER);picker.add_buttons('Cancelar',Gtk.ResponseType.CANCEL,'Agregar carpeta',Gtk.ResponseType.OK)
                if picker.run()==Gtk.ResponseType.OK:
                    current=buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True).strip();buffer.set_text(current+('\n' if current else '')+picker.get_filename())
                picker.destroy()
            row.pack_end(button('Agregar carpeta',choose),False,False,0);box.pack_start(row,False,False,0);box.pack_start(view,False,False,0)
        config=Gtk.Entry();config.set_text(self.preferences.get('eden_config',''));config.set_placeholder_text(str(pathlib.Path.home()/'.config/eden'));box.pack_start(label('Configuración de Eden (qt-config.ini)'),False,False,0);box.pack_start(config,False,False,0)
        row=Gtk.Box(spacing=8);row.pack_start(label('Emuladores instalados','title'),True,True,0);box.pack_start(row,False,False,0)
        emulator_commands=dict(self.preferences.get('emulators',{}));from .discovery import SYSTEMS
        used=set()
        for name,slug,flags,extensions in SYSTEMS.values():
            if slug in used:continue
            used.add(slug);row=Gtk.Box(spacing=10);program=found['emulators'].get(slug);text=Gtk.Label(label=name+' — '+(shlex.join(program['command']) if program else 'No detectado'),xalign=0);text.set_line_wrap(True);row.pack_start(text,True,True,0)
            def choose(_,key=slug,title=name,widget=text):
                path=self.pick_file('Elegir programa de '+title)
                if path:emulator_commands[key]=[path];widget.set_text(title+' — '+path)
            row.pack_end(button('Elegir programa',choose),False,False,0);box.pack_start(row,False,False,0)
        self.fit_dialog(dialog);dialog.show_all()
        if dialog.run()==Gtk.ResponseType.OK:
            for key,buffer in buffers.items():self.preferences[key]=list(dict.fromkeys(str(pathlib.Path(p.strip()).expanduser()) for p in buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True).splitlines() if p.strip()))
            self.preferences['emulators']=emulator_commands;self.preferences['eden_config']=config.get_text().strip();save_settings(self.preferences,self.store);self.toast('Carpetas y rutas guardadas');self.discover()
        dialog.destroy()
    def content_dialog(self,e):
        from .gui import label,button,wrap_row
        dialog=InlineDialog(title='Contenido de Switch · '+e.name,transient_for=self,modal=True);dialog.set_default_size(870,620);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(12);status=label('Leyendo contenido…','muted');box.pack_start(status,False,False,0);scroll=self.new_scroll();rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);scroll.add(rows);box.pack_start(scroll,True,True,0)
        def fill():
            inventory=switch_inventory(e,config_dir=self.preferences.get('eden_config') or None)
            for child in rows.get_children():rows.remove(child)
            rows.pack_start(label('Base: '+('disponible' if inventory['base']['available'] else 'falta el archivo')+' · Title ID: '+(inventory['title_id'] or 'No identificado'),'title'),False,False,0)
            rows.pack_start(label('Versión base: '+inventory['base']['version'],'muted'),False,False,0)
            cached=pathlib.Path.home()/'.cache/eden/game_list'/((inventory['title_id'] or 'unknown')+'.pv.txt')
            if cached.exists():rows.pack_start(label('Último contenido detectado por Eden:\n'+cached.read_text()[:1000],'muted'),False,False,0)
            for kind,title in [('updates','Actualizaciones'),('dlc','DLC')]:
                rows.pack_start(label(title+' ('+str(len(inventory[kind]))+')','title'),False,False,0)
                for item in inventory[kind]:
                    row=Gtk.Box(spacing=8);text=label(item['name']+'\n'+('Instalado en NAND' if item['installed'] else 'Archivo disponible; no registrado por Deck Library'));text.set_max_width_chars(65);row.pack_start(text,True,True,0)
                    if not item['installed']:
                        def install_(_,path=item['path']):self.install_content_job([path],status,fill,e)
                        row.pack_end(button('Instalar en Eden',install_),False,False,0)
                    rows.pack_start(row,False,False,0)
            rows.pack_start(label('Mods ('+str(len(inventory['mods']))+') · '+('activados para este acceso' if e.mods else 'desactivados para comparar'),'title'),False,False,0)
            for item in inventory['mods']:rows.pack_start(label(item['name']),False,False,0)
            rows.show_all();status.set_text('Los archivos originales y las partidas se conservan. Eden debe estar cerrado para instalar.')
        controls=Gtk.FlowBox();controls.set_selection_mode(Gtk.SelectionMode.NONE);controls.set_max_children_per_line(2);controls.set_min_children_per_line(1);box.pack_start(controls,False,False,0)
        def choose_nsp(_):
            path=self.pick_file('Elegir actualización o DLC (NSP)')
            if path:self.install_content_job([path],status,fill,e)
        def all_(_):
            inventory=switch_inventory(e,config_dir=self.preferences.get('eden_config') or None);paths=[p['path'] for kind in ('updates','dlc') for p in inventory[kind] if not p['installed']]
            self.install_content_job(paths,status,fill,e)
        controls.add(button('Elegir actualización / DLC',choose_nsp));controls.add(button('Instalar los pendientes',all_))
        def base_(_):
            path=self.pick_file('Elegir juego base NSP / XCI')
            if path:
                if pathlib.Path(path).suffix.lower() not in ('.nsp','.xci'):self.message('Archivo base','Elegir un NSP o XCI.');return
                e.source=path;e.cwd=str(pathlib.Path(path).parent)
                if '-g' in e.command:e.command[e.command.index('-g')+1]=path
                else:e.command[-1]=path
                self.store.save(self.entries);fill();self.render()
        controls.add(button('Elegir juego base',base_))
        def mod_(_):
            path=self.pick_file('Elegir mod LayeredFS ZIP')
            if path:
                status.set_text('Preparando mod…')
                def work():
                    try:install_mod_zip(path,e,self.store,self.preferences.get('eden_config') or None);GLib.idle_add(fill)
                    except Exception as error:GLib.idle_add(self.message,'No se pudo instalar el mod',str(error))
                threading.Thread(target=work,daemon=True).start()
        controls.add(button('Elegir mod ZIP',mod_))
        fill();self.fit_dialog(dialog);dialog.show_all();dialog.run();dialog.destroy()
    def install_content_job(self,paths,status,done,entry=None):
        if not paths:status.set_text('No hay contenido pendiente.');return
        status.set_text('Preparando instalación…')
        def work():
            try:
                for path in paths:
                    identity=nsp_identity(path)
                    if entry and identity['base_id'] and identity['base_id']!=switch_id(entry):raise ValueError('Este NSP corresponde a otro juego y no se instaló.')
                    if identity['kind']=='base':raise ValueError('Elegir una actualización o un DLC. Para la base, usar «Elegir juego base».')
                    install_nsp(path,self.preferences.get('eden_config') or None,lambda text:GLib.idle_add(status.set_text,text))
                GLib.idle_add(done)
            except Exception as error:GLib.idle_add(self.message,'Contenido de Eden',str(error));GLib.idle_add(status.set_text,'La instalación no se completó.')
        threading.Thread(target=work,daemon=True).start()
    def layout_dialog(self,e):
        from .gui import label,button,wrap_row
        dialog=InlineDialog(title='Controles recomendados · Minecraft',transient_for=self,modal=True);dialog.set_default_size(700,570);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE);box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(12)
        from .steam_input import local_profiles
        profiles=local_profiles(e)
        if profiles:
            profile=profiles[0];box.pack_start(label('Perfil guardado: '+profile['title'],'title'),False,False,0)
            summary=self.new_scroll();summary.set_size_request(-1,210);text=Gtk.TextView();text.set_editable(False);text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);text.get_buffer().set_text('\n'.join(control+' → '+action for control,action in profile['bindings'])+'\nModos: '+', '.join(profile['modes']));summary.add(text);box.pack_start(summary,True,True,0)
            box.pack_start(label('Steam conserva este perfil. El botón inferior abre sus controles; los cambios se hacen allí.','muted'),False,False,0)
        layout=next((p['layout'] for p in presets.catalog(self.store) if presets.compatible(e,p) and p.get('layout')),None)
        if layout and not profiles:
            box.pack_start(label('Steam Input · Teclado (WASD) y ratón','title'),False,False,0);box.pack_start(label('\n'.join(k+' → '+v for k,v in layout['bindings'].items())),True,True,0);box.pack_start(label(layout.get('notes',''),'muted'),False,False,0)
        elif not profiles:box.pack_start(label('No hay perfil local. Añadir un perfil con controles para esta instancia.'),False,False,0)
        def open_(_):
            from .steam import read_kv,get
            if not self.accounts:return
            try:
                shortcuts=read_kv((self.accounts[self.account.get_active()]/'shortcuts.vdf').read_bytes())['shortcuts'][1]
                item=next(v[1] for v in shortcuts.values() if get(v[1],'appid')==e.metadata.get('steam_appid') or get(v[1],'appname')==e.name);appid=get(item,'appid');subprocess.Popen(['steam','steam://controllerconfig/'+str(appid)])
                self.set_status('Controles abiertos en Steam.')
            except (OSError,ValueError,StopIteration):self.message('Instancia sin acceso','Guardar primero su acceso en Steam para abrir la configuración de controles.')
        box.pack_start(button('Abrir controles en Steam',open_,True),False,False,0);self.fit_dialog(dialog);dialog.show_all();dialog.run();dialog.destroy()
    def setup_wii_dialog(self):
        from .gui import label,button,wrap_row
        from .setup_wii import install,check_image
        dialog=InlineDialog(title='Preparar Mario Kart WiiCompiled',transient_for=self,modal=True);dialog.set_default_size(780,590);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE);box=dialog.get_content_area();box.set_border_width(20);box.set_spacing(15)
        box.pack_start(label('Imagen → recompilación → optimización → Steam','title'),False,False,0)
        box.pack_start(label('Requiere una imagen limpia de Mario Kart Wii PAL (RMCP01). Se descarga el setup oficial 0.2.33 y el SDK si falta. Usa unos 20 GB temporales, tarda bastante y no sobrescribe una instalación existente.','muted'),False,False,0)
        image=InlineFileButton(title='Elegir imagen de Mario Kart Wii',action=Gtk.FileChooserAction.OPEN);box.pack_start(image,False,False,0)
        setup=InlineFileButton(title='Setup oficial existente (opcional)',action=Gtk.FileChooserAction.OPEN);box.pack_start(label('Setup oficial ya descargado (opcional)','muted'),False,False,0);box.pack_start(setup,False,False,0)
        status=label('Elegir la imagen para comenzar.','status');box.pack_start(status,True,True,0);cancel=threading.Event();busy=[False]
        def start(_):
            try:check_image(image.get_filename() or '')
            except Exception as error:self.message('Imagen de Wii',str(error));return
            if busy[0]:return
            cancel.clear();chosen_image=image.get_filename();chosen_setup=setup.get_filename()
            busy[0]=True;start_button.set_sensitive(False);stop.set_sensitive(True)
            def work():
                try:
                    install(chosen_image,self.store,chosen_setup,lambda text:GLib.idle_add(status.set_text,text),cancel)
                    GLib.idle_add(self.finish_wii_setup,status)
                except Exception as error:GLib.idle_add(status.set_text,str(error)+'\nRegistro local: '+str(self.store.root/'wii-setup/install.log'))
                finally:busy[0]=False;GLib.idle_add(start_button.set_sensitive,True);GLib.idle_add(stop.set_sensitive,False)
            threading.Thread(target=work,daemon=True).start()
        actions=Gtk.Box(spacing=10);start_button=button('Preparar y optimizar',start,True);stop=button('Cancelar proceso',lambda _:cancel.set());stop.set_sensitive(False);actions.pack_start(start_button,False,False,0);actions.pack_start(stop,False,False,0);box.pack_start(actions,False,False,0)
        self.fit_dialog(dialog);dialog.show_all();dialog.run()
        if busy[0]:cancel.set()
        dialog.destroy()
    def finish_wii_setup(self,status):
        self.preferences=settings(self.store);self.entries=self.store.load();self.refresh_platforms();self.render();status.set_text('Listo. Mario Kart Wii ya está en la biblioteca y puede agregarse a Steam.');self.toast('Mario Kart Wii preparado');return False

    def project2099_dialog(self):
        from .gui import label,button,wrap_row
        from . import project2099
        dialog=InlineDialog(title='Preparar Project-2099',transient_for=self,modal=True)
        dialog.set_default_size(660,360);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_spacing(12);box.set_border_width(20)
        box.pack_start(label('Spider-Man: Edge of Time','title'),False,False,0)
        box.pack_start(label('Requiere la versión de Xbox 360; la de PS3 no es compatible. Descarga la última versión oficial, verifica sus archivos y la instala en español con Proton.','muted'),False,False,0)
        source=InlineFileButton(title='Elegir ISO, ZIP o 7z de Xbox 360',action=Gtk.FileChooserAction.OPEN)
        box.pack_start(source,False,False,0)
        destination=Gtk.Entry();destination.set_text(str(pathlib.Path.home()/'ports/project2099'))
        box.pack_start(label('Carpeta de destino vacía'),False,False,0);box.pack_start(destination,False,False,0)
        status=label('El juego se agrega a la biblioteca al terminar.');box.pack_start(status,False,False,0)
        busy=[False];key='GenryTheFox0/Project-2099';cancel=threading.Event();self.transfer_row(box,key)
        def done(entry,error):
            self.port_busy=False;getattr(self,'port_jobs',{}).pop(key,None);self.finish_transfer(key,error)
            busy[0]=False;start.set_sensitive(True);source.set_sensitive(True);destination.set_sensitive(True)
            dialog.set_response_sensitive(Gtk.ResponseType.CLOSE,True)
            if error:status.set_text(error)
            else:
                status.set_text('Instalado. Se puede agregar a Steam desde su ficha.');self.discover()
            return False
        def begin(_):
            if not source.get_filename():status.set_text('Elegir una ISO, ZIP o 7z de Xbox 360.');return
            selected=source.get_filename();target=destination.get_text();busy[0]=True
            if getattr(self,'port_busy',False):busy[0]=False;status.set_text('Ya hay una instalación en curso.');return
            self.port_busy=True;cancel.clear()
            if not hasattr(self,'port_jobs'):self.port_jobs={}
            self.port_jobs[key]=cancel;self.start_transfer(key);progress=self.port_progress(key)
            start.set_sensitive(False);source.set_sensitive(False);destination.set_sensitive(False);dialog.set_response_sensitive(Gtk.ResponseType.CLOSE,False)
            def work():
                try:
                    entry=project2099.prepare(selected,target,self.store,progress,cancel)
                    GLib.idle_add(done,entry,None)
                except Exception as error:GLib.idle_add(done,None,str(error))
            threading.Thread(target=work,daemon=True).start()
        start=button('Instalar',begin,True);box.pack_start(start,False,False,0)
        dialog.connect('delete-event',lambda *_:busy[0]);self.fit_dialog(dialog);dialog.show_all();dialog.run();dialog.destroy()
