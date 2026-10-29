"""Explicit removal plans. Never infer ownership from an arbitrary working directory."""
import pathlib,shutil
from . import port_removal,ports
from .models import Store
from .installations import settings,save_settings


def set_hidden(identifier,hidden,store=None):
    store=store or Store();preferences=settings(store)
    ids=set(preferences.get('hidden_entries',[]))
    if hidden:ids.add(identifier)
    else:ids.discard(identifier)
    preferences['hidden_entries']=sorted(ids);save_settings(preferences,store)
    return preferences['hidden_entries']


def library_entries(entries,preferences,prefer_ports=True):
    from .library_view import visible_entries
    # Keep associations intact when a port is hidden, rather than resurfacing its ROM.
    values,count=visible_entries([e for e in entries if e.id not in preferences.get('hidden_originals',[])],prefer_ports=prefer_ports,association_exclusions=preferences.get('unlinked_originals',[]))
    return [e for e in values if e.id not in preferences.get('hidden_entries',[])],count


def plan(entry,store=None):
    store=store or Store();entries=store.load()
    entry=next((e for e in entries if e.id==entry.id),None)
    if entry is None:raise ValueError('El juego ya no está registrado en la biblioteca.')
    repository=entry.metadata.get('port_repository','')
    if repository and repository.casefold()!='genrythefox0/project-2099' and repository in ports.records(store):
        return {**port_removal.plan(repository,store),'managed':True}
    preferences=settings(store);targets=[]
    def add(path,boundary):
        path=pathlib.Path(path);boundary=pathlib.Path(boundary)
        port_removal.safe_path(path,boundary)
        if path.exists():targets.append((path,boundary))
    if entry.kind=='emulated':
        from .originals import files_for
        source=pathlib.Path(entry.source)
        if source.suffix.lower() in ('.m3u','.rpx'):
            raise ValueError('Esta instalación usa varios archivos. El borrado debe hacerse desde el emulador; se puede quitar de la biblioteca sin borrar datos.')
        for path in files_for(entry,entries):add(path,path.parent)
    elif entry.kind=='minecraft' and entry.metadata.get('instance_root'):
        folder=pathlib.Path(entry.metadata['instance_root'])
        if not (folder/'instance.cfg').is_file() or pathlib.Path(entry.source)!=folder/'instance.cfg':
            raise ValueError('No se pudo verificar la carpeta de esta instancia de Minecraft.')
        from .discovery import prism_installations
        roots=[pathlib.Path(i['instances']) for i in prism_installations(preferences=preferences)]
        if folder.parent not in roots:raise ValueError('La instancia no pertenece a una instalación conocida de Prism Launcher.')
        add(folder,folder.parent)
    elif entry.kind in ('port','wiicompiled') and entry.source:
        from .installations import launcher_roots,apps_folder
        roots=[ports.ports_root(),pathlib.Path.home()/'ports',*map(pathlib.Path,preferences.get('port_roots',[])),*(apps_folder(r) for r in launcher_roots(preferences=preferences))]
        source=pathlib.Path(entry.source)
        if not source.is_file():raise ValueError('No se encuentra el archivo del juego. No se modificó ninguna carpeta.')
        candidates=[root/source.relative_to(root).parts[0] for root in roots if root.is_absolute() and root not in (pathlib.Path('/'),pathlib.Path.home()) and source.is_relative_to(root) and len(source.relative_to(root).parts)>1]
        if not candidates:raise ValueError('No se pudo verificar una carpeta exclusiva del juego. Se puede quitar de la biblioteca sin borrar archivos.')
        # Most specific configured root wins; never use entry.cwd (it may be the launcher).
        folder=max(candidates,key=lambda p:len(p.parts));add(folder,folder.parent)
    else:
        raise ValueError('El borrado de esta instalación se gestiona desde su lanzador. Se puede quitar de Deck Library sin borrar archivos.')
    if not targets:raise ValueError('No se encuentran los archivos del juego.')
    game_paths=[p for p,_ in targets]
    for other in entries:
        if other.id==entry.id:continue
        references=[other.source,other.cwd,other.metadata.get('original_source',''),*other.command]
        for reference in references:
            if not reference or not pathlib.Path(reference).is_absolute():continue
            resolved=pathlib.Path(reference).resolve()
            if any(resolved==p.resolve() or resolved.is_relative_to(p.resolve()) for p in game_paths):
                raise ValueError('Otro juego utiliza esta carpeta o archivo. No se permite borrar datos compartidos.')
    # Only per-game files are owned here; emulator-wide saves, NAND and settings are shared.
    for relative in ('launchers/'+entry.id+'.sh','logs/'+entry.id+'.log','logs/'+entry.id+'.status.json','applied-presets/'+entry.id+'.json','preferred-presets/'+entry.id+'.json','preset-backups/'+entry.id,'runtimes/ports/'+entry.id):
        add(store.root/relative,store.root)
    targets=list(dict.fromkeys(targets));paths=[p for p,_ in targets]
    return {'managed':False,'name':entry.name,'paths':paths,'targets':targets,'ids':[entry.id],'entries':[entry],
            'signature':[(str(p),p.stat().st_dev,p.stat().st_ino) for p in paths]}


def execute(entry,store=None,expected=None,start_worker=True):
    store=store or Store();value=plan(entry,store)
    if value['managed']:
        return port_removal.execute(value['repository'],store,expected=expected,start_worker=start_worker)
    if expected is not None and value['signature']!=expected['signature']:
        raise ValueError('La instalación cambió. Revisar nuevamente los archivos antes de eliminar.')
    if port_removal.in_use(value['paths']):raise ValueError('Cerrar el juego y su lanzador antes de eliminarlo.')
    steam=port_removal.prepare_steam(value,store,start_worker=start_worker)
    for path,boundary in value['targets']:
        port_removal.safe_path(path,boundary)
        if path.is_dir():shutil.rmtree(path)
        else:path.unlink(missing_ok=True)
    store.save([e for e in store.load() if e.id not in value['ids']])
    return {**value,'steam':steam}
