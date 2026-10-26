"""Release package families. Catalog metadata never supplies executable install commands."""
import pathlib,re,shutil,sys

ARCHIVES=('.zip','.7z','.rar','.tar.gz','.tgz','.tar.xz','.tar.bz2','.tbz2','.tar.zst','.tar')
SAVES=('UserData','userdata','saves','Saves','savegames','SaveGames','savedata','hdd','user')

def select(assets,runtime='auto',platforms=(),asset_prefix=''):
    from .ports import pick_asset
    if runtime not in ('auto','linux','proton'):raise ValueError('Runtime de instalación desconocido.')
    native=pick_asset([a for a in assets if not asset_prefix or a.get('name','').lower().startswith(asset_prefix.lower())]) if runtime!='proton' else None
    if native:return {'asset':native,'runtime':'linux','kind':'appimage' if native['name'].lower().endswith('.appimage') else 'archive' if native['name'].lower().endswith(ARCHIVES) else 'binary'}
    if runtime=='linux':return None
    platforms={p.lower() for p in platforms}
    windows_only='windows' in platforms and not any(p in platforms for p in ('linux','steamos'))
    candidates=[];unlabelled=[]
    for asset in assets:
        name=asset.get('name','').lower()
        if asset_prefix and not name.startswith(asset_prefix.lower()):continue
        if re.search(r'arm64|aarch64|armv|(?<![a-z])arm(?![a-z])|setup|installer|uninstall|source|symbols|debug|runtime|readme|patch|manifest|notices|license.compliance',name):continue
        if re.search(r'linux|steamos|macos|darwin|osx|android|flatpak|(?<![a-z])(?:mac|ios|appletv|visionos|3ds|nds|psp|psvita|switch|wiiu|gamecube|web)(?![a-z])|odroid',name):continue
        if not name.endswith((*ARCHIVES,'.exe')):continue
        windows=bool(re.search(r'(?<![a-z])(?:win|windows|win32|win64|windows32|windows64|mingw|msvc|w32|w64)(?![a-z])',name))
        if not (windows or name.endswith('.exe') or windows_only or runtime=='proton'):
            if name.endswith(ARCHIVES):unlabelled.append(asset)
            continue
        score=3 if re.search(r'x64|x86[_-]64|amd64|win64',name) else 1 if re.search(r'x86|win32|i386',name) else 2
        if re.search(r'(?<![a-z])(?:jp|japan|japanese)(?![a-z])',name):score-=1
        candidates.append((score,asset))
    if candidates:
        asset=max(candidates,key=lambda pair:pair[0])[1]
        return {'asset':asset,'runtime':'proton','kind':'archive' if asset['name'].lower().endswith(ARCHIVES) else 'binary'}
    if runtime=='auto' and unlabelled:
        asset=max(unlabelled,key=lambda a:bool(re.search(r'x64|x86[_-]64|amd64|64bit',a['name'],re.I)))
        return {'asset':asset,'runtime':'detect','kind':'archive'}
    return None

def summary(plan):
    if not plan:return 'Sin paquete compatible: requiere una integración específica o una compilación desde código fuente.'
    if plan['runtime']=='proton':return 'Windows portable · Proton · compatibilidad del juego sin comprobar.'
    if plan['runtime']=='detect':return 'Paquete sin etiqueta de sistema · se comprobará su contenido; Windows usa Proton.'
    return {'appimage':'AppImage de Linux','archive':'Paquete de Linux','binary':'Ejecutable de Linux'}[plan['kind']]+' · instalación y actualización desde Deck Library.'

def detect_runtime(folder):
    """Inspect executable headers instead of guessing Windows/Linux from a ZIP filename."""
    root=pathlib.Path(folder);native=False;windows=False
    for path in root.rglob('*'):
        if not path.is_file() or len(path.relative_to(root).parts)>3:continue
        if re.search(r'(^|/)(deps|tools|compiler|redist|third.party)(/|$)',path.relative_to(root).as_posix(),re.I):continue
        with path.open('rb') as source:magic=source.read(4)
        native|=magic==b'\x7fELF'
        windows|=path.suffix.lower()=='.exe' and magic[:2]==b'MZ'
    if native:return 'linux'
    if windows:return 'proton'
    raise ValueError('El paquete no contiene una aplicación Linux o Windows identificable. Puede ser código fuente o un constructor; conviene revisar los requisitos de su ficha.')

def windows_candidates(folder):
    from .ports import SKIP_NAMES
    root=pathlib.Path(folder)
    files=[p for p in root.rglob('*') if p.is_file() and p.suffix.lower()=='.exe' and len(p.relative_to(root).parts)<=3 and not SKIP_NAMES.search(p.name) and not re.search(r'redist|crash|helper|tools|vcredist|unitycrash',str(p.relative_to(root)),re.I)]
    def pe(path):
        with path.open('rb') as stream:return stream.read(2)==b'MZ'
    return sorted(p for p in files if pe(p))

def windows_executable(folder,repository=''):
    files=windows_candidates(folder)
    if len(files)==1:return files[0]
    # Portable families often contain a launcher and its corresponding engine.
    # Prefer that launcher only when every candidate belongs to the same pair.
    for launcher in files:
        match=re.fullmatch(r'(.+?)[ _-]?launcher',launcher.stem,re.I)
        if match and len(files)==2:
            key=re.sub('[^a-z0-9]','',match[1].lower())
            engine=next(p for p in files if p!=launcher)
            if engine.parent==launcher.parent and key==re.sub('[^a-z0-9]','',engine.stem.lower()):return launcher
    key=re.sub('[^a-z0-9]','',repository.rsplit('/',1)[-1].lower())
    named=[p for p in files if key and key==re.sub('[^a-z0-9]','',p.stem.lower())]
    return named[0] if len(named)==1 else ''

def preserve_saves(old,new,cancel=None,extra=(),exclude=()):
    from .ports import check_cancel
    for name in dict.fromkeys((*SAVES,*extra)):
        if pathlib.PurePath(name).is_absolute() or '..' in pathlib.PurePath(name).parts:raise ValueError('Destino de conservación inválido.')
        source=old/name
        if source.is_symlink():raise ValueError('La carpeta de partidas es un enlace; se conserva la instalación anterior.')
        if source.is_file():
            target=new/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);continue
        if not source.is_dir():continue
        for path in source.rglob('*'):
            check_cancel(cancel)
            if path.is_symlink():raise ValueError('Hay un enlace en las partidas; se conserva la instalación anterior.')
        target=new/name
        if target.exists() and not target.is_dir():raise ValueError('La nueva versión cambió la carpeta de partidas; se conserva la instalación anterior.')
        def ignore(directory,names):
            return [n for n in names if (pathlib.Path(directory)/n).relative_to(old).as_posix() in exclude]
        shutil.copytree(source,target,dirs_exist_ok=True,ignore=ignore)
