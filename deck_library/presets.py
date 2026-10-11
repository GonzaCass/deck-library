"""Portable, data-only presets with explicit adapters, backups and local feedback."""
import configparser,datetime,hashlib,json,os,pathlib,re,shutil,tempfile,tomllib,urllib.request
from .models import Store,atomic_json
from .content import switch_id,eden_paths,emulator_busy

REGISTRY={
 'project2099':{'runtime':{'window_width':(640,1920),'window_height':(360,1200),'fullscreen':bool,'gpu_backend':('d3d12',),'resolution_scale':(1,1),'eot_internal_scale':(1,1),'genry_eot_target_fps':(30,120),'d3d12_present_frame_limiter':bool,'d3d12_present_frame_limiter_fps':(30.0,120.0),'vsync':bool,'anisotropic_override':(0,5),'async_shader_compilation':bool,'store_shaders':bool,'input_backend':('xinput',),'mnk_mode':bool,'present_effect':('bilinear','cas','fsr','fsr2','fsr3'),'eot_pc_raster_glyphs':bool,'eot_pc_prompt_labels':bool,'show_fps_counter':bool}},
 'eden':{
  'Core':{'use_multi_core':bool,'use_speed_limit':bool,'speed_limit':(100,100),'sync_core_speed':bool},
  'Cpu':{'cpu_accuracy':(0,2),'use_custom_cpu_ticks':bool},
  'System':{'use_docked_mode':bool},
  'Renderer':{'backend':(0,1),'resolution_setup':(1,6),'aspect_ratio':(0,4),'anti_aliasing':(0,2),'scaling_filter':(0,5),'gpu_accuracy':(0,2),'dma_accuracy':(0,2),'vram_usage_mode':(0,2),'use_disk_shader_cache':bool,'use_vulkan_driver_pipeline_cache':bool,'use_asynchronous_gpu_emulation':bool,'use_asynchronous_shaders':bool,'async_presentation':bool,'use_vsync':(0,3),'force_max_clock':bool,'max_anisotropy':(0,5)}},
 'wiicompiled':{'video':{'resolution_multiplier':(1.0,3.0),'disable_copy_filter':bool,'frame_interpolation_fps':(0,0),'graphics_api':('vulkan','opengl'),'display_mode':('borderless','windowed','fullscreen'),'skip_unready_pipelines':bool,'show_fps':bool},'audio':{'mix_worker':bool}},
 'dolphin':{'Video_Settings':{'InternalResolution':(1,4),'MSAA':(0,8),'SSAA':bool,'MaxAnisotropy':(0,4)},'Video_Hacks':{'EFBScaledCopy':bool,'EFBAccessEnable':bool,'EFBToTextureEnable':bool}},
 'duckstation':{
  'GPU':{'ResolutionScale':(1,16),'Multisamples':(1,16),'TextureFilter':('Nearest','Bilinear','BilinearBinAlpha','JINC2','JINC2BinAlpha','xBR','xBRBinAlpha'),'TrueColor':bool,'ScaledDithering':bool,'WidescreenHack':bool,'DisableInterlacing':bool,'ForceNTSCTimings':bool,'ChromaSmoothing24Bit':bool,'PGXPEnable':bool,'PGXPCulling':bool,'PGXPTextureCorrection':bool,'PGXPColorCorrection':bool,'PGXPDepthBuffer':bool,'PGXPCPU':bool,'PGXPPreserveProjFP':bool,'PGXPVertexCache':bool},
  'Display':{'MaxFPS':(0.0,300.0),'VSync':bool,'IntegerScaling':bool,'LinearFiltering':bool,'ShowFPS':bool},
  'CPU':{'OverclockEnable':bool,'OverclockNumerator':(1,500),'OverclockDenominator':(1,100)},
  'CDROM':{'ReadSpeedup':(1,10),'LoadImageToRAM':bool,'LoadImagePatches':bool}},
 'prism':{'General':{'OverrideMemory':bool,'MinMemAlloc':(512,8192),'MaxMemAlloc':(1024,8192),'OverrideWindow':bool,'MinecraftWinWidth':(640,2560),'MinecraftWinHeight':(360,1600),'LaunchMaximized':bool}}
}

def adapter_for(entry):
    return entry.metadata.get('adapter') or {'Switch':'eden','WiiCompiled':'wiicompiled','Minecraft':'prism','Wii':'dolphin','GameCube':'dolphin','PlayStation':'duckstation'}.get(entry.platform,'')

SERIAL=re.compile(rb'BOOT\s*=\s*cdrom:\\?([A-Z]{4})_(\d{3})\.(\d{2})',re.I)

def ps1_serial(path):
    """Serial from SYSTEM.CNF in a plain BIN/ISO/IMG (or the first track of a CUE). CHD/PBP need it set by hand."""
    path=pathlib.Path(path)
    try:
        if path.suffix.lower()=='.cue':
            track=re.search(r'FILE\s+"([^"]+)"',path.read_text(errors='replace'))
            if not track:return ''
            path=path.parent/track[1]
        if path.suffix.lower() not in ('.bin','.iso','.img'):return ''
        with open(path,'rb') as source:data=source.read(4*1024*1024)
    except OSError:return ''
    match=SERIAL.search(data)
    return (match[1]+b'-'+match[2]+match[3]).decode().upper() if match else ''

PROCESSES={'eden':('eden',),'wiicompiled':('WiiCompiled',),'dolphin':('dolphin-emu',),'prism':('java',),'project2099':('SpiderManEOT.exe','SpiderManEOT.ex'),'duckstation':('duckstation-qt','duckstation-nogui')}

def busy(adapter):return any(emulator_busy(name) for name in PROCESSES.get(adapter,('unknown',)))

def public_game_id(entry):
    if entry.platform=='Switch':return switch_id(entry)
    if adapter_for(entry)=='prism':return 'minecraft-java'
    if entry.game_id:return entry.game_id
    if adapter_for(entry)=='wiicompiled':return 'RMCP01'
    if adapter_for(entry)=='duckstation':return ps1_serial(entry.source)
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
    if not isinstance(url,str) or not url.startswith('https://'):raise ValueError('Se requiere la URL HTTPS raw de un catálogo JSON.')
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
    if adapter=='project2099':
        return pathlib.Path(entry.source).parent/'spider_man_edge_of_time.toml'
    if adapter=='wiicompiled':
        path=entry.metadata.get('config')
        if not path:raise ValueError('Indicar la instalación de WiiCompiled en Instalaciones y rutas.')
        return pathlib.Path(path)
    if adapter=='prism':return pathlib.Path(entry.source)
    if adapter=='dolphin':
        tid=public_game_id(entry)
        if not re.fullmatch('[A-Z0-9]{6}',tid):raise ValueError('Falta el ID de juego de Dolphin.')
        roots=[home/'.var/app/org.DolphinEmu.dolphin-emu/data/dolphin-emu',home/'.local/share/dolphin-emu']
        return next((p for p in roots if p.exists()),roots[-1])/'GameSettings'/(tid+'.ini')
    if adapter=='duckstation':
        serial=public_game_id(entry)
        if not re.fullmatch(r'[A-Z]{4}-\d{5}',serial.upper()):raise ValueError('Falta el serial del juego (por ejemplo SLES-01234). Se detecta en BIN/ISO; en CHD hay que ingresarlo en Editar juego.')
        roots=[home/'.local/share/duckstation',home/'.var/app/org.duckstation.DuckStation/config/duckstation',home/'.config/duckstation']
        return next((p for p in roots if (p/'settings.ini').exists()),roots[0])/'gamesettings'/(serial.upper()+'.ini')
    raise ValueError('Este programa todavía no tiene adaptador de ajustes.')

def ini_parser(text):
    parser=configparser.ConfigParser(interpolation=None,strict=False);parser.optionxform=str
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

def patch_ini(text,updates,spaced=False):
    """Edit only the given keys, line by line. Repeated keys, comments, order and other sections stay as they were."""
    out=[];section=None;seen=set();known=set()
    def flush(name):
        trailing=[]
        while out and not out[-1].strip():trailing.append(out.pop())
        for key,value in updates.get(name,{}).items():
            if (name,key) not in seen:out.append(key+(' = ' if spaced else '=')+scalar(value));seen.add((name,key))
        out.extend(trailing)
    for line in text.splitlines():
        header=re.fullmatch(r'\s*\[([^]]+)\]\s*',line)
        if header:
            flush(section);section=header[1];known.add(section);out.append(line);continue
        match=re.match(r'(\s*)([^=;#\[\s][^=]*?)(\s*=\s*)(.*)$',line)
        if section in updates and match and match[2] in updates[section]:
            line=match[1]+match[2]+match[3]+scalar(updates[section][match[2]]);seen.add((section,match[2]))
        out.append(line)
    flush(section)
    for name in updates:
        if name not in known:
            out+=['','['+name+']'];flush(name)
    return '\n'.join(out).strip('\n')+'\n'

def preview(entry,value,config_dir=None):
    if not compatible(entry,value):raise ValueError('El preset no corresponde a este juego o programa.')
    path=target_for(entry,config_dir);old=path.read_text() if path.exists() else '';adapter=adapter_for(entry)
    previous=tomllib.loads(old) if adapter in ('wiicompiled','project2099') else ini_parser(old);changes=[]
    for section,items in value['settings'].items():
        current=(previous if adapter=='project2099' else previous.get(section,{})) if isinstance(previous,dict) else previous[section] if previous.has_section(section) else {}
        for key,new in items.items():changes.append((section+'.'+key,current.get(key,'predeterminado'),new))
    return path,changes

def apply(entry,value,store=None,config_dir=None):
    path,changes=preview(entry,value,config_dir);adapter=adapter_for(entry)
    if busy(adapter):raise RuntimeError('El juego o programa debe estar cerrado para aplicar un perfil.')
    current=entry.metadata.get('build') or entry.metadata.get('emulator_version')
    if current and current not in value['adapter']['versions']:raise ValueError('Este preset no declara compatibilidad con la versión instalada: '+current)
    old=path.read_text() if path.exists() else '';store=store or Store();stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f');backup=store.root/'preset-backups'/entry.id/stamp;backup.mkdir(parents=True,exist_ok=True)
    (backup/'original').write_text(old)
    if adapter=='project2099':new=patch_root_toml(old,value['settings']['runtime'])
    elif adapter=='wiicompiled':new=patch_toml(old,value['settings'])
    else:
        updates={}
        for section,items in value['settings'].items():
            for key,setting in items.items():
                updates.setdefault(section,{})[key]=setting
                if adapter=='eden':updates[section][key+'\\default']='false';updates[section][key+'\\use_global']='false'
        new=patch_ini(old,updates,spaced=adapter=='duckstation')
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
    if busy(adapter_for(entry)):raise RuntimeError('El juego debe estar cerrado para restaurar.')
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=value['sha256']:raise ValueError('La configuración cambió después del preset. El backup se conservó; no se sobrescribieron esos cambios.')
    if value['existed']:target.write_bytes((backup/'original').read_bytes())
    else:target.unlink()
    (store.root/'applied-presets'/(entry.id+'.json')).unlink()
    return str(backup)

def export_current(entry,name,author,store=None,config_dir=None):
    adapter=adapter_for(entry);target=target_for(entry,config_dir);text=target.read_text();parser=tomllib.loads(text) if adapter in ('wiicompiled','project2099') else ini_parser(text);values={}
    for section,options in REGISTRY[adapter].items():
        group=(parser if adapter=='project2099' else parser.get(section,{})) if isinstance(parser,dict) else parser[section] if parser.has_section(section) else {}
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
    if not game_id:raise ValueError('Falta el ID público del juego para exportar.')
    revision=datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    result={'schema_version':1,'id':adapter+'-'+game_id.lower()+'-'+revision,'name':name,'game':{'id':game_id,'name':entry.name,'platform':entry.platform},'adapter':{'id':adapter,'versions':[entry.metadata.get('build') or entry.metadata.get('emulator_version') or 'unknown']},'hardware':['steam-deck-lcd','steam-deck-oled'],'objective':'Configuración compartida para recibir feedback','author':author,'license':'MIT','tested':{'status':'proposal','date':datetime.date.today().isoformat()},'settings':values,'notes':'Verificar la versión del programa y probar el perfil antes de recomendarlo.','sources':[]}
    return validate(result)

def feedback(entry,value,result,notes,store=None):
    if result not in ('works','issues','not-tested') or len(notes)>2000:raise ValueError('Feedback inválido.')
    value=validate(value);store=store or Store()
    report={'schema_version':1,'preset_id':value['id'],'game_id':public_game_id(entry),'result':result,'notes':notes,'date':datetime.date.today().isoformat()}
    path=store.root/'feedback'/(value['id']+'.json');atomic_json(path,report);return report


def patch_root_toml(text,updates):
    """Change allowlisted root scalars, retaining unrelated keys and sections."""
    tomllib.loads(text)
    root=True;seen=set();out=[]
    def missing():
        for key,value in updates.items():
            if key not in seen:
                out.append(key+' = '+json.dumps(value));seen.add(key)
    for line in text.splitlines():
        if root and re.match(r'\s*\[',line):missing();root=False
        match=re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=',line)
        if root and match and match[1] in updates:
            line=match[1]+' = '+json.dumps(updates[match[1]]);seen.add(match[1])
        out.append(line)
    if root:missing()
    result='\n'.join(out)+'\n';tomllib.loads(result);return result


def global_values(entry):
    """Emulator-wide values used when a game has no override of its own (DuckStation only)."""
    if adapter_for(entry)!='duckstation':return {}
    path=target_for(entry).parent.parent/'settings.ini'
    try:return {s:dict(v) for s,v in ini_parser(path.read_text()).items()}
    except OSError:return {}

def typed(rule,raw):
    """Convert an INI string to the registry's type, or None when it does not fit."""
    try:
        if rule is bool:
            if str(raw).lower() not in ('true','false','0','1'):return None
            return str(raw).lower() in ('true','1')
        if isinstance(rule[0],str):return str(raw) if str(raw) in rule else None
        value=float(raw) if type(rule[0]) is float else int(float(raw))
        return value if rule[0]<=value<=rule[1] else None
    except (TypeError,ValueError):return None

def current_values(entry,config_dir=None):
    """Effective values for the manual editor: game file over emulator-wide settings."""
    adapter=adapter_for(entry);path=target_for(entry,config_dir);fallback=global_values(entry)
    text=path.read_text() if path.exists() else ''
    if adapter in ('wiicompiled','project2099'):raise ValueError('Este programa se edita solo con perfiles.')
    local=ini_parser(text);result={}
    for section,options in REGISTRY[adapter].items():
        for key,rule in options.items():
            raw=local[section][key] if local.has_section(section) and key in local[section] else fallback.get(section,{}).get(key)
            if adapter=='eden' and local.has_section(section) and local[section].get(key+'\\use_global')=='true':raw=None
            value=None if raw is None else typed(rule,raw)
            if value is not None:result.setdefault(section,{})[key]=value
    return result

def manual_profile(entry,changes,config_dir=None):
    """Wrap hand-edited values in a regular, validated profile so apply/backup/restore are shared."""
    game_id=public_game_id(entry)
    if not game_id:raise ValueError('Falta el identificador del juego.')
    adapter=adapter_for(entry)
    value={'schema_version':1,'id':'manual-'+hashlib.sha256((entry.id+json.dumps(changes,sort_keys=True)).encode()).hexdigest()[:12],'name':'Ajustes manuales','game':{'id':game_id,'name':entry.name,'platform':entry.platform},'adapter':{'id':adapter,'versions':[entry.metadata.get('build') or entry.metadata.get('emulator_version') or 'unknown']},'hardware':['steam-deck-lcd','steam-deck-oled'],'objective':'Ajustes manuales del usuario','author':'Usuario','license':'MIT','tested':{'status':'proposal','date':datetime.date.today().isoformat()},'settings':changes}
    return validate(value)
