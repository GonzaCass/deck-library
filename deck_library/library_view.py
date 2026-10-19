"""How the library is grouped for display: entry types, filters and duplicate handling."""
import re
from .artwork import normalized

TYPES=[('port','Ports'),('emulator','Emulador'),('minecraft','Instancias de Minecraft'),('steam','Accesos de Steam'),('custom','Personalizados')]
TYPE_LABELS=dict(TYPES)

def entry_type(entry):
    """Port (native, recompiled or WiiCompiled), emulator game, Minecraft instance, imported Steam shortcut or custom command."""
    if entry.kind in ('port','wiicompiled'):return 'port'
    if entry.kind=='emulated':return 'emulator'
    if entry.kind=='minecraft' or entry.platform=='Minecraft' and entry.kind!='steam':return 'minecraft'
    if entry.kind=='steam':return 'steam'
    return 'custom'

def loose(name):
    """Name with every letter and digit kept, brackets included."""
    return re.sub(r'[^a-z0-9]','',name.lower())

def title_key(name):
    """Name without edition tags such as (USA), (PAL) or (PS1 recompilado)."""
    return normalized(name)

def duplicate_emulator_entries(entries):
    """Emulator entries whose game is already available as a port (same title once tags are removed)."""
    ports=set()
    for e in entries:
        if entry_type(e)=='port':ports|={title_key(e.name),*([title_key(e.metadata['game_title'])] if e.metadata.get('game_title') else [])}
    return [e for e in entries if entry_type(e)=='emulator' and title_key(e.name) in ports]

def visible_entries(entries,prefer_ports=True):
    """Entries to show; with `prefer_ports` the emulator version of a game that has a port is left out."""
    entries=[e for e in entries if not e.metadata.get('library_app')]
    hidden={e.id for e in duplicate_emulator_entries(entries)} if prefer_ports else set()
    return [e for e in entries if e.id not in hidden],len(hidden)
