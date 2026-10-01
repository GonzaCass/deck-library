from dataclasses import dataclass, field, asdict
import hashlib,json,os,pathlib,tempfile,re

@dataclass
class Entry:
    name: str
    command: list[str]
    kind: str = 'port'
    platform: str = 'Linux'
    source: str = ''
    cwd: str = ''
    icon: str = ''
    mods: bool = True
    id: str = ''
    game_id: str = ''
    cover: str = ''
    metadata: dict = field(default_factory=dict)
    def __post_init__(self):
        if not self.name.strip() or not self.command or not self.command[0].strip() or not all(isinstance(a,str) and '\0' not in a for a in self.command):
            raise ValueError('Nombre o comando inválido.')
        if not self.id:
            self.id=hashlib.sha256(json.dumps([self.kind,self.command,self.mods],ensure_ascii=False).encode()).hexdigest()[:20]
        if not re.fullmatch(r'[a-f0-9]{20}',self.id):raise ValueError('Identificador de juego inválido.')
        if not self.cwd: self.cwd=str(pathlib.Path(self.source).parent if self.source else pathlib.Path.home())
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls,value): return cls(**value)

def atomic_json(path,value):
    path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,name=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(value,f,indent=2,ensure_ascii=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)

class Store:
    def __init__(self,root=None):
        self.root=pathlib.Path(root or pathlib.Path(os.environ.get('XDG_DATA_HOME',pathlib.Path.home()/'.local/share'))/'deck-library')
        self.path=self.root/'library.json'
    def load(self):
        if not self.path.exists(): return []
        data=json.loads(self.path.read_text())
        if data.get('schema')!=1: raise ValueError('Versión de biblioteca no reconocida; se conservó el archivo.')
        return [Entry.from_dict(v) for v in data['entries']]
    def save(self,entries): atomic_json(self.path,{'schema':1,'entries':[e.to_dict() for e in entries]})
    def merge(self,entries,overwrite=True):
        existing={e.id:e for e in self.load()}
        for e in entries:
            match=next((old for old in existing.values() if old.kind==e.kind and old.command==e.command),None)
            if not match and e.source:
                match=next((old for old in existing.values() if old.kind==e.kind and old.platform==e.platform and old.source==e.source),None)
                if match and not match.metadata.get('manual_command'):match.command=e.command
            if match:e.id=match.id
            if overwrite or e.id not in existing:existing[e.id]=e
            else:
                old=existing[e.id]
                if not old.game_id:old.game_id=e.game_id
                if not old.cover:old.cover=e.cover
                old.metadata={**e.metadata,**old.metadata}
                for key in ('emulator_version','version','build'):
                    if e.metadata.get(key):old.metadata[key]=e.metadata[key]
        self.save(list(existing.values())); return list(existing.values())
