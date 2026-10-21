"""Resolve emulator settings locally; portable profiles contain only allowlisted values."""
import hashlib,pathlib,re

ROOTS={
 'pcsx2':('.config/PCSX2','.var/app/net.pcsx2.PCSX2/config/PCSX2'),
 'azahar':('.config/azahar-emu','.config/azahar','.var/app/org.azahar_emu.Azahar/config/azahar-emu','.var/app/org.azahar_emu.Azahar/config/azahar','.config/citra-emu','.var/app/org.citra_emu.citra/config/citra-emu'),
 'mgba':('.config/mgba','.var/app/io.mgba.mGBA/config/mgba'),
 'ppsspp':('.config/ppsspp/PSP/SYSTEM','.var/app/org.ppsspp.PPSSPP/config/ppsspp/PSP/SYSTEM'),
}
GLOBALS={'pcsx2':'inis/PCSX2.ini','azahar':'qt-config.ini','mgba':'config.ini','ppsspp':'ppsspp.ini'}

def root_for(entry,adapter):
    custom=entry.metadata.get('emulator_config_dir')
    if custom:return pathlib.Path(custom)
    roots=[pathlib.Path.home()/p for p in ROOTS[adapter]]
    return next((p for p in roots if (p/GLOBALS[adapter]).is_file()),next((p for p in roots if p.is_dir()),roots[0]))

def serial(entry,adapter):
    pattern=r'[A-Z]{4}-\d{5}' if adapter=='pcsx2' else r'[A-Z]{4}\d{5}'
    raw=entry.game_id or entry.metadata.get('serial','')
    if re.fullmatch(pattern,raw.upper()):return raw.upper()
    match=re.search(pattern,pathlib.Path(entry.source).name.upper())
    if match:return match[0]
    if adapter=='pcsx2' and pathlib.Path(entry.source).suffix.lower()=='.iso':
        try:
            with open(entry.source,'rb') as source:data=source.read(4*1024*1024)
            match=re.search(rb'BOOT2\s*=\s*cdrom0?:\\?([A-Z]{4})_(\d{3})\.(\d{2})',data,re.I)
            if match:return (match[1]+b'-'+match[2]+match[3]).decode().upper()
        except OSError:pass
    return ''

def game_target(entry,adapter):
    root=root_for(entry,adapter)
    if adapter=='pcsx2':
        identity=serial(entry,adapter);crc=str(entry.metadata.get('crc','')).upper()
        if identity and re.fullmatch('[0-9A-F]{8}',crc):return root/'gamesettings'/(identity+'_'+crc+'.ini')
        matches=list((root/'gamesettings').glob(identity+'_????????.ini')) if identity else []
        if len(matches)==1:return matches[0]
        raise ValueError('PCSX2 necesita el serial y CRC del juego. Crear sus ajustes por juego en PCSX2 para identificar el archivo; la lectura global sigue disponible.')
    if adapter=='azahar':
        tid=entry.game_id or entry.metadata.get('title_id','')
        if not re.fullmatch('[0-9A-Fa-f]{16}',tid):
            try:
                with open(entry.source,'rb') as stream:
                    stream.seek(0x100);magic=stream.read(4)
                    offset=0 if magic==b'NCCH' else 0x4000 if magic==b'NCSD' else None
                    if offset is not None:
                        stream.seek(offset+0x118);raw=stream.read(8)
                        if len(raw)==8:tid=f'{int.from_bytes(raw,"little"):016X}'
            except OSError:pass
        if re.fullmatch('0004[0-9A-Fa-f]{12}',tid):return root/'custom'/(tid.upper()+'.ini')
        raise ValueError('Falta el Title ID de Nintendo 3DS; completarlo en Editar acceso.')
    if adapter=='ppsspp':
        identity=serial(entry,adapter)
        if not identity:raise ValueError('Falta el ID de PSP (por ejemplo ULUS10567); completarlo en Editar acceso.')
        return root/(identity+'_ppsspp.ini')
    raise ValueError('mGBA se captura como referencia. Sus opciones globales se cambian desde el emulador.')

def fallback_id(entry):
    project=entry.metadata.get('port_repository','')
    identity=project.lower() if project else entry.platform.casefold()+'\n'+re.sub(r'\s+',' ',entry.name.casefold()).strip()
    return 'game-'+hashlib.sha256(identity.encode()).hexdigest()[:24]

def runtime_info(entry):
    """Only names, never local executable paths, prefixes or environment variables."""
    command=entry.command
    version=entry.metadata.get('proton_version','')
    for i,arg in enumerate(command):
        if arg=='--proton' and i+1<len(command):version=command[i+1]
        if pathlib.Path(arg).name=='proton':version=pathlib.Path(arg).parent.name
    if not version and entry.metadata.get('adapter')=='project2099' and entry.metadata.get('engine')=='reeot':
        from .project2099 import proton_path
        try:version=proton_path(preferred='Proton 9.0 (Beta)').parent.name
        except ValueError:
            try:version=proton_path().parent.name
            except ValueError:pass
    if not version and entry.metadata.get('steam_appid'):
        from .steam_input import parse_text,first
        path=pathlib.Path.home()/'.local/share/Steam/config/config.vdf'
        try:
            node=parse_text(path.read_text())
            for key in ('InstallConfigStore','Software','Valve','Steam','CompatToolMapping'):node=first(node,key,[])
            tool=first(first(node,str(entry.metadata['steam_appid']),[]),'name','')
            if tool and re.fullmatch(r'[A-Za-z0-9_.+ -]{1,100}',tool):version=tool
        except (OSError,ValueError,TypeError):pass
    if entry.metadata.get('steam_store') and not version:return {'kind':'steam','version':'Seleccionado en Steam'}
    proton=bool(version or entry.platform=='Windows' or entry.metadata.get('runtime')=='proton' or any('project2099' in arg for arg in command))
    return {'kind':'proton' if proton else 'native','version':str(version)[:100] if version else ('No detectada' if proton else '')}

def port_notes(entry):
    """Capture scalar graphics options from known files as manual, inert instructions."""
    from .presets import ini_parser
    root=pathlib.Path(entry.metadata.get('gtaiv_root') or entry.cwd)
    names=('plugins/GTAIV.EFLC.FusionFix.ini','plugins/GTAIV.EFLC.FusionFix.cfg','dxvk.conf','Crimson.ini','dmc3.ini')
    allowed={'width','height','resolutionwidth','resolutionheight','fullscreen','vsync','framelimit','fpslimit','fps_limit','fps','antialiasing','anisotropicfiltering','framelimittype','cutscenefpslimit','loadingfpslimit','minigamesfpslimit','unlockframerateduringloadscreens','highresolutionshadows','extradynamicshadows','shadowquality','reflectionquality','drawdistance','d3d9.maxframelatency','d3d9.presentinterval'}
    lines=[]
    for name in names:
        path=root/name
        try:
            if path.stat().st_size>256*1024:continue
            content=path.read_text();parser=ini_parser(content if content.lstrip().startswith('[') else '[General]\n'+content)
        except (OSError,ValueError):continue
        values=[]
        for section in parser.sections():
            for key,raw in parser[section].items():
                value=raw.split(';',1)[0].split('#',1)[0].split('//',1)[0].strip()
                if key.lower() in allowed and re.fullmatch(r'(?:true|false|[+-]?\d+(?:\.\d+)?)',value,re.I):values.append(section+'.'+key+' = '+value)
        if values:lines.extend([name,*values,''])
    if 'devil may cry' in entry.name.casefold() or 'crimson' in entry.name.casefold():
        lines.append('Referencia de preparación de DMC3 Crimson: https://github.com/GonzaCass/deck-library/blob/main/docs/DMC3-CRIMSON.md\nContrastar el mod, las DLL y la versión instalada antes de repetir el arreglo.')
    if 'shattered dimensions' in entry.name.casefold():
        lines.append('Referencia de preparación: https://github.com/GonzaCass/deck-library/blob/main/docs/SPIDER-MAN-SHATTERED-DIMENSIONS.md\nContrastar el prefijo, la versión y el estado instalado antes de repetir el arreglo.')
    return '\n'.join(lines).strip()

def read_file(entry,path):
    """Explicit import of an emulator file, with the same portable-key filter as capture."""
    from . import presets
    import tomllib
    path=pathlib.Path(path)
    if path.stat().st_size>1024*1024:raise ValueError('El archivo de configuración supera 1 MiB.')
    adapter=presets.adapter_for(entry);content=path.read_text()
    if adapter in ('wiicompiled','project2099'):
        parsed=tomllib.loads(content);groups={'runtime':parsed} if adapter=='project2099' else parsed
    else:groups={s:dict(v) for s,v in presets.ini_parser(content).items()}
    if adapter=='dolphin' and path.name.lower()=='gfx.ini':groups={'Video_'+s:v for s,v in groups.items()}
    values={}
    for section,options in presets.REGISTRY[adapter].items():
        group=groups.get(section,{})
        for key,rule in options.items():
            if key not in group:continue
            if adapter in ('eden','azahar') and group.get(key+'\\use_global','false').lower()=='true':continue
            value=presets.typed(rule,group[key])
            if value is not None:values.setdefault(section,{})[key]=value
    if not values:raise ValueError('El archivo no contiene opciones compatibles con este juego y adaptador.')
    return values
