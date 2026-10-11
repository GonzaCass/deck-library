"""Update an installed Mario Kart WiiCompiled from Deck Library, without opening Quiver.

WiiCompiled ships as a console setup tool (`WiiCompiled-Setup-x86_64.AppImage`); the game is built from the player's own PAL disc
by `install --game <image>`. An update therefore replaces the setup tool by the new release (SHA-256 checked against the digest
GitHub publishes) and runs that install again with the same environment the Quiver adapter uses. The previous tool and version
file are restored if anything fails before the install starts.
"""
import json,os,pathlib,shutil,subprocess,urllib.request
from . import updates

REPOSITORY='patchzyy/Wiicompiled'
ASSET='WiiCompiled-Setup-x86_64.AppImage'
FREE_NEEDED=20_000_000_000

def clean_env():
    env=dict(os.environ)
    for key in ('APPDIR','APPIMAGE','ARGV0','OWD'):env.pop(key,None)
    for key in ('PATH','LD_LIBRARY_PATH'):
        if key in env:env[key]=':'.join(p for p in env[key].split(':') if '/tmp/.mount_' not in p)
    return env

def installations(preferences=None,home=None):
    """WiiCompiled folders managed by Quiver/GithubLauncher: {folder, tool, version, command, data_home}."""
    home=pathlib.Path(home or pathlib.Path.home());found=[]
    for app in updates.quiver_apps(preferences,home):
        if app['repository'].lower()!=REPOSITORY.lower():continue
        folder=pathlib.Path(app['folder']);tools=sorted(folder.glob('WiiCompiled-Setup*.AppImage'))
        if len(tools)!=1:continue
        runner={}
        try:runner=json.loads((folder/'.steamdeck/runner.json').read_text())
        except (OSError,ValueError):pass
        if runner.get('type')=='flatpak':
            app_id=runner['app_id'];data_home=home/'.var/app'/app_id/'data'
            command=['flatpak','run','--filesystem=home','--env=APPIMAGE_EXTRACT_AND_RUN=1','--command='+str(tools[0]),app_id]
        else:
            data_home=pathlib.Path(os.environ.get('XDG_DATA_HOME',str(home/'.local/share')));command=[str(tools[0])]
        # Building needs glibc development files, which a game runtime such as Wheel Wizard's lacks: the install runs in the KDE SDK
        # with the same data folder, as the setup wizard does.
        from .setup_wii import SDK
        build=['flatpak','run','--share=network','--filesystem=home','--env=APPIMAGE_EXTRACT_AND_RUN=1','--env=DISABLE_AUTO_UPDATES=1','--env=XDG_DATA_HOME='+str(data_home),'--command='+str(tools[0]),SDK]
        found.append({'name':app['name'],'folder':folder,'tool':tools[0],'version':app['installed'],'command':command,'build_command':build,'data_home':data_home})
    return found

def latest(get=updates.fetch_json):
    release=updates.latest_release(REPOSITORY,get)
    if not release:return None
    asset=next((a for a in release.get('assets',[]) if a.get('name')==ASSET),None)
    if not asset:return None
    digest=str(asset.get('digest',''))
    return {'tag':release['tag_name'],'url':asset['browser_download_url'],'sha256':digest[7:] if digest.startswith('sha256:') else '','page':release.get('html_url',''),'notes':(release.get('body') or '')[:1500]}

def check(preferences=None,get=updates.fetch_json,home=None):
    """{name, installed, latest, page} for the first installation that is behind, else None."""
    installed=installations(preferences,home)
    if not installed:return None
    info=latest(get)
    if not info:return None
    for item in installed:
        if info['tag']!=item['version'] and updates.is_newer(info['tag'],item['version']):
            return {'name':item['name'],'installed':item['version'],'latest':info['tag'],'page':info['page']}
    return None

def find_image(entries):
    """Path of a clean PAL Mario Kart Wii disc image in the library (RMCP01), or ''."""
    from .setup_wii import check_image
    for entry in entries:
        source=getattr(entry,'source','') or ''
        if 'mario kart wii' in entry.name.lower() and source.lower().endswith(('.iso','.gcm','.gcz','.ciso','.wbfs','.wia','.rvz')):
            try:return str(check_image(source))
            except ValueError:continue
    return ''

def download(info,target,progress,opener=urllib.request.urlopen):
    import hashlib
    if not info['url'].startswith('https://'):raise ValueError('La descarga no usa HTTPS.')
    if not info['sha256']:raise ValueError('La versión publicada no incluye suma SHA-256; no se instala.')
    digest=hashlib.sha256();count=0
    with opener(info['url'],timeout=60) as response,open(target,'wb') as out:
        total=int(response.headers.get('Content-Length',0))
        while True:
            chunk=response.read(1<<20)
            if not chunk:break
            out.write(chunk);digest.update(chunk);count+=len(chunk);progress(f'Descargando el setup: {count//1024**2} MiB'+(f' de {total//1024**2} MiB' if total else ''))
    if digest.hexdigest()!=info['sha256'].lower():raise ValueError('La suma SHA-256 del setup no coincide; no se instaló.')
    with open(target,'rb') as check_file:
        if check_file.read(4)!=b'\x7fELF':raise ValueError('La descarga no es un AppImage.')

def update(item,info,image,progress=lambda text:None,run=None,opener=urllib.request.urlopen,cancel=None):
    """Replace the setup tool and run `install --game IMAGE` again. Returns the installed tag."""
    from .setup_wii import run_logged,check_image
    import threading,tempfile
    image=check_image(image);folder=pathlib.Path(item['folder']);tool=pathlib.Path(item['tool']);cancel=cancel or threading.Event()
    free=shutil.disk_usage(item['data_home'] if pathlib.Path(item['data_home']).exists() else pathlib.Path.home()).free
    if free<FREE_NEEDED:raise RuntimeError(f'La reinstalación necesita unos 20 GB libres; hay {free/1e9:.1f} GB.')
    version_file=folder/'version.txt';old_version=version_file.read_text() if version_file.exists() else None;backup=tool.with_name(tool.name+'.previous')
    temporary=folder/(ASSET+'.download')
    try:
        download(info,temporary,progress,opener);temporary.chmod(0o755)
        if backup.exists():backup.unlink()
        tool.rename(backup);new_tool=folder/ASSET;temporary.replace(new_tool)
    except Exception:
        if temporary.exists():temporary.unlink()
        raise
    version_file.write_text(info['tag'])
    command=[a.replace(str(tool),str(new_tool)) for a in item.get('build_command') or item['command']]
    log_path=pathlib.Path(item['data_home'])/'WiiCompiled/deck-library-update.log';log_path.parent.mkdir(parents=True,exist_ok=True)
    try:
        with log_path.open('w') as log:
            (run or run_logged)([*command,'install','--game',image],str(folder),clean_env(),log,progress,cancel)
    except BaseException:
        # The new tool could not finish: put the previous one back so Quiver and the launcher keep working with what was installed.
        if new_tool.exists():new_tool.unlink()
        backup.rename(tool)
        if old_version is not None:version_file.write_text(old_version)
        raise
    if backup.exists():backup.unlink()
    return info['tag']
