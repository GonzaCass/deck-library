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
GHL_LIST='https://raw.githubusercontent.com/SirDiabo/GHLAppList/main/apps.json'
SOURCE_NAMES={INDEX:'Quiver',GHL_LIST:'GithubLauncher'}
CACHE_SECONDS=24*3600
MAX_DOWNLOAD=2*1024**3
REPOSITORY=re.compile(r'[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}')
FOLDER=re.compile(r'[A-Za-z0-9][A-Za-z0-9 ._()-]{0,79}')
SKIP_NAMES=re.compile(r'setup|install|uninstall|updater|crashpad|crashhandler|\.so(\.|$)',re.I)
LAUNCHERS=('launch.sh','run.sh','start.sh')

def ports_root(home=None):return pathlib.Path(home or pathlib.Path.home())/'ports'

SETUP_KIT='Kit de instalación: requiere el disco y la BIOS propios y compila el juego en el primer inicio. En la Deck corre dentro del SDK de KDE de Flatpak, que la app instala una vez (sin root).'
BUILTIN=[
 {'name':'Spider-Man (PSX)','repository':'alexbeavs-ps1-ports/spider-man-recomp','folderName':'SpiderManPSX','category':'PlayStation','kit':True,'note':'Necesita el disco SLUS-00875 (EE. UU.) y la BIOS SCPH-5502 o 5552 (Europa). '+SETUP_KIT},
 {'name':'Spider-Man 2: Enter Electro (PSX)','repository':'alexbeavs-ps1-ports/spider-man-2-enter-electro-recomp','folderName':'SpiderMan2PSX','category':'PlayStation','kit':True,'note':'Necesita el disco SLUS-01378 (EE. UU., Rev 1) y la BIOS SCPH-1001 (EE. UU.). Una copia europea no sirve. '+SETUP_KIT},
]
PLATFORMS={'playstation':'PlayStation','ps1':'PlayStation','psx':'PlayStation','playstation 2':'PlayStation 2','ps2':'PlayStation 2','gamecube':'GameCube','wii':'Wii','nintendo':'Nintendo','n64':'Nintendo 64','xbox':'Xbox 360','rexglue':'Xbox 360'}

def platform_for(category):
    low=str(category).lower()
    for key in sorted(PLATFORMS,key=len,reverse=True):
        if key in low:return PLATFORMS[key]
    return ''

def parse_repository(text):
    """owner/repo from `owner/repo` or any github.com URL; None when it is something else."""
    text=str(text).strip()
    match=re.fullmatch(r'(?:https://github\.com/)?([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:/.*)?',text)
    repo=match[1]+'/'+match[2] if match else ''
    return repo if valid_repository(repo) else None

def valid_repository(repo):
    return isinstance(repo,str) and bool(REPOSITORY.fullmatch(repo)) and not any(part.strip('.')=='' for part in repo.split('/'))

def clean(item,category='',source=''):
    """A catalog entry reduced to the fields used here, or None when it is malformed."""
    if not isinstance(item,dict):return None
    repo=item.get('repository');folder=item.get('folderName') or item.get('folder') or ''
    if not valid_repository(repo):return None
    if not isinstance(folder,str) or not FOLDER.fullmatch(folder):folder=re.sub(r'[^A-Za-z0-9._-]','',repo.split('/')[1]) or 'port'
    name=item.get('name');icon=item.get('appIconUrl');category=str(item.get('category') or item.get('list') or category)[:80];note=item.get('note')
    ai=bool(re.match(r'AI\b',category));category=re.sub(r'^AI\s*-?\s*','',category) if ai else category
    return {'name':name if isinstance(name,str) and 0<len(name)<=120 else repo,'repository':repo,'folder':folder,'icon':icon if isinstance(icon,str) and icon.startswith('https://') else '','list':category,'source':source,'ai':ai,'note':note[:400] if isinstance(note,str) else '','kit':item.get('kit') is True}

def parse_source(document,source=''):
    """Entries of a Quiver list file ({apps:[...]}) or a GithubLauncher list ({category:[...]})."""
    if not isinstance(document,dict):return []
    rows=[]
    if isinstance(document.get('apps'),list):
        rows=[clean(a,document.get('name',''),source) for a in document['apps'][:2000]]
    else:
        for category,apps in list(document.items())[:60]:
            if isinstance(apps,list):rows+=[clean(a,category,source) for a in apps[:2000]]
    return [r for r in rows if r]

def fetch_catalog(get=fetch_json,extra=()):
    """Quiver's community lists, GithubLauncher's list and any extra raw-GitHub sources, merged by repository."""
    found={}
    def add(rows):
        for item in rows:
            key=item['repository'].lower();previous=found.get(key)
            if previous is None:found[key]=item
            else:
                # GithubLauncher's categories are finer than Quiver's; its AI-assisted flag is kept.
                if item['source']=='GithubLauncher' and item['list']:previous['list']=item['list']
                previous['ai']=previous['ai'] or item['ai'];previous['source']=', '.join(dict.fromkeys(filter(None,[*previous['source'].split(', '),item['source']])))
    failures=0
    for url in (INDEX,GHL_LIST,*extra):
        if not url.startswith('https://raw.githubusercontent.com/'):continue
        try:document=get(url)
        except (OSError,ValueError):failures+=1;continue
        source=SOURCE_NAMES.get(url,'Personalizada')
        if isinstance(document,dict) and isinstance(document.get('lists'),list):
            for entry in document['lists'][:40]:
                location=entry.get('remoteLocation','') if isinstance(entry,dict) else ''
                if not location.startswith('https://raw.githubusercontent.com/'):continue
                try:add(parse_source(get(location),source))
                except (OSError,ValueError):continue
        else:add(parse_source(document,source))
    if not found and failures:raise OSError('No se pudo descargar ninguna fuente del catálogo.')
    return sorted(found.values(),key=lambda i:i['name'].casefold())

def merged(apps,preferences=None):
    """Remote catalog plus the built-in recommendations and the user's own repositories; the latter two win on conflicts."""
    result={a['repository'].lower():a for a in apps}
    for raw,source in [(b,'Recomendado') for b in BUILTIN]+[(c,'Agregado') for c in (preferences or {}).get('custom_ports',[])]:
        item=clean(raw,'',source)
        if item:
            previous=result.get(item['repository'].lower(),{});result[item['repository'].lower()]={**previous,**{k:v for k,v in item.items() if v or k not in previous}}
    return sorted(result.values(),key=lambda i:i['name'].casefold())

ICON_LIMIT=2*1024*1024

def icon_path(store,item,get=None):
    """Cached icon or box art for a catalog entry, or '' when none is available. Network work: call off the GTK thread."""
    import hashlib
    from . import cover_provider
    folder=store.root/'catalog-icons';url=item.get('icon') or ''
    if not url:
        platform=platform_for(item.get('list',''))
        if not platform:return ''
        key='cover:'+platform+':'+item['name']
    else:key=url
    base=folder/hashlib.sha256(key.encode()).hexdigest()
    for suffix in ('.png','.jpg','.webp','.ico','.none'):
        if (base.with_suffix(suffix)).exists():return '' if suffix=='.none' else str(base.with_suffix(suffix))
    folder.mkdir(parents=True,exist_ok=True)
    try:
        if url:data=cover_provider.request(url,limit=ICON_LIMIT)
        else:
            title=re.sub(r'\s*\((?:PSX|PS1|PS2|N64)\)\s*$','',item['name'])
            rows=cover_provider.search(title,{'artwork_provider':'automatic','_artwork_platform':platform_for(item.get('list',''))})
            row=next((r for r in rows if cover_provider.normalized(r['title'])==cover_provider.normalized(title)),None)
            if not row:raise ValueError('sin portada')
            data=cover_provider.request(row['url'],limit=ICON_LIMIT)
    except (OSError,ValueError):
        base.with_suffix('.none').write_bytes(b'');return ''
    suffix='.png' if data.startswith(b'\x89PNG') else '.jpg' if data.startswith(b'\xff\xd8') else '.webp' if data[:4]==b'RIFF' else '.ico' if data[:4]==b'\x00\x00\x01\x00' else ''
    if not suffix:
        base.with_suffix('.none').write_bytes(b'');return ''
    base.with_suffix(suffix).write_bytes(data);return str(base.with_suffix(suffix))

def catalog(store,force=False,get=fetch_json,extra=()):
    """Cached list; a failed refresh falls back to the previous copy."""
    path=store.root/'catalog-ports.json'
    try:cached=json.loads(path.read_text())
    except (OSError,ValueError):cached={}
    if not force and cached.get('apps') and time.time()-cached.get('time',0)<CACHE_SECONDS:return cached['apps']
    try:apps=fetch_catalog(get,extra)
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
        from . import buildenv
        kit=buildenv.looks_like_kit(staging)
        executable=find_executable(staging,item['repository'])
        if executable:executable.chmod(executable.stat().st_mode|0o111)
        record={'repository':item['repository'],'name':item['name'],'folder':item['folder'],'tag':tag,'asset':asset['name'],'verified':digest.startswith('sha256:'),'executable':executable.name if executable else '','sandbox':kit,'date':time.strftime('%Y-%m-%dT%H:%M:%S')}
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
    from . import buildenv
    command=buildenv.wrap([str(exe)]) if record.get('sandbox') else [str(exe)]
    return Entry(record.get('name',folder.name),command,'port','Linux',str(exe),str(folder),metadata={'port_repository':record['repository'],'port_tag':record.get('tag',''),**({'sandbox':'flatpak-kde-sdk'} if record.get('sandbox') else {})})
