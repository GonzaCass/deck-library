"""Read-only XDVDFS extraction, in Python, for full Xbox discs and trimmed XISOs.

Format reference: XboxDev/extract-xiso. No external installer or compiler is run.
"""
import dataclasses,hashlib,pathlib,struct

MAGIC=b'MICROSOFT*XBOX*MEDIA'
SECTOR=2048
BASES=(0,0xFD90000,0x2080000,0x18300000)

def fingerprint(stat):
    return {key:getattr(stat,'st_'+key) for key in ('dev','ino','size','mtime_ns','ctime_ns')}

@dataclasses.dataclass(frozen=True)
class Member:
    path:str
    offset:int
    size:int

class Image:
    def __init__(self,path,cancel=None):
        self.path=pathlib.Path(path);self.cancel=cancel;self.stream=None

    def __enter__(self):
        import os
        self.stream=self.path.open('rb');self.identity=fingerprint(os.fstat(self.stream.fileno()));self.size=self.identity['size']
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

    def _index(self):
        header=None
        for base in BASES:
            if base+0x10000+SECTOR>self.size:continue
            data=self.read(base+0x10000,SECTOR)
            if data[:20]==MAGIC and data[-20:]==MAGIC:self.base=base;header=data;break
        if header is None:raise ValueError('No se encontró un sistema de archivos Xbox válido en la ISO.')
        sector,size=struct.unpack_from('<II',header,20)
        self.files=[];self.directories=[];self.skipped=[];pending=[(sector,size,'',0)]
        visited=set();names=set();metadata=0;nodes=0
        while pending:
            sector,size,parent,depth=pending.pop()
            if depth>64 or len(parent)>4096:raise ValueError('La ISO contiene demasiados niveles de carpetas.')
            if not size:
                if parent:continue
                raise ValueError('La ISO no contiene archivos del juego.')
            if size>16*1024**2 or metadata+size>64*1024**2 or (sector,size) in visited:raise ValueError('El índice de carpetas de la ISO es inválido.')
            visited.add((sector,size));metadata+=size
            table=self.read(self.base+sector*SECTOR,size);todo=[0];seen=set()
            while todo:
                position=todo.pop();nodes+=1
                if nodes>200000 or position in seen or position%4 or position+14>size:raise ValueError('El índice de carpetas de la ISO es inválido.')
                seen.add(position)
                if table[position:position+2]==b'\xff\xff':
                    if not position:break  # An empty directory has a padded first sector.
                    following=(position//SECTOR+1)*SECTOR
                    if following>=size:raise ValueError('El índice de carpetas de la ISO es inválido.')
                    todo.append(following);continue
                left,right,start,length,attributes,count=struct.unpack_from('<HHIIBB',table,position)
                if not count or position+14+count>size:raise ValueError('El índice de carpetas de la ISO es inválido.')
                raw=table[position+14:position+14+count]
                try:name=raw.decode('utf-8')
                except UnicodeDecodeError:
                    try:name=raw.decode('cp1252')
                    except UnicodeDecodeError:raise ValueError('La ISO contiene un nombre de archivo inválido.') from None
                if name in ('.','..') or name!=name.rstrip(' .') or any(c in '/\\:\x00' or ord(c)<32 for c in name):raise ValueError('La ISO contiene un nombre de archivo inválido.')
                path=(parent+'/'+name).lstrip('/');key=path.casefold()
                if key in names:raise ValueError('La ISO contiene rutas duplicadas.')
                names.add(key)
                if left:todo.append(left*4)
                if right:todo.append(right*4)
                if not parent and key=='$systemupdate':self.skipped.append(path);continue
                offset=self.base+start*SECTOR
                if attributes&0x10:
                    self.directories.append(path);pending.append((start,length,path,depth+1))
                else:
                    if offset+length>self.size:raise ValueError('La ISO está truncada o contiene una ruta de datos inválida.')
                    self.files.append(Member(path,offset,length))
        self.total=sum(m.size for m in self.files)
        if self.total>32*1024**3 or self.total>self.size*4:raise ValueError('El tamaño extraído de la ISO supera el límite admitido.')

    def verify_game(self,spec):
        member=next((m for m in self.files if m.path.casefold()=='default.xex'),None)
        if member is None:raise ValueError('La ISO no contiene default.xex en la raíz del juego.')
        head=self.read(member.offset,min(member.size,1024*1024+16));title=None
        if len(head)>=24 and head[:4]==b'XEX2':
            count=struct.unpack_from('>I',head,20)[0]
            if count<=4096 and 24+8*count<=len(head):
                for key,offset in struct.iter_unpack('>II',head[24:24+8*count]):
                    if key==0x40006 and offset>=24+8*count and offset+16<=len(head):title=struct.unpack_from('>I',head,offset+12)[0];break
        if title!=int(spec['title_id'],16):raise ValueError('La ISO no corresponde al juego de Xbox 360 requerido por este port.')
        if spec.get('sha256'):
            digest=hashlib.sha256()
            for offset in range(0,member.size,1024*1024):digest.update(self.read(member.offset+offset,min(1024*1024,member.size-offset)))
            if digest.hexdigest() not in spec['sha256']:raise ValueError('default.xex no coincide con la revisión admitida por el port.')

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
                for offset in range(0,member.size,1024*1024):
                    block=self.read(member.offset+offset,min(1024*1024,member.size-offset));output.write(block);digest.update(block);done+=len(block);update()
            verify=hashlib.sha256()
            with path.open('rb') as copied:
                while block:=copied.read(1024*1024):check_cancel(self.cancel);verify.update(block);done+=len(block);update()
            if verify.digest()!=digest.digest():raise ValueError('La verificación de los archivos extraídos falló. Se conservó la ISO.')
            manifest.append({'path':member.path,'size':member.size,'sha256':digest.hexdigest()})
        self.unchanged();check_cancel(self.cancel)
        return manifest
