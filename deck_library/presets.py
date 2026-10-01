"""Portable, data-only presets with explicit adapters, backups and local feedback."""
import configparser,datetime,hashlib,json,os,pathlib,re,shutil,tempfile,tomllib,urllib.request
from .models import Store,atomic_json
from .content import switch_id,eden_paths,emulator_busy

REGISTRY={
 'eden':{
  'Core':{'use_multi_core':bool,'use_speed_limit':bool,'speed_limit':(100,100),'sync_core_speed':bool},
  'Cpu':{'cpu_accuracy':(0,2),'use_custom_cpu_ticks':bool},
  'System':{'use_docked_mode':bool},
  'Renderer':{'backend':(0,1),'resolution_setup':(1,6),'aspect_ratio':(0,4),'anti_aliasing':(0,2),'scaling_filter':(0,5),'gpu_accuracy':(0,2),'dma_accuracy':(0,2),'vram_usage_mode':(0,2),'use_disk_shader_cache':bool,'use_vulkan_driver_pipeline_cache':bool,'use_asynchronous_gpu_emulation':bool,'use_asynchronous_shaders':bool,'async_presentation':bool,'use_vsync':(0,3),'force_max_clock':bool,'max_anisotropy':(0,5)}},
 'wiicompiled':{'video':{'resolution_multiplier':(1.0,3.0),'disable_copy_filter':bool,'frame_interpolation_fps':(0,0),'graphics_api':('vulkan','opengl'),'display_mode':('borderless','windowed','fullscreen'),'skip_unready_pipelines':bool,'show_fps':bool},'audio':{'mix_worker':bool}},
 'dolphin':{'Video_Settings':{'InternalResolution':(1,4),'MSAA':(0,8),'SSAA':bool,'MaxAnisotropy':(0,4)},'Video_Hacks':{'EFBScaledCopy':bool,'EFBAccessEnable':bool,'EFBToTextureEnable':bool}},
 'prism':{'General':{'OverrideMemory':bool,'MinMemAlloc':(512,8192),'MaxMemAlloc':(1024,8192),'OverrideWindow':bool,'MinecraftWinWidth':(640,2560),'MinecraftWinHeight':(360,1600),'LaunchMaximized':bool}}
}

def adapter_for(entry):
    return entry.metadata.get('adapter') or {'Switch':'eden','WiiCompiled':'wiicompiled','Minecraft':'prism','Wii':'dolphin','GameCube':'dolphin'}.get(entry.platform,'')

def public_game_id(entry):
    if entry.platform=='Switch':return switch_id(entry)
    if adapter_for(entry)=='prism':return 'minecraft-java'
    if entry.game_id:return entry.game_id
    if adapter_for(entry)=='wiicompiled':return 'RMCP01'
    if entry.source.lower().endswith('.iso') and entry.platform in ('Wii','GameCube'):
        try:
            with open(entry.source,'rb') as source:disc=source.read(6).decode('ascii')
            if re.fullmatch('[A-Z0-9]{6}',disc):return disc
        except (OSError,UnicodeError):pass
    return ''

def validate(value):
    if not isinstance(value,dict) or value.get('schema_version')!=1:raise ValueError('Versión de preset no compatible.')
    allowed={'schema_version','id','name','game','adapter','hardware','objective','author','license','tested','settings','notes','sources','layout'}
    if set(value)-allowed:raise ValueError('El preset incluye campos desconocidos.')
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,79}',value.get('id','')):raise ValueError('ID de preset inválido.')
    for key in ('name','objective','author','license'):
        if not isinstance(value.get(key),str) or not 1<=len(value[key])<=200:raise ValueError('Falta '+key+' o es inválido.')
    game=value.get('game',{});adapter=value.get('adapter',{})
    if not isinstance(game,dict) or set(game)-{'id','name','platform','update'} or not re.fullmatch(r'[A-Za-z0-9._-]{1,80}',game.get('id','')):raise ValueError('Identidad de juego inválida.')
    if not isinstance(adapter,dict) or set(adapter)-{'id','versions'} or adapter.get('id') not in REGISTRY:raise ValueError('Adaptador no soportado.')
    versions=adapter.get('versions',[])
    if not isinstance(versions,list) or not versions or any(not isinstance(v,str) or not re.fullmatch(r'[0-9A-Za-z.+_-]{1,40}',v) for v in versions):raise ValueError('El preset debe declarar versiones del programa.')
    hardware=value.get('hardware',[])
    if not isinstance(hardware,list) or not hardware or any(v not in ('steam-deck-lcd','steam-deck-oled','linux-pc') for v in hardware):raise ValueError('Hardware de preset inválido.')
    tested=value.get('tested',{})
    if not isinstance(tested,dict) or set(tested)-{'status','date','notes'} or tested.get('status') not in ('proposal','boot-tested','user-confirmed'):raise ValueError('Estado de prueba inválido.')
    if not isinstance(value.get('notes',''),str) or len(value.get('notes',''))>4000:raise ValueError('Notas inválidas.')
    sources=value.get('sources',[])
    if not isinstance(sources,list) or len(sources)>20 or any(not isinstance(u,str) or len(u)>1000 or not u.startswith('https://') for u in sources):raise ValueError('Fuentes inválidas.')
    settings=value.get('settings');registry=REGISTRY[adapter['id']]
    if not isinstance(settings,dict) or not settings:raise ValueError('El preset no tiene ajustes.')
    for section,options in settings.items():
        if section not in registry or not isinstance(options,dict) or not options:raise ValueError('Sección no permitida: '+section)
        for key,setting in options.items():
            rule=registry[section].get(key)
            if rule is None:raise ValueError('Ajuste no permitido: '+key)
            if rule is bool:valid=type(setting) is bool
            elif isinstance(rule[0],str):valid=setting in rule
            else:valid=type(setting) in (int,float) and rule[0]<=setting<=rule[1] and (type(rule[0]) is float or type(setting) is int)
            if not valid:raise ValueError('Valor fuera de rango: '+key)
    layout=value.get('layout')
    if layout is not None:
        if not isinstance(layout,dict) or set(layout)-{'template','bindings','notes'} or layout.get('template') not in ('keyboard-mouse','gamepad'):raise ValueError('Layout inválido.')
        bindings=layout.get('bindings',{})
        if not isinstance(bindings,dict) or len(bindings)>30 or any(not isinstance(k,str) or not isinstance(v,str) or len(k)>60 or len(v)>100 for k,v in bindings.items()):raise ValueError('Bindings inválidos.')
    # No paths, credentials or executable commands are allowed anywhere in the schema.
    if any(len(json.dumps(v))>12000 for v in (game,tested,layout or {})):raise ValueError('Metadata demasiado grande.')
    return value

def compatible(entry,value):
    validate(value)
    return adapter_for(entry)==value['adapter']['id'] and public_game_id(entry).lower()==value['game']['id'].lower()

def catalog(store=None):
    store=store or Store();by_id={}
    for folder in (pathlib.Path(__file__).resolve().parent.parent/'presets',store.root/'presets'):
        for path in sorted(folder.glob('*.json')):
            try:
                if path.stat().st_size>128*1024:continue
                value=validate(json.loads(path.read_text()));by_id[value['id']]=value
            except (OSError,ValueError,TypeError,KeyError):continue
    return list(by_id.values())

def import_preset(path,store=None):
    store=store or Store();path=pathlib.Path(path)
    if path.stat().st_size>128*1024:raise ValueError('El preset supera 128 KiB.')
    value=validate(json.loads(path.read_text()));atomic_json(store.root/'presets'/(value['id']+'.json'),value);return value

def refresh_catalog(url,store=None):
    if not isinstance(url,str) or not url.startswith('https://'):raise ValueError('Usá la URL HTTPS raw de un catálogo JSON.')
    request=urllib.request.Request(url,headers={'User-Agent':'DeckLibrary/0.2.0'})
    with urllib.request.urlopen(request,timeout=15) as response:
        if not response.url.startswith('https://'):raise ValueError('La redirección no usa HTTPS.')
        data=response.read(1024*1024+1)
    if len(data)>1024*1024:raise ValueError('El catálogo supera 1 MiB.')
    document=json.loads(data)
    if document.get('schema_version')!=1 or not isinstance(document.get('presets'),list) or len(document['presets'])>1000:raise ValueError('Catálogo inválido.')
    values=[validate(v) for v in document['presets']];store=store or Store()
    # Validate the entire download before publishing any profile locally.
    for value in values:atomic_json(store.root/'presets'/(value['id']+'.json'),value)
    return len(values)

def target_for(entry,config_dir=None):
    adapter=adapter_for(entry);home=pathlib.Path.home()
    if adapter=='eden':
        tid=public_game_id(entry)
        if not re.fullmatch(r'010[0-9A-Fa-f]{13}',tid):raise ValueError('Falta el Title ID; completalo en Editar acceso.')
        return eden_paths(config_dir=config_dir)['config']/'custom'/(tid.upper()+'.ini')
    if adapter=='wiicompiled':
        path=entry.metadata.get('config')
        if not path:raise ValueError('Indicá la instalación de WiiCompiled en Instalaciones y rutas.')
        return pathlib.Path(path)
    if adapter=='prism':return pathlib.Path(entry.source)
    if adapter=='dolphin':
        tid=public_game_id(entry)
        if not re.fullmatch('[A-Z0-9]{6}',tid):raise ValueError('Falta el ID de juego de Dolphin.')
        roots=[home/'.var/app/org.DolphinEmu.dolphin-emu/data/dolphin-emu',home/'.local/share/dolphin-emu']
        return next((p for p in roots if p.exists()),roots[-1])/'GameSettings'/(tid+'.ini')
    raise ValueError('Este programa todavía no tiene adaptador de ajustes.')

def ini_parser(text):
    parser=configparser.ConfigParser(interpolation=None);parser.optionxform=str
    if text.strip():parser.read_string(text)
    return parser

def scalar(value):return str(value).lower() if type(value) is bool else str(value)

def patch_toml(text,updates):
    tomllib.loads(text);section='';seen={s:set() for s in updates};out=[];sections=set()
    def missing(s):
        if s in updates:
            for k,v in updates[s].items():
                if k not in seen[s]:out.append(k+' = '+json.dumps(v));seen[s].add(k)
    for line in text.splitlines():
        match=re.fullmatch(r'\s*\[([^]]+)\]\s*',line)
        if match:missing(section);section=match[1];sections.add(section)
        key=re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=',line)
        if section in updates and key and key[1] in updates[section]:line=key[1]+' = '+json.dumps(updates[section][key[1]]);seen[section].add(key[1])
        out.append(line)
    missing(section)
    for s in updates:
        if s not in sections:out+=['','['+s+']'];missing(s)
    value='\n'.join(out)+'\n';tomllib.loads(value);return value

def preview(entry,value,config_dir=None):
    if not compatible(entry,value):raise ValueError('El preset no corresponde a este juego o programa.')
    path=target_for(entry,config_dir);old=path.read_text() if path.exists() else '';adapter=adapter_for(entry)
    previous=tomllib.loads(old) if adapter=='wiicompiled' else ini_parser(old);changes=[]
    for section,items in value['settings'].items():
        current=previous.get(section,{}) if isinstance(previous,dict) else previous[section] if previous.has_section(section) else {}
        for key,new in items.items():changes.append((section+'.'+key,current.get(key,'predeterminado'),new))
    return path,changes

def apply(entry,value,store=None,config_dir=None):
    path,changes=preview(entry,value,config_dir);adapter=adapter_for(entry)
    process={'eden':'eden','wiicompiled':'WiiCompiled','dolphin':'dolphin-emu','prism':'java'}[adapter]
    if emulator_busy(process):raise RuntimeError('Cerrá el juego/programa antes de aplicar un preset.')
    current=entry.metadata.get('build') or entry.metadata.get('emulator_version')
    if current and current not in value['adapter']['versions']:raise ValueError('Este preset no declara compatibilidad con la versión instalada: '+current)
    old=path.read_text() if path.exists() else '';store=store or Store();stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f');backup=store.root/'preset-backups'/entry.id/stamp;backup.mkdir(parents=True,exist_ok=True)
    (backup/'original').write_text(old)
    if adapter=='wiicompiled':new=patch_toml(old,value['settings'])
    else:
        parser=ini_parser(old)
        for section,items in value['settings'].items():
            if not parser.has_section(section):parser.add_section(section)
            for key,setting in items.items():
                parser[section][key]=scalar(setting)
                if adapter=='eden':parser[section][key+'\\default']='false';parser[section][key+'\\use_global']='false'
        import io
        buffer=io.StringIO();parser.write(buffer,space_around_delimiters=False);new=buffer.getvalue()
    path.parent.mkdir(parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix='.preset-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as out:out.write(new);out.flush();os.fsync(out.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
    atomic_json(backup/'record.json',{'target':str(path),'existed':bool(old),'preset':value['id'],'sha256':hashlib.sha256(new.encode()).hexdigest()})
    atomic_json(store.root/'applied-presets'/(entry.id+'.json'),{'backup':str(backup),'preset':value['id']})
    return {'backup':str(backup),'changes':len(changes)}

def restore(entry,store=None):
    store=store or Store();record=json.loads((store.root/'applied-presets'/(entry.id+'.json')).read_text());backup=pathlib.Path(record['backup']);value=json.loads((backup/'record.json').read_text());target=pathlib.Path(value['target'])
    if emulator_busy({'eden':'eden','wiicompiled':'WiiCompiled','dolphin':'dolphin-emu','prism':'java'}.get(adapter_for(entry),'unknown')):raise RuntimeError('Cerrá el juego antes de restaurar.')
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=value['sha256']:raise ValueError('La configuración cambió después del preset. El backup se conservó; no se sobrescribieron esos cambios.')
    if value['existed']:target.write_bytes((backup/'original').read_bytes())
    else:target.unlink()
    (store.root/'applied-presets'/(entry.id+'.json')).unlink()
    return str(backup)

def export_current(entry,name,author,store=None,config_dir=None):
    adapter=adapter_for(entry);target=target_for(entry,config_dir);text=target.read_text();parser=tomllib.loads(text) if adapter=='wiicompiled' else ini_parser(text);values={}
    for section,options in REGISTRY[adapter].items():
        group=parser.get(section,{}) if isinstance(parser,dict) else parser[section] if parser.has_section(section) else {}
        for key,rule in options.items():
            if key not in group:continue
            if adapter=='eden' and group.get(key+'\\use_global')=='true':continue
            raw=group[key]
            if rule is bool:
                if str(raw).lower() not in ('true','false','0','1'):continue
                value=str(raw).lower() in ('true','1')
            elif isinstance(rule[0],str):value=str(raw)
            else:
                try:value=float(raw) if type(rule[0]) is float else int(raw)
                except (TypeError,ValueError):continue
            values.setdefault(section,{})[key]=value
    game_id=public_game_id(entry)
    if not game_id:raise ValueError('Completá un ID público del juego antes de exportar.')
    revision=datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    result={'schema_version':1,'id':adapter+'-'+game_id.lower()+'-'+revision,'name':name,'game':{'id':game_id,'name':entry.name,'platform':entry.platform},'adapter':{'id':adapter,'versions':[entry.metadata.get('build') or entry.metadata.get('emulator_version') or 'unknown']},'hardware':['steam-deck-lcd','steam-deck-oled'],'objective':'Configuración compartida para recibir feedback','author':author,'license':'MIT','tested':{'status':'proposal','date':datetime.date.today().isoformat()},'settings':values,'notes':'Revisá la versión del programa y probá el preset antes de recomendarlo.','sources':[]}
    return validate(result)

def feedback(entry,value,result,notes,store=None):
    if result not in ('works','issues','not-tested') or len(notes)>2000:raise ValueError('Feedback inválido.')
    value=validate(value);store=store or Store()
    report={'schema_version':1,'preset_id':value['id'],'game_id':public_game_id(entry),'result':result,'notes':notes,'date':datetime.date.today().isoformat()}
    path=store.root/'feedback'/(value['id']+'.json');atomic_json(path,report);return report
