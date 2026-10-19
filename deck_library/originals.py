"""Match originals to installed ports, with explicit hide/trash choices."""
import pathlib,re
from .library_view import title_key,entry_type
from .models import atomic_json
ALIASES={'crashteamracingturbocharged':'crashteamracing','ctrcrashteamracing':'crashteamracing','crashteamracing':'crashteamracing','mariokartwiicompiled':'mariokartwii'}
def key(name):
    value=re.sub(r'[^a-z0-9]','',title_key(name));return ALIASES.get(value,value)
def pairs(entries):
    result=[];ports=[e for e in entries if entry_type(e)=='port' and e.metadata.get('configured') is not False]
    for original in entries:
        if entry_type(original)!='emulator':continue
        matches=[p for p in ports if (original.game_id and p.game_id and original.game_id.upper()==p.game_id.upper()) or key(original.name) in {key(p.name),key(p.metadata.get('game_title',''))}]
        if matches:result.append((original,matches))
    return result

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
