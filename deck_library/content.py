"""Inventory and installation of user-supplied Switch content; no downloads or keys."""
import configparser,hashlib,json,os,pathlib,re,shutil,struct,tempfile
from .models import atomic_json

KNOWN_IDS={'mario kart 8 deluxe':'0100152000022000','super smash bros. ultimate':'01006A800016E000','super mario party jamboree':'0100965017338000','super mario party':'010036B0034E4000','mario party superstars':'01006FE013472000'}

def pfs_entries(path):
    """Read the unencrypted PFS0 container only, validating offsets before extracting."""
    path=pathlib.Path(path);size=path.stat().st_size
    with path.open('rb') as source:
        header=source.read(16)
        if len(header)!=16 or header[:4]!=b'PFS0':raise ValueError('El archivo NSP no tiene un formato admitido; el original no se modificó.')
        count,string_size,_=struct.unpack('<III',header[4:])
        if not 0<count<=4096 or not 0<string_size<=1024*1024:raise ValueError('El archivo NSP está dañado o no es un NSP.')
        table=source.read(count*24);names=source.read(string_size)
        if len(table)!=count*24 or len(names)!=string_size:raise ValueError('NSP truncado.')
        start=16+count*24+string_size;items=[];seen=set()
        for index in range(count):
            offset,length,string_offset,_=struct.unpack_from('<QQII',table,index*24)
            if string_offset>=len(names):raise ValueError('El archivo NSP está dañado o no es un NSP.')
            end=names.find(b'\0',string_offset)
            if end<0:raise ValueError('El archivo NSP está dañado o no es un NSP.')
            name=names[string_offset:end].decode('utf-8')
            if pathlib.PurePosixPath(name).name!=name or '\\' in name or name in ('.','..') or name in seen:raise ValueError('El archivo NSP está dañado o no es un NSP.')
            if start+offset+length>size:raise ValueError('El archivo NSP está dañado o no es un NSP.')
            seen.add(name);items.append({'name':name,'offset':start+offset,'size':length})
        ranges=sorted((i['offset'],i['offset']+i['size']) for i in items if i['size'])
        if any(a[1]>b[0] for a,b in zip(ranges,ranges[1:])):raise ValueError('Datos NSP superpuestos.')
        return items

def switch_id(entry):
    if entry.game_id and re.fullmatch(r'010[0-9A-Fa-f]{13}',entry.game_id):return entry.game_id.upper()
    for text in (entry.source,entry.name):
        match=re.search(r'(010[0-9a-fA-F]{13})',text)
        if match:return f'{int(match.group(1),16)&~0x1fff:016X}'
    folder=pathlib.Path(entry.source).parent
    for path in folder.glob('updates/*.nsp'):
        match=re.search(r'(010[0-9a-fA-F]{13})',path.name)
        if match:return f'{int(match.group(1),16)&~0x1fff:016X}'
    if entry.source.lower().endswith('.nsp'):
        try:
            for item in pfs_entries(entry.source):
                match=re.fullmatch(r'(010[0-9a-fA-F]{13})[0-9a-fA-F]{16}\.tik',item['name'])
                if match:return f'{int(match.group(1),16)&~0x1fff:016X}'
        except (OSError,ValueError):pass
    return KNOWN_IDS.get(entry.name.lower(),'')

def eden_paths(home=None,config_dir=None):
    home=pathlib.Path(home or pathlib.Path.home())
    fallback=home/'.var/app/dev.eden_emu.eden/config/eden'
    config=pathlib.Path(config_dir or (home/'.config/eden' if (home/'.config/eden/qt-config.ini').exists() or not (fallback/'qt-config.ini').exists() else fallback))
    parser=configparser.ConfigParser(interpolation=None);parser.optionxform=str;parser.read(config/'qt-config.ini')
    section=parser['Data%20Storage'] if parser.has_section('Data%20Storage') else {}
    data=config.parent.parent/'data/eden' if '.var/app/dev.eden_emu.eden/' in str(config) else home/'.local/share/eden'
    return {'config':config,'data':data,**{k:pathlib.Path(section.get(k+'_directory') or data/k) for k in ('nand','load','sdmc')}}

def emulator_busy(name='eden'):
    for path in pathlib.Path('/proc').glob('[0-9]*/comm'):
        try:
            if path.read_text().strip()==name:return True
        except OSError:pass
    return False

def nsp_identity(path):
    match=re.search(r'(010[0-9a-fA-F]{13})',pathlib.Path(path).name)
    if not match:
        for item in pfs_entries(path):
            if item['name'].endswith('.tik'):
                match=re.match(r'(010[0-9a-fA-F]{13})',item['name'])
                if match:break
    if not match:return {'title_id':'','base_id':'','kind':''}
    title_id=int(match.group(1),16);suffix=title_id&0x1fff
    return {'title_id':f'{title_id:016X}','base_id':f'{title_id&~0x1fff:016X}','kind':'updates' if suffix==0x800 else 'dlc' if suffix>=0x1000 else 'base'}

def content_installed(path,registered):
    try:
        parts=[i for i in pfs_entries(path) if re.fullmatch(r'[0-9a-fA-F]{32}(?:\.cnmt)?\.nca',i['name'])]
        return bool(parts) and all((registered/i['name']).is_file() and (registered/i['name']).stat().st_size==i['size'] for i in parts)
    except (OSError,ValueError):return False

def switch_inventory(entry,home=None,config_dir=None):
    paths=eden_paths(home,config_dir);folder=pathlib.Path(entry.source).parent;tid=switch_id(entry)
    registered=paths['nand']/'user/Contents/registered'
    base_version=re.search(r'\[v(\d+)\]',pathlib.Path(entry.source).name)
    inventory={'title_id':tid,'base':{'path':entry.source,'available':pathlib.Path(entry.source).is_file(),'version':'v'+base_version[1] if base_version else 'No identificada; consultar Eden'},'updates':[],'dlc':[],'mods':[],'paths':{k:str(v) for k,v in paths.items()}}
    for key in ('updates','dlc'):
        for path in sorted((folder/key).glob('*.nsp')):
            inventory[key].append({'path':str(path),'name':path.name,'installed':content_installed(path,registered),'version':(re.search(r'(?:Update )?v(\d+\.\d+\.\d+)',path.name) or [None,''])[1]})
    for record in registered.parent.glob('deck-library-content-*.json'):
        try:
            value=json.loads(record.read_text());identity=value.get('identity',{});kind=identity.get('kind')
            if identity.get('base_id')!=tid or kind not in ('updates','dlc'):continue
            path=pathlib.Path(value['source'])
            if not any(p['path']==str(path) for p in inventory[kind]):inventory[kind].append({'path':str(path),'name':path.name,'installed':all((registered/n).is_file() for n in value['ncas']),'version':''})
        except (OSError,ValueError,KeyError):continue
    if tid:
        for path in sorted((paths['load']/tid).glob('*')):
            if path.is_dir() and any((path/p).exists() for p in ('exefs','romfs','cheats')):inventory['mods'].append({'name':path.name,'path':str(path),'available':True})
    return inventory

def install_nsp(path,config_dir=None,progress=lambda text:None):
    """Register encrypted NCAs from a supplied NSP so CLI boot doesn't race library scanning."""
    if emulator_busy():raise RuntimeError('Eden debe estar cerrado para instalar contenido.')
    path=pathlib.Path(path);items=[i for i in pfs_entries(path) if re.fullmatch(r'[0-9a-fA-F]{32}(?:\.cnmt)?\.nca',i['name'])]
    if not items or not any('.cnmt.nca' in i['name'] for i in items):raise ValueError('El archivo NSP no tiene el contenido esperado para instalarse.')
    target=eden_paths(config_dir=config_dir)['nand']/'user/Contents/registered';target.mkdir(parents=True,exist_ok=True)
    missing=[i for i in items if not (target/i['name']).exists()]
    if shutil.disk_usage(target).free<sum(i['size'] for i in missing)+128*1024**2:raise RuntimeError('No hay espacio suficiente para instalar este contenido.')
    added=[]
    with tempfile.TemporaryDirectory(prefix='.deck-library-install-',dir=target.parent) as folder:
        with path.open('rb') as source:
            for item in items:
                dest=target/item['name'];temporary=pathlib.Path(folder)/item['name'];digest=hashlib.sha256()
                # Existing files are never overwritten, even if a different tool installed them.
                if dest.exists():
                    if dest.is_file() and dest.stat().st_size==item['size']:continue
                    raise ValueError('Ya existe contenido con distinto tamaño: '+item['name'])
                progress('Verificando '+item['name']);source.seek(item['offset']);remaining=item['size']
                with temporary.open('wb') as out:
                    while remaining:
                        chunk=source.read(min(1024**2,remaining))
                        if not chunk:raise ValueError('El archivo NSP quedó incompleto durante la copia. No se instaló.')
                        out.write(chunk);digest.update(chunk);remaining-=len(chunk)
                if digest.hexdigest()[:32].lower()!=item['name'][:32].lower():raise ValueError('El archivo NSP está dañado (falló la verificación). No se instaló.')
                added.append((temporary,dest))
        # All parts validated before any become visible to Eden.
        if emulator_busy():raise RuntimeError('Eden se abrió durante la preparación; cerrarlo y reintentar.')
        committed=[]
        try:
            for temporary,dest in added:
                # Atomic hard-link avoids replacing a concurrent external write.
                os.link(temporary,dest);committed.append(dest)
        except Exception:
            for dest in committed:dest.unlink()
            raise
    atomic_json(target.parent/('deck-library-content-'+hashlib.sha256(str(path).encode()).hexdigest()[:16]+'.json'),{'source':str(path),'identity':nsp_identity(path),'ncas':[i['name'] for i in items]})
    return {'count':len(added),'target':str(target)}


def install_mod_zip(path,entry,store=None,config_dir=None):
    """Install only a supplied LayeredFS tree for this game's title ID."""
    import datetime,zipfile
    from .models import Store
    if emulator_busy():raise RuntimeError('Eden debe estar cerrado para instalar un mod.')
    tid=switch_id(entry)
    if not re.fullmatch(r'010[0-9A-F]{13}',tid):raise ValueError('Falta el Title ID del juego.')
    path=pathlib.Path(path);name=re.sub(r'[^A-Za-z0-9 ._-]','_',path.stem).strip('. ')[:100]
    if not name:raise ValueError('Nombre de mod inválido.')
    target=eden_paths(config_dir=config_dir)['load']/tid/name;target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        files=[]
        for item in archive.infolist():
            if item.is_dir():continue
            relative=pathlib.PurePosixPath(item.filename)
            if relative.is_absolute() or '..' in relative.parts or '\\' in item.filename or (item.external_attr>>16)&0o170000==0o120000:raise ValueError('ZIP con ruta o enlace no permitido.')
            parts=relative.parts
            if 'contents' in parts:
                index=parts.index('contents')
                if len(parts)<=index+2 or parts[index+1].upper()!=tid:continue
                parts=parts[index+2:]
            else:
                index=next((i for i,p in enumerate(parts) if p in ('romfs','exefs','cheats')),None)
                if index is None:continue
                parts=parts[index:]
            if not parts or parts[0] not in ('romfs','exefs','cheats'):continue
            files.append((item,pathlib.Path(*parts)))
        if not files or len(files)>100000 or sum(i.file_size for i,_ in files)>12*1024**3:raise ValueError('ZIP sin un mod compatible o demasiado grande.')
        if len({str(p) for _,p in files})!=len(files):raise ValueError('El ZIP contiene rutas duplicadas.')
        if shutil.disk_usage(target.parent).free<sum(i.file_size for i,_ in files)+128*1024**2:raise ValueError('No hay espacio para este mod.')
        with tempfile.TemporaryDirectory(prefix='.mod-install-',dir=target.parent) as temp:
            stage=pathlib.Path(temp)/'mod';stage.mkdir()
            for item,relative in files:
                dest=stage/relative;dest.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(item) as source,dest.open('wb') as out:shutil.copyfileobj(source,out,1024**2)
            if emulator_busy():raise RuntimeError('Eden se abrió durante la preparación; no se instaló el mod.')
            backup=None
            if target.exists():
                store=store or Store();backup=store.root/'content-backups'/datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')/name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(target),str(backup))
            try:stage.rename(target)
            except Exception:
                if backup:shutil.move(str(backup),str(target))
                raise
    return {'name':name,'files':len(files),'backup':str(backup) if backup else None}
