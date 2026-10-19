"""Current public catalogs and an independent list; metadata never runs install scripts."""
import re,urllib.parse
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
            value.update(added_at=(row.get('addedAt') or 0)/1000,release_at=(row.get('lastReleaseAt') or 0)/1000,game_title=' / '.join(g.get('title','') for g in games if g.get('title')) or row.get('name',''),description=str(row.get('description') or '')[:600],icon_fallback=row.get('artwork') or '',supported_os=row.get('supportedOS',[]),catalog_slug=row.get('slug',''))
            result.append(value)
    return result

def independent(document,clean):
    if not isinstance(document,str):return []
    category='Otros';rows=[]
    for line in document.splitlines():
        if line.startswith('## '):category=re.sub(r'[^\w\s]','',line[3:]).strip()
        match=re.match(r'###\s+(?:⭐\s*)?\[([^\]]+)\]\(https://github.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:/[^)]*)?\)',line)
        if match:
            value=clean({'repository':match[2],'name':match[1],'category':category},source='Lista independiente')
            if value:rows.append(value)
    return rows
