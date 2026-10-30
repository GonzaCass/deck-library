"""Explicit permanent removal of receipt-owned ports and their private runtime data."""
import json,pathlib,shutil
from .models import Store,atomic_json


def safe_path(path,boundary):
    path=pathlib.Path(path);boundary=pathlib.Path(boundary)
    relative=path.relative_to(boundary)
    if not relative.parts:raise ValueError('No se puede eliminar la carpeta principal.')
    current=boundary
    for part in relative.parts:
        current=current/part
        if part=='..' or current.is_symlink():raise ValueError('La ruta contiene un enlace simbólico; no se modificó.')
    if not path.resolve().is_relative_to(boundary.resolve()):raise ValueError('La ruta está fuera de la carpeta administrada.')
    return path


def owns(folder,repository):
    receipt=folder/'.deck-library-port.json'
    try:
        return not receipt.is_symlink() and json.loads(receipt.read_text()).get('repository','').casefold()==repository.casefold()
    except (OSError,ValueError,AttributeError):return False


def in_use(paths,proc=pathlib.Path('/proc')):
    roots=[pathlib.Path(path).resolve() for path in paths]
    for process in pathlib.Path(proc).glob('[0-9]*'):
        for name in ('cwd','exe'):
            try:
                target=(process/name).resolve(strict=True)
                if any(target==root or target.is_relative_to(root) for root in roots):return True
            except OSError:pass
        try:
            args=(process/'cmdline').read_bytes().decode(errors='replace').split('\0')
            for argument in args:
                # Wine represents absolute Unix paths as Z:\\home\\... .
                if argument.startswith('--') and '=' in argument:argument=argument.split('=',1)[1]
                value=argument.replace('\\','/')
                if value[:3].lower()=='z:/':value=value[2:]
                if value.startswith('/') and any(value==str(root) or value.startswith(str(root)+'/') for root in roots):return True
        except OSError:pass
    return False


def plan(repository,store=None,root=None):
    from . import ports
    store=store or Store();root=pathlib.Path(root or ports.ports_root());records=ports.records(store);record=records.get(repository)
    if not record:raise ValueError('Este port no fue instalado por Deck Library.')
    if record.get('external_install'):raise ValueError('Esta instalación está vinculada desde otra carpeta. Se puede quitar de la biblioteca; sus archivos se gestionan desde el lanzador original.')
    if repository.casefold()=='genrythefox0/project-2099':raise ValueError('Project 2099 se administra desde su propio instalador.')
    name=record.get('folder','')
    if not isinstance(name,str) or not ports.FOLDER.fullmatch(name):raise ValueError('La carpeta registrada del port no es válida.')
    if any(key!=repository and value.get('folder')==name for key,value in records.items()):raise ValueError('La carpeta está compartida con otro port; no se modificó.')
    folder=ports.folder_for(record,root=root)
    if record.get('install_path'):root=folder.parent
    folder=safe_path(folder,root);paths=[]
    if folder.exists():
        if not folder.is_dir() or not owns(folder,repository):raise ValueError('No se pudo comprobar que esta carpeta pertenece al port.')
        paths.append(folder)
    for category in (ports.REMOVED,'.deck-library-replaced'):
        parent=safe_path(root/category,root)
        if parent.is_dir():
            for candidate in parent.iterdir():
                if not candidate.is_symlink() and candidate.is_dir() and owns(candidate,repository):paths.append(safe_path(candidate,root))
    entries=[e for e in store.load() if e.metadata.get('port_repository','').casefold()==repository.casefold()]
    ids=sorted({ports.port_id(repository),*(e.id for e in entries)})
    relatives=[pathlib.Path('runtimes/ports')/ports.port_id(repository)]
    for identifier in ids:
        relatives.extend([pathlib.Path('launchers')/(identifier+'.sh'),pathlib.Path('logs')/(identifier+'.log'),pathlib.Path('logs')/(identifier+'.status.json'),pathlib.Path('applied-presets')/(identifier+'.json'),pathlib.Path('preferred-presets')/(identifier+'.json'),pathlib.Path('preset-backups')/identifier])
    for relative in relatives:
        target=safe_path(store.root/relative,store.root)
        if target.exists():paths.append(target)
    paths=list(dict.fromkeys(paths))
    for other in store.load():
        if other.id in ids:continue
        for reference in [other.source,other.cwd,other.metadata.get('original_source',''),*other.command]:
            if reference and pathlib.Path(reference).is_absolute() and any(pathlib.Path(reference).resolve().is_relative_to(p.resolve()) for p in paths):
                raise ValueError('Otro juego utiliza esta carpeta o archivo. No se permite borrar datos compartidos.')
    signature=[(str(p),p.stat().st_dev,p.stat().st_ino) for p in paths]
    return {'repository':repository,'name':record.get('name',repository),'paths':paths,'ids':ids,'entries':entries,'signature':signature,'ports_root':root}


def execute(repository,store=None,root=None,expected=None,start_worker=True):
    from . import ports,updates
    store=store or Store();root=pathlib.Path(root or ports.ports_root());value=plan(repository,store,root)
    if expected is not None and value['signature']!=expected['signature']:raise ValueError('La instalación cambió. Revisar nuevamente los archivos antes de eliminar.')
    if in_use(value['paths']):raise ValueError('Cerrar el juego y su lanzador antes de eliminarlo.')
    steam_result=prepare_steam(value,store,start_worker=start_worker)
    for path in value['paths']:
        boundary=value['ports_root'] if path.is_relative_to(value['ports_root']) else store.root
        safe_path(path,boundary)
        if path.is_dir():shutil.rmtree(path)
        else:path.unlink(missing_ok=True)
    records=ports.records(store);records.pop(repository,None);atomic_json(store.root/'ports.json',records)
    store.save([e for e in store.load() if e.id not in value['ids'] and e.metadata.get('port_repository','').casefold()!=repository.casefold()])
    state=updates.cached(store)
    for key in ('ports','catalog'):state[key]=[row for row in state.get(key) or [] if row.get('repository','').casefold()!=repository.casefold()]
    atomic_json(updates.cache_path(store),state)
    return {**value,'steam':steam_result}


def prepare_steam(value,store,start_worker=True):
    """Cancel additions and queue shortcut removal before any game files are deleted."""
    from . import service
    steam={}
    for entry in value['entries']:
        if entry.metadata.get('steam_account') and entry.metadata.get('steam_appid'):steam.setdefault(entry.metadata['steam_account'],[]).append(entry.metadata['steam_appid'])
    if len(steam)>1:raise ValueError('Quitar los accesos directos de las distintas cuentas de Steam antes de eliminar el port.')
    appids={appid for ids in steam.values() for appid in ids}
    with service.pending_lock(store):
        pending=store.root/'pending.json'
        if pending.exists():
            queued=json.loads(pending.read_text())
            if steam and queued['account'] not in steam:raise ValueError('Hay cambios pendientes para otra cuenta de Steam. Aplicarlos antes de eliminar el port.')
            queued['ids']=[i for i in queued['ids'] if i not in value['ids']]
            queued['art']=[i for i in queued.get('art',[]) if i['appid'] not in appids]
            queued['controllers']=[i for i in queued.get('controllers',[]) if i not in appids]
            if any(queued.get(k) for k in ('ids','remove','art','controllers')):atomic_json(pending,queued)
            else:pending.unlink()
    steam_result={'state':'idle','count':0}
    for account,ids in steam.items():steam_result=service.queue_removals(ids,pathlib.Path(account),store,start_worker=start_worker)
    return steam_result
