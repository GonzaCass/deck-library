"""Steam-independent launchers, environment cleanup and visible diagnostics."""
import configparser,datetime,json,os,pathlib,re,resource,shlex,shutil,signal,subprocess,sys,time
from .models import Store,atomic_json

STEAM_RUNTIME_KEYS=('LD_PRELOAD','LD_LIBRARY_PATH','STEAM_RUNTIME','STEAM_RUNTIME_LIBRARY_PATH','APPIMAGE','APPDIR','ARGV0','OWD','GIO_EXTRA_MODULES','GTK_PATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH')
def clean_environment(env=None):
    env=dict(os.environ if env is None else env)
    for key in STEAM_RUNTIME_KEYS:env.pop(key,None)
    env['PATH']=':'.join(p for p in env.get('PATH','/usr/bin:/bin').split(':') if '/tmp/.mount_' not in p and '/steam-runtime/' not in p and '/pressure-vessel/' not in p)
    # Preserve display, Wayland, session bus and Steam Input app IDs. Never redirect a remote session.
    runtime=env.get('XDG_RUNTIME_DIR','')
    if pathlib.Path('/usr/lib/alsa-lib').is_dir():env.setdefault('ALSA_PLUGIN_DIR','/usr/lib/alsa-lib')
    if runtime and pathlib.Path(runtime,'pulse/native').exists():env.setdefault('SDL_AUDIODRIVER','pulseaudio')
    if env.get('XDG_SESSION_TYPE')=='x11':env.setdefault('QT_QPA_PLATFORM','xcb')
    if not env.get('DISPLAY') and env.get('WAYLAND_DISPLAY'):env.pop('QT_QPA_PLATFORM',None)
    return env

def diagnostics(entry,store=None):
    store=store or Store(); issues=[]
    executable=entry.command[0]
    if not (pathlib.Path(executable).is_file() or shutil.which(executable)):issues.append('No se encuentra el programa seleccionado.')
    elif pathlib.Path(executable).is_file() and not os.access(executable,os.X_OK):issues.append('El programa no tiene permiso de ejecución.')
    if entry.source and not pathlib.Path(entry.source).exists():issues.append('No se encuentra el juego. Puede haberse movido o faltar la microSD.')
    if entry.command[0].endswith('.exe'):issues.append('Un ejecutable Windows necesita Wine/Proton. Usar un launcher de Lutris o Heroic, o un comando personalizado.')
    if entry.metadata.get('sandbox'):
        from . import buildenv
        if not buildenv.installed():issues.append('Falta el entorno de compilación (SDK de KDE de Flatpak). Instalarlo desde el catálogo de ports.')
    if entry.kind=='wiicompiled':
        try:
            check=subprocess.run(['flatpak','info','io.github.TeamWheelWizard.WheelWizard'],env=clean_environment(),capture_output=True,timeout=8)
            if check.returncode:issues.append('Falta el entorno WheelWizard instalado en Flatpak.')
        except (OSError,subprocess.TimeoutExpired):issues.append('No se pudo comprobar Flatpak.')
    log=store.root/'logs'/(entry.id+'.log')
    details=log.read_text(errors='replace')[-18000:] if log.exists() else ''
    if 'invalid merge-dirs' in details:issues.append('Flatpak no pudo preparar su extensión gráfica. El juego no llegó a arrancar; revisar el runtime, no la ROM.')
    if 'Cannot execute instruction at unmapped address' in details:issues.append('El juego emulado se detuvo con una excepción. Si usa mods, probar el perfil sin mods.')
    return issues,details

def make_launcher(entry,store=None,app=None):
    store=store or Store(); folder=store.root/'launchers'; folder.mkdir(parents=True,exist_ok=True)
    path=folder/(entry.id+'.sh'); app=pathlib.Path(app or pathlib.Path(__file__).resolve().parent.parent/'app.py')
    interpreter=shutil.which('python3') or sys.executable
    text='#!/bin/sh\nexec '+shlex.join([interpreter,str(app),'launch',entry.id,'--data-dir',str(store.root)])+'\n'
    path.write_text(text); path.chmod(0o755); return path

def prepare_eden_profile(entry,store,env):
    # Eden's bundled self-updater.hook explicitly supports this opt-out.
    # Only managed game launches skip update dialogs; normal Eden launches are unchanged.
    if entry.platform=='Switch':env['DISABLE_AUTO_UPDATES']='1'
    if entry.platform!='Switch':return env
    if entry.mods:
        from .installations import settings
        configured=settings(store).get('eden_config')
        if configured:
            location=pathlib.Path(configured).expanduser()
            if location.name!='eden':raise RuntimeError('La carpeta de configuración debe llamarse eden y contener qt-config.ini.')
            env['XDG_CONFIG_HOME']=str(location.parent)
        return env
    from .installations import settings
    from .content import eden_paths
    paths=eden_paths(config_dir=settings(store).get('eden_config') or None)
    source=paths['config']; original=source/'qt-config.ini'
    if not original.exists():raise RuntimeError('Eden debe abrirse una vez antes de usar el perfil sin mods.')
    profile=store.root/'profiles'/entry.id; dest=profile/'eden'
    # Rebuild configuration from the current real config on each launch. Saves/NAND/keys stay canonical.
    dest.mkdir(parents=True,exist_ok=True)
    graphics_config=pathlib.Path.home()/'.config/lsfg-vk'
    if graphics_config.is_dir():shutil.copytree(graphics_config,profile/'lsfg-vk',dirs_exist_ok=True)
    parser=configparser.ConfigParser(interpolation=None); parser.optionxform=str; parser.read(original)
    if not parser.has_section('Data%20Storage'):parser.add_section('Data%20Storage')
    section=parser['Data%20Storage']; data=pathlib.Path.home()/'.local/share/eden'
    for key,fallback in (('nand_directory',data/'nand'),('sdmc_directory',data/'sdmc')):
        if not section.get(key):section[key]=str(fallback)
        section[key+'\\default']='false'
    no_mods=store.root/'profiles/empty-mods'; no_mods.mkdir(parents=True,exist_ok=True)
    section['load_directory']=str(no_mods); section['load_directory\\default']='false'
    with (dest/'qt-config.ini').open('w') as out:parser.write(out,space_around_delimiters=False)
    if (source/'custom').is_dir():shutil.copytree(source/'custom',dest/'custom',dirs_exist_ok=True)
    env['XDG_CONFIG_HOME']=str(profile)
    env['XDG_DATA_HOME']=str(paths['data'].parent)
    return env

def show_error(message,store=None):
    print(message,file=sys.stderr)
    try:atomic_json((store or Store()).root/'launch-notice.json',{'message':str(message),'time':time.time()})
    except OSError:pass

def launch(entry,store=None,notify=True):
    store=store or Store(); issues,_=diagnostics(entry,store)
    # Old error logs inform the diagnostic panel, but do not prevent trying a repaired launch.
    blocking=[i for i in issues if i.startswith(('No se encuentra','El programa no tiene','Un ejecutable Windows','Falta el entorno'))]
    if blocking:
        if notify:show_error('\n'.join(blocking),store)
        return 1
    try:env=prepare_eden_profile(entry,store,clean_environment())
    except (OSError,configparser.Error,RuntimeError) as error:
        if notify:show_error('No se pudo preparar '+entry.name+'.\n'+str(error),store)
        return 1
    folder=store.root/'logs'; folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    log=folder/(entry.id+'.log'); start=time.monotonic()
    # Steam may inherit an unusually low fd limit. Flatpak/graphics extension setup uses many fds.
    soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft<min(hard,8192):resource.setrlimit(resource.RLIMIT_NOFILE,(min(hard,8192),hard))
    with log.open('w') as output:
        log.chmod(0o600); output.write(f'Deck Library — {entry.name}\nStarted: {datetime.datetime.now().isoformat()}\n'); output.flush()
        command=list(entry.command)
        if entry.platform=='Switch' and pathlib.Path(command[0]).name=='flatpak' and len(command)>1 and command[1]=='run':
            from .content import eden_paths
            from .installations import settings
            paths=eden_paths(config_dir=settings(store).get('eden_config') or None)
            config_home=env.get('XDG_CONFIG_HOME',str(paths['config'].parent))
            data_home=str(paths['data'].parent)
            permissions=[str(pathlib.Path(entry.source).parent),str(paths['nand']),str(paths['load']),str(paths['sdmc']),config_home,data_home]
            command[2:2]=['--env=DISABLE_AUTO_UPDATES=1','--env=XDG_CONFIG_HOME='+config_home,'--env=XDG_DATA_HOME='+data_home,*['--filesystem='+p for p in dict.fromkeys(permissions)]]
        output.write(f'Program: {pathlib.Path(command[0]).name}; platform: {entry.platform}; mods: {entry.mods}\n');output.flush()
        try:process=subprocess.Popen(command,cwd=pathlib.Path.home() if entry.platform=='Switch' else entry.cwd if pathlib.Path(entry.cwd).is_dir() else pathlib.Path.home(),env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        except OSError as error:
            output.write(str(error)+'\n')
            if notify:show_error('No se pudo abrir '+entry.name+'.\n'+str(error),store)
            return 1
        previous={};stop_requested=False
        def forward(signum,frame):
            nonlocal stop_requested
            stop_requested=True
            try:os.killpg(process.pid,signum)
            except ProcessLookupError:pass
        if __import__('threading').current_thread() is __import__('threading').main_thread():
            for sig in (signal.SIGTERM,signal.SIGINT):previous[sig]=signal.signal(sig,forward)
        try:code=process.wait()
        finally:
            for sig,handler in previous.items():signal.signal(sig,handler)
        output.write(f'\nExit: {code}; elapsed: {time.monotonic()-start:.1f}s\n')
    # Eden has its own log; retain it privately so loading failures are diagnosable.
    if entry.platform=='Switch':
        source=pathlib.Path.home()/'.local/share/eden/log/eden_log.txt'
        if source.exists():
            with log.open('a') as output:output.write('\n--- Eden ---\n'+source.read_text(errors='replace')[-24000:])
    atomic_json(folder/(entry.id+'.status.json'),{'exit':code,'seconds':round(time.monotonic()-start,1)})
    if code and notify and not stop_requested:
        issues,details=diagnostics(entry,store)
        show_error(entry.name+' terminó con error '+str(code)+'.\n\n'+('\n'.join(issues) or details[-2200:])+'\n\nRegistro local: '+str(log),store)
    return code if code>=0 else 128-code
