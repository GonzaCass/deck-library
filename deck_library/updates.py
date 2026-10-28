"""Update checks for Deck Library, its preset catalog and installed ports; verified self-update.

Every request is HTTPS with a size cap. Nothing is installed without a matching SHA-256 published
next to the release asset. Ports found in Quiver's folder are reported and, for WiiCompiled and for ports with a GitHub release, updated from Deck Library itself.
"""
import hashlib,json,os,pathlib,re,subprocess,sys,tarfile,tempfile,time,urllib.error,urllib.request,urllib.parse
from . import __version__
from .models import Store,atomic_json

REPO='GonzaCass/deck-library'
CATALOG_URL='https://raw.githubusercontent.com/GonzaCass/deck-library/main/presets/catalog.json'
PROJECT2099_REPO='GenryTheFox0/Project-2099'
HANDLED_HERE='patchzyy/wiicompiled'  # updated by wiiupdate.py, so Quiver's report is not repeated
INTERVAL=6*3600
APP_INTERVAL=3600
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
        if error.code==404:return None
        raise

def web_release():
    """Public GitHub redirect, independent of the anonymous API quota."""
    request=urllib.request.Request('https://github.com/'+REPO+'/releases/latest',headers={'User-Agent':'DeckLibrary/'+__version__})
    with urllib.request.urlopen(request,timeout=10) as response:url=response.url
    parsed=urllib.parse.urlparse(url)
    match=re.fullmatch('/'+re.escape(REPO)+r'/releases/tag/(v?\d+(?:\.\d+)+)',parsed.path)
    if parsed.scheme!='https' or parsed.hostname!='github.com' or not match:raise ValueError('No se pudo identificar la última versión publicada en GitHub.')
    tag=match[1];name='DeckLibrary-'+tag.lstrip('v')+'.tar.gz';base='https://github.com/'+REPO+'/releases/download/'+tag+'/'
    return {'tag_name':tag,'html_url':url,'assets':[{'name':name,'browser_download_url':base+name},{'name':name+'.sha256','browser_download_url':base+name+'.sha256'}]}

def check_app(current=__version__,get=fetch_json,fallback=None):
    fallback=fallback or (web_release if get is fetch_json else None)
    try:release=latest_release(REPO,get)
    except (OSError,ValueError):
        if not fallback:raise
        release=fallback()
    if not release and fallback:release=fallback()
    if not release or not is_newer(release.get('tag_name'),current):return None
    assets={a['name']:a['browser_download_url'] for a in release.get('assets',[]) if isinstance(a,dict) and 'name' in a and 'browser_download_url' in a}
    archive=next((n for n in assets if re.fullmatch(r'DeckLibrary-[\d.]+\.tar\.gz',n)),None)
    return {'version':release['tag_name'].lstrip('v'),'page':release.get('html_url',''),'notes':(release.get('body') or '')[:1500],'archive':assets.get(archive),'checksum':assets.get(archive+'.sha256') if archive else None,'name':archive}

def quiver_apps(preferences=None,home=None):
    """Ports installed through Quiver or GithubLauncher as {name, repository, installed, folder}."""
    from .installations import launcher_roots,apps_folder
    found=[]
    for root in launcher_roots(home,preferences):
        try:apps=json.loads((root/'apps.json').read_text(encoding='utf-8-sig')).get('apps',[])
        except (OSError,ValueError):continue
        for app in apps:
            folder=apps_folder(root)/str(app.get('folderName',''))
            if not app.get('repository') or not folder.is_dir():continue
            try:installed=(folder/'version.txt').read_text().strip()
            except OSError:continue
            found.append({'name':app.get('name',app['repository']),'repository':app['repository'],'installed':installed,'skipped':app.get('skippedUpdateVersion') or '','folder':str(folder)})
    return found

def check_quiver(preferences=None,get=fetch_json,home=None):
    updates=[]
    for app in quiver_apps(preferences,home):
        if app['repository'].lower()==HANDLED_HERE:continue
        try:release=latest_release(app['repository'],get)
        except (OSError,ValueError):break
        if release and release.get('tag_name') not in (app['installed'],app['skipped']) and is_newer(release['tag_name'],app['installed']):
            updates.append({'name':app['name'],'installed':app['installed'],'latest':release['tag_name'],'page':release.get('html_url',''),'repository':app['repository'],'notes':(release.get('body') or '')[:8000]})
    return updates

def check_project2099(entries,get=fetch_json):
    from .project2099 import VERSION
    if not any(e.metadata.get('adapter')=='project2099' for e in entries):return None
    current=next((e.metadata.get('build') for e in entries if e.metadata.get('adapter')=='project2099' and e.metadata.get('build') not in (None,'unknown')),VERSION)
    release=latest_release(PROJECT2099_REPO,get)
    if release and release.get('tag_name','').lstrip('v')!=current and is_newer(release['tag_name'],current):
        return {'name':'Project-2099','installed':current,'latest':release['tag_name'].lstrip('v'),'page':release.get('html_url',''),'repository':PROJECT2099_REPO,'notes':(release.get('body') or '')[:8000]}
    return None

def refresh_presets(preferences,store):
    from . import presets
    before={p['id']:p for p in presets.catalog(store)}
    count=presets.refresh_catalog(preferences.get('catalog_url') or CATALOG_URL,store)
    after={p['id']:p for p in presets.catalog(store)}
    return {'count':count,'new':len([i for i in after if i not in before]),'changed':len([i for i in after if i in before and after[i]!=before[i]])}

def cache_path(store):return store.root/'updates.json'

def cached(store):
    try:state=json.loads(cache_path(store).read_text())
    except (OSError,ValueError):return {}
    if not isinstance(state,dict):return {}
    # The search is cached for hours: once the app itself is at or beyond the cached release, the offer is stale.
    if state.get('app') and not is_newer(state['app'].get('version'),__version__):state['app']=None
    clean=reconcile_ports(state,store)
    if clean!=state:atomic_json(cache_path(store),clean)
    return clean

def reconcile_ports(state,store):
    """Discard stale offers against the installed receipt, including checks started before an install finished."""
    from .ports import records
    installed={repo.lower():record for repo,record in records(store).items()}
    state={**state}
    for key in ('catalog','ports'):
        state[key]=[row for row in state.get(key) or [] if not (
            installed.get(str(row.get('repository','')).lower(),{}).get('tag') and
            not is_newer(row.get('latest'),installed[str(row['repository']).lower()]['tag']))]
    return state

def port_completed(store,repository,tag):
    state=cached(store)
    for key in ('catalog','ports'):
        state[key]=[row for row in state.get(key) or [] if row.get('repository','').lower()!=repository.lower() or is_newer(row.get('latest'),tag)]
    atomic_json(cache_path(store),state)
    return state

def check_all(store,preferences,entries,force=False,get=fetch_json,on_app=None):
    """Run the checks that are due. Failures of one source never hide the others."""
    state=cached(store)
    now=time.time();ports_due=force or now-state.get('checked',0)>=INTERVAL
    app_due=force or state.get('app_checked_version')!=__version__ or now-state.get('app_checked',0)>=(60 if state.get('app_error') else APP_INTERVAL)
    if not app_due and not ports_due:return state
    state={**state,'errors':list(state.get('errors') or [])}
    if app_due:
        state['errors']=[error for error in state['errors'] if not error.startswith('app:')]
        try:state['app']=check_app(get=get);state.pop('app_error',None)
        except (OSError,ValueError,KeyError) as error:state['app_error']=str(error);state['errors'].append('app: '+str(error))
        state.update(app_checked=now,app_checked_version=__version__);atomic_json(cache_path(store),state)
    if on_app:on_app({**state,'errors':list(state['errors'])})
    if not ports_due:return state
    state.update(checked=now,errors=[error for error in state['errors'] if error.startswith('app:')])
    from . import ports
    for key,run in (('ports',lambda:check_quiver(preferences,get)),('catalog',lambda:ports.installed_updates(store,get)),('project2099',lambda:check_project2099(entries,get)),('wiicompiled',lambda:__import__('deck_library.wiiupdate',fromlist=['check']).check(preferences,get))):
        try:state[key]=run()
        except (OSError,ValueError,KeyError) as error:state['errors'].append(f'{key}: {error}')
    if preferences.get('catalog_auto',True):
        try:state['presets']=refresh_presets(preferences,store)
        except (OSError,ValueError,KeyError) as error:state['errors'].append(f'presets: {error}')
    state=reconcile_ports(state,store);atomic_json(cache_path(store),state);return state

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

def preload():
    import importlib,pkgutil
    package=importlib.import_module(__package__)
    for module in pkgutil.iter_modules(package.__path__):
        try:importlib.import_module(f'{__package__}.{module.name}')
        except Exception:pass

def install_update(info,store=None,progress=print,runner=subprocess.run):
    """Download, verify and install a release. Returns the installed version."""
    if not info.get('archive') or not info.get('checksum'):raise ValueError('La versión publicada no incluye paquete verificable (.tar.gz y .sha256).')
    # The running process keeps using the files it loaded; load the rest now so replacing them cannot mix two versions.
    preload()
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
        from .runtime import clean_environment
        result=runner([sys.executable,'-I',str(installer)],cwd=str(installer.parent),capture_output=True,text=True,timeout=120,env=clean_environment())
        if result.returncode:raise RuntimeError('El instalador terminó con error:\n'+(result.stderr or result.stdout)[-1500:])
    return info['version']

def summary(state):
    """One-line items for the interface."""
    items=[]
    if state.get('app'):items.append(('app',f'Deck Library {state["app"]["version"]} disponible',state['app']))
    for port in state.get('ports') or []:items.append(('port',f'{port["name"]}: {port["installed"]} → {port["latest"]}',port))
    for port in state.get('catalog') or []:items.append(('catalog',f'{port["name"]}: {port["installed"]} → {port["latest"]}',port))
    if state.get('wiicompiled'):w=state['wiicompiled'];items.append(('wii',f'{w["name"]}: {w["installed"]} → {w["latest"]}',w))
    if state.get('project2099'):p=state['project2099'];items.append(('port',f'{p["name"]}: {p["installed"]} → {p["latest"]}',p))
    return items


def release_notes(data,get=fetch_json):
    """Notes for the displayed release, never unrelated commits or an unverified newer tag."""
    if 'notes' in data:return data['notes']
    repository=data.get('repository','');tag=str(data.get('latest',''))
    if not repository:
        page=urllib.parse.urlsplit(data.get('page',''));parts=page.path.strip('/').split('/')
        if page.scheme=='https' and page.netloc=='github.com' and len(parts)>=2:repository='/'.join(parts[:2])
        elif data.get('name')=='Project-2099':repository=PROJECT2099_REPO
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository) or not tag:return ''
    release=None
    for candidate in dict.fromkeys([tag,tag[1:] if tag.startswith('v') else 'v'+tag]):
        try:release=get('https://api.github.com/repos/'+repository+'/releases/tags/'+urllib.parse.quote(candidate,safe=''));break
        except urllib.error.HTTPError as error:
            if error.code!=404:raise
    if release is None:release=latest_release(repository,get)
    if not release or release.get('tag_name','').lstrip('v')!=tag.lstrip('v'):return ''
    return (release.get('body') or '')[:8000]

def notes_text(body):
    """Readable release Markdown without loading images or rendering active HTML."""
    from html.parser import HTMLParser
    text=re.sub(r'<!--.*?-->','',str(body),flags=re.S)
    text=re.sub(r'!\[([^\]]*)\]\([^)]*\)','',text)
    text=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',text)
    text=re.sub(r'(?m)^\s*#{1,6}\s*','',text)
    text=re.sub(r'(?m)^\s*[-*]\s+', '• ',text).replace('**','').replace('`','')
    class Plain(HTMLParser):
        def __init__(self):super().__init__();self.parts=[]
        def handle_data(self,data):self.parts.append(data)
        def handle_starttag(self,tag,attrs):
            if tag in ('br','p','div','summary','details','li'):self.parts.append('\n')
        def handle_endtag(self,tag):
            if tag in ('p','div','summary','details','li'):self.parts.append('\n')
    parser=Plain();parser.feed(text)
    return re.sub(r'\n{3,}','\n\n',''.join(parser.parts)).strip()
