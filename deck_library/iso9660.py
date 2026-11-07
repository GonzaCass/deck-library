"""Read-only ISO 9660 extraction, in Python: PlayStation 3 disc images (decrypted dumps) and other plain data discs.

Same interface as xdvdfs.Image. Files are copied and verified one by one; nothing outside the destination is touched."""
import dataclasses,hashlib,pathlib,struct

SECTOR=2048
LIMIT=96*1024**3

@dataclasses.dataclass(frozen=True)
class Member:
    path:str
    extents:tuple
    size:int

def fingerprint(stat):
    return {key:getattr(stat,'st_'+key) for key in ('dev','ino','size','mtime_ns','ctime_ns')}

def sniff(path):
    """'ps3' for a PlayStation 3 disc image, 'iso9660' for another data disc, '' when the file is not an ISO 9660 image (reads 36 KiB at most)."""
    try:
        with open(path,'rb') as stream:head=stream.read(0x8800)
    except OSError:return ''
    if len(head)<0x8800 or head[0x8001:0x8006]!=b'CD001':return ''
    return 'ps3' if b'PS3VOLUME' in head[0x8000:0x8800] or b'PS3_DISC' in head[0x8000:0x8800] else 'iso9660'

class Image:
    def __init__(self,path,cancel=None):
        self.path=pathlib.Path(path);self.cancel=cancel;self.stream=None

    def __enter__(self):
        import os
        self.stream=self.path.open('rb');self.identity=fingerprint(os.fstat(self.stream.fileno()));self.size=self.identity['size'];self.kind=sniff(self.path)
        try:self._index()
        except BaseException:self.stream.close();raise
        return self

    def __exit__(self,*_):self.stream.close()

    def read(self,offset,size):
        from .ports import check_cancel
        check_cancel(self.cancel)
        if offset<0 or size<0 or offset+size>self.size:raise ValueError('La ISO está truncada o contiene una ruta de datos inválida.')
        self.stream.seek(offset);data=self.stream.read(size)
        if len(data)!=size:raise ValueError('La ISO está truncada o contiene una ruta de datos inválida.')
        return data

    def unchanged(self):
        import os
        if fingerprint(os.fstat(self.stream.fileno()))!=self.identity or fingerprint(self.path.stat())!=self.identity:raise ValueError('La ISO cambió durante la preparación. Se conservó el original.')

    def _volume(self):
        """The volume descriptor to read names from: Joliet when the disc has one (long names), the primary one otherwise."""
        primary=joliet=None;sector=16
        while sector<64 and (sector+1)*SECTOR<=self.size:
            block=self.read(sector*SECTOR,SECTOR)
            if block[1:6]!=b'CD001':break
            kind=block[0]
            if kind==255:break
            if kind==1 and primary is None:primary=block
            if kind==2 and block[88:91] in (b'%/@',b'%/C',b'%/E'):joliet=block
            sector+=1
        if primary is None:raise ValueError('No se encontró un sistema de archivos ISO 9660 válido en la imagen.')
        return primary,joliet

    def _index(self):
        primary,joliet=self._volume();volume=joliet or primary;unicode_names=joliet is not None
        self.block=struct.unpack_from('<H',primary,128)[0]
        if self.block not in (512,1024,2048,4096):raise ValueError('El tamaño de bloque de la ISO no es válido.')
        self.encrypted=self.read(0xF70,16)[:12]==b'Encrypted 3K'
        record=volume[156:190];start=struct.unpack_from('<I',record,2)[0];length=struct.unpack_from('<I',record,10)[0]
        self.files=[];self.directories=[];self.skipped=[];pending=[(start,length,'',0)];names=set();nodes=0;visited=set()
        while pending:
            start,length,parent,depth=pending.pop()
            if depth>64 or len(parent)>4096:raise ValueError('La ISO contiene demasiados niveles de carpetas.')
            if not length or length>64*1024**2 or (start,length) in visited or start*self.block+length>self.size:raise ValueError('El índice de carpetas de la ISO es inválido.')
            visited.add((start,length));table=self.read(start*self.block,length);position=0;extents=[];held=None
            while position<length:
                size=table[position]
                if not size:position=(position//self.block+1)*self.block;continue
                if position+size>length or size<34:raise ValueError('El índice de carpetas de la ISO es inválido.')
                nodes+=1
                if nodes>400000:raise ValueError('El índice de carpetas de la ISO es inválido.')
                extent=struct.unpack_from('<I',table,position+2)[0];span=struct.unpack_from('<I',table,position+10)[0];flags=table[position+25];count=table[position+32]
                if position+33+count>position+size:raise ValueError('El índice de carpetas de la ISO es inválido.')
                raw=table[position+33:position+33+count];position+=size
                if raw in (b'\x00',b'\x01'):continue
                try:name=raw.decode('utf-16-be') if unicode_names else raw.decode('utf-8')
                except UnicodeDecodeError:
                    try:name=raw.decode('cp1252')
                    except UnicodeDecodeError:raise ValueError('La ISO contiene un nombre de archivo inválido.') from None
                if not flags&2:name=name.split(';')[0]
                if name.endswith('.') and len(name)>1:name=name[:-1]
                if name in ('.','..') or not name or any(c in '/\\:\x00' or ord(c)<32 for c in name):raise ValueError('La ISO contiene un nombre de archivo inválido.')
                path=(parent+'/'+name).lstrip('/')
                if flags&2:
                    key=path.casefold()
                    if key in names:raise ValueError('La ISO contiene rutas duplicadas.')
                    names.add(key);self.directories.append(path);pending.append((extent,span,path,depth+1));continue
                # A file larger than 4 GiB is split into several records that share one name; the last one has no continuation flag.
                held=(held[0],held[1]+[(extent,span)]) if held and held[0]==path else (path,[(extent,span)])
                if flags&0x80:continue
                key=path.casefold()
                if key in names:raise ValueError('La ISO contiene rutas duplicadas.')
                names.add(key);spans=tuple((e*self.block,s) for e,s in held[1]);held=None
                if any(offset+s>self.size for offset,s in spans):raise ValueError('La ISO está truncada o contiene una ruta de datos inválida.')
                self.files.append(Member(path,spans,sum(s for _,s in spans)))
            if held:raise ValueError('El índice de carpetas de la ISO es inválido.')
        self.total=sum(m.size for m in self.files)
        if not self.files:raise ValueError('La ISO no contiene archivos.')
        if self.total>LIMIT:raise ValueError('El tamaño extraído de la ISO supera el límite admitido.')

    def verify_ps3(self):
        """Refuse what cannot work as a game folder: encrypted dumps and discs without the PS3_GAME folder."""
        if self.encrypted:raise ValueError('Esta ISO de PS3 está cifrada. Hace falta descifrarla antes de extraerla; Deck Library no incluye ni pide claves.')
        paths={m.path.casefold() for m in self.files}
        if 'ps3_game/param.sfo' not in paths:raise ValueError('La ISO no contiene la carpeta PS3_GAME del juego.')

    def extract(self,destination,progress=lambda event:None):
        from .ports import check_cancel
        target=pathlib.Path(destination);target.mkdir()
        for directory in self.directories:(target/directory).mkdir(parents=True,exist_ok=True)
        done=0;manifest=[];total=self.total*2
        def update():progress({'phase':'extract','done':done,'total':total})
        update()
        for member in self.files:
            path=target/member.path;path.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256()
            with path.open('xb') as output:
                for offset,span in member.extents:
                    for step in range(0,span,1024*1024):
                        block=self.read(offset+step,min(1024*1024,span-step));output.write(block);digest.update(block);done+=len(block);update()
            verify=hashlib.sha256()
            with path.open('rb') as copied:
                while block:=copied.read(1024*1024):check_cancel(self.cancel);verify.update(block);done+=len(block);update()
            if verify.digest()!=digest.digest():raise ValueError('La verificación de los archivos extraídos falló. Se conservó la ISO.')
            manifest.append({'path':member.path,'size':member.size,'sha256':digest.hexdigest()})
        self.unchanged();check_cancel(self.cancel)
        return manifest
