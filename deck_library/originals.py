"""Associate original images with ready ports without changing either entry or file."""
import pathlib,re
from .library_view import title_key,entry_type
from .models import atomic_json
ALIASES={'crashteamracingturbocharged':'crashteamracing','ctrcrashteamracing':'crashteamracing','crashteamracing':'crashteamracing','mariokartwiicompiled':'mariokartwii'}
def key(name):
    name=str(name or '')
    name=re.sub(r'^(.+?),\s*(The|A|An)(\s*[-:]\s*|$)',r'\2 \1\3',name,flags=re.I)
    value=re.sub(r'[^a-z0-9]','',title_key(name));return ALIASES.get(value,value)

def platform_key(name):
    value=re.sub(r'[^a-z0-9]','',name.lower().replace(' ports',''))
    return {'ps1':'playstation','psx':'playstation','ps2':'playstation2','ps3':'playstation3','ps4':'playstation4','n64':'nintendo64','gcn':'gamecube','gc':'gamecube','x360':'xbox360','gba':'gameboyadvance','snes':'supernintendo'}.get(value,value)

def original_platform(port):
    value=port.metadata.get('original_platform','')
    if value:return platform_key(value)
    if port.kind=='wiicompiled' or port.metadata.get('adapter')=='wiicompiled':return 'wii'
    if port.metadata.get('adapter')=='project2099':return 'xbox360'
    if re.search(r'\bps1\b',port.name,re.I):return 'playstation'
    return ''

def pairs(entries,excluded=()):
    result=[];ports=[e for e in entries if entry_type(e)=='port' and e.metadata.get('configured') is not False]
    title_platforms={}
    for e in entries:
        if entry_type(e)=='emulator':title_platforms.setdefault(key(e.name),set()).add(platform_key(e.platform))
    for original in entries:
        if entry_type(original)!='emulator' or original.id in excluded:continue
        matches=[]
        for port in ports:
            platform=original_platform(port)
            if platform and platform!=platform_key(original.platform):continue
            if original.game_id and port.game_id:
                if original.game_id.upper()==port.game_id.upper():matches.append(port)
                continue
            title=key(original.name)
            if not title or not platform and len(title_platforms.get(title,()))>1:continue
            if title in {key(port.name),key(port.metadata.get('game_title',''))}:matches.append(port)
        if matches:result.append((original,matches))
    return result

def associations(entries,excluded=()):
    linked={}
    for original,ports in pairs(entries,excluded):
        for port in ports:linked.setdefault(port.id,[]).append(original)
    return linked

def rom_caption(originals):
    available=sum(bool(e.source and pathlib.Path(e.source).is_file()) for e in originals)
    if not originals:return ''
    return ('ROM encontrada' if available==1 else str(available)+' ROMs encontradas') if available else 'ROM no disponible'

def files_for(entry,entries):
    path=pathlib.Path(entry.source)
    if not path.is_file() or path.is_symlink():raise ValueError('El original no es un archivo local disponible o es un enlace.')
    files=[path]
    if path.suffix.lower()=='.cue':
        for name in re.findall(r'^\s*FILE\s+"([^"]+)"',path.read_text(errors='replace'),re.I|re.M):
            child=(path.parent/name)
            if child.is_symlink() or child.parent.resolve()!=path.parent.resolve():raise ValueError('El CUE referencia archivos fuera de su carpeta.')
            if child.is_file():files.append(child)
    targets={p.resolve() for p in files}
    for other in entries:
        if other.id==entry.id:continue
        if other.source and pathlib.Path(other.source).resolve() in targets:raise ValueError('Otro juego de la biblioteca usa uno de estos archivos.')
        other_path=pathlib.Path(other.source) if other.source else None
        if other_path and other_path.suffix.lower()=='.cue' and other_path.is_file():
            for track in re.findall(r'^\s*FILE\s+"([^"]+)"',other_path.read_text(errors='replace'),re.I|re.M):
                if (other_path.parent/track).resolve() in targets:raise ValueError('Otro CUE de la biblioteca comparte una pista de este disco.')
        if any(pathlib.Path(a).is_absolute() and pathlib.Path(a).resolve() in targets for a in other.command):raise ValueError('Otro acceso utiliza este archivo para ejecutarse.')
    return list(dict.fromkeys(files))

def trash(entry,entries,trash_file=None):
    files=files_for(entry,entries)
    if trash_file is None:
        from gi.repository import Gio
        trash_file=lambda p:Gio.File.new_for_path(str(p)).trash(None)
    for p in files:
        if trash_file(p) is False:raise OSError('No se pudo enviar a la papelera: '+p.name)
    return len(files)
