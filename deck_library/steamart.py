"""Steam artwork slots for non-Steam shortcuts (SteamGridDB), written in the file layout Steam and Decky's SteamGridDB plugin use.

Slots in `userdata/<id>/config/grid/`: `<appid>p` vertical cover, `<appid>` horizontal cover, `<appid>_hero` background,
`<appid>_logo` logo (with `<appid>.json` for its position) and `<appid>_icon`. Existing files are never replaced unless a slot is
chosen explicitly, and every replaced file is backed up first. Writes only happen with Steam closed.
"""
import datetime,json,os,pathlib,shutil,tempfile,urllib.parse
from . import cover_provider

BASE='https://www.steamgriddb.com/api/v2/'
IMAGE_LIMIT=20*1024*1024
EXTENSIONS=('.png','.jpg','.jpeg','.webp')
# slot -> (file suffix, label, API collection, query)
SLOTS={
 'portrait':('p','Portada vertical','grids','dimensions=600x900'),
 'banner':('','Portada horizontal','grids','dimensions=460x215,920x430'),
 'hero':('_hero','Fondo','heroes',''),
 'logo':('_logo','Logotipo','logos',''),
 'icon':('_icon','Icono','icons',''),
}
LOGO_POSITION={'nVersion':1,'logoPosition':{'pinnedPosition':'BottomLeft','nWidthPct':50,'nHeightPct':50}}

def image_type(data):
    """File extension of a PNG, JPEG or WebP payload, or None."""
    if data.startswith(b'\x89PNG\r\n\x1a\n'):return '.png'
    if data.startswith(b'\xff\xd8\xff'):return '.jpg'
    if data[:4]==b'RIFF' and data[8:12]==b'WEBP':return '.webp'
    return None

def existing(account,appid):
    """{slot: Path or None} for the artwork already in the account's grid folder."""
    grid=pathlib.Path(account)/'grid';found={}
    for slot,(suffix,_,_,_) in SLOTS.items():
        names=[str(appid)+suffix+ext for ext in EXTENSIONS]+([str(appid)+suffix+'.ico'] if slot=='icon' else [])
        found[slot]=next((grid/n for n in names if (grid/n).is_file()),None)
    return found

def find_games(key,title,request=cover_provider.request):
    if not key:raise ValueError('SteamGridDB necesita una clave API (Ajustes).')
    rows=json.loads(request(BASE+'search/autocomplete/'+urllib.parse.quote(title,safe=''),key)).get('data',[])
    return [{'id':int(r['id']),'name':str(r.get('name',''))} for r in rows[:6] if 'id' in r]

def candidates(key,game_id,slot,request=cover_provider.request,limit=18):
    """Thumbnail and full-size URLs for one slot, without adult or humor items."""
    _,_,collection,query=SLOTS[slot]
    url=f'{BASE}{collection}/game/{int(game_id)}?types=static&nsfw=false&humor=false'+('&'+query if query else '')
    rows=[]
    for item in json.loads(request(url,key,limit=4*1024*1024)).get('data',[]):
        if item.get('nsfw') or item.get('humor') or not str(item.get('url','')).startswith('https://'):continue
        rows.append({'id':item.get('id'),'url':item['url'],'thumb':item.get('thumb') or item['url'],'width':item.get('width',0),'height':item.get('height',0),'author':(item.get('author') or {}).get('name',''),'page':f'https://www.steamgriddb.com/{collection[:-1]}/{item.get("id")}'})
        if len(rows)>=limit:break
    return rows

def fetch_image(url,request=cover_provider.request):
    data=request(url,limit=IMAGE_LIMIT,timeout=60);ext=image_type(data)
    if not ext:raise ValueError('La imagen descargada no es PNG, JPEG ni WebP.')
    return data,ext

def stage(store,appid,slot,data,ext):
    """Keep a chosen image in the library's private folder until Steam is closed and it can be written."""
    folder=store.root/'art-pending';folder.mkdir(parents=True,exist_ok=True)
    path=folder/f'{int(appid)&0xffffffff}-{slot}{ext}';path.write_bytes(data);return str(path)

def write(account,appid,slot,source,is_running):
    """Copy `source` into the grid folder as the slot's file. Returns True when something changed."""
    from .steam import SteamRunningError
    suffix=SLOTS[slot][0];source=pathlib.Path(source);data=source.read_bytes();ext=image_type(data)
    if not ext:raise ValueError('La imagen no es PNG, JPEG ni WebP.')
    if len(data)>IMAGE_LIMIT:raise ValueError('La imagen es demasiado grande para Steam.')
    grid=pathlib.Path(account)/'grid';grid.mkdir(parents=True,exist_ok=True);appid=str(int(appid)&0xffffffff)
    target=grid/(appid+suffix+ext);previous=[p for p in (grid/(appid+suffix+e) for e in (*EXTENSIONS,'.ico')) if p.is_file()]
    if previous==[target] and target.read_bytes()==data:return False
    if is_running():raise SteamRunningError('Steam se abrió antes de guardar el arte. Guardar de nuevo con Steam cerrado.')
    stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f');backups={}
    for path in previous:
        backup=grid/'.deck-library-backups'/(path.name+'.'+stamp);backup.parent.mkdir(exist_ok=True);shutil.copy2(path,backup);backups[path]=backup
    fd,name=tempfile.mkstemp(prefix='.deck-library-art-',dir=grid)
    try:
        with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
        if is_running():raise SteamRunningError('Steam se abrió durante el guardado del arte.')
        for path in previous:
            if path!=target:path.unlink()
        os.replace(name,target)
        if slot=='logo' and not (grid/(appid+'.json')).exists():(grid/(appid+'.json')).write_text(json.dumps(LOGO_POSITION,separators=(',',':')))
    except Exception:
        for path,backup in backups.items():shutil.copy2(backup,path)
        raise
    finally:
        if os.path.exists(name):os.unlink(name)
    return True
