"""Read existing non-Steam shortcuts without changing launch or Proton settings."""
import pathlib,re,shlex
from .models import Entry
from .steam import read_kv,get,find_accounts,active_account

def shortcuts(account):
    path=pathlib.Path(account)/'shortcuts.vdf'
    if not path.exists():return []
    root=read_kv(path.read_bytes())['shortcuts'][1];items=[]
    for _,pair in root.items():
        if pair[0]!=0:continue
        value=pair[1];name=get(value,'appname','');exe=get(value,'exe','');appid=get(value,'appid')
        if not name or not exe or appid is None:continue
        items.append({'name':name,'appid':appid,'exe':exe,'options':get(value,'LaunchOptions',''),'startdir':get(value,'StartDir',''),'icon':get(value,'icon',''),'account':str(account)})
    return items

def launch_command(item):
    # exe is a single executable even if a legacy shortcut omitted its quotes.
    executable=item['exe'].strip().strip('"')
    try:args=shlex.split(item['options'])
    except ValueError:args=[]
    return [executable,*args]

def merge_steam(entries,home=None,account=None):
    from .gtaiv import discover
    entries=list(entries)
    for game in discover(home) if account is None or home is not None else []:
        match=next((e for e in entries if e.metadata.get('steam_store') and e.metadata.get('steam_appid')==12210),None)
        if match:match.metadata.update(game.metadata)
        else:entries.append(game)
    account=account or active_account(home)
    if account is None:
        accounts=find_accounts(home)
        if len(accounts)!=1:return entries
        account=accounts[0]
    result=list(entries);items=shortcuts(account)
    for item in items:
        command=launch_command(item);launch=command[0]
        instance=''
        if '--launch' in command:
            try:instance=command[command.index('--launch')+1]
            except IndexError:pass
        managed_id=pathlib.Path(launch).stem if pathlib.Path(launch).parent.name=='launchers' else ''
        match=next((e for e in result if not e.metadata.get("steam_store") and ((managed_id and e.id==managed_id) or (instance and e.metadata.get('instance_id')==instance) or (e.platform=='Minecraft' and e.kind=='minecraft' and re.sub(r'[^a-z0-9]','',e.name.lower())==re.sub(r'[^a-z0-9]','',item['name'].lower())) or (e.kind=='steam' and e.metadata.get('steam_appid')==item['appid']) or (e.kind!='steam' and e.source==launch) or e.name==item['name'])),None)
        if match:
            match.metadata.update(steam_appid=item['appid'],steam_account=str(account),steam_name=item['name'])
            if match.kind=='steam':match.metadata['steam_original']=item
            continue
        platform='Minecraft' if instance else 'Windows' if launch.lower().endswith('.exe') else 'Steam'
        entry=Entry(item['name'],command,'steam',platform,launch if launch.startswith('/') else '',item['startdir'].strip('"') or str(pathlib.Path.home()),icon=item['icon'],metadata={'steam_appid':item['appid'],'steam_account':str(account),'steam_name':item['name'],'steam_original':item})
        result.append(entry)
    return prune(result,account,{item['appid'] for item in items})

def prune(entries,account,present):
    """Forget shortcuts that no longer exist in Steam: imported entries disappear, managed ones lose their Steam link."""
    kept=[];linked={(e.metadata.get('steam_account'),e.metadata.get('steam_appid')) for e in entries if e.kind!='steam' and e.metadata.get('steam_appid') is not None}
    for entry in entries:
        meta=entry.metadata
        # An imported shortcut that a managed entry now owns is the same game; keep only the managed one.
        if entry.kind=='steam' and not meta.get('steam_store') and (meta.get('steam_account'),meta.get('steam_appid')) in linked:continue
        if meta.get('steam_store') or meta.get('steam_appid') is None or meta.get('steam_account')!=str(account) or meta['steam_appid'] in present:kept.append(entry);continue
        if entry.kind=='steam':continue
        for key in ('steam_appid','steam_account','steam_name','steam_original','steam_override'):meta.pop(key,None)
        kept.append(entry)
    return kept

def game_uri(appid):return 'steam://rungameid/'+str((int(appid)<<32)|0x02000000)

def sync_covers(account,entries,results,is_running=None):
    """Write portrait grids, backing up replacements; caller synchronizes Steam closure."""
    import datetime,hashlib,os,tempfile,shutil
    from .steam import steam_running,SteamRunningError
    is_running=is_running or steam_running
    if not any(entry.cover for entry in entries):return 0
    grid=pathlib.Path(account)/'grid';grid.mkdir(parents=True,exist_ok=True)
    saved=0
    by_id={r['id']:r for r in results if 'id' in r and 'appid' in r}
    for entry in entries:
        if not entry.cover or entry.id not in by_id:continue
        source=pathlib.Path(entry.cover)
        if not source.is_file():continue
        if source.stat().st_size>12*1024*1024:raise ValueError('Carátula demasiado grande para Steam.')
        data=source.read_bytes()
        if data.startswith(b'\x89PNG\r\n\x1a\n'):suffix='.png'
        elif data.startswith(b'\xff\xd8\xff'):suffix='.jpg'
        else:
            # Decode other local formats through the same image loader as the UI.
            import gi
            gi.require_version('GdkPixbuf','2.0')
            from gi.repository import GdkPixbuf
            pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(source),600,900,True);ok,data=pixbuf.save_to_bufferv('png',[],[])
            if not ok:raise ValueError('No se pudo convertir la carátula para Steam.')
            suffix='.png'
        appid=str(by_id[entry.id]['appid']);target=grid/(appid+'p'+suffix)
        previous=[p for ext in ('.png','.jpg','.jpeg','.webp') if (p:=grid/(appid+'p'+ext)).exists()]
        if previous==[target] and target.read_bytes()==data:continue
        if is_running():raise SteamRunningError('Steam se abrió antes de guardar las carátulas. Guardar el acceso de nuevo.')
        stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f');backups={}
        for path in previous:
            backup=grid/'.deck-library-backups'/(path.name+'.'+stamp);backup.parent.mkdir(exist_ok=True);shutil.copy2(path,backup);backups[path]=backup
        fd,name=tempfile.mkstemp(prefix='.deck-library-grid-',dir=grid)
        try:
            with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
            if is_running():raise SteamRunningError('Steam se abrió durante el guardado de las carátulas.')
            for path in previous:
                if path!=target:path.unlink()
            os.replace(name,target);saved+=1
        except Exception:
            for path,backup in backups.items():shutil.copy2(backup,path)
            raise
        finally:
            if os.path.exists(name):os.unlink(name)
    return saved
