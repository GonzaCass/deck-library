"""Explicit installation locations and recovery of moved portable ports.

Discovery only reads receipts. Linking does not move user files or change Steam's
AppID. An installation without our receipt is referenced, never owned implicitly.
"""
import copy,json,os,pathlib
from .models import Store,atomic_json


def folder_for(record,home=None,root=None):
    from . import ports
    selected=record.get('install_path')
    if selected:
        path=pathlib.Path(selected).expanduser()
        if not path.is_absolute() or '..' in path.parts:raise ValueError('La carpeta registrada del port no es válida.')
        return path
    name=record.get('folder','')
    if not isinstance(name,str) or not ports.FOLDER.fullmatch(name):raise ValueError('La carpeta registrada del port no es válida.')
    return pathlib.Path(root or ports.ports_root(home))/name


def receipt(folder):
    path=pathlib.Path(folder)/'.deck-library-port.json'
    try:
        if path.is_symlink() or path.stat().st_size>256*1024:return None
        value=json.loads(path.read_text())
        return value if isinstance(value,dict) else None
    except (OSError,ValueError):return None


def record_at(folder,store=None):
    folder=pathlib.Path(folder).resolve()
    from .ports import records
    for value in records(store or Store()).values():
        try:
            if folder_for(value).resolve()==folder:return value
        except ValueError:continue
    return receipt(folder)


def executable_in(folder,record):
    value=record.get('executable','')
    if not isinstance(value,str) or not value:return None
    path=(pathlib.Path(folder)/value).resolve()
    return path if path.is_relative_to(pathlib.Path(folder).resolve()) and path.is_file() else None


def candidates(repository,store=None,home=None):
    """Only matching receipts, one directory level deep. Never guess by title."""
    from . import ports,layout
    from .installations import settings,launcher_roots,apps_folder
    store=store or Store();home=pathlib.Path(home or pathlib.Path.home())
    preferences=settings(store);saved=ports.records(store)
    record=next((v for k,v in saved.items() if k.casefold()==repository.casefold()),None)
    roots=[ports.ports_root(home),home/'ports',layout.folder('ports',home),*map(pathlib.Path,preferences.get('port_roots',[]))]
    # Known launcher installations are read only; a receipt still has to match.
    roots.extend(apps_folder(p) for p in launcher_roots(home,preferences))
    found=[]
    if record:
        path=folder_for(record,home)
        if executable_in(path,record):found.append(path.resolve())
    for root in dict.fromkeys(roots):
        try:children=list(root.iterdir())
        except OSError:continue
        for path in children:
            if path.name.startswith('.') or not path.is_dir() or path.is_symlink():continue
            value=receipt(path)
            if value and value.get('repository','').casefold()==repository.casefold() and executable_in(path,value):found.append(path.resolve())
    return list(dict.fromkeys(found))


def manual_candidates(entry,store=None,home=None):
    """Possible locations of a manual port. A filename alone never authorizes reuse."""
    from . import ports,layout
    from .installations import settings
    home=pathlib.Path(home or pathlib.Path.home());preferences=settings(store or Store());found=[]
    name=pathlib.Path(entry.source).name
    for root in dict.fromkeys([ports.ports_root(home),home/'ports',layout.folder('ports',home),*map(pathlib.Path,preferences.get('port_roots',[]))]):
        try:children=list(root.iterdir())
        except OSError:continue
        for path in children:
            if not path.name.startswith('.') and path.is_dir() and not path.is_symlink() and (path/name).is_file():found.append(path.resolve())
    return list(dict.fromkeys(found))


def link(repository,path,store=None,item=None,entry=None,home=None,executable=None):
    """Register a selected existing directory; refuse wrong receipts/ambiguous binaries."""
    from . import ports,port_packages
    from .port_removal import in_use
    store=store or Store();home=pathlib.Path(home or pathlib.Path.home());path=pathlib.Path(path).expanduser()
    if not path.is_absolute() or not path.is_dir():raise ValueError('Elegir la carpeta donde está instalado el port.')
    path=path.resolve()
    if path in (pathlib.Path('/'),home.resolve(),store.root.resolve()) or path.parent==pathlib.Path('/'):
        raise ValueError('Elegir una carpeta exclusiva del juego, no una carpeta principal.')
    saved=ports.records(store);previous=saved.get(repository,{})
    manifest=receipt(path)
    if (path/'.deck-library-port.json').exists() and manifest is None:raise ValueError('No se pudo leer el registro de esta instalación.')
    if manifest and manifest.get('repository','').casefold()!=repository.casefold():raise ValueError('Esta carpeta pertenece a otro port. Elegir la instalación correcta.')
    for repo,value in saved.items():
        if repo.casefold()!=repository.casefold() and folder_for(value,home).resolve()==path:raise ValueError('Esta carpeta ya está asociada a otro port.')
    for value in (path,folder_for(previous,home) if previous else path):
        if in_use([value]):raise ValueError('Cerrar el juego y su lanzador antes de cambiar la ubicación.')
    record=copy.deepcopy(manifest or previous or ports.clean(item or {'repository':repository}))
    if not record:raise ValueError('No se pudo identificar este port.')
    binary=executable_in(path,record)
    if executable:
        chosen=pathlib.Path(executable).resolve()
        if not chosen.is_relative_to(path) or not chosen.is_file():raise ValueError('Elegir un ejecutable dentro de la carpeta del port.')
        binary=chosen
    if not binary:
        preferred=record.get('windows_exe') or ''
        if preferred:
            matches=[p for p in path.rglob(pathlib.Path(preferred).name) if p.is_file() and len(p.relative_to(path).parts)<=3]
            if len(matches)==1:binary=matches[0]
        if not binary:
            native=ports.find_executable(path,repository)
            windows=port_packages.windows_executable(path,repository)
            if native and windows:raise ValueError('Hay ejecutables Linux y Windows. Elegir el ejecutable del juego.')
            binary=native or windows
    if not binary:raise ValueError('No se identificó un ejecutable único. Elegir el ejecutable del juego.')
    binary=binary.resolve()
    if not binary.is_relative_to(path):raise ValueError('El ejecutable sale de la carpeta elegida.')
    runtime='proton' if binary.suffix.lower()=='.exe' else 'linux'
    if runtime=='linux' and not os.access(binary,os.X_OK):raise ValueError('El programa no tiene permiso de ejecución.')
    linked=entry or next((e for e in store.load() if e.metadata.get('port_repository','').casefold()==repository.casefold()),None)
    record.update(repository=repository,install_path=str(path),executable=str(binary.relative_to(path)),runtime=runtime,
                  external_install=bool((manifest or {}).get('external_install',not bool(manifest))))
    record.setdefault('folder',(ports.clean(item or {'repository':repository}) or {})['folder'])
    record.setdefault('tag','')
    if not manifest:record.update(tag='',verified=False)
    if linked:record['entry_id']=linked.id
    previous_folder=None
    # Move a remembered original that was inside the old installation with it.
    if previous:
        record['inputs']={**record.get('inputs',{}),**previous.get('inputs',{})}
        if previous.get('game_data_dir'):record['game_data_dir']=previous['game_data_dir']
        old=folder_for(previous,home)
        if not previous.get('install_path') and linked and linked.source and previous.get('executable'):
            original=pathlib.Path(linked.source)
            suffix=pathlib.Path(previous['executable'])
            ancestor=next((p for p in original.parents if p.name==previous.get('folder')),None)
            if ancestor:old=ancestor
            elif original.is_absolute() and original.parts[-len(suffix.parts):]==suffix.parts:
                old=original
                for _ in suffix.parts:old=old.parent
        for key,value in list((record.get('inputs') or {}).items()):
            p=pathlib.Path(value)
            if p.is_relative_to(old):record['inputs'][key]=str(path/p.relative_to(old))
        data=record.get('game_data_dir')
        if data and pathlib.Path(data).is_relative_to(old):record['game_data_dir']=str(path/pathlib.Path(data).relative_to(old))
        previous_folder=old
    if repository.casefold()=='revivedx/savagewindrecomp' and runtime=='linux' and binary.suffix.lower()=='.appimage':
        record['args']=list(dict.fromkeys([*record.get('args',[]),'--appimage-extract-and-run']))
    # Multi-game bundles retain the primary ID and all existing secondary entries.
    if linked and linked.metadata.get('port_game') and previous.get('entry_id'):record['entry_id']=previous['entry_id']
    freshes=ports.entries_for(path,record=record)
    fresh=next((e for e in freshes if linked and e.metadata.get('port_game')==linked.metadata.get('port_game')),None) or (freshes[0] if freshes else None)
    if fresh is None:raise ValueError('No se pudo preparar el acceso del juego.')
    saved[repository]=record
    old_saved=(store.root/'ports.json').read_bytes() if (store.root/'ports.json').exists() else None
    old_library=store.load()
    try:
        atomic_json(store.root/'ports.json',saved)
        replacements={}
        for value in freshes:
            old=next((e for e in old_library if e.metadata.get('port_repository','').casefold()==repository.casefold() and e.metadata.get('port_game')==value.metadata.get('port_game')),None)
            old=old or (linked if value is fresh else None)
            if old:
                value.id=old.id;value.name=old.name;value.cover=old.cover;value.icon=old.icon;value.mods=old.mods;value.game_id=old.game_id
                value.metadata={**old.metadata,**value.metadata}
                if old.metadata.get('manual_command') and previous_folder:
                    def remap(argument):
                        p=pathlib.Path(argument)
                        return str(path/p.relative_to(previous_folder)) if p.is_absolute() and p.is_relative_to(previous_folder) else argument
                    value.command=[remap(a) for a in old.command];value.cwd=remap(old.cwd)
                else:value.metadata.pop('manual_command',None)
            replacements[value.id]=value
        entries=[replacements.pop(e.id,e) for e in old_library];entries.extend(replacements.values())
        store.save(entries)
    except BaseException:
        if old_saved is None:(store.root/'ports.json').unlink(missing_ok=True)
        else:(store.root/'ports.json').write_bytes(old_saved)
        store.save(old_library)
        raise
    return fresh


def link_entry(entry,path,store=None,executable=None):
    """Known ports use receipts; a manually added portable entry keeps its command."""
    store=store or Store();repo=entry.metadata.get('port_repository','')
    if repo:return link(repo,path,store,entry=entry,executable=executable)
    from .port_removal import in_use
    path=pathlib.Path(path).expanduser().resolve()
    if not path.is_dir():raise ValueError('Elegir la carpeta donde está instalado el port.')
    old=pathlib.Path(entry.source)
    if not old.is_absolute():raise ValueError('Editar el acceso directo para indicar el ejecutable de este port.')
    chosen=pathlib.Path(executable).resolve() if executable else path/old.name
    if not chosen.is_file() or not chosen.resolve().is_relative_to(path):raise ValueError('No se encontró el ejecutable anterior en esta carpeta. Elegir el ejecutable del juego.')
    if in_use([old.parent,path]):raise ValueError('Cerrar el juego y su lanzador antes de cambiar la ubicación.')
    result=copy.deepcopy(entry)
    def moved(value):
        p=pathlib.Path(value)
        return str(path/p.relative_to(old.parent)) if p.is_absolute() and p.is_relative_to(old.parent) else value
    result.source=str(chosen);result.cwd=moved(entry.cwd);result.command=[moved(p) for p in entry.command]
    result.command=[str(chosen) if p==moved(entry.source) else p for p in result.command]
    if result.command[0]==entry.command[0] and not pathlib.Path(result.command[0]).exists():raise ValueError('Este port usa un lanzador externo. Editar el acceso directo para actualizar su comando.')
    store.save([result if e.id==entry.id else e for e in store.load()])
    return result


def recover(entry,store=None,home=None):
    """Reuse a unique receipt match; disconnected/ambiguous locations stay visible."""
    store=store or Store();repo=entry.metadata.get('port_repository','')
    if entry.kind!='port' or not repo or not entry.source or pathlib.Path(entry.source).is_file():return entry
    found=candidates(repo,store,home)
    if len(found)==1:return link(repo,found[0],store,entry=entry,home=home)
    return entry


def problem(entry,store=None):
    """A missing mounted disk is a recoverable location problem, not an uninstall."""
    from . import ports,switch_port
    repository=entry.metadata.get('port_repository','')
    record=ports.records(store or Store()).get(repository)
    if not record:return 'No se encuentra el juego. Puede haberse movido o faltar la microSD.' if entry.kind=='port' and entry.source and not pathlib.Path(entry.source).is_file() else ''
    if record.get('executable'):
        folder=folder_for(record)
        if not executable_in(folder,record):return 'No se encuentra el port en la ubicación guardada. Revisar la microSD o elegir su carpeta actual.'
    if repository.casefold()==switch_port.REPOSITORY:
        if record.get('game_data_dir') and not switch_port.prepared(record):return 'No se encuentran los datos compilados del juego. Revisar la microSD o elegir su carpeta actual.'
        if not switch_port.prepared(record) and record.get('configured'):
            from .switch_extract import extracted_folder
            try:extracted_folder((record.get('inputs') or {}).get('original_data') or '')
            except (OSError,ValueError):return 'No se encuentran los archivos extraídos del juego. Elegir su carpeta actual o prepararlos otra vez.'
    return ''
