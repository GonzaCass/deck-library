"""First-run wizard worker for the official, pinned WiiCompiled setup."""
import datetime,json,os,pathlib,shutil,signal,subprocess,tempfile,threading,urllib.request
from .models import Store
from .runtime import clean_environment
from .installations import settings,save_settings

VERSION='0.2.33'
SDK='org.kde.Sdk//6.11'
SETUP_URL='https://github.com/patchzyy/Wiicompiled/releases/download/v0.2.33/WiiCompiled-Setup-x86_64.AppImage'

class Cancelled(RuntimeError):pass

def check_image(path):
    path=pathlib.Path(path)
    if not path.is_file():raise ValueError('Elegir la imagen de Mario Kart Wii.')
    if path.suffix.lower() not in ('.iso','.gcm','.gcz','.ciso','.wbfs','.wia','.rvz'):raise ValueError('Formato no compatible con el setup oficial.')
    if path.suffix.lower() in ('.iso','.gcm'):
        with path.open('rb') as source:header=source.read(6)
        if header!=b'RMCP01':raise ValueError('Se necesita Mario Kart Wii PAL limpio RMCP01. Esta imagen no corresponde.')
    return path.resolve()

def run_logged(command,cwd,env,log,progress,cancel):
    progress('Ejecutando '+pathlib.Path(command[0]).name+'…')
    process=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',start_new_session=True,bufsize=1)
    def collect():
        for line in process.stdout:
            log.write(line);log.flush();progress(line.strip()[-350:])
    reader=threading.Thread(target=collect,daemon=True);reader.start()
    while process.poll() is None:
        if cancel.wait(.3):
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            reader.join(timeout=2);process.stdout.close();raise Cancelled('Instalación cancelada; la imagen original se conserva.')
    reader.join(timeout=5)
    process.stdout.close()
    if process.returncode:raise RuntimeError('El proceso terminó con error '+str(process.returncode)+'. Ver el registro de instalación.')

def install(image,store=None,setup=None,progress=lambda text:None,cancel=None):
    image=check_image(image);store=store or Store();cancel=cancel or threading.Event()
    if not shutil.which('flatpak'):raise RuntimeError('Se necesita Flatpak para el entorno de compilación. No se cambió SteamOS.')
    if shutil.disk_usage(store.root if store.root.exists() else pathlib.Path.home()).free<20_000_000_000:raise RuntimeError('La recompilación necesita aproximadamente 20 GB libres temporalmente.')
    workspace=store.root/'wii-setup';workspace.mkdir(parents=True,exist_ok=True)
    data_home=store.root/'wiicompiled-runtime';root=data_home/'WiiCompiled';env=clean_environment()
    log_path=workspace/'install.log'
    with log_path.open('a') as log:
        log.write('\n'+datetime.datetime.now().isoformat()+' — WiiCompiled '+VERSION+'\n')
        health=subprocess.run(['flatpak','info',SDK],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if health.returncode:
            progress('Instalando el SDK de compilación desde Flathub…')
            # Explicit user wizard action authorizes these dependencies; no sudo/system unlock.
            run_logged(['flatpak','remote-add','--user','--if-not-exists','flathub','https://dl.flathub.org/repo/flathub.flatpakrepo'],workspace,env,log,progress,cancel)
            run_logged(['flatpak','install','--user','-y','--noninteractive','flathub',SDK],workspace,env,log,progress,cancel)
        if setup is None:
            setup=workspace/'WiiCompiled-Setup-x86_64.AppImage'
            if not setup.exists():
                temporary=setup.with_suffix('.download')
                progress('Descargando el setup oficial '+VERSION+'…')
                try:
                    with urllib.request.urlopen(SETUP_URL,timeout=30) as response,temporary.open('wb') as out:
                        total=int(response.headers.get('Content-Length',0));count=0
                        while True:
                            if cancel.is_set():raise Cancelled('Descarga cancelada.')
                            chunk=response.read(1024*1024)
                            if not chunk:break
                            out.write(chunk);count+=len(chunk);progress(f'Descargando setup: {count//1024**2} MiB'+(f' / {total//1024**2} MiB' if total else ''))
                    with temporary.open('rb') as inp:
                        if inp.read(4)!=b'\x7fELF':raise ValueError('La descarga no es un AppImage ELF.')
                    temporary.chmod(0o755);temporary.replace(setup)
                finally:
                    if temporary.exists():temporary.unlink()
        setup=pathlib.Path(setup).resolve()
        if not setup.is_file():raise ValueError('No se encuentra el setup seleccionado.')
        command=['flatpak','run','--share=network','--filesystem=home','--env=APPIMAGE_EXTRACT_AND_RUN=1','--env=DISABLE_AUTO_UPDATES=1','--env=XDG_DATA_HOME='+str(data_home),'--command='+str(setup),SDK]
        root.mkdir(parents=True,exist_ok=True)
        product=root/'Install/Base/WiiCompiled'
        if (root/'deck-library-install.json').exists():raise RuntimeError('Esta instalación ya está preparada. El juego ya está en la biblioteca y no se sobrescribió.')
        if not product.exists():run_logged(command+['install','--game',str(image)],workspace,env,log,progress,cancel)
        else:progress('Retomando la optimización de la instalación incompleta…')
        state=json.loads((root/'install-state.json').read_text());base=next((p for p in state.get('Products',[]) if p.get('Profile')=='base'),None)
        if not base:raise RuntimeError('El setup no registró el producto base.')
        product=pathlib.Path(base['InstallDirectory'])/base.get('ExecutableName','WiiCompiled')
        # Reuse our tested Escape fix on the exact known source; don't modify unknown releases.
        native=root/'workspace';source=native/'runtime/src/settings_overlay.cpp'
        old='if (!g_rebind.active && IsToggleKey(ev->sdl, SDL_SCANCODE_ESCAPE)) {'
        new='if (!g_rebind.active && (IsToggleKey(ev->sdl, SDL_SCANCODE_F12) || (g_topBarVisible && IsToggleKey(ev->sdl, SDL_SCANCODE_ESCAPE)))) {'
        if not source.exists() or (source.read_text().count(old)!=1 and source.read_text().count(new)!=1):raise RuntimeError('Fuente del parche de controles no reconocida. El juego se compiló, pero no se aplicó automáticamente la optimización.')
        if source.read_text().count(old)==1:
            backup=source.with_suffix('.cpp.original');shutil.copy2(source,backup);source.write_text(source.read_text().replace(old,new))
        # Stabilize toolkit symlinks: the setup's temporary AppImage mount has already gone.
        extract=workspace/'toolkit';extract.mkdir(exist_ok=True)
        if not (extract/'squashfs-root').exists():run_logged(command+['--appimage-extract'],extract,env,log,progress,cancel)
        for name,relative in (('toolchain','usr/toolchain'),('native-prebuilt','native-prebuilt')):
            link=native/name;target=extract/'squashfs-root'/relative
            if not target.is_dir() or not link.is_symlink():raise RuntimeError('Toolkit no reconocido; no se reemplazó el juego.')
            link.unlink();link.symlink_to(target)
        run_logged(['flatpak','run','--share=network','--filesystem=home','--command='+str(native/'toolchain/bin/cmake'),SDK,'--build',str(native/'native-build'),'--target','WiiCompiled','--parallel','2'],workspace,env,log,progress,cancel)
        rebuilt=native/'native-build/WiiCompiled';shutil.copy2(product,product.with_name('WiiCompiled.before-deck-library'));temporary=product.with_name('WiiCompiled.installing');shutil.copy2(rebuilt,temporary);temporary.replace(product)
    preferences=settings(store);preferences['wiicompiled_roots']=list(dict.fromkeys(preferences['wiicompiled_roots']+[str(root)]));save_settings(preferences,store)
    from .models import atomic_json
    from .models import Entry
    entry=Entry('Mario Kart Wii',['/usr/bin/flatpak','run','--socket=x11','--socket=wayland','--socket=pulseaudio','--device=dri','--share=ipc','--filesystem=home','--env=XDG_DATA_HOME='+str(data_home),'--command='+str(product),SDK],'wiicompiled','WiiCompiled',str(product),str(product.parent),game_id='RMCP01',metadata={'adapter':'wiicompiled','config':str(root/'Config.toml'),'data_root':str(root),'build':VERSION,'sdk':SDK,'data_home':str(data_home),'exit_patch':'F12'})
    # Config doesn't exist on a fresh product until the first run. Initialize only our private root.
    config=root/'Config.toml'
    if not config.exists():config.write_text('[paths]\ndvd_root = '+json.dumps(str(native/'Assets/DATA'))+'\n')
    store.merge([entry])
    from .presets import catalog,apply
    preset=next(p for p in catalog(store) if p['id']=='wiicompiled-rmcp01-sharp');apply(entry,preset,store)
    atomic_json(root/'deck-library-install.json',{'sdk':SDK,'data_home':str(data_home),'build':VERSION,'exit_patch':'F12'})
    progress('Recompilación y preset completados. Ya podés agregarlo a Steam.')
    return entry
