"""Editable, local profile draft. No account or network is needed to capture settings."""
import json
from gi.repository import Gtk
from . import presets
from .ui_components import ActionButton,text

class ProfileComposer(Gtk.Box):
    def __init__(self,entry,store,config_dir=None,pick_file=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=10)
        self.entry=entry;self.store=store;self.config_dir=config_dir;self.draft=None
        self.pack_start(text('Compartir mis ajustes','section-title'),False,False,0)
        self.title=Gtk.Entry();self.title.set_text(entry.name+' — mis ajustes')
        self.pack_start(text('Nombre del perfil'),False,False,0);self.pack_start(self.title,False,False,0)
        self.objective=Gtk.ComboBoxText()
        for name in ('Equilibrado','Rendimiento','Calidad','Personalizado'):self.objective.append(name,name)
        self.objective.set_active_id('Personalizado')
        self.pack_start(text('Objetivo'),False,False,0);self.pack_start(self.objective,False,False,0)
        self.pack_start(ActionButton('Leer configuración del juego','sliders',lambda _:self.capture(),'violet-outline'),False,False,0)
        if pick_file:
            def load_file(_):
                path=pick_file('Leer ajustes de INI o TOML')
                if not path:return
                try:
                    from .profile_capture import read_file
                    values=read_file(entry,path);self.settings.get_buffer().set_text(json.dumps(values,indent=2,ensure_ascii=False));self.status.set_text('Opciones del archivo listas para revisar. El archivo original no se modifica.')
                except Exception as error:self.status.set_text(str(error))
            self.pack_start(ActionButton('Leer otro archivo de configuración','folder',load_file,'quiet'),False,False,0)
        self.status=text('Lee las opciones guardadas y sus valores globales heredados. No incluye controles, rutas ni cuentas.','muted',85)
        self.pack_start(self.status,False,False,0)
        before=len(self.get_children());self.settings=self.editor('Ajustes detectados · JSON editable',130)
        from .ui_components import Reveal
        advanced=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        for child in self.get_children()[before:]:
            self.remove(child);advanced.pack_start(child,False,False,0)
        self.settings_reveal=Reveal('Ver y editar las opciones detectadas',advanced);self.pack_start(self.settings_reveal,False,False,0)
        self.instructions=self.editor('Pasos, ajustes manuales o comandos (solo texto)',110)
        self.instructions.set_tooltip_text('Las instrucciones se muestran al usar el perfil. Deck Library no ejecuta estos comandos.')
        self.notes=self.editor('Resultado de las pruebas y observaciones',70)
        row=Gtk.Box(spacing=10);self.pack_start(row,False,False,0)
        self.runtime=Gtk.ComboBoxText()
        for key,name in (('native','Linux nativo'),('proton','Proton'),('steam','Administrado por Steam')):self.runtime.append(key,name)
        self.version=Gtk.Entry();self.version.set_placeholder_text('Versión de Proton (si corresponde)')
        row.pack_start(self.runtime,False,False,0);row.pack_start(self.version,True,True,0)
        self.launch=Gtk.Entry();self.launch.set_placeholder_text('Opciones de lanzamiento recomendadas · solo texto')
        self.pack_start(self.launch,False,False,0)
        self.program_version=Gtk.Entry();self.program_version.set_placeholder_text('Versión del emulador o port')
        self.pack_start(text('Versión del emulador o port'),False,False,0);self.pack_start(self.program_version,False,False,0)
        self.review=text('','muted',95);self.review.set_selectable(True);self.pack_start(self.review,False,False,0)
        self.capture()

    def editor(self,caption,height):
        self.pack_start(text(caption,'meta'),False,False,0)
        editor=Gtk.TextView();editor.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC);scroll.set_size_request(-1,height);scroll.add(editor)
        self.pack_start(scroll,False,False,0);return editor

    @staticmethod
    def read(editor):
        buf=editor.get_buffer();return buf.get_text(buf.get_start_iter(),buf.get_end_iter(),True).strip()

    def capture(self):
        try:
            value=presets.export_current(self.entry,self.title.get_text().strip(),'Usuario',self.store,self.config_dir)
            self.draft=value;self.settings.get_buffer().set_text(json.dumps(value['settings'],indent=2,ensure_ascii=False))
            self.instructions.get_buffer().set_text(value.get('instructions','') if value.get('instructions')!='Describí aquí los ajustes que probaste y los pasos para reproducirlos.' else '')
            info=value.get('runtime',{});self.runtime.set_active_id(info.get('kind','native'));self.version.set_text(info.get('version',''));self.program_version.set_text(', '.join(value['adapter']['versions']))
            count=sum(len(v) for v in value['settings'].values())
            self.status.set_text(f'{count} opciones leídas. Se pueden editar y agregar instrucciones.' if count else 'No hay opciones reconocidas para capturar. Escribir los pasos y el entorno de ejecución.')
        except Exception as error:
            self.draft=None;self.status.set_text(str(error)+' Se puede crear una guía manual.')
            self.settings.get_buffer().set_text('{}')
            from .profile_capture import runtime_info
            info=runtime_info(self.entry);self.runtime.set_active_id(info['kind']);self.version.set_text(info['version'])

    def profile(self,author='Usuario'):
        import copy,datetime,hashlib
        value=copy.deepcopy(self.draft)
        if value is None:
            game_id=presets.public_game_id(self.entry)
            if not game_id:raise ValueError('Completar el ID del juego antes de compartir.')
            value={'schema_version':1,'id':'draft-'+hashlib.sha256((self.entry.id+datetime.datetime.now().isoformat()).encode()).hexdigest()[:24],'game':{'id':game_id,'name':self.entry.name,'platform':self.entry.platform},'adapter':{'id':presets.adapter_for(self.entry),'versions':['unknown']},'hardware':['steam-deck-lcd','steam-deck-oled'],'license':'MIT','tested':{'status':'proposal','date':datetime.date.today().isoformat()},'sources':[]}
        value.update(name=self.title.get_text().strip(),objective=self.objective.get_active_id(),author=author,settings=json.loads(self.read(self.settings) or '{}'),instructions=self.read(self.instructions),notes=self.read(self.notes),runtime={'kind':self.runtime.get_active_id(),'version':self.version.get_text().strip(),'launch_options':self.launch.get_text().strip()})
        value['adapter']['versions']=[s.strip() for s in self.program_version.get_text().split(',') if s.strip()] or ['unknown']
        presets.validate(value)
        lines=[value['name'],'Autor: '+author,'Programa: '+value['adapter']['id']+' · '+', '.join(value['adapter']['versions']),'Entorno: '+value['runtime']['kind']+' '+value['runtime']['version'],'']
        for section,options in value['settings'].items():
            lines.extend(section+'.'+key+': '+str(setting) for key,setting in options.items())
        lines.extend(['',value['instructions'],value['runtime']['launch_options'],value['notes'],'','Revisar el texto antes de compartirlo: no incluir rutas personales, correos ni credenciales.'])
        self.review.set_text('\n'.join(lines));return value
