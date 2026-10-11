"""Community port catalog (Quiver's public lists) and installation of GitHub release assets.

The catalog is only metadata: a repository name per port. Installing downloads the latest release
asset for Linux x86_64 over HTTPS, verifies the digest GitHub publishes when there is one, extracts
with path checks and records what was installed so updates can be detected.
"""
import hashlib,json,os,pathlib,re,shutil,stat,tarfile,tempfile,time,urllib.error,urllib.request,zipfile
from . import __version__
from .models import Store,atomic_json
from .updates import fetch,fetch_json,RateLimited

INDEX='https://raw.githubusercontent.com/tgeorgiadis/quiver-community-app-catalog/main/index.json'
CACHE_SECONDS=24*3600
MAX_DOWNLOAD=2*1024**3
REPOSITORY=re.compile(r'[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}')
FOLDER=re.compile(r'[A-Za-z0-9][A-Za-z0-9 ._()-]{0,79}')
SKIP_NAMES=re.compile(r'setup|install|uninstall|updater|crashpad|crashhandler|\.so(\.|$)',re.I)
LAUNCHERS=('launch.sh','run.sh','start.sh')

def ports_root(home=None):return pathlib.Path(home or pathlib.Path.home())/'ports'

def clean(item,source=''):
    """A catalog entry reduced to the fields used here, or None when it is malformed."""
    if not isinstance(item,dict):return None
    repo=item.get('repository');folder=item.get('folderName') or ''
    if not isinstance(repo,str) or not REPOSITORY.fullmatch(repo):return None
    if not isinstance(folder,str) or not FOLDER.fullmatch(folder):folder=re.sub(r'[^A-Za-z0-9._-]','',repo.split('/')[1]) or 'port'
    name=item.get('name');icon=item.get('appIconUrl')
    return {'name':name if isinstance(name,str) and 0<len(name)<=120 else repo,'repository':repo,'folder':folder,'icon':icon if isinstance(icon,str) and icon.startswith('https://') else '','list':source}

def fetch_catalog(get=fetch_json):
    index=get(INDEX);found={}
    for entry in index.get('lists',[])[:40]:
        url=entry.get('remoteLocation','') if isinstance(entry,dict) else ''
        if not url.startswith('https://raw.githubusercontent.com/'):continue
        try:document=get(url)
        except (OSError,ValueError):continue
        for raw in document.get('apps',[])[:2000]:
            item=clean(raw,str(document.get('name','')))
            if item:found.setdefault(item['repository'].lower(),item)
    return sorted(found.values(),key=lambda i:i['name'].casefold())

def catalog(store,force=False,get=fetch_json):
    """Cached list; a failed refresh falls back to the previous copy."""
    path=store.root/'catalog-ports.json'
    try:cached=json.loads(path.read_text())
    except (OSError,ValueError):cached={}
    if not force and cached.get('apps') and time.time()-cached.get('time',0)<CACHE_SECONDS:return cached['apps']
    try:apps=fetch_catalog(get)
    except (OSError,ValueError,KeyError):
        if cached.get('apps'):return cached['apps']
        raise
    if apps:atomic_json(path,{'time':time.time(),'apps':apps})
    return apps

def pick_asset(assets):
    """Best Linux x86_64 asset: AppImage, then tar, then zip. None when the release has no Linux build."""
    best=None;best_score=0
    for asset in assets:
        name=str(asset.get('name',''));low=name.lower()
        if re.search(r'\.(sha256|sig|txt|md5|json|asc|exe|msi|dmg|apk|deb|rpm|pkg|7z|rar)$|source|src\b',low):continue
        if re.search(r'win|mac|osx|darwin|android|arm64|aarch64|armv|i386|x86\b|32-?bit',low):continue
        linux=bool(re.search(r'linux|steamdeck|steam-deck|deck',low))
        if not linux and not low.endswith('.appimage'):continue
        score=1
        if re.search(r'x86[_-]64|amd64|x64',low):score+=2
        bare='.' not in low.rsplit('-',1)[-1]
        score+={'.appimage':4,'.tar.gz':3,'.tgz':3,'.tar.xz':3,'.tar.zst':0,'.zip':2}.get(next((e for e in ('.appimage','.tar.gz','.tgz','.tar.xz','.tar.zst','.zip') if low.endswith(e)),''),3 if bare and linux else 0)
        if score>best_score and score>2:best,best_score=asset,score
    return best

def release_for(repo,get=fetch_json):
    """Latest release, or the newest pre-release when the project has no stable one."""
    try:return get(f'https://api.github.com/repos/{repo}/releases/latest')
    except urllib.error.HTTPError as error:
        if error.code!=404:raise
    rows=get(f'https://api.github.com/repos/{repo}/releases?per_page=1')
    if not rows:raise ValueError('El proyecto no tiene releases publicados.')
    return rows[0]

def records(store):
    try:return json.loads((store.root/'ports.json').read_text())
    except (OSError,ValueError):return {}

def download(url,target,limit=MAX_DOWNLOAD,progress=None):
    if not url.startswith('https://'):raise ValueError('La descarga debe usar HTTPS.')
    request=urllib.request.Request(url,headers={'User-Agent':'DeckLibrary/'+__version__})
    with urllib.request.urlopen(request,timeout=30) as response,open(target,'wb') as out:
        if not response.url.startswith('https://'):raise ValueError('La redirección no usa HTTPS.')
        total=int(response.headers.get('Content-Length') or 0);done=0
        if total>limit:raise ValueError('El archivo supera el límite de tamaño.')
        while True:
            block=response.read(1<<20)
            if not block:break
            done+=len(block)
            if done>limit:raise ValueError('El archivo supera el límite de tamaño.')
            out.write(block)
            if progress:progress(done,total)

def sha256_file(path):
    digest=hashlib.sha256()
    with open(path,'rb') as source:
        for block in iter(lambda:source.read(1<<20),b''):digest.update(block)
    return digest.hexdigest()

def extract(archive,destination):
    destination=pathlib.Path(destination).resolve();name=str(archive).lower()
    if name.endswith('.zip'):
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                if not (destination/info.filename).resolve().is_relative_to(destination):raise ValueError('El paquete contiene rutas inseguras.')
                if stat.S_ISLNK(info.external_attr>>16):raise ValueError('El paquete contiene enlaces simbólicos.')
            z.extractall(destination)
            for info in z.infolist():
                mode=info.external_attr>>16
                if mode&0o111 and not info.is_dir():(destination/info.filename).chmod(0o755)
    elif re.search(r'\.(tar\.gz|tgz|tar\.xz)$',name):
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if not (member.isfile() or member.isdir()):raise ValueError('El paquete contiene enlaces o archivos especiales.')
                if not (destination/member.name).resolve().is_relative_to(destination):raise ValueError('El paquete contiene rutas inseguras.')
            tar.extractall(destination,filter='data')
    else:raise ValueError('Formato de paquete no admitido: '+pathlib.Path(archive).name)

def flatten(folder):
    """If the archive wraps everything in one directory, move its contents up."""
    items=list(pathlib.Path(folder).iterdir())
    if len(items)==1 and items[0].is_dir():
        inner=items[0];temporary=inner.with_name(inner.name+'.flatten');inner.rename(temporary)
        for child in temporary.iterdir():child.rename(pathlib.Path(folder)/child.name)
        temporary.rmdir()

def is_elf(path):
    try:
        with open(path,'rb') as source:return source.read(4)==b'\x7fELF'
    except OSError:return False

def find_executable(folder,repository=''):
    """Pick the file that starts the port, or '' when it is ambiguous."""
    folder=pathlib.Path(folder);files=[p for p in folder.iterdir() if p.is_file() and not SKIP_NAMES.search(p.name)]
    for name in LAUNCHERS:
        match=next((p for p in files if p.name.lower()==name),None)
        if match:return match
    images=[p for p in files if p.suffix.lower()=='.appimage']
    if len(images)==1:return images[0]
    binaries=[p for p in files if is_elf(p) or (p.suffix.lower()=='.sh')]
    if len(binaries)==1:return binaries[0]
    key=re.sub(r'[^a-z0-9]','',repository.split('/')[-1].lower())
    named=[p for p in binaries if key and key in re.sub(r'[^a-z0-9]','',p.name.lower())]
    return named[0] if len(named)==1 else ''

def install(item,store=None,root=None,progress=print,get=fetch_json,replace=False):
    """Install or update one catalog port. Returns the stored record."""
    store=store or Store();root=pathlib.Path(root or ports_root());item=clean(item)
    if item is None:raise ValueError('Entrada de catálogo inválida.')
    release=release_for(item['repository'],get);asset=pick_asset(release.get('assets',[]))
    if asset is None:raise ValueError('La última versión no incluye un archivo para Linux x86_64. Se puede instalar manualmente desde '+release.get('html_url','GitHub')+'.')
    tag=str(release.get('tag_name',''));destination=root/item['folder']
    if destination.exists() and not replace:raise ValueError('La carpeta '+item['folder']+' ya existe en '+str(root)+'.')
    if destination.is_symlink():raise ValueError('La carpeta de destino es un enlace simbólico.')
    root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='port-',dir=root) as temp:
        temp=pathlib.Path(temp);archive=temp/asset['name'].replace('/','_');progress('Descargando '+asset['name'])
        download(asset['browser_download_url'],archive,progress=lambda d,t:progress(f'Descargando {asset["name"]}: {d//(1<<20)} de {t//(1<<20)} MB' if t else f'Descargando {asset["name"]}: {d//(1<<20)} MB'))
        digest=str(asset.get('digest') or '')
        if digest.startswith('sha256:') and sha256_file(archive)!=digest[7:].lower():raise ValueError('La suma SHA-256 no coincide con la publicada; no se instaló.')
        staging=temp/'files';staging.mkdir()
        if not re.search(r'\.(zip|tar\.gz|tgz|tar\.xz)$',archive.name.lower()):
            # AppImage or a single bare executable.
            shutil.copy2(archive,staging/archive.name);(staging/archive.name).chmod(0o755)
        else:
            progress('Extrayendo');extract(archive,staging);flatten(staging)
        executable=find_executable(staging,item['repository'])
        if executable:executable.chmod(executable.stat().st_mode|0o111)
        record={'repository':item['repository'],'name':item['name'],'folder':item['folder'],'tag':tag,'asset':asset['name'],'verified':digest.startswith('sha256:'),'executable':executable.name if executable else '','date':time.strftime('%Y-%m-%dT%H:%M:%S')}
        atomic_json(staging/'.deck-library-port.json',record)
        if destination.exists():
            old=root/'.deck-library-replaced'/(item['folder']+'-'+time.strftime('%Y%m%dT%H%M%S'));old.parent.mkdir(exist_ok=True);destination.rename(old)
        shutil.move(str(staging),str(destination))
    saved=records(store);saved[item['repository']]=record;atomic_json(store.root/'ports.json',saved)
    return record

def installed_updates(store,get=fetch_json):
    """Catalog ports whose recorded tag differs from the latest release."""
    result=[]
    for repo,record in records(store).items():
        try:release=release_for(repo,get)
        except (OSError,ValueError):continue
        tag=str(release.get('tag_name',''))
        if tag and tag!=record.get('tag') and pick_asset(release.get('assets',[])):result.append({'name':record.get('name',repo),'repository':repo,'installed':record.get('tag',''),'latest':tag,'page':release.get('html_url','')})
    return result

def entry_for(folder):
    """Library entry for a port installed by this module, or None."""
    from .models import Entry
    folder=pathlib.Path(folder)
    try:record=json.loads((folder/'.deck-library-port.json').read_text())
    except (OSError,ValueError):return None
    exe=folder/record.get('executable','') if record.get('executable') else None
    if not exe or not exe.is_file():return None
    return Entry(record.get('name',folder.name),[str(exe)],'port','Linux',str(exe),str(folder),metadata={'port_repository':record['repository'],'port_tag':record.get('tag','')})
