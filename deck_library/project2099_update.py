"""Verified, staged Project-2099 updates; the old game remains recoverable."""
import json,pathlib,re,shutil,subprocess,tempfile,threading,time
from . import ports,project2099,presets
from .models import atomic_json

def source_for(entry,entries):
    sources=[entry.metadata.get('original_source',''),str(pathlib.Path(entry.source).parent/'Data/Original')]
    receipt=pathlib.Path(entry.source).parent/'deck-library-project2099.json'
    try:sources.append(json.loads(receipt.read_text()).get('source',''))
    except (OSError,ValueError):pass
    sources.extend(e.source for e in entries if e.kind=='emulated' and ('edge of time' in e.name.lower() or e.game_id.upper()=='415608B2'))
    downloads=pathlib.Path.home()/'Downloads'
    for p in [*downloads.glob('*'),*(downloads/'switch').glob('*')]:
        if 'edgeoftime' in re.sub(r'[^a-z0-9]','',p.name.lower()) and p.suffix.lower() in ('.7z','.zip','.iso'):sources.append(str(p))
    for source in sources:
        if source:
            path=pathlib.Path(source)
            if path.is_dir() and all((path/n).is_file() for n in ('Default.xex','Data/Main.pkz','Data/BaseGameplay.pkz')):return source
            if path.is_file() and path.suffix.lower() in ('.7z','.zip','.iso'):return source
    return ''

def assets_for(release):
    assets=release.get('assets',[])
    setup=next((a for a in assets if re.fullmatch(r'(?:Project2099-[A-Za-z0-9._-]+-Setup|EOTInstaller-[A-Za-z0-9._-]+)\.exe',a.get('name',''))),None)
    payload=next((a for a in assets if re.fullmatch(r'(?:Project2099-[A-Za-z0-9._-]+-Payload|EOT-PC-Payload-[A-Za-z0-9._-]+)\.zip',a.get('name',''))),None)
    if not setup or not payload:raise ValueError('La versión no incluye un instalador y un payload reconocibles para actualizar.')
    for a in (setup,payload):
        if not re.fullmatch('sha256:[a-fA-F0-9]{64}',a.get('digest') or ''):raise ValueError('Falta la suma SHA-256 oficial de '+a['name'])
        if not a.get('browser_download_url','').startswith('https://github.com/GenryTheFox0/Project-2099/releases/download/'):raise ValueError('Origen de descarga no permitido.')
    return setup,payload

def installation_activity(work,progress,interval=2):
    """Count actual staged writes; silent WinExe installers need not have a console."""
    previous=[None];checked=[0]
    def poll():
        now=time.monotonic()
        if now-checked[0]<interval:return False
        checked[0]=now;count=size=0
        for folder in work.glob('game*'):
            for path in folder.rglob('*'):
                try:
                    if path.is_file():count+=1;size+=path.stat().st_size
                except FileNotFoundError:pass
        value=(count,size)
        if value==previous[0]:return False
        previous[0]=value
        if count:progress({'phase':'install','text':f'Instalando · {size/(1<<30):.2f} GB escritos · {count} archivos','fraction':None,'eta':None})
        return bool(count)
    return poll

def promote(entry,stage,folder,tag,source,store,cancel=None):
    """Commit only a complete staged game, retaining a restorable previous version."""
    stage=pathlib.Path(stage);folder=pathlib.Path(folder)
    executable,engine=project2099.installation_files(stage)
    if not executable:raise ValueError('La instalación temporal está incompleta; se conserva la anterior.')
    ports.check_cancel(cancel)
    from .port_packages import preserve_saves
    preserve_saves(folder,stage,cancel)
    atomic_json(stage/'deck-library-project2099.json',{'version':tag,'source':str(source)})
    ports.check_cancel(cancel);backup=None
    if folder.exists():
        backup=folder.parent/'.deck-library-replaced'/(folder.name+'-'+time.strftime('%Y%m%dT%H%M%S'));backup.parent.mkdir(exist_ok=True);folder.rename(backup)
    try:stage.rename(folder)
    except BaseException:
        if backup:backup.rename(folder)
        raise
    entry.source=str(project2099.installation_files(folder)[0]);entry.metadata.update(build=tag,engine=engine)
    if engine=='reeot':
        # Legacy runtime switches and graphics profiles belong to the old engine.
        args=[];skip=False
        for value in entry.command:
            if skip:skip=False;continue
            if value=='--proton':skip=True;continue
            if value=='--single-queue':continue
            args.append(value)
        entry.command=args
    store.merge([entry],overwrite=True)
    return {'version':tag,'backup':str(backup) if backup else ''}

def update(entry,source,release,store,progress=lambda _:None,cancel=None,runner=None,*,fresh=False):
    from .setup_wii import run_logged
    cancel=cancel or threading.Event();ports.check_cancel(cancel)
    folder=pathlib.Path(entry.source).parent
    if entry.metadata.get('adapter')!='project2099' or folder.is_symlink() or (not fresh and not project2099.installation_files(folder)[0]):raise ValueError('No se encontró la instalación original de Project-2099.')
    if fresh and folder.exists() and any(folder.iterdir()):raise ValueError('La carpeta de destino debe estar vacía.')
    if presets.busy('project2099'):raise RuntimeError('Cerrá el juego antes de actualizarlo.')
    source=pathlib.Path(source).resolve()
    if source.is_dir():
        if not all((source/n).is_file() for n in ('Default.xex','Data/Main.pkz','Data/BaseGameplay.pkz')):raise ValueError('La carpeta no contiene los datos de Xbox 360 requeridos.')
        iso_size=0
    else:iso_size=project2099.validate_source(source)
    setup,payload=assets_for(release);tag=release['tag_name'].lstrip('v')
    if shutil.disk_usage(folder.parent).free<iso_size+18*1024**3:raise ValueError('Faltan unos 18 GB libres temporales más el espacio para extraer la ISO.')
    cache=store.root/'downloads/project2099'/tag;cache.mkdir(parents=True,exist_ok=True)
    total=sum(a.get('size',0) for a in (setup,payload));offset=0
    for asset in (setup,payload):
        target=cache/asset['name'];expected=asset['digest'][7:].lower()
        if not target.is_file() or ports.sha256_file(target)!=expected:
            partial=target.with_suffix(target.suffix+'.part')
            try:
                ports.download(asset['browser_download_url'],partial,progress=lambda done,size:progress({'phase':'download','done':offset+done,'total':total}),cancel=cancel)
                if (asset.get('size') and partial.stat().st_size!=asset['size']) or ports.sha256_file(partial)!=expected:raise ValueError('La descarga no coincide con el SHA-256 oficial.')
                partial.replace(target)
            finally:
                if partial.exists():partial.unlink()
        offset+=asset.get('size',target.stat().st_size)
        progress({'phase':'download','done':offset,'total':total})
    if '--install-test'.encode('utf-16le') not in (cache/setup['name']).read_bytes():raise ValueError('Este instalador no permite la instalación automática conocida. La instalación anterior se conserva.')
    with tempfile.TemporaryDirectory(prefix='.project2099-update-',dir=folder.parent) as temporary:
        work=pathlib.Path(temporary);payload_dir=work/'payload-files';payload_dir.mkdir();progress('Extrayendo los componentes verificados…');ports.extract(cache/payload['name'],payload_dir)
        manifests=list(payload_dir.rglob('payload-manifest.json'))
        if len(manifests)!=1:raise ValueError('No se reconoció el manifiesto del payload.')
        stage=work/'game';image=source
        if iso_size:
            import zipfile,subprocess
            image=work/'source.iso';progress('Extrayendo la imagen original…')
            if source.suffix.lower()=='.7z':
                tool,name,_=project2099.sevenzip_image(source)
                with image.open('wb') as out:
                    result=subprocess.run([tool,'e','-so',str(source),name],stdout=out,stderr=subprocess.PIPE)
                if result.returncode:raise ValueError('No se pudo extraer la imagen original.')
            else:
                with zipfile.ZipFile(source) as z,z.open(next(i for i in z.infolist() if i.filename.lower().endswith('.iso'))) as inp,image.open('wb') as out:shutil.copyfileobj(inp,out,1<<20)
            with image.open('rb') as stream:project2099.check_image(stream)
        ports.check_cancel(cancel)
        proton,env=project2099.installer_environment(store)
        win=lambda p:'Z:'+str(p).replace('/','\\')
        command=[str(proton),'run',str(cache/setup['name']),'--install-test',win(image),win(stage),win(manifests[0].parent),'5']
        progress('Instalando la nueva versión en una carpeta temporal…')
        def stop_installer():
            clean=dict(env);clean['WINEPREFIX']=str(pathlib.Path(env['STEAM_COMPAT_DATA_PATH'])/'pfx')
            server=proton.parent/'files/bin/wineserver'
            if server.is_file():
                try:subprocess.run([str(server),'-k'],env=clean,timeout=10,capture_output=True)
                except (OSError,subprocess.TimeoutExpired):pass
        with (cache/'update.log').open('w') as log:
            if runner:runner(command,str(cache),env,log,progress,cancel)
            else:run_logged(command,str(cache),env,log,progress,cancel,activity=installation_activity(work,progress),idle_timeout=300,cleanup=stop_installer)
        if not project2099.installation_files(stage)[0]:raise ValueError('El instalador no produjo una instalación completa. Se conserva la anterior. Registro: '+str(cache/'update.log'))
        result=promote(entry,stage,folder,tag,source,store,cancel)
    return result
