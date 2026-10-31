"""Reviewed resource links and bundled runtime recommendations; never execute remote advice."""
import json,pathlib,re


def catalog():
    value=json.loads((pathlib.Path(__file__).resolve().parent.parent/'catalog/game-fixes.json').read_text())
    return value['games'] if value.get('schema_version')==1 else []


def for_entry(entry):
    if entry.kind=='emulated':return []
    name=re.sub(r'[^a-z0-9]','',entry.name.casefold());appid=str(entry.metadata.get('steam_appid') or entry.game_id)
    return [row for row in catalog() if appid in row.get('steam_appids',[]) or name in row.get('names',[])]


def recommendation(entry,store=None):
    from . import presets
    # Community content cannot silently change the runtime. Only shipped, confirmed profiles.
    for value in presets.recommended(entry,store):
        runtime=value.get('runtime') or {}
        if presets.is_bundled(value) and value.get('tested',{}).get('status')=='user-confirmed' and runtime.get('kind')=='proton' and runtime.get('version'):
            return {'version':runtime['version'],'evidence':value['name'],'source':'bundled-confirmed-profile'}
    return None


def discover(home=None):
    """Known owned Steam games only; read manifests without downloading game data."""
    from .proton_tools import libraries
    from .steam_input import parse_text,first
    from .models import Entry
    result=[];seen=set()
    for root in libraries(home):
        for row in catalog():
            for appid in row.get('steam_appids',[]):
                manifest=root/'steamapps'/('appmanifest_'+appid+'.acf')
                try:
                    if manifest.stat().st_size>1024*1024:continue
                    state=first(parse_text(manifest.read_text()),'AppState',[])
                    directory=first(state,'installdir','');name=first(state,'name','')
                    if not directory or pathlib.Path(directory).name!=directory or directory in ('.','..') or not name:continue
                    folder=root/'steamapps/common'/directory
                    if not folder.is_dir() or appid in seen:continue
                    seen.add(appid);source=folder;found=[]
                    for relative in row.get('executables',[]):
                        path=folder
                        for part in pathlib.PurePosixPath(relative).parts:
                            if part in ('.','..'):path=None;break
                            path=next((p for p in path.iterdir() if p.name.casefold()==part.casefold()),path/part) if path.is_dir() else path/part
                        if path and path.is_file():found.append(path)
                    if len(found)==1:source=found[0]
                    result.append(Entry(name,['steam','steam://run/'+appid],'steam','Windows',str(source),game_id=appid,metadata={'steam_appid':int(appid),'steam_store':True,'game_root':str(folder)}))
                except (OSError,ValueError,TypeError):continue
    return result
