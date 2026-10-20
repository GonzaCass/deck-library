"""Release package families. Catalog metadata never supplies executable install commands."""
import pathlib,re,shutil,sys

ARCHIVES=('.zip','.tar.gz','.tgz','.tar.xz','.tar.bz2','.tbz2','.tar.zst','.tar')
SAVES=('UserData','userdata','saves','Saves','savegames','SaveGames')

def select(assets):
    from .ports import pick_asset
    native=pick_asset(assets)
    if native:return {'asset':native,'runtime':'linux','kind':'appimage' if native['name'].lower().endswith('.appimage') else 'archive' if native['name'].lower().endswith(ARCHIVES) else 'binary'}
    candidates=[]
    for asset in assets:
        name=asset.get('name','').lower()
        if re.search(r'arm64|aarch64|win32|i386|(?<![a-z0-9])x86(?![_-]?64)|setup|installer|uninstall|source|symbols|debug',name):continue
        if not re.search(r'(?<![a-z])(?:win|windows|win64)(?![a-z])',name):continue
        if not name.endswith(('.zip','.exe')):continue
        candidates.append((2 if re.search(r'x64|x86[_-]64|amd64|win64',name) else 1,asset))
    if candidates:return {'asset':max(candidates,key=lambda pair:pair[0])[1],'runtime':'proton','kind':'archive' if max(candidates,key=lambda pair:pair[0])[1]['name'].lower().endswith('.zip') else 'binary'}
    return None

def summary(plan):
    if not plan:return 'Sin paquete compatible: requiere una integración específica o una compilación desde código fuente.'
    if plan['runtime']=='proton':return 'Windows portable · Proton · instalación y actualización desde Deck Library.'
    return {'appimage':'AppImage de Linux','archive':'Paquete de Linux','binary':'Ejecutable de Linux'}[plan['kind']]+' · instalación y actualización desde Deck Library.'

def windows_executable(folder,repository=''):
    from .ports import SKIP_NAMES
    root=pathlib.Path(folder)
    files=[p for p in root.rglob('*.exe') if len(p.relative_to(root).parts)<=3 and not SKIP_NAMES.search(p.name) and not re.search(r'redist|crash|helper|tools|vcredist|unitycrash',str(p.relative_to(root)),re.I)]
    def pe(path):
        with path.open('rb') as stream:return stream.read(2)==b'MZ'
    files=[p for p in files if pe(p)]
    if len(files)==1:return files[0]
    key=re.sub('[^a-z0-9]','',repository.rsplit('/',1)[-1].lower())
    named=[p for p in files if key and key==re.sub('[^a-z0-9]','',p.stem.lower())]
    return named[0] if len(named)==1 else ''

def preserve_saves(old,new,cancel=None):
    from .ports import check_cancel
    for name in SAVES:
        source=old/name
        if source.is_symlink():raise ValueError('La carpeta de partidas es un enlace; se conserva la instalación anterior.')
        if not source.is_dir():continue
        for path in source.rglob('*'):
            check_cancel(cancel)
            if path.is_symlink():raise ValueError('Hay un enlace en las partidas; se conserva la instalación anterior.')
        target=new/name
        if target.exists() and not target.is_dir():raise ValueError('La nueva versión cambió la carpeta de partidas; se conserva la instalación anterior.')
        shutil.copytree(source,target,dirs_exist_ok=True)
