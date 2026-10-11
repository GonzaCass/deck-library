"""Update checks for Deck Library, its preset catalog and installed ports; verified self-update.

Every request is HTTPS with a size cap. Nothing is installed without a matching SHA-256 published
next to the release asset. Ports installed by Quiver are only reported: Quiver owns their files.
"""
import hashlib,json,os,pathlib,re,subprocess,sys,tarfile,tempfile,time,urllib.error,urllib.request
from . import __version__
from .models import Store,atomic_json

REPO='GonzaCass/deck-library'
CATALOG_URL='https://raw.githubusercontent.com/GonzaCass/deck-library/main/presets/catalog.json'
PROJECT2099_REPO='GenryTheFox0/Project-2099'
INTERVAL=6*3600
JSON_LIMIT=2*1024*1024
DOWNLOAD_LIMIT=64*1024*1024

class RateLimited(OSError):
    """GitHub refused the request because the hourly quota is used up."""

def fetch(url,limit=JSON_LIMIT,timeout=10):
    if not url.startswith('https://'):raise ValueError('Solo se admiten direcciones HTTPS.')
    headers={'User-Agent':'DeckLibrary/'+__version__,'Accept':'application/vnd.github+json'}
    token=os.environ.get('GITHUB_TOKEN','')
    if token and url.startswith('https://api.github.com/'):headers['Authorization']='Bearer '+token
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout) as response:
            if not response.url.startswith('https://'):raise ValueError('La redirección no usa HTTPS.')
            data=response.read(limit+1)
    except urllib.error.HTTPError as error:
        if error.code==429 or (error.code==403 and error.headers.get('X-RateLimit-Remaining')=='0'):
            raise RateLimited('GitHub limitó las consultas por hora. Reintentar en unos minutos o definir la variable GITHUB_TOKEN.') from None
        raise
    if len(data)>limit:raise ValueError('La respuesta supera el límite de tamaño.')
    return data

def fetch_json(url):return json.loads(fetch(url))

def version_key(text):
    """Numeric parts of a tag; a pre-release suffix such as `-beta.4` sorts after its numbers but is kept."""
    return tuple(int(n) for n in re.findall(r'\d+',str(text or '')))

def is_newer(latest,current):
    a,b=version_key(latest),version_key(current)
    return bool(a) and (a>b if b else True)

def latest_release(repo,get=fetch_json):
    try:return get(f'https://api.github.com/repos/{repo}/releases/latest')
    except urllib.error.HTTPError as error:
        if error.code in (403,404):return None
        raise

def check_app(current=__version__,get=fetch_json):
    release=latest_release(REPO,get)
    if not release or not is_newer(release.get('tag_name'),current):return None
    assets={a['name']:a['browser_download_url'] for a in release.get('assets',[]) if isinstance(a,dict) and 'name' in a and 'browser_download_url' in a}
    archive=next((n for n in assets if re.fullmatch(r'DeckLibrary-[\d.]+\.tar\.gz',n)),None)
    return {'version':release['tag_name'].lstrip('v'),'page':release.get('html_url',''),'notes':(release.get('body') or '')[:1500],'archive':assets.get(archive),'checksum':assets.get(archive+'.sha256') if archive else None,'name':archive}

def quiver_apps(preferences=None,home=None):
    """Installed Quiver ports as {name, repository, installed, folder}."""
    home=pathlib.Path(home or pathlib.Path.home());roots=[home/'ports/quiver-launcher',*map(pathlib.Path,(preferences or {}).get('quiver_roots',[]))];found=[]
    for root in dict.fromkeys(roots):
        try:apps=json.loads((root/'apps.json').read_text()).get('apps',[])
        except (OSError,ValueError):continue
        for app in apps:
            folder=root/'Apps'/str(app.get('folderName',''))
            if not app.get('repository') or not folder.is_dir():continue
            try:installed=(folder/'version.txt').read_text().strip()
            except OSError:continue
            found.append({'name':app.get('name',app['repository']),'repository':app['repository'],'installed':installed,'skipped':app.get('skippedUpdateVersion') or '','folder':str(folder)})
    return found

def check_quiver(preferences=None,get=fetch_json,home=None):
    updates=[]
    for app in quiver_apps(preferences,home):
        try:release=latest_release(app['repository'],get)
        except (OSError,ValueError):break
        if release and release.get('tag_name') not in (app['installed'],app['skipped']) and is_newer(release['tag_name'],app['installed']):
            updates.append({'name':app['name'],'installed':app['installed'],'latest':release['tag_name'],'page':release.get('html_url','')})
    return updates

def check_project2099(entries,get=fetch_json):
    from .project2099 import VERSION
    if not any(e.metadata.get('adapter')=='project2099' for e in entries):return None
    release=latest_release(PROJECT2099_REPO,get)
    if release and release.get('tag_name','').lstrip('v')!=VERSION and is_newer(release['tag_name'],VERSION):
        return {'name':'Project-2099','installed':VERSION,'latest':release['tag_name'].lstrip('v'),'page':release.get('html_url','')}
    return None

def refresh_presets(preferences,store):
    from . import presets
    before={p['id']:p for p in presets.catalog(store)}
    count=presets.refresh_catalog(preferences.get('catalog_url') or CATALOG_URL,store)
    after={p['id']:p for p in presets.catalog(store)}
    return {'count':count,'new':len([i for i in after if i not in before]),'changed':len([i for i in after if i in before and after[i]!=before[i]])}

def cache_path(store):return store.root/'updates.json'

def cached(store):
    try:return json.loads(cache_path(store).read_text())
    except (OSError,ValueError):return {}

def check_all(store,preferences,entries,force=False,get=fetch_json):
    """Run the checks that are due. Failures of one source never hide the others."""
    state=cached(store)
    if not force and time.time()-state.get('checked',0)<INTERVAL:return state
    state={**state,'checked':time.time(),'errors':[]}
    from . import ports
    for key,run in (('app',lambda:check_app(get=get)),('ports',lambda:check_quiver(preferences,get)),('catalog',lambda:ports.installed_updates(store,get)),('project2099',lambda:check_project2099(entries,get))):
        try:state[key]=run()
        except (OSError,ValueError,KeyError) as error:state['errors'].append(f'{key}: {error}')
    if preferences.get('catalog_auto',True):
        try:state['presets']=refresh_presets(preferences,store)
        except (OSError,ValueError,KeyError) as error:state['errors'].append(f'presets: {error}')
    atomic_json(cache_path(store),state);return state

def sha256_file(path):
    digest=hashlib.sha256()
    with open(path,'rb') as source:
        for block in iter(lambda:source.read(1<<20),b''):digest.update(block)
    return digest.hexdigest()

def safe_extract(archive,destination):
    destination=pathlib.Path(destination).resolve()
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            target=(destination/member.name).resolve()
            if not member.isfile() and not member.isdir():raise ValueError('El paquete contiene enlaces o archivos especiales.')
            if not target.is_relative_to(destination):raise ValueError('El paquete contiene rutas inseguras.')
        tar.extractall(destination,filter='data')

def install_update(info,store=None,progress=print,runner=subprocess.run):
    """Download, verify and install a release. Returns the installed version."""
    if not info.get('archive') or not info.get('checksum'):raise ValueError('La versión publicada no incluye paquete verificable (.tar.gz y .sha256).')
    store=store or Store();work=store.root/'downloads/update';work.mkdir(parents=True,exist_ok=True)
    expected=fetch(info['checksum'],limit=4096).decode().split()[0].lower()
    if not re.fullmatch(r'[0-9a-f]{64}',expected):raise ValueError('Suma SHA-256 publicada inválida.')
    with tempfile.TemporaryDirectory(prefix='update-',dir=work) as temp:
        temp=pathlib.Path(temp);archive=temp/info['name'];progress('Descargando '+info['name'])
        archive.write_bytes(fetch(info['archive'],limit=DOWNLOAD_LIMIT,timeout=60))
        if sha256_file(archive)!=expected:raise ValueError('La suma SHA-256 del paquete no coincide; no se instaló.')
        progress('Verificado. Instalando');safe_extract(archive,temp/'src')
        installer=next((temp/'src').glob('*/install.py'),None)
        if installer is None:raise ValueError('El paquete no contiene instalador.')
        result=runner([sys.executable,'-I',str(installer)],cwd=str(installer.parent),capture_output=True,text=True,timeout=120)
        if result.returncode:raise RuntimeError('El instalador terminó con error:\n'+(result.stderr or result.stdout)[-1500:])
    return info['version']

def summary(state):
    """One-line items for the interface."""
    items=[]
    if state.get('app'):items.append(('app',f'Deck Library {state["app"]["version"]} disponible',state['app']))
    for port in state.get('ports') or []:items.append(('port',f'{port["name"]}: {port["installed"]} → {port["latest"]}',port))
    for port in state.get('catalog') or []:items.append(('catalog',f'{port["name"]}: {port["installed"]} → {port["latest"]}',port))
    if state.get('project2099'):p=state['project2099'];items.append(('port',f'{p["name"]}: {p["installed"]} → {p["latest"]}',p))
    return items
