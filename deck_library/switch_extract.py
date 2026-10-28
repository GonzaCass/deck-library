"""Convert a Switch NSP/XCI the user owns into the extracted exefs/romfs folder that some ports ask for.

The container and cipher work is done by hactool, built from a pinned source release. Keys and tickets stay on this
machine: the user's prod.keys is only read, tickets are copied to a private temporary folder, and neither reaches a log.
"""
import glob,json,os,pathlib,re,shutil,struct,subprocess,tempfile,time
from .models import atomic_json

HACTOOL={'tag':'1.4.0','commit':'3121a5bf08cd81d3a99719feb2cab3b60767afd5','sha256':'5307bbc57131e29a324c18e2c7cdde3a679c2f7d046e82c75e7cea99045ab382'}
HACTOOL['url']='https://github.com/SciresM/hactool/archive/'+HACTOOL['commit']+'.tar.gz'
# nstool applies recent updates (BKTR) that hactool 1.4.0 cannot read, and it ships a prebuilt Linux binary: it is the preferred tool.
NSTOOL={'tag':'1.9.2','sha256':'2ab1d484d79199d1bb428cb920a49cece0ae4d7129c80120eaf48b7361785351','url':'https://github.com/jakcron/nstool/releases/download/v1.9.2/nstool-v1.9.2-ubuntu_x86_64.zip'}
NSTOOL_BINARY_SHA256='b77319d6fb1840599b822a710ec9260a9b32bd51e0f32a472852a8fd2430b67c'
MANIFEST='.deck-library-switch-extract.json'
SUFFIXES=('.nsp','.xci')
# Ports that ask for an extracted exefs/romfs folder, with the Title ID of the game they expect.
KNOWN_TITLES={'01007ef00011e000':'The Legend of Zelda: Breath of the Wild'}
# Signature block size in front of the ticket body, by signature type.
TICKET_BODY={0x10000:0x240,0x10001:0x140,0x10002:0x80,0x10003:0x240,0x10004:0x140,0x10005:0x80}

class NeedsTool(Exception):pass
class NeedsUpdate(ValueError):
    """The game is older than the version a port asks for and no (new enough) update was given."""

def pfs0_entry(path,suffix):
    """(name, offset, size) of the first file in an NSP whose name ends with `suffix`, or None."""
    with open(path,'rb') as stream:
        head=stream.read(16)
        if head[:4]!=b'PFS0':return None
        count,strings=struct.unpack('<II',head[4:12])
        if not 0<count<4096 or strings>1<<20:return None
        entries=stream.read(24*count);names=stream.read(strings);base=16+24*count+strings
    for index in range(count):
        offset,size,name_at=struct.unpack('<QQI',entries[24*index:24*index+20])
        end=names.find(b'\0',name_at)
        name=names[name_at:end if end>=0 else None].decode('utf-8','replace')
        if name.endswith(suffix):return name,base+offset,size
    return None

def parse_cnmt(data):
    """Title ID, version and type (0x80 application, 0x81 patch) from a content-meta record."""
    if len(data)<16:raise ValueError('El registro de versión del juego está incompleto.')
    return {'title_id':format(int.from_bytes(data[:8],'little'),'016x'),'version':int.from_bytes(data[8:12],'little'),'type':data[12]}

def leftovers(root):
    """Folders this app left in a destination (interrupted conversions, backups of replaced ones) and their sizes."""
    root=pathlib.Path(root).expanduser();found=[]
    try:children=sorted(root.glob('.deck-library-*'))
    except OSError:return found
    for path in children:
        if path.is_symlink() or not path.is_dir():continue
        size=0
        for item in path.rglob('*'):
            try:
                if item.is_file() and not item.is_symlink():size+=item.stat().st_size
            except OSError:pass
        found.append((path,size))
    return found

def clean(root):
    """Delete what `leftovers` lists. Returns the bytes freed; the converted games themselves are never touched."""
    freed=0
    for path,size in leftovers(root):
        shutil.rmtree(path,ignore_errors=True)
        if not path.exists():freed+=size
    return freed

def find_keys(home=None,extra=()):
    """prod.keys files left by Switch emulators or by hactool's own folder, most likely first."""
    home=pathlib.Path(home or pathlib.Path.home())
    names=[*map(pathlib.Path,extra)]
    for app in ('eden','yuzu','suyu','sudachi','citron'):names.append(home/'.local/share'/app/'keys/prod.keys')
    names+=[home/'.config/Ryujinx/system/prod.keys',home/'.switch/prod.keys',home/'.config/switch/prod.keys',home/'Emulation/bios/switch/keys/prod.keys']
    names+=map(pathlib.Path,sorted(glob.glob(str(home/'.var/app/*/data/*/keys/prod.keys'))))
    found=[]
    for path in names:
        try:
            if path.is_file() and not path.is_symlink() and str(path) not in found:found.append(str(path))
        except OSError:continue
    return found

def check_keys(path):
    """A prod.keys needs at least the header key and a master key; anything else is not worth passing to hactool."""
    try:text=pathlib.Path(path).read_text(errors='replace')
    except OSError:raise ValueError('No se pudo leer el archivo de claves.')
    if not re.search(r'^\s*header_key\s*=\s*[0-9a-fA-F]{64}\s*$',text,re.M) or not re.search(r'^\s*master_key_0[0-9a-fA-F]\s*=\s*[0-9a-fA-F]{32}\s*$',text,re.M):
        raise ValueError('El archivo no parece un prod.keys completo (faltan header_key o las master_key). Volver a exportarlo desde la consola propia.')
    return str(path)

def parse_ticket(data):
    """(rights ID, encrypted title key) as hex strings from a common ticket. Personalized tickets need the console's own key."""
    if len(data)<0x180:raise ValueError('El ticket es demasiado corto.')
    body=TICKET_BODY.get(int.from_bytes(data[:4],'little'))
    if body is None or len(data)<body+0x170:raise ValueError('Tipo de ticket no reconocido.')
    if data[body+0x141]!=0:raise ValueError('El ticket es personalizado (cifrado para una consola concreta); no se puede convertir sin ella.')
    return data[body+0x160:body+0x170].hex(),data[body+0x40:body+0x50].hex()

def container_kind(path):
    """'nsp' or 'xci' by content, not by name. Compressed NSZ/XCZ are recognised only to explain how to continue."""
    path=pathlib.Path(path)
    if path.suffix.lower() in ('.nsz','.xcz'):raise ValueError('Los archivos NSZ/XCZ están comprimidos. Descomprimirlos primero (por ejemplo con nsz -D) y elegir el NSP/XCI resultante.')
    try:
        with path.open('rb') as stream:
            head=stream.read(4);stream.seek(0x100);xci=stream.read(4)
    except OSError:raise ValueError(f'No se pudo leer {path.name}.')
    if head==b'PFS0':return 'nsp'
    if xci==b'HEAD':return 'xci'
    raise ValueError(f'{path.name} no es un NSP ni un XCI.')

def sanitize(line):
    """Long hexadecimal runs are keys, tickets or hashes: they never go to the screen or to a report."""
    return re.sub(r'[0-9a-fA-F]{24,}','…',line)

def is_hactool(path):
    try:result=subprocess.run([str(path)],capture_output=True,text=True,timeout=15)
    except (OSError,subprocess.SubprocessError):return False
    return 'hactool (c) SciresM' in result.stdout+result.stderr

def is_nstool(path):
    try:result=subprocess.run([str(path)],capture_output=True,text=True,timeout=15)
    except (OSError,subprocess.SubprocessError):return False
    return 'NSTool v' in result.stdout+result.stderr

def backend_of(tool):
    return 'nstool' if pathlib.Path(str(tool)).name.startswith('nstool') else 'hactool'

def tool_folder(store):return pathlib.Path(store.root)/'tools/hactool'

def nstool_folder(store):return pathlib.Path(store.root)/'tools/nstool'

def bundled_tool():
    """Redistributed upstream Linux x86-64 executable, with its license and pinned digest."""
    import platform
    from .ports import sha256_file
    path=pathlib.Path(__file__).resolve().parent.parent/'assets/tools/nstool/nstool'
    if platform.system()!='Linux' or platform.machine().lower() not in ('x86_64','amd64'):return ''
    if path.is_file() and os.access(path,os.X_OK) and sha256_file(path)==NSTOOL_BINARY_SHA256:return str(path)
    return ''

def extracted_folder(path):
    """Accept a dump root, or its exefs/romfs child. No guessing by game name."""
    path=pathlib.Path(path).expanduser()
    if path.name.lower() in ('exefs','romfs'):path=path.parent
    if not path.is_dir() or not (path/'exefs/main').is_file() or not (path/'romfs').is_dir():
        raise ValueError('Elegir la carpeta que contiene exefs/main y romfs.')
    return path.resolve()

def fetch_nstool(store,progress=print,cancel=None,fetch=None):
    """Download the pinned nstool release, check its SHA-256 and keep only its executable. No compiler is needed."""
    import zipfile
    from . import ports
    fetch=fetch or ports.download;folder=nstool_folder(store);folder.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.nstool-',dir=folder.parent) as temporary:
        work=pathlib.Path(temporary);archive=work/'nstool.zip'
        progress(f"Descargando nstool {NSTOOL['tag']}…");fetch(NSTOOL['url'],archive,limit=30*1024**2,cancel=cancel)
        if ports.sha256_file(archive)!=NSTOOL['sha256']:raise ValueError('La descarga de nstool no coincide con la suma SHA-256 esperada; no se guardó.')
        try:
            with zipfile.ZipFile(archive) as bundle:
                member=next((i for i in bundle.infolist() if i.filename=='nstool' and not i.is_dir()),None)
                if member is None:raise ValueError('El paquete de nstool no tiene la forma esperada.')
                (work/'nstool').write_bytes(bundle.read(member))
        except zipfile.BadZipFile:raise ValueError('El paquete de nstool no tiene la forma esperada.')
        (work/'nstool').chmod(0o755)
        if not is_nstool(work/'nstool'):raise RuntimeError('nstool descargado no se puede ejecutar en este equipo.')
        if folder.exists():shutil.rmtree(folder)
        folder.mkdir(parents=True);shutil.copy(work/'nstool',folder/'nstool');(folder/'nstool').chmod(0o755)
        atomic_json(folder/'build.json',{'tag':NSTOOL['tag'],'sha256':NSTOOL['sha256'],'date':time.strftime('%Y-%m-%dT%H:%M:%S')})
    return str(folder/'nstool')

def tool_path(store=None,preferences=None,home=None):
    """A working converter: nstool first (settings, PATH or the copy this app downloaded), then hactool (same places, or the copy this app built)."""
    preferences=preferences or {}
    nstools=[preferences.get('nstool_path'),shutil.which('nstool')]
    if store is not None:nstools.append(str(nstool_folder(store)/'nstool'))
    for candidate in nstools:
        if candidate and os.access(candidate,os.X_OK) and is_nstool(candidate):return str(candidate)
    candidates=[preferences.get('hactool_path'),shutil.which('hactool')]
    if store is not None:candidates.append(str(tool_folder(store)/'hactool'))
    for candidate in candidates:
        if candidate and os.access(candidate,os.X_OK) and is_hactool(candidate):return str(candidate)
    return bundled_tool()

def build_tool(store,progress=print,cancel=None,run=None,fetch=None):
    """Download the pinned hactool source, check its SHA-256 and compile it. Uses the KDE SDK when the system has no compiler."""
    from . import buildenv,ports
    run=run or buildenv.run;fetch=fetch or ports.download
    host=bool(shutil.which('gcc') and shutil.which('make'))
    if not host and not buildenv.installed():raise NeedsTool('Compilar la herramienta necesita el SDK de KDE (se instala sin permisos de administrador).')
    folder=tool_folder(store);folder.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.hactool-',dir=folder.parent) as temporary:
        work=pathlib.Path(temporary);archive=work/'hactool.tar.gz'
        progress(f"Descargando el código de hactool {HACTOOL['tag']}…");fetch(HACTOOL['url'],archive,limit=20*1024**2,cancel=cancel)
        if ports.sha256_file(archive)!=HACTOOL['sha256']:raise ValueError('La descarga de hactool no coincide con la suma SHA-256 esperada; no se compiló.')
        source=work/'source';source.mkdir();ports.extract(archive,source)
        root=next((p for p in source.iterdir() if p.is_dir()),None)
        if root is None or not (root/'Makefile').is_file():raise ValueError('El código descargado no tiene la forma esperada.')
        if (root/'config.mk.template').is_file():shutil.copy(root/'config.mk.template',root/'config.mk')
        progress('Compilando hactool…')
        run(['make','-j4'],cwd=str(root),progress=lambda line:progress(sanitize(line)),until=(lambda:cancel is not None and cancel.is_set()),sandbox=not host)
        binary=root/'hactool'
        if not binary.is_file() or not is_hactool(binary):raise RuntimeError('La compilación terminó pero el programa no responde como hactool.')
        if folder.exists():shutil.rmtree(folder)
        folder.mkdir(parents=True);shutil.copy(binary,folder/'hactool');(folder/'hactool').chmod(0o755)
        atomic_json(folder/'build.json',{'tag':HACTOOL['tag'],'commit':HACTOOL['commit'],'date':time.strftime('%Y-%m-%dT%H:%M:%S')})
    return str(folder/'hactool')

def parse_nstool_info(lines):
    """Content type, program ID, size and Rights ID from the header nstool prints for an NCA."""
    text='\n'.join(lines);info={}
    for key,pattern in (('type',r'Content Type:\s+(\w+)'),('title_id',r'ProgID:\s+0x([0-9a-fA-F]{16})'),('size',r'Size:\s+0x([0-9a-fA-F]+)'),('rights_id',r'RightsId:\s+([0-9a-fA-F]{32})')):
        match=re.search(pattern,text)
        if match:info[key]=match.group(1)
    if 'size' in info:info['size']=int(info['size'],16)
    for key in ('rights_id','title_id'):
        if key in info:info[key]=info[key].lower()
    return info

def parse_info(lines):
    """Content type, Title ID, size and Rights ID from `hactool -t nca -i` output."""
    text='\n'.join(lines);info={}
    for key,pattern in (('type',r'Content Type:\s+(\w+)'),('title_id',r'Title ID:\s+([0-9a-fA-F]{16})'),('size',r'Content Size:\s+0x([0-9a-fA-F]+)'),('rights_id',r'Rights ID:\s+([0-9a-fA-F]{32})')):
        match=re.search(pattern,text)
        if match:info[key]=match.group(1)
    if 'size' in info:info['size']=int(info['size'],16)
    if 'rights_id' in info:info['rights_id']=info['rights_id'].lower()
    if 'title_id' in info:info['title_id']=info['title_id'].lower()
    return info

class Job:
    """One conversion: private HOME for hactool, a staging folder next to the destination and a transactional swap at the end."""
    def __init__(self,tool,keys,progress=print,cancel=None,run=None):
        from . import buildenv
        self.tool=tool;self.backend=backend_of(tool);self.keys=check_keys(keys);self.progress=progress;self.cancel=cancel;self.run=run or buildenv.run;self.titlekeys={}
    def hactool(self,args,capture=None):
        from .ports import check_cancel
        check_cancel(self.cancel);lines=[]
        def line(text):
            lines.append(text)
            # hactool prints the whole header of every file it reads; only the files it writes are worth showing.
            if capture is None and text.startswith('Saving '):self.progress(sanitize('Guardando '+pathlib.PurePosixPath(text[7:].rsplit(' to ',1)[-1].rstrip('.')).name))
        from .runtime import clean_environment
        env=clean_environment({**os.environ,'HOME':str(self.home),'XDG_CONFIG_HOME':str(self.home/'.config')})
        command=[self.tool,'-k',self.keys,*args] if self.backend=='nstool' else [self.tool,'-k',self.keys,'--disablekeywarns','--suppresskeys',*args]
        try:self.run(command,progress=line,until=(lambda:self.cancel is not None and self.cancel.is_set()),sandbox=False,env=env)
        except RuntimeError as error:
            detail=sanitize(str(error))
            if self.backend=='nstool':raise ValueError('nstool no pudo procesar el archivo. Revisar que las claves sean de una versión de firmware igual o posterior a la del juego.\n'+detail)
            if 'BKTR' in detail:raise ValueError('hactool 1.4.0 no puede leer el formato de esta actualización (BKTR). Convertir solo el juego base o usar una actualización anterior.\n'+detail)
            raise ValueError('hactool no pudo procesar el archivo. Revisar que las claves sean de una versión de firmware igual o posterior a la del juego.\n'+detail)
        check_cancel(self.cancel)
        return lines
    def write_titlekeys(self):
        folder=self.home/'.switch';folder.mkdir(parents=True,exist_ok=True)
        path=folder/'title.keys';fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as stream:stream.write(''.join(f'{rights} = {key}\n' for rights,key in self.titlekeys.items()))
    def unpack(self,source,index):
        kind=container_kind(source);target=self.work/f'package-{index}';target.mkdir()
        self.progress('Leyendo '+pathlib.Path(source).name+'…')
        if self.backend=='nstool':self.hactool(['-x','/',str(target),str(source)] if kind=='nsp' else ['--secure',str(target),str(source)])
        else:self.hactool(['-t','pfs0','--pfs0dir='+str(target),str(source)] if kind=='nsp' else ['-t','xci','--securedir='+str(target),str(source)])
        for ticket in sorted(target.rglob('*.tik')):
            try:rights,key=parse_ticket(ticket.read_bytes())
            except ValueError as error:raise ValueError(f'{pathlib.Path(source).name}: {error}')
            self.titlekeys[rights]=key
        self.write_titlekeys()
        archives=sorted(p for p in target.rglob('*.nca') if not p.name.endswith('.cnmt.nca'))
        if not archives:raise ValueError(f'{pathlib.Path(source).name} no contiene datos de juego (NCA).')
        return archives
    def programs(self,archives):
        found=[]
        for path in archives:
            info=parse_nstool_info(self.hactool([str(path)],capture=True)) if self.backend=='nstool' else parse_info(self.hactool(['-t','nca','-i',str(path)],capture=True))
            if info.get('type')=='Program' and info.get('title_id'):found.append({**info,'path':path})
        return found
    def version(self,source):
        """Version of an NSP read from its small content-meta file alone (no full extraction); None when it cannot be told cheaply."""
        if container_kind(source)!='nsp' or self.backend!='nstool':return None
        try:
            found=pfs0_entry(source,'.cnmt.nca')
            if not found or found[2]>4*1024**2:return None
            name,offset,size=found;meta=pathlib.Path(tempfile.mkdtemp(prefix='meta-',dir=self.work));package=meta/'meta.nca'
            with open(source,'rb') as stream:stream.seek(offset);package.write_bytes(stream.read(size))
            target=meta/'out';target.mkdir();self.hactool(['-x','/0',str(target),str(package)],capture=True)
            record=next(target.rglob('*.cnmt'),None)
            return parse_cnmt(record.read_bytes())['version'] if record else None
        except (OSError,ValueError,struct.error):return None
    def check_minimum(self,source,update,minimum):
        label=minimum['label'];base=self.version(source);patch=self.version(update) if update else None
        if update and patch is not None and patch<minimum['version']:raise NeedsUpdate(f'La actualización elegida es anterior a la {label}. Elegir una actualización {label} o posterior.')
        if not update and base is not None and base<minimum['version']:raise NeedsUpdate(f'Este archivo es la versión base del juego. El port pide la actualización {label} o posterior: elegir también el archivo de la actualización.')
    def convert(self,source,root,update=None,minimum=None):
        """Extract `source` (and the patch in `update`, if any) into `root`/<Title ID>. Returns a summary.
        `minimum` ({'label','version'}) makes a game older than that version fail early, before the long extraction."""
        from .ports import check_cancel
        root=pathlib.Path(root).expanduser();root.mkdir(parents=True,exist_ok=True)
        if root.is_symlink():raise ValueError('La carpeta de destino es un enlace; no se modificó.')
        sizes=sum(pathlib.Path(p).stat().st_size for p in (source,update) if p)
        # NSP/XCI contents are copied once to read them and once more as exefs/romfs.
        need=int(sizes*2.1)+256*1024**2
        if shutil.disk_usage(root).free<need:raise ValueError(f'No hay espacio suficiente en la carpeta de destino (hacen falta unos {need/1024**3:.0f} GB libres).')
        with tempfile.TemporaryDirectory(prefix='.deck-library-switch-',dir=root) as temporary:
            self.work=pathlib.Path(temporary);self.home=self.work/'home';self.home.mkdir(mode=0o700)
            if minimum:self.check_minimum(source,update,minimum)
            base=self.programs(self.unpack(source,0));patch=None
            if update:patch=self.programs(self.unpack(update,1))
            if not base:raise ValueError('No se encontró el programa del juego en el archivo base. Puede ser solo una actualización o contenido descargable.')
            base_tid=sorted({p['title_id'] for p in base})[0];game=max((p for p in base if p['title_id']==base_tid),key=lambda p:p['size'])
            if patch is not None:
                expected=format(int(base_tid,16)+0x800,'016x');matching=[p for p in patch if p['title_id'] in (expected,base_tid)]  # a patch's NCA header may carry the base application's ID
                if not matching:raise ValueError('La actualización elegida no corresponde a este juego.')
                target=max(matching,key=lambda p:p['size'])
            else:target=game
            destination=root/base_tid
            if destination.is_symlink():raise ValueError('La carpeta del juego es un enlace; no se modificó.')
            if destination.exists() and any(destination.iterdir()) and not (destination/MANIFEST).is_file():raise ValueError(f'Ya existe una carpeta {base_tid} que no es una conversión de Deck Library. Moverla o elegir otro destino.')
            staged=self.work/'game';(staged/'exefs').mkdir(parents=True);(staged/'romfs').mkdir()
            self.progress('Extrayendo exefs y romfs…')
            if self.backend=='nstool':
                base_option=['--basenca',str(game['path'])] if patch is not None else []
                self.hactool([*base_option,'-x','/0',str(staged/'exefs'),str(target['path'])]);self.hactool([*base_option,'-x','/1',str(staged/'romfs'),str(target['path'])])
            else:self.hactool(['-t','nca','--exefsdir='+str(staged/'exefs'),'--romfsdir='+str(staged/'romfs'),*(['--basenca='+str(game['path'])] if patch is not None else []),str(target['path'])])
            files,size=validate(staged)
            check_cancel(self.cancel)
            receipt={'schema':1,'title_id':base_tid,'title':KNOWN_TITLES.get(base_tid,''),'sources':[pathlib.Path(source).name]+([pathlib.Path(update).name] if update else []),'update':bool(update),'tool':({'name':'nstool','tag':NSTOOL['tag']} if self.backend=='nstool' else {'name':'hactool','tag':HACTOOL['tag'],'commit':HACTOOL['commit']}),'files':files,'size':size,'date':time.strftime('%Y-%m-%dT%H:%M:%S')}
            atomic_json(staged/MANIFEST,receipt)
            backup=None
            if destination.exists():
                backup=root/'.deck-library-original-backups'/str(time.time_ns())
                if backup.parent.is_symlink():raise ValueError('La carpeta de respaldo es un enlace; no se modificó.')
                backup.parent.mkdir(exist_ok=True);destination.rename(backup)
            try:staged.rename(destination)
            except BaseException:
                if backup:backup.rename(destination)
                raise
        return {'path':str(destination),**{k:receipt[k] for k in ('title_id','title','files','size','update')}}

def validate(folder):
    """(file count, bytes) of an extracted folder, or an error when exefs/main or romfs is missing."""
    folder=pathlib.Path(folder);main=folder/'exefs/main'
    if not main.is_file() or main.stat().st_size==0 or not (folder/'exefs/main.npdm').is_file():raise ValueError('La extracción no produjo exefs/main. El juego puede requerir claves de un firmware más reciente.')
    files=size=0
    for path in (folder/'romfs').rglob('*'):
        if path.is_file() and not path.is_symlink():files+=1;size+=path.stat().st_size
    if not files:raise ValueError('La extracción no produjo archivos en romfs. Si se eligió una actualización, comprobar que sea la del mismo juego.')
    return files,size

def details(folder):
    """The receipt of a conversion made by this app, or None."""
    path=pathlib.Path(folder)/MANIFEST
    if path.is_symlink():return None
    try:data=json.loads(path.read_text())
    except (OSError,ValueError):return None
    return data if isinstance(data,dict) and data.get('schema')==1 else None

def default_root(home=None):
    """Where converted games go unless the user picks another folder; each game gets its Title ID as subfolder."""
    from . import layout
    return layout.folder('switch',home)
