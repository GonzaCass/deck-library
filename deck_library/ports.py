"""Community port catalog (Quiver's public lists) and installation of GitHub release assets.

The catalog is only metadata: a repository name per port. Installing downloads the latest release
asset for Linux x86_64 over HTTPS, verifies the digest GitHub publishes when there is one, extracts
with path checks and records what was installed so updates can be detected.
"""
import hashlib,json,os,pathlib,re,shutil,stat,subprocess,tarfile,tempfile,time,urllib.error,urllib.parse,urllib.request,zipfile
from . import __version__
from .models import Store,atomic_json
from .updates import fetch,fetch_json,RateLimited
from .presets import ps1_serial

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
WEB_HOSTS=('dl.openpete.com','ctr.cmzi.uk')
BUILTIN=[
 {'name':'Spider-Man (PS1 recompilado)','repository':'alexbeavs-ps1-ports/spider-man-recomp','folderName':'SpiderManPSX','category':'PlayStation','kit':True,'setup':'kit','cover_title':'Spider-Man','bios':{'name':'SCPH-5502 o 5552 (Europa)','sha256':['1faaa18fa820a0225e488d9f086296b8e6c46df739666093987ff7d8fd352c09']},'disc':{'serial':'SLUS-00875','match':'spiderman','exclude':'spiderman2'},'note':'Necesita el disco SLUS-00875 (EE. UU.) y la BIOS SCPH-5502 o 5552 (Europa). '+SETUP_KIT},
 {'name':'Spider-Man 2: Enter Electro (PS1 recompilado)','repository':'alexbeavs-ps1-ports/spider-man-2-enter-electro-recomp','folderName':'SpiderMan2PSX','category':'PlayStation','kit':True,'setup':'kit','cover_title':'Spider-Man 2 - Enter - Electro','bios':{'name':'SCPH-1001 (EE. UU.)','sha256':['71af94d1e47a68c11e8fdb9f8368040601514a42a5a399cda48c7d3bff1e99d3']},'disc':{'serial':'SLUS-01378','match':'spiderman2enterelectro','exclude':''},'note':'Necesita el disco SLUS-01378 (EE. UU., Rev 1) y la BIOS SCPH-1001 (EE. UU.). Una copia europea no sirve. '+SETUP_KIT},
 {'name':'Spyro the Dragon (OpenPete)','repository':'web/openpete','folderName':'OpenPete','category':'PlayStation','kit':True,'setup':'openpete','web':{'kind':'openpete'},'cover_title':'Spyro the Dragon','disc':{'serial':'SCUS-94228','match':'spyrothedragon','exclude':''},'note':'Descarga de openpete.com (se verifica el SHA-256 publicado). Necesita el disco NTSC-U SCUS-94228. Compila el juego desde el disco en el primer inicio, dentro del SDK de KDE de Flatpak.'},
 {'name':'Crash Team Racing: Turbocharged','repository':'web/ctr-turbocharged','folderName':'CTRTurbocharged','category':'PlayStation','setup':'ctr','web':{'kind':'ctr'},'cover_title':'CTR - Crash Team Racing','disc':{'serial':'SCUS-94426','match':'crashteamracing','exclude':''},'note':'Descarga de ctr.cmzi.uk (el sitio no publica hash; se comprueba el tamaño). Necesita el BIN crudo MODE2/2352 del disco NTSC-U SCUS-94426, que se copia como ctr-u.bin en ~/.local/share/ctr-turbocharged.'},
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

BIOS_SIZE=524288

def find_bios(sha256,home=None):
    """First BIOS file whose SHA-256 matches, searching the usual EmuDeck folders; '' when none."""
    home=pathlib.Path(home or pathlib.Path.home());wanted={h.lower() for h in sha256}
    roots=[home/'Emulation/bios',home/'.config/EmuDeck/bios']
    try:
        from .installations import emudeck_paths
        roots.insert(0,pathlib.Path(emudeck_paths(home)['root'])/'bios')
    except (OSError,KeyError):pass
    for root in dict.fromkeys(roots):
        try:files=[f for f in sorted(root.glob('*'))+sorted(root.glob('*/*')) if f.is_file() and f.stat().st_size==BIOS_SIZE]
        except OSError:continue
        for file in files:
            try:
                if sha256_file(file) in wanted:return str(file)
            except OSError:continue
    return ''

def find_disc(spec,games):
    """A library disc whose SYSTEM.CNF serial equals spec['serial'] (BIN, ISO or CUE only). Returns {name, source, cue, bin} or None."""
    for game in games:
        name,source=(game,'') if isinstance(game,str) else game
        path=pathlib.Path(source) if source else None
        if path is None or path.suffix.lower() not in ('.cue','.bin','.iso','.img'):continue
        if ps1_serial(path)!=spec.get('serial'):continue
        cue=path if path.suffix.lower()=='.cue' else next((c for c in (path.with_suffix('.cue'),path.with_suffix('.CUE')) if c.is_file()),None)
        binary=path
        if path.suffix.lower()=='.cue':
            match=re.search(r'FILE\s+"([^"]+)"',path.read_text(errors='replace'));binary=path.parent/match[1] if match else None
        return {'name':name,'source':str(path),'cue':str(cue) if cue else '','bin':str(binary) if binary else ''}
    return None

def requirements(item,games,home=None):
    """Lines (ok, text) describing what a port still needs, from what the library already has.

    `games` holds names or (name, source) pairs. A disc is matched by its serial when the source is a readable image;
    otherwise by Redump-style name, in which case ok is None (only a name check was possible).
    """
    lines=[]
    if item.get('bios'):
        found=find_bios(item['bios'].get('sha256',[]),home)
        lines.append((True,'BIOS '+item['bios'].get('name','')+': encontrada en '+found) if found else (False,'BIOS '+item['bios'].get('name','')+': no se encontró un archivo con el hash exacto.'))
    disc=item.get('disc')
    if disc:
        exact=find_disc(disc,games)
        if exact:lines.append((True,'Disco '+disc['serial']+': encontrado «'+exact['name']+'» (serial verificado en el disco).'));return lines
        names=[g if isinstance(g,str) else g[0] for g in games]
        def key(name):return re.sub(r'[^a-z0-9]','',re.sub(r'\([^)]*\)|\[[^]]*\]','',name.lower()))
        match=[n for n in names if key(n).startswith(disc.get('match','\0')) and not (disc.get('exclude') and key(n).startswith(disc['exclude']))]
        usa=[n for n in match if '(USA' in n]
        if usa:lines.append((None,'Disco '+disc['serial']+': posible copia USA «'+usa[0]+'». Se confirma en el asistente, que exige el hash exacto de Redump.'))
        elif match:lines.append((False,'Disco '+disc['serial']+': la biblioteca solo tiene «'+match[0]+'», de otra región o en un formato que no se puede leer. El port exige la edición NTSC-U.'))
        else:lines.append((False,'Disco '+disc['serial']+': no hay una copia en la biblioteca; se necesita la edición NTSC-U.'))
    return lines

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
    return {'name':name if isinstance(name,str) and 0<len(name)<=120 else repo,'repository':repo,'folder':folder,'icon':icon if isinstance(icon,str) and icon.startswith('https://') else '','list':category,'source':source,'ai':ai,'note':note[:400] if isinstance(note,str) else '','kit':item.get('kit') is True,'setup':item.get('setup') if item.get('setup') in ('kit','openpete','ctr') else '','web':item.get('web') if isinstance(item.get('web'),dict) and item['web'].get('kind') in ('openpete','ctr') else None,'cover_title':str(item.get('cover_title') or '')[:120],'bios':item.get('bios') if isinstance(item.get('bios'),dict) else None,'disc':item.get('disc') if isinstance(item.get('disc'),dict) else None}

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
            title=item.get('cover_title') or re.sub(r'\s*\((?:PSX|PS1|PS2|N64)(?: recompilado)?\)\s*$','',item['name'])
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

def resolve_web(web,page=None):
    """Current download of a port published on its own website: {tag, name, url, sha256, size, page}."""
    kind=web.get('kind')
    if kind=='openpete':
        home='https://www.openpete.com/';text=(page or fetch(home,limit=4*1024*1024).decode('utf-8','replace'))
        link=re.search(r'https://dl\.openpete\.com/(OpenPete-v([0-9.]+)-x86_64\.AppImage)',text)
        if not link:raise ValueError('No se encontró el AppImage de Linux en openpete.com.')
        plain=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',text));digest=re.search(r'Linux AppImage has the SHA-256 hash ([0-9a-f]{64})',plain)
        return {'tag':'v'+link[2],'name':link[1],'url':link[0],'sha256':digest[1] if digest else '','size':0,'page':home}
    if kind=='ctr':
        home='https://ctr.cmzi.uk/';text=(page or fetch(home,limit=4*1024*1024).decode('utf-8','replace'))
        start=text.find('window.__BUILDS__=')
        if start<0:raise ValueError('No se encontró la lista de builds en ctr.cmzi.uk.')
        data,_=json.JSONDecoder().raw_decode(text[start+len('window.__BUILDS__='):])
        build=next((b for b in data.get('builds',[]) if b.get('key')=='appimage' and b.get('platform')=='linux'),None)
        if not build or not str(build.get('downloadUrl','')).startswith('/api/download/'):raise ValueError('No hay un AppImage de Linux en la lista de builds.')
        return {'tag':str(build.get('commit','')),'name':build['name'],'url':home.rstrip('/')+build['downloadUrl'],'sha256':'','size':int(build.get('size') or 0),'page':home}
    raise ValueError('Fuente web desconocida.')

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

def install(item,store=None,root=None,progress=print,get=fetch_json,replace=False,web=None,runner=None):
    """Install or update one catalog port. Returns the stored record."""
    store=store or Store();root=pathlib.Path(root or ports_root());item=clean(item)
    if item is None:raise ValueError('Entrada de catálogo inválida.')
    if item['web']:
        resolved=(web or resolve_web)(item['web'])
        if urllib.parse.urlparse(resolved['url']).hostname not in WEB_HOSTS:raise ValueError('La descarga apunta a un servidor no permitido.')
        asset={'name':resolved['name'],'browser_download_url':resolved['url'],'digest':('sha256:'+resolved['sha256']) if resolved.get('sha256') else '','size':resolved.get('size') or 0};tag=resolved['tag']
    else:
        release=release_for(item['repository'],get);asset=pick_asset(release.get('assets',[]))
        if asset is None:raise ValueError('La última versión no incluye un archivo para Linux x86_64. Se puede instalar manualmente desde '+release.get('html_url','GitHub')+'.')
        tag=str(release.get('tag_name',''))
    destination=root/item['folder']
    if destination.exists() and not replace:raise ValueError('La carpeta '+item['folder']+' ya existe en '+str(root)+'.')
    if destination.is_symlink():raise ValueError('La carpeta de destino es un enlace simbólico.')
    root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='port-',dir=root) as temp:
        temp=pathlib.Path(temp);archive=temp/asset['name'].replace('/','_');progress('Descargando '+asset['name'])
        download(asset['browser_download_url'],archive,progress=lambda d,t:progress(f'Descargando {asset["name"]}: {d//(1<<20)} de {t//(1<<20)} MB' if t else f'Descargando {asset["name"]}: {d//(1<<20)} MB'))
        digest=str(asset.get('digest') or '')
        if asset.get('size') and archive.stat().st_size!=asset['size']:raise ValueError('El tamaño descargado no coincide con el publicado; no se instaló.')
        if digest.startswith('sha256:') and sha256_file(archive)!=digest[7:].lower():raise ValueError('La suma SHA-256 no coincide con la publicada; no se instaló.')
        staging=temp/'files';staging.mkdir()
        if not re.search(r'\.(zip|tar\.gz|tgz|tar\.xz)$',archive.name.lower()):
            # AppImage or a single bare executable.
            shutil.copy2(archive,staging/archive.name);(staging/archive.name).chmod(0o755)
        else:
            progress('Extrayendo');extract(archive,staging);flatten(staging)
        from . import buildenv
        kit=buildenv.looks_like_kit(staging)
        if item['web'] and item['web']['kind']=='openpete':
            # The AppImage is unpacked once: its compiler needs the SDK's headers, and the module it builds is kept next to the unpacked files.
            progress('Desempaquetando OpenPete');(runner or subprocess.run)([str(staging/archive.name),'--appimage-extract'],cwd=str(staging),capture_output=True,timeout=300,check=True)
            (staging/archive.name).unlink();executable=staging/'squashfs-root/AppRun';kit=True
        else:executable=find_executable(staging,item['repository'])
        if executable:executable.chmod(executable.stat().st_mode|0o111)
        record={'repository':item['repository'],'name':item['name'],'folder':item['folder'],'tag':tag,'asset':asset['name'],'verified':digest.startswith('sha256:'),'executable':str(executable.relative_to(staging)) if executable else '','sandbox':kit,'setup':item['setup'],'web':item['web']['kind'] if item['web'] else '','cover_title':item['cover_title'],'disc':item['disc'],'bios':item['bios'],'args':[],'configured':False,'date':time.strftime('%Y-%m-%dT%H:%M:%S')}
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
        if record.get('web'):
            try:resolved=resolve_web({'kind':record['web']})
            except (OSError,ValueError):continue
            if resolved['tag'] and resolved['tag']!=record.get('tag'):result.append({'name':record.get('name',repo),'repository':repo,'installed':record.get('tag',''),'latest':resolved['tag'],'page':resolved['page']})
            continue
        try:release=release_for(repo,get)
        except (OSError,ValueError):continue
        tag=str(release.get('tag_name',''))
        if tag and tag!=record.get('tag') and pick_asset(release.get('assets',[])):result.append({'name':record.get('name',repo),'repository':repo,'installed':record.get('tag',''),'latest':tag,'page':release.get('html_url','')})
    return result

def port_id(repository):
    """Stable library id for a catalog port, so the entry survives a change of executable."""
    import hashlib
    return hashlib.sha256(('port:'+repository.lower()).encode()).hexdigest()[:20]

def entry_for(folder):
    """Library entry for a port installed by this module, or None.

    A setup kit that has already been generated and compiled starts its built game directly
    (`--no-launcher`) instead of reopening the setup wizard.
    """
    from .models import Entry
    from . import buildenv
    folder=pathlib.Path(folder)
    try:record=json.loads((folder/'.deck-library-port.json').read_text())
    except (OSError,ValueError):return None
    exe=folder/record.get('executable','') if record.get('executable') else None
    if not exe or not exe.is_file():return None
    args=list(record.get('args') or []);cwd=str(folder);built=folder/'build'/exe.name
    if record.get('sandbox') and built.is_file():
        # The built game's own launcher adopts the BIOS on first run and stores it in bios.cfg; only then can it boot directly.
        exe=built;cwd=str(built.parent)
        if (built.parent/'bios.cfg').is_file():args=[*args,'--no-launcher']
    command=buildenv.wrap([str(exe),*args]) if record.get('sandbox') else [str(exe)]
    title=record.get('cover_title') or next((b.get('cover_title','') for b in BUILTIN if b['repository']==record['repository']),'')
    return Entry(record.get('name',folder.name),command,'port','Linux',str(exe),cwd,id=port_id(record['repository']),metadata={'port_repository':record['repository'],**({'game_title':title} if title else {}),'port_tag':record.get('tag',''),**({'sandbox':'flatpak-kde-sdk'} if record.get('sandbox') else {}),**({'built':True} if built.is_file() and record.get('sandbox') else {}),**({'configured':True} if record.get('configured') else {})})


DATA_CTR=pathlib.Path('.local/share/ctr-turbocharged')

def configure(repository,store=None,games=(),progress=print,home=None,run=None):
    """Prepare an installed port with what the Deck already has: the disc from the library and, for kits, the BIOS found by hash.

    kit: verify the disc, generate the recompiled code and build it inside the SDK, then store the BIOS choice.
    openpete: pre-build the game module inside the SDK and remember the disc.
    ctr: copy the raw BIN as ctr-u.bin into the game's data folder.
    Returns the updated record; raises ValueError with what is missing.
    """
    from . import buildenv
    store=store or Store();home=pathlib.Path(home or pathlib.Path.home());run=run or buildenv.run
    record=records(store).get(repository)
    if not record or not record.get('setup'):raise ValueError('Este port no necesita configuración.')
    folder=ports_root(home)/record['folder']
    if not folder.is_dir():raise ValueError('La carpeta del port ya no existe: '+str(folder))
    problems=[text for ok,text in requirements(record,games,home) if ok is False]
    if problems:raise ValueError('Faltan requisitos:\n'+'\n'.join(problems))
    disc=find_disc(record['disc'],games) if record.get('disc') else None
    if record.get('disc') and not disc:raise ValueError('No se encontró el disco '+record['disc']['serial']+' en un formato legible (BIN, ISO o CUE).')
    kind=record['setup'];executable=folder/record['executable']
    if kind=='kit':
        if not disc['cue']:raise ValueError('El kit necesita el archivo .cue del disco.')
        bios=find_bios(record['bios']['sha256'],home);cli='psxrecomp/psxrecomp_cli.py';base=['python3',cli]
        progress('Verificando el disco');run([*base,'verify-disc','--config','game.toml','--project-root','.','--disc',disc['cue']],cwd=str(folder),progress=progress)
        progress('Generando el juego a partir del disco');run([*base,'generate','--config','game.toml','--project-root','.','--disc',disc['cue'],'--bios',bios],cwd=str(folder),progress=progress)
        progress('Compilando (varios minutos)');run([*base,'rebuild','--config','game.toml','--project-root','.','--build-dir','build','--target','psx-runtime','--exe-basename',executable.name,'--no-pgo'],cwd=str(folder),progress=progress)
        config=folder/'build/bios.cfg'
        if not config.is_file():
            staged=sorted((folder/'psxrecomp/bios').glob('*.[Bb][Ii][Nn]'))
            if not staged:raise ValueError('La BIOS no quedó preparada junto al juego.')
            config.parent.mkdir(parents=True,exist_ok=True);config.write_text(str(staged[0])+'\n')
    elif kind=='openpete':
        module=executable.parent/'usr/spyro1-recomp.so'
        if not module.is_file():
            progress('Compilando OpenPete desde el disco (menos de un minuto)')
            run([str(executable),'--disc',disc['source'],'--headless'],cwd=str(executable.parent),progress=progress,until=module.is_file)
            if not module.is_file():raise RuntimeError('OpenPete no llegó a compilar su módulo.')
        record['args']=['--disc',disc['source'],'--fullscreen','1']
    elif kind=='ctr':
        source=pathlib.Path(disc['bin'])
        if not source.is_file() or source.stat().st_size%2352:raise ValueError('CTR necesita un BIN crudo MODE2/2352; el archivo '+source.name+' no tiene ese formato.')
        target=home/DATA_CTR/'assets/ctr-u.bin';target.parent.mkdir(parents=True,exist_ok=True)
        if not target.is_file() or target.stat().st_size!=source.stat().st_size:
            progress('Copiando el disco como ctr-u.bin');temporary=target.with_suffix('.part');shutil.copyfile(source,temporary);temporary.replace(target)
    else:raise ValueError('Tipo de configuración desconocido: '+str(kind))
    record['configured']=True;record['configured_with']=disc['name'] if disc else '';record['configured_date']=time.strftime('%Y-%m-%dT%H:%M:%S')
    saved=records(store);saved[repository]=record;atomic_json(store.root/'ports.json',saved);atomic_json(folder/'.deck-library-port.json',record)
    return record
