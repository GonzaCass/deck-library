"""Current public catalogs and an independent list; metadata never runs install scripts."""
import re,urllib.parse,html
API='https://api.quiverlauncher.com/api/v1'
INDEPENDENT='https://raw.githubusercontent.com/Sebastrion/awesome-unofficial-pc-ports/main/README.md'

def pages(path,get):
    rows=[];cursor='';seen=set()
    for _ in range(20):
        value=get(API+path+('' if path.endswith('?') else '&' if '?' in path else '?')+'limit=100'+('&cursor='+urllib.parse.quote(cursor,safe='') if cursor else ''))
        if not isinstance(value,dict) or not isinstance(value.get('items'),list):break
        rows.extend(value['items']);cursor=value.get('nextCursor')
        if value.get('isDone') or not cursor or cursor in seen:break
        seen.add(cursor)
    return rows

def quiver(get,clean):
    apps=pages('/apps?',get);statuses=pages('/release-status?',get)
    repos={r.get('slug'):r.get('repository') for r in statuses if r.get('provider')=='github'}
    result=[]
    systems={'n64':'Nintendo 64','ps1':'PlayStation','ps2':'PlayStation 2','xbox360':'Xbox 360','wii':'Wii','wiiu':'Wii U','gba':'Game Boy Advance','snes':'Super Nintendo','gc':'GameCube'}
    for row in apps:
        repo=repos.get(row.get('slug'));art=row.get('libraryArt') or {};games=row.get('games') or []
        value=clean({'repository':repo,'name':row.get('projectName') or row.get('name'),'folderName':row.get('launcher',{}).get('folderName'),'category':', '.join(systems.get(c,c) for c in row.get('consoles',[])),'appIconUrl':art.get('capsule') or row.get('artwork')},source='Quiver actual')
        if value:
            value.update(added_at=(row.get('addedAt') or 0)/1000,release_at=(row.get('lastReleaseAt') or 0)/1000,release_version=str(row.get('lastReleaseVersion') or '')[:100],game_title=' / '.join(g.get('title','') for g in games if g.get('title')) or row.get('name',''),description=str(row.get('description') or '')[:600],icon_fallback=row.get('artwork') or '',supported_os=row.get('supportedOS',[]),catalog_slug=row.get('slug',''))
            result.append(value)
    return result

def independent(document,clean):
    if not isinstance(document,str):return []
    category='Otros';rows=[];title='';description=[];current=None
    def finish():
        if current and description:
            current['description']=' '.join(description)[:600]
            if current['list'] in ('Nintendo','Xbox','SEGA'):
                text=current['description']+' '+current.get('game_title','')
                for pattern,platform in [(r'Game Boy Advance','Game Boy Advance'),(r'Xbox 360','Xbox 360'),(r'original.Xbox','Xbox'),(r'GameCube','GameCube'),(r'\bN64\b','Nintendo 64'),(r'Wii U','Wii U'),(r'\bWii\b','Wii')]:
                    if re.search(pattern,text,re.I):current['list']=platform;break
    for line in document.splitlines():
        if line.startswith('## '):finish();current=None;category=re.sub(r'[^\w\s]','',line[3:]).strip();title=''
        summary=re.search(r'<summary>\s*(.*?)\s*</summary>',line)
        if summary:finish();current=None;title=html.unescape(re.sub('<[^>]+>','',summary[1])).strip()
        if line.strip()=='</details>':finish();current=None;title=''
        match=re.match(r'###\s+(?:⭐\s*)?\[([^\]]+)\]\(https://github.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:/[^)]*)?\)',line)
        if match:
            finish();description=[];current=None
            value=clean({'repository':match[2],'name':match[1],'category':category},source='Lista independiente')
            if value:
                value['game_title']=title if 'utilit' not in category.casefold() else '';rows.append(value);current=value
        elif line.startswith('#'):finish();current=None
        elif current and line.strip() and not line.lstrip().startswith(('<','📺','📖','- ')):
            description.append(html.unescape(re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',line.strip())).replace('**','').replace('`',''))
    finish()
    return rows

def enrich_games(rows,get):
    """Match exact game identities, never project-name guesses, to public game artwork."""
    from .cover_provider import normalized
    games={normalized(game['title']):game for game in pages('/games?',get) if isinstance(game.get('title'),str)}
    systems={'n64':'Nintendo 64','ps1':'PlayStation','ps2':'PlayStation 2','ps3':'PlayStation 3','gc':'GameCube','wii':'Wii','wiiu':'Wii U','gba':'Game Boy Advance','snes':'Super Nintendo','xbox360':'Xbox 360','x360':'Xbox 360','og xbox':'Xbox','nes':'Nintendo Entertainment System'}
    for row in rows:
        title=row.get('game_title') or row.get('cover_title')
        if not title:continue
        game=games.get(normalized(title))
        if not game:continue
        art=game.get('libraryArt') or {}
        if not row.get('icon'):row['icon']=art.get('capsule') or game.get('artwork') or ''
        if not row.get('icon_fallback'):row['icon_fallback']=game.get('artwork') or ''
        if row.get('list') in ('Nintendo','SEGA','Xbox','Indie','Otros',''):
            consoles=game.get('originalSystems') or []
            if consoles:row['list']=', '.join(systems.get(c,c) for c in consoles)
