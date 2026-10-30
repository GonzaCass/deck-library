"""Pass selected originals to Savage Wind's own first-run builder, only while needed."""
import os,pathlib

REPOSITORY='revivedx/savagewindrecomp'

def data_root(record,home=None,env=None):
    from .ports import folder_for
    home=pathlib.Path(home or pathlib.Path.home());env=os.environ if env is None else env
    selected=record.get('game_data_dir') or env.get('SAVAGEWIND_DATA_ROOT')
    if selected:
        path=pathlib.Path(selected)
        if not path.is_absolute():raise ValueError('La carpeta de datos del juego debe ser absoluta.')
        return path
    try:folder=folder_for(record,home)
    except ValueError:folder=None
    if folder and (folder/'extracted').is_dir():return folder
    if record.get('runtime')=='proton':
        return (folder/pathlib.Path(record.get('executable') or '.')).parent if record.get('executable') else folder
    return pathlib.Path(env.get('XDG_DATA_HOME') or home/'.local/share')/'savagewind'

def compiled_folder(path,windows=False):
    path=pathlib.Path(path).expanduser()
    # Accept the application data root, extracted/, or a parent of extracted/.
    root=path.parent if path.name=='extracted' else path
    if not all((root/'extracted'/name).is_file() for name in ('exefs/main','romfs.bin','swgame.dll' if windows else 'swgame.so')):
        raise ValueError('Elegir la carpeta de Savage Wind con extracted/exefs/main, romfs.bin y el módulo compilado del sistema elegido.')
    return root.resolve()

def set_data(repository,path,store=None):
    from .models import Store,atomic_json
    from .ports import records
    from .port_removal import in_use
    store=store or Store();saved=records(store);record=saved.get(repository)
    if not record or repository.casefold()!=REPOSITORY:raise ValueError('Este port no admite una carpeta compilada de Savage Wind.')
    root=compiled_folder(path,record.get('runtime')=='proton')
    if in_use([root,data_root(record)]):raise ValueError('Cerrar el juego antes de cambiar su carpeta de datos.')
    record.update(game_data_dir=str(root),configured=True)
    atomic_json(store.root/'ports.json',saved)
    return record

def prepared(record,home=None,env=None):
    try:compiled_folder(data_root(record,home,env),record.get('runtime')=='proton');return True
    except (OSError,ValueError,TypeError):return False

def launch_environment(entry,env,store,home=None):
    if entry.metadata.get('port_repository','').casefold()!=REPOSITORY:return env
    from .ports import records
    record=next((r for repo,r in records(store).items() if repo.casefold()==REPOSITORY),{})
    windows=record.get('runtime')=='proton'
    selected=record.get('game_data_dir')
    if selected:
        if not prepared(record,home,env):raise ValueError('No se encuentran los datos compilados del juego. Elegir su ubicación en Juego y archivos → Carpetas del juego.')
        env={**env,'SAVAGEWIND_DATA_ROOT':('Z:'+selected.replace('/','\\')) if windows else selected}
    # The port validates its own build and version even when these files exist.
    # Never force setup on every launch: doing so would compile again and open its configuration screen.
    if prepared(record,home,env):return env
    source=(record.get('inputs') or {}).get('original_data')
    if not source:return env
    from .switch_extract import extracted_folder
    source=extracted_folder(source)
    value=('Z:'+str(source).replace('/','\\')) if windows else str(source)
    return {**env,'SAVAGEWIND_LAUNCHER_SETUP':value,'SAVAGEWIND_LAUNCHER_MODE':'setup'}
