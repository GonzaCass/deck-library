"""Per-game Proton preferences resolved when a managed Steam launcher runs."""
import pathlib
from .models import Store
from . import proton_tools,project2099


def mode(entry):
    if entry.metadata.get('steam_store') or entry.kind=='steam':return 'steam' if entry.source.lower().endswith('.exe') or entry.platform=='Windows' else ''
    if '-m' in entry.command:
        index=entry.command.index('-m')+1
        module=entry.command[index] if index<len(entry.command) else ''
        if module=='deck_library.port_runtime':return 'port'
        if module=='deck_library.project2099':return 'project2099'
    if entry.command[0].lower().endswith('.exe'):return 'exe'
    return ''


def choice(entry):
    if 'proton_version' in entry.metadata:return entry.metadata['proton_version']
    if mode(entry)=='project2099' and '--proton' in entry.command:
        index=entry.command.index('--proton')+1
        if index<len(entry.command):return entry.command[index]
    return ''


def automatic_version(entry,store=None,home=None):
    """Prefer an installed build from a shipped, confirmed game profile."""
    from .game_fixes import recommendation
    if mode(entry) not in ('port','project2099','exe'):return ''
    value=recommendation(entry,store)
    return value['version'] if value and value['version'] in proton_tools.installed(home) else ''


def default_tool(entry):
    recommended=automatic_version(entry)
    if recommended:return proton_tools.resolve(recommended)
    if mode(entry)=='project2099' and entry.metadata.get('engine')=='reeot':
        try:return project2099.proton_path(preferred='Proton 9.0 (Beta)')
        except ValueError:pass
    return project2099.proton_path()


def busy(entry):
    from .content import emulator_busy
    root=pathlib.Path(entry.source).parent
    names={path.name for path in root.glob('*.exe')} if entry.source.lower().endswith('.exe') else set()
    names.update({'narutorise.exe','narutorise_launcher.exe'} if entry.metadata.get('port_repository','').lower()=='jorjbarbosa/naruto-rise-recomp' else ())
    return any(emulator_busy(value) for name in names for value in (name,name[:15]))


def save(entry,version,store=None):
    if mode(entry) not in ('port','project2099','exe'):raise ValueError('Este acceso directo administra su compatibilidad desde Steam o desde otro lanzador.')
    if version:proton_tools.resolve(version)
    else:default_tool(entry)
    if busy(entry):raise RuntimeError('Cerrar el juego y su lanzador antes de cambiar Proton.')
    store=store or Store();entries=store.load();saved=next((item for item in entries if item.id==entry.id),None)
    if saved is None:raise ValueError('El juego ya no está en la biblioteca.')
    saved.metadata['proton_version']=version
    if mode(saved)=='project2099' and '--proton' in saved.command:
        index=saved.command.index('--proton');del saved.command[index:index+2]
    store.save(entries);entry.metadata=dict(saved.metadata);entry.command=list(saved.command)
    return version


def launch_command(entry,command,env,store):
    """Keep AppID, launcher path and per-game data directory unchanged."""
    kind=mode(entry);version=choice(entry) or automatic_version(entry,store);command=list(command)
    if kind in ('port','project2099'):
        if '--proton' in command and kind=='project2099':
            index=command.index('--proton');del command[index:index+2]
        if kind=='port' and '--data-dir' not in command:command+=['--data-dir',str(store.root)]
        if version:
            if kind=='port':proton_tools.resolve(version)
            command+=['--proton',version]
        return command,env
    if kind=='exe':
        tool=proton_tools.resolve(version) if version else default_tool(entry)
        runtime=project2099.proton_env(store);env={**env,**runtime}
        prefix=store.root/'runtimes/standalone'/entry.id;prefix.mkdir(parents=True,exist_ok=True)
        env['STEAM_COMPAT_DATA_PATH']=str(prefix)
        return [str(tool),'run',*command],env
    return command,env
