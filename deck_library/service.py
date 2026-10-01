import datetime,json,os,pathlib,shutil,subprocess,sys,time,fcntl
from contextlib import contextmanager
from .models import Store,Entry,atomic_json
from .runtime import clean_environment,make_launcher
from .steam import update_shortcuts,steam_running

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
    pending=store.root/'pending.json'
    with pending_lock(store):
        if pending.exists():
            previous=json.loads(pending.read_text())
            if previous['account']!=str(account):raise ValueError('Hay accesos pendientes para otra cuenta. Guardalos antes de cambiar de cuenta.')
            ids=list(dict.fromkeys(previous['ids']+[e.id for e in entries]))
        else:ids=[e.id for e in entries]
        atomic_json(pending,{'schema':1,'account':str(account),'ids':ids})
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
    return {'state':'pending','count':len(ids)}

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
        if not wait:return {'state':'pending','count':len(json.loads(pending.read_text())['ids'])}
        if time.monotonic()-start>timeout:return {'state':'pending','count':0}
        time.sleep(2)
    value=json.loads(pending.read_text()); by_id={e.id:e for e in store.load()}
    if any(i not in by_id for i in value['ids']):raise ValueError('La biblioteca cambió. Seleccioná nuevamente los juegos pendientes.')
    entries=[by_id[i] for i in value['ids']]
    for e in entries:
        if e.kind!='steam':make_launcher(e,store)
    result,backup=update_shortcuts(value['account'],entries,lambda e:pathlib.Path(e.command[0]) if e.kind=='steam' else make_launcher(e,store))
    from .steam_inventory import sync_covers
    covers=sync_covers(value['account'],entries,result)
    atomic_json(store.root/'last-sync.json',{'state':'saved','count':len(result),'shortcuts':result,'covers':covers,'backup':backup,'date':datetime.datetime.now().isoformat()})
    # Don't erase a newly queued selection if it changed while writing.
    with pending_lock(store):
        changed=pending.exists() and json.loads(pending.read_text())!=value
        if pending.exists() and not changed:pending.unlink()
    if changed:return _sync(store,wait,timeout)
    return {'state':'saved','count':len(result),'backup':backup}


def restart_steam(store=None):
    """Explicit Desktop UI action. Never restart Steam from one of its games."""
    if os.environ.get('SteamAppId') or os.environ.get('SteamGameId'):
        raise RuntimeError('Cerrá Steam desde Escritorio para guardar los accesos.')
    if not shutil.which('steam'):raise RuntimeError('No se encuentra Steam.')
    env=clean_environment()
    subprocess.run(['steam','-shutdown'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
    try:
        for _ in range(40):
            if not steam_running():break
            time.sleep(1)
        if steam_running():raise RuntimeError('Steam sigue abierto. Cerralo completamente desde Steam → Salir.')
        # The deferred service may hold the lock while finishing the same queue.
        for _ in range(15):
            result=sync(store,wait=False)
            if result['state']!='pending':return result
            time.sleep(1)
        raise RuntimeError('Los accesos siguen pendientes. Volvé a abrir Deck Library.')
    finally:subprocess.Popen(['steam','-silent'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
