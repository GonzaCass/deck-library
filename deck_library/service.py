import datetime,json,os,pathlib,shutil,subprocess,sys,time,fcntl
from contextlib import contextmanager
from .models import Store,Entry,atomic_json
from .runtime import clean_environment,make_launcher
from .steam import update_shortcuts,remove_shortcuts,move_artwork_aside,steam_running

@contextmanager
def pending_lock(store):
    store.root.mkdir(parents=True,exist_ok=True)
    with (store.root/"pending.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        yield

def queue_entries(entries,account,store=None,start_worker=True):
    entries=[e for e in entries if not e.metadata.get('steam_store')]
    if not entries:return {'state':'idle','count':0}
    store=store or Store(); store.merge(entries)
    return _queue(account,store,[e.id for e in entries],[],start_worker)

def queue_removals(appids,account,store=None,start_worker=True):
    """Queue shortcut removals by app ID; they run once Steam is closed."""
    appids=list(dict.fromkeys(int(a)&0xffffffff for a in appids))
    if not appids:return {'state':'idle','count':0}
    return _queue(account,store or Store(),[],appids,start_worker)

def queue_controllers(appids,account,store=None,start_worker=True):
    """Queue an explicit gamepad-layout assignment (replaces the saved layout of those shortcuts)."""
    appids=list(dict.fromkeys(int(a)&0xffffffff for a in appids))
    if not appids:return {'state':'idle','count':0}
    return _queue(account,store or Store(),[],[],start_worker,appids)

def _queue(account,store,ids,remove,start_worker,fix=()):
    pending=store.root/'pending.json'
    with pending_lock(store):
        if pending.exists():
            previous=json.loads(pending.read_text())
            if previous['account']!=str(account):raise ValueError('Hay cambios pendientes para otra cuenta. Guardarlos antes de cambiar de cuenta.')
            ids=list(dict.fromkeys(previous['ids']+ids));remove=list(dict.fromkeys(previous.get('remove',[])+remove));fix=list(dict.fromkeys(previous.get('controllers',[])+list(fix)))
        # A shortcut queued for removal must not also be written, and vice versa.
        if remove:ids=[i for i in ids if i not in {e.id for e in store.load() if e.metadata.get('steam_appid') in remove}]
        value={'schema':1,'account':str(account),'ids':ids}
        if remove:value['remove']=remove
        if fix:value['controllers']=fix
        atomic_json(pending,value)
    if not steam_running():return sync(store,wait=False)
    if start_worker:
        app=pathlib.Path(__file__).resolve().parent.parent/'app.py'
        args=[sys.executable,str(app),'sync','--data-dir',str(store.root)]
        log=store.root/'worker.log'
        with log.open('a') as output:
            # Detach a user service from Steam's process tracking where available.
            launcher=shutil.which('systemd-run')
            started=False
            if launcher:
                result=subprocess.run([launcher,'--user','--collect','--unit=deck-library-sync','--quiet','--',*args],env=clean_environment(),stdout=output,stderr=subprocess.STDOUT)
                started=result.returncode==0
            if not started and not os.environ.get('SteamAppId'):
                subprocess.Popen(args,env=clean_environment(),stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
    return {'state':'pending','count':len(ids)+len(remove)+len(fix)}

def sync(store=None,wait=True,timeout=86400):
    store=store or Store();store.root.mkdir(parents=True,exist_ok=True)
    with (store.root/'sync.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {'state':'pending','count':0}
        return _sync(store,wait,timeout)

def _sync(store=None,wait=True,timeout=86400):
    store=store or Store(); pending=store.root/'pending.json'
    if not pending.exists():return {'state':'idle','count':0}
    start=time.monotonic()
    while steam_running():
        if not wait:
            queued=json.loads(pending.read_text());return {'state':'pending','count':len(queued['ids'])+len(queued.get('remove',[]))+len(queued.get('controllers',[]))}
        if time.monotonic()-start>timeout:return {'state':'pending','count':0}
        time.sleep(2)
    value=json.loads(pending.read_text()); by_id={e.id:e for e in store.load()}
    if any(i not in by_id for i in value['ids']):raise ValueError('La biblioteca cambió. Seleccionar nuevamente los juegos pendientes.')
    entries=[by_id[i] for i in value['ids']];remove=value.get('remove',[]);result=[];backup=None;covers=0;removed=[]
    if entries:
        for e in entries:
            if e.kind!='steam':make_launcher(e,store)
        result,backup=update_shortcuts(value['account'],entries,lambda e:pathlib.Path(e.command[0]) if e.kind=='steam' else make_launcher(e,store))
        from .steam_inventory import sync_covers
        covers=sync_covers(value['account'],entries,result)
        _controllers(value['account'],[r['appid'] for r in result if 'appid' in r],store,[r['appid'] for r in result if 'appid' in r and by_id.get(r.get('id')) is not None and by_id[r['id']].platform in DUAL_SCREEN])
    if remove:
        removed,removal_backup=remove_shortcuts(value['account'],remove);backup=backup or removal_backup
        move_artwork_aside(value['account'],remove)
        try:
            from . import controllers
            controllers.forget(value['account'],remove)
        except Exception as error:_log(store,'controles: '+str(error))
    fix=[a for a in value.get('controllers',[]) if a not in remove]
    if fix:
        from . import controllers
        controllers.apply(value['account'],fix,force=True,special=dual_screen_appids(store.load()))
    count=len(result)+len(removed)+len(fix)
    atomic_json(store.root/'last-sync.json',{'state':'saved','count':count,'shortcuts':result,'removed':removed,'layouts':fix,'covers':covers,'backup':backup,'date':datetime.datetime.now().isoformat()})
    # Don't erase a newly queued selection if it changed while writing.
    with pending_lock(store):
        changed=pending.exists() and json.loads(pending.read_text())!=value
        if pending.exists() and not changed:pending.unlink()
    if changed:return _sync(store,wait,timeout)
    return {'state':'saved','count':count,'added':len(result),'removed':len(removed),'layouts':len(fix),'backup':backup}


def restart_steam(store=None):
    """Explicit Desktop UI action. Never restart Steam from one of its games."""
    if os.environ.get('SteamAppId') or os.environ.get('SteamGameId'):
        raise RuntimeError('Cerrar Steam desde el modo Escritorio para guardar los cambios.')
    if not shutil.which('steam'):raise RuntimeError('No se encuentra Steam.')
    env=clean_environment()
    subprocess.run(['steam','-shutdown'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
    try:
        for _ in range(40):
            if not steam_running():break
            time.sleep(1)
        if steam_running():raise RuntimeError('Steam sigue abierto. Cerrarlo completamente desde Steam → Salir.')
        # The deferred service may hold the lock while finishing the same queue.
        for _ in range(15):
            result=sync(store,wait=False)
            if result['state']!='pending':return result
            time.sleep(1)
        raise RuntimeError('Los accesos siguen pendientes. Abrir Deck Library de nuevo.')
    finally:subprocess.Popen(['steam','-silent'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)


def _log(store,text):
    with (store.root/'worker.log').open('a') as out:out.write(datetime.datetime.now().isoformat()+' '+text+'\n')

DUAL_SCREEN={'Nintendo 3DS'}

def dual_screen_appids(entries):
    """App IDs of shortcuts whose game needs the screen-swap layout."""
    return [e.metadata['steam_appid'] for e in entries if e.platform in DUAL_SCREEN and e.metadata.get('steam_appid')]

def _controllers(account,appids,store,special=()):
    """Give new shortcuts a gamepad layout for every controller family; never overwrite existing choices."""
    from .installations import settings
    if not settings(store).get('fix_controllers',True):return
    try:
        from . import controllers
        controllers.apply(account,appids,special=special)
    except Exception as error:_log(store,'controles: '+str(error))
