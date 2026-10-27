"""Stable self-shortcut definition, independent of each user's installation path."""
import hashlib,json,pathlib,sys
from .models import Entry
APP_ID=hashlib.sha256(b'deck-library-app').hexdigest()[:20]

def entry(app=None):
    app=pathlib.Path(app or pathlib.Path(__file__).resolve().parent.parent/'app.py')
    return Entry('Deck Library',[sys.executable,str(app),'--gaming'],kind='custom',platform='Linux',source=str(app),id=APP_ID,icon=str(app.parent/'assets/icon.png'),metadata={'library_app':True})

ART_FILES={'portrait':'portrait.png','banner':'banner.png','hero':'hero.png','logo':'logo.png','icon':'icon.png'}

def managed_shortcuts(account):
    from . import steam_inventory
    return [r for r in steam_inventory.shortcuts(account) if r['name']=='Deck Library' and pathlib.Path(r['exe'].strip('"')).name==APP_ID+'.sh' and pathlib.Path(r['exe'].strip('"')).parent.name=='launchers']

def refresh_existing_launcher(store=None,home=None,app=None):
    """An existing managed Steam shortcut must launch the installed copy after an upgrade."""
    from .models import Store
    from . import steam,runtime
    store=store or Store();app=pathlib.Path(app or pathlib.Path(__file__).resolve().parent.parent/'app.py')
    if not any(managed_shortcuts(account) for account in steam.find_accounts(home)):return False
    current=store.load();existing=next((item for item in current if item.id==APP_ID),None);wanted=entry(app)
    if existing:
        if existing.icon==str(pathlib.Path(existing.source).parent/'assets/icon.png'):existing.icon=wanted.icon
        existing.command=wanted.command;existing.source=wanted.source;existing.metadata['library_app']=True
    else:current.append(wanted)
    launcher=store.root/'launchers'/(APP_ID+'.sh');before=launcher.read_text() if launcher.is_file() else None
    store.save(current);runtime.make_launcher(existing or wanted,store,app=app)
    if before is not None and before!=launcher.read_text():launcher.with_suffix('.sh.before-upgrade').write_text(before)
    return True

def art_items(account,store,app=None):
    """Fill empty slots and refresh byte-exact previous bundled artwork; preserve custom images."""
    from . import steam,steamart
    app=pathlib.Path(app or pathlib.Path(__file__).resolve().parent.parent/'app.py');me=entry(app)
    rows=managed_shortcuts(account)
    if rows:appid=int(rows[0]['appid'])&0xffffffff
    else:appid=steam.shortcut_id('"'+str(store.root/'launchers'/(me.id+'.sh'))+'"',me.name)
    present=steamart.existing(account,appid);base=app.parent/'assets/steam'
    try:pending=json.loads((store.root/'pending.json').read_text())
    except FileNotFoundError:pending={}
    except (OSError,ValueError):return []
    if not isinstance(pending,dict):return []
    if pending.get('account') and pending['account']!=str(account):return []
    choices=pending.get('art',[])
    if not isinstance(choices,list):return []
    queued={i.get('slot') for i in choices if isinstance(i,dict) and i.get('appid')==appid}
    try:history=json.loads((base/'previous-defaults.json').read_text())
    except (OSError,ValueError):history={}
    history=history.get('slots',{}) if isinstance(history,dict) and history.get('schema')==1 else {}
    if not isinstance(history,dict):history={}
    items=[]
    for slot,name in ART_FILES.items():
        if slot in queued:continue  # A manual choice already waiting for Steam takes precedence.
        target=base/name;current=present.get(slot)
        if not target.is_file():continue
        if current:
            known=history.get(slot,[])
            if not isinstance(known,list):continue
            try:
                if current.stat().st_size>steamart.IMAGE_LIMIT:continue
                digest=hashlib.sha256(current.read_bytes()).hexdigest()
                if digest not in known or digest==hashlib.sha256(target.read_bytes()).hexdigest():continue
            except OSError:continue
        items.append({'appid':appid,'slot':slot,'file':str(target)})
    return items

def refresh_existing_art(store=None,home=None,app=None,start_worker=True):
    """During installation, queue only our existing managed shortcuts, without changing their definitions."""
    from .models import Store
    from . import steam,service
    store=store or Store();count=0
    for account in steam.find_accounts(home):
        if not managed_shortcuts(account):continue
        items=art_items(account,store,app)
        for item in items:
            data=pathlib.Path(item['file']).read_bytes();folder=store.root/'art-pending/library-defaults';folder.mkdir(parents=True,exist_ok=True)
            target=folder/(str(item['appid'])+'-'+item['slot']+'-'+hashlib.sha256(data).hexdigest()+'.png');target.write_bytes(data);item['file']=str(target)
        if items:service.queue_art(items,account,store,start_worker=start_worker,preserve_pending=True);count+=len(items)
    return count
