"""Stable self-shortcut definition, independent of each user's installation path."""
import hashlib,pathlib,sys
from .models import Entry
APP_ID=hashlib.sha256(b'deck-library-app').hexdigest()[:20]

def entry(app=None):
    app=pathlib.Path(app or pathlib.Path(__file__).resolve().parent.parent/'app.py')
    return Entry('Deck Library',[sys.executable,str(app),'--gaming'],kind='custom',platform='Linux',source=str(app),id=APP_ID,icon=str(app.parent/'assets/icon.png'),metadata={'library_app':True})

ART_FILES={'portrait':'portrait.png','banner':'banner.png','hero':'hero.png','logo':'logo.png','icon':'icon.png'}

def art_items(account,store,app=None):
    """Steam artwork Deck Library ships for its own shortcut, only for the slots that are still empty (an image chosen by the user is never replaced)."""
    from . import steam,steam_inventory,steamart
    app=pathlib.Path(app or pathlib.Path(__file__).resolve().parent.parent/'app.py');me=entry(app)
    rows=[r for r in steam_inventory.shortcuts(account) if r['name']==me.name and 'launchers' in r['exe']]
    if rows:appid=int(rows[0]['appid'])&0xffffffff
    else:appid=steam.shortcut_id('"'+str(store.root/'launchers'/(me.id+'.sh'))+'"',me.name)
    present=steamart.existing(account,appid);base=app.parent/'assets/steam'
    return [{'appid':appid,'slot':slot,'file':str(base/name)} for slot,name in ART_FILES.items() if not present.get(slot) and (base/name).is_file()]
