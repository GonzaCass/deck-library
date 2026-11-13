"""Reader for NUP (NX Package) containers: unencrypted Switch 1 and Switch 2 dumps packed as base, updates and add-ons.

Clean-room implementation of the public format specification (v1, magic `NUP\\x01`, MIT,
https://github.com/a55uka/nup). Nothing is decrypted and no key is used: NUP content is plaintext.
Every offset is bounds-checked, the table of contents is verified by its SHA-256 before it is trusted,
file names are labels (never paths) and each extracted file is checked against its SHA-256.
"""
import hashlib,pathlib,re,shutil,struct,subprocess,tempfile,threading

MAGIC=b'NUP\x01'
TOC_MAGIC=b'TOC\x01'
SUPERBLOCK=struct.Struct('<4sHHQQ32sQQII16s32s')
TOC_HEAD=struct.Struct('<4sIQQQQQ')
PACKAGE=struct.Struct('<QIIIIBBHIQI20s')
DIR=struct.Struct('<IIIIQ')
FILE=struct.Struct('<IIQQQ32sBBH12s')
NONE=0xFFFFFFFF
KINDS={0:'base',1:'update',2:'addon',3:'addon_update',4:'system'}
TOC_LIMIT=256*1024*1024
META_LIMIT=64*1024*1024
CHUNK=1<<20
TLV_VERSION,TLV_TITLE,TLV_PUBLISHER,TLV_ICON=4,5,6,3

def sniff(path):
    try:
        with open(path,'rb') as handle:return handle.read(4)==MAGIC
    except OSError:return False

def version_text(value):
    return f'{value>>16}.{(value>>8)&0xFF}.{value&0xFF}'

def safe_label(name):
    """A NUP name is one path component. Anything that could climb or address another place is refused."""
    if not name or name in ('.','..') or '/' in name or '\\' in name or '\x00' in name or len(name.encode())>255:
        raise ValueError('El NUP contiene un nombre de archivo no válido: '+repr(name[:60]))
    return name

class Container:
    """An opened .nup file. Use as a context manager."""
    def __init__(self,path,cancel=None):
        self.path=pathlib.Path(path);self.cancel=cancel;self.handle=open(self.path,'rb')
        try:self._load()
        except BaseException:self.handle.close();raise
    def __enter__(self):return self
    def __exit__(self,*_):self.handle.close()

    def _read(self,offset,size):
        self.handle.seek(offset);data=self.handle.read(size)
        if len(data)!=size:raise ValueError('El NUP está incompleto o dañado.')
        return data

    def _load(self):
        actual=self.path.stat().st_size
        if actual<SUPERBLOCK.size:raise ValueError('No es un archivo NUP.')
        (magic,header_size,_header_version,toc_offset,toc_size,toc_hash,blob_offset,file_size,
         package_count,flags,self.uuid,_reserved)=SUPERBLOCK.unpack(self._read(0,SUPERBLOCK.size))
        if magic!=MAGIC:raise ValueError('No es un archivo NUP (o es de una versión que no se admite).')
        if header_size<0x80 or toc_offset!=header_size:raise ValueError('La cabecera del NUP no es válida.')
        if flags:raise ValueError('El NUP usa opciones que esta versión no admite.')
        if file_size!=actual:raise ValueError('El tamaño del NUP no coincide con su cabecera: el archivo está incompleto.')
        if blob_offset%16 or blob_offset<toc_offset+toc_size or blob_offset>file_size:raise ValueError('Las regiones del NUP se superponen.')
        if not 0<toc_size<=TOC_LIMIT:raise ValueError('El índice del NUP tiene un tamaño no válido.')
        if package_count<1:raise ValueError('El NUP no contiene paquetes.')
        toc=self._read(toc_offset,toc_size)
        if hashlib.sha256(toc).digest()!=toc_hash:raise ValueError('El índice del NUP no coincide con su SHA-256: el archivo está dañado.')
        self.blob_offset,self.file_size=blob_offset,file_size
        if len(toc)<TOC_HEAD.size:raise ValueError('El índice del NUP está incompleto.')
        toc_magic,count,dir_count,file_count,pool_off,pool_size,_=TOC_HEAD.unpack_from(toc,0)
        if toc_magic!=TOC_MAGIC or count!=package_count:raise ValueError('El índice del NUP no es válido.')
        position=TOC_HEAD.size
        def records(layout,amount):
            nonlocal position
            end=position+layout.size*amount
            if amount>len(toc) or end>len(toc):raise ValueError('El índice del NUP declara más registros de los que contiene.')
            values=[layout.unpack_from(toc,position+i*layout.size) for i in range(amount)];position=end;return values
        packages=records(PACKAGE,package_count);dirs=records(DIR,dir_count);files=records(FILE,file_count)
        if pool_off<position or pool_off+pool_size>len(toc):raise ValueError('Los nombres del NUP están fuera de su índice.')
        pool=toc[pool_off:pool_off+pool_size]
        slots=sum(d[3] for d in dirs)
        if position+4*slots>pool_off:raise ValueError('El índice del NUP no es válido.')
        self.children=struct.unpack_from(f'<{slots}I',toc,position) if slots else ()
        def name(offset,length):
            if offset+length>len(pool):raise ValueError('Un nombre del NUP está fuera de su índice.')
            try:return pool[offset:offset+length].decode('utf-8')
            except UnicodeDecodeError:raise ValueError('Un nombre del NUP no es UTF-8 válido.') from None
        self.dirs=[]
        for name_off,name_len,first,child_count,_ in dirs:
            if first+child_count>slots:raise ValueError('Una carpeta del NUP apunta fuera de su índice.')
            self.dirs.append({'name':name(name_off,name_len),'first':first,'count':child_count})
        self.files=[]
        for name_off,name_len,size,extent_offset,extent_size,digest,codec,_codec_flags,_,_ in files:
            if codec not in (0,1):raise ValueError(f'El NUP usa una compresión que no se admite (códec {codec}).')
            if size==0 and extent_size==0:pass
            elif extent_offset%16 or extent_offset<blob_offset or extent_offset+extent_size>file_size:raise ValueError('Un archivo del NUP apunta fuera de sus datos.')
            elif codec==0 and extent_size!=size:raise ValueError('Un archivo sin comprimir del NUP declara un tamaño incoherente.')
            self.files.append({'name':name(name_off,name_len),'size':size,'offset':extent_offset,'stored':extent_size,'sha256':digest,'codec':codec})
        self.packages=[]
        for title_id,root,exefs,romfs,version,kind,pflags,_,_,meta_offset,meta_size,_ in packages:
            if kind>=5:raise ValueError('El NUP contiene un tipo de paquete desconocido.')
            for index in (root,exefs,romfs):
                if index!=NONE and index>=len(self.dirs):raise ValueError('Un paquete del NUP apunta a una carpeta inexistente.')
            if root==NONE:raise ValueError('Un paquete del NUP no tiene carpeta raíz.')
            meta=self._meta(meta_offset,meta_size)
            self.packages.append({'title_id':f'{title_id:016X}','kind':KINDS.get(kind,'reserved'),'version':version,'standalone':bool(pflags&1),'root':root,
                                  'display_version':meta.get(TLV_VERSION) or version_text(version),'title':meta.get(TLV_TITLE,''),'publisher':meta.get(TLV_PUBLISHER,'')})
        if sum(p['kind']=='base' for p in self.packages)>1:raise ValueError('El NUP contiene más de un juego base.')

    def _meta(self,offset,size):
        if not offset or not size:return {}
        if size>META_LIMIT or offset<SUPERBLOCK.size or offset+size>self.file_size:raise ValueError('Los datos del juego en el NUP están fuera del archivo.')
        data=self._read(offset,size);values={};position=0
        while position+8<=len(data):
            kind,_,length=struct.unpack_from('<HHI',data,position);position+=8
            if position+length>len(data):break
            if kind in (TLV_VERSION,TLV_TITLE,TLV_PUBLISHER):
                values[kind]=data[position:position+length].decode('utf-8','replace').strip()[:200]
            position+=length
        return values

    @property
    def title(self):
        for package in sorted(self.packages,key=lambda p:p['kind']!='base'):
            if package['title']:return package['title']
        return self.packages[0]['title_id']

    @property
    def total(self):return sum(f['size'] for f in self.files)

    def walk(self,directory):
        """(relative path parts, file record) for every file under a directory. Each folder is visited once, so a malformed tree cannot loop."""
        stack=[(directory,())];seen=set()
        while stack:
            index,prefix=stack.pop()
            if index in seen:raise ValueError('El árbol de carpetas del NUP no es válido.')
            seen.add(index);entry=self.dirs[index];names=set()
            for node in self.children[entry['first']:entry['first']+entry['count']]:
                if node<len(self.dirs):
                    label=safe_label(self.dirs[node]['name']);stack.append((node,prefix+(label,)))
                elif node-len(self.dirs)<len(self.files):
                    record=self.files[node-len(self.dirs)];label=safe_label(record['name']);yield prefix+(label,),record
                else:raise ValueError('Una carpeta del NUP apunta a un archivo inexistente.')
                if label in names:raise ValueError('Una carpeta del NUP repite un nombre: '+label)
                names.add(label)

    def plan(self,merge=True):
        """Destination path parts → file record.
        merge=True: the base game with its newest update laid over it (later files shadow earlier ones), in one exefs/romfs tree, which is what
        ports and emulators load from a folder; add-ons go to dlc/<title id>/. merge=False keeps every package apart:
        base/, updates/<version>/ and dlc/<title id>/, like the NUP Extractor's full dump."""
        result={};updates=sorted((p for p in self.packages if p['kind']=='update'),key=lambda p:p['version'])
        def add(package,prefix):
            for parts,record in self.walk(package['root']):result[prefix+parts]=record
        base=[p for p in self.packages if p['kind']=='base']
        if merge:
            for package in base+updates[-1:]:add(package,())
        else:
            for package in base:add(package,('base',))
            for package in updates:add(package,('updates',re.sub(r'[^\w.\-]+','_',package['display_version']) or str(package['version'])))
        for package in self.packages:
            if package['kind'] in ('addon','addon_update'):add(package,('dlc',package['title_id']))
        return result

    def chunks(self,record):
        """The uncompressed content of one file, in pieces, stopping as soon as it would exceed its declared size."""
        if record['size']==0 and record['stored']==0:return  # empty files have no extent, whatever codec is recorded
        remaining=record['stored'];self.handle.seek(record['offset'])
        def stored():
            nonlocal remaining
            while remaining:
                if self.cancel is not None and self.cancel.is_set():
                    from .ports import Cancelled
                    raise Cancelled('Cancelado')
                block=self.handle.read(min(CHUNK,remaining))
                if not block:raise ValueError('El NUP está incompleto o dañado.')
                remaining-=len(block);yield block
        if record['codec']==0:yield from stored();return
        yield from decompress(stored(),record['size'])

def decompress(blocks,size):
    """One zstd frame, with output bounded by the declared size. Uses Python's zstd when present (3.14+), else the zstd program."""
    try:from compression import zstd
    except ImportError:zstd=None
    produced=0
    def bound(data):
        nonlocal produced
        produced+=len(data)
        if produced>size:raise ValueError('Un archivo del NUP se descomprime en más datos de los declarados.')
        return data
    if zstd is not None:
        engine=zstd.ZstdDecompressor()
        for block in blocks:
            data=engine.decompress(block,max_length=CHUNK)
            if data:yield bound(data)
            while not engine.eof and not engine.needs_input:
                data=engine.decompress(b'',max_length=CHUNK)
                if not data:break
                yield bound(data)
        if not engine.eof:raise ValueError('Un archivo comprimido del NUP está incompleto.')
        return
    tool=shutil.which('zstd')
    if not tool:raise ValueError('Para extraer este NUP hace falta zstd (viene con SteamOS) o Python 3.14.')
    process=subprocess.Popen([tool,'-d','-q','-c'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    failure=[]
    def feed():
        try:
            for block in blocks:process.stdin.write(block)
        except BrokenPipeError:pass
        except BaseException as error:failure.append(error)
        finally:
            try:process.stdin.close()
            except OSError:pass
    writer=threading.Thread(target=feed,daemon=True);writer.start()
    try:
        while True:
            data=process.stdout.read(CHUNK)
            if not data:break
            yield bound(data)
    except BaseException:
        process.kill();raise
    finally:
        writer.join();process.wait()
    if failure:raise failure[0]
    if process.returncode:raise ValueError('No se pudo descomprimir un archivo del NUP.')

def extract_folder(source,root,progress=lambda event:None,cancel=None,merge=True):
    """Extract a .nup into root/<container name>, verifying every file. The NUP is only read; the folder appears once all files are checked.
    Returns {'path','files','size','title','packages'}."""
    from .diskspace import ensure_space
    from .ports import check_cancel
    source=pathlib.Path(source).resolve();root=pathlib.Path(root).expanduser();root.mkdir(parents=True,exist_ok=True)
    if root.is_symlink():raise ValueError('La carpeta de destino es un enlace; no se modificó.')
    name=re.sub(r'[^\w.\- ]+','_',source.stem).strip(' ._') or 'nup';destination=root/name
    if destination.is_symlink():raise ValueError('La carpeta de destino es un enlace; no se modificó.')
    if destination.exists() and any(destination.iterdir()):raise ValueError(f'La carpeta {name} ya existe y no está vacía. Elegir otro destino o moverla.')
    with Container(source,cancel) as container:
        plan=container.plan(merge);total=sum(r['size'] for r in plan.values());done=0
        ensure_space(total,root)
        with tempfile.TemporaryDirectory(prefix='.deck-library-nup-',dir=root) as temporary:
            staged=pathlib.Path(temporary)/'game';staged.mkdir()
            for parts,record in sorted(plan.items()):
                check_cancel(cancel)
                target=staged.joinpath(*parts);target.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256();written=0
                with open(target,'wb') as output:
                    for block in container.chunks(record):
                        output.write(block);digest.update(block);written+=len(block);done+=len(block);progress({'done':done,'total':total})
                if written!=record['size'] or digest.digest()!=record['sha256']:raise ValueError('El archivo '+'/'.join(parts)+' no coincide con su SHA-256: el NUP está dañado. No se extrajo nada.')
            check_cancel(cancel)
            if destination.exists():destination.rmdir()
            staged.rename(destination)
        return {'path':str(destination),'files':len(plan),'size':total,'title':container.title,
                'packages':[{k:p[k] for k in ('kind','title_id','display_version')} for p in container.packages]}
