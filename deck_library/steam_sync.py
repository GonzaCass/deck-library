"""Durable, per-user Steam queue recovery, including before SteamOS launches Steam."""
import os,pathlib,pwd,shutil,subprocess,sys,time
from .models import Store
from .runtime import clean_environment


def manager_environment():
    # Only service-management commands use the canonical bus. Never move a GUI
    # or game out of the user's current (possibly remote) graphical session.
    env=clean_environment();runtime=pathlib.Path('/run/user')/str(os.getuid())
    try:
        if pathlib.Path.home().resolve()==pathlib.Path(pwd.getpwuid(os.getuid()).pw_dir).resolve() and runtime.stat().st_uid==os.getuid() and (runtime/'bus').is_socket():
            env['XDG_RUNTIME_DIR']=str(runtime);env['DBUS_SESSION_BUS_ADDRESS']='unix:path='+str(runtime/'bus')
    except OSError:pass
    return env


def _quoted(value,command=True):
    value=str(value).replace('\\','\\\\').replace('"','\\"').replace('%','%%').replace('\n','\\n').replace('\r','\\r')
    return '"'+(value.replace('$','$$') if command else value)+'"'


def install(store=None,app=None,home=None,activate=True):
    store=store or Store();home=pathlib.Path(home or pathlib.Path.home())
    app=pathlib.Path(app or pathlib.Path(__file__).resolve().parent.parent/'app.py').resolve()
    folder=home/'.config/systemd/user';folder.mkdir(parents=True,exist_ok=True)
    command=' '.join(_quoted(v) for v in (shutil.which('python3') or sys.executable,app,'sync','--data-dir',store.root))
    pending=str((store.root/'pending.json').resolve()).replace('%','%%')
    if any(c in pending for c in ('\n','\r')):raise ValueError('Ruta de datos inválida para la sincronización de Steam.')
    files={
        'deck-library-sync.service':'[Unit]\nDescription=Apply Deck Library changes after Steam closes\nStartLimitIntervalSec=0\n\n[Service]\nType=simple\nExecStart='+command+'\nRestart=on-failure\nRestartSec=30\n',
        'deck-library-sync.path':'[Unit]\nDescription=Watch Deck Library Steam changes\n\n[Path]\nPathExists='+pending+'\nUnit=deck-library-sync.service\n\n[Install]\nWantedBy=default.target\n',
        'deck-library-before-steam.service':'[Unit]\nDescription=Recover Deck Library changes before Steam starts\nBefore=steam-launcher.service gamescope-session.service graphical-session-pre.target\n\n[Service]\nType=oneshot\nExecStart=-'+command+' --before-steam\nTimeoutStartSec=40\n',
    }
    for unit in ('steam-launcher.service','gamescope-session.service'):
        if any((pathlib.Path(base)/unit).exists() for base in ('/usr/lib/systemd/user','/lib/systemd/user')):
            files[unit+'.d/deck-library-sync.conf']='[Unit]\nWants=deck-library-before-steam.service\nAfter=deck-library-before-steam.service\n'
    changed=False
    for name,content in files.items():
        target=folder/name
        if target.exists() and target.read_text()==content:continue
        target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.new');temporary.write_text(content);temporary.replace(target);changed=True
    for unit in ('deck-library-sync.path','deck-library-before-steam.service'):
        enabled=folder/'default.target.wants'/unit;enabled.parent.mkdir(parents=True,exist_ok=True)
        if not enabled.is_symlink():enabled.symlink_to('../'+unit);changed=True
    if activate and shutil.which('systemctl'):
        env=manager_environment()
        if changed:subprocess.run(['systemctl','--user','daemon-reload'],env=env,capture_output=True,timeout=15)
        result=subprocess.run(['systemctl','--user','start','--no-block','deck-library-sync.path'],env=env,capture_output=True,timeout=15)
        if result.returncode:raise RuntimeError('No se pudo activar la sincronización automática de Steam: '+result.stderr.decode(errors='replace').strip())
    return folder


def start(store):
    """Use the installed durable watcher only for the store it was installed for."""
    service=pathlib.Path.home()/'.config/systemd/user/deck-library-sync.service'
    expected=_quoted('--data-dir')+' '+_quoted(store.root)
    if not service.is_file() or expected not in service.read_text() or not shutil.which('systemctl'):return False
    result=subprocess.run(['systemctl','--user','start','--no-block','deck-library-sync.path'],env=manager_environment(),capture_output=True,timeout=15)
    return result.returncode==0


def before_steam(store):
    from .service import sync
    from .steam import steam_running
    end=time.monotonic()+30
    while True:
        result=sync(store,wait=False)
        if result['state']!='pending' or steam_running() or time.monotonic()>=end:return result
        time.sleep(.1)
