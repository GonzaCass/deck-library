"""Read-only, conservative library overlap reports. Never hash or remove ROMs."""
import pathlib,shutil
from collections import defaultdict
from .library_view import title_key
from .installations import emudeck_paths,flatpak_apps
from .discovery import SYSTEMS,EMULATOR_FLATPAKS

def analyze(entries,home=None,preferences=None):
    home=pathlib.Path(home or pathlib.Path.home());preferences=preferences or {};groups=defaultdict(list);result=[]
    for e in entries:
        if e.kind!='emulated':continue
        key=(e.platform,e.game_id.casefold() if e.game_id else title_key(e.name))
        groups[key].append(e)
    for (platform,_),items in groups.items():
        paths={str(pathlib.Path(e.source).resolve()) for e in items if e.source}
        if len(paths)>1:
            result.append({'kind':'rom','title':items[0].name+' · '+platform,'note':'Mismo ID o nombre normalizado; pueden ser regiones o revisiones distintas. No se comparó el contenido.','paths':sorted(paths)})
        elif len(items)>1:
            result.append({'kind':'entry','title':items[0].name+' · '+platform,'note':'Varias entradas apuntan al mismo archivo.','paths':sorted(paths)})
    emu=emudeck_paths(home);installed=flatpak_apps() if home==pathlib.Path.home() else set()
    for slug in sorted({v[1] for v in SYSTEMS.values()}):
        # Wrappers are launch routes, not extra emulator installations. Identify the
        # real AppImage/binary or Flatpak once, resolving links and hard links.
        backends={};custom=preferences.get('emulators',{}).get(slug,[])
        if isinstance(custom,str):custom=[custom]
        def add_file(path):
            p=pathlib.Path(path).expanduser()
            try:
                if not p.is_file():return
                if p.suffix.lower() in ('.sh','.desktop','.bat'):return
                with p.open('rb') as stream:
                    if stream.read(2)==b'#!':return
                stat=p.stat();backends[('file',stat.st_dev,stat.st_ino)]=str(p.resolve())
            except OSError:pass
        if custom:
            if 'flatpak' in pathlib.Path(custom[0]).name and 'run' in custom:
                app=next((p for p in custom if p in EMULATOR_FLATPAKS.values()),None)
                if app:backends[('flatpak',app)]='Flatpak: '+app
            else:add_file(custom[0])
        for folder in {home/'Applications',pathlib.Path(emu['apps'])}:
            for p in folder.glob('*.AppImage'):
                if p.name.lower().startswith(slug.split('-')[0]):add_file(p)
        app=EMULATOR_FLATPAKS.get(slug)
        if app in installed:backends[('flatpak',app)]='Flatpak: '+app
        binary=shutil.which(slug)
        if binary:add_file(binary)
        if len(backends)>1:result.append({'kind':'emulator','title':slug,'note':'Instalaciones alternativas disponibles. El lanzador de EmuDeck no se cuenta como otra instalación.','paths':sorted(backends.values())})
    return result
