"""Lossless binary KeyValues editing, atomic backups and deferred Steam writes."""
import datetime,fcntl,os,pathlib,struct,tempfile,zlib,re

class SteamRunningError(RuntimeError): pass
class KVError(ValueError): pass

def steam_running(proc=pathlib.Path('/proc')):
    for p in proc.glob('[0-9]*/comm'):
        try:
            if p.read_text().strip().lower() in ('steam','steam.exe'): return True
        except OSError: pass
    return False

def read_kv(data):
    position=0
    def string():
        nonlocal position
        try: end=data.index(b'\0',position)
        except ValueError: raise KVError('Archivo Steam truncado.')
        value=data[position:end].decode('utf-8'); position=end+1; return value
    def take(n):
        nonlocal position
        if position+n>len(data): raise KVError('Archivo Steam truncado.')
        value=data[position:position+n]; position+=n; return value
    def obj(depth=0):
        if depth>32: raise KVError('Archivo Steam demasiado anidado.')
        result={}
        while True:
            type_=take(1)[0]
            if type_==8: return result
            key=string()
            if key in result: raise KVError('Claves duplicadas; se preservó el archivo Steam.')
            if type_==0: value=obj(depth+1)
            elif type_==1: value=string()
            elif type_ in (2,3,4,6): value=take(4)
            elif type_==7: value=take(8)
            else: raise KVError(f'Tipo VDF {type_} no soportado; se preservó el archivo.')
            result[key]=(type_,value)
    result=obj()
    if position!=len(data): raise KVError('Contenido adicional inesperado en VDF.')
    return result

def write_kv(obj):
    output=bytearray()
    for key,(type_,value) in obj.items():
        output.extend(bytes([type_])); output.extend(key.encode()+b'\0')
        if type_==0: output.extend(write_kv(value))
        elif type_==1: output.extend(value.encode()+b'\0')
        else: output.extend(value)
    output.append(8); return bytes(output)

def get(entry,key,default=None):
    pair=next((v for k,v in entry.items() if k.lower()==key.lower()),None)
    if pair is None:return default
    if pair[0]==2:return struct.unpack('<I',pair[1])[0]
    return pair[1]

def set_value(entry,key,value):
    actual=next((k for k in entry if k.lower()==key.lower()),key)
    entry[actual]=(2,struct.pack('<I',value&0xffffffff)) if isinstance(value,int) else (1,value)

def find_accounts(home=None):
    home=pathlib.Path(home or pathlib.Path.home()); result=[]; seen=set()
    for root in (home/'.local/share/Steam',home/'.steam/steam',home/'.steam/root',home/'.var/app/com.valvesoftware.Steam/data/Steam'):
        if not root.exists():continue
        for p in (root/'userdata').glob('[0-9]*/config'):
            if p.resolve() not in seen:result.append(p.resolve()); seen.add(p.resolve())
    return sorted(result,key=lambda p:(p/'shortcuts.vdf').stat().st_mtime if (p/'shortcuts.vdf').exists() else 0,reverse=True)

def active_account(home=None):
    home=pathlib.Path(home or pathlib.Path.home());candidates=[]
    for root in (home/'.local/share/Steam',home/'.steam/steam',home/'.var/app/com.valvesoftware.Steam/data/Steam'):
        path=root/'config/loginusers.vdf'
        if not path.is_file():continue
        for id_,block in re.findall(r'"(\d{17})"\s*\{(.*?)\n\s*\}',path.read_text(),re.S):
            fields={k.lower():v for k,v in re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"',block)}
            account=int(id_)-76561197960265728;config=root/'userdata'/str(account)/'config'
            if config.is_dir():candidates.append((fields.get('mostrecent')=='1',int(fields.get('timestamp','0')),config.resolve()))
    return max(candidates,key=lambda c:(c[0],c[1]))[2] if candidates else None

def shortcut_id(exe,name):return zlib.crc32((exe+name).encode())|0x80000000

def update_shortcuts(config,entries,launcher_for,is_running=None):
    """Preserve all other entries and reject concurrent Steam/filesystem writes."""
    if is_running is None:is_running=steam_running
    config=pathlib.Path(config)
    if is_running():raise SteamRunningError('Steam debe estar cerrado para guardar los accesos.')
    config.mkdir(parents=True,exist_ok=True)
    with (config/'shortcuts.vdf.deck-library.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=config/'shortcuts.vdf'; existed=path.exists(); old=path.read_bytes() if existed else b''
        root=read_kv(old) if old else {'shortcuts':(0,{})}
        if 'shortcuts' not in root or root['shortcuts'][0]!=0:raise KVError('VDF sin biblioteca válida.')
        shortcuts=root['shortcuts'][1]; result=[]
        duplicate_names={e.name for e in entries if sum(other.name==e.name for other in entries)>1}
        for entry in entries:
            steam_name=entry.name+(' · '+entry.platform if entry.name in duplicate_names else '')
            original=entry.metadata.get('steam_original') if entry.kind=='steam' else entry.metadata.get('steam_override')
            if original and pathlib.Path(original['account']).resolve()!=config.resolve():raise ValueError('Se requiere la cuenta de Steam a la que pertenece el acceso.')
            launcher=pathlib.Path(launcher_for(entry)); exe='"'+str(launcher)+'"'
            target_id=entry.metadata.get('steam_appid') if entry.metadata.get('steam_account')==str(config) else None
            match=next((v[1] for v in shortcuts.values() if v[0]==0 and ((target_id is not None and get(v[1],'appid')==target_id) or (target_id is None and (get(v[1],'exe')==exe or get(v[1],'appname')==steam_name)))),None)
            if original and match is None:raise ValueError('El acceso de Steam ya no existe. Buscar juegos de nuevo antes de editarlo.')
            if match is None:
                match={}; index=str(max([int(k) for k in shortcuts if k.isdigit()]+[-1])+1); shortcuts[index]=(0,match)
                for k,v in {'appid':shortcut_id(exe,steam_name),'ShortcutPath':'','IsHidden':0,'AllowDesktopConfig':0,'AllowOverlay':1,'OpenVR':0,'Devkit':0,'DevkitGameID':'','DevkitOverrideAppID':0,'LastPlayTime':0,'FlatpakAppID':''}.items():set_value(match,k,v)
                match['tags']=(0,{'0':(1,'Deck Library')})
            fields={'appname':steam_name,'exe':exe,'StartDir':'"'+str(launcher.parent)+'"','LaunchOptions':'','AllowDesktopConfig':0}
            if original:fields={'appname':entry.name,'exe':original['exe'],'StartDir':original['startdir'],'LaunchOptions':original['options']}
            for k,v in fields.items():set_value(match,k,v)
            if entry.icon:set_value(match,'icon',entry.icon)
            result.append({'id':entry.id,'appid':get(match,'appid'),'name':entry.name})
        new=write_kv(root); read_kv(new)
        if is_running() or path.exists()!=existed or (path.exists() and path.read_bytes()!=old):raise SteamRunningError('Steam o la biblioteca cambió durante el guardado; intentá nuevamente.')
        backup=None
        if existed and new!=old:
            stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')
            backup=path.with_name('shortcuts.vdf.deck-library-backup-'+stamp); backup.write_bytes(old); backup.chmod(0o600)
        fd,temp=tempfile.mkstemp(prefix='.shortcuts-',dir=config)
        try:
            with os.fdopen(fd,'wb') as f:f.write(new); f.flush(); os.fsync(f.fileno())
            os.replace(temp,path)
        finally:
            if os.path.exists(temp):os.unlink(temp)
        return result,str(backup) if backup else None

def remove_shortcuts(config,appids,is_running=None):
    """Delete shortcuts by app ID, renumber the rest and keep a backup. Returns the removed names."""
    if is_running is None:is_running=steam_running
    config=pathlib.Path(config);wanted={int(a)&0xffffffff for a in appids}
    if is_running():raise SteamRunningError('Steam debe estar cerrado para quitar los accesos.')
    path=config/'shortcuts.vdf'
    if not path.exists():return [],None
    with (config/'shortcuts.vdf.deck-library.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old=path.read_bytes();root=read_kv(old)
        if 'shortcuts' not in root or root['shortcuts'][0]!=0:raise KVError('VDF sin biblioteca válida.')
        kept=[];removed=[]
        for key in sorted(root['shortcuts'][1],key=lambda k:(0,int(k)) if k.isdigit() else (1,0)):
            pair=root['shortcuts'][1][key]
            if pair[0]==0 and get(pair[1],'appid') is not None and (get(pair[1],'appid')&0xffffffff) in wanted:removed.append(get(pair[1],'appname',''))
            else:kept.append(pair)
        if not removed:return [],None
        root['shortcuts']=(0,{str(i):pair for i,pair in enumerate(kept)})
        new=write_kv(root);read_kv(new)
        if is_running() or path.read_bytes()!=old:raise SteamRunningError('Steam o la biblioteca cambió durante el guardado; intentar nuevamente.')
        stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')
        backup=path.with_name('shortcuts.vdf.deck-library-backup-'+stamp);backup.write_bytes(old);backup.chmod(0o600)
        fd,temp=tempfile.mkstemp(prefix='.shortcuts-',dir=config)
        try:
            with os.fdopen(fd,'wb') as f:f.write(new);f.flush();os.fsync(f.fileno())
            os.replace(temp,path)
        finally:
            if os.path.exists(temp):os.unlink(temp)
    return removed,str(backup)

def move_artwork_aside(config,appids):
    """Grid images of removed shortcuts go to a backup folder instead of being deleted."""
    grid=pathlib.Path(config)/'grid'
    if not grid.is_dir():return 0
    stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f');moved=0
    for appid in appids:
        number=str(int(appid)&0xffffffff)
        for path in grid.iterdir():
            if path.is_file() and re.fullmatch(re.escape(number)+r'(_hero|_logo|_icon|p)?\.(png|jpg|jpeg|webp|ico)',path.name):
                target=grid/'.deck-library-backups'/(path.name+'.removed.'+stamp);target.parent.mkdir(exist_ok=True);path.replace(target);moved+=1
    return moved
