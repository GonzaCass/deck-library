"""Network artwork providers. Downloads stay in the private local cache."""
import json,pathlib,re,urllib.parse,urllib.request,functools,html
from .artwork import normalized
from .models import atomic_json

MAX_IMAGE=12*1024*1024
ALIASES={'0100152000022000':'Mario Kart 8 Deluxe','01006A800016E000':'Super Smash Bros. Ultimate','0100000000010000':'Super Mario Odyssey','010036B0034E4000':'Super Mario Party','01006FE013472000':'Mario Party Superstars','0100965017338000':'Super Mario Party Jamboree','RMCP01':'Mario Kart Wii'}

def title_for(entry):
    if entry.platform=='Minecraft':return 'Minecraft'
    return ALIASES.get(entry.game_id.upper(),re.sub(r'\([^)]*\)|\[[^]]*\]|(?:\s+v?\d+\.\d+.*)$','',entry.name).strip())

def request(url,key='',limit=1024*1024,timeout=15):
    if urllib.parse.urlparse(url).scheme!='https':raise ValueError('El proveedor debe usar HTTPS.')
    headers={'User-Agent':'DeckLibrary/0.3 (local game library; artwork lookup)'}
    if key:headers['Authorization']='Bearer '+key
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout) as response:
        data=response.read(limit+1)
        if len(data)>limit:raise ValueError('Respuesta del proveedor demasiado grande.')
        return data

def wiki_search(query):
    # Exact title first; search is only used if the exact article has no image.
    base='https://en.wikipedia.org/w/api.php?'
    common={'action':'query','format':'json','prop':'pageimages','piprop':'thumbnail','pithumbsize':600,'pilicense':'any','redirects':1}
    def fetch(params):
        result=json.loads(request(base+urllib.parse.urlencode({**common,**params})))
        rows=[]
        for page in result.get('query',{}).get('pages',{}).values():
            image=page.get('thumbnail',{})
            if image.get('source'):
                rows.append({'title':page['title'],'url':image['source'],'provider':'Wikipedia','page':'https://en.wikipedia.org/wiki/'+urllib.parse.quote(page['title'].replace(' ','_')),'width':image.get('width',0),'height':image.get('height',0)})
        return rows
    exact=fetch({'titles':query})
    if exact:return exact
    return fetch({'generator':'search','gsrsearch':query+' video game','gsrlimit':6,'gsrnamespace':0})

def sgdb_search(query,key):
    if not key:raise ValueError('SteamGridDB necesita una clave API. Wikipedia funciona sin clave.')
    base='https://www.steamgriddb.com/api/v2/'
    games=json.loads(request(base+'search/autocomplete/'+urllib.parse.quote(query,safe=''),key)).get('data',[])
    rows=[]
    for game in games[:3]:
        grids=json.loads(request(base+'grids/game/'+str(int(game['id']))+'?dimensions=600x900&types=static&limit=6',key)).get('data',[])
        for grid in grids[:6]:
            if grid.get('nsfw') or grid.get('humor'):continue
            if grid.get('url'):rows.append({'title':game['name'],'url':grid['url'],'provider':'SteamGridDB','page':'https://www.steamgriddb.com/grid/'+str(grid['id']),'width':grid.get('width',600),'height':grid.get('height',900)})
    return rows

SYSTEMS={'Wii':'Nintendo - Wii','WiiCompiled':'Nintendo - Wii','GameCube':'Nintendo - GameCube','PlayStation':'Sony - PlayStation','PlayStation 2':'Sony - PlayStation 2','PSP':'Sony - PlayStation Portable','Nintendo 3DS':'Nintendo - Nintendo 3DS','Wii U':'Nintendo - Wii U','Nintendo 64':'Nintendo - Nintendo 64','Game Boy Advance':'Nintendo - Game Boy Advance','Super Nintendo':'Nintendo - Super Nintendo Entertainment System','Xbox 360':'Microsoft - Xbox 360','Xbox':'Microsoft - Xbox'}
@functools.lru_cache(maxsize=12)
def libretro_index(system):
    url='https://thumbnails.libretro.com/'+urllib.parse.quote(system,safe='')+'/Named_Boxarts/'
    data=request(url,limit=16*1024*1024,timeout=40).decode('utf-8')
    rows=[]
    for href in re.findall(r'href="([^"]+)"',data):
        filename=urllib.parse.unquote(html.unescape(href))
        if '/' in filename or not filename.lower().endswith('.png'):continue
        rows.append({'title':filename[:-4],'url':url+urllib.parse.quote(filename,safe=''),'provider':'Libretro','page':url})
    return rows

def libretro_search(query,platform,fuzzy=False):
    system=SYSTEMS.get(platform)
    if not system:return []
    wanted=normalized(query)
    # Fuzzy lookups (manual search) accept titles that contain the query; automatic ones stay exact.
    rows=[row for row in libretro_index(system) if normalized(row['title'])==wanted or (fuzzy and len(wanted)>=4 and wanted in normalized(row['title']))]
    rows.sort(key=lambda row:('Europe' not in row['title'],len(row['title'])))
    return rows[:12]

def search(query,preferences,merge=False):
    """One provider chain for automatic use; `merge` collects every source for the manual dialog."""
    provider=preferences.get('artwork_provider','automatic')
    if provider=='off':return []
    key=preferences.get('steamgriddb_key','')
    if merge and provider=='automatic':
        rows=[];errors=[]
        for name,run in (('SteamGridDB',lambda:sgdb_search(query,key) if key else []),('Libretro',lambda:libretro_search(query,preferences.get('_artwork_platform',''),True)),('Wikipedia',lambda:wiki_search(query))):
            try:rows+=run()
            except (OSError,ValueError,KeyError) as error:errors.append(name+': '+str(error))
        if not rows and errors:raise OSError('; '.join(errors))
        return list({row['url']:row for row in rows}.values())
    if provider=='steamgriddb':return sgdb_search(query,key)
    if provider=='libretro':return libretro_search(query,preferences.get('_artwork_platform',''))
    if provider=='automatic' and key:
        try:
            rows=sgdb_search(query,key)
            if rows:return rows
        except (OSError,ValueError,KeyError):pass
    if provider=='automatic':
        try:
            rows=libretro_search(query,preferences.get('_artwork_platform',''))
            if rows:return rows
        except (OSError,ValueError):pass
    return wiki_search(query)

def best_match(entry,rows):
    wanted=normalized(title_for(entry))
    exact=[row for row in rows if normalized(row['title'])==wanted]
    # Never silently assign an unrelated search result.
    if exact:return exact[0]
    # Wikipedia redirects the Deluxe edition to the shared Mario Kart 8 article.
    if entry.game_id.upper()=='0100152000022000':
        return next((row for row in rows if row.get('provider')=='Wikipedia' and normalized(row['title'])=='mariokart8'),None)
    return None

def download(row,store):
    import hashlib
    url=row['url'];parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or not parsed.hostname:raise ValueError('URL de imagen inválida.')
    data=request(url,limit=MAX_IMAGE)
    if not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff') or (data.startswith(b'RIFF') and data[8:12]==b'WEBP')):raise ValueError('El proveedor no devolvió una imagen PNG, JPEG o WebP.')
    suffix='.png' if data.startswith(b'\x89PNG') else '.jpg' if data.startswith(b'\xff\xd8') else '.webp'
    target=store.root/'artwork'/(hashlib.sha256(url.encode()).hexdigest()+suffix);target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():
        temporary=target.with_suffix('.download');temporary.write_bytes(data);temporary.replace(target)
    atomic_json(target.with_suffix('.json'),{k:row[k] for k in ('title','provider','page','url') if k in row})
    return str(target)
