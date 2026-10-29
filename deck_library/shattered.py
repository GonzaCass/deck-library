"""Observed Shattered Dimensions audio recipe in the existing Steam prefix.

Only fixed Winetricks verbs and registry values are executed. Never import a
community command or copy someone else's prefix/DLLs.
"""
import datetime,os,pathlib,re,shlex,shutil,signal,struct,subprocess,threading
from .models import Store,atomic_json
from . import proton_tools

APP='com.github.Matoking.protontricks'
VERBS=('d3dx9_43','xact')
REGISTRY='HKEY_CURRENT_USER\\Software\\Activision\\Spider-Man (TM) SD\\Settings\\Game'


def matches(entry):
    name=re.sub(r'[^a-z0-9]','',entry.name.casefold())
    windows=entry.platform in ('Windows','PC','Steam') or entry.source.lower().endswith('.exe')
    return entry.kind!='emulated' and windows and 'spiderman' in name and 'shattereddimensions' in name


def pe32(path):
    with pathlib.Path(path).open('rb') as stream:
        header=stream.read(64)
        if len(header)<64 or header[:2]!=b'MZ':return False
        offset=struct.unpack_from('<I',header,0x3c)[0]
        if offset>16*1024*1024:return False
        stream.seek(offset);return stream.read(6)==b'PE\0\0L\x01'


def inspect(entry,home=None):
    from .steam_inventory import shortcuts
    from .steam_input import parse_text,first
    if not matches(entry):raise ValueError('Este arreglo corresponde a Spider-Man: Shattered Dimensions.')
    source=pathlib.Path(entry.source)
    if not source.is_absolute() or source.name.casefold()!='game.exe' or not source.is_file() or not pe32(source):
        raise ValueError('Elegir la instalación de Windows de 32 bits con Game.exe.')
    account=pathlib.Path(entry.metadata.get('steam_account',''))
    appid=entry.metadata.get('steam_appid')
    if not account.is_absolute() or account.name!='config' or not isinstance(appid,int) or not 0<appid<2**32:
        raise ValueError('Agregar este Game.exe a Steam e iniciarlo una vez con Proton 10.0 para crear su prefijo.')
    target=next((s for s in shortcuts(account) if s['appid']==appid),None)
    if target is None or pathlib.Path(target['exe'].strip('"')).resolve()!=source.resolve():
        raise ValueError('El acceso de Steam no apunta al Game.exe elegido. Revisar el acceso antes de aplicar el arreglo.')
    steam=account.parents[2];prefixes=[]
    for root in dict.fromkeys([steam,*proton_tools.libraries(home)]):
        prefix=root/'steamapps/compatdata'/str(appid)/'pfx'
        if prefix.is_dir() and (prefix/'user.reg').is_file() and prefix.resolve() not in prefixes:prefixes.append(prefix.resolve())
    if len(prefixes)!=1:raise ValueError('No hay un prefijo único para este acceso. Iniciar el juego una vez con Proton 10.0 y volver a intentarlo.')
    prefix=prefixes[0]
    node=parse_text((steam/'config/config.vdf').read_text())
    for key in ('InstallConfigStore','Software','Valve','Steam','CompatToolMapping'):node=first(node,key,[])
    tool=first(first(node,str(appid),[]),'name','')
    if tool!='proton_10':raise ValueError('Seleccionar Proton 10.0 en Propiedades → Compatibilidad del juego en Steam. El arreglo conserva el prefijo y el acceso existentes.')
    proton_tools.resolve('Proton 10.0',home)
    log=prefix/'winetricks.log';installed=set(log.read_text().splitlines()) if log.is_file() else set()
    local=source.parent/'d3dx9_43.dll'
    detected=all(v in installed for v in VERBS) and local.is_file()
    return {'source':source,'folder':source.parent,'steam':steam,'appid':appid,'prefix':prefix,'missing':[v for v in VERBS if v not in installed],'detected':detected}


def run(command,progress,timeout=2700,**kwargs):
    """Run without a terminal or native installer dialogs; retain output in the job log."""
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',start_new_session=True,**kwargs)
    tail=[];expired=threading.Event()
    def terminate():
        expired.set()
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    timer=threading.Timer(timeout,terminate);timer.daemon=True;timer.start()
    try:
        for line in process.stdout:
            line=line.rstrip();tail.append(line);tail=tail[-12:]
            if line:progress(line)
        code=process.wait()
    finally:timer.cancel();process.stdout.close()
    if expired.is_set():raise RuntimeError('La preparación superó el tiempo de espera. Se puede volver a intentar; el respaldo se conserva.')
    if code:raise RuntimeError('Protontricks terminó con error '+str(code)+'.\n'+'\n'.join(tail))


def tool(progress,runner=run):
    if shutil.which('flatpak'):
        if subprocess.run(['flatpak','info',APP],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
            progress('Instalando Protontricks…')
            runner(['flatpak','remote-add','--user','--if-not-exists','flathub','https://flathub.org/repo/flathub.flatpakrepo'],progress)
            runner(['flatpak','install','--user','--noninteractive','-y','flathub',APP],progress)
        return ['flatpak','run']
    binary=shutil.which('protontricks')
    if binary:return [binary]
    raise ValueError('Hace falta Flatpak o Protontricks para instalar los componentes de DirectX.')


def apply(entry,store=None,language='keep',progress=lambda _:None,home=None,runner=run):
    from .port_removal import in_use
    from .runtime import clean_environment
    store=store or Store()
    if language not in ('ESN','keep'):raise ValueError('Idioma de Shattered Dimensions no admitido.')
    value=inspect(entry,home)
    if in_use([value['folder']]):raise ValueError('Cerrar Shattered Dimensions antes de aplicar el arreglo.')
    prefix=value['prefix'];folder=value['folder']
    appid_file=folder/'steam_appid.txt';disabled=folder/'steam_appid.txt.disabled'
    if appid_file.exists() and disabled.exists():raise ValueError('Hay dos archivos steam_appid.txt. Revisar los archivos antes de aplicar el arreglo.')
    # Fixed dependencies affect the registry and the Wine system directories. The
    # backup explicitly covers registry/local changes, not a complete prefix.
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup=store.root/'fix-backups'/entry.id/('shattered-'+stamp);backup.mkdir(parents=True,mode=0o700)
    tracked=[prefix/name for name in ('user.reg','system.reg','userdef.reg','winetricks.log')]+[folder/'d3dx9_43.dll',folder/'steam_appid.txt',folder/'steam_appid.txt.disabled']
    manifest=[]
    for index,path in enumerate(tracked):
        if path.is_symlink():raise ValueError('Un archivo que se modificaría es un enlace simbólico. No se aplicó el arreglo.')
        saved=backup/str(index)
        if path.is_file():shutil.copy2(path,saved)
        manifest.append({'path':str(path),'backup':str(saved) if saved.exists() else ''})
    atomic_json(backup/'manifest.json',{'recipe':1,'files':manifest,'prefix':str(prefix),'dependencies':list(VERBS),'language':language,'state':'preparing'})
    command=tool(progress,runner) if value['missing'] or language!='keep' else []
    environment=clean_environment();environment.update(PROTON_VERSION='Proton 10.0',STEAM_DIR=str(value['steam']))
    if command==['flatpak','run']:
        command+=['--env=PROTON_VERSION=Proton 10.0','--env=STEAM_DIR='+str(value['steam']),*('--filesystem='+str(p) for p in (prefix.parent,folder,backup)),APP]
    def execute(arguments):runner(command+arguments,progress,env=environment)
    progress('Respaldo del registro guardado. Preparando DirectX y audio…')
    if value['missing']:execute([str(value['appid']),'-q',*value['missing']])
    # Check that the dependency installer completed, not only that a command exited.
    log=prefix/'winetricks.log'
    if not log.is_file() or not set(VERBS).issubset(log.read_text().splitlines()):raise RuntimeError('No se verificó la instalación de d3dx9_43 y XACT. Se conservó el respaldo del registro.')
    source=prefix/'drive_c/windows/syswow64/d3dx9_43.dll';target=folder/'d3dx9_43.dll'
    if not target.exists():
        if not source.is_file() or not pe32(source):raise RuntimeError('No se encontró la DLL de DirectX de 32 bits en el prefijo del juego.')
        shutil.copy2(source,target)
    if language!='keep':
        reg=backup/'language.reg';lines=['Windows Registry Editor Version 5.00','', '['+REGISTRY+']']
        lines.extend('"'+key+'"="'+language+'"' for key in ('AudioLanguage','Language','Locale','TextLanguage'))
        reg.write_text('\n'.join(lines)+'\n');execute(['-c','wine reg import '+shlex.quote(str(reg)),str(value['appid'])])
        section=REGISTRY.split('\\',1)[1].replace('\\','\\\\')
        registry=(prefix/'user.reg').read_text(errors='replace')
        block=re.search(r'^\['+re.escape(section)+r'\][^\n]*\n(.*?)(?=^\[|\Z)',registry,re.M|re.S)
        values=dict(re.findall(r'^"([^"]+)"="([^"]*)"',block[1],re.M)) if block else {}
        if any(values.get(key)!=language for key in ('AudioLanguage','Language','Locale','TextLanguage')):raise RuntimeError('No se pudo verificar el idioma en el registro. Se conservó el respaldo anterior.')
    if appid_file.exists():
        appid_file.rename(disabled)
    result={'recipe':1,'state':'applied','backup':str(backup),'prefix':str(prefix),'source':str(value['source']),'language':language,'proton':'Proton 10.0'}
    atomic_json(backup/'result.json',result);atomic_json(store.root/'fixes'/(entry.id+'-shattered.json'),result)
    progress('Arreglo aplicado. Las voces requieren los archivos de audio del idioma elegido.');return result
