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
    return result+environment(home,preferences,emu)

OTHER_SWITCH={'yuzu':'org.yuzu_emu.yuzu','ryujinx':'org.ryujinx.Ryujinx','suyu':'dev.suyu_emu.suyu','citron':'org.citron_emu.citron','sudachi':'org.sudachi_emu.sudachi'}

def environment(home,preferences,emu):
    """Conflicts around Eden and Deck Library itself: duplicate configuration or saves, rival emulators, controller and running state."""
    from .content import emulator_busy
    result=[];real=home==pathlib.Path.home()
    native=home/'.config/eden';boxed=home/'.var/app/dev.eden_emu.eden/config/eden'
    if (native/'qt-config.ini').is_file() and (boxed/'qt-config.ini').is_file():
        from .content import eden_paths
        used=eden_paths(home,preferences.get('eden_config') or None)['config']
        result.append({'kind':'eden-config','title':'Eden · dos configuraciones','note':'Hay una configuración de Eden de AppImage y otra de Flatpak. Deck Library edita solo la marcada como en uso; el otro Eden seguirá con sus propios ajustes.','paths':[str(native)+(' (en uso)' if used==native else ''),str(boxed)+(' (en uso)' if used==boxed else '')]})
    saves=[d for d in (home/'.local/share/eden/nand/user/save',home/'.var/app/dev.eden_emu.eden/data/eden/nand/user/save') if d.is_dir() and any(d.rglob('*'))]
    if len(saves)>1:result.append({'kind':'eden-saves','title':'Eden · partidas en dos lugares','note':'Las partidas guardadas existen en la carpeta de AppImage y en la de Flatpak. No se combinan solas; conviene elegir una y respaldar la otra.','paths':[str(d) for d in saves]})
    rivals={}
    for name,app in OTHER_SWITCH.items():
        for folder in {home/'Applications',pathlib.Path(emu['apps'])}:
            for p in folder.glob('*.AppImage'):
                if p.name.lower().startswith(name):rivals[str(p)]=name
        if real and app in flatpak_apps():rivals['Flatpak: '+app]=name
    if rivals and (any(home.glob('Applications/[Ee]den*.AppImage')) or (boxed.parent.parent).is_dir() or (native).is_dir()):
        result.append({'kind':'switch-emulators','title':'Más de un emulador de Switch','note':'Eden está instalado junto a otros emuladores de Switch. Los juegos usan el emulador indicado en cada entrada; las partidas y los mods no se comparten entre ellos.','paths':sorted(rivals)})
    if real:
        from . import eden_controls
        if eden_controls.status(preferences.get('eden_config') or None)=='other':
            result.append({'kind':'eden-controls','title':'Eden · mando del jugador 1','note':'El jugador 1 de Eden usa un dispositivo distinto de la Steam Deck. Puede actualizarse al aplicar un ajuste a un juego de Switch.','paths':[str(eden_controls.config_path(preferences.get('eden_config') or None))]})
        if emulator_busy():result.append({'kind':'running','title':'Eden está abierto','note':'Con Eden en ejecución no se pueden aplicar perfiles ni cambiar el mando; cerrarlo antes.','paths':[]})
    me=pathlib.Path(__file__).resolve().parent.parent
    copies=sorted({str(p.parent.resolve()) for pattern in ('Applications/DeckLibrary','ports/deck-library*') for p in home.glob(pattern+'/app.py')})
    if len(copies)>1:result.append({'kind':'app','title':'Más de una copia de Deck Library','note':'Hay varias carpetas con la app. La de Steam y el menú de aplicaciones usan la instalada en Applications/DeckLibrary; las demás no se actualizan solas.','paths':[c+(' (esta)' if c==str(me) else '') for c in copies]})
    return result
