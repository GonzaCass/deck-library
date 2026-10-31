"""Opt-in visual fixtures. Only public artwork is downloaded; no game files."""
import concurrent.futures,html,json,pathlib,re,urllib.parse,urllib.request

GAMES=[
    {'name':'The Legend of Zelda: Tears of the Kingdom','platform':'Switch','kind':'emulated','id':'0100F2C0115B6000','wiki':'The_Legend_of_Zelda:_Tears_of_the_Kingdom'},
    {'name':'Hollow Knight','platform':'Linux','steam':367520},
    {'name':'God of War II','platform':'PlayStation 2','kind':'emulated','id':'SCUS-97481','libretro':('Sony - PlayStation 2','God of War II (USA).png')},
    {'name':'Mario Kart Wii','platform':'Wii','kind':'emulated','id':'RMCP01','libretro':('Nintendo - Wii','Mario Kart Wii (USA) (En,Fr,Es).png')},
    {'name':'Grand Theft Auto IV','platform':'Windows','steam':12210},
    {'name':'Hades','platform':'Windows','steam':1145360},
    {'name':'Super Mario Odyssey','platform':'Switch','kind':'emulated','id':'0100000000010000','wiki':'Super_Mario_Odyssey'},
    {'name':'Portal 2','platform':'Linux','steam':620},
    {'name':'Celeste','platform':'Linux','steam':504230},
    {'name':'Dead Cells','platform':'Linux','steam':588650},
    {'name':'Stardew Valley','platform':'Linux','steam':413150},
    {'name':'DOOM','platform':'Windows','steam':379720},
]

PORT_ARTWORK=[{'name':'Spider-Man','libretro':('Sony - PlayStation','Spider-Man (USA).png')}]

def fetch(url,limit=12*1024*1024):
    if urllib.parse.urlparse(url).scheme!='https':raise ValueError('Artwork requires HTTPS')
    request=urllib.request.Request(url,headers={'User-Agent':'DeckLibrary-VisualPreview/1.0'})
    with urllib.request.urlopen(request,timeout=15) as response:
        data=response.read(limit+1)
    if len(data)>limit:raise ValueError('Artwork response exceeds the preview limit')
    return data


def artwork(cache,download=False):
    """Return title -> artwork paths, keeping the optional cache outside releases."""
    cache=pathlib.Path(cache);cache.mkdir(parents=True,exist_ok=True)
    def one(index,game):
        result={};sources={}
        for kind in ('cover','hero') if game.get('steam') else ('cover',):
            target=cache/f'{index:02d}-{kind}.img'
            if target.is_file():result[kind]=str(target);continue
            if not download:continue
            try:
                if game.get('steam'):
                    filename='library_600x900.jpg' if kind=='cover' else 'library_hero.jpg'
                    url=f'https://cdn.akamai.steamstatic.com/steam/apps/{game["steam"]}/{filename}'
                elif game.get('libretro'):
                    system,filename=game['libretro'];url='https://thumbnails.libretro.com/'+urllib.parse.quote(system,safe='')+'/Named_Boxarts/'+urllib.parse.quote(filename,safe='')
                else:
                    page='https://en.wikipedia.org/wiki/'+urllib.parse.quote(game['wiki'],safe=':_')
                    body=fetch(page,3*1024*1024).decode('utf-8')
                    match=re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"',body)
                    if not match:raise ValueError('No cover image in article metadata')
                    url=html.unescape(match[1])
                data=fetch(url)
                if not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff') or (data.startswith(b'RIFF') and data[8:12]==b'WEBP')):raise ValueError('Not an artwork image')
                target.write_bytes(data);result[kind]=str(target);sources[kind]=url
            except (OSError,ValueError) as error:print(f'Artwork unavailable: {game["name"]} ({kind}): {error}',flush=True)
        if sources:(cache/f'{index:02d}-sources.json').write_text(json.dumps({'title':game['name'],'sources':sources},indent=2),encoding='utf-8')
        return game['name'],result
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        return dict(pool.map(lambda item:one(*item),enumerate(GAMES+PORT_ARTWORK)))


def entries(store,images):
    from deck_library.models import Entry
    result=[]
    for index,game in enumerate(GAMES):
        result.append(Entry(game['name'],['/bin/true',f'visual-demo-{index}'],kind=game.get('kind','port'),platform=game['platform'],game_id=game.get('id',''),cover=images.get(game['name'],{}).get('cover',''),cwd=str(store.root),metadata={'visual_demo':True}))
    return result
