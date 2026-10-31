"""Detect known Windows runtime imports and prepare only the selected game's prefix."""
import datetime,fcntl,hashlib,json,os,pathlib,shutil,subprocess,urllib.request
from .models import Store,atomic_json
from . import proton_selection,proton_tools,project2099,pe_imports

WINETRICKS_TAG='20260125'
WINETRICKS_SHA256='431f82fc74000e6c864409f1d8fb495d696c03928808e3e8acffc45179312a7b'
COMPONENTS={
 'vcrun2005':('Visual C++ 2005',('msvcr80.dll','msvcp80.dll','msvcm80.dll')),
 'vcrun2008':('Visual C++ 2008',('msvcr90.dll','msvcp90.dll','msvcm90.dll')),
 'vcrun2010':('Visual C++ 2010',('msvcr100.dll','msvcp100.dll')),
 'vcrun2012':('Visual C++ 2012',('msvcr110.dll','msvcp110.dll')),
 'vcrun2013':('Visual C++ 2013',('msvcr120.dll','msvcp120.dll')),
 'vcrun2022':('Visual C++ 2015–2022',('vcruntime140.dll','vcruntime140_1.dll','msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','concrt140.dll','vcomp140.dll')),
 'd3dx9_43':('DirectX · D3DX9 43',('d3dx9_43.dll',)),
 'd3dcompiler_43':('DirectX · Compiler 43',('d3dcompiler_43.dll',)),
 'd3dcompiler_47':('DirectX · Compiler 47',('d3dcompiler_47.dll',)),
 'xact':('XACT · Audio de DirectX',('xaudio2_7.dll','xapofx1_5.dll')),
 'xact_x64':('XACT · Audio de DirectX (64 bits)',('xaudio2_7.dll','xapofx1_5.dll')),
 'xinput':('XInput · Mandos',('xinput1_3.dll',)),
 'physx':('NVIDIA PhysX legacy',('physxloader.dll','physxloader64.dll')),
}

for _revision in range(24,44):
    COMPONENTS.setdefault('d3dx9_'+str(_revision),('DirectX · D3DX9 '+str(_revision),('d3dx9_'+str(_revision)+'.dll',)))
for _family,_revisions in [('d3dcompiler',(42,46)),('d3dx10',(43,)),('d3dx11',(42,43))]:
    for _revision in _revisions:
        _name=_family+'_'+str(_revision)
        COMPONENTS[_name]=('DirectX · '+_name,(_name+'.dll',))


def tool_for(entry,home=None,store=None):
    choice=proton_selection.choice(entry) or proton_selection.automatic_version(entry,store,home)
    if choice:return proton_tools.resolve(choice,home)
    if proton_selection.mode(entry)=='steam':
        from .steam_input import parse_text,first
        appid=entry.metadata.get('steam_appid')
        for steam in proton_tools.steam_roots(home):
            try:
                node=parse_text((steam/'config/config.vdf').read_text())
                for key in ('InstallConfigStore','Software','Valve','Steam','CompatToolMapping'):node=first(node,key,[])
                name=first(first(node,str(appid),[]),'name','') or first(first(node,'0',[]),'name','')
                if name=='proton_experimental':return proton_tools.resolve('Proton - Experimental',home)
                if name.startswith('proton_'):
                    major=name.removeprefix('proton_').split('_',1)[0]
                    for caption,path in proton_tools.installed(home).items():
                        if caption.startswith('Proton '+major+'.'):return path
                for caption,path in proton_tools.installed(home).items():
                    if path.parent.name==name:return path
            except (OSError,ValueError):continue
        raise ValueError('No se pudo identificar el Proton elegido en Steam. Seleccionarlo en Propiedades → Compatibilidad.')
    if proton_selection.mode(entry)=='project2099' and entry.metadata.get('engine')=='reeot':
        try:return project2099.proton_path(home,preferred='Proton 9.0 (Beta)')
        except ValueError:pass
    return project2099.proton_path(home)


def prefix_for(entry,store=None,home=None):
    store=store or Store();kind=proton_selection.mode(entry)
    if kind=='port':
        from .ports import port_id
        repo=entry.metadata.get('port_repository')
        if not repo:raise ValueError('Falta la identidad del port para localizar su prefijo.')
        return store.root/'runtimes/ports'/port_id(repo)/'pfx'
    if kind=='exe':return store.root/'runtimes/standalone'/entry.id/'pfx'
    if kind=='project2099':
        version=proton_selection.choice(entry)
        if not version and entry.metadata.get('engine')=='reeot':
            try:version=tool_for(entry,home,store).parent.name
            except ValueError:pass
        slug='project2099' if not version or version=='Proton 11.0' else 'project2099-'+version.lower().replace(' ','-')
        return store.root/'runtimes'/slug/'pfx'
    if kind=='steam':
        appid=entry.metadata.get('steam_appid')
        if not isinstance(appid,int) or not 0<appid<2**32:raise ValueError('Falta el AppID de Steam del juego.')
        found=list(dict.fromkeys((root/'steamapps/compatdata'/str(appid)/'pfx').resolve() for root in proton_tools.libraries(home) if (root/'steamapps/compatdata'/str(appid)/'pfx/user.reg').is_file()))
        if len(found)!=1:raise ValueError('Iniciar este juego una vez desde Steam. Debe existir un único prefijo para su AppID.')
        return found[0]
    raise ValueError('Este juego no utiliza un prefijo de Proton administrado.')


def executable_for(entry):
    selected=entry.metadata.get('dependency_executable')
    if selected:return pathlib.Path(selected)
    source=pathlib.Path(entry.source)
    if source.suffix.lower()=='.exe':return source
    if entry.metadata.get('gtaiv_root'):return pathlib.Path(entry.metadata['gtaiv_root'])/'GTAIV.exe'
    return source


def inspect(entry,store=None,home=None):
    store=store or Store();path=executable_for(entry)
    if path.suffix.lower()!='.exe' or not path.is_file():return {'state':'unknown','components':[],'reason':'Elegir el ejecutable Windows para revisar sus componentes.'}
    try:pe=pe_imports.inspect(path)
    except (OSError,ValueError,UnicodeError) as e:return {'state':'unknown','components':[],'reason':str(e)}
    try:prefix=prefix_for(entry,store,home);reason=''
    except ValueError as e:prefix=None;reason=str(e)
    rows=[];imports=set(pe['imports'])
    for verb,(title,names) in COMPONENTS.items():
        if verb=='xact' and pe['architecture']=='x64' or verb=='xact_x64' and pe['architecture']=='x86':continue
        requested=sorted(imports.intersection(names))
        if not requested:continue
        found=[]
        for dll in requested:
            locations=[path.parent/dll]
            if prefix:
                directory='syswow64' if pe['architecture']=='x86' and (prefix/'drive_c/windows/syswow64').is_dir() else 'system32'
                locations.append(prefix/'drive_c/windows'/directory/dll)
                if verb in ('vcrun2005','vcrun2008'):
                    assembly='vc80' if verb=='vcrun2005' else 'vc90'
                    locations.extend((prefix/'drive_c/windows/winsxs').glob('*microsoft.'+assembly+'.crt*'+'/'+dll))
                if verb=='physx':
                    locations.extend(prefix/'drive_c'/program/'NVIDIA Corporation/PhysX/Common'/dll for program in ('Program Files (x86)','Program Files'))
            for candidate in locations:
                try:
                    if not candidate.is_file() and candidate.parent.is_dir():candidate=next((p for p in candidate.parent.iterdir() if p.name.casefold()==candidate.name.casefold()),candidate)
                    info=pe_imports.inspect(candidate)
                    if info['architecture']==pe['architecture']:found.append(dll);break
                except (OSError,ValueError,UnicodeError):pass
        rows.append({'verb':verb,'name':title,'dlls':requested,'state':'present' if len(found)==len(requested) else 'missing','found':found})
    return {'state':'unknown' if not rows else 'missing' if any(r['state']=='missing' for r in rows) else 'present','components':rows,'prefix':str(prefix) if prefix else '', 'architecture':pe['architecture'],'reason':reason,'scope':'imports-only','executable':str(path)}


def script(store,progress):
    from .gtaiv import write,digest
    path=store.root/'tools/runtime-components'/('winetricks-'+WINETRICKS_TAG)
    if path.is_file() and digest(path)==WINETRICKS_SHA256:return path
    progress('Descargando Winetricks verificado…')
    url='https://raw.githubusercontent.com/Winetricks/winetricks/'+WINETRICKS_TAG+'/src/winetricks'
    with urllib.request.urlopen(url,timeout=60) as response:data=response.read(2*1024*1024)
    if hashlib.sha256(data).hexdigest()!=WINETRICKS_SHA256:raise ValueError('La descarga de Winetricks no coincide con su SHA-256.')
    write(path,data);return path


def prepare(entry,verbs,store=None,home=None,progress=lambda _:None,runner=None,cancel=None):
    from .shattered import run,tool,APP
    from .runtime import clean_environment
    from .port_removal import in_use
    from .ports import check_cancel,Cancelled
    check_cancel(cancel)
    original_runner=runner or run
    def execute(command,progress,**kwargs):
        check_cancel(cancel)
        if cancel is not None:kwargs['cancel']=cancel
        result=original_runner(command,progress,**kwargs);check_cancel(cancel);return result
    store=store or Store();runner=execute;verbs=list(dict.fromkeys(verbs))
    if not verbs or any(v not in COMPONENTS for v in verbs):raise ValueError('Componente de Windows no permitido.')
    value=inspect(entry,store,home);known={r['verb'] for r in value['components']}
    if not set(verbs)<=known:raise ValueError('Los componentes elegidos no corresponden al análisis de este ejecutable.')
    prefix=prefix_for(entry,store,home);proton=tool_for(entry,home,store)
    if in_use([prefix.parent,pathlib.Path(value['executable']).parent]):raise ValueError('Cerrar el juego y su lanzador antes de preparar componentes.')
    if prefix.is_symlink() or prefix.parent.is_symlink():raise ValueError('El prefijo no debe ser un enlace simbólico.')
    stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f');backup=store.root/'dependency-backups'/entry.id/stamp
    backup.mkdir(parents=True,mode=0o700)
    with (backup.parent/'lock').open('w') as lock, (backup/'install.log').open('w',buffering=1) as install_log:
        notify=progress
        def progress(line):
            if install_log.tell()<4*1024*1024:install_log.write(str(line)[:8192]+'\n')
            notify(line)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for name in ('user.reg','system.reg','userdef.reg','winetricks.log'):
            path=prefix/name
            if path.is_symlink():raise ValueError('El registro del prefijo contiene un enlace simbólico.')
            if path.is_file():shutil.copy2(path,backup/name)
        record={'state':'preparing','verbs':verbs,'prefix':str(prefix),'proton':proton.parent.name,'backup':str(backup),'log':str(backup/'install.log'),'scope':'registry-backup; runtime DLL changes are not rolled back'}
        atomic_json(backup/'result.json',record)
        env=clean_environment();env.update(STEAM_COMPAT_DATA_PATH=str(prefix.parent),STEAM_COMPAT_CLIENT_INSTALL_PATH=str(next(iter(proton_tools.steam_roots(home)),pathlib.Path.home()/'.local/share/Steam')))
        try:
            if not (prefix/'user.reg').is_file():
                if proton_selection.mode(entry)=='steam':raise ValueError('Iniciar el juego una vez desde Steam antes de preparar componentes.')
                prefix.parent.mkdir(parents=True,exist_ok=True);progress('Creando el prefijo de este juego…');runner([str(proton),'run','cmd.exe','/c','exit','0'],progress,env=env)
            if not (prefix/'user.reg').is_file():raise RuntimeError('Proton no creó el prefijo del juego.')
            remaining={r['verb'] for r in inspect(entry,store,home)['components'] if r['state']=='missing'}
            verbs=[v for v in verbs if v in remaining]
            if not verbs:
                record['state']='present';atomic_json(backup/'result.json',record);atomic_json(store.root/'dependencies'/(entry.id+'.json'),record);return record
            installer=script(store,progress);wine=proton.parent/'files/bin/wine';server=proton.parent/'files/bin/wineserver'
            if not wine.is_file() or not server.is_file():raise ValueError('Esta distribución de Proton no expone Wine para instalar componentes.')
            cache=store.root/'downloads/winetricks';cache.mkdir(parents=True,exist_ok=True)
            executor=tool(progress,runner)
            environment={**env,'WINE':str(wine),'WINESERVER':str(server),'WINEPREFIX':str(prefix),'WINETRICKS_CACHE':str(cache),'WINETRICKS_GUI':'none'}
            if executor==['flatpak','run']:
                command=['flatpak','run','--command=sh',*['--filesystem='+str(p) for p in (prefix.parent,cache)],'--filesystem='+str(installer.parent)+':ro','--filesystem='+str(proton.parent)+':ro',*['--env='+k+'='+environment[k] for k in ('WINE','WINESERVER','WINEPREFIX','WINETRICKS_CACHE','WINETRICKS_GUI')],APP,str(installer),'-q',*verbs]
            elif shutil.which('cabextract'):command=['sh',str(installer),'-q',*verbs]
            else:raise ValueError('Hace falta cabextract o Protontricks Flatpak para preparar estos componentes.')
            progress('Instalando componentes en el prefijo del juego…');runner(command,progress,env=environment)
            log=prefix/'winetricks.log';installed=set(log.read_text().splitlines()) if log.is_file() else set()
            if not set(verbs)<=installed:raise RuntimeError('No se verificó la instalación en winetricks.log.')
            after=inspect(entry,store,home)
            if any(r['state']!='present' for r in after['components'] if r['verb'] in verbs):raise RuntimeError('La instalación terminó, pero siguen faltando DLLs del ejecutable.')
            record['state']='installed';atomic_json(backup/'result.json',record);atomic_json(store.root/'dependencies'/(entry.id+'.json'),record)
        except Exception as error:
            record.update(state='cancelled' if isinstance(error,Cancelled) else 'failed',error=str(error));atomic_json(backup/'result.json',record);raise
    return record
